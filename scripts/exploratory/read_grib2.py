#!/usr/bin/env python3
"""Read GRIB2 message headers to identify parameters in goessimpgrb2 file"""
import struct
import sys

def read_grib2_messages(filepath, max_messages=30):
    with open(filepath, 'rb') as f:
        count = 0
        while count < max_messages:
            # Find GRIB indicator
            while True:
                pos = f.tell()
                byte = f.read(1)
                if not byte:
                    return
                if byte == b'G':
                    check = f.read(3)
                    if check == b'RIB':
                        break
            
            # Read rest of header: reserved(3) + discipline(1) + total_length(8)
            header = f.read(12)
            if len(header) < 12:
                return
            
            discipline = header[3]
            total_length = struct.unpack('>Q', header[4:12])[0]
            
            msg_start = pos
            msg_end = pos + total_length
            
            # Read identification section (section 0)
            sec0 = f.read(21)
            if len(sec0) < 21:
                return
            centre = struct.unpack('>H', sec0[0:2])[0]
            sub_centre = struct.unpack('>H', sec0[2:4])[0]
            
            # Read section 1 (product definition)
            sec1_size_bytes = f.read(4)
            sec1_size = struct.unpack('>I', sec1_size_bytes)[0]
            
            sec1_data = f.read(sec1_size - 4)
            param_category = sec1_data[0] if len(sec1_data) > 0 else -1
            param_number = sec1_data[1] if len(sec1_data) > 1 else -1
            
            # Read template number from sec1 bytes 7-8
            template_num = struct.unpack('>H', sec1_data[6:8])[0] if len(sec1_data) > 7 else -1
            
            print(f"Message {count+1}: discipline={discipline}, param_category={param_category}, param_number={param_number}, template={template_num}, centre={centre}")
            
            count += 1
            f.seek(msg_end)

filepath = '/wrf/WPS/gfs_data/gfs.t12z.goessimpgrb2.0p25.f000'
read_grib2_messages(filepath, 30)
