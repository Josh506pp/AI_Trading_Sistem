import os
roots = [r'C:\Program Files', r'C:\Program Files (x86)', r'C:\Users\Joshua\AppData\Local', r'C:\Users\Joshua\AppData\Roaming', r'C:\Users\Joshua\Downloads']
found = []
for root in roots:
    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower() in ('terminal64.exe', 'terminal.exe'):
                    found.append(os.path.join(dirpath, fn))
with open('search_mt5_results.txt', 'w', encoding='utf-8') as f:
    for p in found:
        f.write(p + '\n')
    f.write('FOUND_COUNT: ' + str(len(found)) + '\n')
