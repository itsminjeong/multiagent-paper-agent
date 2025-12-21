# 📚 MultiAgent Paper Agent
AI 기반 **논문 검색·요약·기여도 분석·참고문헌 생성·코드 리포지토리 탐색** 시스템  
Semantic Scholar + GPT + GitHub API + Streamlit 기반 다기능 연구 도우미 에이전트

---

## 🚀 주요 기능

### 1️⃣ **논문 검색 (Semantic Scholar API)**
- 키워드, 저널/컨퍼런스, 연도 범위, 인용 수 필터 지원  
- NeurIPS/ICML/ICLR/CVPR 등 컨퍼런스 이름 별칭 자동 인식  
- 초록, 저자, 인용 수, DOI, PDF 링크 표시  

### 2️⃣ **논문 자동 분석 (GPT 기반)**
- 초록 기반 빠른 분석:
  - 요약 Summary
  - 핵심 기여도 Contribution
  - 한계점 Weakness
  - 장단점 Strength & Weakness  
- 한국어/영어/일본어 지원

### 3️⃣ **참고문헌 자동 생성**
- DOI 기반 IEEE 스타일 참고문헌 자동 생성  
- BibTeX 포맷 자동 생성  
- 커스텀 포맷도 쉽게 확장 가능

### 4️⃣ **GitHub 코드 저장소 탐색 기능**
- 논문 제목 기반 GitHub Repository 검색  
- stars, 언어, 설명, 링크 자동 정리  
- 논문 PDF URL 기반 검색도 (지원되는 경우) 가능

### 5️⃣ **로컬 라이브러리 저장 기능**
- `library.json`을 로컬 DB처럼 사용  
- 중복 저장 방지  
- 라이브러리 전체를 BibTeX로 Export 가능  

### 6️⃣ **Streamlit UI 제공**
- 직관적인 브라우저 UI  
- 버튼 기반 기능 실행  
- 모듈별 구조로 확장 쉬움

---
## 📁 프로젝트 구조
~~~
MULTIAGENT-PAPER-AGENT/
│
├── agents/
│   ├── agent_base.py
│   └── paper_agent.py
│
├── tools/
│   ├── paper_search_tool.py
│   ├── paper_summarize_tool.py
│   ├── code_search_tool.py
│   ├── library_tool.py
│   ├── bibtex_tool.py
│   └── tool_base.py
│
├── configs/
│   └── settings.py
│
├── data/
│   ├── library.json
│   └── exports/
│
├── rag/
│   └── index/
│
├── app.py
├── requirements.txt
└── .env

---
~~~

## 🛠 설치 및 실행

### 1) Python & 가상환경
```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate   # Windows
```

### 2) 패키지 설치

~~~bash
pip install -r requirements.txt
~~~

### 3) 환경변수 설정 (.env 생성)

~~~bash
OPENAI_API_KEY=your_openai_key
S2_API_KEY=your_semantic_scholar_key
GITHUB_TOKEN=your_github_personal_token
PAPER_PROVIDER=semantic_scholar
~~~

### 4) 실행

~~~bash
streamlit run app.py
~~~

⸻

## 🌿 기술 스택
- Python 3.10+
- Streamlit – 웹 UI
- OpenAI GPT API – 요약/분석
- Semantic Scholar API – 논문 검색
- GitHub Search API – 코드 저장소 탐색
- FAISS + SentenceTransformer (옵션) – 확장 가능

⸻

## 🧱 설계 철학
- Tool 기반 모듈형 구조
- Agent가 Tool을 조합하여 작업 실행
- 유지보수/확장성 최적화 (PDF 분석, RAG 확장, Embedding 추가 가능)

⸻

## 🚀 향후 개발 예정 기능
- PDF 업로드 → 본문 기반 심층 요약
- RAG 기반 논문 검색
- 메타데이터 기반 여러 논문 비교 기능
- Research Trend 자동 정리
- 학습용 벡터 DB 구축

⸻

## 📄 라이선스

MIT License (자유롭게 연구/수정/사용 가능)

⸻

## 👩‍💻 만든 사람

itsminjeong (2025)
