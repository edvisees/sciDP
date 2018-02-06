'''
Created on April 27, 2017

@author: Gully
'''
from __future__ import print_function, division
import argparse
import codecs
import os

import numpy as np
import warnings

from sets import Set
from nltk.corpus import stopwords
from gensim.models.word2vec import Word2Vec
from gensim.models import KeyedVectors
import pandas as pd
import re

import pandas as pd
from nltk.corpus import stopwords
import re

def retrieve_sentences_for_modeling(inFile, fid):
    tsv = pd.read_csv(inFile, sep='\t')
    sentences = []

    sw = stopwords.words('english')
    regex1 = re.compile(r"[\(\)\{\}\[\]\;\.\'\"\,\/\_\*]", re.IGNORECASE)
    regex2 = re.compile(r"\s+", re.IGNORECASE)

    allHits = 0
    hits = 0
    j = 0
    for i, row in tsv.iterrows():
        sid = row['SentenceId']
        codeStr = row['Codes']
        paragraph = row['Paragraph']
        text = row['Sentence Text']
        heading = row['Headings']
        floatingBox = row['FloatingBox?']
        discourse = row['Discourse Type']
        reachData = row['friesEventsTypes']

        j += 1
        if (reachData == reachData):
            allHits += 1

        if (heading != heading):
            heading = ""

        if (floatingBox):
            continue

        if (('implication' not in discourse) and
                    'result' not in discourse):
            continue

        if 'exLink' in codeStr:
            continue

        if ('methods' in str(heading).lower()):
            continue

        r = 'X'
        if (reachData != reachData):
            r = '0'

        if (reachData == reachData):
            hits += 1

        # print(sid + ' (' + heading + ',' + discourse + ') ' + '[' + r + '] : ' + text )

        text = re.sub(regex1, "", text)
        sent = regex2.split(text)
        sent = [w for w in sent if w not in sw and len(w)>0]
        tup = (fid, sid, sent)
        sentences.append(tup)

    return sentences

def load_embedding_model():
    wv = KeyedVectors.load_word2vec_format(
        "/Users/Gully/Documents/Projects/2_active/bigMech/work/2017-01-30-ldk_paper/embeddings_pubmed_files/PMC-w2v.bin",
        binary=True)
    model = Word2Vec(iter=1)
    model.wv = wv
    return model

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inDir', help='Directory for input files')
    parser.add_argument('-o', '--outFile', help='Directory for output files')
    #parser.add_argument('-w', '--wv', help='Word Embedding File')
    args = parser.parse_args()

    sent_tup_list = []
    for fn in os.listdir(args.inDir):
        infile = args.inDir + "/" + fn
        if (os.path.isfile(infile) and fn.endswith('.tsv')):
            fid = fn.replace(".tsv", "")

            for tup in retrieve_sentences_for_modeling(infile, fid):
                sent_tup_list.append(tup);

    print (len(sent_tup_list))
    #tsv = pd.concat(1)
    #tsv.to_csv(args.outFile, sep='\t')