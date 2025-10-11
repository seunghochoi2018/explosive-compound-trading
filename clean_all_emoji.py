#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import glob

dirs = [
    r'C:\Users\user\Documents\코드3',
    r'C:\Users\user\Documents\코드4',
    r'C:\Users\user\Documents\코드5'
]

emoji_pattern = re.compile(
    r'[\u2600-\u27BF]|'
    r'[\U0001F300-\U0001F9FF]|'
    r'[\u2700-\u27BF]|'
    r'[\uFE00-\uFE0F]|'
    r'[\U0001F1E6-\U0001F1FF]'
)

count = 0
for directory in dirs:
    if not os.path.exists(directory):
        continue

    for py_file in glob.glob(os.path.join(directory, '*.py')):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if emoji_pattern.search(content):
                new_content = emoji_pattern.sub('', content)
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count += 1
                print(f"[OK] {os.path.basename(py_file)}")
        except:
            pass

print(f"\n{count} files cleaned")
