from bottle import Bottle
from bottle import route, run
from bottle import get, post, request # or route

import warnings
import sys
import codecs
import numpy
import argparse
import theano
import json
import pickle

from rep_reader import RepReader
from util import read_passages, evaluate, make_folds

from keras.models import Sequential, Graph, model_from_json
from keras.layers.core import TimeDistributedDense, Dropout
from keras.layers.recurrent import LSTM, GRU
from keras.callbacks import EarlyStopping

from attention import TensorAttention
from keras_extensions import HigherOrderTimeDistributedDense

from nn_passage_tagger import PassageTagger
from scidtPlugin import SciDTPlugin

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Train, cross-validate and run LSTM discourse tagger")
    argparser.add_argument('--repfile', type=str, help="Gzipped word embedding file")
    argparser.add_argument('--use_attention', help="Use attention over words? Or else will average their representations", action='store_true')
    argparser.add_argument('--att_context', type=str, help="Context to look at for determining attention (word/clause)")
    argparser.set_defaults(att_context='word')
    argparser.add_argument('--bidirectional', help="Bidirectional LSTM", action='store_true')
    argparser.add_argument('--show_attention', help="When testing, if using attention, also print the weights", action='store_true')
    args = argparser.parse_args()
    repfile = args.repfile
    use_attention = args.use_attention
    att_context = args.att_context
    bid = args.bidirectional
    show_att = args.show_attention

    model_ext = "att=%s_cont=%s_bi=%s"%(str(use_attention), att_context, str(bid))
    model_config_file = open("model_%s_config.json"%model_ext, "r")
    model_weights_file_name = "model_%s_weights"%model_ext
    model_label_ind = "model_%s_label_ind.json"%model_ext
    model_rep_reader = "model_%s_rep_reader.pkl"%model_ext

    scidt = SciDTPlugin(use_attention=args.use_attention, 
                        att_context=args.att_context,
                        bidirectional=args.bidirectional)
    app = Bottle()
    app.install(scidt)
    
    @app.route('/txt') # or @route('/scidp')
    def scidt():
        return '''
            <form action="/txt" method="post" enctype="multipart/form-data">
                <label>Upload the file to be parsed here</label><br>
                <input type="file" name="file">
                <input value="Submit" type="submit">
            </form>
        '''
    
    @app.post('/txt') # or @route('/login', method='POST')
    def run_scidt_tagger(scidt):
        
        lines = request.files.get('file').file.read().split('\n')
        passages = []
        for l in lines:
            ll = l.split('\t')
            passages.append(ll[0])
        tags = scidt.tag_passage(passages)
        out = "<html><body><table>"
        for l in zip(passages, tags.split('\n')):
           out += '<tr><td>' + '</td><td>'.join(l) + '</td></tr>\n' 
        out += '</table></body></html>' 
        return out
    
    run(app, host='0.0.0.0', port=8787, debug=True)
