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

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--intactFile', help='simplified + normalized INTACT data')
    parser.add_argument('-s', '--scidtDir', help='Directory for sciDT files')
    parser.add_argument('-o', '--outFile', help='Output file')
    args = parser.parse_args()
  
    frames = []
  
    intact_tsv = pd.read_csv(args.intactFile, sep='\t')
    
    fries_sentences = []
    fries_hits = []
    fries_events = []
    count = 0
    fries_count = 0
    hit_count = 0
    miss_count = 0
    for i,row in intact_tsv.iterrows():
        pmid = row['pmid']
        print(pmid)
        intact_fig = row['fig']
        p1 = row['p1_xref']
        p2 = row['p2_xref']
        p3 = row['p3_xref']

        fries_events_local = []
        
        # find the figure numbers in the paper designation 
        scidt_path = os.path.join(args.scidtDir, str(pmid) + ".tsv")
        if( os.path.isfile( scidt_path ) ):
            scidt_tsv = pd.read_csv(scidt_path, sep='\t')
            for i2,row2 in scidt_tsv.iterrows():
                fries_sentence = row2['friesSentenceId'] 
                fries_event = row2['friesEventsTypes'] 
                scidt_figs = row2['Figure Assignment']
                if( scidt_figs == scidt_figs and fries_event == fries_event):
                    for scidt_fig in scidt_figs.split('|'):
                        if scidt_fig == intact_fig and 'complex-assembly' in fries_event:
                            fries_count += 1
                            if( p1 != p1 or p2 != p2 or p3 != p3):
                                hit = "MISS"
                                miss_count += 1
                            elif( (p1 == '-' or p1 in fries_event) and 
                                (p2 == '-' or p2 in fries_event) and 
                                (p3 == '-' or p3 in fries_event) ):
                                hit = "HIT"
                                hit_count += 1
                            else :
                                hit = "MISS"
                                miss_count += 1
                            fries_events_local.append(fries_event + '[' + hit + ']')
                            
        fries_events.append(fries_events_local)
    
    intact_tsv['fries_events'] = pd.Series(fries_events)
        
    intact_tsv.to_csv(args.outFile, sep='\t')
    print ("COUNT: %d" % fries_count)
    print ("HITS: %d" % hit_count)
    print ("MISSES: %d" % miss_count )