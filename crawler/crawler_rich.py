#!/usr/bin/env python3
# crawler/build_index.py
# Builds index.json with title, snippet, collection, domain, is_pdf, filesize, lastmod
# PLUS: keywords (from meta + heuristic), pub_date (ISO yyyy-mm-dd), thumb (URL)

import os, re, json, time, html, datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

SOURCES = [
    {"base":"https://embassyofthefreemind.com",
     "start":"https://embassyofthefreemind.com/en/library/online-catalogue/",
     "collection":"Embassy of the Free Mind","allow_offsite":False,"max_pages":30},
    {"base":"https://www.occultlibrary.org",
     "start":"https://www.occultlibrary.org/community/resources",
     "collection":"Occult Library","allow_offsite":False,"max_pages":12},
    {"base":"https://digitaloccultlibrary.commons.gc.cuny.edu",
     "start":"https://digitaloccultlibrary.commons.gc.cuny.edu/",
     "collection":"CUNY Digital Occult Library","allow_offsite":False,"max_pages":18},
    {"base":"https://rmc.library.cornell.edu",
     "start":"https://rmc.library.cornell.edu/witchcraftcoll/",
     "collection":"Cornell Witchcraft Collection","allow_offsite":False,"max_pages":30},
]

UA = "OccultReferenceNetBot/1.1 (+https://www.theoccultreference.net/)"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9"}
TIMEOUT = 25
SLEEP = 1.2
MAX_TOTAL = 400

# ---------- helpers ----------

def clean(s):
    if not s: return ""
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url): return urlparse(url).netloc

def absolute(page_url, href):
    try: return urljoin(page_url, href)
    except: return href

def safe_date_iso(s):
    # Try many common date formats → ISO yyyy-mm-dd
    if not s: return None
    s = s.strip()
    fmts = [
        "%Y-%m-%d", "%Y/%m/%d",
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
        "%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"
    ]
    for f in fmts:
        try:
            dt = datetime.datetime.strptime(s, f)
            return dt.date().isoformat()
        except Exception:
            pass
    # last resort: bare year or year-month
    m = re.search(r"\b(1[5-9]\d{2}|20\d{2})(?:-(0[1-9]|1[0-2]))?(?:-(0[1-9]|[12]\d|3[01]))?\b", s)
    if m:
        y = m.group(1)
        mo = m.group(2) or "01"
        d = m.group(3) or "01"
        return f"{y}-{mo}-{d}"
    return None

def head_info(url):
    """HEAD to detect type/size/date"""
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        ctype = (r.headers.get("Content-Type") or "").lower()
        is_pdf = "application/pdf" in ctype or url.lower().endswith(".pdf")
        size = r.headers.get("Content-Length")
        size = int(size) if size and size.isdigit() else None
        lastmod = safe_date_iso(r.headers.get("Last-Modified"))
        return is_pdf, size, lastmod
    except Exception:
        return url.lower().endswith(".pdf"), None, None

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def same_site(u, base):
    try:
        return urlparse(u).netloc == urlparse(base).netloc
    except:
        return False

def meta(soup, *names):
    for n in names:
        m = soup.find("meta", attrs={"name": n})
        if m and m.get("content"): return m["content"]
        p = soup.find("meta", attrs={"property": n})
        if p and p.get("content"): return p["content"]
    return None

def first_image_url(soup, page_url):
    cand = meta(soup, "og:image", "twitter:image")
    if cand: return absolute(page_url, cand)
    link_img = soup.find("link", attrs={"rel": "image_src"})
    if link_img and link_img.get("href"):
        return absolute(page_url, link_img["href"])
    img = soup.find("img", src=True)
    if img:
        return absolute(page_url, img["src"])
    return None

def extract_keywords(soup, title, snippet):
    kws = set()
    # meta keywords
    mk = meta(soup, "keywords")
    if mk:
        for k in re.split(r"[;,]\s*|\s{2,}", mk):
            k = clean(k.lower())
            if 2 < len(k) < 40:
                kws.add(k)

    # Heuristic: from headings and bold terms (RAKE-lite)
    pieces = []
    for sel in ["h1","h2","h3","strong","em","b"]:
        for t in soup.select(sel):
            pieces.append(t.get_text(" ", strip=True))
    pieces = " ".join(pieces + [title or "", snippet or ""]).lower()
    # Keep multi-word phrases up to length 4
    tokens = re.findall(r"[a-z][a-z\-']{2,}", pieces)
    # Compose phrases by sliding window
    for n in (4,3,2):
        for i in range(0, max(0, len(tokens)-n+1)):
            phrase = " ".join(tokens[i:i+n])
            if len(phrase) <= 40:
                kws.add(phrase)
    # Limit/normalize
    out = sorted(kws)
    return out[:20]

