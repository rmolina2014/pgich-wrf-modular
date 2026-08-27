import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
bucket = 'noaa-gfs-bdp-pds'

for fecha in ['20260525', '20260524', '20260523', '20260522']:
    for hora in ['12', '00']:
        prefix = 'gfs.' + fecha + '/' + hora + '/atmos/'
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
        if 'Contents' in response:
            pgrb2_files = [obj for obj in response['Contents']
                          if 'pgrb2.0p25' in obj['Key']
                          and 'goes' not in obj['Key']
                          and not obj['Key'].endswith('.idx')]
            if pgrb2_files:
                print(fecha + ' ' + hora + 'Z: ' + str(len(pgrb2_files)) + ' archivos pgrb2 estandar')
                for f in pgrb2_files[:5]:
                    name = f['Key'].split('/')[-1]
                    size_mb = f['Size'] // (1024*1024)
                    print('  ' + name + ' (' + str(size_mb) + ' MB)')
