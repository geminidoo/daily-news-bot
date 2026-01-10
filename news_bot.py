import feedparser
import requests
import datetime
import time
import os
import sys

# 로그 출력을 위한 설정 (버퍼링 방지)
sys.stdout.reconfigure(line_buffering=True)

# ---------------------------------------------------------
# [설정] 텔레그램 봇 정보
# ---------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# ---------------------------------------------------------
# [소스] 카테고리별 고품질 RSS 피드
# ---------------------------------------------------------
RSS_FEEDS = {
    "1. 🌏 지정학 & 국제 정세 (Geopolitics)": [
        "https://news.google.com/rss/search?q=Geopolitics+International+Relations+when:1d&hl=en-US&gl=US&ceid=US:en",
        "http://feeds.bbci.co.uk/news/world/rss.xml"
    ],
    "2. 📈 거시 경제 & 금융 (Macro Economy)": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", 
        "https://finance.yahoo.com/news/rssindex" 
    ],
    "3. 🏛️ 정책 & 규제 (Policy & Politics)": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.washingtonpost.com/rss/politics"
    ],
    "4. 🏭 산업 & 기술 (Industry & Tech)": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910", 
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
    ]
}

def send_telegram_message(message):
    """텔레그램 메시지 전송 함수 (4000자 단위 분할 전송)"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ [오류] 토큰이나 CHAT_ID가 없습니다.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # 메시지가 너무 길 경우를 대비해 4000자 단위로 자름
    chunk_size = 4000
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i+chunk_size]
        payload = {
            'chat_id': CHAT_ID,
            'text': chunk,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            time.sleep(1) # 도배 방지
        except Exception as e:
            print(f"❌ 전송 실패: {e}")

def fetch_news():
    print("📰 뉴스 수집을 시작합니다...")
    today = datetime.datetime.now().strftime("%Y-%m-%d %A")
    full_report = f"<b>🇺🇸 US Morning Briefing: {today}</b>\n\n"

    for category, urls in RSS_FEEDS.items():
        print(f"🔍 {category} 수집 중...")
        full_report += f"<b>{category}</b>\n"
        news_count = 0
        
        for url in urls:
            if news_count >= 10: break # 카테고리당 최대 10개
            
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if news_count >= 10: break
                    
                    title = entry.title
                    link = entry.link
                    
                    # 제목에 HTML 특수문자가 있을 경우 처리 (간단하게)
                    title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    
                    full_report += f"• <a href='{link}'>{title}</a>\n"
                    news_count += 1
            except Exception as e:
                print(f"⚠️ 피드 오류 ({url}): {e}")
                continue
        
        full_report += "\n"

    full_report += "<i>Data aggregated via RSS.</i>"
    return full_report

if __name__ == "__main__":
    news_report = fetch_news()
    print("📤 텔레그램 전송 중...")
    send_telegram_message(news_report)
    print("✅ 완료되었습니다.")
