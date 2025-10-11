#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이모지 제거 스크립트
"""

import re

def remove_emojis(text):
    """이모지를 제거하고 텍스트만 남김"""
    # 유니코드 이모지 패턴
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002700-\U000027BF"  # Dingbats
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)

    return emoji_pattern.sub(r'', text)

def main():
    input_file = 'nvdl_nvdq_signal_notifier.py'
    output_file = 'nvdl_nvdq_signal_notifier_fixed.py'

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 이모지 제거
        fixed_content = remove_emojis(content)

        # 특정 패턴들 수정
        replacements = [
            ('', ''),
            ('', '[ERROR]'),
            ('', '[WARNING]'),
            ('', '[SAVE]'),
            ('', '[LOG]'),
            ('', '[AI]'),
            ('', '[STATS]'),
            ('', '[TARGET]'),
            ('', '[STOP]'),
            ('⏰', '[TIME]'),
            ('', '[SUCCESS]'),
            ('', '[FAIL]'),
            ('', '[UP]'),
            ('', '[DOWN]'),
            ('', '[BUY]'),
            ('', '[SELL]'),
            ('', '[HOLD]'),
            ('', '[$]'),
            ('', '[CONF]'),
            ('⏹', '[STOP]'),
            ('', '[END]'),
            ('', '[TIP]'),
        ]

        for old, new in replacements:
            fixed_content = fixed_content.replace(old, new)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        print(f"이모지 제거 완료: {output_file}")

    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    main()