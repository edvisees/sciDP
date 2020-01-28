from __future__ import print_function, division
import argparse
import codecs
import os
from glob import glob
import ntpath

import numpy as np
import pandas as pd
import warnings

from sets import Set
import re

from sets import Set
import re
from tqdm import tqdm

from bs4 import BeautifulSoup
from bokeh.plotting import figure, show, save, output_notebook, output_file
from bokeh.models import ColumnDataSource, Range1d

def build_figure_extraction_patterns():
    bf = "\s*f(igs|igs\.|ig|ig\.|igure|\.|ig\:){0,1}"
    d =  "\s*(\d+\s*[\.\;\,]{0,1}\s*[a-z]*)\s*\.{0,1}\s*"
    d_split =  "\s*(\d*)\s*[\.\;\,]{0,1}\s*([a-z]*)"
    interval = "\s*(\d+)([a-z]+)\\-([a-z]+)"
    pattHash = {} 
    
    figPatt = []
    pattHash['figPatt'] = figPatt
    
    # 0. No alphanumeric codes at all: 'Figure. 1; more text'
    figPatt.append(re.compile("^" + bf + d + "$"))         
    figPatt.append(re.compile("^" + bf + "\s*(\d+\s*[\.\;\,]{0,1}\s*[a-z]*)[\,\;\.]{0,1}\s*t"))
    figPatt.append(re.compile("^" + bf + "\s*(\d+\s*[\.\;\,]{0,1}\s*[a-z]*)[\,\;\.]{0,1}\s*s"))
    figPatt.append(re.compile("^" + bf + "\s*(\d+\s*[\.\;\,]{0,1}\s*[a-z]*)[\,\;\.]{0,1}\s+and\s+s"))
    
    # [1]
    simplePatt = re.compile("^" + d + "$");
    pattHash['simplePatt'] = simplePatt
    
    # [2,4]    
    space2Patt = re.compile("^" + bf + d + "\s+" + bf + d + "$");
    pattHash['space2Patt'] = space2Patt

    # [2,4,6]    
    space3Patt = re.compile("^"+bf+d+"\s+"+bf+d+"\s+"+bf+d+"$");
    pattHash['space3Patt'] = space3Patt

    # [2,4]
    fullComma2Patt = re.compile("^" + bf + d + "[\;\,]" + bf + d + "$")
    pattHash['fullComma2Patt'] = fullComma2Patt
    
    # [2,3]
    comma2Patt = re.compile("^" + bf + d + "[\;\,]" + d + "$")
    pattHash['comma2Patt'] = comma2Patt

    # [1,2]
    simpleComma2Patt = re.compile("^" + d + "[\;\,]" + d + "$")
    pattHash['simpleComma2Patt'] = simpleComma2Patt

    # [2,3,4]
    comma3Patt = re.compile("^" + bf + d + "[\;\,]" + d + "[\;\,]" + d + "$");
    pattHash['comma3Patt'] = comma3Patt
    
    # [1,2,3]
    simpleComma3Patt = re.compile("^" + d + "[\;\,]" + d + "[\;\,]" + d + "$");
    pattHash['simpleComma3Patt'] = simpleComma3Patt

    # [2,3,4,5]
    comma4Patt = re.compile("^"+bf+d+"[\;\,]"+d+"[\;\,]"+d+"[\;\,]"+d+"$");
    pattHash['comma4Patt'] = comma4Patt

    # [2,3,4,5,6]
    comma5Patt = re.compile("^"+bf+d+"[\;\,]"+d+"[\;\,]"+d+"[\;\,]"+d+"[\;\,]"+d+"$");
    pattHash['comma5Patt'] = comma5Patt

    # [1,2,3,4]
    simpleComma4Patt = re.compile("^"+d+"[\;\,]"+d+"[\;\,]"+d+"[\;\,]"+d+"$");
    pattHash['simpleComma4Patt'] = simpleComma4Patt

    # [2,3]
    and2Patt = re.compile("^" + bf + d + "\s+and\s+" + d + "$");
    pattHash['and2Patt'] = and2Patt
    
    # [1,2]
    simpleAnd2Patt = re.compile("^" + d + "\s+and\s+" + d + "$");
    pattHash['simpleAnd2Patt'] = simpleAnd2Patt

    # [1,2,3]
    simple_a_and_b_patt = re.compile("^" + d_split + "\s+and\s+([a-z])$");
    pattHash['simple_a_and_b_patt'] = simple_a_and_b_patt

    # [2,3,4]
    a_and_b_patt = re.compile("^" + bf + d_split + "\s+and\s+([a-z])$");
    pattHash['a_and_b_patt'] = a_and_b_patt

    # [1,2,3]
    simple_a_comma_b_patt = re.compile("^" + d_split + "[\;\,]\s*([a-z])$");
    pattHash['simple_a_comma_b_patt'] = simple_a_comma_b_patt

    # [2,3,4]
    a_comma_b_patt = re.compile("^"+bf+d_split+"[\;\,]\s*([a-z])$");
    pattHash['a_comma_b_patt'] = a_comma_b_patt

    # [1,2,3]
    simple_a_comma_b_comma_c_patt = re.compile("^" + d_split + "[\;\,]\s*([a-z])\s*[\;\,]\s*([a-z])$");
    pattHash['simple_a_comma_b_comma_c_patt'] = simple_a_comma_b_comma_c_patt

    # [2,3,4]
    a_comma_b_comma_c_patt = re.compile("^"+bf+d_split+"[\;\,]\s*([a-z])\s*[\;\,]\s*([a-z])$");
    pattHash['a_comma_b_comma_c_patt'] = a_comma_b_comma_c_patt

    # [2,3,4,5]
    a_b_and_c_patt = re.compile("^" + bf + d_split + "[\;\,]\s+([a-z])\s+and\s+([a-z])$");
    pattHash['a_b_and_c_patt'] = a_b_and_c_patt

    # [1,2,3,4]
    simple_a_b_and_c_patt = re.compile("^" + d_split + "[\;\,]\s+([a-z])\s+and\s+([a-z])$");
    pattHash['simple_a_b_and_c_patt'] = simple_a_b_and_c_patt

    tableFigPatt = re.compile("^t(ab\.|ab|able){0,1}.*" + bf + d + "$");
    pattHash['tableFigPatt'] = tableFigPatt

    intervalPatt = re.compile("^" + bf + interval + "$");
    pattHash['intervalPatt'] = intervalPatt

    # simple single table (table 1, t1, tab. 1a)
    # returned value is second group
    tablePatt = re.compile("^t(ab\.|ab|able){0,1}\s*([\di]+[a-z]{0,1})[\,\;\.]{0,1}$");
    pattHash['tablePatt'] = tablePatt

    # simple single table (table 1, t1, tab. 1a)
    # returned value is third group
    suppTablePatt = re.compile("^s(upp|upp.|lementary){0,1}\s*t(ab\.|ab|able){0,1}\s*([i\d]+[a-z]{0,1})[\,\;\.]{0,1}$");
    pattHash['suppTablePatt'] = suppTablePatt
    
    return pattHash

