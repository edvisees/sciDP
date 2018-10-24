'''
Created on Sep 2, 2016

@author: Gully
'''
from __future__ import print_function, division
import argparse
import os
from gensim.models.keyedvectors import KeyedVectors

import pandas as pd


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inFile', help='Input file')
    parser.add_argument('-o', '--outFile', help='Output file')
    args = parser.parse_args()

    if os.path.exists(args.outFile):
        os.remove(args.outFile)
    model = KeyedVectors.load_word2vec_format(args.inFile, binary=True)
    model.save_word2vec_format(args.inFile, binary=False)
