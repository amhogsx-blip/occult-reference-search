# Builds public/index.json from four sources (free, no servers).
import time, re, hashlib, json
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

SEEDS = [
  "https://embassyofthefreemind.com/en/library/online-catalogue/?mode=gallery&view=horizontal&sort=random%7B1517048201764%7D%20asc&page=1&fq%5B%5D=search_s_digitized_publication:%22Ja%22&reverse=0",
  "https://www.occultlibrary.org/community/resources",
  "https://digitaloccultlibrary.commons.gc.cuny.edu/",
  "https://rmc.library.cornell.edu/witchcraftcoll/"
]
HEADERS = {"User-Agent":"T.O.R.N. static crawler (contact: admin@occultreference.net)"}
ALLOWED = {urlparse(u).netloc for u in SEEDS}
SEEN=set()
DOCS=[]

def clean(x): 
    return re.sub(r'\s+',' ', x or '').strip()

def to_int_year(x):
    if not x: return None
    m=re.search(r'(1[4-9]\d{2}|20\d{2})', x)  # 1400–2099
    return int(m.group(1)) if m else None

def make_id(url): 
    return hashlib.md5(url.encode()).hexdigest()

def soup_get(url):
    try:
        r=requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code!=200 or "text/html" not in r.headers.get("Content-Type",""):
            return None, None
        return r, BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None, None

def base_doc(url, title, snippet):
    return {
      "id": make_id(url),
      "url": url,
      "title": title[:250] if title else url,
      "snippet": (snippet or "")[:600],
      "source": urlparse(url).netloc,
      "collection": None,
      "type": None,
      "author": None,
      "year": None,
      "date": None,
      "tags": []
    }

# --- Extractors per domain ----------------------------------------------------

def extract_eotfm(url, soup):
    title = clean(soup.find("h1").get_text() if soup.find("h1") else soup.title.get_text() if soup.title else url)
    snippet = clean(next((p.get_text() for p in soup.select("div.item-description p, .content p, .item p") if clean(p.get_text())), ""))
    doc = base_doc(url, title, snippet)
    doc["collection"]="Embassy of the Free Mind – Online Catalogue"
    doc["type"]="book"
    meta_text = " ".join([clean(el.get_text()) for el in soup.select("div.meta, .field, .item-info, .metadata")])
    # Author heuristics
    m = re.search(r'Author(?:s)?:\s*([^|;]+)', meta_text, re.I)
    if m: doc["author"]=clean(m.group(1))
    # Year
    y = to_int_year(meta_text or title)
    if y: 
        doc["year"]=y
        doc["date"]=f"{y}-01-01"
    return doc

def extract_occultlibrary(url, soup):
    title = clean(soup.find("h1").get_text() if soup.find("h1") else soup.title.get_text() if soup.title else url)
    snippet = clean(next((p.get_text() for p in soup.select("article p, .entry-content p, .bbp-body p") if clean(p.get_text())), ""))
    doc = base_doc(url, title, snippet)
    doc["collection"]="OccultLibrary.org – Community Resources"
    doc["type"]="resource"
    cats=[clean(a.get_text()) for a in soup.select(".cat-links a, .tags-links a, .entry-meta a") if clean(a.get_text())]
    doc["tags"]=sorted(list(set(cats)))[:10]
    y = to_int_year(" ".join([title, snippet]))
    if y: 
        doc["year"]=y
        doc["date"]=f"{y}-01-01"
    return doc

