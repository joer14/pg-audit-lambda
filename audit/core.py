"""
Audit Lambda Handler

It will look for all log files for a given RDS instance, that have been updated in the last n minutes, compresses them and uploads them to glacier.

"""
import arrow
import boto3
import os
import shutil
import StringIO
import tarfile
import tempfile

from rds_download_log import get_log_file_contents_via_rest

DB_INSTANCE_IDENTIFIER = os.getenv('DB_INSTANCE_IDENTIFIER')
GLACIER_VAULT_NAME = os.getenv('GLACIER_VAULT_NAME')

PERSIST_TO_DISC_AFTER = False

TEMP_DIR = tempfile.mktemp()

def get_parent_path(path):
    return os.path.abspath(os.path.join(path, os.pardir))

def list_files(rds_client):
    # files last modified before this time will not be listed.
    threshold_timestamp = 1000 * arrow.now().shift(hours=-24).timestamp
    response = rds_client.describe_db_log_files(
        DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER,
        FileLastWritten=threshold_timestamp,
    )

    logs_to_download = response['DescribeDBLogFiles']
    # remove the most recently written log from the list; its not being done written.
    logs_to_download.remove(max(logs_to_download, key=lambda x: x['LastWritten']))
    # remove the the 'error/postgres.log' log if it exists - this is the bootup log and not necessary.
    try:
        logs_to_download.remove(next(log for log in logs_to_download if log['LogFileName'] == 'error/postgres.log'))
    except StopIteration:
        pass

    return [ f['LogFileName'] for f in logs_to_download ]

def download(rds_client, filename):
    '''downloads file and loads it into memory'''
    tmp_file = open(filename, 'w+')
    contents = get_log_file_contents_via_rest(filename)
    tmp_file.write(contents)
    return tmp_file

def make_tar(files, archive_name):
    """ given a list of (filename, filecontents), return a tar) """
    delete_after = not PERSIST_TO_DISC_AFTER
    tmp_file = open(archive_name, 'w+')
    tar = tarfile.open(fileobj=tmp_file, mode="w:gz")
    for filename, file in files:
        file.seek(0)
        info = tar.gettarinfo(fileobj=file, arcname=os.path.basename(filename))
        tar.addfile(tarinfo=info, fileobj=file)
    tar.close()

    if PERSIST_TO_DISC_AFTER:
        print tmp_file.name
    return tmp_file

def upload(filepath, archive_file):
    glacier_client = boto3.client('glacier')

    # 4GB max file size
    response = glacier_client.upload_archive(
        archiveDescription=filepath,
        body=archive_file.getvalue(),
        vaultName=GLACIER_VAULT_NAME,
    )
    if 'archiveId' not in response:
        raise Exception('failed to upload filepath: %s' % filepath)

def make_dirs_for_path(path):
    parent = get_parent_path(path)
    if not os.path.exists(parent):
        os.makedirs(parent)
        make_dirs_for_path(parent)
    return

def main():
    '''This function will always replace any existing files that exist that have the same names,
    but this is okay since we only upload files that have changed.
    '''
    rds_client = boto3.client('rds')

    filenames = list_files(rds_client)
    files = []

    for filename in filenames:
        filename = TEMP_DIR + '/' + filename
        make_dirs_for_path(filename)
        file = download(rds_client, filename)
        files.append((filename, file))

    archive_timestamp = arrow.utcnow().format('YYYY-MM-DD__HH-mm-ss__UTC')
    archive_base_name = "{0}-{1}.tar".format(DB_INSTANCE_IDENTIFIER, archive_timestamp)
    archive_name = os.path.join(TEMP_DIR, archive_base_name)
    make_dirs_for_path(archive_name)
    archive = make_tar(files, archive_name)

    print 'Archive Created'
    print 'Archive has: %s files' % len(filenames)

    upload(archive_name, archive)
    print 'Successfully uploaded archive: %s' % archive_name
    print 'Deleting temporary directory'
    shutil.rmtree(TEMP_DIR)


def lambda_handler(event, context):
    main()

if __name__ == "__main__":
    main()
