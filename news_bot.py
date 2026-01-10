import feedparser
import requests
import datetime
import time
import os
import sys
import socket

# 1. 막힘 방지 설정 (15초 동안 응답 없으면 건너뜀)
socket.setdefaulttimeout(15)
sys.stdout.reconfigure(line_buffering=True)

# 텔레그램 설정
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

RSS_FEEDS = {
    "1. 🌏 지정학 (Geopolitics)": [
        "https://news.google.com/rss/search?q=Geopolitics+when:1d&hl=en-US&gl=US&ceid=US:en",
        "http://feeds.bbci.co.uk/news/world/rss.xml"
    ],
    "2. 📈 경제 (Economy)": [
        "https://finance.yahoo.com/news/rssindex",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    ],
    "3. 🏛️ 정치 (Politics)": [
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
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'})
    except Exception as e:
        log(f"❌ 전송 실패: {e}")

def fetch_and_send():
    # [핵심] 봇이 살아있음을 먼저 알림
    log("🚀 뉴스 수집기 가동... 텔레그램으로 시작 알림을 보냅니다.")
    send_telegram("🤖 <b>[상태]</b> 뉴스 수집을 시작합니다... (잠시만 기다려주세요)")

    today = datetime.datetime.now().strftime("%Y-%m-%d %A")
    full_report = f"<b>🇺🇸 US Morning Briefing: {today}</b>\n\n"
    
    total_count = 0

    for category, urls in RSS_FEEDS.items():
        log(f"\n🔍 [카테고리] {category} 처리 중...")
        full_report += f"<b>{category}</b>\n"
        
        for url in urls:
            try:
                log(f"  - 접속 시도: {url[:40]}...")
                # 구글 뉴스 등 차단 방지를 위한 헤더 추가
                d = feedparser.parse(url, agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
                
                if not d.entries:
                    log("    ⚠️ 빈 결과 (차단되었거나 뉴스가 없음)")
                    continue
                
                count = 0
                for entry in d.entries[:5]: # 소스당 5개만
                    title = entry.title.replace("<", "&lt;").replace(">", "&gt;")
                    full_report += f"• <a href='{entry.link}'>{title}</a>\n"
                    count += 1
                
                log(f"    ✅ {count}개 수집 완료")
                total_count += count
                
            except Exception as e:
                log(f"    ❌ 에러 발생: {e}")
                continue
        
        full_report += "\n"

    if total_count == 0:
        log("❌ 수집된 뉴스가 0개입니다.")
        send_telegram("⚠️ <b>[오류]</b> 뉴스를 하나도 가져오지 못했습니다. 로그를 확인해주세요.")
    else:
        log(f"📤 총 {total_count}개의 뉴스 전송 시작...")
        send_telegram(full_report)
        log("✅ 전송 완료")

if __name__ == "__main__":
    try:
        fetch_and_send()
    except Exception as e:
        log(f"🔥 치명적 오류: {e}")
        send_telegram(f"🔥 봇 실행 중 오류 발생: {e}")
