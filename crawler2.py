import requests
import json
import urllib3
import urllib.parse
from datetime import date, datetime, timedelta
import time
import re
import difflib  # 💡 문자열 유사도 검사 라이브러리
import feedparser

# SSL 경고 숨김
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SUPABASE_URL = "https://beaqnrzlnbqxltphfxrc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJlYXFucnpsbmJxeGx0cGhmeHJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwODA3MjgsImV4cCI6MjA5MDY1NjcyOH0.m41O66_yWUFFI_RdP07XxhbrCpnHR9AyNX3jrBkeZSQ"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

GEMINI_API_KEY = "AIzaSyBVXU9iuezo_0aP_0loz0ltZgdayvML07U"
WORKING_MODEL = None

def clean_url(url_str):
    if not url_str: return "#"
    match = re.search(r'(https?://[^\s)\]\'\"]+)', url_str)
    return match.group(1) if match else url_str

def get_setting(id_num):
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/user_settings?id=eq.{id_num}", headers=HEADERS, verify=False, timeout=8)
        if res.status_code == 200 and res.json(): return res.json()[0]['keywords']
    except: pass
    return []

def get_existing_data():
    url = f"{SUPABASE_URL}/rest/v1/articles?select=source_url,title,summary&limit=1000"
    try:
        res = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return set(item['source_url'] for item in data), [item['title'] for item in data], [item.get('summary', '') for item in data]
    except: pass
    return set(), [], []

def save_article(article):
    requests.post(f"{SUPABASE_URL}/rest/v1/articles", headers=HEADERS, json=article, verify=False)

