#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$(dirname "$SCRIPT_DIR")

bash $PROJECT_DIR/tools/build.sh
bash $PROJECT_DIR/tools/deploy.sh
