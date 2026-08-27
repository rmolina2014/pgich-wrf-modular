import urllib.request
import ssl
import struct

ctx = ssl.create_default_context()

# Try with explicit variable filter
url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t12z.pgrb2.0p25.f000&var_TMP=on&subregion=&leftlon=-70&rightlon=-66&toplat=-30&bottomlat=-33&dir=%2Fgfs.20260705%2F12%2Fatmos"

print("Testing with var_TMP filter...")
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=60, context=ctx)
data = resp.read()

# Save full file
with open("gfs_data/test_nomads_filtered.grib2", "wb") as f:
    f.write(data)

print(f"Downloaded {len(data)} bytes")
print(f"Header: {data[:4]}")

# Read GRIB messages
with open("gfs_data/test_nomads_filtered.grib2", "rb") as f:
    count = 0
    while count < 10:
        while True:
            pos = f.tell()
            byte = f.read(1)
            if not byte:
                break
            if byte == b'G':
                check = f.read(3)
                if check == b'RIB':
                    break
        else:
            break
        
        header = f.read(12)
        if len(header) < 12:
            break
        discipline = header[3]
        total_length = struct.unpack('>Q', header[4:12])[0]
        
        # Read PDS to get parameter info
        sec0 = f.read(21)
        centre = struct.unpack('>H', sec0[0:2])[0]
        sec1_size_bytes = f.read(4)
        sec1_size = struct.unpack('>I', sec1_size_bytes)[0]
        sec1_data = f.read(sec1_size - 4)
        
        param_cat = sec1_data[0] if len(sec1_data) > 0 else -1
        param_num = sec1_data[1] if len(sec1_data) > 1 else -1
        
        # Print first 30 bytes of sec1 for analysis
        sec1_hex = ' '.join(f'{b:02x}' for b in sec1_data[:30])
        
        print(f"  msg {count+1}: disc={discipline} cat={param_cat} num={param_num} len={total_length}")
        print(f"    PDS hex: {sec1_hex}")
        
        count += 1
        f.seek(pos + total_length)
