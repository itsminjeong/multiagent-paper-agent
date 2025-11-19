# tools/paper_search_tool.py
import requests
from typing import List, Dict, Optional

from tools.tool_base import BaseTool
from configs import settings  # S2_API_KEY


class PaperSearchTool(BaseTool):
    """
    논문 검색 Tool
    - 기본: Semantic Scholar (S2)
    - 실패/빈결과: Crossref 백업
    - 결과 스키마 통일: title/authors/year/citations/venue/doi/url/pdf/abstract/source/venue_all
    - venue 입력 시: alias를 쿼리에 섞어 추가 검색 → 합치고 dedupe → venue_all 기준 contains 필터
    """

    # --------------- Public ---------------
    def invoke(
        self,
        query: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_citations: Optional[int] = None,
        venue: Optional[str] = None,   # S2는 서버 필터가 없어 후처리/alias 재검색
        max_results: int = 5,
    ) -> List[Dict]:
        # 1) 기본 검색
        base = self._search_semantic_scholar(
            query=query,
            year_from=year_from,
            year_to=year_to,
            min_citations=min_citations,
            limit=max_results,
        )

        # 2) venue가 있으면 alias들을 쿼리에 섞어 추가 검색 → 합치고 dedupe
        results = base[:]
        seen = set(self._dedupe_key(r) for r in results)

        if venue and venue.strip():
            aliases = self._venue_aliases(venue)
            for alias in aliases:
                q2 = f"{query} {alias}"
                more = self._search_semantic_scholar(
                    query=q2,
                    year_from=year_from,
                    year_to=year_to,
                    min_citations=min_citations,
                    limit=max_results,
                )
                for r in more:
                    k = self._dedupe_key(r)
                    if k not in seen:
                        results.append(r)
                        seen.add(k)

            # 2-1) venue_all(간단명+정식명) contains로 사후 필터
            v = venue.strip().lower()
            filtered = [
                r for r in results
                if v in ((r.get("venue_all") or r.get("venue") or "").lower())
            ]
            if filtered:
                results = filtered

        # 3) 폴백: 그래도 없다면 Crossref
        if not results:
            results = self._search_crossref(
                query=query,
                year_from=year_from,
                year_to=year_to,
                limit=max_results,
            )

        # 결과 너무 많으면 상한
        return results[:max_results] if results else []

    # --------------- Semantic Scholar ---------------
    def _search_semantic_scholar(
        self,
        query: str,
        year_from: Optional[int],
        year_to: Optional[int],
        min_citations: Optional[int],
        limit: int,
    ) -> List[Dict]:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {}
        if settings.S2_API_KEY:
            headers["x-api-key"] = settings.S2_API_KEY

        params = {
            "query": query,
            "limit": max(1, int(limit)),
            # publicationVenue.name을 함께 요청해 venue 정보를 풍부하게
            "fields": "title,year,venue,abstract,citationCount,authors,url,externalIds,openAccessPdf,publicationVenue",
        }

        try:
            res = requests.get(url, headers=headers, params=params, timeout=20)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print("❌ Semantic Scholar Error:", e)
            return []

        out: List[Dict] = []
        for item in data.get("data", []):
            # 조건 필터링
            yr = item.get("year")
            if year_from and yr and yr < year_from:
                continue
            if year_to and yr and yr > year_to:
                continue
            if min_citations is not None and item.get("citationCount", 0) < int(min_citations):
                continue

            # 저자
            authors = ", ".join(a.get("name", "") for a in item.get("authors", [])) or "(저자 정보 없음)"
            # DOI
            doi = (item.get("externalIds") or {}).get("DOI")
            doi_url = f"https://doi.org/{doi}" if doi else None
            # venue (간단 표시) + venue_all (간단명 + 정식명 결합)
            venue_simple = item.get("venue")
            pubv = item.get("publicationVenue") or {}
            venue_full = pubv.get("name")
            venue_all = " | ".join(s for s in [venue_simple, venue_full] if s)

            out.append({
                "title": item.get("title") or "(제목 없음)",
                "authors": authors,
                "year": yr,
                "citations": item.get("citationCount"),
                "venue": venue_simple,              # 카드에 표시용
                "venue_all": venue_all,            # 필터용(간단+정식명)
                "doi": doi_url,
                "url": item.get("url"),
                "pdf": (item.get("openAccessPdf") or {}).get("url"),
                "abstract": item.get("abstract") or "(초록 없음)",
                "source": "Semantic Scholar",
            })
        return out

    # --------------- Crossref (fallback) ---------------
    def _search_crossref(
        self,
        query: str,
        year_from: Optional[int],
        year_to: Optional[int],
        limit: int,
    ) -> List[Dict]:
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": max(1, int(limit)),
        }
        filters = []
        if year_from:
            filters.append(f"from-pub-date:{int(year_from)}")
        if year_to:
            filters.append(f"until-pub-date:{int(year_to)}")
        if filters:
            params["filter"] = ",".join(filters)

        try:
            res = requests.get(url, params=params, timeout=20)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print("❌ Crossref Error:", e)
            return []

        out: List[Dict] = []
        for it in data.get("message", {}).get("items", []):
            title = (it.get("title") or ["(제목 없음)"])[0]
            authors = ", ".join(
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in it.get("author", []) if isinstance(a, dict)
            ) or "(저자 정보 없음)"
            year = None
            if "issued" in it and "date-parts" in it["issued"] and it["issued"]["date-parts"]:
                year = it["issued"]["date-parts"][0][0]
            doi = it.get("DOI")
            doi_url = f"https://doi.org/{doi}" if doi else None
            url_final = doi_url or it.get("URL")

            venue_title = (it.get("container-title") or [""])[0] or None
            out.append({
                "title": title,
                "authors": authors,
                "year": year,
                "citations": None,          # Crossref에선 제공 한계
                "venue": venue_title,
                "venue_all": venue_title,
                "doi": doi_url,
                "url": url_final,
                "pdf": None,
                "abstract": "(초록 없음)",
                "source": "Crossref",
            })
        return out

    # --------------- Helpers ---------------
    def _dedupe_key(self, r: Dict) -> str:
        d = (r.get("doi") or "").lower()
        if d:
            return f"doi:{d}"
        return f"title:{(r.get('title') or '').lower()}|year:{r.get('year')}"

    def _venue_aliases(self, v: str) -> List[str]:
        """유명 저널/컨퍼런스의 약어/정식명 alias 세트 반환(대소문자 그대로 유지하여 쿼리에 활용)."""
        t = (v or "").strip().lower()
        aliases = {
            # Conferences
            "neurips": [
                "NeurIPS", "NIPS",
                "Neural Information Processing Systems",
                "Advances in Neural Information Processing Systems",
            ],
            "icml": ["ICML", "International Conference on Machine Learning"],
            "iclr": ["ICLR", "International Conference on Learning Representations"],
            "cvpr": ["CVPR", "Computer Vision and Pattern Recognition"],
            "iccv": ["ICCV", "International Conference on Computer Vision"],
            "eccv": ["ECCV", "European Conference on Computer Vision"],
            "aaai": ["AAAI", "Association for the Advancement of Artificial Intelligence"],
            "acl": ["ACL", "Association for Computational Linguistics"],
            "emnlp": ["EMNLP", "Empirical Methods in Natural Language Processing"],
            "kdd": ["KDD", "SIGKDD", "Knowledge Discovery and Data Mining"],
            "sigir": ["SIGIR", "Information Retrieval"],
            "uai": ["UAI", "Uncertainty in Artificial Intelligence"],
            # Journals
            "jmlr": ["JMLR", "Journal of Machine Learning Research"],
            "tmlr": ["TMLR", "Transactions on Machine Learning Research"],
            "tpami": ["TPAMI", "Transactions on Pattern Analysis and Machine Intelligence"],
            "tacl": ["TACL", "Transactions of the Association for Computational Linguistics"],
            "nature": ["Nature"],
            "science": ["Science"],
            "cell": ["Cell"],
            "pnas": ["PNAS", "Proceedings of the National Academy of Sciences"],
        }
        for k, vals in aliases.items():
            if t == k:
                return vals
        # 사용자가 정식명을 직접 입력했다면 그대로도 alias로 활용
        return [v] if v else []