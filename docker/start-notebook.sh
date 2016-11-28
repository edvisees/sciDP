#!/bin/bash
cd /tmp/scidt/
exec screen -dmS ipython jupyter notebook --ip='*' --port 8888 --no-browser
