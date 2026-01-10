import os
import requests
import sys

# 환경변수 가져오기
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('CHAT_ID')

print("--- 🔍 진단 시작 ---")

# 1. 시크릿(비밀번호)이 잘 넘어왔는지 확인
if not token:
    print("❌ 치명적 에러: TELEGRAM_TOKEN이 없습니다! Secrets 설정 이름을 확인하세요.")
    sys.exit(1)
else:
    # 보안을 위해 앞 4자리만 보여주고 나머지는 가림
    print(f"✅ 토큰 로드 성공: {token[:4]}****** (글자수: {len(token)})")

if not chat_id:
    print("❌ 치명적 에러: CHAT_ID가 없습니다! Secrets 설정 이름을 확인하세요.")
    sys.exit(1)
else:
    print(f"✅ CHAT_ID 로드 성공: {chat_id}")

# 2. 텔레그램 서버에 강제로 '테스트' 메시지 보내보기
print("\n--- 🚀 메시지 전송 시도 ---")
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    'chat_id': chat_id,
    'text': '🔔 [테스트] 연결 성공! 이 메시지가 보이면 설정이 완벽한 것입니다.'
}

try:
    response = requests.post(url, data=payload)
    print(f"📡 서버 응답 코드: {response.status_code}")
    print(f"📝 서버 응답 메시지: {response.text}") # 여기가 핵심입니다!

    if response.status_code == 200:
        print("\n🎉 결과: 전송 성공! 텔레그램을 확인하세요.")
    else:
        print("\n🔥 결과: 전송 실패! 위의 '서버 응답 메시지'를 읽어보세요.")
        sys.exit(1) # 실패 시 빨간 X를 띄우기 위해 강제 종료

except Exception as e:
    print(f"시스템 에러 발생: {e}")
    sys.exit(1)
