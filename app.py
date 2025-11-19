# app.py
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from agents.paper_agent import PaperAgent
from tools.paper_summarize_tool import PaperSummarizeTool
from tools.library_tool import add_to_library, load_library, clear_library
from tools.bibtex_tool import (
    export_bibtex_string,
    ieee_reference_from_paper,
    make_bibtex_entry,
)
from tools.code_search_tool import CodeSearchTool

# ---------------- 기본 설정 ----------------
st.set_page_config(page_title="📚 Paper Search Agent", layout="wide")
st.title("📚 Paper Search Agent")

# ---------------- 세션 상태 ----------------
def _ensure_state():
    if "mode" not in st.session_state:
        st.session_state.mode = "검색"  # "검색" | "라이브러리"
    if "results" not in st.session_state:
        st.session_state.results = []
    if "last_query" not in st.session_state:
        st.session_state.last_query = {}
    if "summary_lang" not in st.session_state:
        st.session_state.summary_lang = "ko"  # ko/en/ja
    if "debug" not in st.session_state:
        st.session_state.debug = False

_ensure_state()

# ---------------- 에이전트/툴 ----------------
agent = PaperAgent()           
summ_tool = PaperSummarizeTool()
code_tool = CodeSearchTool()

# ---------------- 사이드바 ----------------
with st.sidebar:
    st.subheader("📚 내 라이브러리")
    lib = load_library()
    st.write(f"{len(lib)}개 저장됨")

    if st.button("라이브러리 열기"):
        st.session_state.mode = "라이브러리"

    st.divider()
    st.subheader("🗣️ 요약 언어")
    st.session_state.summary_lang = st.selectbox(
        "언어 선택", ["ko", "en", "ja"],
        index=["ko", "en", "ja"].index(st.session_state.summary_lang)
    )
    st.caption("요약 버튼 클릭 시 적용")

    st.divider()
    st.subheader("🛠️ 개발자 옵션")
    st.session_state.debug = st.toggle("디버그 로그 보기", value=st.session_state.debug)

