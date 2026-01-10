import requests
from bs4 import BeautifulSoup
import datetime
import time
import os
import sys
import socket
import re
from collections import Counter

# ---------------------------------------------------------
# [설정] 기본값
# ---------------------------------------------------------
# 많은 양의 기사를 읽어야 하므로 타임아웃 60초 설정
socket.setdefaulttimeout(60)
sys.stdout.reconfigure(line_buffering=True)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

MAJOR_PRESS = {
    "조선일보": "023", "중앙일보": "025", "동아일보": "020",
    "매일경제": "009", "한국경제": "015"
}

def log(msg):
    print(msg, flush=True)

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # 메시지가 길면 4000자 단위로 나눠서 전송
    chunk_size = 4000
    for i in range(0, len(msg), chunk_size):
        chunk = msg[i:i+chunk_size]
        payload = {'chat_id': CHAT_ID, 'text': chunk, 'parse_mode': 'HTML', 'disable_web_page_preview': False}
        try:
            requests.post(url, data=payload, timeout=15)
            time.sleep(1) # 도배 방지
        except Exception as e:
            log(f"❌ 전송 실패: {e}")

# ---------------------------------------------------------
# [알고리즘] TextRank 기반 핵심 3문장 요약
# ---------------------------------------------------------
def summarize_text(text, num_sentences=3):
    if not text: return "내용 없음"
    
    # 문장 분리
    sentences = re.split(r'(?<=[.?!])\s+', text)
    if len(sentences) <= num_sentences:
        return "\n".join([f"- {s.strip()}" for s in sentences if s.strip()])

    # 단어 빈도 계산
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text)
    word_counts = Counter(words)
    
    # 문장 중요도 점수 계산
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        score = 0
        for word in word_counts:
            if word in sentence:
                score += word_counts[word]
        if len(sentence) < 10: score = 0 # 너무 짧은 문장 제외
        sentence_scores[i] = score

    # 상위 N개 문장 추출 및 순서 정렬
    top_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
    top_indices.sort()
    
    summary = []
    for idx in top_indices:
        summary.append(f"- {sentences[idx].strip()}")
        
    return "\n".join(summary)

def get_soup(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")
    except:
        return None

def analyze_article(link):
    """기사 상세 페이지 분석 (이미지 + 요약)"""
    try:
        # 0.1초 딜레이 (서버 부하 방지)
        time.sleep(0.1) 
        soup = get_soup(link)
        if not soup: return None, "본문을 가져올 수 없습니다."
        
        # 이미지 추출
        image_url = ""
        meta_img = soup.select_one("meta[property='og:image']")
        if meta_img: image_url = meta_img['content']
        
        # 본문 추출
        article_body = soup.select_one("div#newsct_article")
        if not article_body:
            article_body = soup.select_one("div#articeBody")
            
        if article_body:
            full_text = article_body.get_text(" ", strip=True)
            summary = summarize_text(full_text, num_sentences=3)
        else:
            summary = "요약 불가 (본문 형식 다름)"
            
        return image_url, summary
    except Exception as e:
        return None, f"분석 오류: {e}"

def crawl_section_and_send(sid, section_name, limit=20):
    """섹션별 크롤링 후 즉시 전송 (limit: 기사 개수)"""
    url = f"https://news.naver.com/section/{sid}"
    log(f"🔍 [{section_name}] {limit}개 기사 집중 분석 중...")
    
    soup = get_soup(url)
    if not soup: return
    
    articles = soup.select("div.sa_text")
    count = 0
    
    # 헤더 메시지
    msg = f"<b>[{section_name} 주요 뉴스 Top {limit}]</b>\n\n"
    
    for art in articles:
        if count >= limit: break
        
        title_tag = art.select_one("a.sa_text_title")
        if not title_tag: continue
        
        title = title_tag.get_text(strip=True)
        link = title_tag['href']
        
        # 상세 분석
        img_url, summary = analyze_article(link)
        
        # 투명 이미지 링크 (썸네일용)
        if img_url: msg += f"<a href='{img_url}'>&#8205;</a>"
        
        msg += f"<b>{count+1}. {title}</b>\n"
        msg += f"{summary}\n"
        msg += f"<a href='{link}'>[원문]</a>\n\n" # 원문 버튼 필수 추가
        count += 1
    
    log(f"   ✅ {section_name} {count}개 분석 완료 -> 전송")
    send_telegram(msg)

def crawl_finance():
    """금융/증권 뉴스 (10개)"""
    url = "https://finance.naver.com/news/mainnews.naver"
    log(f"🔍 [주식/금융] 분석 중...")
    
    soup = get_soup(url)
    if not soup: return
    
    articles = soup.select("div.mainNewsList li.block1")
    count = 0
    msg = f"<b>[📉 주식/금융 주요 뉴스]</b>\n\n"
    
    for art in articles:
        if count >= 10: break # 금융은 10개만
        
        subject = art.select_one("dd.articleSubject a")
        if not subject: continue
        
        title = subject.get_text(strip=True)
        link = "https://finance.naver.com" + subject['href']
        
        img_url, summary = analyze_article(link)
        
        if img_url: msg += f"<a href='{img_url}'>&#8205;</a>"
        msg += f"<b>{count+1}. {title}</b>\n{summary}\n<a href='{link}'>[원문]</a>\n\n"
        count += 1
        
    send_telegram(msg)

def crawl_major_press():
    """메이저 언론사 헤드라인 TOP 3"""
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    log("🔍 [주요 언론사] 분석 중...")
    
    soup = get_soup(url)
    if not soup: return
    
    msg = f"<b>[📰 메이저 언론사 헤드라인]</b>\n"
    ranking_boxes = soup.select("div.rankingnews_box")
    
    for box in ranking_boxes:
        name = box.select_one("strong.rankingnews_name").get_text(strip=True)
        if name not in MAJOR_PRESS: continue
        
        msg += f"\n🗞 <b>{name}</b>\n"
        list_items = box.select("ul.rankingnews_list li")
        
        c = 0
        for li in list_items:
            if c >= 3: break
            
            a_tag = li.select_one("a.list_title")
            title = a_tag.get_text(strip=True)
            link = a_tag['href']
            
            img_url, summary = analyze_article(link)
            
            if img_url: msg += f"<a href='{img_url}'>&#8205;</a>"
            msg += f"🔹 {title}\n{summary}\n<a href='{link}'>[원문]</a>\n"
            c += 1
            
    send_telegram(msg)

def run():
    log("🚀 대규모 뉴스 크롤러 가동...")
    send_telegram("🤖 <b>[분석 시작]</b> 주요 4대 섹션(20개씩) + 금융 + 언론사를 정밀 분석합니다.\n(기사가 많아 약 3~4분 소요됩니다. 섹션별로 순차 도착합니다.)")
    
    # 1. 정치 (20개) -> 전송
    crawl_section_and_send("100", "정치", limit=20)
    
    # 2. 세계 (20개) -> 전송
    crawl_section_and_send("104", "세계", limit=20)
    
    # 3. 경제 (20개) -> 전송
    crawl_section_and_send("101", "경제", limit=20)
    
    # 4. IT/과학 (20개) -> 전송
    crawl_section_and_send("105", "IT/과학", limit=20)
    
    # 5. 금융/주식 (10개) -> 전송
    crawl_finance()
    
    # 6. 언론사 헤드라인 -> 전송
    crawl_major_press()
    
    log("✅ 모든 작업 완료")
    send_telegram("✅ <b>[완료]</b> 오늘의 모든 뉴스 브리핑이 끝났습니다.")

if __name__ == "__main__":
    run()
