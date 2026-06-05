import urllib.request, json, ssl, sys, time

ssl._create_default_https_context = ssl._create_unverified_context

coords = [
    (1,  121.3565, 31.1875, '长宁区（住宅区）'),
    (9,  121.5321, 31.1811, '浦东南'),
]

sys.stdout.reconfigure(encoding='utf-8')

for cid, lon, lat, old_name in coords:
    success = False
    for attempt in range(3):
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=12&language=zh"
            req = urllib.request.Request(url, headers={"User-Agent": "PaperCheck/2.0"})
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read())
            addr = data.get('address', {})
            district = addr.get('district', addr.get('city_district', ''))
            suburb = addr.get('suburb', '')
            county = addr.get('county', '')
            display_name = data.get('display_name', 'N/A')
            
            parts = []
            if district:
                parts.append(district)
            if suburb and suburb not in parts:
                parts.append(suburb)
            if county and county not in parts:
                parts.append(county)
            if not parts:
                parts.append(display_name[:60])
            short = ', '.join(parts)
            
            print(f'  {cid:2d}   | {lon:10.4f} | {lat:9.4f} | {old_name:<26s} | {short}')
            print(f'       Full: {display_name[:150]}')
            sys.stdout.flush()
            success = True
            break
        except Exception as e:
            print(f'  {cid:2d}   | Attempt {attempt+1}/3: ERROR: {e}')
            sys.stdout.flush()
            time.sleep(3)
    if not success:
        print(f'  {cid:2d}   | {lon:10.4f} | {lat:9.4f} | {old_name:<26s} | ALL ATTEMPTS FAILED')
        sys.stdout.flush()