# ---------------- 화면 전환: 라이브러리 ----------------
if st.session_state.mode == "라이브러리":
    st.header("📚 내 라이브러리")

    lib = load_library()
    if not lib:
        st.info("저장된 항목이 없습니다. 검색 화면에서 '라이브러리에 저장'을 눌러보세요.")
        if st.button("검색으로 돌아가기"):
            st.session_state.mode = "검색"
        st.stop()

    df = pd.DataFrame(lib)[["title", "authors", "year", "citations", "doi", "url"]]
    st.dataframe(df, use_container_width=True, hide_index=True)

    bibtex_str = export_bibtex_string(lib)
    st.download_button(
        "BibTeX 다운로드",
        bibtex_str.encode("utf-8"),
        file_name="my_library.bib",
        mime="text/plain",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("검색으로 돌아가기"):
            st.session_state.mode = "검색"
    with col2:
        if st.button("라이브러리 비우기", type="primary"):
            clear_library()
            st.success("라이브러리를 비웠습니다.")
            st.rerun()
    st.stop()

# ---------------- 화면: 검색 ----------------
with st.form("search_form"):
    query = st.text_input("검색 키워드", placeholder="예: diffusion model")
    venue = st.text_input("저널 또는 컨퍼런스명 (선택)", placeholder="예: NeurIPS, Nature, ICML, CVPR")

    col1, col2, col3 = st.columns(3)
    with col1:
        year_from = st.number_input("시작 연도", min_value=1900, max_value=2100, value=2020)
    with col2:
        year_to = st.number_input("끝 연도", min_value=1900, max_value=2100, value=2025)
    with col3:
        min_citations = st.number_input("최소 인용 수", min_value=0, value=50)

    submitted = st.form_submit_button("검색")

# ---------------- 유틸 (영어 전용, 대소문자 무시) ----------------
def _normalize_venue(v: str) -> str:
    return (v or "").strip().lower()

def _alias_candidates(v: str) -> List[str]:
    """
    유명 저널/컨퍼런스의 약어/정식명 별칭 후보를 반환.
    영어 전용, 대소문자 무시(lower)로 처리.
    """
    v = _normalize_venue(v)
    aliases: Dict[str, List[str]] = {
        # Top ML/AI conferences
        "neurips": [
            "neurips", "nips",
            "neural information processing systems",
            "advances in neural information processing systems",
        ],
        "icml": ["icml", "international conference on machine learning"],
        "iclr": ["iclr", "international conference on learning representations", "learning representations"],
        "aaai": ["aaai", "association for the advancement of artificial intelligence"],
        "kdd": ["kdd", "sigkdd", "knowledge discovery and data mining"],
        "uai": ["uai", "uncertainty in artificial intelligence"],
        # Vision
        "cvpr": ["cvpr", "computer vision and pattern recognition"],
        "iccv": ["iccv", "international conference on computer vision"],
        "eccv": ["eccv", "european conference on computer vision"],
        "wacv": ["wacv"],
        # NLP
        "acl": ["acl", "association for computational linguistics"],
        "emnlp": ["emnlp", "empirical methods in natural language processing"],
        "naacl": ["naacl"],
        "coling": ["coling", "computational linguistics"],
        # IR / Data
        "sigir": ["sigir", "information retrieval"],
        "www": ["www", "the web conference", "international world wide web conference"],
        # Journals
        "jmlr": ["jmlr", "journal of machine learning research"],
        "tmlr": ["tmlr", "transactions on machine learning research"],
        "tpami": ["tpami", "transactions on pattern analysis and machine intelligence"],
        "tacl": ["tacl", "transactions of the association for computational linguistics"],
        "nature": ["nature"],
        "science": ["science"],
        "cell": ["cell"],
        "pnas": ["pnas", "proceedings of the national academy of sciences"],
        # Workshops (예시)
        "neurips workshop": ["neurips workshop"],
    }
    for key, vals in aliases.items():
        if v == key:
            return vals
    return [v] if v else []

def _matches_any_venue(paper: Dict[str, Any], candidates: List[str]) -> bool:
    venue_text = ((paper.get("venue_all") or paper.get("venue") or "")).lower()
    return any(c and c in venue_text for c in candidates)

# ---------------- 검색 실행 ----------------
if submitted and query:
    with st.spinner("논문 검색 중..."):
        # 1차: 기본 검색
        raw_results = agent.run(
            instruction=query,
            year_from=year_from,
            year_to=year_to,
            min_citations=min_citations,
            venue=venue,
            max_results=8,
        ) or []

        results = raw_results

        # 2차: venue 별칭 확장 필터
        if venue and results:
            cand = _alias_candidates(venue)
            filtered = [r for r in results if _matches_any_venue(r, cand)] if cand else results
            if filtered:  # 0건 되면 너무 빡빡하니까 원본 유지
                results = filtered

        # 3차: venue 지정 + 0건 -> venue 없이 폴백
        if venue and _normalize_venue(venue) and len(results) == 0:
            st.warning(f"**‘{venue}’**로 매칭된 결과가 없어, 저널/컨퍼런스 미지정으로 다시 검색한 결과를 보여줍니다.")
            results = agent.run(
                instruction=query,
                year_from=year_from,
                year_to=year_to,
                min_citations=min_citations,
                venue=None,
                max_results=8,
            ) or []

        # 세션 저장
        st.session_state.results = results
        st.session_state.last_query = {
            "query": query,
            "year_from": year_from,
            "year_to": year_to,
            "min_citations": min_citations,
            "venue": venue,
        }

# ---------------- 결과 렌더 ----------------
results = st.session_state.results

if st.session_state.debug:
    st.caption("🔎 last_query:")
    st.json(st.session_state.last_query)
    st.caption("📦 results_count:")
    st.write(len(results))


def _make_ieee_citation(paper: Dict[str, Any], index: int | None = None) -> str:
    """간단 IEEE 스타일 참고문헌 문자열."""
    authors = paper.get("authors", "").rstrip(".")
    title = paper.get("title", "(제목 없음)")
    venue = paper.get("venue") or "arXiv.org"
    year = paper.get("year") or "n.d."
    doi = paper.get("doi") or ""

    base = f'{authors}, "{title}", {venue}, {year}'
    if doi:
        base += f", doi: {doi}"
    base += "."
    if index is not None:
        base = f"[{index}] " + base
    return base


def _make_bibtex_entry(paper: Dict[str, Any]) -> str:
    """간단 BibTeX 엔트리."""
    title = paper.get("title", "").replace("{", "").replace("}", "")
    authors_str = paper.get("authors", "")
    year = paper.get("year") or "2024"
    venue = paper.get("venue") or "arXiv.org"
    doi = paper.get("doi")
    url = paper.get("url")

    authors_parts = [a.strip() for a in authors_str.split(",") if a.strip()]
    authors_bib = " and ".join(authors_parts) if authors_parts else "Unknown"
    key = f"{authors_parts[0].split()[-1].lower() if authors_parts else 'paper'}{year}"

    lines = [
        f"@article{{{key},",
        f"  title   = {{{title}}},",
        f"  author  = {{{authors_bib}}},",
        f"  year    = {{{year}}},",
        f"  journal = {{{venue}}},",
    ]
    if doi:
        lines.append(f"  doi     = {{{doi}}},")
    if url:
        lines.append(f"  url     = {{{url}}},")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


if results:
    st.subheader("검색 결과")
    for idx, paper in enumerate(results, 1):
        with st.container(border=True):
            # ---------- 기본 정보 ----------
            st.markdown(f"**{idx}. {paper.get('title','(제목 없음)')}**")
            st.caption(
                f"{paper.get('authors','')} · {paper.get('year','?')} · "
                f"cites: {paper.get('citations','-')} · venue: {paper.get('venue','N/A')}"
            )

            if paper.get("doi"):
                st.write(f"DOI: {paper['doi']}")
            if paper.get("url"):
                st.write(f"[링크 열기]({paper['url']})")
            if paper.get("pdf"):
                st.markdown(f"[PDF]({paper['pdf']})")

            # ---------- 초록 ----------
            abstract_text = paper.get("abstract", "")
            if abstract_text:
                with st.expander("초록 보기"):
                    st.write(abstract_text)

            st.markdown("---")

            # 세션 키 (값 보관용)
            sum_key = f"summary_text_{idx}"
            contrib_key = f"contrib_text_{idx}"
            weak_key = f"weak_text_{idx}"
            sw_key = f"sw_text_{idx}"
            ieee_key = f"ieee_text_{idx}"
            bibtex_key = f"bibtex_text_{idx}"
            code_key = f"code_results_{idx}"  

            # ---------- 버튼 + 결과를 '짝'으로 배치 ----------

            # 1) 요약
            if st.button("요약", key=f"btn_sum_{idx}"):
                with st.spinner("요약 중..."):
                    st.session_state[sum_key] = summ_tool.invoke(
                        abstract_text,
                        lang=st.session_state.summary_lang,
                        mode="summary",
                    )
            if st.session_state.get(sum_key):
                st.info(st.session_state[sum_key])

            # 2) 기여도
            if st.button("기여도", key=f"btn_contrib_{idx}"):
                with st.spinner("기여도 분석 중..."):
                    st.session_state[contrib_key] = summ_tool.invoke(
                        abstract_text,
                        lang=st.session_state.summary_lang,
                        mode="contribution",
                    )
            if st.session_state.get(contrib_key):
                st.success(st.session_state[contrib_key])

            # 3) 한계점
            if st.button("한계점", key=f"btn_weak_{idx}"):
                with st.spinner("한계점 분석 중..."):
                    st.session_state[weak_key] = summ_tool.invoke(
                        abstract_text,
                        lang=st.session_state.summary_lang,
                        mode="weakness",
                    )
            if st.session_state.get(weak_key):
                st.warning(st.session_state[weak_key])

            # 4) 장단점
            if st.button("장단점", key=f"btn_sw_{idx}"):
                with st.spinner("장단점 정리 중..."):
                    st.session_state[sw_key] = summ_tool.invoke(
                        abstract_text,
                        lang=st.session_state.summary_lang,
                        mode="strength_weakness",
                    )
            if st.session_state.get(sw_key):
                st.info(st.session_state[sw_key])

            # 5) 참고문헌 (IEEE)
            if st.button("참고문헌 (IEEE)", key=f"btn_ieee_{idx}"):
                st.session_state[ieee_key] = _make_ieee_citation(paper, index=idx)
            if st.session_state.get(ieee_key):
                st.code(st.session_state[ieee_key])

            # 6) BibTeX
            if st.button("BibTeX", key=f"btn_bibtex_{idx}"):
                st.session_state[bibtex_key] = _make_bibtex_entry(paper)
            if st.session_state.get(bibtex_key):
                st.code(st.session_state[bibtex_key], language="bibtex")

            # 7) 코드 찾기 (PDF → GitHub 링크, 없으면 검색 fallback)
            if st.button("코드 찾기", key=f"btn_code_{idx}"):
                pdf_url = paper.get("pdf")
                with st.spinner("코드 저장소를 찾는 중입니다..."):
                    st.session_state[code_key] = code_tool.invoke(
                        title=paper.get("title", ""),
                        authors=paper.get("authors", ""),
                        year=paper.get("year", None),
                        doi=paper.get("doi", None),
                        pdf_url=pdf_url,
                        max_results=3,
                    )

            code_results = st.session_state.get(code_key)
            if code_results is not None:
                if len(code_results) == 0:
                    st.info("연결된 코드 저장소를 찾지 못했습니다.")
                else:
                    # PDF에서 찾았는지, GitHub 검색인지 간단 안내
                    src = code_results[0].get("source")
                    if src == "pdf":
                        st.markdown("**🔗 논문 PDF 안에서 발견된 GitHub 링크**")
                    else:
                        st.markdown("**🔍 논문 제목 기반 GitHub 검색 결과(후보)**")

                    for r in code_results:
                        url = r.get("html_url")
                        repo_title = r.get("full_name") or url
                        desc = r.get("description") or ""
                        stars = r.get("stars")
                        lang = r.get("language") or "N/A"

                        # PDF에서 바로 찾은 경우엔 full_name/stars가 없을 수 있음
                        meta = []
                        if stars is not None:
                            meta.append(f"⭐ {stars}")
                        if lang:
                            meta.append(f"`{lang}`")
                        meta_str = "  ".join(meta)

                        st.markdown(
                            f"- [{repo_title}]({url})  {meta_str}\n"
                            f"  <br/>{desc}",
                            unsafe_allow_html=True,
                        )

            # 8) 라이브러리 저장
            if st.button("라이브러리에 저장", key=f"btn_save_{idx}"):
                ok, msg = add_to_library(paper)
                (st.success if ok else st.warning)(msg)

else:
    # 초기 상태 또는 결과 없음
    pass