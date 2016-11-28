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

from sets import Set
import re

from bokeh.plotting import figure, show, save, output_notebook, output_file
from bokeh.models import ColumnDataSource, Range1d

#
# This function checks to see if there is a boundary condition between clause 1 and clause 2
# Returns a tuple: (True / False, Explanation) 
#
def checkForStartBoundary(clause1, clause2, expt_codes, tsv, c_s_lookup, s_c_lookup):
    
    row1 = tsv.loc[clause1]
    row2 = tsv.loc[clause2]
        
    # both clauses are in the same sentence => false 
    if( row1['SentenceId'] == row2['SentenceId'] ):
        return (False,"Same sentence")
    
    # clause 2 is a title paragraph => true
    elif( "header" in row2['Codes'] ):
        return (True, "?/header") 
    
    #
    # clause 1 is in a sentence where 
    #           (A) there are hypotheses/problems/facts 
    #           (B) there are results/implications with exLinks present
    # clause 2 is in a sentence where 
    #           (A) there are goals/methods 
    #           (B) there are results/implications with no exLinks
    #
    sentence1 = c_s_lookup[clause1]
    sentence2 = c_s_lookup[clause2]
    go_condition_2 = False
    for cs2 in s_c_lookup[sentence2]:
        disc2 = tsv.loc[cs2]['Discourse Type']
        inExHead2 = tsv.loc[cs2]['Codes']
        if( (disc2 == 'result' or disc2 == 'implication')
               and "exLink" not in inExHead2):
            go_condition_2 = True
        elif( disc2 == 'goal' or disc2 == 'method'):
            go_condition_2 = True
    if( go_condition_2 ) :
        for cs1 in s_c_lookup[sentence1]:
            disc1 = tsv.loc[cs1]['Discourse Type']
            inExHead1 = tsv.loc[cs1]['Codes']
            if(disc1 == 'hypothesis' or disc1 == 'problem' or disc1 == 'fact'):
                #print(tsv.loc[cs2])
                return (True, "A:"+disc1+inExHead1+"/"+disc2+inExHead2)
            elif((disc1 == 'result' or disc1 != 'implication') and "exLink" in inExHead1):
                #print(tsv.loc[cs2])
                return (True, "B:"+disc1+inExHead1+"/"+disc2+inExHead2)
    
    es1 = row1['ExperimentValues'] 
    if( es1 == es1 and len(set(expt_codes).intersection(es1.split('|'))) == 0 ):
        return (True, "|".join(expt_codes) + "!=" + es1 + "(1)")
    es2 = row2['ExperimentValues'] 
    if( es2 == es2 and len(set(expt_codes).intersection(es2.split('|'))) == 0 ):
        return (True, "|".join(expt_codes) + "!=" + es2 + "(2)")
            
    return (False,"end")

#
# This function checks to see if there is a boundary condition between clause 1 and clause 2
# Returns a tuple: (True / False, Explanation) 
#
def checkForEndBoundary(clause1, clause2, expt_codes, tsv, c_s_lookup, s_c_lookup):
    
    row1 = tsv.loc[clause1]
    row2 = tsv.loc[clause2]
        
    # both clauses are in the same sentence => false 
    if( row1['SentenceId'] == row2['SentenceId'] ):
        return (False,"Same sentence")
    
    # clause 2 is a title paragraph => true
    elif( "header" in row2['Codes'] ):
        return (True, "?/header") 
    
    #
    # clause 1 is in a sentence where there are results/implications with no exLinks and
    # clause 2 is in a sentence where 
    #           (A) there are goals/methods/hypotheses/problems/facts 
    #           (B) there are results/implications with exLinks present
    #
    sentence1 = c_s_lookup[clause1]
    sentence2 = c_s_lookup[clause2]
    go_condition_1 = False
    for cs1 in s_c_lookup[sentence1]:
        disc1 = tsv.loc[cs1]['Discourse Type']
        inExHead1 = tsv.loc[cs1]['Codes']
        if( (disc1 == 'result' or disc1 == 'implication')
               and "exLink" not in inExHead1):
            go_condition_1 = True
    if( go_condition_1 ) :
        for cs2 in s_c_lookup[sentence2]:
            disc2 = tsv.loc[cs2]['Discourse Type']
            inExHead2 = tsv.loc[cs2]['Codes']
            if(disc1 != 'result' and disc1 != 'implication'):
                #print(tsv.loc[cs2])
                return (True, "C"+disc1+inExHead1+"/"+disc2+inExHead2)
            elif((disc1 == 'result' or disc1 != 'implication') and "exLink" in inExHead2):
                #print(tsv.loc[cs2])
                return (True, "D"+disc1+inExHead1+"/"+disc2+inExHead2)
    
    es1 = row1['ExperimentValues'] 
    if( es1 == es1 and len(set(expt_codes).intersection(es1.split('|'))) == 0 ):
        return (True, "|".join(expt_codes) + "!=" + es1 + "(1)")
    es2 = row2['ExperimentValues'] 
    if( es2 == es2 and len(set(expt_codes).intersection(es2.split('|'))) == 0 ):
        return (True, "|".join(expt_codes) + "!=" + es2 + "(2)")
            
    return (False,"end")

