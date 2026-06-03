import pathlib

p = pathlib.Path(r'C:\Users\33294\Desktop\paper_project\paper\main.tex')
t = p.read_text(encoding='utf-8')

# Show all lines containing textdegree or circ
lines = t.splitlines()
for i, l in enumerate(lines, 1):
    if 'textdegree' in l or 'circ' in l:
        print(f'{i}: {l[:150]}')

# Replace ALL \textdegree{} with {}^{\circ} (since they're all in math mode)
old_count = t.count('\\textdegree{}')
t = t.replace('\\textdegree{}', '{}^{\\circ}')
new_count = t.count('{}^{\\circ}')

p.write_text(t, encoding='utf-8')
print(f'\nReplaced {old_count} textdegree -> {new_count} circ occurrences')