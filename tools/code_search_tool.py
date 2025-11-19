# tools/code_search_tool.py
import re
from typing import List, Dict, Optional

import requests
import fitz  # PyMuPDF

from tools.tool_base import BaseTool
from configs import settings  # GITHUB_TOKEN(optional)


class CodeSearchTool(BaseTool):
    """
    논문과 연결된 코드 저장소를 찾는 Tool

    우선순위:
      1) Semantic Scholar가 제공한 PDF URL 안에서 github.com 링크 파싱
      2) 실패/없음 → 논문 제목/저자를 이용해 GitHub 검색 (후보 레포 리스트)
    """

    def invoke(
        self,
        title: str,
        authors: str = "",
        year: Optional[int] = None,
        doi: Optional[str] = None,
        pdf_url: Optional[str] = None,
        max_results: int = 3,
    ) -> List[Dict]:
        # 1) PDF에 직접 포함된 GitHub 링크 우선 시도
        if pdf_url:
            try:
                pdf_links = self._extract_github_links_from_pdf(pdf_url)
                if pdf_links:
                    # PDF 안에서 찾은 링크는 가장 신뢰도가 높으므로 그대로 반환
                    return pdf_links
            except Exception as e:
                print("❌ PDF 파싱 중 오류:", e)

        # 2) PDF가 없거나, GitHub 링크가 없을 경우 → 제목 기반 GitHub 검색 fallback
        if not title:
            return []

        try:
            return self._search_github_repos(
                title=title,
                authors=authors,
                year=year,
                max_results=max_results,
            )
        except Exception as e:
            print("❌ GitHub 검색 중 오류:", e)
            return []

    # ------------------------------------------------------------------ #
    #  PDF 파싱: github.com 링크 추출
    # ------------------------------------------------------------------ #
    def _extract_github_links_from_pdf(self, pdf_url: str) -> List[Dict]:
        """
        PDF 파일을 다운로드한 뒤 텍스트/링크에서 github.com URL을 추출한다.
        반환 형식:
          [
            {
              "html_url": "https://github.com/...",
              "source": "pdf",
              "where": "text" | "link",
            },
            ...
          ]
        """
        res = requests.get(pdf_url, timeout=30)
        res.raise_for_status()

        doc = fitz.open(stream=res.content, filetype="pdf")

        urls = set()

        # 1) 텍스트에서 URL 패턴 검색
        for page in doc:
            text = page.get_text("text") or ""
            for m in re.findall(r"https?://github\.com/[^\s\)>\]]+", text):
                urls.add(self._clean_url(m))

            # 2) 링크 오브젝트에서 URL 추출
            for link in page.get_links():
                uri = link.get("uri")
                if uri and "github.com" in uri:
                    urls.add(self._clean_url(uri))

        doc.close()

        return [
            {
                "html_url": u,
                "full_name": None,
                "description": None,
                "language": None,
                "stars": None,
                "source": "pdf",
            }
            for u in urls
        ]

    @staticmethod
    def _clean_url(url: str) -> str:
        # 끝에 붙은 불필요한 마침표/괄호/쉼표 제거
        return url.rstrip(".,);] ")

    # ------------------------------------------------------------------ #
    #  GitHub 검색 fallback
    # ------------------------------------------------------------------ #
    def _search_github_repos(
        self,
        title: str,
        authors: str = "",
        year: Optional[int] = None,
        max_results: int = 3,
    ) -> List[Dict]:
        """
        논문 제목/저자를 기반으로 GitHub 저장소 검색.
        - PDF를 못 읽는 경우나, PDF에 GitHub 링크가 없을 때 fallback 용도.
        """
        base_url = "https://api.github.com/search/repositories"

        # 첫 번째 저자 성 정도만 추가 (검색 힌트용)
        first_author_last = ""
        if authors:
            first = authors.split(",")[0].strip()
            if first:
                parts = first.split()
                first_author_last = parts[-1]

        # 검색 쿼리 구성
        q_parts = [f'"{title}" in:name,description,readme']
        if first_author_last:
            q_parts.append(first_author_last)
        query = " ".join(q_parts)

        params = {
            "q": query,
            "per_page": max(1, int(max_results)),
            "sort": "stars",
            "order": "desc",
        }

        headers = {"Accept": "application/vnd.github+json"}
        token = getattr(settings, "GITHUB_TOKEN", None)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        res = requests.get(base_url, headers=headers, params=params, timeout=30)
        res.raise_for_status()
        data = res.json()

        out: List[Dict] = []
        for item in data.get("items", []):
            out.append(
                {
                    "full_name": item.get("full_name"),
                    "html_url": item.get("html_url"),
                    "description": item.get("description"),
                    "language": item.get("language"),
                    "stars": item.get("stargazers_count", 0),
                    "source": "github_search",
                }
            )
        return out