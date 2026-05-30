import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class TataBFSISpider(CrawlSpider):
    name = "tata_bfsi"
    allowed_domains = ["tatacapital.com"]
    start_urls = ["https://www.tatacapital.com/"]

    custom_settings = {
        "PLAYWRIGHT_INCLUDE_PAGE": True,  # enable if using scrapy-playwright
        "DEPTH_LIMIT": 3,  # optional: controls how deep the crawler goes
    }

    # Follow internal links automatically
    rules = (
        Rule(LinkExtractor(allow_domains=["tatacapital.com"]), callback="parse_item", follow=True),
    )

    def parse_item(self, response):
        """
        Extract only the core page content and skip headers, footers, navs, etc.
        """

        # Candidate containers that usually hold article or content text
        selectors = [
            "//main//text()",  # common semantic tag for main content
            "//article//text()",  # blogs and articles
            "//div[contains(@class, 'content')]//text()",  # general text containers
            "//div[contains(@class, 'article')]//text()",
            "//div[contains(@class, 'loan')]//text()",
            "//div[contains(@id, 'content')]//text()"
        ]

        # Extract and clean up meaningful text
        page_text = ""
        for sel in selectors:
            text_parts = response.xpath(sel).getall()
            if text_parts:
                page_text = " ".join(text_parts)
                break  # stop when something meaningful found

        # Clean up whitespace, newlines, and script junk
        page_text = (
            page_text.replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
            .strip()
        )
        page_text = " ".join(page_text.split())  # collapse extra spaces

        if not page_text:
            return  # skip empty pages

        # Filter BFSI-relevant pages
        keywords = ["loan", "finance", "insurance", "investment", "credit", "emi", "banking"]
        if any(word in page_text.lower() for word in keywords):
            yield {
                "url": response.url,
                "title": response.xpath("//title/text()").get(),
                "text": page_text[:5000]  # extract first 5000 chars of cleaned content
            }
