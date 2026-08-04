# FinAtlas 🏦

**FinAtlas is an AI Financial Product Research Agent that finds, verifies, and compares loans, savings, FDRs, DPS, and other financial products from official sources. It analyzes rates, fees, eligibility, and returns to deliver trusted, evidence-backed recommendations.**

---

## 🌟 Core Features

- 🔍 **Real-Time Web Research**: Searches official bank, NBFI, MFI, and regulatory websites directly.
- 🛡️ **Zero Hallucination Policy**: If financial data is not explicitly found in an official source, it is marked `null / unknown`. Rates and fees are never invented.
- 📊 **Deterministic Calculation Engine**: Standard amortizing EMI formulas and simple/compound return calculations executed in Python — never calculated by an LLM.
- ⚖️ **Multi-Source Verification & Conflict Detection**: Cross-references claims across rate sheets, product pages, and circulars. Flags conflicting information explicitly.
- 🎯 **Eligibility Classifier**: 4-tier classification (`likely_eligible`, `possibly_eligible`, `likely_not_eligible`, `unknown`) based on published income, age, employment, and collateral criteria.
- 🏆 **Transparent Ranking**: Priority-weighted ranking (lowest total cost, highest return, lowest monthly payment, no collateral, lowest fees) with plain-English explanations.
- 📅 **Freshness & Traceability**: Cites source URLs, exact evidence snippets, and checked dates for every claim.

---

## 🏗️ Architecture

FinAtlas is built as an edge customization layer on top of the **Hermes Agent** platform.

```
┌──────────────────────────────────────────────────────────────────────┐
│                              FINATLAS                                │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    FRONTEND LAYER                           │    │
│  │   Next.js / React 19 + Vite + Tailwind CSS                  │    │
│  │   Multi-language (EN / BN) | ৳ Currency Support             │    │
│  └────────────────────────┬────────────────────────────────────┘    │
│                           │ REST / WebSocket                        │
│  ┌────────────────────────▼────────────────────────────────────┐    │
│  │                  API GATEWAY (FastAPI)                      │    │
│  │   Auth | Country Routing | Pipeline Orchestrator            │    │
│  └──────┬────────────────┬──────────────────┬─────────────────┘    │
│         │                │                  │                       │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼──────┐               │
│  │  RESEARCH   │  │  CALC       │  │  DATABASE &  │               │
│  │  PIPELINE   │  │  ENGINES    │  │  CACHE       │               │
│  │  (15-stage) │  │  (Python)   │  │  (PostgreSQL │               │
│  └──────┬──────┘  └─────────────┘  │  + Redis)    │               │
│         │                          └──────────────┘               │
│  ┌──────▼──────────────────────────────────────────────────────┐    │
│  │              COUNTRY PLUGIN LAYER                           │    │
│  │   🇧🇩 Bangladesh (MVP Live) | 🇮🇳 India | 🇵🇰 Pakistan | ...   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 15-Stage Research Pipeline

```
USER QUERY
  ↓ 1. Intent Extraction (NL → JSON schema)
  ↓ 2. Clarification Agent (minimum necessary questions)
  ↓ 3. Research Planning
  ↓ 4. Source Discovery (Tier 1–5 source hierarchy)
  ↓ 5. Web Research (official product pages, PDFs, circulars)
  ↓ 6. Product Extraction (normalized schema)
  ↓ 7. Evidence Collection (URL + quote + confidence)
  ↓ 8. Verification & Conflict Detection
  ↓ 9. Financial Calculations (deterministic EMI / returns)
  ↓ 10. Eligibility Evaluation (published criteria)
  ↓ 11. Comparison & Ranking (weighted priority scoring)
  ↓ 12. Answer Generation (sources + evidence + checked date)
  ↓ COMPLETED
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+

### 1. Web Frontend

```bash
cd apps/compare-ai-web
npm install
npm run dev
```
Open **http://localhost:3000** in your browser.

### 2. FastAPI Backend

```bash
cd apps/compare-ai-api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API Documentation available at **http://localhost:8000/api/docs**.

### 3. Run Test Suite

```bash
python -m pytest tests/compare-ai/ -v --noconftest -p no:hermes
```

---

## 🛠️ Tech Stack

- **Agent Core**: Hermes Agent (Nous Research)
- **Backend**: FastAPI (Python 3.11), SQLAlchemy, Pydantic, Celery, Redis
- **Frontend**: React 19, Vite, TypeScript, Inter + Noto Sans Bengali typography
- **Database**: PostgreSQL (12 tables + 15 country registries seeded)
- **Deployment**: Docker, Docker Compose

---

## 📄 License

MIT License. Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent).
