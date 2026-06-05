import urllib.request, json, ssl, sys, time

ssl._create_default_https_context = ssl._create_unverified_context

coords = [
    (1,  121.3565, 31.1875, '长宁区（住宅区）'),
    (2,  121.4301, 31.3269, '宝山区（高校区）'),
    (3,  121.4778, 31.2705, '虹口区（早高峰净流入站）'),
    (4,  121.5396, 31.2738, '杨浦区（商务区）'),
    (5,  121.4161, 31.1428, '徐汇区南'),
    (6,  121.4538, 31.2086, '徐汇区（住宅区）'),
    (7,  121.3375, 31.2639, '嘉定区'),
    (8,  121.5085, 31.3175, '杨浦区'),
    (9,  121.5321, 31.1811, '浦东南'),
    (10, 121.4105, 31.2594, '普陀区（早高峰净流出站）'),
]

sys.stdout.reconfigure(encoding='utf-8')

print('Cluster | 经度       | 纬度      | 论文地名                    | API实际查询结果')
print('-' * 110)
sys.stdout.flush()

for cid, lon, lat, old_name in coords:
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=12&language=zh"
    req = urllib.request.Request(url, headers={"User-Agent": "PaperCheck/2.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read())
        addr = data.get('address', {})
        district = addr.get('district', addr.get('city_district', ''))
        suburb = addr.get('suburb', '')
        county = addr.get('county', '')
        city = addr.get('city', '')
        display_name = data.get('display_name', 'N/A')
        
        # Build short name
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
        time.sleep(1.2)
    except Exception as e:
        print(f'  {cid:2d}   | {lon:10.4f} | {lat:9.4f} | {old_name:<26s} | ERROR: {e}')
        sys.stdout.flush()
        time.sleep(2.0)