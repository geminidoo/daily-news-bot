import os
import requests
import sys

# [핵심] 설정과 상관없이 무조건 로그를 출력하게 만드는 함수
def log(msg):
    print(msg, flush=True)

log("--- 🔍 진단 시작 (강제 출력 모드) ---")

# 1. 환경변수 확인
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('CHAT_ID')

if not token:
    log("❌ 에러: TELEGRAM_TOKEN이 없습니다. Secrets를 확인하세요.")
else:
    log(f"✅ 토큰 로드 성공 (앞 4자리): {token[:4]}...")

if not chat_id:
    log("❌ 에러: CHAT_ID가 없습니다. Secrets를 확인하세요.")
else:
    log(f"✅ CHAT_ID 로드 성공: {chat_id}")

# 2. 메시지 전송 시도
log("\n--- 🚀 전송 시도 ---")
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    'chat_id': chat_id,
    'text': '🔔 [테스트] 드디어 로그가 보입니다! 설정이 완료되었습니다.'
}

try:
    response = requests.post(url, data=payload)
    # 여기가 가장 중요합니다. 텔레그램 서버가 왜 거절했는지 알려줍니다.
    log(f"📝 서버 응답 메시지: {response.text}") 
except Exception as e:
    log(f"시스템 에러 발생: {e}")
