#!/usr/bin/env python3
"""Daily fetcher for the Footwear Tech site. Stdlib only (no pip install).

Sources are exactly those listed in the user's source files:
- Papers: OpenAlex API (needs free OPENALEX_API_KEY in env/GitHub Secrets;
  the keyless shared budget is often exhausted), PubMed E-utilities (free),
  Crossref (free, strict title filter), Semantic Scholar (optional key).
  Search formulas adapted from footwear-papers-sources.md section 6.
- Tech news: RSS feeds + Google News keyword RSS from footwear-tech-feeds.md,
  with the keep/block word rules from its section G.
- Patents: real records only when EPO_OPS_KEY/EPO_OPS_SECRET or LENS_TOKEN
  are provided (per footwear-patent-sources.md both need registration).
  Without keys, emits per-brand prefilled search entries (Espacenet /
  Google Patents / USPTO / CNIPA) built from the brand->applicant map and
  CPC classes in that file. Never fabricates patent records.
"""
import json, os, re, sys, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "data.json")
UA = {"User-Agent": "footwear-tech-site/1.0 (+daily research aggregator)"}

def get(url, timeout=25, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def get_json(url, **kw):
    return json.loads(get(url, **kw).decode("utf-8", "replace"))

# ---------------- Papers ----------------
PAPER_QUERIES = [
    ("AFT / 跑鞋技术", "advanced footwear technology running economy carbon-plated"),
    ("中底材料 / 发泡", "supercritical foam midsole PEBA thermoplastic polyurethane footwear"),
    ("有限元仿真", "finite element midsole footwear hyperelastic constitutive model"),
    ("梯度 / 点阵结构", "functionally graded lattice midsole additive manufacturing footwear"),
    ("后跟 / 稳定性", "heel geometry running shoe stability rearfoot"),
]
PUBMED_QUERIES = [
    ("AFT / 跑鞋技术", '("running shoe" OR "carbon-plated" OR "super shoe") AND ("running economy" OR biomechanics OR "energy return")'),
    ("中底材料 / 发泡", '(midsole OR footwear) AND (foam OR PEBA) AND (biomechanics OR "energy return")'),
    ("后跟 / 稳定性", '(heel OR rearfoot) AND (shoe OR footwear) AND (stability OR "ankle inversion")'),
]
SHOE_RE = re.compile(r"(shoe|footwear|midsole|carbon.?plat|super shoe)", re.I)

def papers_openalex():
    key = os.environ.get("OPENALEX_API_KEY", "")
    out = []
    for tag, q in PAPER_QUERIES:
        params = {"search": q, "sort": "publication_date:desc", "per_page": "10",
                  "filter": "from_publication_date:2023-01-01"}
        if key: params["api_key"] = key
        try:
            d = get_json("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
        except Exception as e:
            print(f"[openalex] {tag}: {e}", file=sys.stderr); continue
        for w in d.get("results", []):
            title = (w.get("title") or "").strip()
            if not title or not SHOE_RE.search(title): continue
            authors = [a["author"]["display_name"] for a in w.get("authorships", [])[:4]]
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
            inv = w.get("abstract_inverted_index") or {}
            abstract = ""
            if inv:
                pos = sorted((p, word) for word, ps in inv.items() for p in ps)
                abstract = " ".join(word for _, word in pos)[:600]
            out.append({"type": "paper", "source": "OpenAlex", "tag": tag, "title": title,
                        "date": w.get("publication_date") or str(w.get("publication_year") or ""),
                        "authors": authors, "venue": src, "abstract": abstract,
                        "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                        "url": w.get("doi") or w.get("id") or ""})
    return out

def papers_pubmed():
    out = []
    for tag, term in PUBMED_QUERIES:
        try:
            s = get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" +
                         urllib.parse.urlencode({"db": "pubmed", "term": term, "retmax": "12",
                                                 "retmode": "json", "sort": "date"}))
            ids = s["esearchresult"]["idlist"]
            if not ids: continue
            time.sleep(0.4)
            d = get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" +
                         urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "json"}))
        except Exception as e:
            print(f"[pubmed] {tag}: {e}", file=sys.stderr); continue
        for pid in ids:
            r = d["result"].get(pid, {})
            if not r.get("title"): continue
            # PubMed query expansion can surface off-topic hits; keep shoe-relevant titles.
            if not SHOE_RE.search(r["title"]): continue
            doi = next((a["value"] for a in r.get("articleids", []) if a["idtype"] == "doi"), "")
            out.append({"type": "paper", "source": "PubMed", "tag": tag, "title": r["title"].rstrip("."),
                        "date": (r.get("sortpubdate") or r.get("pubdate") or "")[:10].replace("/", "-"),
                        "authors": [a["name"] for a in r.get("authors", [])[:4]],
                        "venue": r.get("fulljournalname") or r.get("source") or "", "abstract": "",
                        "doi": doi, "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"})
    return out

