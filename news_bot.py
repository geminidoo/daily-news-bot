import feedparser
import requests
import datetime
import time
import os
import sys
import socket
import subprocess

# ---------------------------------------------------------
# [자동 설치] 번역 라이브러리가 없으면 스스로 설치 (YAML 수정 불필요)
# ---------------------------------------------------------
try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("🛠️ 번역 라이브러리(deep-translator) 설치 중...", flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
    from deep_translator import GoogleTranslator

# ---------------------------------------------------------
# [설정] 기본값 세팅
# ---------------------------------------------------------
socket.setdefaulttimeout(30) # 타임아웃 30초로 연장
sys.stdout.reconfigure(line_buffering=True)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 고품질 RSS 소스
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

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # 메시지가 길어질 수 있으므로 4000자씩 끊어서 전송
    chunk_size = 4000
    for i in range(0, len(msg), chunk_size):
        chunk = msg[i:i+chunk_size]
        payload = {'chat_id': CHAT_ID, 'text': chunk, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
        try:
            requests.post(url, data=payload)
            time.sleep(1) 
        except Exception as e:
            log(f"❌ 전송 실패: {e}")

def translate_text(text):
    """한글 번역 함수 (에러 발생 시 원문 반환)"""
    try:
        # 3000자 넘으면 잘라서 번역 (오류 방지)
        if len(text) > 3000: text = text[:3000]
        return GoogleTranslator(source='auto', target='ko').translate(text)
    except:
        return text

def fetch_and_send():
    log("🚀 뉴스 수집 및 번역기 가동...")
    send_telegram("🤖 <b>[상태]</b> 뉴스 수집 및 번역을 시작합니다. (약 1~2분 소요)")

    today = datetime.datetime.now().strftime("%Y-%m-%d %A")
    full_report = f"<b>🇺🇸 미국 아침 브리핑 (번역본): {today}</b>\n\n"
    
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
                # 카테고리당 최신 기사 3개만 (번역 속도 고려)
                for entry in feed.entries[:3]: 
                    title_en = entry.title
                    link = entry.link
                    
                    # 요약 내용 가져오기 (summary가 없으면 description 사용)
                    summary_en = getattr(entry, 'summary', getattr(entry, 'description', ''))
                    
                    # HTML 태그 제거 (간단 버전)
                    summary_clean = summary_en.split('<')[0] if '<' in summary_en else summary_en
                    if len(summary_clean) > 200: summary_clean = summary_clean[:200] + "..."

                    # 번역 시도
                    try:
                        title_ko = translator.translate(title_en)
                        summary_ko = translator.translate(summary_clean) if summary_clean else ""
                        time.sleep(0.5) # 번역 서버 차단 방지 딜레이
                    except Exception as e:
                        log(f"    ⚠️ 번역 실패: {e}")
                        title_ko = title_en
                        summary_ko = "번역 실패"

                    # 이모지 및 스타일 적용
                    full_report += f"🔹 <b>{title_ko}</b>\n"
                    full_report += f"   <a href='{link}'>[원문 보기]</a>\n"
                    if summary_ko:
                        full_report += f"   Cannot load summary.\n" # 텔레그램 가독성을 위해 요약은 인용구 처리 안함
                        full_report += f"   📝 <i>{summary_ko}</i>\n\n"
                    else:
                        full_report += "\n"
                    
                    count += 1
                
                log(f"    ✅ {count}개 완료")
                total_count += count
                
            except Exception as e:
                log(f"    ❌ 에러: {e}")
                continue
        
        full_report += "\n"

    if total_count == 0:
        send_telegram("⚠️ 뉴스를 가져오지 못했습니다.")
    else:
        log("📤 전송 시작...")
        send_telegram(full_report)
        log("✅ 완료")

if __name__ == "__main__":
    fetch_and_send()
