import requests
from bs4 import BeautifulSoup
import datetime
import time
import os
import sys
import socket

# ---------------------------------------------------------
# [설정] 기본값 세팅
# ---------------------------------------------------------
# 기사 본문을 일일이 방문해야 하므로 타임아웃을 넉넉하게 설정
socket.setdefaulttimeout(60) 
sys.stdout.reconfigure(line_buffering=True)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 네이버 뉴스 차단 방지용 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# [타겟] 주요 언론사 ID (조선, 중앙, 동아, 매경, 한경)
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
    
    # 메시지 분할 전송 (4000자 제한)
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
    """URL 접속 후 BeautifulSoup 객체 반환"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        log(f"⚠️ 접속 오류 ({url}): {e}")
        return None

def get_article_summary(link):
    """기사 상세 페이지에 들어가서 '헤드라인 요약(og:description)'을 가져오는 함수"""
    try:
        time.sleep(0.3) # 너무 빠른 접속 방지
        soup = get_soup(link)
        if not soup: return ""
        
        # 1. 메타 태그 설명이 가장 깔끔함 (og:description)
        meta_desc = soup.select_one("meta[property='og:description']")
        if meta_desc:
            return meta_desc['content'].strip()
        
        # 2. 없으면 본문 앞부분 추출
        body = soup.select_one("div#newsct_article")
        if body:
            return body.get_text(strip=True)[:150] # 150자까지만
            
        return "요약 내용을 가져올 수 없습니다."
    except:
        return ""

def crawl_naver_section(sid, section_name):
    """네이버 뉴스 섹션별 크롤링 (요약문 전체 가져오기)"""
    url = f"https://news.naver.com/section/{sid}"
    log(f"🔍 [{section_name}] 수집 중...")
    
    soup = get_soup(url)
    if not soup: return ""

    articles = soup.select("div.sa_text")
    count = 0
    result_msg = f"<b>[{section_name} 주요 뉴스]</b>\n"
    
    for art in articles:
        if count >= 10: break # 10개 제한
        
        title_tag = art.select_one("a.sa_text_title")
        if not title_tag: continue
        title = title_tag.get_text(strip=True)
        
        # [수정됨] 글자 수 제한 제거 (네이버가 제공하는 요약문 전체 사용)
        lede_tag = art.select_one("div.sa_text_lede")
        lede = lede_tag.get_text(strip=True) if lede_tag else ""
        
        result_msg += f"🔹 <b>{title}</b>\n"
        if lede:
            result_msg += f"   📄 {lede}\n"
        result_msg += "\n"
        count += 1
        
    log(f"   ✅ {count}개 완료")
    return result_msg

def crawl_naver_finance():
    """주식/금융 뉴스 크롤링"""
    url = "https://finance.naver.com/news/mainnews.naver"
    log(f"🔍 [주식/금융] 수집 중...")
    
    soup = get_soup(url)
    if not soup: return ""
    
    articles = soup.select("div.mainNewsList li.block1")
    count = 0
    result_msg = f"<b>[📉 주식/금융 주요 뉴스]</b>\n"
    
    for art in articles:
        if count >= 10: break
        
        subject = art.select_one("dd.articleSubject a")
        if not subject: continue
        title = subject.get_text(strip=True)
        
        summary_tag = art.select_one("dd.articleSummary")
        if summary_tag:
            for span in summary_tag.select("span"): span.decompose() # 기자 이름 제거
            summary = summary_tag.get_text(strip=True) # [수정됨] 글자 수 제한 제거
        else:
            summary = ""
            
        result_msg += f"🔹 <b>{title}</b>\n"
        if summary:
            result_msg += f"   📄 {summary}\n"
        result_msg += "\n"
        count += 1
        
    log(f"   ✅ {count}개 완료")
    return result_msg

def crawl_major_press_ranking():
    """[심화] 주요 언론사별 TOP 5 기사 + 상세 요약"""
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    log(f"🔍 [메이저 언론사] 상세 크롤링 시작 (시간이 좀 걸립니다)...")
    
    soup = get_soup(url)
    if not soup: return ""
    
    result_msg = f"<b>[📰 주요 언론사 헤드라인 (TOP 5)]</b>\n"
    ranking_boxes = soup.select("div.rankingnews_box")
    
    total_press_count = 0
    
    for box in ranking_boxes:
        name_tag = box.select_one("strong.rankingnews_name")
        if not name_tag: continue
        press_name = name_tag.get_text(strip=True)
        
        # 지정된 메이저 언론사만 처리
        if press_name not in MAJOR_PRESS: continue
        
        result_msg += f"\n🗞 <b>{press_name}</b>\n"
        log(f"   Exploring {press_name}...")
        
        # [수정됨] TOP 5 기사 가져오기
        list_items = box.select("ul.rankingnews_list li")
        news_count = 0
        
        for li in list_items:
            if news_count >= 5: break # 5개 제한
            
            a_tag = li.select_one("a.list_title")
            if not a_tag: continue
            
            title = a_tag.get_text(strip=True)
            link = a_tag['href']
            
            # [추가됨] 기사 링크로 들어가서 요약문 가져오기
            summary = get_article_summary(link)
            
            result_msg += f"{news_count+1}. <b>{title}</b>\n"
            if summary:
                result_msg += f"   - {summary}\n"
            news_count += 1
            
        total_press_count += 1
            
    result_msg += "\n"
    log(f"   ✅ {total_press_count}개 언론사 완료")
    return result_msg

def run():
    log("🚀 뉴스 크롤러 가동 시작...")
    send_telegram("🤖 <b>[시작]</b> 뉴스 수집을 시작합니다. (기사 본문 분석으로 약 1분 정도 소요됩니다)")
    
    full_report = f"<b>🇰🇷 오늘의 심층 뉴스 브리핑</b>\n({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    
    # 1. 섹션별 뉴스 (요약문 전체)
    full_report += crawl_naver_section("100", "정치")
    full_report += crawl_naver_section("104", "세계")
    full_report += crawl_naver_section("105", "IT/과학")
    full_report += crawl_naver_section("101", "경제")
    
    # 2. 주식 뉴스
    full_report += crawl_naver_finance()
    
    # 3. 주요 언론사 (TOP 5 + 상세 요약)
    full_report += crawl_major_press_ranking()
    
    log("📤 전송 시작...")
    send_telegram(full_report)
    log("✅ 작업 완료")

if __name__ == "__main__":
    run()
