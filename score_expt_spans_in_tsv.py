'''
Created on Sep 2, 2016

@author: Gully
'''
from __future__ import print_function, division
import argparse
import argparse_config
import codecs
import os

import numpy as np
import pandas as pd
import warnings

from sets import Set
import re

def add_spans(tsv, title): 
    
    expt_code_set = Set()   
    
    for i,row in tsv.iterrows():
        fs = row['fig_spans']
        fsc = row['fig_spans_corrected']
        sid = row['SentenceId']
        paragraph = row['Paragraph']
        heading = row['Headings']
        floatingBox = row['FloatingBox?']
    
        #print("i: " + str(i))
        #print("refs: " + str(es))
        #print("~~~~~~~~~~~~~~~~~~")
        
        if( heading != heading ):
            heading = ""
    
        if( re.match('^Result', heading) is None or floatingBox):
            continue
            
        if(fs!=fs):
            continue
            
        codes = fs.split('|')
    
        for c in codes:
            expt_code_set.add(c)
                      
    expt_codes = sorted(expt_code_set)
    print(expt_codes)

    f_score_table = []
    
    for f in expt_codes:
    
        tp = 0
        fp = 0
        tn = 0
        fn = 0
    
        #print(f)
    
        for i,row in tsv.iterrows():
            fs = row['fig_spans']
            fsc = row['fig_spans_corrected']
            heading = row['Headings']
            floatingBox = row['FloatingBox?']
    
            if( heading != heading ):
                heading = ""
    
            if( re.match('^Result', heading) is None or floatingBox):
                continue
    
            if(fs!=fs):
                fs = ''
                
            if(fsc!=fsc):
                fsc = ''
                
            match1 = re.search("(^|/|)"+f+"($|/|)", fs)
            match2 = re.search("(^|/|)"+f+"($|/|)", fsc)
            
            #print("\tpred: "+fs+"("+str(match1)+"), actual: "+fsc+"("+str(match2)+")")
            
            if( match1 is not None and match2 is not None ):
                tp += 1
            elif( match1 is None and match2 is None ):
                tn += 1
            elif( match1 is not None and match2 is None ):
                fp += 1
            elif( match1 is None and match2 is not None ):
                fn += 1
        
        print([title, f, tp, tn, fp, fn])
        
        precision = tp / (tp + fp)
        recall = 0.0
        if((tp + fn) > 0):
            recall = tp / (tp + fn)
        f_score = ( precision + recall ) / 2
        f_score_table.append([title, f, tp, tn, fp, fn, precision, recall, f_score])
        
        print([title, f, tp, tn, fp, fn, precision, recall, f_score])
            
    
    f_score_df = pd.DataFrame.from_records(f_score_table, columns=['pmid','expt','tp', 'tn', 'fp', 'fn', 'precision', 'recall', 'f_score']) 
    
    return f_score_df    

def score_expt_spans_for_tsv(input, title):
    
    tsv = pd.read_csv(input, sep='\t')

    scores = add_spans(tsv, title)

    return scores

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inDir', help='Directory for input files')
    parser.add_argument('-o', '--outFile', help='Directory for output files')
    args = parser.parse_args()
  
    frames = []
  
    for fn in os.listdir(args.inDir):
        infile = args.inDir + "/" + fn
        if( os.path.isfile(infile) and fn.endswith('.tsv') ):
            print(infile)
            title = fn.replace(".tsv", "")
            frames.append( score_expt_spans_for_tsv(infile, title) )
            
    tsv = pd.concat(frames)
    tsv.to_csv(args.outFile, sep='\t')