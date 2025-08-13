import csv
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

OPAC_BASE = "https://libraryopac.bennett.edu.in"
SEARCH_URL = f"{OPAC_BASE}/cgi-bin/koha/opac-search.pl"

# ---- tweakable settings ----
DEFAULT_IDX = "ti"            # ti = title search; use 'kw' for keyword, 'au' for author etc.
REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_PAGES = 0.7     # polite delay between page fetches

HEADERS = {
    "User-Agent": "BU-LRC-OPAC-Scraper/1.0 (+library.bennett.edu.in; contact: libraryhelpdesk@bennett.edu.in)"
}


def parse_biblionumber_from_href(href: str) -> str:
    """
    Extract biblionumber from URLs like:
    /cgi-bin/koha/opac-detail.pl?biblionumber=2739
    """
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
        if "biblionumber" in qs:
            return qs["biblionumber"][0]
    except Exception:
        pass
    return ""


def scrape_search_page(html: str):
    """
    Parse one OPAC search result page and return list of dicts.
    Tries multiple selectors to be robust across Koha themes.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 1) Common Koha OPAC: links to detail pages
    for a in soup.select('a[href*="opac-detail.pl?biblionumber="]'):
        # Heuristics to avoid header/footer nav links
        text = a.get_text(strip=True)
        if not text:
            continue

        # Title is usually on the <a> itself or in a surrounding .title element
        title = text
        parent = a.find_parent()
        author = ""
        # Try nearby author tags
        # Common classes seen: .author, .results_author, span[class*="author"]
        nearby_author = None
        for sel in (".author", ".results_author", 'span[class*="author"]'):
            nearby_author = parent.select_one(sel) if parent else None
            if not nearby_author:
                nearby_author = soup.select_one(sel)  # fallback: anywhere on line
            if nearby_author:
                break
        if nearby_author:
            author = nearby_author.get_text(" ", strip=True)

        bid = parse_biblionumber_from_href(a.get("href") or "")
        detail_url = urllib.parse.urljoin(OPAC_BASE, a.get("href"))

        results.append({
            "biblio_id": bid,
            "title": title,
            "author": author,
            "detail_url": detail_url
        })

    # De-duplicate by (biblio_id or title+author)
    deduped = []
    seen = set()
    for r in results:
        key = r["biblio_id"] or (r["title"].lower(), r["author"].lower())
        if key not in seen:
            deduped.append(r)
            seen.add(key)

    return deduped


def find_next_page_url(soup: BeautifulSoup):
    """
    Try to find a 'Next' pagination link.
    Koha themes vary; try common patterns:
      - a[rel="next"]
      - a.next, li.next > a
      - link text contains 'Next' or '›' or '»'
    """
    # rel=next
    a = soup.select_one('a[rel="next"]')
    if a and a.get("href"):
        return urllib.parse.urljoin(SEARCH_URL, a["href"])

    # class next
    a = soup.select_one("a.next, li.next > a")
    if a and a.get("href"):
        return urllib.parse.urljoin(SEARCH_URL, a["href"])

    # text contains Next or arrows
    for a in soup.select("a"):
        txt = a.get_text(" ", strip=True).lower()
        if any(token in txt for token in ("next", "›", "»")) and a.get("href"):
            return urllib.parse.urljoin(SEARCH_URL, a["href"])

    return None


def opac_search(keyword: str, idx: str = DEFAULT_IDX, max_pages: int = 10):
    """
    Scrape OPAC search results for `keyword`.
    idx:
      'ti' = title, 'kw' = keyword, 'au' = author, etc.
    max_pages: safety ceiling to avoid endless loops.
    """
    # First page params
    params = {
        "idx": idx,
        "q": keyword
    }

    all_rows = []
    next_url = None

    for page_no in range(1, max_pages + 1):
        if page_no == 1:
            url = SEARCH_URL
        else:
            url = next_url

        try:
            resp = requests.get(url, params=(params if page_no == 1 else None),
                                headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[!] Request failed on page {page_no}: {e}")
            break

        # Parse results
        page_rows = scrape_search_page(resp.text)
        print(f"[page {page_no}] parsed {len(page_rows)} rows")
        all_rows.extend(page_rows)

        # Check if more pages exist
        soup = BeautifulSoup(resp.text, "html.parser")
        next_url = find_next_page_url(soup)
        if not next_url:
            break

        time.sleep(SLEEP_BETWEEN_PAGES)

    # Final de-dup in case pages overlap
    final = []
    seen = set()
    for r in all_rows:
        key = r["biblio_id"] or (r["title"].lower(), r["author"].lower())
        if key not in seen:
            final.append(r)
            seen.add(key)

    return final


def save_csv(rows, filename):
    if not rows:
        print("No rows to save.")
        return
    fields = ["biblio_id", "title", "author", "detail_url"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Saved {len(rows)} rows to {filename}")


if __name__ == "__main__":
    # Example: all "Artificial Intelligence" titles (title-index search)
    KEYWORD = "Artificial Intelligence"
    results = opac_search(KEYWORD, idx="ti", max_pages=25)  # increase pages if needed
    print(f"Total found: {len(results)}")
    for r in results[:20]:
        print("-", r["title"], ("— " + r["author"]) if r["author"] else "")
        print("  ", r["detail_url"])
    save_csv(results, "opac_ai_books.csv")
