"""Scrape GitHub trending repositories page."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime

TRENDING_URL = "https://github.com/trending"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_trending(time_range="daily", language="", spoken_language=""):
    """Scrape GitHub trending and return a list of repo dicts.

    Args:
        time_range: 'daily', 'weekly', or 'monthly'
        language: programming language filter (empty string = all)
        spoken_language: spoken language code filter (empty = all)

    Returns:
        List of dicts with keys: rank, name, url, description, language,
        stars, stars_today, forks, contributors.
    """
    params = {"since": time_range}
    if language:
        params["language"] = language
    if spoken_language:
        params["spoken_language_code"] = spoken_language

    resp = requests.get(TRENDING_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")

    repos = []
    for i, article in enumerate(articles, 1):
        repo = _parse_article(article, i)
        if repo:
            repos.append(repo)

    return repos


def _parse_article(article, rank):
    """Parse a single trending article element."""
    # Repo name and URL
    h2 = article.select_one("h2 a")
    if not h2:
        return None
    href = h2.get("href", "").strip()
    name = href.lstrip("/")
    url = f"https://github.com{href}"

    # Description
    p = article.select_one("p")
    description = p.get_text(strip=True) if p else ""

    # Language
    lang_span = article.select_one("[itemprop='programmingLanguage']")
    language = lang_span.get_text(strip=True) if lang_span else ""

    # Stars and forks
    stars = 0
    forks = 0
    links = article.select("a.Link")
    for link in links:
        href = link.get("href", "")
        text = link.get_text(strip=True).replace(",", "")
        if "stargazers" in href:
            try:
                stars = int(text)
            except ValueError:
                pass
        elif "forks" in href:
            try:
                forks = int(text)
            except ValueError:
                pass

    # Stars today
    stars_today = 0
    spans = article.select("span")
    for span in spans:
        text = span.get_text(strip=True)
        if "stars" in text and "today" in text:
            num = text.split("stars")[0].strip().replace(",", "")
            try:
                stars_today = int(num)
            except ValueError:
                pass

    # Contributors (built by)
    contributors = []
    for img in article.select("img.avatar"):
        alt = img.get("alt", "")
        if alt:
            contributors.append(alt)

    return {
        "rank": rank,
        "name": name,
        "url": url,
        "description": description,
        "language": language,
        "stars": stars,
        "stars_today": stars_today,
        "forks": forks,
        "contributors": contributors,
    }


def apply_filters(repos, filters):
    """Apply user filters to the scraped repo list."""
    filtered = repos

    min_stars = filters.get("min_stars", 0)
    if min_stars > 0:
        filtered = [r for r in filtered if r["stars"] >= min_stars]

    min_stars_today = filters.get("min_stars_today", 0)
    if min_stars_today > 0:
        filtered = [r for r in filtered if r["stars_today"] >= min_stars_today]

    exclude_kw = [k.lower() for k in filters.get("exclude_keywords", [])]
    if exclude_kw:
        filtered = [
            r for r in filtered
            if not any(kw in r["description"].lower() for kw in exclude_kw)
        ]

    include_kw = [k.lower() for k in filters.get("include_keywords", [])]
    if include_kw:
        filtered = [
            r for r in filtered
            if any(kw in r["description"].lower() for kw in include_kw)
        ]

    max_repos = filters.get("max_repos", 25)
    if max_repos > 0:
        filtered = filtered[:max_repos]

    return filtered


def format_repos_for_agent(repos):
    """Format repo data as a concise text block for the agent prompt."""
    lines = []
    for r in repos:
        contribs = ", ".join(r["contributors"][:5]) if r["contributors"] else "N/A"
        lines.append(
            f"{r['rank']}. {r['name']} | Stars: {r['stars']} "
            f"(+{r['stars_today']} today) | Forks: {r['forks']} | "
            f"Language: {r['language'] or 'N/A'} | "
            f"Contributors: {contribs}\n"
            f"   Description: {r['description']}\n"
            f"   URL: {r['url']}"
        )
    return "\n\n".join(lines)
