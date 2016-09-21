'''
Created on Sep 2, 2016

@author: Gully
'''
from __future__ import print_function, division
import argparse
import os

import pandas as pd


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inDir', help='Directory for input files')
    parser.add_argument('-o', '--outFile', help='Output file')
    args = parser.parse_args()

    os.remove(args.outFile)
    out = open(args.outFile, 'w')
    
    for fn in os.listdir(args.inDir):
        infile = args.inDir + "/" + fn
        if( os.path.isfile(infile) and fn.endswith('.tsv') ):
            print(infile)
            title = fn.replace(".tsv", "")
            tsv = pd.read_csv(infile, sep='\t')
            
            oldP = ""
            for i,row in tsv.iterrows():
                ct = row['Clause Text']
                es = row['ExperimentValues']
                dt = row['Discourse Type']
                dta = row['Discourse Type Annotations']
                sid = row['SentenceId']
                pid = row['Paragraph']
                
                if( oldP != pid and oldP[:1] != 't'):
                    out.write("\n")
                oldP = pid 
                
                out.write(ct + "\t" + str(dta) + '\n')
    
    out.close()
