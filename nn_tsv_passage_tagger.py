import warnings
import sys
import codecs
import numpy
import argparse
import theano
import json
import pandas as pd
import csv
import itertools
import os
from rep_reader import RepReader
from util import read_passages, evaluate, make_folds, read_passages_from_tsv
from sets import Set

from keras.models import Sequential, Graph, model_from_json
from keras.layers.core import TimeDistributedDense, Dropout
from keras.layers.recurrent import LSTM, GRU
from keras.callbacks import EarlyStopping

from attention import TensorAttention
from keras_extensions import HigherOrderTimeDistributedDense
import psutil

class PassageTagger_tsv(object):
    def __init__(self, word_rep_file=None, pickled_rep_reader=None):
        if pickled_rep_reader:
            self.rep_reader = pickled_rep_reader
        elif word_rep_file:
            self.rep_reader = RepReader(word_rep_file)
        else:
            self.rep_reader = RepReader(elastic=True)            
        self.input_size = self.rep_reader.rep_shape[0]
        self.tagger = None

    def make_data(self, clauses, use_attention, maxseqlen=None, maxclauselen=None, label_ind=None, train=False, sec='w'):
        print >>sys.stderr, "Reading data.."
        
        str_seqs, label_seqs = read_passages_from_tsv(clauses,sec=sec)
                
        print >>sys.stderr, "Sample data for train:" if train else "Sample data for test:"
        print >>sys.stderr, zip(str_seqs[0], label_seqs[0])
        if not label_ind:
            self.label_ind = {"none": 0}
        else:
            self.label_ind = label_ind
        seq_lengths = [len(seq) for seq in str_seqs]
        if not maxseqlen:
            maxseqlen = max(seq_lengths)
        if not maxclauselen:
            if use_attention:
                clauselens = []
                for str_seq in str_seqs:
                    clauselens.extend([len(clause.split()) for clause in str_seq])
                maxclauselen = max(clauselens)
        X = []
        Y = []
        Y_inds = []
        #init_word_rep_len = len(self.rep_reader.word_rep)
        all_word_types = set([])
        for str_seq, label_seq in zip(str_seqs, label_seqs):
            for i, label in enumerate(label_seq):
                if label not in self.label_ind:
                    if(label != label):
                        raise Exception('Found NaN in label for clause: ' + str_seq[i] )
                    print "%d: %s" % (len(self.label_ind), label)
                    self.label_ind[label] = len(self.label_ind)
            if use_attention:
                x = numpy.zeros((maxseqlen, maxclauselen, self.input_size))
            else:
                x = numpy.zeros((maxseqlen, self.input_size))
            y_ind = numpy.zeros(maxseqlen)
            seq_len = len(str_seq)
            # The following conditional is true only when we've already trained, and one of the sequences in the test set is longer than the longest sequence in training.
            if seq_len > maxseqlen:
                str_seq = str_seq[:maxseqlen]
                seq_len = maxseqlen 
            if train:
                for i, (clause, label) in enumerate(zip(str_seq, label_seq)):
                    clause_rep = self.rep_reader.get_clause_rep(clause)
                    for word in clause.split():
                        all_word_types.add(word)
                    if use_attention:
                        if len(clause_rep) > maxclauselen:
                            clause_rep = clause_rep[:maxclauselen]
                        x[-seq_len+i][-len(clause_rep):] = clause_rep
                    else:
                        x[-seq_len+i] = numpy.mean(clause_rep, axis=0)
                    y_ind[-seq_len+i] = self.label_ind[label]
                X.append(x)
                Y_inds.append(y_ind)
            else:
                for i, clause in enumerate(str_seq):
                    if(clause != clause):
                        clause = "none"
                    clause_rep = self.rep_reader.get_clause_rep(clause)
                    for word in clause.split():
                        all_word_types.add(word)
                    if use_attention:
                        if len(clause_rep) > maxclauselen:
                            clause_rep = clause_rep[:maxclauselen]
                        x[-seq_len+i][-len(clause_rep):] = clause_rep
                    else:
                        x[-seq_len+i] = numpy.mean(clause_rep, axis=0)
                X.append(x)
        #final_word_rep_len = len(self.rep_reader.word_rep)
        #oov_ratio = float(final_word_rep_len - init_word_rep_len)/len(all_word_types)
        #print >>sys.stderr, "OOV ratio: %f" % oov_ratio
        process = psutil.Process(os.getpid())
        for j,y_ind in enumerate(Y_inds):
            y = numpy.zeros((maxseqlen, len(self.label_ind)))
            for i, y_ind_i in enumerate(y_ind):
                y[i][int(y_ind_i)] = 1
            Y.append(y) 
            #print "%d/%d" % (j, len(Y_inds))
        self.rev_label_ind = {i: l for (l, i) in self.label_ind.items()}
        return seq_lengths, numpy.asarray(X), numpy.asarray(Y)

    def get_attention_weights(self, X_test):
        if not self.tagger:
            raise RuntimeError, "Tagger not trained yet!"
        inp = self.tagger.get_input()
        att_out = None
        for layer in self.tagger.layers:
            if layer.get_config()['name'].lower() == "tensorattention":
                att_out = layer.get_output()
                break
        if not att_out:
            raise RuntimeError, "No attention layer found!"
        f = theano.function([inp], att_out)
        return f(X_test)

    def predict(self, X, bidirectional, test_seq_lengths=None, tagger=None):
        if not tagger:
            tagger = self.tagger
        if not tagger:
            raise RuntimeError, "Tagger not trained yet!"
        if test_seq_lengths is None:
            # Determining actual lengths sans padding
            x_lens = []
            for x in X:
                x_len = 0
                for i, xi in enumerate(x):
                    if xi.sum() != 0:
                        x_len = len(x) - i
                        break
                x_lens.append(x_len)
        else:
            x_lens = test_seq_lengths
        if bidirectional:
            pred_probs = tagger.predict({'input':X})['output']
        else:
            pred_probs = tagger.predict(X)
        pred_inds = numpy.argmax(pred_probs, axis=2)
        pred_label_seqs = []
        for pred_ind, x_len in zip(pred_inds, x_lens):
            pred_label_seq = [self.rev_label_ind[pred] for pred in pred_ind][-x_len:]
            # If the following number is positive, it means we ignored some clauses in the test passage to make it the same length as the ones we trained on.
            num_ignored_clauses = max(0, x_len - len(pred_label_seq))
            # Make labels for those if needed.
            if num_ignored_clauses > 0:
                warnings.warn("Test sequence too long. Ignoring %d clauses at the beginning and labeling them none." % num_ignored_clauses)
                ignored_clause_labels = ["none"] * num_ignored_clauses
                pred_label_seq = ignored_clause_labels + pred_label_seq
            pred_label_seqs.append(pred_label_seq)
        return pred_probs, pred_label_seqs, x_lens

    def fit_model(self, X, Y, use_attention, att_context, bidirectional):
        print >>sys.stderr, "Input shape:", X.shape, Y.shape
        early_stopping = EarlyStopping(patience = 2)
        num_classes = len(self.label_ind)
        if bidirectional:
            tagger = Graph()
            tagger.add_input(name='input', input_shape=X.shape[1:])
            if use_attention:
                tagger.add_node(TensorAttention(X.shape[1:], context=att_context), name='attention', input='input')
                lstm_input_node = 'attention'
            else:
                lstm_input_node = 'input'
            tagger.add_node(LSTM(X.shape[-1]/2, return_sequences=True), name='forward', input=lstm_input_node)
            tagger.add_node(LSTM(X.shape[-1]/2, return_sequences=True, go_backwards=True), name='backward', input=lstm_input_node)
            tagger.add_node(TimeDistributedDense(num_classes, activation='softmax'), name='softmax', inputs=['forward', 'backward'], merge_mode='concat', concat_axis=-1)
            tagger.add_output(name='output', input='softmax')
            tagger.summary()
            tagger.compile('adam', {'output':'categorical_crossentropy'})
            #tagger.fit({'input':X, 'output':Y}, validation_split=0.1, callbacks=[early_stopping], show_accuracy=True, nb_epoch=100, batch_size=10)
            tagger.fit({'input':X, 'output':Y}, validation_split=0.1, callbacks=[early_stopping],  nb_epoch=100, batch_size=10)
        else:
            tagger = Sequential()
            word_proj_dim = 50
            if use_attention:
                _, input_len, timesteps, input_dim = X.shape
                tagger.add(HigherOrderTimeDistributedDense(input_dim=input_dim, output_dim=word_proj_dim))
                att_input_shape = (input_len, timesteps, word_proj_dim)
                print >>sys.stderr, "Attention input shape:", att_input_shape
                tagger.add(Dropout(0.5))
                tagger.add(TensorAttention(att_input_shape, context=att_context))
            else:
                _, input_len, input_dim = X.shape
                tagger.add(TimeDistributedDense(input_dim=input_dim, input_length=input_len, output_dim=word_proj_dim))
            tagger.add(LSTM(input_dim=word_proj_dim, output_dim=word_proj_dim, input_length=input_len, return_sequences=True))
            tagger.add(TimeDistributedDense(num_classes, activation='softmax'))
            tagger.summary()
            tagger.compile(loss='categorical_crossentropy', optimizer='adam')
            tagger.fit(X, Y, validation_split=0.1, callbacks=[early_stopping], show_accuracy=True, batch_size=10)

        return tagger

    def train(self, X, Y, use_attention, att_context, bidirectional, cv=True, folds=5):
        if cv:
            cv_folds = make_folds(X, Y, folds)
            accuracies = []
            fscores = []
            for fold_num, ((train_fold_X, train_fold_Y), (test_fold_X, test_fold_Y)) in enumerate(cv_folds):
                tagger = self.fit_model(train_fold_X, train_fold_Y, use_attention, att_context, bidirectional)
                pred_probs, pred_label_seqs, x_lens = self.predict(test_fold_X, bidirectional, tagger=tagger)
                pred_inds = numpy.argmax(pred_probs, axis=2)
                flattened_preds = []
                flattened_targets = []
                for x_len, pred_ind, test_target in zip(x_lens, pred_inds, test_fold_Y):
                    flattened_preds.extend(pred_ind[-x_len:])
                    flattened_targets.extend([list(tt).index(1) for tt in test_target[-x_len:]])
                assert len(flattened_preds) == len(flattened_targets)
                accuracy, weighted_fscore, all_fscores = evaluate(flattened_targets, flattened_preds)
                print >>sys.stderr, "Finished fold %d. Accuracy: %f, Weighted F-score: %f"%(fold_num, accuracy, weighted_fscore)
                print >>sys.stderr, "Individual f-scores:"
                for cat in all_fscores:
                    print >>sys.stderr, "%s: %f"%(self.rev_label_ind[cat], all_fscores[cat])
                accuracies.append(accuracy)
                fscores.append(weighted_fscore)
            accuracies = numpy.asarray(accuracies)
            fscores = numpy.asarray(fscores)
            print >>sys.stderr, "Accuracies:", accuracies
            print >>sys.stderr, "Average: %0.4f (+/- %0.4f)"%(accuracies.mean(), accuracies.std() * 2)
            print >>sys.stderr, "Fscores:", fscores
            print >>sys.stderr, "Average: %0.4f (+/- %0.4f)"%(fscores.mean(), fscores.std() * 2)
        self.tagger = self.fit_model(X, Y, use_attention, att_context, bidirectional)
        model_ext = "att=%s_cont=%s_bi=%s"%(str(use_attention), att_context, str(bidirectional))
        model_config_file = open("model_%s_config.json"%model_ext, "w")
        model_weights_file_name = "model_%s_weights"%model_ext
        model_label_ind = "model_%s_label_ind.json"%model_ext
        model_rep_reader = "model_%s_rep_reader.pkl"%model_ext
        print >>model_config_file, self.tagger.to_json()
        self.tagger.save_weights(model_weights_file_name, overwrite=True)
        json.dump(self.label_ind, open(model_label_ind, "w"))
        #pickle.dump(self.rep_reader, open(model_rep_reader, "wb"))

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Train, cross-validate and run LSTM discourse tagger")
    argparser.add_argument('--repfile', type=str, help="Gzipped word embedding file")
    argparser.add_argument('--train_dir', type=str, help="Training Directory. TSV Files with Discourse Types set.")
    argparser.add_argument('--cv', help="Do cross validation", action='store_true')
    argparser.add_argument('--test_dir', metavar="TESTFILE", type=str,help="Directory of test file name(s), TSV-formatted.")
    argparser.add_argument('--out_dir', type=str, help="Output Directory.")
    argparser.add_argument('--paper_section', type=str, help="Which Section? [w]hole, ex_[m]eth, [r]esults_only)")
    argparser.add_argument('--use_attention', help="Use attention over words? Or else will average their representations", action='store_true')
    argparser.add_argument('--att_context', type=str, help="Context to look at for determining attention (word/clause)")
    argparser.set_defaults(att_context='word')
    argparser.add_argument('--bidirectional', help="Bidirectional LSTM", action='store_true')
    argparser.add_argument('--show_attention', help="When testing, if using attention, also print the weights", action='store_true')
    args = argparser.parse_args()
    repfile = args.repfile

    if args.paper_section:
        sec = args.paper_section
    else: 
        sec = "w"
    
    out_dir = ''
    if args.out_dir:
        out_dir = args.out_dir + "/"

    if args.train_dir:
        train = True
    else:
        train = False

    errors = False
    if args.test_dir:
        testfiles = []
        for root, dirs, files in os.walk(args.test_dir):
            for testfile in files:
                if os.path.isfile(os.path.join(root, testfile)) and testfile[-4:]=='.tsv' :
                    try:
                        tsv = pd.read_csv(os.path.join(root, testfile), sep='\t', quoting=csv.QUOTE_NONE, encoding='utf-8')
                    except:
                        e = sys.exc_info()[0]
                        print "Error: %s in %s" % (e, testfile)

                    for i,row in tsv.iterrows():
                        p = row['Paragraph']
                        c = row['Clause Text']
                        d = row['Discourse Type']
                        if( p!=p or c!=c or d!=d):
                            raise Exception('Error in ' + testfile + ' Headings ')
                        break
                    testfiles.append(os.path.join(root, testfile))

        test = True
    else:
        test = False

    #    if errors:
    #        raise RuntimeError, "Error in TSV files"

    if not train and not test:
        raise RuntimeError, "Please specify a train file or test files."
    
    use_attention = args.use_attention
    att_context = args.att_context
    bid = args.bidirectional
    show_att = args.show_attention

    if train:
        # First returned value is sequence lengths (without padding)
        #nnt = PassageTagger(word_rep_file=repfile)
        if args.repfile is None:
            nnt = PassageTagger_tsv()
        else:
            nnt = PassageTagger_tsv(word_rep_file=repfile)

        clauses = []
        for root, dirs, files in os.walk(args.train_dir):
            for trainfile in files:
                if os.path.isfile(os.path.join(root, trainfile)) and trainfile[-4:]=='.tsv' :
                    print("reading data from " + os.path.join(root, trainfile))
                    tsv = pd.read_csv(os.path.join(root, trainfile), sep='\t',quoting=csv.QUOTE_NONE, encoding='utf-8')
                    for i,row in tsv.iterrows():
                        clauses.append(row)
        _, X, Y = nnt.make_data(clauses, use_attention, train=True, sec=sec)
        nnt.train(X, Y, use_attention, att_context, bid, cv=args.cv)
        
    if test:
        if train:
            label_ind = nnt.label_ind
        else:
            # Load the model from files
            model_ext = "att=%s_cont=%s_bi=%s"%(str(use_attention), att_context, str(bid))
            model_config_file = open("models/model_%s_config.json"%model_ext, "r")
            model_weights_file_name = "models/model_%s_weights"%model_ext
            model_label_ind = "models/model_%s_label_ind.json"%model_ext
            if args.repfile is None:
                nnt = PassageTagger_tsv()
            else:
                nnt = PassageTagger_tsv(word_rep_file=args.repfile)

            nnt.tagger = model_from_json(model_config_file.read(), custom_objects={"TensorAttention":TensorAttention, "HigherOrderTimeDistributedDense":HigherOrderTimeDistributedDense})
            print >>sys.stderr, "Loaded model:"
            print >>sys.stderr, nnt.tagger.summary()
            nnt.tagger.load_weights(model_weights_file_name)
            print >>sys.stderr, "Loaded weights"
            label_ind_json = json.load(open(model_label_ind))
            label_ind = {k: int(label_ind_json[k]) for k in label_ind_json}
            print >>sys.stderr, "Loaded label index:", label_ind
            
        if not use_attention:
            assert nnt.tagger.layers[0].name == "timedistributeddense"
            maxseqlen = nnt.tagger.layers[0].input_length
            maxclauselen = None
        else:
            for l in nnt.tagger.layers:
                if l.name == "tensorattention":
                    maxseqlen, maxclauselen = l.td1, l.td2
                    break
                
        all_actual_labels = []
        for test_file in testfiles:
            print test_file
            tsv = pd.read_csv(test_file, sep='\t',quoting=csv.QUOTE_NONE, encoding='utf-8')
            clauses = []
            for i,row in tsv.iterrows():
                clauses.append(row)
            str_seqs, label_seqs = read_passages_from_tsv(clauses)
            for l in list(itertools.chain(*label_seqs)):
                if l not in all_actual_labels:
                    all_actual_labels.append(l)

        conf_matrix = {}        
        f_score_counts = {}        
        for l in all_actual_labels:
            f_score_counts[l] = {}
            f_score_counts.get(l)['tp'] = 0
            f_score_counts.get(l)['tn'] = 0
            f_score_counts.get(l)['fp'] = 0
            f_score_counts.get(l)['fn'] = 0
            conf_matrix[l] = {}
            for ll in all_actual_labels:
                conf_matrix[l][ll] = 0
                
        for test_file in testfiles:

            print >>sys.stderr, "Predicting on file %s"%(test_file)
            test_out_file_name = test_file.split("/")[-1].replace(".tsv", "")+"_att=%s_cont=%s_bid=%s"%(str(use_attention), att_context, str(bid))+".tsv"
            print >> sys.stderr, "Outputting to file %s" % (test_out_file_name)

            outfile = open(out_dir + test_out_file_name, "w")
            
            tsv = pd.read_csv(test_file, sep='\t', quoting=csv.QUOTE_NONE, encoding='utf-8')
            clauses = []
            for i,row in tsv.iterrows():
                clauses.append(row)

            print test_file
            str_seqs, label_seqs = read_passages_from_tsv(clauses, sec=args.paper_section)
            
            test_seq_lengths, X_test, _ = nnt.make_data(clauses, 
                                                        use_attention, 
                                                        maxseqlen=maxseqlen, 
                                                        maxclauselen=maxclauselen, 
                                                        label_ind=label_ind, 
                                                        train=False,
                                                        sec=args.paper_section)
            print >>sys.stderr, "X_test shape:", X_test.shape
            pred_probs, pred_label_seqs, _ = nnt.predict(X_test, bid, test_seq_lengths)

            '''
            for i in range(0, len(label_seqs)):
                for j in range(0, len(label_seqs[i])):
                    actual_label = label_seqs[i][j] 
                    predicted_label = pred_label_seqs[i][j]
                    conf_matrix[actual_label][predicted_label] += 1
                    
                    if( actual_label == predicted_label ) :
                        f_score_counts.get(actual_label)['tp'] += 1 
                    elif( actual_label != predicted_label ) :
                        f_score_counts.get(actual_label)['fn'] += 1 
                        f_score_counts.get(predicted_label)['fp'] += 1 
            '''
            '''
            if show_att:
                    att_weights = nnt.get_attention_weights(X_test.astype('float32'))
                    pred_labels = list(itertools.chain(*pred_label_seqs))
                    tsv = pd.read_csv(test_file, sep='\t')
                    tsv['Discourse Label'] = pd.Series(pred_labels)
                    print >>sys.stderr, "Output file:", test_out_file_name
                    tsv.to_csv(test_out_file_name, sep='\t')
                    tsv = pd.read_csv(test_file, sep='\t')
                    clauses = []q
                    for i,row in tsv.iterrows():
                        clauses.append(row)
                    clause_seqs, _ = read_passages_from_tsv(clauses)
                    paralens = [[len(clause.split()) for clause in seq] for seq in clause_seqs]
                    for clauselens, sample_att_weights, pred_label_seq in zip(paralens, att_weights, pred_label_seqs):
                        for clauselen, clause_weights, pred_label in zip(clauselens, sample_att_weights[-len(clauselens):], pred_label_seq):
                            print >>outfile, pred_label, " ".join(["%.4f"%val for val in clause_weights[-clauselen:]])
                        print >>outfile
                    
            else:'''

            # Write output to data files.
            pred_labels = list(itertools.chain(*pred_label_seqs))
            tsv = pd.read_csv(test_file, sep='\t',quoting=csv.QUOTE_NONE, encoding='utf-8')
            tsv['Discourse Label'] = pd.Series(pred_labels)
            print >>sys.stderr, "Output file:", test_out_file_name
            tsv.to_csv(test_out_file_name, sep='\t',encoding='utf-8')

        print "CONFUSION MATRIX"
        s = "            "
        for l in all_actual_labels:
            s += "%5s" % (l[:4]) + " "
        print s
        for l in all_actual_labels:
            s = "%12s" % (l)
            for ll in all_actual_labels:
                s += "%5d" % (conf_matrix[l][ll])
            print s
        
        print "\n~~~~~~~\n"
        
        # PRINT SUMMARY DATA
        print "%14s||%4s|%4s|%4s|| %4s| %4s|| %4s||" % ('label','tp','fp','fn','P','R','F1')
        for l in all_actual_labels:
            tp = f_score_counts.get(l)['tp']
            fp = f_score_counts.get(l)['fp']
            fn = f_score_counts.get(l)['fn']
            P = 0.0 if tp == 0 else 1.0 * tp/(tp+fp)
            R = 0.0 if tp == 0 else 1.0 * tp/(tp+fn)
            F1 = (P + R) / 2
            print "%14s||%4d|%4d|%4d|| %0.2f| %0.2f|| %0.2f||" % (l,tp,fp,fn,P,R,F1)
