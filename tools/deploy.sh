#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$(dirname "$SCRIPT_DIR")

STACK_NAME='pg-audit-'$DB_INSTANCE_IDENTIFIER

# zip local artifacts that are referenced by template file in (CodeUri: dist)
# uploads them to the s3 bucket
sam package \
  --template-file $PROJECT_DIR/dist/template.yml \
  --s3-bucket $LAMBDA_BUCKET \
  --s3-prefix builds/audit \
  --output-template-file \
  $PROJECT_DIR/dist/template.packaged.yaml

# deploy
sam deploy \
  --template-file $PROJECT_DIR/dist/template.packaged.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM
