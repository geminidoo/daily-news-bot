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
# 기사 본문을 다 읽어야 하므로 타임아웃을 넉넉히 줍니다.
socket.setdefaulttimeout(30)
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
    
    # 메시지가 길면 나눠서 전송
    chunk_size = 4000
    for i in range(0, len(msg), chunk_size):
        chunk = msg[i:i+chunk_size]
        # disable_web_page_preview=False로 해야 이미지가 보임
        payload = {'chat_id': CHAT_ID, 'text': chunk, 'parse_mode': 'HTML', 'disable_web_page_preview': False}
        try:
            requests.post(url, data=payload, timeout=10)
            time.sleep(1)
        except Exception as e:
            log(f"❌ 전송 실패: {e}")

# ---------------------------------------------------------
# [핵심] 자체 요약 알고리즘 (TextRank 방식의 경량화 버전)
# ---------------------------------------------------------
def summarize_text(text, num_sentences=3):
    """
    기사 전문을 분석하여 가장 핵심적인 3문장을 추출합니다.
    (빈도수가 높은 키워드가 많이 포함된 문장을 중요 문장으로 판단)
    """
    if not text: return "내용 없음"
    
    # 1. 문장 분리 (마침표, 물음표, 느낌표 기준)
    sentences = re.split(r'(?<=[.?!])\s+', text)
    if len(sentences) <= num_sentences:
        return "\n".join([f"- {s.strip()}" for s in sentences if s.strip()])

    # 2. 단어 추출 (2글자 이상만)
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text)
    
    # 3. 단어 빈도 계산
    word_counts = Counter(words)
    
    # 4. 문장별 점수 매기기 (중요 단어가 많을수록 고득점)
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        score = 0
        for word in word_counts:
            if word in sentence:
                score += word_counts[word]
        # 문장 길이가 너무 짧으면(10자 이하) 감점 (단순 인사말 등 제외)
        if len(sentence) < 10: score = 0
        sentence_scores[i] = score

    # 5. 상위 N개 문장 선택
    top_sentences_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
    
    # 6. 원래 글의 순서대로 정렬 (문맥 유지를 위해)
    top_sentences_indices.sort()
    
    summary = []
    for idx in top_sentences_indices:
        clean_sent = sentences[idx].strip()
        summary.append(f"- {clean_sent}")
        
    return "\n".join(summary)

def get_soup(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")
    except:
        return None

def analyze_article(link):
    """기사 링크로 들어가서 [이미지 URL]과 [본문 요약]을 가져옴"""
    try:
        time.sleep(0.2) # 서버 부하 방지
        soup = get_soup(link)
        if not soup: return None, "본문을 가져올 수 없습니다."
        
        # 1. 이미지 추출 (og:image)
        image_url = ""
        meta_img = soup.select_one("meta[property='og:image']")
        if meta_img:
            image_url = meta_img['content']
        
        # 2. 본문 추출 (네이버 뉴스 표준 태그: #newsct_article)
        article_body = soup.select_one("div#newsct_article")
        if not article_body:
            article_body = soup.select_one("div#articeBody") # 연예/스포츠 등 예외 처리
            
        if article_body:
            # 기자 정보, 이메일 등 불필요한 텍스트 제거
            full_text = article_body.get_text(" ", strip=True)
            # 요약 실행
            summary = summarize_text(full_text, num_sentences=3)
        else:
            summary = "본문 형식이 달라 요약할 수 없습니다."
            
        return image_url, summary
        
    except Exception as e:
        return None, f"분석 중 오류: {e}"

def crawl_section(sid, section_name):
    """섹션별 크롤링 (이미지+요약 포함)"""
    url = f"https://news.naver.com/section/{sid}"
    log(f"🔍 [{section_name}] 정밀 분석 중...")
    
    soup = get_soup(url)
    if not soup: return ""
    
    articles = soup.select("div.sa_text")
    count = 0
    
    # 텔레그램 메시지 생성
    msg = f"<b>[{section_name} 주요 뉴스]</b>\n"
    
    for art in articles:
        if count >= 5: break # (중요) 정밀 분석은 시간이 걸리므로 5개로 제한 권장
        
        title_tag = art.select_one("a.sa_text_title")
        if not title_tag: continue
        
        title = title_tag.get_text(strip=True)
        link = title_tag['href']
        
        # 상세 분석 (이미지, 요약)
        img_url, summary = analyze_article(link)
        
        # 텔레그램 이미지 프리뷰 트릭 (투명 링크 삽입)
        # 첫 번째 기사의 이미지를 대표로 보여주거나, 각 기사마다 링크를 걸어줌
        if img_url:
            msg += f"<a href='{img_url}'>&#8205;</a>" # 투명 문자
            
        msg += f"🔹 <b>{title}</b>\n"
        msg += f"{summary}\n"
        msg += f"<a href='{link}'>[원문]</a>\n\n"
        count += 1
        
    log(f"   ✅ {count}개 완료")
    return msg

def crawl_finance():
    """금융 뉴스 크롤링"""
    url = "https://finance.naver.com/news/mainnews.naver"
    log(f"🔍 [주식/금융] 정밀 분석 중...")
    
    soup = get_soup(url)
    if not soup: return ""
    
    articles = soup.select("div.mainNewsList li.block1")
    count = 0
    msg = f"<b>[📉 주식/금융]</b>\n"
    
    for art in articles:
        if count >= 5: break
        
        subject = art.select_one("dd.articleSubject a")
        if not subject: continue
        
        title = subject.get_text(strip=True)
        link = "https://finance.naver.com" + subject['href']
        
        img_url, summary = analyze_article(link)
        
        if img_url: msg += f"<a href='{img_url}'>&#8205;</a>"
        msg += f"🔹 <b>{title}</b>\n{summary}\n<a href='{link}'>[원문]</a>\n\n"
        count += 1
        
    log(f"   ✅ {count}개 완료")
    return msg

def crawl_major_press():
    """주요 언론사 TOP 3 정밀 분석"""
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    log("🔍 [주요 언론사] 헤드라인 분석 중...")
    
    soup = get_soup(url)
    if not soup: return ""
    
    msg = f"<b>[📰 메이저 언론사 헤드라인]</b>\n"
    ranking_boxes = soup.select("div.rankingnews_box")
    
    for box in ranking_boxes:
        name = box.select_one("strong.rankingnews_name").get_text(strip=True)
        if name not in MAJOR_PRESS: continue
        
        msg += f"\n🗞 <b>{name}</b>\n"
        list_items = box.select("ul.rankingnews_list li")
        
        c = 0
        for li in list_items:
            if c >= 3: break # 언론사별 3개만 (너무 길어짐 방지)
            
            a_tag = li.select_one("a.list_title")
            title = a_tag.get_text(strip=True)
            link = a_tag['href']
            
            img_url, summary = analyze_article(link)
            
            if img_url: msg += f"<a href='{img_url}'>&#8205;</a>"
            msg += f"<b>{c+1}. {title}</b>\n{summary}\n"
            c += 1
            
    return msg

def run():
    log("🚀 뉴스 심층 분석 봇 가동...")
    send_telegram("🤖 <b>[분석 시작]</b> 기사 본문을 읽고 요약 중입니다... (약 2~3분 소요)")
    
    report = f"<b>🇰🇷 모닝 뉴스 심층 브리핑</b>\n({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    
    # 너무 길어지는 것을 막기 위해 끊어서 전송
    # 1. 정치/세계
    part1 = crawl_section("100", "정치") + crawl_section("104", "세계")
    send_telegram(report + part1)
    
    # 2. 경제/IT
    part2 = crawl_section("101", "경제") + crawl_section("105", "IT/과학")
    send_telegram(part2)
    
    # 3. 주식/언론사
    part3 = crawl_finance() + crawl_major_press()
    send_telegram(part3)
    
    log("✅ 모든 전송 완료")

if __name__ == "__main__":
    run()