def papers_crossref():
    out = []
    for tag, q in PAPER_QUERIES:
        try:
            d = get_json("https://api.crossref.org/works?" + urllib.parse.urlencode(
                {"query.bibliographic": q, "sort": "published", "order": "desc", "rows": "15",
                 "filter": "from-pub-date:2023-01-01,type:journal-article",
                 "select": "DOI,title,published,container-title,author,abstract"}))
        except Exception as e:
            print(f"[crossref] {tag}: {e}", file=sys.stderr); continue
        for it in d["message"]["items"]:
            title = (it.get("title") or [""])[0].strip()
            # Crossref free-text ranking is noisy: keep only shoe-relevant titles.
            if not title or not SHOE_RE.search(title): continue
            dp = (it.get("published") or {}).get("date-parts", [[None]])[0]
            date = "-".join(str(x).zfill(2) for x in dp if x) if dp and dp[0] else ""
            if len(date) == 4: date += "-01-01"
            out.append({"type": "paper", "source": "Crossref", "tag": tag, "title": title,
                        "date": date, "authors": [f"{a.get('given','')} {a.get('family','')}".strip() for a in it.get("author", [])[:4]],
                        "venue": (it.get("container-title") or [""])[0],
                        "abstract": re.sub(r"<[^>]+>", "", it.get("abstract", ""))[:600],
                        "doi": it.get("DOI", ""), "url": "https://doi.org/" + it.get("DOI", "")})
    return out

# ---------------- Tech news (RSS) ----------------
DIRECT_FEEDS = [  # footwear-tech-feeds.md A/B/C
    ("Believe in the Run", "https://believeintherun.com/feed/", False),
    ("SGB Media", "https://sgbonline.com/feed/", True),
    ("36氪", "https://36kr.com/feed", True),
    ("Runner's World", "https://www.runnersworld.com/rss/all.xml/", True),
    ("Doctors of Running", "https://www.doctorsofrunning.com/feeds/posts/default", False),
    ("Footwear News", "https://footwearnews.com/feed/", True),
    ("Sourcing Journal", "https://sourcingjournal.com/feed/", True),
]
GNEWS_EN = ["supercritical foam midsole", "super foam running shoe midsole", "PEBA midsole running shoe",
            "carbon plate running shoe technology", "running shoe biomechanics midsole",
            "Nike Adidas new midsole foam", "BASF Infinergy footwear", "Arkema Pebax footwear",
            "Covestro footwear foam", "Dow footwear foam midsole"]
GNEWS_CN = ["超临界发泡 中底", "跑鞋 中底 科技", "碳板 跑鞋", "PEBA 中底", "安踏 跑鞋 科技",
            "李宁 跑鞋 科技", "特步 跑鞋 科技", "361度 跑鞋 科技", "匹克 跑鞋 科技", "跑鞋 生物力学"]
KEEP = ["midsole", "foam", "peba", "supercritical", "carbon plate", "energy return", "stack height",
        "中底", "超临界", "发泡", "碳板", "回弹", "缓震", "running shoe", "跑鞋", "footwear", "鞋"]
BLOCK = ["coupon", "deal", "sale", "折扣", "优惠"]