def call_gemini_with_retry(prompt_text):
    global WORKING_MODEL
    models_to_try = ["gemini-3.0-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
    if WORKING_MODEL: models_to_try = [WORKING_MODEL]
        
    safety_settings = [{"category": f"HARM_CATEGORY_{cat}", "threshold": "BLOCK_NONE"} for cat in ["HARASSMENT", "HATE_SPEECH", "SEXUALLY_EXPLICIT", "DANGEROUS_CONTENT"]]
    payload = {"contents": [{"parts": [{"text": prompt_text}]}], "safetySettings": safety_settings}

    last_error_detail = ""
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(url, json=payload, verify=False, timeout=90) 
            if res.status_code == 200:
                if not WORKING_MODEL:
                    print(f"  -> ✅ [마스터 키 확인 완료] 쌩쌩한 최신 AI 모델({model}) 연결 성공!")
                    WORKING_MODEL = model
                return res.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                last_error_detail = f"상태코드 {res.status_code} | {res.text}"
                print(f"  -> 🔍 [{model}] 접속 거부: {res.status_code}")
        except Exception as e:
            last_error_detail = str(e)
            print(f"  -> 🔍 [{model}] 통신 에러: {e}")
            
    raise ValueError(f"모든 AI 모델 접속 실패. 에러 원인: {last_error_detail}")

def translate_keywords_via_llm(field, tech, detail):
    print("🤖 AI 조사관이 해외 검색을 위해 키워드를 학술 영문으로 번역 중입니다...")
    f_str = ", ".join(field) if field else "연구"
    t_str = ", ".join(tech) if tech else "기술"
    d_str = ", ".join(detail) if detail else "동향"

    prompt = f"""
    Translate the following Korean research keywords into English academic search terms.
    Keywords: Field: {f_str}, Tech: {t_str}, Details: {d_str}
    Return ONLY a JSON object: {{"field_en": "...", "tech_en": "...", "detail_en": "..."}}
    """
    try:
        raw_text = call_gemini_with_retry(prompt)
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        translated = json.loads(json_match.group(0)) if json_match else json.loads(raw_text)
        print(f"  -> 🔤 번역 성공: {translated}")
        return translated
    except Exception as e:
        print("비상용 백업 키워드로 전환합니다.")
        return {"field_en": "livestock", "tech_en": "AI", "detail_en": "odor"}

def fetch_crossref_candidates(field_en, tech_en, detail_en):
    print("⚙️ 1단계: 글로벌 학술망(Crossref)에서 최신 논문 스캔 중...")
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    query = f"{field_en} {tech_en} {detail_en}"
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={encoded_query}&rows=60&filter=from-pub-date:{three_months_ago}"
    
    try:
        res = requests.get(url, timeout=15, verify=False)
        items = res.json().get("message", {}).get("items", [])
        candidates = {}
        for item in items:
            title = item.get("title", [""])[0]
            url = item.get("URL", "")
            if title and url: candidates[url] = {"title": title, "url": url}
        print(f"  -> {len(candidates)}개의 영문 논문 후보 스캔 완료.")
        return candidates
    except: return {}

def evaluate_papers_with_llm(candidates, field, tech, detail):
    if not candidates: return []
    print(f"🤖 2단계: AI 조사관이 최정예 논문 15개를 선별 중입니다... (최대 1분 정도 소요될 수 있습니다)")
    papers_text = ""
    for url, data in candidates.items(): papers_text += f"- Title: {data['title']} (URL: {url})\n"

    prompt = f"""
    Identify papers related to: Domain({field}), Tech({tech}), Detail({detail}).
    Evaluate context. Return top relevant papers (Score 7-10) as JSON array.
    Format: [{{"url": "...", "score": 10, "reason": "한글 요약"}}]
    List:\n{papers_text}
    """
    try:
        raw_text = call_gemini_with_retry(prompt)
        json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        return json.loads(json_match.group(0)) if json_match else []
    except Exception as e: 
        return []

def crawl_google_news(query, category, existing_urls, existing_titles, lang="ko"):
    print(f"📰 [{category}] 뉴스 수집 중... ({query})")
    headers = {'User-Agent': 'Mozilla/5.0'}
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:7d&hl={'ko&gl=KR&ceid=KR:ko' if lang=='ko' else 'en-US&gl=US&ceid=US:en'}"

    try:
        res = requests.get(rss_url, headers=headers, verify=False, timeout=10)
        feed = feedparser.parse(res.content)
        saved = 0
        today = str(date.today())
        
        for entry in feed.entries:
            title = entry.title
            link = clean_url(entry.link)
            
            # [1차 방어] URL 완전 일치 검사
            if link in existing_urls: continue
            
            # 💡 [2차 방어] 제목 유사도 검사 (60% 이상 일치하면 복붙 기사로 간주하고 버림)
            is_duplicate = False
            for ex_title in existing_titles:
                similarity = difflib.SequenceMatcher(None, title, ex_title).ratio()
                if similarity > 0.6:
                    is_duplicate = True
                    break
            if is_duplicate: continue
            
            # 방어막을 뚫은 진짜 새로운 기사만 저장
            save_article({"title": title, "summary": title[:100], "source_url": link, "publish_date": today, "category": category})
            existing_urls.add(link)
            existing_titles.append(title) # 다음 기사 검사를 위해 기억 장부에 추가
            saved += 1
            if saved >= 10: break
        return saved
    except: return 0

def run_ultimate_crawler():
    field = get_setting(2) or ["축산"]
    tech = get_setting(3) or ["인공지능"]
    detail = get_setting(1) or ["냄새"]
    
    print(f"🚀 [조사 시작] 분야: {field} | 기술: {tech}")
    existing_urls, existing_titles, _ = get_existing_data()
    today = str(date.today())
    
    en_terms = translate_keywords_via_llm(field, tech, detail)
    candidates = fetch_crossref_candidates(en_terms['field_en'], en_terms['tech_en'], en_terms['detail_en'])
    approved_papers = evaluate_papers_with_llm(candidates, field, tech, detail)
    
    saved_count = 0
    for p in sorted(approved_papers, key=lambda x: x.get('score', 0), reverse=True):
        url = p.get('url')
        if not url or clean_url(url) in existing_urls: continue
        title = candidates.get(url, {}).get('title', 'Unknown Paper')
        
        save_article({
            "title": f"[{field[0]} 연구] {title}", 
            "summary": f"⭐ [AI 리포트] {p.get('reason')}",
            "source_url": clean_url(url), "publish_date": today, "category": "최신연구"
        })
        saved_count += 1
        print(f"  -> 🎯 논문 저장: {title[:35]}...")
        if saved_count >= 15: break
        
    print("-" * 50)
    q_ko = f'"{field[0]}" {tech[0]} {detail[0]}'
    q_en = f'"{en_terms["field_en"]}" {en_terms["tech_en"]}'
    
    crawl_google_news(q_ko, "국내동향", existing_urls, existing_titles, "ko")
    crawl_google_news(q_ko, "기술소식", existing_urls, existing_titles, "ko")
    crawl_google_news(q_en, "해외트렌드", existing_urls, existing_titles, "en")
    print(f"✅ 조사 완료 (논문 {saved_count}건 수집)")

if __name__ == "__main__":
    run_ultimate_crawler()
