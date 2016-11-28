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
from traitlets.config.application import catch_config_error

def save_extracted_experiments(input, outdir, title): 
    
    tsv = pd.read_csv(input, sep='\t')

    expt_code_set = Set()   
    
    for i,row in tsv.iterrows():
        fs = row['fig_spans']
        sid = row['SentenceId']
        paragraph = row['Paragraph']
        discourse = row['Discourse Type']
        heading = str(row['Headings'])
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
    #print(expt_codes)
    
    problems = []

    for f in expt_codes:
        outfile = outdir+"/"+title+"_"+f+".tsv"
        if( os.path.isfile(outfile) ): 
            continue
        
        idx = []
                    
        for i,row in tsv.iterrows():
            fs = row['fig_spans']
            heading = str(row['Headings'])
            floatingBox = row['FloatingBox?']
    
            if( heading != heading ):
                heading = ""
    
            if( re.match('^Result', heading) is None or floatingBox):
                continue
    
            if(fs!=fs):
                fs = ''
                   
            match1 = re.search("(^|/|)"+f+"($|/|)", fs)
            
            if( match1 is not None ):
                if( os.path.isdir(outdir) is False):
                    os.makedirs(outdir)
                idx.append(i)
    
        if( len(idx) > 0 ): 
            out_tsv = pd.DataFrame(tsv,index=idx)
            out_tsv.to_csv(outfile, sep='\t')
        else: 
            problems.append(title)
    
    return problems

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inDir', help='Directory for input files')
    parser.add_argument('-o', '--outDir', help='Directory for output files')
    args = parser.parse_args()
  
    frames = []
    problems = []
    
    for fn in os.listdir(args.inDir):
        infile = args.inDir + "/" + fn
        outdir = args.outDir + "/" + fn[:(len(fn)-len("_spans.tsv"))]

        if( os.path.isfile(infile) and fn.endswith('.tsv') ):
            print(infile)
            title = fn.replace("_spans.tsv", "")
            problems.append(save_extracted_experiments(infile, outdir, title))
    
    print(problems)
            