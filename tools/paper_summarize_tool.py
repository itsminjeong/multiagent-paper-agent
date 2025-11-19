# tools/paper_summarize_tool.py
from typing import Literal
from openai import OpenAI

from tools.tool_base import BaseTool
from configs import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

SummaryMode = Literal["summary", "contribution", "weakness", "strength_weakness"]


class PaperSummarizeTool(BaseTool):
    """
    논문 분석/요약 Tool

    - summary            : 전체 요약
    - contribution       : 핵심 기여도 정리
    - weakness           : 한계/약점 분석
    - strength_weakness  : 장단점 같이 정리
    """

    def invoke(
        self,
        text: str,
        lang: str = "ko",
        mode: SummaryMode = "summary",
    ) -> str:
        """
        text : 논문 초록 또는 본문 일부
        lang : ko / en / ja
        mode : summary / contribution / weakness / strength_weakness
        """
        if not text or text.strip() == "":
            return "요약할 내용(초록/본문)이 없습니다."

        system_msg = self._build_system_prompt(lang, mode)
        user_msg = self._build_user_prompt(text, lang, mode)

        resp = client.chat.completions.create(
            model=settings.MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()

    # ---------------- internal helpers ----------------
    def _build_system_prompt(self, lang: str, mode: SummaryMode) -> str:
        base = {
            "ko": "너는 논문을 분석해주는 조교야. 한국어로만 답해.",
            "en": "You are an AI assistant that analyzes research papers. Answer in English.",
            "ja": "あなたは論文を分析するアシスタントです。日本語で答えてください。",
        }.get(lang, "You are an AI assistant that analyzes research papers.")

        if mode == "summary":
            extra = " 사용자가 제공한 논문 내용을 구조적으로 요약해줘."
        elif mode == "contribution":
            extra = " 논문의 핵심 contribution만 2~4개 bullet로 정리해줘."
        elif mode == "weakness":
            extra = " 논문의 한계점/약점을 3~5개 bullet로 비판적으로 정리해줘."
        elif mode == "strength_weakness":
            extra = " 논문의 장점 3개, 단점 3개를 bullet 형식으로 나누어 정리해줘."
        else:
            extra = ""

        return base + extra

    def _build_user_prompt(self, text: str, lang: str, mode: SummaryMode) -> str:
        if mode == "summary":
            return f"다음 논문 내용을 간결하고 논리적으로 요약해줘.\n\n{text}"
        elif mode == "contribution":
            return (
                "다음 논문의 핵심 contribution만 뽑아서 bullet 형식으로 정리해줘. "
                "구현 아이디어, 이론적 기여, 실험적 기여를 구분해주면 더 좋다.\n\n"
                f"{text}"
            )
        elif mode == "weakness":
            return (
                "다음 논문의 한계점과 약점을 비판적으로 분석해 bullet로 정리해줘. "
                "데이터/실험셋 한계, 비교 대상 부족, 가정의 비현실성, 재현 가능성 문제 등을 포함해서 적어줘.\n\n"
                f"{text}"
            )
        elif mode == "strength_weakness":
            return (
                "다음 논문의 내용을 바탕으로, 먼저 장점(strengths) 3개, "
                "그 다음 줄에 단점(weaknesses) 3개를 bullet 형태로 정리해줘.\n\n"
                f"{text}"
            )
        else:
            return text