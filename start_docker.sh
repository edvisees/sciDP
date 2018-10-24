#!/bin/bash
if [[ $# -ne 4 ]] ; then
  echo "Run this from within the data directory you are analyzing"
  echo "USAGE ./run_docker.sh <ES_DATA> <SCIDT_FOLDER>"
  exit
fi

ES_DATA=$1
SCIDT=$2

#  -v option mounts the place where this command was run from as /tmp/evidence_extractor
docker run -i -t --user $(id -u):$(id -g): -v $SCIDT:/tmp/scidt/ -v $PWD:/tmp/data -v $ES_DATA:/tmp/es_data -w=/tmp/scidt/ --rm scidt
