import gzip
import numpy
import os
import codecs
import argparse
import json
import string
import re
import time
import sys

from elasticsearch import Elasticsearch, helpers

class RepReader(object):

    rep_min = 100000.0
    rep_max = -100000.0
    rep_size = 0

    def __init__(self, embedding_file=None, elastic=False):
        self.elastic = elastic
        if( elastic ):
            self.es = Elasticsearch()
        
        self.skip_patterns = []
        self.skip_patterns.append( re.compile('^\<.*\>$') )
        
        self.word_rep = {}
            
        if( elastic and embedding_file is not None) :
            self.build_representation_elastic_index(embedding_file)
        elif(embedding_file is not None): 
            for x in gzip.open(embedding_file):
                x_parts = x.strip().split()
                if len(x_parts) == 2:
                    continue
                word = x_parts[0]
                vec = numpy.asarray([float(f) for f in x_parts[1:]])
                self.word_rep[word] = vec
            #self.word_rep = {x.split()[0]: numpy.asarray([float(f) for f in x.strip().split()[1:]]) for x in gzip.open(embedding_file)}
            self.rep_min = min([x.min() for x in self.word_rep.values()])
            self.rep_max = max([x.max() for x in self.word_rep.values()])
            self.rep_shape = self.word_rep.values()[0].shape
            self.numpy_rng = numpy.random.RandomState(12345)
        else:
            self.elastic = True
            meta = self.es.search(index="scidt",doc_type=['meta'],
                body={"query": {
                    "match_all": {}
                }})
            meta_dict = meta['hits']['hits'][0]['_source']
            self.rep_min = float(meta_dict['rep_min'])
            self.rep_max = float(meta_dict['rep_max'])
            self.rep_shape = int(meta_dict['rep_shape']),
            self.numpy_rng = numpy.random.RandomState(12345)
        
    def get_clause_rep(self, clause):
        reps = []
        for word in clause.split():
            
            w = self.preprocess_word_rep(word) 
            
            if w in self.word_rep:
                rep = self.word_rep[w]
            
            # Use elastic search index if available. 
            elif( self.elastic ):
                rep_res = self.es.search(index="scidt",doc_type=['rep'],
                    body={"query": {
                        "term" : { "word" : w }
                    }})
                try:
                    rep = rep_res['hits']['hits'][0]['_source']['rep']
                    self.word_rep[w] = rep
                except StandardError:
                    rep = self.numpy_rng.uniform(low = self.rep_min, high = self.rep_max, size = self.rep_shape)
                    self.word_rep[w] = rep
                    
            else:
                rep = self.numpy_rng.uniform(low = self.rep_min, high = self.rep_max, size = self.rep_shape)
                self.word_rep[w] = rep
                
            reps.append(rep)
                
        return numpy.asarray(reps)

    def preprocess_word_rep(self, w):
        return w
    
#        for p in self.skip_patterns:
#            if re.match(p, w) :
#                return None
#        w = re.sub(ur"\p{P}+", "", w)
#        if len(w) == 0 :
#            return None

    def decode_ref_file(self, embedding_file):
        #from gensim.models import word2vec
        #model = word2vec.Word2Vec.load_word2vec_format('path/to/GoogleNews-vectors-negative300.bin', binary=True)
        #model.save_word2vec_format('path/to/GoogleNews-vectors-negative300.txt', binary=False)
        
        for i, x in enumerate(gzip.open(embedding_file)):
            x_parts = x.strip().split()
            if len(x_parts) == 2:
                    continue
    
            w = self.preprocess_word_rep(x_parts[0])
            if w is None:
                continue
            
            es_fields_keys = ('word', 'rep')
            es_fields_vals = (w, x_parts[1:])
            
            # Use Global variables to set maxima / minima,
            # TODO: Find a better way
            minimum = min(float(x) for x in x_parts[1:])
            if( minimum < RepReader.rep_min):
                RepReader.rep_min = minimum
            maximum = max(float(x) for x in x_parts[1:])
            if( maximum > RepReader.rep_max):
                RepReader.rep_max = maximum
                            
            # We return a dict holding values from each line
            es_d = dict(zip(es_fields_keys, es_fields_vals))

            # Return the row on each iteration
            yield i, es_d     # <- Note the usage of 'yield'

    def build_representation_elastic_index(self, embedding_file):
        
        #es.indices.delete(index='scidt', ignore=[400, 404])                

        index_exists = self.es.indices.exists(index=["scidt"],ignore=404)
        
        if( index_exists is False ):

            rep_min = 10000
            rep_max = -10000  
            shape = 0
    
            i=0
            count=0
            length = 0
            start = time.time()
            
            for x in gzip.open(args.repfile):
                
                x_parts = x.strip().split()
                
                if( len(x_parts) == 2 ):
                    count = x_parts[0]
                    shape = x_parts[1]
                    continue
                
                minimum = min(float(xx) for xx in x_parts[1:])
                if( minimum < rep_min):
                    rep_min = minimum
                maximum = max(float(xx) for xx in x_parts[1:])
                if( maximum > rep_max):
                    rep_max = maximum
                i=i+1
                if( i%100000 == 0 ):
                    print "it: " + str(i) + ", t=" + str(time.time()-start) + " s"
            
            self.es.indices.create(index='scidt', ignore=400)
            
            # Mapping to make the encoding of individual words unique.
            mapping_body = {
                "properties" : {
                    "word" : {
                        "type" : "string",
                        "index" : "not_analyzed" 
                    }
                }
            }
            self.es.indices.put_mapping("rep", mapping_body, "scidt")            
            
            # NOTE the (...) round brackets. This is for a generator.
            gen = ({
                            "_index": "scidt",
                            "_type" : "rep",
                            "_id"     : i,
                            "_source": es_d,
                     } for i, es_d in self.decode_ref_file(embedding_file))
            helpers.bulk(self.es, gen)
            
            actions = [{
                "_index": "scidt",
                "_type": "meta",
                "_id": 0,
                "_source": {
                    "rep_min": str(rep_min),
                    "rep_max": str(rep_max),
                    "rep_shape": str(shape)
                }
            }]      
            print actions  
            helpers.bulk(self.es, actions)
        
        meta = self.es.search(index="scidt",doc_type=['meta'],
                body={"query": {
                    "match_all": {}
                }})
        
        # Note that if we've just built the index, it doesn't immediately provide a response
        # So we search and wait until it provides data. 
        while(len(meta['hits']['hits']) == 0) :
            time.sleep(5)
            meta = self.es.search(index="scidt",doc_type=['meta'],
                body={"query": {
                    "match_all": {}
                }}) 
        
        meta_dict = meta['hits']['hits'][0]['_source']
        self.rep_min = float(meta_dict['rep_min'])
        self.rep_max = float(meta_dict['rep_max'])
        self.rep_shape = int(meta_dict['rep_shape']),
        self.numpy_rng = numpy.random.RandomState(12345)
        
if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Train, cross-validate and run LSTM discourse tagger")
    argparser.add_argument('--repfile', metavar='REP-FILE', type=str, help="Gzipped embedding file")
    args = argparser.parse_args()
    
    repreader = RepReader(args.repfile, elastic=True)
    
            #temp_file.write('{ "index" : { "_index" : "scidt", "_type" : "rep", "_id" : "' + str(i) + '" } }\n')
            #temp_file.write('{ "word" : "'+x_parts[0]+'", "rep" : '+ json.dumps(x_parts[1:]) + '}\n')
    
    