def extract_record(url, collection, html_text, is_pdf, size, lastmod):
    if is_pdf:
        title = url.split("/")[-1] or url
        snippet = "PDF document"
        thumb = None
        pub_date = lastmod
        keywords = []
    else:
        soup = BeautifulSoup(html_text, "lxml")
        # title
        title = soup.title.get_text(strip=True) if soup.title else url
        # snippet
        desc = meta(soup, "description", "og:description", "twitter:description")
        if not desc:
            p = soup.find("p")
            desc = p.get_text(" ", strip=True) if p else ""
        # date
        pub_date = (meta(soup, "article:published_time", "date", "dc.date", "DC.date", "DC.Date")
                    or (soup.find("time").get("datetime") if soup.find("time") and soup.find("time").get("datetime") else None))
        pub_date = safe_date_iso(pub_date)
        if not pub_date:
            # light regex hunt in visible text
            txt = soup.get_text(" ", strip=True)
            pub_date = safe_date_iso(txt)
        # thumb
        thumb = first_image_url(soup, url)
        # keywords
        keywords = extract_keywords(soup, title, desc)

        title = clean(title)
        desc = clean(desc)

    return {
        "url": url,
        "title": title,
        "snippet": snippet if is_pdf else desc,
        "collection": collection,
        "author": "",
        "year": pub_date[:4] if pub_date else "",
        "tags": keywords,                 # <--- keywords
        "domain": domain_of(url),
        "is_pdf": bool(is_pdf),
        "filesize": size,                 # bytes or null
        "lastmod": lastmod,               # ISO date or null (server header)
        "pub_date": pub_date,             # ISO date or null (page content)
        "thumb": thumb                    # image URL or null
    }

def extract_links(base, html_text, page_url):
    soup = BeautifulSoup(html_text, "lxml")
    out = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href: continue
        u = absolute(page_url, href)
        out.append(u)
    return out

def crawl_source(src):
    base = src["base"]; start = src["start"]; coll = src["collection"]
    allow = src.get("allow_offsite", False)
    max_pages = src.get("max_pages", 10)
    seen, queue, results = set(), [start], []

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in seen: continue
        seen.add(url)
        if not allow and not same_site(url, base): continue

        is_pdf, size, lastmod = head_info(url)
        if is_pdf:
            html_text = ""
        else:
            try:
                html_text = fetch(url)
            except Exception:
                continue

        try:
            rec = extract_record(url, coll, html_text, is_pdf, size, lastmod)
            results.append(rec)
        except Exception:
            pass

        # discover more links if HTML
        if not is_pdf and html_text:
            try:
                for u in extract_links(base, html_text, url)[:60]:
                    if u not in seen:
                        queue.append(u)
            except Exception:
                pass

        time.sleep(SLEEP)

    return results

def dedupe(recs):
    out, seen = [], set()
    for r in recs:
        u = r.get("url")
        if u and u not in seen:
            seen.add(u); out.append(r)
    return out

def main():
    pages_dir = os.environ.get("PAGES_DIR", "").strip()  # "" or "docs"
    target = os.path.join(pages_dir, "index.json") if pages_dir else "index.json"

    allrecs = []
    for src in SOURCES:
        try:
            allrecs.extend(crawl_source(src))
        except Exception:
            pass

    allrecs = dedupe(allrecs)[:MAX_TOTAL]
    # prefer pub_date then lastmod for sorting (newest first per collection)
    def sort_key(r):
        d = r.get("pub_date") or r.get("lastmod") or "0000-00-00"
        return (r.get("collection",""), d, r.get("title","").lower())
    allrecs.sort(key=sort_key, reverse=False)

    if pages_dir: os.makedirs(pages_dir, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(allrecs, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(allrecs)} records to {target}")

if __name__ == "__main__":
    main()
