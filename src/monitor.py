"""Stage 1: Fetch items from Brave Search, GitHub Trending, and RSS feeds."""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from github import Auth, Github, GithubException

load_dotenv()

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"
GITHUB_USER = "rahilpopat"


def _load_sources() -> dict[str, Any]:
    """Load sources.yaml config."""
    with open(CONFIG_DIR / "sources.yaml") as f:
        return yaml.safe_load(f)


def _strip_html(text: str) -> str:
    """Strip HTML tags and truncate to 400 chars."""
    if not text:
        return ""
    clean = BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
    return clean[:400]


def _deduplicate(items: list[dict]) -> list[dict]:
    """Deduplicate items by URL."""
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(item)
    return unique


# --- Brave Search ---

def fetch_brave(sources: dict) -> list[dict]:
    """Fetch results from Brave Search API for each query."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        logger.warning("BRAVE_API_KEY not set — skipping Brave Search")
        return []

    items: list[dict] = []
    queries = sources.get("brave_queries", [])

    for query in queries:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
                params={"q": query, "count": 5, "freshness": "pd"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            for result in data.get("web", {}).get("results", []):
                items.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "summary": _strip_html(result.get("description", "")),
                    "source": "brave",
                    "published": result.get("page_age", ""),
                    "stars": 0,
                })
        except requests.RequestException as e:
            logger.error("Brave query '%s' failed: %s", query, e)

    logger.info("  Brave: %d results from %d queries", len(items), len(queries))
    return items


# --- GitHub Trending ---

def fetch_github_trending(sources: dict) -> tuple[list[dict], list[dict]]:
    """Search GitHub repos by topic, and fetch starred repos as signal."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.warning("GITHUB_TOKEN not set — skipping GitHub")
        return [], []

    g = Github(auth=Auth.Token(token))
    items: list[dict] = []
    seen_repos: set[str] = set()
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    topics = sources.get("github_topics", [])
    for topic in topics:
        query = f"topic:{topic} created:>={seven_days_ago} stars:>10"
        try:
            results = g.search_repositories(query, sort="stars", order="desc")
            count = 0
            for repo in results:
                if count >= 5:
                    break
                if repo.full_name in seen_repos:
                    continue
                seen_repos.add(repo.full_name)
                items.append({
                    "title": f"{repo.full_name}: {repo.description or 'No description'}",
                    "url": repo.html_url,
                    "summary": _strip_html(repo.description or "")[:400],
                    "source": "github",
                    "published": repo.created_at.isoformat() if repo.created_at else "",
                    "stars": repo.stargazers_count,
                })
                count += 1
        except GithubException as e:
            logger.error("GitHub topic '%s' search failed: %s", topic, e)

    logger.info("  GitHub trending: %d repos from %d topics", len(items), len(topics))

    # Starred repos signal
    starred: list[dict] = []
    try:
        user = g.get_user(GITHUB_USER)
        count = 0
        for repo in user.get_starred():
            if count >= 10:
                break
            starred.append({
                "full_name": repo.full_name,
                "topics": repo.get_topics() if hasattr(repo, "get_topics") else [],
                "description": repo.description or "",
            })
            count += 1
    except GithubException as e:
        logger.error("Failed to fetch starred repos: %s", e)

    logger.info("  GitHub starred signal: %d repos", len(starred))
    return items, starred


# --- Recent Commits ---

