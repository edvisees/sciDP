# Scientific Discourse Tagger (SciDT) 

An LSTM based sequence labeling model for analyzing the structure of scientific discourse in text. We provide a `docker` image that allows the system to be run out of the box with the minimum of configuration needed. 

## Basic Python Requirements 
* Docker (tested with v1.12.3)
* This repository
* Pretrained word embedding as a prebuilt elastic search index data directory. Please download this file (http://bmkeg.isi.edu/data/embeddings/es_index_all_data_unique.tar.gz) and unpack it in an directory on the machine where you will be running the docker image. The file will expand into a directory called `data`. 

## Running Docker

First, build the docker image:

```
  cd $SCIDT_HOME$/docker
  docker build -t scidt .
```
Then run a container based on this image. 
```
  cd $SCIDT_HOME$
  ./start_docker.sh 8888 8787 /path/to/documents /path/to/elasticsearch/data
```
This will then load a docker command prompt with all available functionality. 

# Basic SciDT Function (preserved from original edvisees/sciDT version)

We include these instructions from the original version of SciDT (developed by Pradeep Dasigi under Ed Hovy at CMU)

## Basic Python Requirements 
* Theano (tested with v0.8.0)
* Keras (tested with v0.3.2)
* Pretrained word embedding (recommended: http://bio.nlplab.org/#word-vectors): SciDP expects a gzipped embedding file with each line containing word and a the vector (list of floats) separated by spaces

## An Elastic Search Index for Word Embeddings. 

Note, due to the memory requirements imposed by loading word embeddings into memory. We provide additional functionality where the embeddings may be read from a local elastic search index. A gzipped tar file of the embeddings used can be downloaded from here   




## Training
```
python nn_passage_tagger.py REPFILE --train_file TRAINFILE --use_attention
```
where `REPFILE` is the embedding file. `--use_attention` is recommended. Check out the help messages for `nn_passage_tagger.py` for more options

### Trained model
After you train successfully, three new files appear in the directory, with file names containing chosen values for `att`, `cont` and `bi`:
* `model_att=*_cont=*_bi=*_config.json`: The model description
* `model_att=*_cont=*_bi=*_label_ind.json`: The label index
* `model_att=*_cont=*_bi=*_weights`: Learned model weights

## Testing
You can specify test files while training itself using `--test_files` arguments. Alternatively, you can do it after training is done. In the latter case, `nn_passage_tagger` assumes the trained model files described above are present in the directory.
```
python nn_passage_tagger.py REPFILE --test_files TESTFILE1 [TESTFILE2 ..] --use_attention
```
Make sure you use the same options for attention, context and bidirectional as you used for training.
