import requests
import json
import urllib3
import urllib.parse
from datetime import date, datetime, timedelta
import time
import re
import difflib
import feedparser

# SSL 경고 숨김
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Supabase 설정
SUPABASE_URL = "https://beaqnrzlnbqxltphfxrc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJlYXFucnpsbmJxeGx0cGhmeHJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwODA3MjgsImV4cCI6MjA5MDY1NjcyOH0.m41O66_yWUFFI_RdP07XxhbrCpnHR9AyNX3jrBkeZSQ"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

GEMINI_API_KEY = "AIzaSyD0WbRGY317Hq1wR479rmUa2vhDCc3XdHs"

def clean_url(url_str):
    if not url_str: return "#"
    match = re.search(r'(https?://[^\s)\]\'\"]+)', url_str)
    return match.group(1) if match else url_str

def get_setting(id_num):
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/user_settings?id=eq.{id_num}", headers=HEADERS, verify=False, timeout=8)
        if res.status_code == 200 and res.json():
            return res.json()[0]['keywords']
    except: pass
    return []

# 💡 핵심 수정: 중복 방지를 위해 기존 DB에서 요약본(summary)까지 가져옵니다.
def get_existing_data():
    url = f"{SUPABASE_URL}/rest/v1/articles?select=source_url,title,summary&limit=1000"
    try:
        res = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        if res.status_code == 200:
            data = res.json()
            urls = set(item['source_url'] for item in data)
            titles = [item['title'] for item in data]
            summaries = [item.get('summary', '') for item in data]
            return urls, titles, summaries
    except: pass
    return set(), [], []

def save_article(article):
    requests.post(f"{SUPABASE_URL}/rest/v1/articles", headers=HEADERS, json=article, verify=False)

def extract_json_from_response(text):
    text = text.strip()
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match: return json.loads(json_match.group(0))
    raise ValueError("JSON 구조를 찾을 수 없습니다.")

def get_best_gemini_url():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        res = requests.get(url, verify=False, timeout=10)
        if res.status_code != 200:
            return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        models = res.json().get('models', [])
        available_models = [m["name"] for m in models if "generateContent" in m.get("supportedGenerationMethods", []) and "gemini" in m.get("name", "")]
        target_model = next((m for m in ["models/gemini-2.5-flash", "models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"] if m in available_models), available_models[0] if available_models else None)
        if target_model: return f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={GEMINI_API_KEY}"
        return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    except:
        return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

def fetch_crossref_candidates(field, tech, detail):
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    query_terms = []
    for w in field + tech + detail:
        w_lower = w.lower()
        if '축산' in w_lower: query_terms.append("livestock OR animal")
        elif '식품' in w_lower: query_terms.append("food OR dietary")
        elif '영양' in w_lower: query_terms.append("nutrition OR nutrient")
        elif '스마트' in w_lower: query_terms.append("smart OR sensor OR automation")
        else: query_terms.append(w)
        
    query = " ".join(query_terms)
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={encoded_query}&select=URL,title,publisher&filter=from-pub-date:{three_months_ago}&rows=30"
    
    try:
        res = requests.get(url, timeout=15, verify=False)
        items = res.json().get("message", {}).get("items", [])
        candidates = {}
        for item in items:
            title = item.get("title", [""])[0]
            url = item.get("URL", "")
            publisher = item.get("publisher", "Unknown")
            if title and url: candidates[url] = {"title": f"[{publisher}] {title}", "url": url}
        return candidates
    except: return {}

def evaluate_papers_with_llm(candidates, field, tech, detail, gemini_url):
    if not candidates: return []
    papers_text = ""
    for url, data in candidates.items(): papers_text += f"- URL: {url} | Title: {data['title']}\n"

    prompt = f"""
    You are a Universal Senior Research Peer-Reviewer.
    [Research Focus] Domain: {field}, Technology: {tech}, Details: {detail}
    [EVALUATION RULES] 1. CONTEXT IS KING. 2. REJECT (Score 0-6). 3. ACCEPT (Score 7-10).
    Return ONLY a valid JSON array for papers scoring 7 or higher.
    Format: [{{"url": "URL_HERE", "score": 9, "reason": "1문장 요약"}}]
    Papers to evaluate:\n{papers_text}
    """
    
    safety_settings = [{"category": f"HARM_CATEGORY_{cat}", "threshold": "BLOCK_NONE"} for cat in ["HARASSMENT", "HATE_SPEECH", "SEXUALLY_EXPLICIT", "DANGEROUS_CONTENT"]]
    
    try:
        res = requests.post(gemini_url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety_settings}, verify=False, timeout=40)
        res_data = res.json()
        if "candidates" not in res_data: return []
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return extract_json_from_response(raw_text)
    except: return []

# 💡 핵심 수정: 70% 유사도 검증 로직 추가
def crawl_google_news(query, category, existing_urls, existing_titles, existing_summaries, lang="ko"):
    print(f"📰 [{category}] 맞춤형 뉴스 데이터 수집 중... (검색어: {query})")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:7d&hl={'ko&gl=KR&ceid=KR:ko' if lang=='ko' else 'en-US&gl=US&ceid=US:en'}"

    try:
        res = requests.get(rss_url, headers=headers, verify=False, timeout=10)
        feed = feedparser.parse(res.content)
        saved = 0
        today = str(date.today())

        for entry in feed.entries:
            title = entry.title
            link = clean_url(entry.link)
            summary_raw = re.sub('<[^<]+>', '', entry.summary) if 'summary' in entry else "상세 내용은 링크를 참조하세요."
            summary = summary_raw[:100] + "..." if len(summary_raw) > 100 else summary_raw

            if link in existing_urls: continue

            # 🔥 70% 유사도 컷 로직: 제목이나 본문이 70% 이상 일치하면 버림
            is_dup = False
            for i in range(len(existing_titles)):
                if difflib.SequenceMatcher(None, title, existing_titles[i]).ratio() >= 0.7 or \
                   difflib.SequenceMatcher(None, summary, existing_summaries[i]).ratio() >= 0.7:
                    is_dup = True
                    break
            
            if is_dup: continue

            save_article({
                "title": title, "summary": summary, "content": "최신 기사 요약본입니다. 원문 보러가기를 클릭하세요.",
                "source_url": link, "publish_date": today, "category": category
            })
            existing_urls.add(link)
            existing_titles.append(title)
            existing_summaries.append(summary)
            saved += 1
            print(f"  -> 💾 [뉴스 저장] {title[:35]}...")
            
            if saved >= 3: break # 3개 채우면 종료
            
        return saved
    except Exception as e:
        print(f"⚠️ 뉴스 수집 에러: {e}")
        return 0

def run_ultimate_crawler():
    print("🚀 [마스터 아키텍처: 글로벌 70% 중복 컷 동적 크롤러 가동]")
    field = get_setting(2) or ["연구"]
    tech = get_setting(3) or ["기술"]
    detail = get_setting(1) or ["동향"]
    
    main_field = field[0] if field else "연구"
    main_tech = tech[0] if tech else "기술"
    main_detail = detail[0] if detail else "동향"
    
    gemini_dynamic_url = get_best_gemini_url()
    existing_urls, existing_titles, existing_summaries = get_existing_data()
    today = str(date.today())
    
    candidates = fetch_crossref_candidates(field, tech, detail)
    approved_papers = evaluate_papers_with_llm(candidates, field, tech, detail, gemini_dynamic_url)
    
    saved_paper_count = 0
    for p in sorted(approved_papers, key=lambda x: x['score'], reverse=True):
        url = p.get('url')
        if not url or url not in candidates: continue
            
        title = candidates[url]['title']
        clean_url_str = clean_url(url)
        
        if clean_url_str in existing_urls: continue
            
        # 논문 제목도 70% 유사도 검사
        is_dup = False
        for ext_title in existing_titles:
            if difflib.SequenceMatcher(None, title, ext_title).ratio() >= 0.7:
                is_dup = True
                break
        if is_dup: continue
            
        cat = f"[{main_field} 연구]"
        save_article({
            "title": f"{cat} {title}", 
            "summary": f"⭐ [최신연구 AI 심사 {p.get('score', 0)}점] {p.get('reason', '')}",
            "content": "AI 트렌드 분석 논문입니다.", "source_url": clean_url_str, "publish_date": today, "category": "최신연구"
        })
        print(f"  -> 🎯 [합격] 논문 저장: {title[:35]}...")
        existing_urls.add(clean_url_str)
        existing_titles.append(f"{cat} {title}")
        existing_summaries.append("")
        saved_paper_count += 1
        if saved_paper_count >= 5: break
        
    print("-" * 50)
    q_policy = f"{main_field} {main_tech} 동향 OR 정책"
    q_tech = f"{main_tech} {main_detail} 신기술 OR 산업"
    
    # 💡 핵심 수정: 미국 서버(en)에 보낼 때는 한글을 강제로 영어로 치환
    en_field = "livestock OR animal" if "축산" in main_field else ("food OR diet" if "식품" in main_field else "industry")
    en_tech = "smart OR sensor" if "스마트" in main_tech else ("AI" if "인공지능" in main_tech else "technology")
    q_global = f"{en_tech} {en_field} trend OR news"
    
    crawl_google_news(q_policy, "국내동향", existing_urls, existing_titles, existing_summaries, "ko")
    crawl_google_news(q_tech, "기술소식", existing_urls, existing_titles, existing_summaries, "ko")
    crawl_google_news(q_global, "해외트렌드", existing_urls, existing_titles, existing_summaries, "en")
    print("-" * 50)
    
    print("✅ 중복 컷 및 글로벌 언어 치환 크롤링 완벽 종료!")

if __name__ == "__main__":
    run_ultimate_crawler()