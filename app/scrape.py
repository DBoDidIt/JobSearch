from typing import Optional

import requests
from bs4 import BeautifulSoup


def scrape_job_description(url: str, *, timeout_seconds: int = 15, max_chars: int = 12000) -> str:
    """
    Lightweight scraper: extracts visible text and truncates.
    """
    resp = requests.get(
        url,
        timeout=timeout_seconds,
        headers={"User-Agent": "JobSearch Local Resume Builder/1.0"},
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script/style elements.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Normalize whitespace.
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    cleaned = "\n".join(lines)
    return cleaned[:max_chars]


def truncate(s: Optional[str], max_chars: int) -> str:
    if not s:
        return ""
    return s[:max_chars]