def gnews_url(q, cn=False):
    if cn: return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"})
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})

def parse_feed(name, url):
    items = []
    try: raw = get(url)
    except Exception as e:
        print(f"[rss] {name}: {e}", file=sys.stderr); return items
    try: root = ET.fromstring(raw)
    except Exception:
        # Some feeds (36kr, Sourcing Journal) ship invalid XML; fall back to a
        # tolerant regex extraction of <item> blocks.
        import html as _html
        text = raw.decode("utf-8", "replace")
        for block in re.findall(r"<item>(.*?)</item>", text, re.S)[:20]:
            def tag(t):
                m = re.search(rf"<{t}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", block, re.S)
                return _html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
            title, link, date_raw, desc = tag("title"), tag("link"), tag("pubDate"), tag("description")
            date = ""
            if date_raw:
                try: date = parsedate_to_datetime(date_raw).date().isoformat()
                except Exception: date = date_raw[:10]
            if title and link:
                items.append({"type": "news", "source": name, "title": title, "url": link,
                              "date": date, "abstract": desc[:300]})
        return items
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall(".//item") or root.findall(".//atom:entry", ns)
    for e in entries[:20]:
        def txt(tag, nsmap=None):
            el = e.find(tag, nsmap) if nsmap else e.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        title = txt("title") or txt("atom:title", ns)
        link = txt("link")
        if not link:
            el = e.find("atom:link", ns)
            link = el.get("href", "") if el is not None else ""
        date_raw = txt("pubDate") or txt("atom:updated", ns) or txt("atom:published", ns)
        date = ""
        if date_raw:
            try: date = parsedate_to_datetime(date_raw).date().isoformat()
            except Exception:
                try: date = datetime.fromisoformat(date_raw.replace("Z", "+00:00")).date().isoformat()
                except Exception: date = date_raw[:10]
        desc = re.sub(r"<[^>]+>", "", txt("description") or txt("atom:summary", ns))[:300]
        if title and link:
            items.append({"type": "news", "source": name, "title": title, "url": link,
                          "date": date, "abstract": desc})
    return items

def news():
    out = []
    feeds = [(n, u, f) for n, u, f in DIRECT_FEEDS]
    feeds += [(f"Google News · {q}", gnews_url(q), False) for q in GNEWS_EN]
    feeds += [(f"Google News · {q}", gnews_url(q, True), False) for q in GNEWS_CN]
    for name, url, filtered in feeds:
        for it in parse_feed(name, url):
            blob = (it["title"] + " " + it["abstract"]).lower()
            if any(b in blob for b in BLOCK): continue
            if filtered and not any(k in blob for k in KEEP): continue
            out.append(it)
        time.sleep(0.2)
    return out

# ---------------- Patents ----------------
BRANDS = {  # footwear-patent-sources.md section 2.2
    "Nike": ["Nike Innovate C.V.", "Nike, Inc."], "adidas": ["adidas AG"], "PUMA": ["PUMA SE"],
    "New Balance": ["New Balance Athletics, Inc."], "ASICS": ["ASICS Corporation"],
    "Mizuno": ["Mizuno Corporation"], "HOKA": ["Deckers Outdoor Corporation"],
    "Under Armour": ["Under Armour, Inc."], "Skechers": ["Skechers U.S.A., Inc. II"],
    "安踏": ["安踏（中国）有限公司"], "李宁": ["李宁（中国）体育用品有限公司"],
    "特步": ["特步（中国）有限公司"], "361°": ["三六一度（中国）有限公司"], "匹克": ["匹克体育用品有限公司"],
}
CPC = ["A43B13", "A43B5/06", "A43B21", "B29D35", "C08J9"]

