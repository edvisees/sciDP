import inspect
import inspect

from bottle import PluginError, error
from urllib2 import HTTPError

import warnings
import sys
import codecs
import numpy
import argparse
import theano
import json
import pickle

from keras.models import Sequential, Graph, model_from_json
from keras.layers.core import TimeDistributedDense, Dropout
from keras.layers.recurrent import LSTM, GRU
from keras.callbacks import EarlyStopping

from attention import TensorAttention
from keras_extensions import HigherOrderTimeDistributedDense

from nn_passage_tagger import PassageTagger
from util import read_passages

class SciDTPlugin(object):
    ''' This plugin passes an sciDT handle to route callbacks
    that accept a `scidt` keyword argument. If a callback does not expect
    such a parameter, no connection is made. You can override the sciDT
    settings on a per-route basis. '''

    name = 'scidt'
    api = 2

    def __init__(self, use_attention=True, 
                 att_context='word', 
                 bidirectional=False,
                 keyword='scidt'):
        self.keyword = keyword
         
        self.use_attention = use_attention
        self.att_context = att_context
        self.bidirectional = bidirectional
         
        model_ext = "att=%s_cont=%s_bi=%s"%(str(use_attention), att_context, str(bidirectional))
        model_config_file = open("model_%s_config.json"%model_ext, "r")
        model_weights_file_name = "model_%s_weights"%model_ext
        model_label_ind = "model_%s_label_ind.json"%model_ext
        model_rep_reader = "model_%s_rep_reader.pkl"%model_ext
        
        self.nnt = PassageTagger()
        
        self.nnt.tagger = model_from_json(model_config_file.read(), custom_objects={"TensorAttention":TensorAttention, "HigherOrderTimeDistributedDense":HigherOrderTimeDistributedDense})
        print >>sys.stderr, "Loaded model:"
        print >>sys.stderr, self.nnt.tagger.summary()
        self.nnt.tagger.load_weights(model_weights_file_name)
        print >>sys.stderr, "Loaded weights"
        label_ind_json = json.load(open(model_label_ind))
        self.nnt.label_ind = {k: int(label_ind_json[k]) for k in label_ind_json}

        print >>sys.stderr, "Loaded label index:", self.nnt.label_ind
        
        if not use_attention:
            assert self.nnt.tagger.layers[0].name == "timedistributeddense"
            self.maxseqlen = self.nnt.tagger.layers[0].input_length
            self.maxclauselen = None
        else:
            for l in self.nnt.tagger.layers:
                if l.name == "tensorattention":
                    self.maxseqlen, self.maxclauselen = l.td1, l.td2
                    break
        
    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
            keyword argument.'''
        for other in app.plugins:
            if not isinstance(other, SciDTPlugin): continue
            if other.keyword == self.keyword:
                raise PluginError("Found another sqlite plugin with "\
                "conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        # Override global configuration with route-specific values.
        conf = context.config.get('scidt') or {}
        keyword = conf.get('keyword', self.keyword)
        nnt = conf.get('nnt', self.nnt)
 
        # Test if the original callback accepts a 'db' keyword.
        # Ignore it if it does not need a database handle.
        args = inspect.getargspec(context.callback)[0]
        if keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            
            # Add the tagger handle as a keyword argument.
            kwargs[keyword] = self

            #try:
            rv = callback(*args, **kwargs)
            #except StandardError, e:
            #    raise HTTPError(500, "SciDT Server Error", e)

            return rv

        # Replace the route callback with the wrapped one.
        return wrapper
    
    def tag_passage(self, clause_list):
        
        test_seq_lengths, X_test, _ = self.nnt.make_data(clause_list, 
                                                     self.use_attention,
                                                     maxseqlen=self.maxseqlen, 
                                                     maxclauselen=self.maxclauselen, 
                                                     label_ind=self.nnt.label_ind, 
                                                     train=False)
        print >>sys.stderr, "X_test shape:", X_test.shape
        pred_probs, pred_label_seqs, _ = self.nnt.predict(X_test, 
                                                          self.bidirectional, 
                                                          test_seq_lengths)

        out = ""
        for pred_label_seq in pred_label_seqs:
            for pred_label in pred_label_seq:
                out += pred_label + "\n"
            out += "\n"

        return out
    