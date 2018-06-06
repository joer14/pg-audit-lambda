"""
Audit Lambda Handler

It will look for all log files for a given RDS instance, that have been updated in the last n minutes, compresses them and uploads them to glacier.

"""
import arrow
import boto3
import os
import StringIO
import tarfile

from rds_download_log import get_log_file_via_rest

DB_INSTANCE_IDENTIFIER = os.getenv('DB_INSTANCE_IDENTIFIER')
GLACIER_VAULT_NAME = os.getenv('GLACIER_VAULT_NAME')

FAKE_DOWNLOAD = False
WRITE_TO_LOCAL = False

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
    if FAKE_DOWNLOAD:
        return filename + 'some fake content here \n'* 10

    return get_log_file_via_rest(filename)

def make_tar(files):
    """ given a list of (filename, filecontents), return a tar) """
    output_buffer = StringIO.StringIO()
    tar = tarfile.open(fileobj=output_buffer, mode="w:gz")
    for filename, file_contents in files:
        file = StringIO.StringIO()
        file.write(file_contents)
        file.seek(0)
        info = tar.tarinfo(name=filename)
        info.size=len(file.buf)
        tar.addfile(tarinfo=info, fileobj=file)
    tar.close()
    return output_buffer

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


def write_archive_to_local_file(filename, archive):
    """ Useful when debugging """
    target_file = open(filename, 'w')
    target_file.write(archive)
    target_file.close()
    return

def main():
    '''This function will always replace any existing files that exist that have the same names,
    but this is okay since we only upload files that have changed.
    '''
    rds_client = boto3.client('rds')

    filenames = list_files(rds_client)
    files = []

    for filename in filenames:
        file_contents = download(rds_client, filename)
        files.append((filename, file_contents))

    archive = make_tar(files)
    archive_timestamp = arrow.utcnow().format('YYYY-MM-DD__HH-mm-ss__UTC')
    archive_name = "{0}/{1}.tar".format(DB_INSTANCE_IDENTIFIER, archive_timestamp)

    print 'Archive has: %s files' % len(filenames)
    print 'Archive size: %s Kb' % str(float(len(archive)) * 0.001)

    if WRITE_TO_LOCAL:
        write_archive_to_local_file(archive_name, archive)
    upload(archive_name, archive)
    print 'Successfully uploaded archive: %s' % archive_name


def lambda_handler(event, context):
    main()

if __name__ == "__main__":
    main()
