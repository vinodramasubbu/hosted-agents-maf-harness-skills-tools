---
name: etf-analysis
description: Research or compare ETFs using Yahoo Finance prices and holdings and DuckDuckGo qualitative context.
---

# ETF Analysis

- Identify each ETF ticker. Choose `fetch_market_data` functions for the needed quotes, history,
  fundamentals, or top holdings, and `search_research` for issuer context and recent developments.
- Explain the fund objective, concentration, exposures, fees when available, and relevant risks.
- Report unavailable fees or holdings instead of inferring them. Top holdings are not a full portfolio.
- Cite Yahoo source metadata and the research titles, sites, URLs, and dates used.
- Never use news snippets for numeric market facts or recommend a transaction.
- Include `used - etf-analysis` and the educational, not-investment-advice note.
