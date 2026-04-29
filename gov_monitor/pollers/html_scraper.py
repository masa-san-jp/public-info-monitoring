from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


@dataclass
class ScrapedPage:
    content_hash: str
    text_content: str
    latest_date: str
    _soup: object

    def extract_links(self, base_url: str) -> list[str]:
        links = []
        for tag in self._soup.find_all("a", href=True):
            href = tag["href"]
            if href.startswith("http"):
                links.append(href)
            elif href.startswith("/"):
                parsed = urlparse(base_url)
                links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
        return list(dict.fromkeys(links))  # 順序を保ちつつ重複除去

    @property
    def row_count(self) -> int:
        rows = self._soup.find_all("tr")
        # ヘッダー行（th要素のみの行）を除く
        data_rows = [r for r in rows if r.find("td")]
        return len(data_rows)


class HTMLScraper:
    def __init__(self, url: str, selector: str):
        self.url = url
        self.selector = selector

    def parse(self, html: str) -> ScrapedPage:
        soup = BeautifulSoup(html, "html.parser")
        target = soup.select(self.selector)
        text_content = "\n".join(el.get_text(separator=" ", strip=True) for el in target)
        content_hash = sha256(text_content.encode()).hexdigest()

        latest_date = ""
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            latest_date = time_tag["datetime"]

        return ScrapedPage(
            content_hash=content_hash,
            text_content=text_content,
            latest_date=latest_date,
            _soup=soup,
        )
