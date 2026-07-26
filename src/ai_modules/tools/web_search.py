from agno.tools.duckduckgo import DuckDuckGoTools

web_search = DuckDuckGoTools(
    enable_search=True,
    enable_news=True,
    modifier=None,
    fixed_max_results=10,
    proxy=None,
    timeout=10,
    verify_ssl=True,
    timelimit="y",  # "d", "w", "m", "y" — filtro de data, não rate limit
    region="br-pt",
    backend="auto",
)
