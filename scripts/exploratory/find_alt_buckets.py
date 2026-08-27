import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

# Try alternative buckets that might have standard GFS pgrb2
buckets = [
    'noaa-gfs-bdp-pds',
    'nws-gfs-pds',
    'noaa-gfs-gefsv13-pds',
    'noaa-reanalyses-pds',
    'noaa-ncep-gfs-awc-pds',
]

for bucket in buckets:
    try:
        # Search for pgrb2.0p25 files for 20260702
        prefix = 'gfs.20260702/12/atmos/'
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=10)
        count = resp.get('KeyCount', 0)
        if count > 0:
            print(f"{bucket}: {count} objects under {prefix}")
            for obj in resp.get('Contents', [])[:5]:
                print(f"  {obj['Key'].split('/')[-1]} ({obj['Size']//1024} KB)")
        else:
            # Try root level
            resp2 = s3.list_objects_v2(Bucket=bucket, Prefix='gfs.20260702', MaxKeys=5)
            count2 = resp2.get('KeyCount', 0)
            if count2 > 0:
                print(f"{bucket}: {count2} objects under gfs.20260702")
                for obj in resp2.get('Contents', [])[:5]:
                    print(f"  {obj['Key']}")
            else:
                print(f"{bucket}: no objects found")
    except Exception as e:
        print(f"{bucket}: {str(e)[:80]}")