def run_simple_matcher(fig_text, patt_hash, patt_code, groups=[1]):
    match = re.search(patt_hash.get(patt_code), fig_text)
    results = []
    if( match ) :
        for g in groups:
            results.append(match.group(g))
        return results
    else:
        return None

def build_matched_string(matched_list,code):
    matched_str = ""
    for mf in matched_list:
        if len(matched_str) > 0 :
            matched_str += '|'
        matched_str += code + mf.replace(" ", "").replace(".", "")
    return matched_str

def run_matcher(fig_text, patt_hash):
    
    if(fig_text == 'nfa' ):
        return None
    
    # strip out all parentheses.
    paren_patt = re.compile("(\(.+?\))")
    fig_text = re.sub(paren_patt, "", fig_text)

    # covert & to 'and'.
    fig_text = fig_text.replace("&", "and")
    
    fig_patt = patt_hash.get('figPatt')
    for p in fig_patt:
        match = re.search(p, fig_text)
        if match:
            return 'f' + match.group(2).replace(" ","").replace(".","").replace(",","")
    
    # [1] simplePatt
    # [2,4] space2Patt
    # [2,4,6] space3Patt
    # [2,4] fullComma2Patt
    # [2,3] comma2Patt
    # [1,2] simpleComma2Patt
    # [2,3,4] comma3Patt 
    # [1,2,3] simpleComma3Patt
    # [2,3,4,5] comma4Patt
    # [1,2,3,4] simpleComma4Patt
    # [1,2] simpleAnd2Patt
    # [1,2,3] simple_a_comma_b_patt 
    # [2,3,4] a_comma_b_patt 
    # [2,3,4,5]   a_b_and_c_patt 
    # [1,2,3,4] simple_a_b_and_c_patt
    
    matched_figs = run_simple_matcher(fig_text, patt_hash, 'simplePatt', [1])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'tableFigPatt', [3])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'comma2Patt', [2,3])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'fullComma2Patt', [2,4])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'simpleComma2Patt', [1,2])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'comma3Patt', [2,3,4])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'simpleComma3Patt', [1,2,3])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'comma4Patt', [2,3,4,5])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'simpleComma4Patt', [1,2,3,4])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'comma5Patt', [2,3,4,5,6])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'space2Patt', [2,4])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'space3Patt', [2,4,6])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'simpleAnd2Patt', [1,2])
    if( matched_figs is None ):
        matched_figs = run_simple_matcher(fig_text, patt_hash, 'and2Patt', [2,3])
    if( matched_figs is None ):
        match = re.search(patt_hash.get('simple_a_comma_b_patt'), fig_text)
        if( match ):
            f =  match.group(1)
            a = match.group(2)
            b = match.group(3)
            return 'f'+f+a+'|'+'f'+f+b
    if( matched_figs is None ):
        match = re.search(patt_hash.get('a_comma_b_patt'), fig_text)
        if( match ):
            f =  match.group(2)
            a = match.group(3)
            b = match.group(4)
            return 'f'+f+a+'|'+'f'+f+b
    if( matched_figs is None ):
        match = re.search(patt_hash.get('simple_a_and_b_patt'), fig_text)
        if( match ):
            f =  match.group(1)
            a = match.group(2)
            b = match.group(3)
            return 'f'+f+a+'|'+'f'+f+b
    if( matched_figs is None ):
        match = re.search(patt_hash.get('a_and_b_patt'), fig_text)
        if( match ):
            f =  match.group(2)
            a = match.group(3)
            b = match.group(4)
            return 'f'+f+a+'|'+'f'+f+b
    if( matched_figs is None ):
        match = re.search(patt_hash.get('a_b_and_c_patt'), fig_text)
        if( match ):
            f =  match.group(2)
            a = match.group(3)
            b = match.group(4)
            c = match.group(5)
            return 'f'+f+a+'|'+'f'+f+b+'|'+'f'+f+c
    if( matched_figs is None ):
        match = re.search(patt_hash.get('simple_a_b_and_c_patt'), fig_text)
        if( match ):
            f =  match.group(1)
            a = match.group(2)
            b = match.group(3)
            c = match.group(4)
            return 'f'+f+a+'|'+'f'+f+b+'|'+'f'+f+c
    if( matched_figs is None ):
        match = re.search(patt_hash.get('simple_a_comma_b_comma_c_patt'), fig_text)
        if( match ):
            f =  match.group(1)
            a = match.group(2)
            b = match.group(3)
            c = match.group(4)
            return 'f'+f+a+'|'+'f'+f+b+'|'+'f'+f+c
    if( matched_figs is None ):
        match = re.search(patt_hash.get('a_comma_b_comma_c_patt'), fig_text)
        if( match ):
            f =  match.group(2)
            a = match.group(3)
            b = match.group(4)
            c = match.group(5)
            return 'f'+f+a+'|'+'f'+f+b+'|'+'f'+f+c
    if( matched_figs is None ):
        match = re.search(patt_hash.get('intervalPatt'), fig_text)
        if( match ):
            fig_number =  match.group(2)
            start = match.group(3)
            end = match.group(4)
            if( len(start) > 1 or len(end)>1 ):
                return None
            matched_str = ""
            subfigs = [chr(i) for i in range(ord(start),ord(end)+1)] 
            for subfig in subfigs :
                if len(matched_str) > 0 :
                    matched_str += '|'
                matched_str += 'f' + fig_number + subfig
            return matched_str
            
    if(matched_figs is not None):
        return build_matched_string(matched_figs, 'f')
    
    matched_tab = run_simple_matcher(fig_text, patt_hash, 'tablePatt', [2])
    if(matched_tab is not None):
        return build_matched_string(matched_tab, 't')

    matched_tab = run_simple_matcher(fig_text, patt_hash, 'suppTablePatt', [3])
    if(matched_tab is not None):
        return build_matched_string(matched_tab, 'st')
    
    return None

