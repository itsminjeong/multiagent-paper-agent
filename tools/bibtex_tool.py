# tools/bibtex_tool.py
"""
라이브러리 전체 BibTeX export + 개별 논문 BibTeX/IEEE 참고문헌 생성 유틸
"""

from __future__ import annotations
from typing import List, Dict
import re


# ---------------- 기본 유틸 ----------------

def _slugify_key(text: str) -> str:
    """BibTeX key 생성을 위한 간단 slug."""
    if not text:
        return "paper"
    # 알파벳/숫자만 남기고 나머지는 제거
    key = re.sub(r"[^a-zA-Z0-9]+", "", text)
    key = key.lower()
    return key[:30] or "paper"


def _split_authors(authors_str: str) -> List[str]:
    """
    Semantic Scholar / Crossref에서 가져온 authors 문자열을
    BibTeX author 필드용 리스트로 변환.

    현재 paper dict의 authors는 "A. Author, B. Author, C. Author" 형태라고 가정하고
    쉼표 기준으로 단순 분리.
    """
    if not authors_str:
        return []
    # ", " 기준으로 분리해서 공백 정리
    parts = [a.strip() for a in authors_str.split(",") if a.strip()]
    return parts


# ---------------- BibTeX 생성 ----------------

def make_bibtex_entry(paper: Dict, index: int | None = None) -> str:
    """
    단일 paper dict → BibTeX 엔트리 문자열 생성.

    paper dict 스키마 (우리 앱 기준):
      - title: str
      - authors: str  (예: "Lei Huang, Tingyang Xu, Yang Yu, ...")
      - year: int | None
      - venue: str | None
      - doi: str | None   (예: "https://doi.org/10.1038/...")
      - url: str | None
      - source: "Semantic Scholar" | "Crossref" | 기타
    """
    title = paper.get("title") or "(제목 없음)"
    authors_str = paper.get("authors", "")
    authors_list = _split_authors(authors_str)
    authors_bib = " and ".join(authors_list) if authors_list else ""

    year = paper.get("year")
    venue = paper.get("venue")
    url = paper.get("url")
    doi_url = paper.get("doi")  # 보통 "https://doi.org/..." 형태

    # doi 순수 값만 추출
    raw_doi = None
    if doi_url:
        raw_doi = (
            doi_url.replace("https://doi.org/", "")
            .replace("http://doi.org/", "")
            .replace("doi:", "")
            .strip()
        )

    # 타입 추정 (아주 간단한 휴리스틱)
    source = (paper.get("source") or "").lower()
    venue_l = (venue or "").lower()

    entry_type = "article"
    venue_field_name = "journal"

    # 학회 이름이 들어있으면 inproceedings로 취급
    conference_keywords = [
        "conference", "conf.",
        "neurips", "nips", "icml", "iclr", "aaai",
        "cvpr", "iccv", "eccv", "kdd",
        "sigir", "uai", "emnlp", "acl", "naacl", "coling",
    ]

    if any(kw in venue_l for kw in conference_keywords):
        entry_type = "inproceedings"
        venue_field_name = "booktitle"

    # key 생성
    key_base = _slugify_key(title)
    if year:
        key_base = f"{key_base}{year}"
    if index is not None:
        key_base = f"{key_base}_{index}"
    bib_key = key_base

    lines = [f"@{entry_type}{{{bib_key},"]

    if title:
        lines.append(f"  title = {{{title}}},")
    if authors_bib:
        lines.append(f"  author = {{{authors_bib}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if venue:
        lines.append(f"  {venue_field_name} = {{{venue}}},")

    if raw_doi:
        lines.append(f"  doi = {{{raw_doi}}},")
    if url:
        lines.append(f"  url = {{{url}}},")

    # 마지막 콤마 정리
    if len(lines) > 1 and lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]

    lines.append("}")
    return "\n".join(lines)


def export_bibtex_string(papers: List[Dict]) -> str:
    """
    라이브러리 전체를 BibTeX 텍스트로 export.
    기존 app에서 사용하던 함수 (호환 유지).
    """
    entries: List[str] = []
    for idx, p in enumerate(papers, 1):
        entries.append(make_bibtex_entry(p, index=idx))
    return "\n\n".join(entries)


# ---------------- IEEE 스타일 참고문헌 생성 ----------------

def ieee_reference_from_paper(paper: Dict, index: int | None = None) -> str:
    """
    IEEE 스타일에 근접한 한 줄짜리 참고문헌 문자열 생성.

    예시:
      [1] L. Huang, T. Xu, Y. Yu, "A dual diffusion model enables ...",
          Nature Communications, 2024, doi: https://doi.org/...

    index가 있으면 [1] 프리픽스를 붙이고, 없으면 문장만 반환.
    """
    authors = paper.get("authors", "").strip()
    title = paper.get("title", "").strip() or "(제목 없음)"
    venue = (paper.get("venue") or "").strip()
    year = paper.get("year")
    doi_url = paper.get("doi")
    url = paper.get("url")

    parts: List[str] = []

    if authors:
        parts.append(authors)
    if title:
        parts.append(f'"{title}"')
    if venue:
        parts.append(venue)
    if year:
        parts.append(str(year))

    ref = ", ".join(parts) if parts else title

    if doi_url:
        ref += f", doi: {doi_url}"
    elif url:
        ref += f". Available: {url}"
    else:
        ref += "."

    if index is not None:
        return f"[{index}] {ref}"
    return ref