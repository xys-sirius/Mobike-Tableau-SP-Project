with open(r'C:\Users\33294\Desktop\paper_project\paper\main.tex', 'r', encoding='utf-8') as f:
    lines = f.readlines()

target = ['死循环', '滚雪球', '抖动', '调出', '调度成本', '滚雪', '雪球', '高频', '无效', 'CBD', '共振', '5.4.3', 'subsection', '极强', '潮汐共振']

for i, line in enumerate(lines):
    for w in target:
        if w in line:
            print(f"L{i+1} [{w}]: {line.rstrip()[:150]}")
            break