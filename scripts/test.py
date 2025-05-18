import asyncio

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

url = "https://detail.1688.com/offer/764286652699.html"


async def main():
    browser_config = BrowserConfig(
        headless=False,
        verbose=True,
        use_managed_browser=True,
        browser_type="chromium",
        user_data_dir="/Users/zerry/Work/Projects/funs/1click_oversea/data/1688_profile",
    )
    run_config = CrawlerRunConfig(
        wait_for="css:div.title-text",
        delay_before_return_html=8,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

        # with open("data/result.html", "w") as f:
        #     f.write(result.html)


if __name__ == "__main__":
    asyncio.run(main())
