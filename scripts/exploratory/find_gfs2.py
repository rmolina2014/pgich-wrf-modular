import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
bucket = 'noaa-gfs-bdp-pds'

# Buscar en la carpeta de 2021 que sabemos que tiene pgrb2
prefix = 'gfs.20210101/00/atmos/'
response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
if 'Contents' in response:
    for obj in response['Contents']:
        name = obj['Key'].split('/')[-1]
        if 'pgrb2.0p25' in name and 'goes' not in name and not name.endswith('.idx'):
            size_mb = obj['Size'] // (1024*1024)
            print(name + ' (' + str(size_mb) + ' MB)')
