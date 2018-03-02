#!/bin/bash
if [[ $# -ne 4 ]] ; then
  echo "Run this from wihin the data directory you are analyzing"
  echo "USAGE ./run_docker.sh <JUPYTER_PORT> <SCIDT_PORT> <ES_DATA> <SCIDT_FOLDER>"
  exit
fi

JPORT=$1
SPORT=$2
ES_DATA=$3
SCIDT=$4

#  -v option mounts the place where this command was run from as /tmp/evidence_extractor
docker run -i -t -v $SCIDT:/tmp/scidt/ -v $PWD:/tmp/data -v $ES_DATA:/tmp/es_data -w=/tmp/scidt/ --rm -p ${JPORT}:8888 -p ${SPORT}:8787 scidt
