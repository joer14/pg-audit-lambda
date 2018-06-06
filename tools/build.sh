#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$(dirname "$SCRIPT_DIR")

# setup dist folder
rm -rf $PROJECT_DIR/dist
mkdir -p $PROJECT_DIR/dist/

# copy src into dist
cp -r $PROJECT_DIR/audit/* $PROJECT_DIR/dist/

# install dependencies
pip install -r $PROJECT_DIR/requirements.txt -t $PROJECT_DIR/dist/

# build template
python $PROJECT_DIR/tools/generate_template.py
