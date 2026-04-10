import streamlit as st
import requests
import urllib3
from datetime import date
import os
import time
import re
import difflib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SUPABASE_URL = "https://beaqnrzlnbqxltphfxrc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJlYXFucnpsbmJxeGx0cGhmeHJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwODA3MjgsImV4cCI6MjA5MDY1NjcyOH0.m41O66_yWUFFI_RdP07XxhbrCpnHR9AyNX3jrBkeZSQ"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="NIAS Intelligence Report", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    [data-testid="stSidebar"] .block-container { padding-top: 2.5rem !important; }
    .block-container { padding-top: 3rem !important; padding-bottom: 1rem !important; }
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }

    .vertical-title-container {
        writing-mode: vertical-rl;
        text-orientation: upright;
        padding-right: 5px;
        margin-right: 0px;
        height: 100%;
        min-height: 500px;
        padding-top: 0px;
        text-align: left;
    }
    .t-black { font-size: 1.45rem; font-weight: 800; color: #111; letter-spacing: 0.05rem; display: inline-block; margin-top: 0; }
    .t-blue { font-size: 1.45rem; font-weight: 600; color: #1a73e8; letter-spacing: 0.05rem; display: inline-block; }
    .gap-small { margin-top: 4px; } 

    .summary-box { background: #ffffff; border: 1px solid #eef0f2; border-radius: 12px; padding: 20px; margin-bottom: 15px; min-height: 140px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); transition: all 0.2s ease; }
    .summary-box:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.08); transform: translateY(-3px); border-color: #d2d6da; }
    
    a.news-link { text-decoration: none !important; border-bottom: none !important; display: block; }
    .news-title { font-size: 1.15rem; font-weight: 700; color: #222; margin-bottom: 4px !important; line-height: 1.4; word-break: keep-all; transition: color 0.2s; text-decoration: none !important; border-bottom: none !important; }
    a.news-link:hover .news-title { color: #1a73e8 !important; text-decoration: none !important; border-bottom: none !important; }
    .news-summary { font-size: 0.95rem; font-weight: 400; color: #555; line-height: 1.5; word-break: keep-all; }
    
    .tag { font-size: 0.85rem; font-weight: 700; color: white; background: #1a73e8; padding: 6px 14px; border-radius: 6px; display: inline-block; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(26,115,232,0.3); }
    .issue-info { margin-bottom: 5px; font-size: 0.95rem; color: #777; font-weight: 500; }
    .catchphrase { margin-bottom: 25px; font-size: 0.95rem; color: #1a73e8; font-weight: 600; letter-spacing: -0.02em; }
    
    .weather-btn { background-color: #f4f8ff; padding: 12px 10px; border-radius: 8px; text-align: center; margin-top: 10px; border: 1px solid #e0ebff; cursor: pointer; transition: all 0.2s; text-decoration: none !important; border-bottom: none !important; display: block; }
    .weather-btn:hover { background-color: #e0ebff; transform: translateY(-2px); text-decoration: none !important; border-bottom: none !important; }
    
    .stButton>button { font-weight: 600 !important; }
    
    a.archive-link { text-decoration: none !important; border-bottom: none !important; }
    a.archive-link:hover { color: #1a73e8 !important; text-decoration: none !important; border-bottom: none !important; }
    
    div[data-testid="stPopover"] button {
        min-height: 26px !important;
        height: 26px !important;
        padding: 0px 10px !important;
        margin-top: 6px !important; 
        border-radius: 6px !important;
        border: 1px solid #dce8fa !important;
        background-color: #f8fbff !important;
        width: fit-content !important;
    }
    div[data-testid="stPopover"] button p {
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        color: #1a73e8 !important;
        line-height: 24px !important;
        white-space: nowrap !important; 
    }
    div[data-testid="stPopover"] button:hover {
        background-color: #e0ebff !important;
        border-color: #1a73e8 !important;
    }
    
    div[data-testid="stPopoverBody"] {
        padding: 15px !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        min-width: 320px !important; 
    }

    div[data-testid="stVerticalBlock"]:has(> div.element-container:nth-child(1) .research-base-camp) {
        background-color: #f4f8ff !important;
        border: 1px solid #dce8fa !important;
        border-left: 5px solid #1a73e8 !important;
        border-radius: 12px !important;
        padding: 15px 25px 15px 25px !important; 
        margin-bottom: 25px !important;
    }

    div[data-testid="stVerticalBlock"]:has(> div.element-container:nth-child(1) .main-card-target) p {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div.element-container:nth-child(1) .main-card-target) {
        background-color: #ffffff !important;
        border: 1px solid #eef0f2 !important;
        border-radius: 10px !important;
        padding: 18px 20px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
        margin-bottom: 12px !important;
    }

    div[data-testid="stVerticalBlock"]:has(> div.element-container:nth-child(1) .main-card-target) div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    </style>
    """, unsafe_allow_html=True)

def clean_url(url_str):
    if not url_str: return "#"
    match = re.search(r'(https?://[^\s)\]\'\"]+)', url_str)
    return match.group(1) if match else url_str

def get_unique_items(target_list, reference_list, threshold=0.60):
    ref_titles = [item['title'] for item in reference_list]
    unique_list = []
    for item in target_list:
        is_dup = False
        for ref_title in ref_titles:
            if difflib.SequenceMatcher(None, item['title'], ref_title).ratio() >= threshold:
                is_dup = True
                break
        if not is_dup:
            unique_list.append(item)
            ref_titles.append(item['title'])
    return unique_list

def fetch_all_data():
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/articles?order=publish_date.desc,created_at.desc&limit=500", headers=HEADERS, verify=False, timeout=8)
        return res.json() if res.status_code == 200 else []
    except: return []

def get_setting(id_num, default_val):
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/user_settings?id=eq.{id_num}", headers=HEADERS, verify=False, timeout=8)
        return res.json()[0]['keywords'] if res.status_code == 200 and res.json() else default_val
    except: return default_val

def update_setting(id_num, kw_list):
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/user_settings", headers={**HEADERS, "Prefer": "resolution=merge-duplicates"}, json={"id": id_num, "keywords": kw_list}, verify=False, timeout=8)
    except: pass

@st.dialog("📝 AI 심층 분석 리포트")
def show_details(article):
    st.subheader(article['title'])
    st.divider()
    st.info(article.get('content', article['summary']))
    st.link_button("🌐 논문 원문(Source) 보러가기", clean_url(article.get('source_url', '')), use_container_width=True)

with st.sidebar:
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    else: st.title("NIAS Report")
    
    st.markdown("""
        <a href="https://weather.naver.com/today/14110000" target="_blank" class="weather-btn">
            <div style="font-size: 0.8rem; color: #555; margin-bottom: 4px; font-weight: 600;">📍 전북 전주·완주 기상 상황</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1a73e8;">🌤️ 실시간 날씨 확인하기 👆</div>
        </a>
        <div style='margin-bottom: 15px;'></div>
    """, unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 15px 0px;'>", unsafe_allow_html=True)
    selected_date = st.date_input("📅 리포트 날짜 조회", value=date.today())
    
    if st.button("🔄 맞춤형 AI 취재 및 심사 시작", use_container_width=True):
        with st.spinner("🤖 최근 3개월 연구 동향 및 맞춤 뉴스 수집 중..."):
            try:
                from crawler2 import run_ultimate_crawler
                run_ultimate_crawler()
                st.success("✨ 업데이트 완료!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"오류 발생: {e}")

    st.markdown("<hr style='margin: 15px 0px;'>", unsafe_allow_html=True)
    
    st.subheader("🔭 1단계: 연구 분야 (필수)")
    f_val = get_setting(2, ["축산"])
    new_f = st.text_area("Field", value=", ".join(f_val), height=60, label_visibility="collapsed")
    
    st.subheader("💡 2단계: 관심 기술 (가중치)")
    t_val = get_setting(3, ["스마트", "AI", "ICT", "모니터링"])
    new_t = st.text_area("Tech", value=", ".join(t_val), height=60, label_visibility="collapsed")
    
    st.subheader("🎯 3단계: 상세 키워드 (가중치)")
    k_val = get_setting(1, ["분뇨", "환경", "온실가스"])
    new_k = st.text_area("Keywords", value=", ".join(k_val), height=60, label_visibility="collapsed")
    
    if st.button("✅ 모든 설정 저장 및 반영", use_container_width=True):
        update_setting(2, [x.strip() for x in new_f.split(",") if x.strip()])
        update_setting(3, [x.strip() for x in new_t.split(",") if x.strip()])
        update_setting(1, [x.strip() for x in new_k.split(",") if x.strip()])
        st.success("설정 완료!")
        st.rerun()

col_title, col_content = st.columns([1, 14])

# 💡 동적 UI: 사이드바에서 입력한 키워드를 메인 화면 제목에 반영
main_f = f_val[0] if f_val else "연구"
main_t = t_val[0] if t_val else "기술"

with col_title:
    st.markdown(f'<div class="vertical-title-container"><span class="t-black">농촌진흥청</span><span class="t-blue gap-small">AI연구트렌드리포트</span></div>', unsafe_allow_html=True)

with col_content:
    st.markdown(f'<div class="issue-info">발행일: {selected_date} | AI Intelligence Daily</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="catchphrase">"[{main_f}] 분야의 최근 3개월 연구와 [{main_t}] 트렌드를 AI가 큐레이션합니다."</div>', unsafe_allow_html=True)
    
    all_data = fetch_all_data()
    target_data = [a for a in all_data if a['publish_date'] == str(selected_date)]

    if not all_data:
        st.info("📭 수집된 데이터가 없습니다. 좌측의 [🔄 취재 시작] 버튼을 눌러주세요.")
    else:
        research_news = [a for a in target_data if a.get('category') == "최신연구"]
        all_research = [a for a in all_data if a.get('category') == "최신연구"]
        
        with st.container():
            st.markdown('<div class="research-base-camp"></div>', unsafe_allow_html=True)
            st.markdown('<div class="tag" style="margin-bottom: 15px;">오늘의 AI 심사 통과 연구 자료 (최근 3개월)</div>', unsafe_allow_html=True)
            
            if not research_news:
                st.info("📭 해당 날짜의 논문 데이터가 없습니다.")
            else:
                top_papers = research_news[:2]
                leftover_today = research_news[2:]

                for i, top in enumerate(top_papers):
                    clean_title = top["title"]
                    clean_title = re.sub(r'\[.*?연구\]', '', clean_title).strip()

                    with st.container():
                        st.markdown('<div class="main-card-target"></div>', unsafe_allow_html=True)
                        c_txt, c_btn = st.columns([8.2, 1.8]) 
                        with c_txt:
                            st.markdown(f'<div class="news-title">{clean_title}</div><div class="news-summary" style="font-size:0.95rem; color:#555;">{top["summary"]}</div>', unsafe_allow_html=True)
                        with c_btn:
                            if st.button("🔍 리포트 보기", key=f"main_btn_{i}", use_container_width=True): show_details(top)
                
                leftovers_raw = leftover_today + [a for a in all_research if a not in research_news]
                leftovers = get_unique_items(leftovers_raw, top_papers, threshold=0.60)
                
                if len(leftovers) > 0:
                    pop_col1, pop_col2, _ = st.columns([1.6, 1.5, 6.9], gap="small") 
                    with pop_col1:
                        with st.popover(f"➕ 추가 연구 리스트 ({min(len(leftovers), 3)}건)"):
                            st.markdown("<div style='font-weight:700; margin-bottom:12px; color:#1a73e8;'>오늘의 추가 연구 논문</div>", unsafe_allow_html=True)
                            for i, extra in enumerate(leftovers[:3]):
                                e_title = re.sub(r'\[.*?연구\]', '', extra["title"]).strip()
                                c_left, c_right = st.columns([7.5, 2.5])
                                with c_left: 
                                    st.markdown(f'<div class="sub-research-card" style="padding: 12px; margin-bottom: 8px;"><div style="font-size: 0.95rem; font-weight: 600; color: #222; margin-bottom: 4px; line-height: 1.3;">{e_title}</div><div style="font-size: 0.85rem; color: #666; line-height: 1.3;">{extra["summary"][:60]}...</div></div>', unsafe_allow_html=True)
                                with c_right:
                                    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
                                    if st.button("🔍 보기", key=f"extra_btn_{i}", use_container_width=True): show_details(extra)
                    with pop_col2:
                        if len(leftovers) > 3:
                            with st.popover("📂 연구자료 저장소 (이전)"):
                                st.markdown("<div style='font-weight:700; margin-bottom:12px; color:#1a73e8;'>누적된 이전 연구 자료 아카이브</div>", unsafe_allow_html=True)
                                for archive in leftovers[3:]:
                                    a_title = re.sub(r'\[.*?연구\]', '', archive["title"]).strip()
                                    st.markdown(f"<div style='margin-bottom: 10px; font-size: 0.9rem; line-height: 1.4;'>🔗 <a href='{clean_url(archive.get('source_url', ''))}' target='_blank' class='archive-link' style='color: #444;'>{a_title}</a></div>", unsafe_allow_html=True)

        # 💡 하위 섹션 카테고리 태그 변경 (국내동향, 기술소식, 해외트렌드)
        all_policy = [a for a in all_data if a.get('category') == "국내동향"]
        today_policy = [a for a in target_data if a.get('category') == "국내동향"]
        main_policy = today_policy.copy()
        for p in all_policy:
            if len(main_policy) >= 3: break
            if p not in main_policy: main_policy.append(p)
        past_policy = get_unique_items([a for a in all_policy if a not in main_policy], main_policy, threshold=0.60)

        all_smart = [a for a in all_data if a.get('category') == "기술소식"]
        today_smart = [a for a in target_data if a.get('category') == "기술소식"]
        main_smart = today_smart.copy()
        for p in all_smart:
            if len(main_smart) >= 2: break
            if p not in main_smart: main_smart.append(p)
        past_smart = get_unique_items([a for a in all_smart if a not in main_smart], main_smart, threshold=0.60)

        all_global = [a for a in all_data if a.get('category') == "해외트렌드"]
        today_global = [a for a in target_data if a.get('category') == "해외트렌드"]
        main_global = today_global.copy()
        for p in all_global:
            if len(main_global) >= 2: break
            if p not in main_global: main_global.append(p)
        past_global = get_unique_items([a for a in all_global if a not in main_global], main_global, threshold=0.60)

        c1, c2, c3 = st.columns(3)
        
        with c1:
            h_col1, h_col2 = st.columns([7, 3])
            # 동적 UI 반영
            h_col1.markdown(f"<div style='font-size: 1.05rem; font-weight: 700; color: #222; margin-top: 8px; margin-bottom: 10px;'>📢 {main_f} 국내 동향</div>", unsafe_allow_html=True)
            with h_col2:
                if past_policy:
                    with st.popover("➕ 더 보기"):
                        for a in past_policy[:3]: st.markdown(f"<div style='margin-bottom: 10px; font-size: 0.85rem; line-height: 1.4;'>🔗 <a href='{clean_url(a.get('source_url', ''))}' target='_blank' class='archive-link' style='color: #444;'>{a['title']}</a></div>", unsafe_allow_html=True)
            for a in main_policy:
                st.markdown(f'<div class="summary-box"><a href="{clean_url(a.get("source_url", ""))}" target="_blank" class="news-link"><div class="news-title">{a["title"]}</div></a><div class="news-summary">{a["summary"]}</div></div>', unsafe_allow_html=True)

        with c2:
            h_col1, h_col2 = st.columns([7, 3])
            # 동적 UI 반영
            h_col1.markdown(f"<div style='font-size: 1.05rem; font-weight: 700; color: #222; margin-top: 8px; margin-bottom: 10px;'>📡 {main_t} 기술 뉴스</div>", unsafe_allow_html=True)
            with h_col2:
                if past_smart:
                    with st.popover("➕ 더 보기"):
                        for a in past_smart[:3]: st.markdown(f"<div style='margin-bottom: 10px; font-size: 0.85rem; line-height: 1.4;'>🔗 <a href='{clean_url(a.get('source_url', ''))}' target='_blank' class='archive-link' style='color: #444;'>{a['title']}</a></div>", unsafe_allow_html=True)
            for a in main_smart:
                st.markdown(f'<div class="summary-box"><a href="{clean_url(a.get("source_url", ""))}" target="_blank" class="news-link"><div class="news-title">{a["title"]}</div></a><div class="news-summary">{a["summary"]}</div></div>', unsafe_allow_html=True)

        with c3:
            h_col1, h_col2 = st.columns([7, 3])
            # 동적 UI 반영
            h_col1.markdown(f"<div style='font-size: 1.05rem; font-weight: 700; color: #222; margin-top: 8px; margin-bottom: 10px;'>🌎 글로벌 {main_f} 트렌드</div>", unsafe_allow_html=True)
            with h_col2:
                if past_global:
                    with st.popover("➕ 더 보기"):
                        for a in past_global[:3]: st.markdown(f"<div style='margin-bottom: 10px; font-size: 0.85rem; line-height: 1.4;'>🔗 <a href='{clean_url(a.get('source_url', ''))}' target='_blank' class='archive-link' style='color: #444;'>{a['title']}</a></div>", unsafe_allow_html=True)
            for a in main_global:
                st.markdown(f'<div class="summary-box"><a href="{clean_url(a.get("source_url", ""))}" target="_blank" class="news-link"><div class="news-title">{a["title"]}</div></a><div class="news-summary">{a["summary"]}</div></div>', unsafe_allow_html=True)