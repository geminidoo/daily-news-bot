import feedparser
import requests
import datetime
import time
import os

# 텔레그램 설정 (나중에 Secrets에서 가져옴)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 뉴스 소스 (카테고리별 10개씩 수집)
RSS_FEEDS = {
    "1. 🌏 지정학 (Geopolitics)": [
        "https://news.google.com/rss/search?q=Geopolitics+when:1d&hl=en-US&gl=US&ceid=US:en",
        "http://feeds.bbci.co.uk/news/world/rss.xml"
    ],
    "2. 📈 경제 (Economy)": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
        "https://finance.yahoo.com/news/rssindex"
    ],
    "3. 🏛️ 정치 (Politics)": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.washingtonpost.com/rss/politics"
    ],
    "4. 🏭 기술 (Tech)": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
    ]
}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunk_size = 4000
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i+chunk_size]
        payload = {'chat_id': CHAT_ID, 'text': chunk, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
        try: requests.post(url, data=payload)
        except Exception as e: print(e)
        time.sleep(1)

def fetch_news():
    today = datetime.datetime.now().strftime("%Y-%m-%d %A")
    full_report = f"<b>🇺🇸 US Morning Briefing: {today}</b>\n\n"
    for category, urls in RSS_FEEDS.items():
        full_report += f"<b>{category}</b>\n"
        count = 0
        for url in urls:
            if count >= 10: break
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if count >= 10: break
                    full_report += f"• <a href='{entry.link}'>{entry.title}</a>\n"
                    count += 1
            except: continue
        full_report += "\n"
    return full_report

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: 토큰이 없습니다.")
    else:
        report = fetch_news()
        send_telegram_message(report)
