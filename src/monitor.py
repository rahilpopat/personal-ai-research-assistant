"""Stage 1: Fetch items from Brave Search, GitHub Trending, and RSS feeds."""


def fetch_all() -> tuple[list, list, list]:
    """Fetch items, starred repos, and recent commits. Returns (items, starred, commits)."""
    # TODO: Implement in Session 2
    return [], [], []


if __name__ == "__main__":
    items, starred, commits = fetch_all()
    print(f"Items: {len(items)}, Starred: {len(starred)}, Commits: {len(commits)}")
