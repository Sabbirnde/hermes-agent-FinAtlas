---
name: compare-ai
description: "Global AI Financial Product Research Agent. Research, verify, and compare loans, savings, FDR, DPS, and other financial products from official sources worldwide. Covers Bangladesh (MVP), India, Pakistan, and expanding globally. Evidence-backed, source-cited, calculation-transparent."
version: 1.0.0
author: COMPARE AI Team
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Finance, Research, Bangladesh, Global, Loans, Savings, FDR, DPS, Evidence, Verification, Comparison]
    category: finance
    related_skills: [grounded-citations, research-paper-writing, stocks]
---

# COMPARE AI Skill

Global AI Financial Product Research Agent. Researches official financial sources, verifies claims with evidence, performs deterministic calculations, evaluates eligibility, and ranks products transparently.

## When to Use

Use this skill whenever a user asks about:
- Finding loans (personal, home, auto, SME, education, agriculture)
- Comparing savings accounts, FDR, DPS, term deposits
- Finding the highest-rate savings product in a country
- Evaluating whether they qualify for a financial product
- Getting the cheapest loan option with evidence
- Comparing financial products across banks or NBFIs
- Researching Islamic finance products (profit rates, murabaha, etc.)

## Prerequisites

Python 3.11+. All scripts use stdlib + standard packages.

Required environment variables (set in `.env`):
```
COMPARE_AI_DB_URL=postgresql://...   # or sqlite:///compare_ai.db for local dev
COMPARE_AI_REDIS_URL=redis://...     # optional for caching
HERMES_WEB_SEARCH=true              # enable Hermes web search tool
```

## Slash Commands

```bash
/compare search "best personal loan in Bangladesh"
/compare loan 500000 60 --country BD
/compare savings 500000 --country BD
/compare fdr 500000 12 --country BD
/compare dps --country BD
/compare verify "BRAC Bank" personal-loan --country BD
/compare compare personal-loan --country BD
/compare cross-country personal-loan --countries BD,IN,PK
/compare status
/compare sources
```

## Scripts

```bash
SCRIPTS=~/.hermes/skills/finance/compare-ai/scripts

# Run intent extraction
python3 "$SCRIPTS/intent_agent.py" "I need a 5 lakh personal loan for 5 years"

# Run loan calculator (deterministic)
python3 "$SCRIPTS/loan_calculator.py" --principal 500000 --rate 12.0 --tenure 60

# Run deposit calculator
python3 "$SCRIPTS/deposit_calculator.py" --principal 500000 --rate 7.5 --tenure 12 --type fdr

# Run eligibility check
python3 "$SCRIPTS/eligibility_engine.py" --product-id <id> --age 30 --income 80000

# Run full research pipeline
python3 "$SCRIPTS/research_state.py" --query "best personal loan Bangladesh 500000 60 months"

# Check evidence for a product
python3 "$SCRIPTS/evidence_manager.py" list --product-id <id>

# Detect conflicts
python3 "$SCRIPTS/conflict_detector.py" --product-id <id>

# Check source freshness
python3 "$SCRIPTS/freshness_checker.py" --url "https://bank.com.bd/personal-loan"
```

## Full Procedure

### Stage 1 — Intent Extraction

```bash
python3 "$SCRIPTS/intent_agent.py" "<user_query>"
```

Outputs structured JSON intent. If any critical field is null, move to Stage 2.

### Stage 2 — Clarification (if needed)

Ask ONE question at a time. Maximum 3 questions before proceeding.

### Stage 3 — Research Planning

```bash
python3 "$SCRIPTS/research_planner.py" --intent-file intent.json --country BD
```

Outputs: search queries, institutions to check, source types needed.

### Stage 4 — Source Discovery

```bash
python3 "$SCRIPTS/source_discovery.py" --country BD --product personal_loan
```

Outputs ranked list of URLs to check per institution.

### Stage 5 — Web Research

Use Hermes `web_search`, `web_extract`, `browser_navigate`, and `download_file` tools.

For each institution in the research plan:
1. Search for official product page
2. Extract rate, fees, eligibility from the page
3. If PDF found, download and extract tables
4. Register each source immediately:
   ```bash
   python3 "$SCRIPTS/evidence_manager.py" add --url <url> --field interest_rate --value "12%" --evidence-text "Interest Rate: 12.00% per annum"
   ```

### Stage 6 — Product Extraction

```bash
python3 "$SCRIPTS/product_extractor.py" --source-file <extracted_page.txt> --institution "BRAC Bank" --product personal_loan
```

Outputs normalized product schema JSON. Null for any unverifiable field.

### Stage 7 — Verification

```bash
python3 "$SCRIPTS/verification_engine.py" --products-dir ./products/
python3 "$SCRIPTS/conflict_detector.py" --products-dir ./products/
```

Flags conflicts. Never silently resolve.

### Stage 8 — Calculations (Deterministic)

```bash
# Loan EMI
python3 "$SCRIPTS/loan_calculator.py" \
  --principal 500000 \
  --rate 12.0 \
  --tenure 60 \
  --fees 5000

# FDR Return
python3 "$SCRIPTS/deposit_calculator.py" \
  --principal 500000 \
  --rate 7.5 \
  --tenure 12 \
  --type fdr
```

### Stage 9 — Eligibility

```bash
python3 "$SCRIPTS/eligibility_engine.py" \
  --products-dir ./products/ \
  --age 30 \
  --income 80000 \
  --employment salaried
```

### Stage 10 — Comparison & Ranking

```bash
python3 "$SCRIPTS/comparison_engine.py" \
  --products-dir ./products/ \
  --priority lowest_total_cost

python3 "$SCRIPTS/ranking_engine.py" \
  --products-dir ./products/ \
  --priority lowest_total_cost \
  --top 5
```

### Stage 11 — Answer Generation

Format output using response templates from `references/response-templates.md`.
Always include: sources, evidence, checked dates, calculation disclaimer.

## Quick Reference

| Goal | Command |
|---|---|
| Extract intent from query | `intent_agent.py "<query>"` |
| Calculate loan EMI | `loan_calculator.py --principal P --rate R --tenure N` |
| Calculate FDR return | `deposit_calculator.py --principal P --rate R --tenure T --type fdr` |
| Find sources for BD bank | `source_discovery.py --country BD --product personal_loan` |
| Add evidence for a field | `evidence_manager.py add --url U --field F --value V --evidence-text T` |
| Verify all products | `verification_engine.py --products-dir ./products/` |
| Detect conflicts | `conflict_detector.py --products-dir ./products/` |
| Check freshness | `freshness_checker.py --url U` |
| Run eligibility check | `eligibility_engine.py --products-dir D --age A --income I` |
| Rank by priority | `ranking_engine.py --products-dir D --priority P --top 5` |
| Check research state | `research_state.py --status` |

## Pitfalls

- **Never fabricate a rate.** If the source is ambiguous, store null.
- **Never calculate in LLM.** All EMI and return calculations use deterministic Python scripts.
- **Never cite a search snippet as evidence.** Must extract the actual page first.
- **Never rank using rate alone.** Total cost, fees, eligibility all matter.
- **Never silently resolve conflicts.** Flag them clearly to the user.
- **Never guarantee approval.** Always say "based on published eligibility criteria."
- **Always check freshness.** A stale rate sheet is not current evidence.
- **Islamic products:** Use "profit rate" not "interest rate" for Islamic bank products.

## Verification

```bash
python3 "$SCRIPTS/loan_calculator.py" --principal 500000 --rate 12.0 --tenure 60
# Expected: monthly_installment ≈ 11,122 BDT
```
