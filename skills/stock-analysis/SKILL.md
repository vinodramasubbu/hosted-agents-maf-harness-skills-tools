---
name: stock-analysis
description: Research a public company with Yahoo Finance numeric data and DuckDuckGo news and context.
---

# Stock Analysis

- Identify the company ticker. Use `fetch_market_data` for quotes, fundamentals, or price history
  as needed, and `search_research` for recent drivers and risks.
- Choose the tool calls that answer the question; do not run a fixed checklist unnecessarily.
- Separate sourced facts from interpretation. Explain delayed or unavailable data honestly.
- Cite Yahoo source metadata and the research titles, sites, URLs, and dates used.
- Never infer prices from news snippets or recommend buying or selling.
- Include `used - stock-analysis` and the educational, not-investment-advice note.
