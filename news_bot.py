import os
import requests
import sys

# [핵심] 무조건 화면에 글자를 찍어내는(Flush) 설정
sys.stdout.reconfigure(line_buffering=True)

print("--- 🔍 진단 프로그램 시작 ---")
print("이 글자가 보이면 절반은 성공입니다!")

# 1. 환경변수 확인
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('CHAT_ID')

if not token:
    print("❌ [실패] TELEGRAM_TOKEN이 없습니다.")
else:
    print(f"✅ [성공] 토큰 로드됨: {token[:4]}******")

if not chat_id:
    print("❌ [실패] CHAT_ID가 없습니다.")
else:
    print(f"✅ [성공] CHAT_ID 로드됨: {chat_id}")

# 2. 메시지 전송 시도
print("\n--- 🚀 텔레그램 전송 시도 ---")
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    'chat_id': chat_id,
    'text': '🔔 [테스트] 드디어 성공했습니다! 로그가 보이고 메시지가 왔습니다.'
}

try:
    response = requests.post(url, data=payload)
    print(f"📡 서버 응답 코드: {response.status_code}")
    print(f"📝 서버 응답 메시지: {response.text}") # 이 부분이 중요합니다
except Exception as e:
    print(f"🔥 에러 발생: {e}")

print("--- 🏁 진단 종료 ---")
