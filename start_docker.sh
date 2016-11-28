#!/bin/bash
if [[ $# -ne 4 ]] ; then
  echo "USAGE ./run_docker.sh <JUPYTER_PORT> <SCIDT_PORT> <DATA_FOLDER> <ES_DATA>"
  exit
fi

JPORT=$1
SPORT=$2
DATA=$3
ES_DATA=$4

#  -v option mounts the place where this command was run from as /tmp/evidence_extractor
docker run -i -t -v $PWD:/tmp/scidt/ -v $DATA:/tmp/data -v $ES_DATA:/tmp/es_data -w=/tmp/scidt/ --rm -p ${JPORT}:8888 -p ${SPORT}:8787 scidt
