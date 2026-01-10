import requests
from bs4 import BeautifulSoup
import datetime
import time
import os
import sys
import socket

# ---------------------------------------------------------
# [설정] 기본값
# ---------------------------------------------------------
socket.setdefaulttimeout(30)
sys.stdout.reconfigure(line_buffering=True)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 네이버 뉴스 차단 방지를 위한 헤더 (브라우저인 척 위장)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# ---------------------------------------------------------
# [타겟] 주요 언론사 ID 매핑 (네이버 기준)
# ---------------------------------------------------------
MAJOR_PRESS = {
    "조선일보": "023",
    "중앙일보": "025",
    "동아일보": "020",
    "매일경제": "009",
    "한국경제": "015"
}

def log(msg):
    print(msg, flush=True)

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # 메시지 분할 전송
    chunk_size = 4000
    for i in range(0, len(msg), chunk_size):
        chunk = msg[i:i+chunk_size]
        payload = {'chat_id': CHAT_ID, 'text': chunk, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
        try:
            requests.post(url, data=payload, timeout=10)
            time.sleep(1)
        except Exception as e:
            log(f"❌ 전송 실패: {e}")

def get_soup(url):
    """URL에서 HTML을 가져와서 BeautifulSoup 객체로 반환"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        log(f"⚠️ 접속 오류 ({url}): {e}")
        return None

def crawl_naver_section(sid, section_name):
    """네이버 뉴스 섹션별(정치, 경제 등) 크롤링"""
    url = f"https://news.naver.com/section/{sid}"
    log(f"🔍 [{section_name}] 긁어오는 중... ({url})")
    
    soup = get_soup(url)
    if not soup: return ""

    news_list = []
    # 네이버 뉴스 섹션의 기사 컨테이너 (sa_text)
    articles = soup.select("div.sa_text")
    
    count = 0
    result_msg = f"<b>[{section_name} 주요 뉴스]</b>\n"
    
    for art in articles:
        if count >= 10: break
        
        # 제목 추출
        title_tag = art.select_one("a.sa_text_title")
        if not title_tag: continue
        title = title_tag.get_text(strip=True)
        
        # 요약 추출 (sa_text_lede)
        lede_tag = art.select_one("div.sa_text_lede")
        lede = lede_tag.get_text(strip=True) if lede_tag else ""
        
        # 내용이 너무 길면 자름
        if len(lede) > 100: lede = lede[:100] + "..."
        
        result_msg += f"🔹 <b>{title}</b>\n"
        if lede:
            result_msg += f"   - {lede}\n"
        result_msg += "\n"
        count += 1
        
    log(f"   ✅ {count}개 완료")
    return result_msg

def crawl_naver_finance():
    """네이버 금융 주요뉴스 크롤링 (주식)"""
    url = "https://finance.naver.com/news/mainnews.naver"
    log(f"🔍 [주식/금융] 긁어오는 중... ({url})")
    
    soup = get_soup(url)
    if not soup: return ""
    
    articles = soup.select("div.mainNewsList li.block1")
    count = 0
    result_msg = f"<b>[📉 주식/금융 주요 뉴스]</b>\n"
    
    for art in articles:
        if count >= 10: break
        
        # 제목
        subject = art.select_one("dd.articleSubject a")
        if not subject: continue
        title = subject.get_text(strip=True)
        
        # 요약
        summary_tag = art.select_one("dd.articleSummary")
        if summary_tag:
            # 기자 이름 등 불필요한 정보 제거
            for span in summary_tag.select("span"): span.decompose()
            summary = summary_tag.get_text(strip=True)
            if len(summary) > 100: summary = summary[:100] + "..."
        else:
            summary = ""
            
        result_msg += f"🔹 <b>{title}</b>\n"
        if summary:
            result_msg += f"   - {summary}\n"
        result_msg += "\n"
        count += 1
        
    log(f"   ✅ {count}개 완료")
    return result_msg

def crawl_major_press_ranking():
    """주요 언론사별 랭킹 1위 뉴스 (헤드라인)"""
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    log(f"🔍 [메이저 언론사] 1면 톱기사 확인 중...")
    
    soup = get_soup(url)
    if not soup: return ""
    
    result_msg = f"<b>[📰 주요 언론사 헤드라인]</b>\n"
    ranking_boxes = soup.select("div.rankingnews_box")
    
    count = 0
    for box in ranking_boxes:
        name_tag = box.select_one("strong.rankingnews_name")
        if not name_tag: continue
        press_name = name_tag.get_text(strip=True)
        
        # 우리가 원하는 메이저 언론사인지 확인
        if press_name not in MAJOR_PRESS: continue
        
        # 1위 기사만 추출
        first_news = box.select_one("ul.rankingnews_list li:first-child a.list_title")
        if first_news:
            title = first_news.get_text(strip=True)
            result_msg += f"🗞 <b>{press_name}</b>: {title}\n"
            count += 1
            
    result_msg += "\n"
    log(f"   ✅ {count}개 언론사 완료")
    return result_msg

def run():
    log("🚀 네이버 뉴스 크롤러 가동...")
    send_telegram("🤖 <b>[시작]</b> 네이버 뉴스를 수집합니다. (약 30초 소요)")
    
    full_report = f"<b>🇰🇷 오늘의 네이버 뉴스 요약</b>\n({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    
    # 1. 섹션별 뉴스 수집
    full_report += crawl_naver_section("100", "정치") # 정치
    full_report += crawl_naver_section("104", "세계") # 세계
    full_report += crawl_naver_section("105", "IT/과학") # IT
    full_report += crawl_naver_section("101", "경제") # 경제
    
    # 2. 주식 뉴스 수집
    full_report += crawl_naver_finance()
    
    # 3. 주요 언론사 헤드라인 수집
    full_report += crawl_major_press_ranking()
    
    log("📤 전송 시작...")
    send_telegram(full_report)
    log("✅ 모든 작업 완료")

if __name__ == "__main__":
    run()
