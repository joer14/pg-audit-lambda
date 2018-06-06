"""
Extractor Lambda Template Generator
 - generates a SAM template for a given lambda.

# 1 - source the config file you want.
# 2 - generates the template with the filled in values.
"""

import boto3
import os
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

def get_parent_path(path):
    return os.path.abspath(os.path.join(path, os.pardir))

SCRIPT_DIR = get_parent_path(os.path.realpath(__file__))
PROJECT_DIR = get_parent_path(SCRIPT_DIR)

DB_INSTANCE_IDENTIFIER = os.getenv('DB_INSTANCE_IDENTIFIER')
GLACIER_VAULT_NAME = os.getenv('GLACIER_VAULT_NAME')

def get_rds_instance_arn():
    rds_client = boto3.client('rds')
    resp = rds_client.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER)

    instance = resp['DBInstances'][0]
    return instance['DBInstanceArn']

def get_glacier_vault_arn():
    glacier_client = boto3.client('glacier')
    resp = glacier_client.list_vaults()

    vault = next( vault for vault in resp['VaultList'] if vault['VaultName'] == GLACIER_VAULT_NAME)
    return vault['VaultARN']

def get_template():
    env = Environment(
        loader=FileSystemLoader(PROJECT_DIR)
    )
    return env.get_template('template.template.yml')

def main():
    template = get_template()

    template_filename = os.path.join(PROJECT_DIR, 'dist', 'template.yml')

    rendered = template.stream(
        DB_INSTANCE_IDENTIFIER=DB_INSTANCE_IDENTIFIER,
        DBInstanceArn=get_rds_instance_arn(),
        GLACIER_VAULT_NAME=GLACIER_VAULT_NAME,
        VaultInstanceArn=get_glacier_vault_arn()
    ).dump(template_filename)

if __name__ == "__main__":
    main()
