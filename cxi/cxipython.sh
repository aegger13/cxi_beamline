#! /bin/bash

# Create a clean PYTHON setup
unset PYTHONPATH
unset LD_LIBRARY_PATH

HUTCH="cxi"
SETUPDIR=`dirname "$0"`
source ${SETUPDIR}/${HUTCH}env.sh

ipython --no-banner --no-confirm-exit --profile "${HUTCH}-python" -i "$@" -c "%run -i ${SETUPDIR}/${HUTCH}load.py"

