#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$(dirname "$SCRIPT_DIR")

# if LAMBDA_BUCKET isnt set default to lambda.agilemd.com
if [ -z ${LAMBDA_BUCKET+x} ];
  then LAMBDA_BUCKET='lambda.agilemd.com';
fi

GIT_HASH=$(git --git-dir $PROJECT_DIR/.git rev-parse HEAD)
GIT_HASH_SHORT="${GIT_HASH:0:7}"
S3_PREFIX='audit/'$DB_INSTANCE_IDENTIFIER'/'$GIT_HASH_SHORT
STACK_NAME='pg-audit-'$DB_INSTANCE_IDENTIFIER

# Parse profile option
if [ $1 == '--profile' ]
  then
    AWS_PROFILE=$2
elif [ -z "$1" ]
  then
    AWS_PROFILE='default'
else
  echo "[extractors] - Error: Invalid option: $1"
  exit 1
fi
echo "[extractors] - Using AWS Profile: $AWS_PROFILE"

# zip local artifacts that are referenced by template file in (CodeUri: dist)
# uploads them to the s3 bucket
sam package \
  --template-file $PROJECT_DIR/dist/template.yml \
  --s3-prefix $S3_PREFIX \
  --s3-bucket $LAMBDA_BUCKET \
  --output-template-file \
  $PROJECT_DIR/dist/template.packaged.yaml \
  --profile $AWS_PROFILE

# deploy
sam deploy \
  --template-file $PROJECT_DIR/dist/template.packaged.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --profile $AWS_PROFILE
