"""
prompts — a prompt library: prompts you keep for future reference, grouped into sets by the creator who wrote them
(a creator's everyday library, or the prompts from one of their videos).

The creator is an ordinary entry of kind `person`, so the prompts hang off them like any other sub-library. Prompts
live only in the database (the `kb-data` volume). They are not mirrored into the OKF bundle or the git repo: creators
usually license their prompts for personal use only, and the set keeps the creator's terms so the pages can show them.

Import a Prompt Lab page (a single HTML file with a JSON `<script id="data">` block):
    python kb.py import-prompts prompt-lab.html            (or `-` to read the file from stdin)
"""
import json
import re
from html import unescape

from library import now, slugify

SCHEMA = """
CREATE TABLE IF NOT EXISTS prompt_sets(
  id INTEGER PRIMARY KEY, slug TEXT UNIQUE, creator_id INTEGER REFERENCES entities(id) ON DELETE SET NULL,
  kind TEXT DEFAULT 'library', title TEXT, description TEXT DEFAULT '', details TEXT DEFAULT '', footer TEXT DEFAULT '',
  links TEXT DEFAULT '[]', source_url TEXT DEFAULT '', terms TEXT DEFAULT '', caution TEXT DEFAULT '',
  position INTEGER DEFAULT 0, imported TEXT);
CREATE TABLE IF NOT EXISTS prompts(
  id INTEGER PRIMARY KEY, set_id INTEGER REFERENCES prompt_sets(id) ON DELETE CASCADE, slug TEXT,
  title TEXT, category TEXT DEFAULT '', type TEXT DEFAULT 'text', tool TEXT DEFAULT '', description TEXT DEFAULT '',
  prompt TEXT DEFAULT '', featured INTEGER DEFAULT 0, position INTEGER DEFAULT 0,
  saved INTEGER DEFAULT 0, my_version TEXT DEFAULT '', updated TEXT, UNIQUE(set_id, slug));
CREATE INDEX IF NOT EXISTS prompts_set ON prompts(set_id, position);
"""
TYPES = ["text", "image"]


def setup(lib):
    with lib._db() as c:
        c.executescript(SCHEMA)


# ---------------------------------------------------------------------------------------------------- import
def parse_prompt_lab(html_text: str) -> dict:
    """The data, credit line and caution box out of a Prompt Lab page."""
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html_text, re.S)
    if not m:
        raise ValueError("no <script id=\"data\"> block: is this a Prompt Lab page?")
    data = json.loads(m.group(1))
    strip = lambda s: re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()  # noqa: E731
    credit = re.search(r'<p class="credit">(.*?)</p>', html_text, re.S)
    site = re.search(r'<p class="credit">.*?href="([^"]+)"', html_text, re.S)
    warn = re.search(r'<div class="warnbox"><strong>.*?</strong>(.*?)</div>', html_text, re.S)
    by = re.search(r"©\s*\d{4}\s+([^,<]+?),", credit.group(1)) if credit else None
    return {"library": data.get("library", []), "videos": data.get("videos", []),
            "terms": strip(credit.group(1)) if credit else "", "site": site.group(1) if site else "",
            "caution": strip(warn.group(1)) if warn else "", "creator": by.group(1).strip() if by else ""}


def import_prompt_lab(lib, html_text: str, creator: str = "") -> dict:
    """Add or refresh a creator's prompts. Your saved stars and own versions are kept."""
    d = parse_prompt_lab(html_text)
    name = creator or d["creator"] or "Unknown creator"
    with lib._db() as c:
        found = lib._find(c, name)
        slug = lib._slug(c, found) if found else None
    if not slug:   # a new creator gets a short description; an existing entry keeps yours
        slug = lib.create_entity(name, "person", f"Creator. Prompt library and video build prompts from {d['site'] or 'their site'}.")
    if d["site"]:
        lib.add_resource(slug, d["site"], f"{name}'s site", "The original home of these prompts")
    with lib._lock, lib._db() as c:
        eid = c.execute("SELECT id FROM entities WHERE slug=?", (slug,)).fetchone()[0]
        sets = [{"slug": f"{slug}-library", "kind": "library", "title": f"{name}'s prompt library",
                 "description": "Everyday prompts for text and image tools.", "prompts": d["library"]}]
        for i, v in enumerate(d["videos"]):
            sets.append({"slug": f"{slug}-{slugify(v.get('title', ''))[:60] or i}", "kind": "video", "title": v.get("title", ""),
                         "description": v.get("description", ""), "details": v.get("details", ""), "footer": v.get("footer", ""),
                         "links": v.get("links", []), "prompts": v.get("prompts") or _from_sections(v)})
        n = 0
        for pos, s in enumerate(sets):
            c.execute("""INSERT INTO prompt_sets(slug, creator_id, kind, title, description, details, footer, links,
                         source_url, terms, caution, position, imported) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                         ON CONFLICT(slug) DO UPDATE SET creator_id=excluded.creator_id, kind=excluded.kind,
                         title=excluded.title, description=excluded.description, details=excluded.details,
                         footer=excluded.footer, links=excluded.links, source_url=excluded.source_url,
                         terms=excluded.terms, caution=excluded.caution, position=excluded.position, imported=excluded.imported""",
                      (s["slug"], eid, s["kind"], s["title"], s["description"], s.get("details", ""), s.get("footer", ""),
                       json.dumps(s.get("links", []), ensure_ascii=False), d["site"], d["terms"], d["caution"], pos, now()))
            sid = c.execute("SELECT id FROM prompt_sets WHERE slug=?", (s["slug"],)).fetchone()[0]
            for ppos, p in enumerate(s["prompts"]):
                c.execute("""INSERT INTO prompts(set_id, slug, title, category, type, tool, description, prompt, featured,
                             position, updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                             ON CONFLICT(set_id, slug) DO UPDATE SET title=excluded.title, category=excluded.category,
                             type=excluded.type, tool=excluded.tool, description=excluded.description,
                             prompt=excluded.prompt, featured=excluded.featured, position=excluded.position""",
                          (sid, p.get("id") or slugify(p.get("title", "")), p.get("title", ""), p.get("category", ""),
                           p.get("type", "text"), p.get("tool", ""), p.get("description", ""), p.get("prompt", ""),
                           1 if p.get("featured") else 0, ppos, now()))
                n += 1
    return {"creator": name, "slug": slug, "sets": len(sets), "prompts": n}


