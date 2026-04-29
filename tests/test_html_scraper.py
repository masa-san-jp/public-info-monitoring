"""M2: HTMLスクレイパーのテスト"""
from pathlib import Path
import pytest
from gov_monitor.pollers.html_scraper import HTMLScraper, ScrapedPage


FIXTURES = Path(__file__).parent / "fixtures"


class TestHTMLScraper:
    def test_extract_table_rows(self):
        html = (FIXTURES / "mhlw_page.html").read_text()
        scraper = HTMLScraper(
            url="https://www.mhlw.go.jp/stf/shingi/other-syougai_446935_00001.html",
            selector="table.m-tableFlex tbody tr"
        )
        page = scraper.parse(html)
        # 1行はヘッダー、3行はデータ
        assert page.row_count == 3

    def test_detect_change_by_hash(self):
        html = (FIXTURES / "mhlw_page.html").read_text()
        scraper = HTMLScraper(
            url="https://example.com",
            selector="table.m-tableFlex tbody tr"
        )
        page = scraper.parse(html)
        assert len(page.content_hash) == 64  # SHA256 hex

    def test_same_content_same_hash(self):
        html = (FIXTURES / "mhlw_page.html").read_text()
        scraper = HTMLScraper(url="https://example.com", selector="table.m-tableFlex tbody tr")
        page1 = scraper.parse(html)
        page2 = scraper.parse(html)
        assert page1.content_hash == page2.content_hash

    def test_extract_source_urls(self):
        html = (FIXTURES / "mhlw_page.html").read_text()
        scraper = HTMLScraper(
            url="https://www.mhlw.go.jp/stf/shingi/other-syougai_446935_00001.html",
            selector="table.m-tableFlex tbody tr"
        )
        page = scraper.parse(html)
        source_urls = page.extract_links(base_url="https://www.mhlw.go.jp")
        assert "https://www.mhlw.go.jp/stf/newpage_72919.html" in source_urls
        assert "https://www.mhlw.go.jp/stf/newpage_72800.html" in source_urls

    def test_extract_latest_date(self):
        html = (FIXTURES / "mhlw_page.html").read_text()
        scraper = HTMLScraper(url="https://example.com", selector="table.m-tableFlex tbody tr")
        page = scraper.parse(html)
        assert page.latest_date == "2026-04-28"

    def test_get_text_content(self):
        html = (FIXTURES / "mhlw_page.html").read_text()
        scraper = HTMLScraper(url="https://example.com", selector="table.m-tableFlex tbody tr")
        page = scraper.parse(html)
        text = page.text_content
        assert "第55回" in text
        assert "2026年4月28日" in text
