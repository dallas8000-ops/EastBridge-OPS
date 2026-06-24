import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from django.utils.text import slugify

from .base import ParsedProcedure
from .fallback import get_fallback_procedures

logger = logging.getLogger(__name__)

USER_AGENT = "EastBridge-Ops-Intelligence/1.0 (+compliance monitoring)"
HTTP_TIMEOUT = 10.0
CONNECT_TIMEOUT = 5.0

TIP_PORTALS = {
    "UG": {
        "name": "Uganda Trade Portal",
        "base_url": "https://trade.go.ug/",
        "list_paths": ["procedures", "en/procedures", ""],
    },
    "KE": {
        "name": "Kenya Trade Portal",
        "base_url": "https://kenyatradeportal.go.ke/",
        "list_paths": ["procedure-hierarchy", "en/procedures", "procedures", ""],
    },
    "TZ": {
        "name": "Tanzania Trade Portal",
        "base_url": "https://trade.tanzania.go.tz/",
        "list_paths": ["procedures", "en/procedures", ""],
    },
    "RW": {
        "name": "Rwanda Trade Portal",
        "base_url": "https://rwandatrade.rw/",
        "list_paths": ["procedure", "procedures", "en/procedure", ""],
    },
}


def _is_unreachable_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException, OSError)):
        return True
    msg = str(exc).lower()
    return "getaddrinfo" in msg or "11001" in msg


def _http_get(url: str) -> str:
    timeout = httpx.Timeout(HTTP_TIMEOUT, connect=CONNECT_TIMEOUT)
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _infer_activity(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if "export" in text:
        return "export"
    if "import" in text:
        return "import"
    if "transit" in text:
        return "transit"
    if "register" in text or "incorporat" in text:
        return "registration"
    if "licen" in text or "permit" in text:
        return "licensing"
    if "customs" in text or "clearance" in text:
        return "customs"
    return "other"


def _parse_steps_from_page(soup: BeautifulSoup) -> list[dict]:
    steps: list[dict] = []
    step_containers = soup.select(
        ".procedure-step, .step, ol.steps li, .timeline-item, article.step, "
        "[class*='step'] li, .accordion-item"
    )

    for idx, container in enumerate(step_containers[:20]):
        title_el = container.select_one("h2, h3, h4, .step-title, .title, strong")
        title = title_el.get_text(strip=True) if title_el else container.get_text(strip=True)[:120]
        if len(title) < 5:
            continue

        desc_el = container.select_one("p, .description, .content")
        description = desc_el.get_text(strip=True) if desc_el else container.get_text(strip=True)
        agency_el = container.select_one("[class*='agency'], .institution, em")
        agency = agency_el.get_text(strip=True) if agency_el else ""

        docs = [li.get_text(strip=True) for li in container.select("ul li")[:10]]

        steps.append({
            "sort_order": idx,
            "title": title[:255],
            "description": description[:4000],
            "responsible_agency": agency[:255],
            "documents_required": docs,
        })

    if not steps:
        headings = soup.select("h2, h3")
        for idx, heading in enumerate(headings[:10]):
            title = heading.get_text(strip=True)
            if len(title) < 8:
                continue
            sibling = heading.find_next_sibling("p")
            description = sibling.get_text(strip=True) if sibling else title
            steps.append({
                "sort_order": idx,
                "title": title[:255],
                "description": description[:4000],
                "responsible_agency": "",
                "documents_required": [],
            })

    return steps


def _parse_procedure_page(url: str, country_code: str) -> ParsedProcedure | None:
    try:
        html = _http_get(url)
    except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
        logger.warning("Failed to fetch procedure %s: %s", url, exc)
        return None

    soup = BeautifulSoup(html, "lxml")
    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else "Trade procedure"
    if len(title) < 5:
        return None

    summary_el = soup.select_one("meta[name='description'], .summary, .lead, article p")
    summary = summary_el.get("content", "") if summary_el and summary_el.name == "meta" else ""
    if not summary and summary_el:
        summary = summary_el.get_text(strip=True)[:1000]

    steps = _parse_steps_from_page(soup)
    if not steps:
        return None

    activity = _infer_activity(title, summary)

    days_match = re.search(r"(\d+)\s*(?:days|working days)", html, re.I)
    cost_match = re.search(r"(?:cost|fee)[:\s]*([^\n<]{3,60})", html, re.I)

    external_id = f"{country_code}-{slugify(title)[:200]}"
    return ParsedProcedure(
        external_id=external_id,
        title=title[:500],
        url=url,
        summary=summary[:2000],
        activity_type=activity,
        steps=steps,
        estimated_days=int(days_match.group(1)) if days_match else None,
        estimated_cost=cost_match.group(1).strip() if cost_match else "",
    )


def _discover_from_list_url(list_url: str, base_url: str, max_items: int) -> tuple[list[str], BaseException | None]:
    try:
        html = _http_get(list_url)
    except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
        logger.debug("List URL failed %s: %s", list_url, exc)
        return [], exc if _is_unreachable_error(exc) else None

    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    links: list[str] = []
    base_host = urlparse(base_url).netloc

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        text = anchor.get_text(strip=True)
        if not href or len(text) < 8:
            continue

        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != base_host:
            continue

        lower = f"{text} {href}".lower()
        if not any(
            kw in lower
            for kw in ("procedure", "import", "export", "register", "licen", "customs", "clearance", "permit")
        ):
            continue

        if url in seen or url.rstrip("/") == list_url.rstrip("/"):
            continue
        seen.add(url)
        links.append(url)
        if len(links) >= max_items:
            break

    return links, None


def discover_procedure_links(country_code: str, max_items: int = 12) -> list[str]:
    portal = TIP_PORTALS.get(country_code)
    if not portal:
        return []

    base_url = portal["base_url"]
    list_paths = portal.get("list_paths", [portal.get("list_path", "")])

    for path in list_paths:
        list_url = urljoin(base_url, path) if path else base_url
        links, fatal = _discover_from_list_url(list_url, base_url, max_items)
        if links:
            logger.info("Found %d procedure links for %s at %s", len(links), country_code, list_url)
            return links
        if fatal:
            logger.info("TIP portal unreachable for %s — using fallback", country_code)
            return []

    logger.info("No procedure list for %s — using fallback", country_code)
    return []


def fetch_country_procedures(
    country_code: str,
    max_items: int = 10,
    offline: bool = False,
) -> tuple[list[ParsedProcedure], str]:
    if offline:
        return get_fallback_procedures(country_code), "fallback"

    procedures: list[ParsedProcedure] = []

    for url in discover_procedure_links(country_code, max_items=max_items):
        try:
            parsed = _parse_procedure_page(url, country_code)
        except Exception as exc:
            logger.warning("Unexpected error parsing %s: %s", url, exc)
            continue
        if parsed and parsed.steps:
            procedures.append(parsed)

    if procedures:
        return procedures, "live"

    return get_fallback_procedures(country_code), "fallback"
