#!/usr/bin/env python3
"""Read GRIB2 message headers - simplified version"""
import struct

def read_grib2_messages(filepath, max_messages=50):
    with open(filepath, 'rb') as f:
        count = 0
        while count < max_messages:
            while True:
                pos = f.tell()
                byte = f.read(1)
                if not byte:
                    return
                if byte == b'G':
                    check = f.read(3)
                    if check == b'RIB':
                        break
            
            header = f.read(12)
            if len(header) < 12:
                return
            
            discipline = header[3]
            total_length = struct.unpack('>Q', header[4:12])[0]
            
            sec0 = f.read(21)
            if len(sec0) < 21:
                return
            centre = struct.unpack('>H', sec0[0:2])[0]
            
            sec1_size_bytes = f.read(4)
            sec1_size = struct.unpack('>I', sec1_size_bytes)[0]
            
            sec1_data = f.read(sec1_size - 4)
            param_category = sec1_data[0] if len(sec1_data) > 0 else -1
            param_number = sec1_data[1] if len(sec1_data) > 1 else -1
            
            # Parameter names for discipline=0
            disc0_names = {
                (0, 0): "TMP", (0, 1): "SPFH", (0, 2): "RH",
                (0, 3): "HGT", (0, 5): "PRES", (0, 6): "UGRD",
                (0, 7): "VGRD", (0, 8): "STRM", (0, 10): "VVEL",
                (0, 19): "TMP_surface", (0, 34): "REFC",
                (2, 3): "HLCY", (1, 8): "PRATE", (2, 0): "HGT",
                (2, 2): "UGRD", (2, 3): "VGRD",
            }
            name = disc0_names.get((param_category, param_number), f"cat{param_category}_p{param_number}")
            
            print(f"  msg {count+1}: disc={discipline} cat={param_category} num={param_number} centre={centre} len={total_length} [{name}]")
            count += 1
            f.seek(pos + total_length)

print("=== NOMADS pgrb2 (subregion) ===")
read_grib2_messages('gfs_data/2026-07-05/gfs.t12z.pgrb2.0p25.f000')
print()
print("=== goessimpgrb2 (reference) ===")
read_grib2_messages('gfs_data/2026-07-02/gfs.t12z.goessimpgrb2.0p25.f000')
