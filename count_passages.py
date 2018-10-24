import warnings
import sys
import codecs
import numpy
import argparse
import json
import pandas as pd
import itertools

from util import read_passages

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Count ")
    argparser.add_argument('--train_file', type=str, help="Training file. One clause<tab>label per line and passages separated by blank lines.")
    argparser.add_argument('--test_files', metavar="TESTFILE", type=str, nargs='+', help="Test file name(s), separated by space. One clause per line and passages separated by blank lines.")
    args = argparser.parse_args()

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
        clauses = codecs.open(trainfile, "r", "utf-8")
        str_seqs, label_seqs = read_passages(clauses, is_labeled = True)
        p_count += len(str_seqs)
        c_count += len(list(itertools.chain(*label_seqs)))
    if( test ) :
        for testfile in testfiles:
            clauses = codecs.open(testfile, "r", "utf-8")
            str_seqs, label_seqs = read_passages(clauses, is_labeled = True)
            p_count += len(str_seqs)
            c_count += len(list(itertools.chain(*label_seqs)))

    print("Paragraph Count: %d" % p_count)
    print("Clause Count: %d" % c_count)

    