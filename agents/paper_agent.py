# agents/paper_agent.py
from agents.agent_base import BaseAgent
from tools.paper_search_tool import PaperSearchTool

class PaperAgent(BaseAgent):
    """논문 검색 Agent — Semantic Scholar(S2) 메인 + Crossref 백업을 래핑"""

    def __init__(self):
        self.tool = PaperSearchTool()

    def run(
        self,
        instruction: str,
        year_from: int | None = None,
        year_to: int | None = None,
        min_citations: int | None = None,
        venue: str | None = None,   # ✅ venue 지원
        max_results: int = 5,
    ):
        return self.tool.invoke(
            query=instruction,
            year_from=year_from,
            year_to=year_to,
            min_citations=min_citations,
            venue=venue,            # ✅ 그대로 전달
            max_results=max_results,
        )