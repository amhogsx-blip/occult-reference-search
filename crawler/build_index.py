#!/usr/bin/env python3
# crawler/build_index.py
import os, re, json, time, hashlib, html
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# -------- Settings --------
SOURCES = [
    {
        "base": "https://embassyofthefreemind.com",
        "start": "https://embassyofthefreemind.com/en/library/online-catalogue/",
        "collection": "Embassy of the Free Mind",
        "allow_offsite": False,
        "max_pages": 30,
    },
    {
        "base": "https://www.occultlibrary.org",
        "start": "https://www.occultlibrary.org/community/resources",
        "collection": "Occult Library",
        "allow_offsite": False,
        "max_pages": 10,
    },
    {
        "base": "https://digitaloccultlibrary.commons.gc.cuny.edu",
        "start": "https://digitaloccultlibrary.commons.gc.cuny.edu/",
        "collection": "CUNY Digital Occult Library",
        "allow_offsite": False,
        "max_pages": 15,
    },
    {
        "base": "https://rmc.library.cornell.edu",
        "start": "https://rmc.library.cornell.edu/witchcraftcoll/",
        "collection": "Cornell Witchcraft Collection",
        "allow_offsite": False,
        "max_pages": 25,
    },
]

HEADERS = {
    "User-Agent": "OccultReferenceNetBot/1.0 (+https://www.theoccultreference.net/)",
    "Accept": "text/html,application/xhtml+xml",
}

TIMEOUT = 20
SLEEP_BETWEEN = 1.2  # be polite
MAX_TOTAL = 120      # overall result cap; raise if you want bigger indexes

# -------- Helpers --------

def clean_text(s: str) -> str:
    if not s: return ""
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def same_site(url, base):
    try:
        return urlparse(url).netloc == urlparse(base).netloc
    except:
        return False

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def extract_links(base, html_text):
    soup = BeautifulSoup(html_text, "lxml")
    out = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href: continue
        u = urljoin(base, href)
        out.append(u)
    return out

def extract_record(url, collection, html_text):
    soup = BeautifulSoup(html_text, "lxml")

    # Title
    title = soup.title.get_text(strip=True) if soup.title else url

    # Snippet: prefer meta description, else first paragraph-ish text
    desc = ""
    m = soup.find("meta", attrs={"name": "description"})
    if not m:
        m = soup.find("meta", attrs={"property": "og:description"})
    if m and m.get("content"):
        desc = m["content"]
    else:
        p = soup.find("p")
        if p:
            desc = p.get_text(" ", strip=True)[:400]
    # Clean
    title = clean_text(title)
    desc = clean_text(desc)

    return {
        "url": url,
        "title": title,
        "snippet": desc,
        "collection": collection,
        "author": "",
        "year": "",
        "tags": [],
    }

def crawl_source(src):
    base = src["base"]; start = src["start"]
    collection = src["collection"]
    allow_offsite = src.get("allow_offsite", False)
    max_pages = src.get("max_pages", 10)

    seen = set()
    queue = [start]
    results = []

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in seen: continue
        seen.add(url)

        # Stay on-site unless allow_offsite
        if not allow_offsite and not same_site(url, base):
            continue

        try:
            html_text = fetch(url)
        except Exception as e:
            # print(f"Skip {url}: {e}")
            continue

        # Extract record for this page
        try:
            rec = extract_record(url, collection, html_text)
            results.append(rec)
        except Exception:
            pass

        # Discover more links but don't explode
        try:
            links = extract_links(base, html_text)
            # Keep only a reasonable number from the same host
            for u in links[:50]:
                if u not in seen:
                    queue.append(u)
        except Exception:
            pass

        time.sleep(SLEEP_BETWEEN)

    return results

def dedupe(records):
    out = []
    seen = set()
    for r in records:
        key = r.get("url")
        if key and key not in seen:
            seen.add(key); out.append(r)
    return out

def main():
    pages_dir = os.environ.get("PAGES_DIR", "").strip()  # "" or "docs"
    target = os.path.join(pages_dir, "index.json") if pages_dir else "index.json"

    allrecs = []
    for src in SOURCES:
        try:
            recs = crawl_source(src)
            allrecs.extend(recs)
        except Exception:
            pass

    # Trim and dedupe
    allrecs = dedupe(allrecs)[:MAX_TOTAL]

    # Ensure deterministic-ish order: by collection, then title
    allrecs.sort(key=lambda r: (r.get("collection",""), r.get("title","")))

    # Write JSON
    os.makedirs(pages_dir, exist_ok=True) if pages_dir else None
    with open(target, "w", encoding="utf-8") as f:
        json.dump(allrecs, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(allrecs)} records to {target}")

if __name__ == "__main__":
    main()
