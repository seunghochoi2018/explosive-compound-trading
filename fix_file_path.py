# -*- coding: utf-8 -*-
"""학습 파일 경로를 절대 경로로 수정"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 파일 경로 설정 수정
old_paths = '''        # 거래 히스토리 (Few-shot Learning용)
        self.trade_history = []
        self.all_trades = []
        self.learning_file = "kis_trade_history.json"
        self.load_trade_history()

        # 메타 학습 인사이트 (LLM이 학습한 패턴)
        self.meta_insights = []
        self.meta_learning_file = "kis_meta_insights.json"
        self.load_meta_insights()'''

new_paths = '''        # 거래 히스토리 (Few-shot Learning용)
        self.trade_history = []
        self.all_trades = []

        # 프로그램 디렉토리 기준으로 파일 경로 설정
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.learning_file = os.path.join(script_dir, "kis_trade_history.json")
        self.load_trade_history()

        # 메타 학습 인사이트 (LLM이 학습한 패턴)
        self.meta_insights = []
        self.meta_learning_file = os.path.join(script_dir, "kis_meta_insights.json")
        self.load_meta_insights()'''

# 교체
if old_paths in content:
    content = content.replace(old_paths, new_paths)
    print("[OK] 학습 파일 경로를 절대 경로로 변경 완료")
    print("  - 프로그램 위치 기준으로 자동 설정")
    print("  - 작업 디렉토리 무관하게 동작")
else:
    print("[ERROR] 기존 코드를 찾을 수 없습니다")
    exit(1)

# 파일 쓰기
with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
