#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safely remove emojis from Python files
"""
import os
import glob
import re

def safe_remove_emojis(filepath):
    """Safely remove emojis from a file"""
    try:
        # Read file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Save original length
        original_length = len(content)

        # Remove emojis - comprehensive pattern
        emoji_pattern = re.compile(
            r'[\u2600-\u27BF]|'  # Miscellaneous Symbols
            r'[\U0001F300-\U0001F9FF]|'  # Emoji
            r'[\u2700-\u27BF]|'  # Dingbats
            r'[\uFE00-\uFE0F]|'  # Variation Selectors
            r'[\U0001F1E6-\U0001F1FF]'  # Regional Indicators
        )

        new_content = emoji_pattern.sub('', content)

        # Safety check - content shouldn't be empty or too short
        if len(new_content) == 0:
            print(f"  [SKIP] {os.path.basename(filepath)} - Would be empty!")
            return False

        if len(new_content) < original_length * 0.5:
            print(f"  [SKIP] {os.path.basename(filepath)} - Too much content removed!")
            return False

        # Only write if content actually changed
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  [OK] {os.path.basename(filepath)} - {original_length - len(new_content)} chars removed")
            return True
        else:
            return False

    except Exception as e:
        print(f"  [ERROR] {os.path.basename(filepath)}: {e}")
        return False

# Process all directories
dirs = [
    r'C:\Users\user\Documents\코드3',
    r'C:\Users\user\Documents\코드4',
    r'C:\Users\user\Documents\코드5'
]

total_processed = 0
total_modified = 0

print("=" * 80)
print("Safe Emoji Removal")
print("=" * 80)

for directory in dirs:
    if os.path.exists(directory):
        print(f"\n[Processing] {os.path.basename(directory)}")
        py_files = glob.glob(os.path.join(directory, '*.py'))
        for py_file in py_files:
            total_processed += 1
            if safe_remove_emojis(py_file):
                total_modified += 1

print(f"\n{'=' * 80}")
print(f"Total files processed: {total_processed}")
print(f"Total files modified: {total_modified}")
print("=" * 80)
