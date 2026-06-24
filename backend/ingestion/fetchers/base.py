from dataclasses import dataclass
from datetime import date
from hashlib import sha256


@dataclass
class FetchedItem:
    external_id: str
    title: str
    url: str
    content: str
    published_at: date | None = None


def content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()
