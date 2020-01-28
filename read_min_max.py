import gzip
import numpy
import os
import codecs
import argparse
import json
import string
import re
import time

from elasticsearch import Elasticsearch, helpers

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Train, cross-validate and run LSTM discourse tagger")
    argparser.add_argument('--repfile', metavar='REP-FILE', type=str, help="Gzipped embedding file")
    args = argparser.parse_args()
    
    rep_min = 10000
    rep_max = -10000  
 
    start = time.time()
    
    i=0
    for x in gzip.open(args.repfile):
        x_parts = x.strip().split()
        minimum = min(float(x) for x in x_parts[1:])
        if( minimum < rep_min):
            rep_min = minimum
        maximum = max(float(x) for x in x_parts[1:])
        if( maximum > rep_max):
            rep_max = maximum
        i=i+1
        if( i%100000 == 0 ):
            print "it: " + str(i) + ", t=" + str(time.time()-start) + " s"

        
    print( "Min: " + str(rep_min) + ", Max: " + str(rep_max) )     