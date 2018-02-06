import warnings
import sys
import codecs
import numpy
import argparse
import json
import re
import pandas as pd
import itertools

import matplotlib.pyplot as plt
import numpy as np

from util import read_clauses_from_tsv_directory
from numpy import matrix

from bokeh.models import LabelSet
from bokeh.charts import HeatMap, save, output_file
from bokeh.charts.attributes import ColorAttr
from bokeh.palettes import Greys6,gray
from bokeh.models import ColorMapper, Ticker, ColorBar

def prepare_and_draw_matrix(dh_mat2, heading_list, disc_list, outfile):
    
    totals = {}
    for d in disc_list:
        total = 0
        for h in heading_list:
            if( dh_mat2[h].get(d, None) is not None):
                total += dh_mat2[h][d]
        totals[d] = total 
    
    section = []
    d_type = []
    percent = []
    for d in disc_list:
        for h in heading_list:
            if( dh_mat2[h].get(d, None) is None):
                section.append(h)
                d_type.append(d)
                percent.append(0.0)
            else : 
                section.append(h)
                d_type.append(d)
                percent.append(100.0 * dh_mat2[h][d] / totals[d])
        
    data = {'Section': section,
            'Discourse Type': d_type,
             'Percentage': percent
            }
    
    color = ColorAttr(bin=True, palette=gray(6), sort=True, ascending=False)

    hm = HeatMap(data, x='Discourse Type', y='Section', values='Percentage',
                stat=None, plot_height=260, legend=False, color=color)
    
    output_file(outfile+'1.html', mode='cdn', root_dir=None)
    save(hm)

    hm1 = HeatMap(data, x='Discourse Type', y='Section', values='Percentage',
                stat=None, plot_height=260, legend=True, color=color)
    
    output_file(outfile+'2.html', mode='cdn', root_dir=None)
    save(hm1)

     
    '''
    rows = []
    for h in heading_list:
        row = []
        for d in disc_list:
            if( dh_mat2[h].get(d, None) is None):
                row.append(0.0)
            else : 
                row.append(100.0 * dh_mat2[h][d] / totals[h])
        rows.append(row)
    
    column_labels = disc_list
    row_labels = heading_list
    data2 = np.array(rows)
    fig, axis = plt.subplots() 
    heatmap = axis.pcolor(data2) 

    axis.set_yticks(np.arange(data2.shape[0])+0.5, minor=False)
    axis.set_xticks(np.arange(data2.shape[1])+0.5, minor=False)

    axis.invert_yaxis()

    axis.set_yticklabels(row_labels, minor=False)
    axis.set_xticklabels(column_labels, minor=False)

    fig.set_size_inches(11.03, 3.5)
    plt.colorbar(heatmap)

    plt.savefig(outfile + ".png", dpi=100)
    '''
    
    
    
    
    

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Count ")
    argparser.add_argument('--tsv', type=str, help="Directory with input files.")
    argparser.add_argument('--out', type=str, help="Output file.")
    args = argparser.parse_args()

    citation_pattern = re.compile('exLink')
    dh_mat1 = {}
    disc = {}
    total_count = 0
    total_count2 = 0
    clauses = read_clauses_from_tsv_directory(args.tsv)
    for row in clauses:
        d = row['Discourse Type'].strip()
        h = row['Headings']
        f = row['FloatingBox?']
        c = row['Codes']
        file = row['file']
        
        if( h != h ) :
            h = "-"

        #if( re.search(citation_pattern,c) ) :
        #    d += '+cite'

        disc[d] = 0
        
        if(f == 'TRUE'):
            continue
                       
        if( dh_mat1.get(d, None) is None):
            dh_mat1[d] = {};
        if( dh_mat1[d].get(h, None) is None ):
            dh_mat1[d][h] = 0
        dh_mat1[d][h] += 1
        total_count += 1
       
    disc_list = sorted(disc.keys()) 
        
    method_patt = re.compile('(method|procedure)')
    intro_patt = re.compile('(^-$|introduc|background|significance)')
    results_patt = re.compile('result')
    discussion_patt = re.compile('(discussion|conclusion|highlight)')

    dh_mat2 = {}
    dh_mat2['meth'] = {}
    dh_mat2['res'] = {}
    dh_mat2['intro'] = {}
    dh_mat2['disc'] = {}
            
    for d in dh_mat1.keys():
        for h in dh_mat1[d]:
            i = dh_mat1[d][h]

            hh = str(h).lower()
            if re.search(results_patt, hh) :
                if dh_mat2['res'].get(d, None) is None:
                    dh_mat2['res'][d] = 0
                dh_mat2['res'][d] += i
                total_count2 += i
            elif re.search(method_patt, hh) :
                if dh_mat2['meth'].get(d, None) is None:
                    dh_mat2['meth'][d] = 0
                dh_mat2['meth'][d] += i
                total_count2 += i
            elif re.search(intro_patt, hh) :
                if dh_mat2['intro'].get(d, None) is None:
                    dh_mat2['intro'][d] = 0
                dh_mat2['intro'][d] += i
                total_count2 += i
            elif re.search(discussion_patt, hh) :
                if dh_mat2['disc'].get(d, None) is None:
                    dh_mat2['disc'][d] = 0
                dh_mat2['disc'][d] += i
                total_count2 += i
    
    print('TOTAL: %d' % total_count)
    print('SUBTOTAL: %d' % total_count2)
    
    d_string = '                    '
    for d in disc_list:
        d_string += ("%12s " % d[:12])
    print d_string
    
    for h in dh_mat2.keys():
        row = ('%20s' % h)
        for d in disc_list:
            if( dh_mat2[h].get(d, None) is None):
                row += ("%12.1f " % 0.0)
            else : 
                row += ("%12.1f " % (100.0 * dh_mat2[h][d] / total_count2))
        print row 
    
    prepare_and_draw_matrix(dh_mat2, dh_mat2.keys(), disc_list, args.out)