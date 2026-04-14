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

st.set_page_config(page_title="NIAS AI Investigator", layout="wide", page_icon="🕵️‍♂️")

if 'page_view' not in st.session_state:
    st.session_state.page_view = "main"
if 'saved_papers' not in st.session_state:
    st.session_state.saved_papers = {}
if 'saved_news' not in st.session_state:
    st.session_state.saved_news = {}

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
    
    [data-testid="stSidebar"] .block-container { padding-top: 3.5rem !important; }
    .block-container { padding-top: 3.5rem !important; padding-bottom: 1rem !important; }

    .main-header { font-size: 1.8rem; font-weight: 800; color: #111; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.1rem; font-weight: 600; color: #1a73e8; margin-bottom: 0rem; }
    
    div[data-testid="stTabs"] { margin-top: -45px; }
    div[data-testid="stHorizontalBlock"] { position: relative; z-index: 10; }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f8f9fa; border-radius: 8px 8px 0 0; padding-top: 8px; padding-bottom: 8px; font-weight: 700; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #1a73e8 !important; }

    a.paper-link { text-decoration: none !important; display: block; }
    
    .paper-box, .news-box { background: #ffffff; border: 1px solid #eef0f2; border-radius: 10px; padding: 15px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); transition: all 0.2s ease; margin-bottom: 0px; }
    .paper-box:hover, .news-box:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: #d2d6da; }
    .paper-title, .news-title-text { font-size: 1.1rem; font-weight: 700; color: #222; margin-bottom: 6px; line-height: 1.4; transition: color 0.2s ease; }
    a.paper-link:hover .paper-title, a.paper-link:hover .news-title-text { color: #1a73e8; text-decoration: underline; }
    .paper-summary { font-size: 0.95rem; color: #555; line-height: 1.5; word-break: keep-all; }
    
    .section-title { font-size: 1.1rem; font-weight: 800; color: #222; margin-bottom: 15px; padding-left: 5px; border-left: 4px solid #1a73e8; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

def clean_url(url_str):
    if not url_str: return "#"
    match = re.search(r'(https?://[^\s)\]\'\"]+)', url_str)
    return match.group(1) if match else url_str

def fetch_all_data():
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/articles?order=created_at.desc&limit=200", headers=HEADERS, verify=False, timeout=8)
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

with st.sidebar:
    st.title("🕵️‍♂️ AI Investigator")
    if st.button("🚀 AI 조사관 파견", use_container_width=True):
        with st.spinner("🕵️‍♂️ AI 조사관이 전 세계 학술망과 뉴스를 탐색 중입니다..."):
            try:
                from crawler2 import run_ultimate_crawler
                run_ultimate_crawler()
                st.success("✨ 조사가 완료되었습니다!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"오류 발생: {e}")

    st.markdown("<hr style='margin: 15px 0px;'>", unsafe_allow_html=True)
    
    # 💡 박사님의 원래 명칭으로 완벽하게 복구했습니다.
    st.subheader("🔭 연구 분야")
    f_val = get_setting(2, ["축산"])
    new_f = st.text_area("Field", value=", ".join(f_val), height=60, label_visibility="collapsed")
    
    st.subheader("💡 관심 기술")
    t_val = get_setting(3, ["인공지능", "ICT", "모니터링"])
    new_t = st.text_area("Tech", value=", ".join(t_val), height=60, label_visibility="collapsed")
    
    st.subheader("🎯 상세 키워드")
    k_val = get_setting(1, ["냄새"])
    new_k = st.text_area("Keywords", value=", ".join(k_val), height=60, label_visibility="collapsed")
    
    # 💡 버튼 이름도 통일감 있게 맞췄습니다.
    if st.button("✅ 연구 지침 업데이트", use_container_width=True):
        update_setting(2, [x.strip() for x in new_f.split(",") if x.strip()])
        update_setting(3, [x.strip() for x in new_t.split(",") if x.strip()])
        update_setting(1, [x.strip() for x in new_k.split(",") if x.strip()])
        st.success("지침이 저장되었습니다!")
        st.rerun()

all_data = fetch_all_data()
main_f = f_val[0] if f_val else "연구"
main_t = t_val[0] if t_val else "기술"

if st.session_state.page_view == "main":
    st.markdown('<div class="main-header">농촌진흥청 AI 연구 트렌드 조사관</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">AI 조사관이 [{main_f}] 분야의 최근 논문과 [{main_t}] 트렌드를 집중 조사합니다.</div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    col_spacer, col_btn1, col_btn2 = st.columns([7.4, 1.3, 1.3], gap="small")
    with col_btn1:
        if st.button("📂 논문 보관함", type="primary", use_container_width=True):
            st.session_state.page_view = "paper_archive"
            st.rerun()
    with col_btn2:
        if st.button("📂 뉴스 보관함", type="primary", use_container_width=True):
            st.session_state.page_view = "news_archive"
            st.rerun()

    tab_paper, tab_news = st.tabs(["📄 학술 논문", "📰 보도 자료"])

    with tab_paper:
        research_papers = [a for a in all_data if a.get('category') == "최신연구"]
        if not research_papers:
            st.info("🕵️‍♂️ 수집된 논문 자료가 없습니다. 왼쪽의 'AI 조사관 파견' 버튼을 클릭해 주세요.")
        else:
            for i, paper in enumerate(research_papers[:15]):
                clean_title = re.sub(r'\[.*?연구\]', '', paper["title"]).strip()
                url = clean_url(paper.get('source_url', ''))
                
                col_content, col_btn = st.columns([8.8, 1.2], vertical_alignment="center")
                with col_content:
                    st.markdown(f'<div class="paper-box"><a href="{url}" target="_blank" class="paper-link"><div class="paper-title">{clean_title}</div></a><div class="paper-summary">{paper.get("summary", "")}</div></div>', unsafe_allow_html=True)
                with col_btn:
                    if url in st.session_state.saved_papers: st.button("✅ 보관완료", key=f"main_p_saved_{i}", disabled=True)
                    else:
                        if st.button("🔖 보관하기", key=f"main_p_save_{i}"):
                            st.session_state.saved_papers[url] = paper
                            st.rerun()
                st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    with tab_news:
        policy_news = [a for a in all_data if a.get('category') == "국내동향"]
        tech_news = [a for a in all_data if a.get('category') == "기술소식"]
        global_news = [a for a in all_data if a.get('category') == "해외트렌드"]
        
        col1, col2, col3 = st.columns(3)
        
        def render_news_column(news_list, col_obj, section_title, key_prefix):
            with col_obj:
                st.markdown(f'<div class="section-title">{section_title}</div>', unsafe_allow_html=True)
                for i, news in enumerate(news_list[:15]):
                    url = clean_url(news.get('source_url', ''))
                    sub_col_content, sub_col_btn = st.columns([7.5, 2.5], vertical_alignment="center")
                    with sub_col_content:
                        st.markdown(f'<div class="news-box"><a href="{url}" target="_blank" class="paper-link"><div class="news-title-text">{news["title"]}</div></a></div>', unsafe_allow_html=True)
                    with sub_col_btn:
                        if url in st.session_state.saved_news: st.button("✅ 완료", key=f"{key_prefix}_saved_{i}", disabled=True)
                        else:
                            if st.button("🔖 보관", key=f"{key_prefix}_save_{i}"):
                                st.session_state.saved_news[url] = news
                                st.rerun()
                    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

        render_news_column(policy_news, col1, "📢 국내 정책 및 동향", "pol")
        render_news_column(tech_news, col2, "📡 축산 인공지능 소식", "tech")
        render_news_column(global_news, col3, "🌎 글로벌 트렌드", "glob")

elif st.session_state.page_view == "paper_archive":
    col_header, col_btn = st.columns([8, 2])
    with col_header:
        st.markdown('<div class="main-header">📂 논문자료 보관함</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">내가 스크랩한 핵심 연구 논문 리스트입니다.</div>', unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        if st.button("◀ 대시보드로 돌아가기", use_container_width=True):
            st.session_state.page_view = "main"
            st.rerun()
    st.divider()

    saved_papers = list(st.session_state.saved_papers.values())
    if not saved_papers:
        st.info("비어 있습니다. 대시보드에서 유용한 논문을 보관함에 저장해 보세요.")
    else:
        for i, paper in enumerate(saved_papers):
            clean_title = re.sub(r'\[.*?연구\]', '', paper["title"]).strip()
            url = clean_url(paper.get('source_url', ''))
            col_content, col_btn = st.columns([8.8, 1.2], vertical_alignment="center")
            with col_content:
                st.markdown(f'<div class="paper-box"><a href="{url}" target="_blank" class="paper-link"><div class="paper-title">{clean_title}</div></a><div class="paper-summary">{paper.get("summary", "")}</div></div>', unsafe_allow_html=True)
            with col_btn:
                if st.button("🗑️ 삭제하기", key=f"del_p_{i}"):
                    del st.session_state.saved_papers[url]
                    st.rerun()
            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

elif st.session_state.page_view == "news_archive":
    col_header, col_btn = st.columns([8, 2])
    with col_header:
        st.markdown('<div class="main-header">📂 보도자료 보관함</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">스크랩한 주요 동향 및 기술 뉴스를 섹션별로 확인하세요.</div>', unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        if st.button("◀ 대시보드로 돌아가기", use_container_width=True):
            st.session_state.page_view = "main"
            st.rerun()
    st.divider()

    saved_news_list = list(st.session_state.saved_news.values())
    if not saved_news_list:
        st.info("비어 있습니다. 대시보드에서 중요한 뉴스를 보관함에 저장해 보세요.")
    else:
        archived_policy = [n for n in saved_news_list if n.get('category') == "국내동향"]
        archived_tech = [n for n in saved_news_list if n.get('category') == "기술소식"]
        archived_global = [n for n in saved_news_list if n.get('category') == "해외트렌드"]
        
        col1, col2, col3 = st.columns(3)
        def render_archived_news(news_list, col_obj, section_title, key_prefix):
            with col_obj:
                st.markdown(f'<div class="section-title">{section_title}</div>', unsafe_allow_html=True)
                if not news_list: st.caption("저장된 자료가 없습니다.")
                for i, news in enumerate(news_list):
                    url = clean_url(news.get('source_url', ''))
                    sub_col_content, sub_col_btn = st.columns([7.5, 2.5], vertical_alignment="center")
                    with sub_col_content:
                        st.markdown(f'<div class="news-box"><a href="{url}" target="_blank" class="paper-link"><div class="news-title-text">{news["title"]}</div></a></div>', unsafe_allow_html=True)
                    with sub_col_btn:
                        if st.button("🗑️ 삭제", key=f"del_{key_prefix}_{i}"):
                            del st.session_state.saved_news[url]
                            st.rerun()
                    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

        render_archived_news(archived_policy, col1, "📢 국내 정책 및 동향", "pol")
        render_archived_news(archived_tech, col2, "📡 축산 인공지능 소식", "tech")
        render_archived_news(archived_global, col3, "🌎 글로벌 트렌드", "glob")
