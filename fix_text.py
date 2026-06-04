import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\33294\Desktop\paper_project\paper\main.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix RES risk numbers in 5.4.3 (1.35%→2.43%, 4.32%→2.64%)
old = '相比之下，RES站$K=80$的充裕容量使满站风险极低（1.35\\%），调度的焦点集中于空站风险（4.32\\%）。'
new = '相比之下，RES站$K=80$的充裕容量使满站风险极低（2.43\\%），调度的焦点集中于空站风险（2.64\\%）。'
if old in content:
    content = content.replace(old, new)
    print('✓ Fixed RES risk numbers')
else:
    print('✗ RES risk line not found')

# 2. Fix 5.4.3 CBD text: 10.17%→6.37%
old2 = 'CBD站早高峰净流入特征使其面临显著的满站压力（$P(N=K)=6.37\\%$）。'
# Already fixed, skip

# 3. Fix RES risk numbers still in old form (search for remaining 4.32% and 1.35%)
# These appear in the "关键发现" section and in 5.4.3 RES description
old3 = '空站峰值仅2.64\\%（18:00），满站峰值2.43\\%（23:00）'
# Already correct from ODE data

# 4. Fix "但风险量级远低于原先预期的10\\%级别"
old4 = '但风险量级远低于原先预期的10\\%级别'
new4 = '且风险量级控制在个位数百分比级别（$<$7\\%）'
if old4 in content:
    content = content.replace(old4, new4)
    print('✓ Fixed risk magnitude comment')
else:
    print('✗ Risk magnitude line not found')

# 5. Fix 5.3 risk narrative - the text about 10.80% and 10.17%
# Search for remaining occurrences of 10.80% and 10.17% in 5.3 section
old5 = 'CBD站早高峰空站概率10.80\\%、满站概率10.17\\%'
new5 = 'CBD站早高峰空站概率5.28\\%、满站概率6.37\\%'
count5 = content.count(old5)
if count5 > 0:
    content = content.replace(old5, new5)
    print(f'✓ Fixed CBD risk numbers in narrative ({count5} occurrences)')
else:
    print('✗ CBD 10.80/10.17 not found')

# 6. Fix remaining 4.32% and 1.35% for RES
old6 = 'RES站分别为4.32\\%和1.35\\%'
new6 = 'RES站分别为2.64\\%和2.43\\%'
count6 = content.count(old6)
if count6 > 0:
    content = content.replace(old6, new6)
    print(f'✓ Fixed RES risk numbers ({count6} occurrences)')
else:
    print('✗ RES 4.32/1.35 not found')

# 7. Fix 6.1 conclusions: "CBD站容量从50增至60可使空站/满站概率分别降至4.89\\%和3.32\\%"
old7 = '可使空站/满站概率分别降至4.89\\%和3.32\\%'
new7 = '可使空站/满站概率分别降至5.28\\%和3.87\\%'
count7 = content.count(old7)
if count7 > 0:
    content = content.replace(old7, new7)
    print(f'✓ Fixed 6.1 conclusions K-sensitivity numbers ({count7} occurrences)')
else:
    print('✗ 6.1 conclusions numbers not found')

# Check for any remaining 10.80 or 10.17 or 4.32 or 1.35 or 4.89 or 3.32
for search, name in [
    ('10.80', '10.80%'), ('10.17', '10.17%'),
    ('4.32', '4.32% (RES old)'), ('1.35', '1.35% (RES old)'),
    ('4.89', '4.89% (K=60 old)'), ('3.32', '3.32% (K=60 old)')
]:
    indices = [i for i in range(len(content)) if content.startswith(search, i)]
    if indices:
        print(f'⚠ Remaining {name}: found at positions {indices[:5]}')

with open(r'C:\Users\33294\Desktop\paper_project\paper\main.tex', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nDone. File updated.')