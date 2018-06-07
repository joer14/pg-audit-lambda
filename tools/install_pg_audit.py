"""
Setup PG Audit on RDS


- Uses session based logging
- Logs all actions
- Logs the parameters used in the query
- Key assumption: you are using the default parameter group.

"""

import boto3
import click
import os
import psycopg2
import time

from botocore.exceptions import ClientError

DB_INSTANCE_IDENTIFIER = os.getenv('DB_INSTANCE_IDENTIFIER')
DATABASE_URL = os.getenv('DATABASE_URL')

rds_client = boto3.client('rds')

def copy_parameter_group():
    click.echo('Copying Parameter Group')
    # get the parameter group we want
    resp = rds_client.describe_db_instances(
        DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER
    )
    src_group_name = ''
    for instance in resp['DBInstances']:
        if len(instance['DBParameterGroups']) > 1:
            raise ValueError('More than one DBParameterGroup, dont know which to copy')
        # src_group_name
        src_group_name = instance['DBParameterGroups'][0]['DBParameterGroupName']
        # print instance['DBParameterGroups'][0]

    new_group_name = src_group_name+'-pgaudit'

    # the following should work, but the default identifier for the group includes periods
    # which aren't valid, and client enforces this convention, so we can't specify it as a source.
    try:
        resp = rds_client.copy_db_parameter_group(
            SourceDBParameterGroupIdentifier=src_group_name,
            TargetDBParameterGroupIdentifier=new_group_name,
            TargetDBParameterGroupDescription=src_group_name + ' with pg_audit installed.',
            Tags=[]
        )
        return new_group_name
    except ClientError:
        # manually create a new one based on the existing parameter group family
        new_group_name = new_group_name.replace('.','-')
        # get parameter group family
        resp = rds_client.describe_db_parameter_groups(
            DBParameterGroupName=src_group_name
        )
        src_group_family = resp['DBParameterGroups'][0]['DBParameterGroupFamily']
        #
        resp = rds_client.create_db_parameter_group(
            DBParameterGroupName=new_group_name,
            DBParameterGroupFamily=src_group_family,
            Description=new_group_name
        )
        click.echo('Created new parameter group from DBParameterGroupFamily')
        return new_group_name

def modify_group_initial(group_name):
    click.echo('Modifying parameter group with initial settings')

    response = rds_client.modify_db_parameter_group(
        DBParameterGroupName=group_name,
        Parameters=[
            {
                'ParameterName': 'shared_preload_libraries',
                'ParameterValue': 'pgaudit',
                'ApplyMethod': 'pending-reboot',
            },
        ]
    )

def set_pgaudit_log_parameter(group_name):
    response = rds_client.modify_db_parameter_group(
        DBParameterGroupName=group_name,
        Parameters=[
            {
                'ParameterName': 'pgaudit.log',
                'ParameterValue': 'all',
                'ApplyMethod': 'pending-reboot',
            },
            {
                'ParameterName': 'pgaudit.log_parameter',
                'ParameterValue': 'on',
                'ApplyMethod': 'pending-reboot',
            },
            {
                'ParameterName': 'pgaudit.log_relation',
                'ParameterValue': 'on',
                'ApplyMethod': 'pending-reboot',
            },
            {
                'ParameterName': 'pgaudit.log_catalog',
                'ParameterValue': 'off',
                'ApplyMethod': 'pending-reboot',
            },
        ]
    )

def reboot_instance():
    def wait_for_reboot():
        click.echo('Rebooting Instance')
        current_status = ''
        while current_status != 'available':
            resp = rds_client.describe_db_instances(
                DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER
            )
            current_status = resp['DBInstances'][0]['DBInstanceStatus']
            click.echo('\tcurrent status: %s' % current_status)
            time.sleep(5)

    rds_client.reboot_db_instance(
        DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER
    )

    wait_for_reboot()

def set_parameter_group(group_name):
    click.echo('Setting new parameter group')

    response = rds_client.modify_db_instance(
        DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER,
        DBParameterGroupName=group_name,
    )
    time.sleep(5)
    reboot_instance()

def pg_group_applied_successfully(group_name):
    resp = rds_client.describe_db_instances(
        DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER
    )

    instance = resp['DBInstances'][0]
    return instance['DBParameterGroups'][0]['ParameterApplyStatus'] != 'pending-reboot'

def verify_pgaudit_initialized(cursor):
    click.echo('Verifying PG Audit Initialized')
    cursor.execute('show shared_preload_libraries;')
    results = cursor.fetchall()
    return any(res[0] == 'rdsutils,pgaudit' for res in results)

def create_extension(cursor):
    click.echo('Creating PG Audit Extension')
    cursor.execute('DROP EXTENSION IF EXISTS pgaudit;')
    cursor.execute('CREATE EXTENSION pgaudit;')
    click.echo('Created PG Audit extension')


def verify_pg_audit_role(cursor):
    cursor.execute('show pgaudit.role;')
    results = cursor.fetchall()
    return any(res[0] == 'rds_pgaudit' for res in results)

def main():
    new_group_name = copy_parameter_group()
    modify_group_initial(new_group_name)
    set_parameter_group(new_group_name)

    if not pg_group_applied_successfully(new_group_name):
        reboot_instance()
        if not pg_group_applied_successfully(new_group_name):
            raise RuntimeError('New parameter group is not set.')

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    if not verify_pgaudit_initialized(cur):
        click.echo('Verifing pg audit initialized failed, trying again.')
        reboot_instance()
        if not verify_pgaudit_initialized(cur):
            raise RuntimeError('PG Audit shared_preload_libraries verification failed')

    create_extension(cur)
    set_pgaudit_log_parameter(new_group_name)
    if not pg_group_applied_successfully(new_group_name):
        reboot_instance()
        if not pg_group_applied_successfully(new_group_name):
            raise RuntimeError('New parameter group is not set.')
    click.echo('PG Audit Session Logging Installed. Now you should verify this by manually querying the database and checking the logs.')


if __name__ == "__main__":
    main()
