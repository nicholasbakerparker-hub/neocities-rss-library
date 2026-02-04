import os
import json
import re
from datetime import datetime, timezone
import feedparser
from dateutil import parser as dtp

# Your RSS feeds
LETTERBOXD_RSS = "https://letterboxd.com/Jurrasic_parker/rss/"
GOODREADS_READ_RSS = "https://www.goodreads.com/review/list_rss/147391839?shelf=read"

DATA_DIR = "data"
SITE_DIR = "site"

FILMS_JSONL = os.path.join(DATA_DIR, "films.jsonl")
BOOKS_JSONL = os.path.join(DATA_DIR, "books.jsonl")

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SITE_DIR, exist_ok=True)

def load_ids(path):
    ids = set()
    if not os.path.exists(path):
        return ids
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                ids.add(obj["id"])
            except:
                pass
    return ids

def append_jsonl(path, items):
    if not items:
        return
    with open(path, "a", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def parse_date(entry):
    for key in ("published", "updated"):
        if getattr(entry, key, None):
            try:
                return dtp.parse(getattr(entry, key)).astimezone(timezone.utc).isoformat()
            except:
                pass
    return datetime.now(timezone.utc).isoformat()

def stars_to_5(star_str):
    full = star_str.count("★")
    half = 1 if "½" in star_str else 0
    val = full + (0.5 if half else 0.0)
    return int(round(val))

def rating_to_stars(n):
    if n is None:
        return None
    return "★" * n + "☆" * (5 - n)

def normalize_letterboxd(feed_url):
    d = feedparser.parse(feed_url)
    out = []
    for e in d.entries:
        link = e.get("link", "").strip()
        guid = e.get("id", "").strip() or link
        title = (e.get("title", "") or "").strip()
        summary = (e.get("summary", "") or "").strip()

        rating = None
        m = re.search(r"(★+½?)", title)
        if m:
            try:
                rating = stars_to_5(m.group(1))
            except:
                rating = None

        out.append({
            "id": f"letterboxd:{guid}",
            "title": title,
            "link": link,
            "rating_stars": rating_to_stars(rating),
            "review_html": summary,
            "date_utc": parse_date(e),
        })
    return out

def normalize_goodreads(feed_url):
    d = feedparser.parse(feed_url)
    out = []
    for e in d.entries:
        link = e.get("link", "").strip()
        guid = e.get("id", "").strip() or link
        title = (e.get("title", "") or "").strip()
        summary = (e.get("summary", "") or "").strip()

        rating = None
        m = re.search(r"rating:\s*([0-5])", summary, re.IGNORECASE)
        if m:
            try:
                rating = int(m.group(1))
            except:
                rating = None

        out.append({
            "id": f"goodreads:{guid}",
            "title": title,
            "link": link,
            "rating_stars": rating_to_stars(rating),
            "review_html": summary,
            "date_utc": parse_date(e),
        })
    return out

def load_all_jsonl(path):
    items = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    items.append(json.loads(line))
                except:
                    pass
    return sorted(items, key=lambda x: x.get("date_utc", ""), reverse=True)

def render_page(title, items, out_path, gen_time):
    # Decide which CSS to use based on page title
    css_file = "css/films.css" if title.lower() == "films" else "css/books.css"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"""<!doctype html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title} • Nick’s Library</title>
  <link rel="stylesheet" href="{css_file}">
</head>
<body>
  <a href="index.html" class="back-home-btn">← Back to Home</a>
  <h1>{title}</h1>
  <p>Generated {gen_time}</p>
""")

        for it in items:
            stars = it.get("rating_stars") or ""
            review = it.get("review_html") or ""
            title_text = it.get("title") or ""
            link = it.get("link") or ""

            f.write('<div class="entry">\n')
            if link:
                f.write(f'<h2><a href="{link}">{title_text}</a></h2>\n')
            else:
                f.write(f'<h2>{title_text}</h2>\n')

            if stars:
                f.write(f'<p class="rating">{stars}</p>\n')
            if review:
                f.write(f'<p class="review">{review}</p>\n')

            f.write("</div>\n<hr>\n")

        f.write("</body>\n</html>")
def main():
    ensure_dirs()
    seen_films = load_ids(FILMS_JSONL)
    seen_books = load_ids(BOOKS_JSONL)

    new_films = [x for x in normalize_letterboxd(LETTERBOXD_RSS) if x["id"] not in seen_films]
    new_books = [x for x in normalize_goodreads(GOODREADS_READ_RSS) if x["id"] not in seen_books]

    append_jsonl(FILMS_JSONL, new_films)
    append_jsonl(BOOKS_JSONL, new_books)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    render_page("Films", load_all_jsonl(FILMS_JSONL), os.path.join(SITE_DIR, "films.html"), now)
    render_page("Books", load_all_jsonl(BOOKS_JSONL), os.path.join(SITE_DIR, "books.html"), now)

if __name__ == "__main__":
    main()
