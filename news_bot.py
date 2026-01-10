import feedparser
import requests
import datetime
import time
import os
import sys
import socket
import subprocess
import re  # 텍스트 정제용

# ---------------------------------------------------------
# [자동 설치] 번역 라이브러리 (deep-translator)
# ---------------------------------------------------------
try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("🛠️ 번역 라이브러리 설치 중...", flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
    from deep_translator import GoogleTranslator

# ---------------------------------------------------------
# [설정] 기본값
# ---------------------------------------------------------
socket.setdefaulttimeout(30)
sys.stdout.reconfigure(line_buffering=True)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 요약 내용이 충실한 RSS 소스 위주로 구성
RSS_FEEDS = {
    "1. 🌏 지정학 (Geopolitics)": [
        "https://news.google.com/rss/search?q=Geopolitics+when:1d&hl=en-US&gl=US&ceid=US:en",
    ],
    "2. 📈 거시 경제 (Macro Economy)": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", 
    ],
    "3. 🏛️ 정책 (Politics)": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml"
    ],
    "4. 🏭 기술 (Tech)": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
    ]
}

def log(msg):
    print(msg, flush=True)

def clean_html(raw_html):
    """HTML 태그를 제거하고 순수 텍스트만 추출"""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # 4000자 단위로 끊어서 전송
    chunk_size = 4000
    for i in range(0, len(msg), chunk_size):
        chunk = msg[i:i+chunk_size]
        payload = {'chat_id': CHAT_ID, 'text': chunk, 'parse_mode': 'HTML', 'disable_web_page_preview': False} # 미리보기 활성화
        try:
            requests.post(url, data=payload)
            time.sleep(1)
        except Exception as e:
            log(f"❌ 전송 실패: {e}")

def fetch_and_send():
    log("🚀 뉴스 수집 및 번역기 가동...")
    send_telegram("🤖 <b>[상태]</b> 주요 기사를 요약하고 번역 중입니다... (약 1~2분 소요)")

    today = datetime.datetime.now().strftime("%Y-%m-%d %A")
    full_report = f"<b>🇺🇸 미국 아침 브리핑 (국문 요약): {today}</b>\n\n"
    
    total_count = 0
    translator = GoogleTranslator(source='auto', target='ko')

    for category, urls in RSS_FEEDS.items():
        log(f"\n🔍 [카테고리] {category} 처리 중...")
        full_report += f"<b>{category}</b>\n"
        
        for url in urls:
            try:
                log(f"  - 접속: {url[:30]}...")
                feed = feedparser.parse(url)
                
                count = 0
                # 카테고리당 최신 기사 3개씩 (번역 품질과 속도 고려)
                for entry in feed.entries[:3]: 
                    title_en = entry.title
                    link = entry.link
                    
                    # 1. 요약문 추출 (summary 없으면 description 사용)
                    summary_raw = getattr(entry, 'summary', getattr(entry, 'description', ''))
                    
                    # 2. HTML 태그 제거 및 길이 조절
                    summary_clean = clean_html(summary_raw)
                    if len(summary_clean) > 300: # 너무 길면 300자에서 자름
                        summary_clean = summary_clean[:300] + "..."
                    
                    # 요약문이 너무 짧거나 없으면 제목을 대신 사용하지 않고 '내용 없음' 처리 (깔끔하게)
                    if len(summary_clean) < 10:
                        summary_clean = ""

                    # 3. 번역 (제목 + 요약)
                    try:
                        title_ko = translator.translate(title_en)
                        if summary_clean:
                            summary_ko = translator.translate(summary_clean)
                        else:
                            summary_ko = "" # 요약 없으면 번역 안 함
                        time.sleep(0.5) # 번역 서버 과부하 방지
                    except Exception as e:
                        log(f"    ⚠️ 번역 에러: {e}")
                        title_ko = title_en
                        summary_ko = "번역 불가"

                    # 4. 출력 형식 구성
                    full_report += f"🔹 <b>{title_ko}</b>\n"
                    if summary_ko:
                        full_report += f"   📄 {summary_ko}\n"
                    full_report += f"   🔗 <a href='{link}'>원문 기사 보기</a>\n\n"
                    
                    count += 1
                
                log(f"    ✅ {count}개 완료")
                total_count += count
                
            except Exception as e:
                log(f"    ❌ 에러: {e}")
                continue
        
        full_report += "\n"

    if total_count == 0:
        send_telegram("⚠️ 가져올 뉴스가 없습니다.")
    else:
        log("📤 번역된 뉴스 전송 시작...")
        send_telegram(full_report)
        log("✅ 전송 완료")

if __name__ == "__main__":
    fetch_and_send()
