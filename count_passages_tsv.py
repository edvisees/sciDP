import codecs
import argparse
import itertools
import os
import pandas as pd

from util import read_passages_from_tsv, read_clauses_from_tsv_directory

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Count ")
    argparser.add_argument('--train_file', type=str, help="Training file. One clause<tab>label per line and passages separated by blank lines.")
    argparser.add_argument('--test_files', metavar="TESTFILE", type=str, help="Test file name(s), separated by space. One clause per line and passages separated by blank lines.")
    argparser.add_argument('--sec', type=str, help="w = whole, r=results, m=exclude methods.")
    args = argparser.parse_args()

    if args.sec:
        sec = args.sec
    else:
        sec = 'w'

    if args.train_file:
        trainfile = args.train_file
        train = True
    else:
        train = False

    if args.test_files:
        testfiles = args.test_files
        test = True
    else:
        test = False

    p_count = 0
    c_count = 0
    if( train ) :
        
        clauses = read_clauses_from_tsv_directory(trainfile)
        str_seqs, label_seqs = read_passages_from_tsv(clauses, sec)
        p_count += len(str_seqs)
        c_count += len(list(itertools.chain(*label_seqs)))

    if( test ) :
    
        clauses = read_clauses_from_tsv_directory(testfiles)
        str_seqs, label_seqs = read_passages_from_tsv(clauses,sec=sec)
        p_count += len(str_seqs)
        c_count += len(list(itertools.chain(*label_seqs)))

    print("Paragraph Count: %d" % p_count)
    print("Clause Count: %d" % c_count)

    