def add_spans(tsv): 

    c_s_lookup = {}
    c_p_lookup = {}
    s_c_lookup = {}
    p_c_lookup = {}
    
    fig_ref_set = Set()
    expt_code_set = Set()   
    
    clause_max = -1
    clause_min = 1000
    
    for i,row in tsv.iterrows():
        es = row['ExperimentValues']
        dt = row['Discourse Type']
        inExHead = row['Codes']
        sid = row['SentenceId']
        paragraph = row['Paragraph']
        heading = str(row['Headings'])
        floatingBox = row['FloatingBox?']
    
        #print("i: " + str(i))
        #print("refs: " + str(es))
        #print("~~~~~~~~~~~~~~~~~~")
        
        s = int(sid[1:])
        
        if(paragraph!=paragraph):
            continue

        p = 0
        if( paragraph == '-'):
            p = 0
        elif( paragraph[0:1] == 'p'):
            p = int(paragraph[1:])
        elif( paragraph[0:5] == 'title'):
            p = int(paragraph[5:])
        
        c_s_lookup[i] = s
        c_p_lookup[i] = p
        
        if( s_c_lookup.get(s) is None ):
            s_c_lookup[s] = [i]
        else:
            s_c_lookup.get(s).append(i)
        
        if( p_c_lookup.get(p) is None ):
            p_c_lookup[p] = [i]
        else:
            p_c_lookup.get(p).append(i)
        
        if( heading != heading ):
            heading = ""
        
        if( re.match('^Result', heading) is None or floatingBox):
            continue
        
        if( i > clause_max):
            clause_max = i
        if( i < clause_min):
            clause_min = i
        
        if(es!=es):
            continue
            
        try:
            codes = str(es).split('|')        
        except AttributeError:
            print(str(es) + " is not a string.  Skipping...")
            continue
    
        fig_ref_set.add(i)
    
        for c in codes:
            expt_code_set.add(c)
                      
    fig_refs = sorted(fig_ref_set)
    
    fig_spans = {}
    
    for i_fig in fig_refs:
        
        row = tsv.loc[i_fig]
        es = row['ExperimentValues']
        dt = row['Discourse Type']
        inExHead = row['Codes']
        sid = row['SentenceId']
        paragraph = row['Paragraph']
        heading = str(row['Headings'])
        floatingBox = row['FloatingBox?']
        
        try:
            expt_codes = str(es).split('|')
        except AttributeError:
            print(str(es) + " is not a string.  Skipping...")
            continue
        
        # search backwards for a boundary condition between sentences
        c1 = i_fig - 1
        c2 = i_fig 
        while( checkForStartBoundary(c1, c2, expt_codes, tsv, c_s_lookup, s_c_lookup)[0] is False ):
            c1 = c1-1
            c2 = c2-1
        expt_start = c2
            
        # search forwards for a boundary condition between sentences
        c1 = i_fig 
        c2 = i_fig + 1
        while( checkForEndBoundary(c1, c2, expt_codes, tsv, c_s_lookup, s_c_lookup)[0] is False ):
            c1 = c1+1
            c2 = c2+1
        expt_end = c1
    
        for c in range(expt_start, expt_end+1):
            if( fig_spans.get(c) is None ):
                fig_spans[c] = set(expt_codes)
            else:
                fig_spans.get(c).update(set(expt_codes))
        
        #print("Figure Location:  " + str(i_fig) )
        #print("Experiment Label: " + es )
        #print("Expt Start:       " + str(expt_start) )
        #print("Expt Start Expl:  " + str(checkForStartBoundary(expt_start-1, expt_start, expt_codes, tsv, c_s_lookup, s_c_lookup)) )
        #print("Expt End:         " + str(expt_end) )
        #print("Expt End Expl:    " + str(checkForEndBoundary(expt_end, expt_end+1, expt_codes, tsv, c_s_lookup, s_c_lookup)) )
        #print( "~~~~~~~~~~~~~~~~~~~~" )
    
    for i in fig_spans:
        fig_spans[i] = "|".join(fig_spans.get(i))
        #print(fig_spans[i])
        
    tsv['fig_spans'] = pd.Series(fig_spans, index=fig_spans)
    
    return tsv

