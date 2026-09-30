"""Settings shared by every stage of the scraper."""

from pathlib import Path

# An honest user-agent: names the project and links to the repo, so a site
# owner who sees it in their logs can find out who is making the requests.
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Archaii/The-polite-scraper)"

# A request gives up after this many seconds instead of hanging forever.
TIMEOUT_SECONDS = 10

# Minimum wait between two real requests. Cache hits never wait.
DELAY_SECONDS = 0.5

START_URL = "https://books.toscrape.com/catalogue/page-1.html"

# Scope from the target classification: the first 3 catalogue pages only.
MAX_CATALOGUE_PAGES = 3

# Paths are relative to the project folder, so the script runs from any directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
