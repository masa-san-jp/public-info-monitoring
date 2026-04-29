from dataclasses import dataclass
import feedparser


@dataclass
class RSSEntry:
    id: str
    title: str
    url: str
    published_at: str
    description: str = ""


class RSSPoller:
    def __init__(self, url: str):
        self.url = url

    def parse(self, content: str) -> list[RSSEntry]:
        feed = feedparser.parse(content)
        entries = []
        for item in feed.entries:
            entry_id = item.get("id") or item.get("link", "")
            title = item.get("title", "")
            url = item.get("link", "")
            published_at = (
                item.get("published")
                or item.get("dc_date")
                or item.get("updated")
                or ""
            )
            entries.append(RSSEntry(
                id=entry_id,
                title=title,
                url=url,
                published_at=published_at,
                description=item.get("summary", ""),
            ))
        return entries

    def filter_new(self, entries: list[RSSEntry], seen_ids: set[str]) -> list[RSSEntry]:
        return [e for e in entries if e.id not in seen_ids]
