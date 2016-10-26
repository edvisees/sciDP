import gzip
import numpy
import os
import codecs
import argparse
import json
from elasticsearch import Elasticsearch, helpers

class RepReader(object):

    rep_min = 100000.0
    rep_max = -100000.0
    rep_size = 0

    def __init__(self, embedding_file=None, elastic=False):
        self.elastic = elastic
        if( elastic ):
            self.es = Elasticsearch()
        
        if( elastic and embedding_file is not None) :
            self.build_representation_elastic_index(embedding_file)
        elif(embedding_file is not None): 
            self.word_rep = {}
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
            
            # Use ELastic search index if available. This is problematic. Drop idea for now. 
            if( self.elastic ) :
                rep_res = self.es.search(index="scidt",doc_type=['rep'],
                    body={"query": {
                        "term" : { "word" : word }
                    }})
                if 'hits' in rep_res:
                    if( 'hits' in rep_res['hits'] ):
                        rep = self.numpy_rng.uniform(low = self.rep_min, high = self.rep_max, size = self.rep_shape)
                        self.word_rep[word] = rep
                    else:
                        rep = rep_res['hits']['hits'][0]['_source']['rep']
            else:
                if word not in self.word_rep:
                    rep = self.numpy_rng.uniform(low = self.rep_min, high = self.rep_max, size = self.rep_shape)
                    self.word_rep[word] = rep
                else:
                    rep = self.word_rep[word]
                reps.append(rep)
        return numpy.asarray(reps)

# format of data for elastic search. 
#{ "index" : { "_index" : "test", "_type" : "type1", "_id" : "1" } }
#{ "field1" : "value1" }

    def decode_ref_file(self, embedding_file):
        for i, x in enumerate(gzip.open(embedding_file)):
                x_parts = x.strip().split()
                if len(x_parts) == 2:
                        continue
        
                es_fields_keys = ('word', 'rep')
                es_fields_vals = (x_parts[0], x_parts[1:])
                
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
        
        res = self.es.search(index="scidt",
                body={"query": {
                    "ids" : {
                        "type" : "rep",
                        "values" : ["1"]
                    }
                }})
        rep_shape = len(res['hits']['hits'][0]['_source']['rep'])

        if( index_exists is False ):
            self.es.indices.create(index='scidt', ignore=400)
            # NOTE the (...) round brackets. This is for a generator.
            gen = ({
                            "_index": "scidt",
                            "_type" : "rep",
                            "_id"     : i,
                            "_source": es_d,
                     } for i, es_d in self.decode_ref_file(embedding_file))
            helpers.bulk(self.es, gen)
            res = self.es.search(index="scidt",
                body={"query": {
                    "ids" : {
                        "type" : "rep",
                        "values" : ["0"]
                    }
                }})
            rep_shape = len(res['hits']['hits'][1]['_source']['rep'])
            actions = [{
                "_index": "scidt",
                "_type": "meta",
                "_id": 0,
                "_source": {
                    "rep_min": str(RepReader.rep_min),
                    "rep_max": str(RepReader.rep_max),
                    "rep_shape": str(rep_shape)
                }
            }]        
            helpers.bulk(self.es, actions)
    
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
    
    