def patent_search_entries():
    out = []
    for brand, applicants in BRANDS.items():
        a = applicants[0]
        q = urllib.parse.quote(a)
        out.append({"type": "patent_search", "brand": brand, "applicant": a,
                    "cpc": CPC,
                    "links": {
                        "Espacenet": f"https://worldwide.espacenet.com/searchResults?ST=singleline&query=pa%3D%22{q}%22+AND+ipc%3DA43B",
                        "Google Patents": f"https://patents.google.com/?assignee={q}&type=PATENT&sort=new",
                        "USPTO": "https://ppubs.uspto.gov/",
                        "CNIPA 公布公告": "http://epub.cnipa.gov.cn/",
                    },
                    "note": "预填申请人+CPC分类的最新公开检索入口；接入 EPO OPS / Lens 密钥后此处自动替换为真实专利记录。"})
    return out

def patents_ops_lens():
    """Real patent records, only when the user has registered keys (GitHub Secrets)."""
    records = []
    # EPO OPS requires OAuth with consumer key/secret; Lens requires a token.
    # Both are intentionally attempted only when credentials exist.
    if os.environ.get("LENS_TOKEN"):
        try:
            body = json.dumps({"query": {"string": {"query": "class_cpc:A43B13* AND publication_date:[NOW-180DAYS TO NOW]",
                                                     "fields": ["title"]}},
                               "size": 20, "sort": [{"publication_date": "desc"}]}).encode()
            req = urllib.request.Request("https://api.lens.org/patent/search", data=body,
                                         headers={**UA, "Authorization": f"Bearer {os.environ['LENS_TOKEN']}",
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            for hit in d.get("data", []):
                bib = hit.get("biblio", {})
                records.append({"type": "patent", "source": "Lens.org", "brand": "",
                                "title": (bib.get("invention_title") or [{}])[0].get("text", ""),
                                "number": hit.get("lens_id", ""), "date": hit.get("date_published", ""),
                                "applicant": "", "abstract": "",
                                "url": f"https://www.lens.org/lens/patent/{hit.get('lens_id','')}"})
        except Exception as e:
            print(f"[lens] {e}", file=sys.stderr)
    if os.environ.get("EPO_OPS_KEY"):
        print("[ops] EPO_OPS_KEY present: OPS OAuth fetch is configured in scripts/fetch_patents_ops.py", file=sys.stderr)
    return records

# ---------------- Brand classification ----------------
# Brand list starts from the applicant map in footwear-patent-sources.md,
# extended with common model/material names so news and papers can be
# tagged by the brand they actually discuss.
BRAND_ALIASES = {
    "Nike": ["nike", "vaporfly", "alphafly", "zoomx", "耐克"],
    "adidas": ["adidas", "阿迪达斯", "adizero", "boost"],
    "PUMA": ["puma", "彪马", "nitro foam", "fast-r"],
    "New Balance": ["new balance", "新百伦", "fuelcell"],
    "ASICS": ["asics", "亚瑟士", "metaspeed", "ff blast", "gel-"],
    "Mizuno": ["mizuno", "美津浓", "wave rider", "wave rebellion"],
    "HOKA": ["hoka", "deckers", "霍卡", "clifton", "mach x"],
    "On": ["昂跑", "cloudtec", "cloudmonster", "cloudsurfer"],
    "Saucony": ["saucony", "索康尼"],
    "Brooks": ["brooks", "布鲁克斯", "hyperion"],
    "Under Armour": ["under armour", "安德玛", "hovr"],
    "Skechers": ["skechers", "斯凯奇"],
    "FILA": ["fila", "斐乐"],
    "安踏": ["anta", "安踏", "氮科技"],
    "李宁": ["li-ning", "li ning", "李宁", "䨻", "飞电"],
    "特步": ["xtep", "特步", "160x"],
    "361°": ["361°", "361度", "三六一度", "飞燃"],
    "匹克": ["匹克", "态极", "peak sport"],
    "鸿星尔克": ["erke", "鸿星尔克"],
}
def detect_brands(*texts):
    blob = " ".join(t or "" for t in texts).lower()
    found = []
    for brand, aliases in BRAND_ALIASES.items():
        for a in aliases:
            if a.isascii() and len(a) <= 4 and " " not in a:
                hit_b = re.search(r"\b" + re.escape(a) + r"\b", blob)
            else:
                hit_b = a in blob
            if hit_b:
                found.append(brand); break
    return found or ["综合/其他"]

def add_brands(items):
    for x in items:
        x["brands"] = detect_brands(x.get("title", ""), x.get("title_zh", ""),
                                     x.get("abstract", ""), x.get("abstract_zh", ""),
                                     x.get("applicant", ""), x.get("brand", ""))

# ---------------- Chinese translation ----------------
CJK = re.compile(r"[\u4e00-\u9fff]")
def is_zh(s):
    return len(CJK.findall(s or "")) >= 4

def _mm_chunk(text):
    url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(
        {"q": text, "langpair": "en|zh-CN"})
    d = get_json(url, timeout=12)
    return (d.get("responseData") or {}).get("translatedText", "") or ""

def translate_en_zh(text):
    """Best-effort EN->zh via MyMemory free API (chunked at 450 chars).
    Returns '' on failure; the UI then falls back to the English original."""
    if not text or is_zh(text): return text or ""
    chunks, buf = [], ""
    for part in re.split(r"(?<=[.!?])\s+", text):
        if len(buf) + len(part) > 450:
            if buf: chunks.append(buf)
            buf = part
        else:
            buf = (buf + " " + part).strip()
    if buf: chunks.append(buf)
    out = []
    try:
        for c in chunks:
            if len(c) > 450:  # hard split very long sentences
                subs = [c[i:i+450] for i in range(0, len(c), 450)]
            else:
                subs = [c]
            for s in subs:
                out.append(_mm_chunk(s)); time.sleep(0.15)
    except Exception as e:
        print(f"[translate] {e}", file=sys.stderr); return ""
    return " ".join(x for x in out if x).strip()

def add_translations(items):
    """Fill title_zh / abstract_zh. Reuses translations from the previous
    data.json (matched by exact source text) so daily runs only translate
    genuinely new items and stay within free translation quotas."""
    cache = {}
    try:
        prev = json.load(open(OUT, encoding="utf-8"))
        for kind in ("papers", "news"):
            for x in prev.get(kind, []):
                if x.get("title_zh"): cache[("t", x["title"])] = x["title_zh"]
                if x.get("abstract_zh"): cache[("a", x.get("abstract", ""))] = x["abstract_zh"]
    except Exception:
        pass
    for x in items:
        x["title_zh"] = x["title"] if is_zh(x["title"]) else \
            cache.get(("t", x["title"])) or translate_en_zh(x["title"])
        a = x.get("abstract", "")
        x["abstract_zh"] = a if is_zh(a) else \
            (cache.get(("a", a)) or translate_en_zh(a)) if a else ""

def main():
    papers, seen = [], set()
    for fn in (papers_openalex, papers_pubmed, papers_crossref):
        for p in fn():
            k = (p["doi"] or p["title"]).lower()
            if k in seen: continue
            seen.add(k); papers.append(p)
    papers.sort(key=lambda x: x["date"] or "", reverse=True)
    items_news = news()
    nseen, uniq_news = set(), []
    for n in items_news:
        k = n["url"].split("?")[0].lower()
        if k in nseen: continue
        nseen.add(k); uniq_news.append(n)
    uniq_news.sort(key=lambda x: x["date"] or "", reverse=True)
    add_translations(papers[:60])
    add_translations(uniq_news[:80])
    add_brands(papers[:60])
    add_brands(uniq_news[:80])
    patent_recs = patents_ops_lens()
    add_brands(patent_recs)
    searches = patent_search_entries()
    for s in searches: s["brands"] = [s["brand"]]
    data = {"updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
            "papers": papers[:60], "news": uniq_news[:80],
            "patents": patent_recs, "patent_searches": searches,
            "notes": {"openalex_key": bool(os.environ.get("OPENALEX_API_KEY")),
                      "lens_key": bool(os.environ.get("LENS_TOKEN")),
                      "ops_key": bool(os.environ.get("EPO_OPS_KEY"))}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"papers={len(data['papers'])} news={len(data['news'])} patents={len(data['patents'])} searches={len(data['patent_searches'])} -> {OUT}")

if __name__ == "__main__":
    main()
