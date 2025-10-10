# -*- coding: utf-8 -*-
"""학습 데이터 로드 함수에 디버깅 추가"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# load_trade_history 수정
old_load_trade = '''    def load_trade_history(self):
        """거래 히스토리 로드"""
        if os.path.exists(self.learning_file):
            try:
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    self.all_trades = json.load(f)
                print(f"[학습 데이터] {len(self.all_trades)}개 거래 로드")
            except:
                self.all_trades = []'''

new_load_trade = '''    def load_trade_history(self):
        """거래 히스토리 로드"""
        print(f"[DEBUG] 거래 히스토리 로드 시작")
        print(f"[DEBUG] 작업 디렉토리: {os.getcwd()}")
        print(f"[DEBUG] 파일 경로: {self.learning_file}")
        print(f"[DEBUG] 파일 존재: {os.path.exists(self.learning_file)}")

        if os.path.exists(self.learning_file):
            try:
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    self.all_trades = json.load(f)
                print(f"[학습 데이터] {len(self.all_trades)}개 거래 로드 ✅")
            except Exception as e:
                print(f"[ERROR] 거래 히스토리 로드 실패: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                self.all_trades = []
        else:
            print(f"[INFO] 거래 히스토리 파일 없음 (새로 시작)")
            self.all_trades = []'''

# load_meta_insights 수정
old_load_meta = '''    def load_meta_insights(self):
        """메타 학습 인사이트 로드"""
        if os.path.exists(self.meta_learning_file):
            try:
                with open(self.meta_learning_file, 'r', encoding='utf-8') as f:
                    self.meta_insights = json.load(f)
                print(f"[메타 학습] {len(self.meta_insights)}개 인사이트 로드")
            except:
                self.meta_insights = []'''

new_load_meta = '''    def load_meta_insights(self):
        """메타 학습 인사이트 로드"""
        print(f"[DEBUG] 메타 인사이트 로드 시작")
        print(f"[DEBUG] 파일 경로: {self.meta_learning_file}")
        print(f"[DEBUG] 파일 존재: {os.path.exists(self.meta_learning_file)}")

        if os.path.exists(self.meta_learning_file):
            try:
                with open(self.meta_learning_file, 'r', encoding='utf-8') as f:
                    self.meta_insights = json.load(f)
                print(f"[메타 학습] {len(self.meta_insights)}개 인사이트 로드 ✅")
            except Exception as e:
                print(f"[ERROR] 메타 인사이트 로드 실패: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                self.meta_insights = []
        else:
            print(f"[INFO] 메타 인사이트 파일 없음 (새로 시작)")
            self.meta_insights = []'''

# 교체
modified = False

if old_load_trade in content:
    content = content.replace(old_load_trade, new_load_trade)
    print("[OK] load_trade_history 디버깅 추가 완료")
    modified = True
else:
    print("[ERROR] load_trade_history를 찾을 수 없습니다")

if old_load_meta in content:
    content = content.replace(old_load_meta, new_load_meta)
    print("[OK] load_meta_insights 디버깅 추가 완료")
    modified = True
else:
    print("[ERROR] load_meta_insights를 찾을 수 없습니다")

if modified:
    # 파일 쓰기
    with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
else:
    exit(1)
