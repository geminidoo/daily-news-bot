import os
import requests
import sys

token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('CHAT_ID')

print("--- 🔍 진단 시작 ---") # 이 줄이 꼭 있어야 합니다!

if not token:
    print("❌ 에러: TELEGRAM_TOKEN이 없습니다.")
else:
    print(f"✅ 토큰 로드 성공: {token[:4]}...")

if not chat_id:
    print("❌ 에러: CHAT_ID가 없습니다.")
else:
    print(f"✅ CHAT_ID 로드 성공: {chat_id}")

print("\n--- 🚀 전송 시도 ---")
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {'chat_id': chat_id, 'text': '🔔 [테스트] 설정 완료!'}

try:
    response = requests.post(url, data=payload)
    print(f"📝 서버 응답: {response.text}")
except Exception as e:
    print(f"에러 발생: {e}")
