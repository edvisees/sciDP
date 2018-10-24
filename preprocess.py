import os
from nltk.parse import stanford
import sys
import codecs
from nltk.tokenize import word_tokenize, sent_tokenize
import re

def get_longest_cand(cands):
  maxlen = 0
  bestcand = ''
  for cand in cands:
    if len(cand) > maxlen:
      maxlen = len(cand)
      bestcand = cand
  return bestcand

def extract_sat_clause(tree, is_root = True):
  if len(tree) == 0 or type(tree) == unicode:
    return ""
  elif tree.label() == 'S' or tree.label() == 'SBAR':
    if is_root:
      return get_longest_cand([extract_sat_clause(t, is_root = False) for t in tree])
    else:
      phrase = " ".join(tree.leaves())
      return phrase.replace("-LRB-", "(").replace("-RRB-", ")").replace("-LSB-", "[").replace("-RSB-", "]")
  else:
    return get_longest_cand([extract_sat_clause(t, is_root) for t in tree])


def separate_clauses(lines, parser_path, model_path):

#  os.environ['STANFORD_PARSER'] = "/usr1/shared/tools/stanford-parser-full-2015-04-20"
#  os.environ['STANFORD_MODELS'] = "/usr1/shared/tools/stanford-parser-full-2015-04-20"

  os.environ['STANFORD_PARSER'] = parser_path
  os.environ['STANFORD_MODELS'] = model_path
  parser = stanford.StanfordParser()
  parse_iters = parser.parse_sents(lines)

  clauses = []
  #print "Got: ", lines
  for words, parse_iter in zip(lines, parse_iters):
    sent = " ".join(words)
    sat_clause = extract_sat_clause(parse_iter.next())
    #print >>sys.stderr, "Looking for %s in %s"%(sat_clause, sent)
    ind = sent.index(sat_clause)
    sat_len = len(sat_clause)
    if ind == 0:
      main_clause = sent[sat_len:]
      clause_set = (sat_clause, main_clause)
    else:
      main_clause = sent[:ind]
      if ind + sat_len != len(sent):
        # There is a remainder at the end
        remainder = sent[ind + sat_len :]
        if remainder.strip() == ".":
          sat_clause = sat_clause + " ."
          clause_set = (main_clause, sat_clause)
        else:
          clause_set = (main_clause, sat_clause, remainder)
      else:
        clause_set = (main_clause, sat_clause) 
    #clause_set = (sat_clause, sent[sat_len:]) if ind == 0 else (sent[:ind], sat_clause)
    clauses.append(clause_set)
  return clauses

def tokenize_sentences(phrase):
  phrase_sents = sent_tokenize(phrase)
  fixed_phrase_sents = [phrase_sents[0]]
  i = 1
  while i < len(phrase_sents):
    if (phrase_sents[i-1].endswith("Fig.") or phrase_sents[i-1].endswith("et al.") ) and re.match("[0-9a-z]", phrase_sents[i][0]) is not None:
      fixed_phrase_sents[-1] += " "+phrase_sents[i]
    else:
      fixed_phrase_sents.append(phrase_sents[i])
    i += 1
  return fixed_phrase_sents

def extract_result_section(lines):
  in_results = False
  sents_to_process = []
  for sent in lines:
    sent_parts = sent.split()
    if sent[0].isupper() and len(sent_parts) <= 3:
      # We are probably looking at a section header
      if in_results:
        break
      elif sent_parts[0].lower() == "results":
        in_results = True
    elif in_results:
      sents_to_process.append(sent)
  return sents_to_process

def write_clauses(filename, outfilename, train=True, results_only=True):
  outfile = codecs.open(outfilename, "w", "utf-8")
  inlines = codecs.open(filename, "r", "utf-8")
  lines_to_process = extract_result_section(inlines) if results_only else inlines
  for line in lines_to_process:
    if train:
      label, phrase = line.strip().split('\t')
    else:
      phrase = line.strip()
    phrase_sents = tokenize_sentences(phrase)
    for phrase_sent in phrase_sents:
      sent_words = word_tokenize(phrase_sent)
      clause_set = separate_clauses([sent_words])
      for clauses in clause_set:
        for clause in clauses:
          clause = clause.strip()
          if clause != "":
            if train:
              print >>outfile, "%s\t%s"%(label, clause)
            else:
              print >>outfile, clause
