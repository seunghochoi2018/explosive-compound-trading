#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""잔고 엑셀 파일 상세 분석"""

import pandas as pd

print("=" * 80)
print("해외주식 잔고 API 엑셀 파일 분석")
print("=" * 80)

df = pd.read_excel('해외주식 잔고[v1_해외주식-006].xlsx', header=None)

# output2 섹션 찾기
output2_rows = df[df[0].str.contains('output2', na=False, case=False)]

if len(output2_rows) > 0:
    output2_idx = output2_rows.index[0]
    print(f"\noutput2 발견: 행 {output2_idx}")

    # output2 전후 20행 출력
    print("\n=== output2 섹션 (전후 20행) ===")
    start = max(0, output2_idx - 5)
    end = min(len(df), output2_idx + 25)

    for idx in range(start, end):
        row = df.iloc[idx]
        # 비어있지 않은 셀만 출력
        non_empty = [(i, v) for i, v in enumerate(row) if pd.notna(v) and str(v).strip()]
        if non_empty:
            print(f"\n행 {idx}:")
            for col_idx, value in non_empty:
                print(f"  열{col_idx}: {value}")

# 예제 섹션 찾기
example_rows = df[df[0].str.contains('Example', na=False, case=False)]
if len(example_rows) > 0:
    ex_idx = example_rows.index[0]
    print(f"\n\n=== Example 섹션 (행 {ex_idx} 이후) ===")
    for idx in range(ex_idx, min(len(df), ex_idx + 10)):
        row = df.iloc[idx]
        non_empty = [(i, v) for i, v in enumerate(row) if pd.notna(v) and str(v).strip()]
        if non_empty:
            print(f"\n행 {idx}:")
            for col_idx, value in non_empty:
                print(f"  열{col_idx}: {value}")

print("\n" + "=" * 80)