def extract_cuny(url, soup):
    title = clean(soup.find("h1").get_text() if soup.find("h1") else soup.title.get_text() if soup.title else url)
    snippet = clean(next((p.get_text() for p in soup.select("article p, .entry-content p") if clean(p.get_text())), ""))
    doc = base_doc(url, title, snippet)
    doc["collection"]="CUNY Digital Occult Library"
    doc["type"]="article" if ("/category/" in url or soup.select("article")) else "resource"
    author_el = soup.select_one(".byline .author, .author a, .vcard .fn")
    if author_el: doc["author"]=clean(author_el.get_text())
    date_el = soup.select_one("time[datetime], .posted-on time")
    if date_el and date_el.has_attr("datetime"):
        doc["date"]=date_el["datetime"][:10]
        try: doc["year"]=int(doc["date"][:4])
        except: pass
    else:
        y=to_int_year(snippet); 
        if y: doc["year"]=y; doc["date"]=f"{y}-01-01"
    tags=[clean(a.get_text()) for a in soup.select(".tags a, .tagcloud a, .cat-links a") if clean(a.get_text())]
    if tags: doc["tags"]=sorted(list(set(tags)))[:10]
    return doc

def extract_cornell(url, soup):
    title = clean(soup.find("h1").get_text() if soup.find("h1") else soup.title.get_text() if soup.title else url)
    snippet = clean(next((p.get_text() for p in soup.select("main p, .content p") if clean(p.get_text())), ""))
    doc = base_doc(url, title, snippet)
    doc["collection"]="Cornell Witchcraft Collection"
    meta_text = " ".join([clean(el.get_text()) for el in soup.select("table, .metadata, .item-meta")])
    doc["type"]="exhibition page"
    if re.search(r'Author|Printer|Imprint|Call Number', meta_text, re.I):
        doc["type"]="item"
    m=re.search(r'Author:\s*([^|;,\n]+)', meta_text, re.I)
    if m: doc["author"]=clean(m.group(1))
    y = to_int_year(meta_text or title)
    if y: 
        doc["year"]=y
        doc["date"]=f"{y}-01-01"
    tags=[clean(a.get_text()) for a in soup.select("nav a, .sidebar a") if clean(a.get_text()) and len(a.get_text())<30]
    if tags: doc["tags"]=sorted(list(set(tags)))[:10]
    return doc

def extract(url):
    r, soup = soup_get(url)
    if not soup: return None
    host = urlparse(url).netloc
    try:
        if "embassyofthefreemind.com" in host: return extract_eotfm(url, soup)
        if "occultlibrary.org" in host:       return extract_occultlibrary(url, soup)
        if "commons.gc.cuny.edu" in host:     return extract_cuny(url, soup)
        if "rmc.library.cornell.edu" in host: return extract_cornell(url, soup)
        # fallback
        title=clean(soup.title.get_text() if soup.title else url)
        sn=clean(next((p.get_text() for p in soup.find_all("p") if clean(p.get_text())), ""))
        return base_doc(url, title, sn)
    except Exception:
        return None

def crawl(seed, max_pages=250):
    q=[seed]
    while q and len(SEEN)<max_pages:
        url=q.pop(0)
        if url in SEEN: continue
        SEEN.add(url)
        doc=extract(url)
        if doc: DOCS.append(doc)
        time.sleep(0.7)  # polite
        r, soup = soup_get(url)
        if not soup: continue
        for a in soup.find_all("a", href=True):
            link=urljoin(url,a["href"])
            p=urlparse(link)
            if p.netloc in ALLOWED and p.scheme in ("http","https"):
                path=p.path.lower()
                if any(path.endswith(ext) for ext in (".pdf",".jpg",".jpeg",".png",".gif",".zip",".mp4",".mp3")):
                    continue
                if "#comment" in link or "#respond" in link: 
                    continue
                if link not in SEEN: q.append(link)

# Crawl all seeds
for s in SEEDS: 
    crawl(s, max_pages=600)

# De-dup (keep longest snippet)
uniq={}
for d in DOCS:
    k=(d["title"].lower(), d["source"])
    if k not in uniq or len(d.get("snippet",""))>len(uniq[k].get("snippet","")):
        uniq[k]=d

DOCS=list(uniq.values())

# Write the static index for the frontend
with open("index.json","w",encoding="utf-8") as f:
    json.dump(DOCS, f, ensure_ascii=False)
  Write index.json to repo root

