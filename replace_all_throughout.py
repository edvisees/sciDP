import pandas as pd
import os
import argparse

def replace_all_throughout(dir, suffix, lookup):

    for fn in os.listdir(dir):
        infilepath = dir + "/" + fn
        
        if os.path.isfile(infilepath) and infilepath[-len(suffix):]==suffix:        
            with open(infilepath) as f:
                old_lines = f.readlines()
            new_lines = []
            for l in old_lines:
                nl = l
                for s in lookup:
                    nl = nl.replace(s, lookup[s])
                new_lines.append(nl)
            os.remove(infilepath)
            f = open(infilepath, 'w')
            for l in new_lines:
                f.write(l)
            f.close()
        elif os.path.isdir(infilepath) :        
            replace_all_throughout(infilepath, suffix, lookup)

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inDir', help='Directory for input files')
    parser.add_argument('-m', '--mappings', help='Mappings file')
    parser.add_argument('-s', '--suffix', help='File suffix')
    args = parser.parse_args()
  
    tsv = pd.read_csv(args.mappings, sep='\t', )
    lookup = {}
    for i,row in tsv.iterrows():
        s = row['s']
        r = row['r']
        lookup[s]=r

    replace_all_throughout(args.inDir, args.suffix, lookup)