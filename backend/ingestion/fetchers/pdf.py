"""PDF document fetcher for legal gazettes and court documents."""

import logging
import re
from io import BytesIO
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .base import FetchedItem

logger = logging.getLogger(__name__)

USER_AGENT = "EastBridge-Ops-Intelligence/1.0 (+https://github.com/eastbridge; compliance monitoring)"

PDF_LINK_SELECTOR = "a[href$='.pdf' i]"


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def _extract_text_from_pdf_url(pdf_url: str) -> str:
    """Extract text from a PDF URL using available libraries."""
    try:
        pdf_content = _http_get(pdf_url)
    except httpx.HTTPError as exc:
        logger.warning("Failed to download PDF %s: %s", pdf_url, exc)
        return ""

    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not available, falling back to basic text extraction")
        return _basic_pdf_extraction(pdf_url, pdf_content)

    try:
        reader = PdfReader(BytesIO(pdf_content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning("Failed to extract text from PDF %s: %s", pdf_url, exc)
        return ""
    return text[:10000]  # Limit to prevent excessive processing


def _basic_pdf_extraction(pdf_url: str, content: bytes) -> str:
    """Basic text extraction when PDF libraries are unavailable."""
    filename = urlparse(pdf_url).path.rsplit("/", 1)[-1]
    filename = re.sub(r"\.pdf$", "", filename, flags=re.IGNORECASE)
    filename = re.sub(r"[._-]", " ", filename).strip()

    # Simple extraction of printable ASCII text from the raw bytes
    text = content.decode("latin-1", errors="ignore")
    readable = re.sub(r"[^\x20-\x7E\n\r\t]", " ", text)
    readable = re.sub(r"\s+", " ", readable).strip()
    return readable[:5000] if len(readable) > 100 else filename


def fetch_pdf_list(
    list_url: str,
    pdf_link_selector: str = PDF_LINK_SELECTOR,
    max_items: int = 10,
    base_url: str | None = None,
) -> list[FetchedItem]:
    """Fetch PDF documents from a listing page."""
    try:
        html_content = _http_get(list_url).decode("utf-8", errors="ignore")
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch PDF list from %s: %s", list_url, exc)
        return []

    soup = BeautifulSoup(html_content, "lxml")
    base = base_url or list_url
    seen_urls: set[str] = set()
    items: list[FetchedItem] = []

    for link in soup.select(pdf_link_selector):
        if len(items) >= max_items:
            break

        href = link.get("href")
        if not href:
            continue

        url = urljoin(base, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Get link text as title, falling back to the surrounding element
        title = link.get_text(strip=True)
        if len(title) < 5 and link.parent:
            title = link.parent.get_text(strip=True)
        if not title:
            title = url.split("/")[-1]

        content = _extract_text_from_pdf_url(url) or title

        items.append(
            FetchedItem(
                external_id=url[:512],
                title=title[:500],
                url=url,
                content=content[:8000],
                published_at=None,
            )
        )

    return items


def fetch_gazette_notices(
    gazette_url: str,
    max_items: int = 10,
) -> list[FetchedItem]:
    """Fetch gazette notices (PDF links) from a gazette listing page."""
    return fetch_pdf_list(
        list_url=gazette_url,
        max_items=max_items,
    )
