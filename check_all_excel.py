#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""모든 엑셀 파일 확인"""

import pandas as pd
import os

files = [
    '해외주식 현재가상세[v1_해외주식-029].xlsx',
    '해외주식 잔고[v1_해외주식-006].xlsx',
    '해외주식 주문[v1_해외주식-001].xlsx'
]

for filename in files:
    print("=" * 80)
    print(f"파일: {filename}")
    print("=" * 80)

    df = pd.read_excel(filename, header=None)

    # TR_ID 찾기
    tr_id_rows = df[df[0].str.contains('TR_ID|TR ID', na=False, case=False)]
    if len(tr_id_rows) > 0:
        print(f"\nTR_ID 정보:")
        for idx in tr_id_rows.index[:3]:
            row = df.iloc[idx]
            non_empty = [str(v) for v in row if pd.notna(v) and str(v).strip()]
            print(f"  {' | '.join(non_empty)}")

    # Example 응답 찾기
    example_rows = df[df[0].str.contains('Response Example', na=False, case=False)]
    if len(example_rows) > 0:
        ex_idx = example_rows.index[0]
        print(f"\n예제 응답 (행 {ex_idx}):")

        # 다음 행의 값 (JSON)
        if ex_idx + 1 < len(df):
            response_json = df.iloc[ex_idx, 1]  # 두번째 열
            if pd.notna(response_json):
                # JSON 파싱
                try:
                    import json
                    resp = json.loads(str(response_json))

                    # rt_cd와 msg1 확인
                    print(f"  rt_cd: {resp.get('rt_cd', 'N/A')}")
                    print(f"  msg1: {resp.get('msg1', 'N/A')}")

                    # output 구조 확인
                    if 'output' in resp:
                        print(f"  output 타입: {type(resp['output']).__name__}")
                        if isinstance(resp['output'], dict):
                            print(f"  output 키: {list(resp['output'].keys())[:5]}")
                    if 'output1' in resp:
                        print(f"  output1 타입: {type(resp['output1']).__name__}")
                    if 'output2' in resp:
                        print(f"  output2 타입: {type(resp['output2']).__name__}")
                        if isinstance(resp['output2'], dict):
                            print(f"  output2 키: {list(resp['output2'].keys())}")
                            # 중요 필드 출력
                            for key in ['frcr_buy_amt_smtl1', 'frcr_pchs_amt1']:
                                if key in resp['output2']:
                                    print(f"    {key}: {resp['output2'][key]}")
                except:
                    print(f"  (JSON 파싱 실패)")

    print("\n")
