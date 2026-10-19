# InvestIQ local skills and tools demo

Keep this example self-contained. Anthropic through the existing APIM endpoint is the model
provider; Microsoft Foundry is the hosting runtime. Read the microsoft-foundry skill before
changing Foundry integration.

Use only `fetch_market_data` (Yahoo Finance) for numeric market facts and `search_research`
(DuckDuckGo) for qualitative research. Keep built-in web search and file access disabled.
Skills are local Markdown instructions, selected by the model, not keyword routing.
Do not add deterministic analysis workflows, projections, SQL, a Python sandbox, or evidence UI.
Keep credentials in environment variables or the Foundry project connection, never source or responses.