def prepare_and_draw_gannt(filename, title, tsv):
    
    gantt_rows = []
    gantt_rows2 = []
    gantt_rows3 = []
    
    dtypes = ["fact","hypothesis","problem","goal"  ,"method","result","implication"]
    colors = ["Snow" ,"Snow"    ,"Snow" ,"LightGray","Gray"  ,"LightBlue"  ,"LightGreen"] 
    colors_s = pd.Series(colors, index=dtypes)
    
    all_codes = Set()   
    
    clause_max = -1
    clause_min = 1000
    
    for i,row in tsv.iterrows():
        fig_refs = row['ExperimentValues']
        fig_spans = row['fig_spans']
        dt = row['Discourse Type']
        inExHead = row['Codes']
        sid = row['SentenceId']
        paragraph = row['Paragraph']
        heading = str(row['Headings'])
        floatingBox = row['FloatingBox?']
        
        #print("i: " + str(i))
        #print("refs: " + str(fig_refs))
        #print("~~~~~~~~~~~~~~~~~~")
    
        if( heading != heading ):
            heading = ""
    
        #if(not floatingBox):
        #    clause_max = i
            
        if( re.match('^Result', heading) is None or floatingBox):
            continue
        
        if( i > clause_max):
            clause_max = i
        if( i < clause_min):
            clause_min = i
        
        if(fig_spans!=fig_spans):
            continue
        if(fig_refs!=fig_refs):
            fig_refs = ""
            
        fig_span_list = fig_spans.split('|')
        fig_ref_list = fig_refs.split('|')  
        
        #print("i: " + str(i))
        #print("spans: " + fig_spans)
        #print("refs: " + fig_refs)
        #print("~~~~~~~~~~~~~~~~~~")
    
        for fs in fig_span_list:
            all_codes.add(fs)
            
            if( fs in fig_ref_list ):
                gantt_rows2.append([fs, i])
            
            if('exLink' in inExHead):
                gantt_rows3.append([fs, i])     
            
            gantt_rows.append([fs, i, dt, heading])
                       
    codes_s = pd.Series(range(len(all_codes)), index=sorted(list(all_codes)))
    
    gantt_df = pd.DataFrame.from_records(gantt_rows, columns=['fig_span', 'clause_id','discourse_type', 'heading']) 
    gantt_df = gantt_df.sort(columns=['clause_id'], ascending=True)
    
    #print(codes_s.loc[gantt_df['expt'].tolist()].tolist())
    
    gantt_df['fig_span_id'] = codes_s.loc[gantt_df['fig_span'].tolist()].tolist()
    gantt_df['color'] = colors_s.loc[gantt_df['discourse_type'].tolist()].tolist()
    
    gantt_df2 = pd.DataFrame.from_records(gantt_rows2, columns=['fig_ref','clause_id']) 
    gantt_df2['fig_ref_id'] = codes_s.loc[gantt_df2['fig_ref'].tolist()].tolist()
    
    gantt_df3 = pd.DataFrame.from_records(gantt_rows3, columns=['fig_span', 'clause_id']) 
    gantt_df3['fig_span_id'] = codes_s.loc[gantt_df3['fig_span'].tolist()].tolist()

    output_file(filename, title=title, autosave=False, mode='cdn', root_dir=None)

    G=figure(title=title, width=800, height=600, 
         x_range=Range1d(clause_min, clause_max), 
         y_range=list(codes_s.index.values))

    G.xaxis.axis_label="Clause #"
    G.yaxis.axis_label="Figure Code"
    
    gantt_df['top'] = gantt_df['fig_span_id']+0.75
    gantt_df['bottom'] = gantt_df['fig_span_id']+1.25
    gantt_df['left'] = gantt_df['clause_id']-0.5
    gantt_df['right'] = gantt_df['clause_id']+0.5
    
    gantt_df2['offset'] = gantt_df2['fig_ref_id']+1
    
    gantt_df3['top'] = gantt_df3['fig_span_id']+0.75
    gantt_df3['bottom'] = gantt_df3['fig_span_id']+1.25
    gantt_df3['left'] = gantt_df3['clause_id']-0.5
    gantt_df3['right'] = gantt_df3['clause_id']+0.5
    
    cds = ColumnDataSource(gantt_df)
    G.quad(left='left', right='right', bottom='bottom', top='top',
           source=cds, line_color="gray", color='color')
    
    cds3 = ColumnDataSource(gantt_df3)
    G.quad(left='left', right='right', bottom='bottom', top='top',
           source=cds3, line_color="black")
    
    cds2 = ColumnDataSource(gantt_df2)
    G.scatter('clause_id', 'offset', source=cds2, marker='x', size=15,
                  line_color="red", fill_color="red")
    
    save(G)

def fill_expt_spans_for_tsv(input, title, tsv_output, img_output=None):
    
    tsv = pd.read_csv(input, sep='\t')

    tsv = add_spans(tsv)

    if( img_output is not None ):
        prepare_and_draw_gannt(img_output, title, tsv)

    tsv.to_csv(tsv_output, sep='\t')

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inDir', help='Directory for input files')
    parser.add_argument('-o', '--outDir', help='Directory for output files')
    parser.add_argument('-g', '--ganntChartDir', help='Directory for Gannt Chart output')
    args = parser.parse_args()
  
    for fn in os.listdir(args.inDir):
        infile = args.inDir + "/" + fn
        if( os.path.isfile(infile) and fn.endswith('.tsv') ):
            print(infile)
            title = fn.replace(".tsv", "")
            outfile = args.outDir + "/" + title + "_spans.tsv"
            if( args.ganntChartDir is not None ):
                ganntfile = args.ganntChartDir + "/" + title + ".html"
            if( not os.path.isfile(outfile) ):
                try:
                    fill_expt_spans_for_tsv(infile, title, outfile, ganntfile)
                except KeyError:
                    print("KeyError for " + infile)