def fetch_commits() -> list[dict]:
    """Fetch recent commits for the user.

    Primary: GitHub Events API PushEvent commits.
    Fallback: list user repos and fetch commits directly from each.
    """
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    commits: list[dict] = []

    # --- Try Events API first ---
    page = 1
    while page <= 3:
        try:
            resp = requests.get(
                f"https://api.github.com/users/{GITHUB_USER}/events/public",
                headers=headers,
                params={"per_page": 100, "page": page},
                timeout=10,
            )
            resp.raise_for_status()
            events = resp.json()
            if not events:
                break
            for event in events:
                if event.get("type") != "PushEvent":
                    continue
                repo_name = event.get("repo", {}).get("name", "")
                created_at = event.get("created_at", "")
                for commit in event.get("payload", {}).get("commits", []):
                    message = commit.get("message", "").split("\n")[0][:120]
                    commits.append({
                        "repo": repo_name,
                        "message": message,
                        "date": created_at,
                    })
            page += 1
        except requests.RequestException as e:
            logger.error("GitHub Events API page %d failed: %s", page, e)
            break

    # --- Fallback: fetch commits directly from user's repos ---
    if not commits:
        logger.warning("  Events API returned 0 commits — falling back to repo commits API")
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        try:
            resp = requests.get(
                f"https://api.github.com/users/{GITHUB_USER}/repos",
                headers=headers,
                params={"sort": "pushed", "per_page": 10},
                timeout=10,
            )
            resp.raise_for_status()
            repos = resp.json()

            for repo in repos:
                repo_full = repo.get("full_name", "")
                try:
                    cresp = requests.get(
                        f"https://api.github.com/repos/{repo_full}/commits",
                        headers=headers,
                        params={"author": GITHUB_USER, "since": since, "per_page": 20},
                        timeout=10,
                    )
                    cresp.raise_for_status()
                    for c in cresp.json():
                        commit_data = c.get("commit", {})
                        message = commit_data.get("message", "").split("\n")[0][:120]
                        date = commit_data.get("author", {}).get("date", "")
                        commits.append({
                            "repo": repo_full,
                            "message": message,
                            "date": date,
                        })
                except requests.RequestException as e:
                    logger.error("  Commits for %s failed: %s", repo_full, e)
        except requests.RequestException as e:
            logger.error("  Repos list failed: %s", e)

    logger.info("  Recent commits: %d", len(commits))
    return commits


# --- RSS Feeds ---

def fetch_rss(sources: dict) -> list[dict]:
    """Fetch items from RSS feeds, stripping HTML from summaries."""
    items: list[dict] = []
    feeds = sources.get("rss_feeds", [])

    for feed_cfg in feeds:
        url = feed_cfg["url"]
        name = feed_cfg["name"]
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:10]:
                summary = _strip_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                items.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": summary,
                    "source": name,
                    "published": entry.get("published", ""),
                    "stars": 0,
                })
        except Exception as e:
            logger.error("RSS feed '%s' failed: %s", name, e)

    logger.info("  RSS: %d items from %d feeds", len(items), len(feeds))
    return items


# --- Main ---

def fetch_all() -> tuple[list[dict], list[dict], list[dict]]:
    """Fetch items, starred repos, and recent commits. Returns (items, starred, commits)."""
    sources = _load_sources()

    brave_items = fetch_brave(sources)
    github_items, starred = fetch_github_trending(sources)
    commits = fetch_commits()
    rss_items = fetch_rss(sources)

    all_items = _deduplicate(brave_items + github_items + rss_items)
    logger.info("  Total deduplicated items: %d", len(all_items))

    return all_items, starred, commits


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    items, starred, commits = fetch_all()

    print(f"\n{'='*60}")
    print(f"MONITOR RESULTS")
    print(f"{'='*60}")
    print(f"Total items: {len(items)}")

    # Source breakdown
    source_counts: dict[str, int] = {}
    for item in items:
        src = item["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
    print(f"Source breakdown: {source_counts}")

    # First 3 items
    print(f"\nFirst 3 items:")
    for i, item in enumerate(items[:3], 1):
        print(f"  {i}. [{item['source']}] {item['title']}")
        print(f"     URL: {item['url']}")
        print(f"     Summary: {item['summary'][:100]}...")

    # Commits
    print(f"\n{'='*60}")
    print(f"COMMITS: {len(commits)}")
    print(f"{'='*60}")
    if commits:
        for c in commits[:5]:
            print(f"  [{c['date'][:10]}] {c['repo']} — {c['message']}")
    else:
        print("  WARNING: No commits found! This must be fixed before moving on.")