def _from_sections(v: dict) -> list[dict]:
    """Some videos group their prompts into steps: flatten them, keeping the step as the category."""
    out = []
    for sec in v.get("sections", []):
        for p in sec.get("prompts", []):
            out.append(p | {"category": p.get("category") or sec.get("title", ""),
                            "description": p.get("description") or sec.get("intro", "")})
    return out


def _has(c, table: str) -> bool:
    return bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


# ---------------------------------------------------------------------------------------------------- read
_COLS = """p.id, p.slug, p.title, p.category, p.type, p.tool, p.description, p.prompt, p.featured, p.saved, p.my_version,
           s.id AS set_id, s.slug AS set_slug, s.title AS set_title, s.kind AS set_kind,
           e.name AS creator, e.slug AS creator_slug"""
_FROM = "FROM prompts p JOIN prompt_sets s ON s.id=p.set_id LEFT JOIN entities e ON e.id=s.creator_id"


def find(lib, q: str = "", type_: str = "", set_slug: str = "", creator: str = "", category: str = "",
         featured: bool = False, saved: bool = False, videos: bool = False, limit: int = 500) -> list[dict]:
    where, args = [], []
    for term in q.split():
        where.append("(p.title LIKE ? OR p.description LIKE ? OR p.prompt LIKE ? OR p.category LIKE ? OR p.tool LIKE ? OR s.title LIKE ?)")
        args += [f"%{term}%"] * 6
    for col, v in (("p.type", type_), ("s.slug", set_slug), ("e.slug", creator), ("p.category", category)):
        if v:
            where.append(f"{col}=?")
            args.append(v)
    if featured:
        where.append("p.featured=1")
    if saved:
        where.append("p.saved=1")
    if videos:
        where.append("s.kind='video'")
    sql = f"SELECT {_COLS} {_FROM} {'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY s.position, p.position LIMIT ?"
    with lib._db() as c:
        return [dict(r) for r in c.execute(sql, (*args, limit))]


def get(lib, pid: int) -> dict | None:
    with lib._db() as c:
        r = c.execute(f"SELECT {_COLS}, s.terms, s.caution, s.source_url {_FROM} WHERE p.id=?", (pid,)).fetchone()
        return dict(r) if r else None


def counts(lib, creator: str = "") -> dict:
    with lib._db() as c:
        w, a = ("WHERE e.slug=?", (creator,)) if creator else ("", ())
        r = c.execute(f"""SELECT COUNT(*) n, SUM(p.type='text' AND s.kind='library') text, SUM(p.type='image' AND s.kind='library') image,
                          SUM(p.featured AND s.kind='library') featured,
                          SUM(p.saved) saved, SUM(s.kind='video') videos {_FROM} {w}""", a).fetchone()
        return {k: (r[k] or 0) for k in r.keys()}


def categories(lib, creator: str = "") -> list[tuple[str, int]]:
    with lib._db() as c:
        w, a = ("AND e.slug=?", (creator,)) if creator else ("", ())
        return [(r[0], r[1]) for r in c.execute(
            f"SELECT p.category, COUNT(*) {_FROM} WHERE s.kind='library' {w} GROUP BY p.category ORDER BY COUNT(*) DESC", a)]


def sets(lib, creator: str = "") -> list[dict]:
    with lib._db() as c:
        w, a = ("WHERE e.slug=?", (creator,)) if creator else ("", ())
        out = []
        for r in c.execute(f"""SELECT s.*, e.name AS creator, e.slug AS creator_slug,
                                (SELECT COUNT(*) FROM prompts WHERE set_id=s.id) AS n
                               FROM prompt_sets s LEFT JOIN entities e ON e.id=s.creator_id {w} ORDER BY s.position""", a):
            d = dict(r)
            d["links"] = json.loads(d["links"] or "[]")
            out.append(d)
        return out


def creators(lib) -> list[dict]:
    with lib._db() as c:
        return [dict(r) for r in c.execute(
            """SELECT e.name, e.slug, e.description, COUNT(DISTINCT s.id) AS sets, COUNT(p.id) AS prompts,
                      COUNT(DISTINCT CASE WHEN s.kind='video' THEN s.id END) AS videos, MAX(s.source_url) AS site, MAX(s.imported) AS imported
               FROM prompt_sets s JOIN entities e ON e.id=s.creator_id LEFT JOIN prompts p ON p.set_id=s.id
               GROUP BY e.id ORDER BY e.name""")]


def set_saved(lib, pid: int, on: bool):
    with lib._lock, lib._db() as c:
        c.execute("UPDATE prompts SET saved=?, updated=? WHERE id=?", (1 if on else 0, now(), pid))


def set_my_version(lib, pid: int, text: str):
    with lib._lock, lib._db() as c:
        c.execute("UPDATE prompts SET my_version=?, updated=? WHERE id=?", (text.strip(), now(), pid))
