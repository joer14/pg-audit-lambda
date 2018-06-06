# Lambda PG Audit

This repo allows one to deploy a cloud formation stack with a lambda function that will automatically backup `pg_audit` logs from an AWS `rds` instance. Every 24 hours the lambda will turn on, and download all logs that have been written to in the last 24 hours, except for the most recent log. It will then compress those files, and upload them as an archive to AWS glacier. It does not download the most recently modified log, because that log file is not complete (yet), and we don't want to download and upload duplicate data.

# Getting Started
This repo uses `python2.7`.

# Resources
Before deploying you must create the following resources:
- aws s3 bucket (for storing the packaged lambda)
- rds instance
- glacier vault (in the same region as the rds instance)

# Required environment variables
| Variable | Description |
| --- | --- |
| `DATABASE_URL` | Postgres Database URI, only used by `install_pg_audit.py` utility. |
| `DB_IDENTIFIER` | The RDS identifier found by running `aws rds describe-db-instances` |
| `GLACIER_VAULT_NAME` | The name of the glacier vault you created for storing the logs. |
| `LAMBDA_BUCKET` | The name of the S3 bucket you created to be used to store the packaged lambda. |


# Reference

## Installing PG Audit
- [Docs](/docs/pg_audit_setup)

## Building
Running `./tools/build.sh` results in a `dist` folder being created, with the latest source code from the `audit` module copied over, and the necessary dependencies listed in `requirements.txt` installed.

## Deploying
Deploying is a 2 step process, packaging and deploying.

### Packaging
The `dist` folder is zipped and then it is uploaded to s3. A new `template.packaged.{timestamp}.yaml` file is created, with the `codeURI` field filled out with path to the file on s3.

### Deploying
The packaged template file is read is deployed by cloud formation to a particular stack.

## Build and Deploy
`./build_and_deploy.sh`

# Development

## Developer Setup
`pip install virtualenv`
`pip install virtualenvwrapper`
`which virtualenvwrapper.sh`
Copy that path into bash profile
`source /some/path/here/virtualenvwrapper.sh`
`mkvirtualenv pg-audit-lambda`
`workon pg-audit-lambda`
`pip install -r requirements.txt`
`pip install -r requirements-dev.txt`

## Running Locally
If you have the virtual environment configured correctly, you should be able to directly execute the audit code like so:
`python audit/core.py`

Alternatively, if you want to test the lambda handler itself using a AWS's python lambda docker image, run the following:
`./tools/build.sh && echo '{}' | sam local invoke "Audit"`


## Limitations
- Database logs for a 24 hour period cannot exceed 4GB or the upload will fail.
- Due to a [bug](https://github.com/aws/aws-sdk-net/issues/921#issuecomment-381540115) present in the aws CLI, and many AWS SDKs, we have to download the log file using the AWS REST interface directly.
- Files are being saved to memory right now - we should probably be writing to disk instead.
