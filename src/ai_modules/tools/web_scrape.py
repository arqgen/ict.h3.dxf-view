from agno.tools.trafilatura import TrafilaturaTools

web_scrape = TrafilaturaTools(
    output_format="markdown",
    include_comments=False,
    include_tables=True,
    include_images=False,
    include_formatting=True,
    include_links=True,
    with_metadata=True,
    favor_precision=True,
    favor_recall=False,
    target_language="pt-br",
    deduplicate=True,
    max_crawl_urls=10,
    max_known_urls=100,
)
