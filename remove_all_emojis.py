#!/usr/bin/env python3
# Remove ALL emojis from all Python files
import os
import glob

def remove_emojis_from_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove specific emojis one by one
        emojis_to_remove = [
            '', '', '', '', '', '', '', '', '', '',
            '', '', '', '', '', '', '', '', '', '',
            '', '', '', '', '', '', '', '', '', ''
        ]

        for emoji in emojis_to_remove:
            content = content.replace(emoji, '')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

# Process all directories
directories = [
    r'C:\Users\user\Documents\코드3',
    r'C:\Users\user\Documents\코드4',
    r'C:\Users\user\Documents\코드5'
]

total_processed = 0
for directory in directories:
    if os.path.exists(directory):
        py_files = glob.glob(os.path.join(directory, '*.py'))
        for py_file in py_files:
            if remove_emojis_from_file(py_file):
                total_processed += 1
                print(f"Cleaned: {os.path.basename(py_file)}")

print(f"\nTotal files processed: {total_processed}")
