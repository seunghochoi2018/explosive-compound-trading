#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

files = ['unified_trader_manager.py', 'watchdog.py']

for filename in files:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove all emojis
    emoji_pattern = re.compile(
        r'[\u2600-\u27BF]|'  # Miscellaneous Symbols
        r'[\U0001F300-\U0001F9FF]|'  # Emoji
        r'[\u2700-\u27BF]|'  # Dingbats
        r'[\uFE00-\uFE0F]|'  # Variation Selectors
        r'[\U0001F1E6-\U0001F1FF]'  # Regional Indicators
    )

    new_content = emoji_pattern.sub('', content)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"[OK] {filename}")

print("Done!")
