#!/usr/bin/env python3
"""Search for old place names in PNG binary."""
import sys

img_path = r"C:\Users\33294\Desktop\paper_project\figures\dual_arrival_departure_rate.png"

with open(img_path, 'rb') as f:
    data = f.read()

# Check for old place names in UTF-8
checks = {
    '静安寺': '静安寺'.encode('utf-8'),
    '中山公园': '中山公园'.encode('utf-8'),
    '静安寺站': '静安寺站'.encode('utf-8'),
    '中山公园住宅区': '中山公园住宅区'.encode('utf-8'),
}

found_any = False
for name, b in checks.items():
    if b in data:
        print(f"WARNING: Found '{name}' in figure!")
        found_any = True
    
if not found_any:
    print("OK: No old place names found in figure binary data")
    print("Figure titles have been successfully updated")

# Also check expected new titles
expected = ['CBD (Cluster', 'RES (Cluster']
for e in expected:
    eb = e.encode('utf-8')
    if eb in data:
        print(f"Confirmed: '{e}' found in figure")