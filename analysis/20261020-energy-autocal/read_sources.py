"""Save documentary source text; this script does not calculate calibration results."""
import asyncio
from pathlib import Path
import pymupdf
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

HERE = Path(__file__).resolve().parent
URL = 'https://zhihuanli.github.io/Experimental-Method-in-Nuclear-Physics/chapt3/coursework3.1/3.1_HpGe_gamma_calibration.html'

async def main():
    for stem in ['eu152', 'ba133']:
        with pymupdf.open(HERE / (stem + '-tables.pdf')) as doc:
            text = '\n'.join(p.get_text(sort=True) for p in doc)
        (HERE / (stem + '-tables.txt')).write_text(text)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=URL, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        if not result.success:
            raise RuntimeError(result.error_message)
        (HERE / 'tutorial-source.md').write_text('Source: ' + URL + '\n\n' + result.markdown.raw_markdown)

if __name__ == '__main__':
    asyncio.run(main())