def extract_simple_intact_data(input, title, tsv_output):
    
    with open(input, 'r') as input_file:
        xml = input_file.read()
        
    # Check if the figure legends are specified
    if "\"figure legend\"" not in xml: 
        return  
    
    soup = BeautifulSoup(xml, 'lxml')    

    intact_headings = ['pmid','i_id','primary_ref','secondary_ref','orig_fig','fig','kinetics','kinetics_conditions','type','type_xref','p1_name','p1_xref','p1_site','p2_name','p2_xref','p2_site','p3_name','p3_xref','p3_site','i_meth','p_meth']
    intact_rows = []

    patt_hash = build_figure_extraction_patterns()

    # EXPERIMENTS
    all_expt_dict = {}
    for e in soup.select('experimentlist experimentdescription'):
        ex_dict = {}
        ex_dict['i_meth'] = e.interactiondetectionmethod.names.shortlabel.text
        ex_dict['p_meth'] = e.participantidentificationmethod.names.shortlabel.text 
        all_expt_dict[e.get('id')] = ex_dict

    # INTERACTORS
    all_int_dict = {}
    for i1 in soup.select('interactorlist interactor'):
        int_dict = {}
        int_dict['name'] = i1.names.shortlabel.text
        urls = []
        for t in i1.select('primaryref[db="uniprotkb"]'):
            if( t.get('reftype') == 'identity' ) :
                urls.append(t.get('id'))
        for t in i1.select('secondaryref[db="uniprotkb"]'):
            if( t.get('reftype') == 'identity' ) :
                urls.append(t.get('id'))
        int_dict['xref'] = urls
        all_int_dict[i1.get('id')] = int_dict

    # INTERACTIONS
    for i in soup.select('interactionlist interaction'):
        int_dict = {}
        int_dict['pmid'] = title
        int_dict['i_id'] = i.get('id')
        int_dict['type'] = i.interactiontype.names.shortlabel.text        
        int_dict['type_xref'] = i.interactiontype.xref.primaryref.get('id')
        p_count = 1
        if i.primaryref is not None:
            int_dict['primary_ref'] = i.primaryref.attrs['id']
        else: 
            int_dict['primary_ref'] = '-'
        if i.secondaryref is not None:
            int_dict['secondary_ref']  = i.secondaryref.attrs['id']
        else: 
            int_dict['secondary_ref'] = '-'
        
        for p_tag in i.select('participantlist participant'):
            p_id = p_tag.interactorref.text
            p = all_int_dict[p_id]
            int_dict['p'+str(p_count)+"_name"] = p.get('name')
            int_dict['p'+str(p_count)+"_xref"] = '|'.join(p.get('xref'))
            p_count += 1
        int_dict['fig'] = '-'
        int_dict['orig_fig'] = '-'
        int_dict['kinetics'] = '-'
        int_dict['kinetics_conditions'] = '-'
        for a in i.select('attributelist attribute[name]'):
            if( a.get('name') == "figure legend" ):
                fig_text = a.text.lower()
                fig_text = run_matcher(fig_text, patt_hash)
                if( fig_text is None):
                    print(a.text.lower() + "  :  None")
                int_dict['orig_fig'] = a.text
                int_dict['fig'] = fig_text
            if( a.get('name') == "kinetics" ):
                int_dict['kinetics'] = a.text
            if( a.get('name') == "kinetics_conditions" ):
                int_dict['kinetics_conditions'] = a.text
        e_id = i.experimentlist.experimentref.text
        e = all_expt_dict.get(e_id)
        if( e is not None ):
            int_dict['i_meth'] = e.get('i_meth', '-')
            int_dict['p_meth'] = e.get('p_meth', '-')
        else: 
            int_dict['i_meth'] = '-'
            int_dict['p_meth'] = '-'
            
        r = []
        for h in intact_headings:
            r.append(int_dict.get(h,'-'))
        intact_rows.append(r)
        
    intact_df = pd.DataFrame.from_records(intact_rows, columns=intact_headings) 
    intact_df.to_csv(tsv_output, sep='\t', encoding='utf-8')

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--text_mine_file', help='input file')
    parser.add_argument('-i', '--intact_file', help='input file')
    parser.add_argument('-o', '--out', help='output file')
    args = parser.parse_args()

    text_mine_tsv = pd.read_csv(args.text_mine_file, sep=',', )
    lookup = {}
    for i,row in text_mine_tsv.iterrows():
        ebit_id = row['ebi_id']
        lookup[ebit_id]=row

    intact_tsv = tqdm(pd.read_csv(args.intact_file, sep=',', ))
    for i,row in intact_tsv.iterrows():
        ref1 = row['primary_ref']
        ref2 = row['secondary_ref']
        if lookuplookup[s]=r

