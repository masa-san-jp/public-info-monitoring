from dataclasses import dataclass, field


@dataclass
class UpdateEvent:
    id: str
    url: str
    source_url: str
    title: str
    detected_at: str
    published_at: str
    diff_text: str
    summary: str
    category: str
    monitor_id: str


@dataclass
class MonitorConfig:
    id: str
    name: str
    url: str
    type: str
    interval_minutes: int
    keywords: list[str] = field(default_factory=list)
    selector: str = ""
    notify: list[str] = field(default_factory=list)
