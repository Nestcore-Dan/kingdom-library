"""
library — the knowledge base store (the centre of the project).

Extensions (ytdl now; news recaps, dataset watchers and agents later) send it *documents*
(see DOC CONTRACT in README.md); the KB curates them into a reference library:

  entities   General knowledge (topic, concept, technique), tool-specific knowledge (a concept whose
             parent is a product) and Tools & products (tool, library, llm, service, company, person)
  aliases    every spelling that maps to an entity (typos and speech-to-text errors included)
  tags       your curated categories (e.g. "Voice"); applied automatically + by hand; new ones proposed
  sources    videos, articles, datasets... with the original document kept for rebuilds
  mentions   entity <-> source links, with timestamps and context
  insights   what sources teach: tool-agnostic principles and tool-specific tips (with timestamps)
  notes      your own internal knowledge
  inbox      documents waiting to be curated (survives restarts)
"""
import difflib
import json
import os
import re
import sqlite3
import threading
import time
from html import escape
from pathlib import Path
from urllib.parse import parse_qs, quote

KINDS = ["topic", "concept", "technique", "tool", "library", "llm", "dataset", "service", "company", "person", "project"]
KNOWLEDGE = ["topic", "concept", "technique"]
PRODUCTS = ["tool", "library", "llm", "dataset", "service", "company", "person", "project"]  # project = your own work (projects.py)
REL_RANK = {"core": 2, "supporting": 1, "": 0}

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS entities(
  id INTEGER PRIMARY KEY, slug TEXT UNIQUE, name TEXT, kind TEXT,
  description TEXT DEFAULT '', description_source TEXT DEFAULT 'auto',
  created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS aliases(norm TEXT PRIMARY KEY,
  entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY, kind TEXT, title TEXT, url TEXT, channel TEXT, published TEXT,
  local_path TEXT, summary TEXT DEFAULT '', created TEXT, UNIQUE(kind, url));
CREATE TABLE IF NOT EXISTS mentions(
  id INTEGER PRIMARY KEY,
  entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
  source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
  t REAL, context TEXT);
CREATE INDEX IF NOT EXISTS mentions_entity ON mentions(entity_id);
CREATE INDEX IF NOT EXISTS mentions_source ON mentions(source_id);
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY, entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
  body TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS insights(
  id INTEGER PRIMARY KEY, entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
  source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE, scope TEXT, text TEXT);
CREATE INDEX IF NOT EXISTS insights_entity ON insights(entity_id);
CREATE TABLE IF NOT EXISTS suggestions(
  id INTEGER PRIMARY KEY, kind TEXT, a TEXT, b TEXT, extra TEXT, reason TEXT,
  status TEXT DEFAULT 'open', created TEXT);
CREATE TABLE IF NOT EXISTS dismissed(a INTEGER, b INTEGER, PRIMARY KEY(a, b));
CREATE TABLE IF NOT EXISTS blocked(norm TEXT PRIMARY KEY, name TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS tags(
  id INTEGER PRIMARY KEY, slug TEXT UNIQUE, name TEXT, description TEXT DEFAULT '',
  status TEXT DEFAULT 'active', created TEXT);
CREATE TABLE IF NOT EXISTS entity_tags(entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
  tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE, origin TEXT DEFAULT 'auto', PRIMARY KEY(entity_id, tag_id));
CREATE TABLE IF NOT EXISTS source_tags(source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
  tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE, origin TEXT DEFAULT 'auto', PRIMARY KEY(source_id, tag_id));
CREATE TABLE IF NOT EXISTS inbox(
  id INTEGER PRIMARY KEY, extension TEXT, title TEXT, doc TEXT, status TEXT DEFAULT 'pending',
  error TEXT DEFAULT '', source_id INTEGER, created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS agents(
  name TEXT PRIMARY KEY, role TEXT DEFAULT '', color TEXT DEFAULT '', location TEXT DEFAULT 'entrance',
  activity TEXT DEFAULT '', entered TEXT, updated TEXT, present INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS agent_log(id INTEGER PRIMARY KEY, name TEXT, location TEXT, text TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS libraries(
  namespace TEXT PRIMARY KEY, name TEXT, owner TEXT DEFAULT '', kind TEXT DEFAULT 'imported',
  description TEXT DEFAULT '', origin TEXT DEFAULT '', created TEXT, report TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS id_map(namespace TEXT, old_id TEXT, new_id TEXT, note TEXT DEFAULT '',
  PRIMARY KEY(namespace, old_id));
CREATE TABLE IF NOT EXISTS review_log(
  id INTEGER PRIMARY KEY, target TEXT, change_class TEXT, decision TEXT, reviewer TEXT, basis TEXT, created TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(body, title, ref UNINDEXED);
"""
MIGRATIONS = [  # columns added after v1 (ALTER is skipped when the column exists)
    ("entities", "parent_id", "INTEGER REFERENCES entities(id) ON DELETE SET NULL"),
    ("entities", "origin", "TEXT DEFAULT 'auto'"),        # auto | curated (you acted on it) | manual (you made it)
    ("entities", "relevance", "TEXT DEFAULT ''"),         # best seen: core | supporting
    ("entities", "parent_source", "TEXT DEFAULT 'auto'"), # auto | internal
    ("sources", "doc", "TEXT"),          # the document the extension sent (JSON) - lets us rebuild
    ("sources", "canon", "TEXT"),        # the tidy-pass result (JSON)
    ("sources", "extension", "TEXT DEFAULT ''"),
    ("sources", "external_id", "TEXT DEFAULT ''"),
    ("sources", "duration", "REAL"),
    ("insights", "t", "REAL"),
    ("insights", "created", "TEXT"),
    # house rules R3-R6: source identity, rating and review state
    ("sources", "src_id", "TEXT"),                          # SRC-<namespace>-<sequence>, never reused
    ("sources", "namespace", "TEXT DEFAULT 'KB'"),
    ("sources", "reputability", "TEXT DEFAULT 'Unassessed'"),
    ("sources", "assessment", "TEXT"),                      # JSON: dimensions, basis, method, date
    ("sources", "assessed_by", "TEXT DEFAULT ''"),          # '' | 'model (draft)' | owner name
    ("sources", "origin_family", "TEXT DEFAULT ''"),
    ("sources", "status", "TEXT DEFAULT 'unreviewed'"),     # unreviewed | reviewed
    ("sources", "sha256", "TEXT DEFAULT ''"),
    ("sources", "supersedes", "TEXT DEFAULT ''"),
    ("insights", "status", "TEXT DEFAULT 'unreviewed'"),    # R6.1 lifecycle
    ("insights", "confidence", "TEXT DEFAULT 'unknown'"),   # R5 high | moderate | low | unknown
    ("insights", "basis", "TEXT DEFAULT ''"),
    ("insights", "label", "TEXT DEFAULT ''"),               # R3.4 observation | claim | analysis | hypothesis
    ("insights", "reviewed", "TEXT DEFAULT ''"),
]

OWNER = os.environ.get("KB_OWNER", "the owner")
HOME_NS = "KB"
RATINGS = ["Excellent", "Good", "Mixed", "Weak", "Unreliable", "Unassessed"]
CONFIDENCE = ["high", "moderate", "low", "unknown"]
LABELS = ["observation", "claim", "analysis", "hypothesis"]
INSIGHT_STATES = ["unreviewed", "accepted", "rejected", "disputed", "stale", "superseded", "retracted"]
HIDDEN_STATES = ("rejected", "retracted")    # stop being used, but kept as tombstones (R6.1)

DEFAULT_TAGS = [
    ("Voice", "Voice technology: speech-to-text, text-to-speech, voice agents and voice models"),
    ("Vision", "Image/video understanding, vision-language models, OCR, image generation"),
    ("Coding agents", "AI that writes or edits code: Claude Code, Codex, Cursor and similar"),
    ("Agent frameworks", "Frameworks/SDKs for building agents: LangGraph, CrewAI, Agents SDK..."),
    ("Multi-agent", "Several agents working together: orchestration, hand-offs, agent teams"),
    ("MCP & tool use", "Model Context Protocol, function calling, connecting models to tools"),
    ("Browser & computer use", "Agents that drive browsers, desktops or phones"),
    ("RAG & memory", "Retrieval, vector search, knowledge bases, long-term agent memory"),
    ("Automation & workflows", "n8n, Zapier, Make, scheduled jobs, business process automation"),
    ("Local models", "Running models on your own hardware: Ollama, llama.cpp, quantisation"),
    ("Training & fine-tuning", "Fine-tuning, LoRA, RL, distillation, synthetic data"),
    ("Datasets", "Datasets for training/evaluating models"),
    ("Evaluation", "Benchmarks, evals, testing and measuring model/agent quality"),
    ("Prompting", "Prompt engineering, system prompts, context engineering"),
    ("Infrastructure & hosting", "Servers, VPS, deployment, GPUs, cloud platforms"),
    ("Security & safety", "Prompt injection, sandboxing, permissions, AI safety"),
    ("Business & monetisation", "Selling AI services, pricing, agencies, revenue claims"),
]


STOPWORDS = set("""a an and are as at be but by can do does for from has have how i if in into is it its me
my of on or our should so that the their them then there these they this to use used using was we what when where which
who why will with would you your about any best between could get give good know like make more most much need new now
one only other some such than tell very want way""".split())


def _conf(x):
    return x.get("confidence") if x.get("confidence") in ("high", "moderate", "low", "unknown") else "unknown"


def _label(x):
    return x.get("label") if x.get("label") in ("observation", "claim", "analysis", "hypothesis") else ""


def norm(name: str) -> str:
    """'GPT-5' / 'gpt 5' / 'Gpt5' -> 'gpt5'; 'Claude Code' -> 'claudecode'."""
    return re.sub(r"[^a-z0-9+#]", "", (name or "").lower())


def local_file(path: str | None):
    """A stored file path as this machine sees it. Paths recorded on Windows (C:\\Users\\...) are translated with
    KB_PATH_MAP="C:\\Users\\you\\Downloads\\ytdl=/downloads;..." when the knowledge base runs in a container."""
    from pathlib import Path as _P, PureWindowsPath

    if not path:
        return None
    p = str(path)
    for pair in (os.environ.get("KB_PATH_MAP") or "").split(";"):
        if "=" not in pair:
            continue
        src, dst = pair.split("=", 1)
        if p.replace("/", "\\").lower().startswith(src.replace("/", "\\").rstrip("\\").lower() + "\\"):
            rest = PureWindowsPath(p[len(src.rstrip("/\\")) + 1:]).as_posix()
            return _P(dst) / rest
    return _P(p)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", "-", name.lower()).strip("-").replace("#", "sharp").replace("+", "plus") or "x"


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def hms(t) -> str:
    if t is None:
        return ""
    t = int(t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def at_time(url, t):
    if not url:
        return None
    if t is not None and "youtube.com/watch" in url:
        return f"{url}&t={int(t)}s"
    return url


class Library:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._db() as c:
            c.executescript(SCHEMA)
            for table, col, decl in MIGRATIONS:
                cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})")]
                if col not in cols:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            c.execute("INSERT OR IGNORE INTO libraries(namespace,name,owner,kind,description,created) VALUES(?,?,?,?,?,?)",
                      (HOME_NS, "Knowledge base", OWNER, "own", "The home library", now()))
            for (sid, ns) in c.execute("SELECT id, IFNULL(namespace,'KB') FROM sources WHERE src_id IS NULL ORDER BY id").fetchall():
                c.execute("UPDATE sources SET src_id=?, namespace=? WHERE id=?", (self._next_src_id(c, ns), ns, sid))
            if not c.execute("SELECT 1 FROM meta WHERE k='tags_seeded'").fetchone():
                for name, desc in DEFAULT_TAGS:
                    c.execute("INSERT OR IGNORE INTO tags(slug,name,description,status,created) VALUES(?,?,?,?,?)",
                              (slugify(name), name, desc, "active", now()))
                c.execute("INSERT INTO meta VALUES('tags_seeded','1')")
        import projects  # noqa: PLC0415 - these modules build on Library
        import skills

        import kingdom

        skills.setup(self)
        import prompts

        prompts.setup(self)
        with self._db() as c:
            c.executescript(projects.SCHEMA)
        kingdom.setup(self)          # town tables; adds project_info.office before the seed uses it
        try:
            projects.setup(self)    # first-run project articles (seeds/projects.json)
            kingdom.default_offices(self)
        except Exception as e:  # noqa: BLE001 - a bad seed file must never stop the library opening
            print(f"[kb] project seed skipped: {e}")

    @staticmethod
    def _next_src_id(c, ns: str) -> str:
        """R3.1: SRC-<namespace>-<sequence>; the counter only ever goes up, so IDs are never reused."""
        k = f"seq:{ns}"
        r = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        n = int(r[0]) + 1 if r else 1
        c.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, str(n)))
        return f"SRC-{ns}-{n:04d}"

    def _db(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        return c

    # ================================================================ entities
    def _find(self, c, name: str):
        r = c.execute("SELECT entity_id FROM aliases WHERE norm=?", (norm(name),)).fetchone()
        return r[0] if r else None

    def _name(self, c, eid):
        r = c.execute("SELECT name FROM entities WHERE id=?", (eid,)).fetchone()
        return r[0] if r else None

    def upsert_entity(self, c, name: str, kind: str, description: str = "", canonical: bool = False,
                      relevance: str = "", origin: str = "auto") -> int:
        name = name.strip()
        kind = kind if kind in KINDS else "concept"
        eid = self._find(c, name)
        if eid:
            if canonical:  # cleaner name/kind from the tidy pass; never touch user-edited entries
                c.execute("UPDATE entities SET name=?, kind=? WHERE id=? AND description_source='auto'"
                          " AND origin='auto'", (name, kind, eid))
            if description:
                c.execute("UPDATE entities SET description=?, updated=? WHERE id=? AND description=''"
                          " AND description_source='auto'", (description, now(), eid))
                self._reindex_entity(c, eid)
            if relevance:
                c.execute("UPDATE entities SET relevance=? WHERE id=? AND"
                          " (CASE relevance WHEN 'core' THEN 2 WHEN 'supporting' THEN 1 ELSE 0 END) < ?",
                          (relevance, eid, REL_RANK.get(relevance, 0)))
            return eid
        slug, n = slugify(name), 2
        while c.execute("SELECT 1 FROM entities WHERE slug=?", (slug,)).fetchone():
            slug, n = f"{slugify(name)}-{n}", n + 1
        eid = c.execute(
            "INSERT INTO entities(slug,name,kind,description,created,updated,origin,relevance)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (slug, name, kind, description or "", now(), now(), origin, relevance)).lastrowid
        c.execute("INSERT OR IGNORE INTO aliases VALUES(?,?)", (norm(name), eid))
        self._reindex_entity(c, eid)
        return eid

    def _reindex_entity(self, c, eid):
        r = c.execute("SELECT name, description FROM entities WHERE id=?", (eid,)).fetchone()
        c.execute("DELETE FROM fts WHERE ref=?", (f"e:{eid}",))
        if r:
            c.execute("INSERT INTO fts(body,title,ref) VALUES(?,?,?)", (r[1] or "", r[0], f"e:{eid}"))

    def _eid(self, c, slug_or_name: str) -> int:
        r = c.execute("SELECT id FROM entities WHERE slug=?", (slug_or_name.strip(),)).fetchone()
        eid = r[0] if r else self._find(c, slug_or_name)
        if not eid:
            raise KeyError(slug_or_name)
        return eid

    def _curate(self, c, eid):
        """You acted on this entry: keep it (and its name/kind) through rebuilds."""
        c.execute("UPDATE entities SET origin='curated' WHERE id=? AND origin='auto'", (eid,))

    def _block(self, c, eid):
        """Never re-add this entry (all its spellings) from future analyses."""
        name = self._name(c, eid)
        for (n,) in c.execute("SELECT norm FROM aliases WHERE entity_id=?", (eid,)).fetchall():
            c.execute("INSERT OR IGNORE INTO blocked VALUES(?,?,?)", (n, name, now()))

    def _blocked(self, c) -> set:
        return {r[0] for r in c.execute("SELECT norm FROM blocked")}

    def blocked(self):
        with self._db() as c:
            return [dict(r) for r in c.execute("SELECT name, GROUP_CONCAT(norm, ', ') AS spellings FROM blocked"
                                               " GROUP BY name ORDER BY name COLLATE NOCASE")]

    def unblock(self, name: str):
        with self._lock, self._db() as c:
            c.execute("DELETE FROM blocked WHERE name=?", (name,))

    def _slug(self, c, eid):
        return c.execute("SELECT slug FROM entities WHERE id=?", (eid,)).fetchone()[0]

    def create_entity(self, name: str, kind: str, description: str = "", parent: str = "") -> str:
        with self._lock, self._db() as c:
            eid = self.upsert_entity(c, name, kind, origin="manual")
            c.execute("UPDATE entities SET origin='manual' WHERE id=?", (eid,))
            if description:
                self._set_description(c, eid, description)
            if parent.strip():
                self._set_parent(c, eid, parent, "internal")
            return self._slug(c, eid)

    def _set_description(self, c, eid: int, text: str):
        c.execute("UPDATE entities SET description=?, description_source='internal', updated=? WHERE id=?",
                  (text, now(), eid))
        self._reindex_entity(c, eid)

    def set_description(self, slug: str, text: str):
        with self._lock, self._db() as c:
            self._set_description(c, self._eid(c, slug), text.strip())

    def rename(self, slug: str, new_name: str) -> str:
        new_name = new_name.strip()
        if not new_name:
            return slug
        with self._lock, self._db() as c:
            eid = self._eid(c, slug)
            other = self._find(c, new_name)
            if other and other != eid:  # renaming onto an existing entry = merge
                return self._merge(c, eid, other)
            c.execute("UPDATE entities SET name=?, origin='manual', updated=? WHERE id=?", (new_name, now(), eid))
            c.execute("INSERT OR REPLACE INTO aliases VALUES(?,?)", (norm(new_name), eid))
            self._reindex_entity(c, eid)
            return self._slug(c, eid)

    def _set_parent(self, c, eid, parent_name: str, source: str = "auto", parent_kind: str = ""):
        parent_name = parent_name.strip()
        if not parent_name:
            c.execute("UPDATE entities SET parent_id=NULL, parent_source=? WHERE id=?", (source, eid))
            return
        pid = self._find(c, parent_name)
        if not pid:
            kind = c.execute("SELECT kind FROM entities WHERE id=?", (eid,)).fetchone()[0]
            guess = parent_kind if parent_kind in KINDS else ("topic" if kind in KNOWLEDGE else "company")
            pid = self.upsert_entity(c, parent_name, guess)
        if pid == eid:
            return
        # refuse cycles: walk up from the new parent
        p, seen = pid, set()
        while p and p not in seen:
            if p == eid:
                return
            seen.add(p)
            r = c.execute("SELECT parent_id FROM entities WHERE id=?", (p,)).fetchone()
            p = r[0] if r else None
        if source == "auto":
            c.execute("UPDATE entities SET parent_id=? WHERE id=? AND parent_id IS NULL AND parent_source='auto'",
                      (pid, eid))
        else:
            c.execute("UPDATE entities SET parent_id=?, parent_source='internal' WHERE id=?", (pid, eid))
            self._curate(c, pid)

    def set_parent(self, slug: str, parent_name: str):
        with self._lock, self._db() as c:
            self._set_parent(c, self._eid(c, slug), parent_name, "internal")

    def add_note(self, slug: str, body: str):
        body = body.strip()
        if not body:
            return
        with self._lock, self._db() as c:
            eid = self._eid(c, slug)
            nid = c.execute("INSERT INTO notes(entity_id,body,created) VALUES(?,?,?)", (eid, body, now())).lastrowid
            c.execute("INSERT INTO fts(body,title,ref) VALUES(?,?,?)", (body, f"Note: {self._name(c, eid)}", f"n:{nid}"))

    def delete_note(self, note_id: int):
        with self._lock, self._db() as c:
            c.execute("DELETE FROM notes WHERE id=?", (note_id,))
            c.execute("DELETE FROM fts WHERE ref=?", (f"n:{note_id}",))

    def add_alias(self, slug: str, alias: str):
        if alias.strip():
            with self._lock, self._db() as c:
                c.execute("INSERT OR REPLACE INTO aliases VALUES(?,?)", (norm(alias), self._eid(c, slug)))

    def add_resource(self, slug: str, url: str, title: str = "", note: str = ""):
        url = url.strip()
        if not url:
            return
        with self._lock, self._db() as c:
            eid = self._eid(c, slug)
            c.execute("INSERT OR IGNORE INTO sources(kind,title,url,created) VALUES('url',?,?,?)",
                      (title.strip() or url, url, now()))
            sid = c.execute("SELECT id FROM sources WHERE kind='url' AND url=?", (url,)).fetchone()[0]
            c.execute("INSERT INTO mentions(entity_id,source_id,t,context) VALUES(?,?,NULL,?)", (eid, sid, note.strip()))

    def _merge(self, c, a: int, b: int) -> str:
        """Fold entity a into b: mentions, notes, insights, aliases, children all move."""
        if a == b:
            return self._slug(c, b)
        for t in ("mentions", "notes", "aliases", "insights"):
            c.execute(f"UPDATE {t} SET entity_id=? WHERE entity_id=?", (b, a))
        c.execute("UPDATE entities SET parent_id=? WHERE parent_id=? AND id!=?", (b, a, b))
        ra = c.execute("SELECT description, description_source, relevance FROM entities WHERE id=?", (a,)).fetchone()
        rb = c.execute("SELECT description, relevance FROM entities WHERE id=?", (b,)).fetchone()
        if ra and not rb["description"] and ra["description"]:
            c.execute("UPDATE entities SET description=?, description_source=? WHERE id=?",
                      (ra["description"], ra["description_source"], b))
        if ra and REL_RANK.get(ra["relevance"] or "", 0) > REL_RANK.get(rb["relevance"] or "", 0):
            c.execute("UPDATE entities SET relevance=? WHERE id=?", (ra["relevance"], b))
        c.execute("DELETE FROM fts WHERE ref=?", (f"e:{a}",))
        c.execute("DELETE FROM entities WHERE id=?", (a,))
        self._curate(c, b)
        self._reindex_entity(c, b)
        return self._slug(c, b)

    def merge(self, slug: str, into: str) -> str:
        """Merge a duplicate into the main entry; `into` may be a slug, name or alias."""
        with self._lock, self._db() as c:
            return self._merge(c, self._eid(c, slug), self._eid(c, into))

    def set_kind(self, slug: str, kind: str):
        if kind in KINDS:
            with self._lock, self._db() as c:
                c.execute("UPDATE entities SET kind=?, origin='manual', updated=? WHERE id=?",
                          (kind, now(), self._eid(c, slug)))

    def delete_entity(self, slug: str, block: bool = True):
        """Delete an entry. block=True (a user delete) also stops it being re-added by rebuilds."""
        with self._lock, self._db() as c:
            eid = self._eid(c, slug)
            if block:
                self._block(c, eid)
            c.execute("DELETE FROM fts WHERE ref=?", (f"e:{eid}",))
            c.execute("DELETE FROM entities WHERE id=?", (eid,))

    # ================================================================ ingest
    def candidates(self, raw: list, limit: int = 150) -> list[str]:
        """Existing names that might be the same as the raw names (fed to the tidy pass)."""
        with self._db() as c:
            rows = c.execute("SELECT a.norm, e.name FROM aliases a JOIN entities e ON e.id=a.entity_id").fetchall()
        by_norm = {r[0]: r[1] for r in rows}
        keys = list(by_norm)
        out = []
        for item in raw:
            n = norm(item[0] if isinstance(item, (list, tuple)) else item)
            if not n:
                continue
            hits = difflib.get_close_matches(n, keys, n=3, cutoff=0.6)
            if len(n) >= 4:
                hits += [k for k in keys if len(k) >= 4 and (k in n or n in k)][:5]
            out += [by_norm[h] for h in hits]
        return list(dict.fromkeys(out))[:limit]

    def ingest_doc(self, doc: dict, canon: dict | None = None, extension: str = "") -> int:
        """Add/replace one source document. Re-sending the same source (same kind + url) replaces
        its links, insights and auto tags; your notes, edits, aliases and manual tags stay."""
        src, o = doc["source"], doc.get("overview") or {}
        kind = src.get("kind") or "article"
        url = src.get("url") or f"file:{src.get('local_path') or src.get('title')}"
        summary = o.get("summary") or src.get("summary") or ""
        segs = doc.get("segments", [])
        ns = (src.get("namespace") or HOME_NS).upper()
        with self._lock, self._db() as c:
            c.execute("INSERT OR IGNORE INTO libraries(namespace,name,created) VALUES(?,?,?)", (ns, ns, now()))
            row = c.execute("SELECT id FROM sources WHERE kind=? AND url=?", (kind, url)).fetchone()
            kept = {}   # reviews you made survive re-filing (R6)
            if row:
                kept = {(r[0], r[1]): r[2:] for r in c.execute(
                    "SELECT scope, text, status, confidence, basis, reviewed, label FROM insights"
                    " WHERE source_id=? AND (status!='unreviewed' OR reviewed!='')", (row[0],))}
            vals = (src.get("title") or url, src.get("author"), src.get("published"), src.get("local_path"),
                    summary, json.dumps(doc, ensure_ascii=False), json.dumps(canon, ensure_ascii=False) if canon else None,
                    extension or doc.get("extension", ""), src.get("external_id") or "", src.get("duration"))
            if row:
                sid = row[0]
                c.execute("DELETE FROM mentions WHERE source_id=?", (sid,))
                c.execute("DELETE FROM insights WHERE source_id=?", (sid,))
                c.execute("DELETE FROM source_tags WHERE source_id=? AND origin='auto'", (sid,))
                c.execute("DELETE FROM fts WHERE ref LIKE ?", (f"s:{sid}:%",))
                c.execute("UPDATE sources SET title=?,channel=?,published=?,local_path=?,summary=?,doc=?,canon=?,"
                          "extension=?,external_id=?,duration=? WHERE id=?", (*vals, sid))
            else:
                sid = c.execute(
                    "INSERT INTO sources(title,channel,published,local_path,summary,doc,canon,extension,external_id,"
                    "duration,kind,url,created,src_id,namespace) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (*vals, kind, url, now(), self._next_src_id(c, ns), ns)).lastrowid
            c.execute("UPDATE sources SET sha256=COALESCE(NULLIF(?,''), sha256), supersedes=COALESCE(NULLIF(?,''), supersedes)"
                      " WHERE id=?", (src.get("sha256") or "", src.get("supersedes") or "", sid))

            if canon:
                self._ingest_canon(c, sid, doc, canon)
                a = canon.get("source_assessment") or {}
                if a.get("reputability") in RATINGS:   # R4.4: the model drafts; your review is never overwritten
                    c.execute("UPDATE sources SET reputability=?, assessment=?, assessed_by='model (draft)', origin_family=?"
                              " WHERE id=? AND status='unreviewed'",
                              (a["reputability"], json.dumps({**a, "method": "KB-Reputability-v1", "date": now()[:10]}),
                               a.get("origin_family", ""), sid))
            else:
                self._ingest_raw(c, sid, doc)
            for (scope, text), (st, conf, basis, rev, label) in kept.items():
                c.execute("UPDATE insights SET status=?, confidence=?, basis=?, reviewed=?, label=COALESCE(NULLIF(?,''),label)"
                          " WHERE source_id=? AND scope=? AND text=?", (st, conf, basis, rev, label, sid, scope, text))

            title = src.get("title") or url
            for s in segs:
                body = "\n".join([s.get("on_screen", ""), *s.get("steps", []),
                                  *[v["text"] for v in s.get("verbatim", [])], s.get("text", "")])
                c.execute("INSERT INTO fts(body,title,ref) VALUES(?,?,?)",
                          (body, title, f"s:{sid}:{s.get('start') if s.get('start') is not None else 'overview'}"))
            ov = "\n".join([summary, o.get("core_method", ""), *o.get("key_takeaways", [])])
            c.execute("INSERT INTO fts(body,title,ref) VALUES(?,?,?)", (ov, title, f"s:{sid}:overview"))
            return sid

    def ingest_analysis(self, analysis: dict, local_path: str) -> int:
        """Legacy: a ytdl *.analysis.json (keeps any tidy pass it already carries)."""
        return self.ingest_doc(analysis_to_doc(analysis, local_path), analysis.get("canon"), "ytdl")

    def _tag_id(self, c, name: str, create_status: str | None = None):
        r = c.execute("SELECT id, status FROM tags WHERE slug=?", (slugify(name),)).fetchone()
        if r:
            return r[0] if r[1] == "active" else None
        if create_status:
            c.execute("INSERT INTO tags(slug,name,description,status,created) VALUES(?,?,?,?,?)",
                      (slugify(name), name.strip(), "", create_status, now()))
        return None

    def _ingest_canon(self, c, sid, analysis, canon):
        amap, dropped = {}, set()   # norm(raw name) -> entity id ; norms of incidental/blocked things
        blocked = self._blocked(c)
        core_topics = []
        for e in canon.get("entities", []):
            if not e.get("name", "").strip():
                continue
            names = [e["name"], *e.get("aliases", [])]
            if e.get("relevance") == "incidental" or any(norm(x) in blocked for x in names):
                dropped.update(norm(x) for x in names)
                continue
            eid = self.upsert_entity(c, e["name"], e.get("kind", "concept"), e.get("description", ""),
                                     canonical=True, relevance=e.get("relevance", ""))
            for x in names:
                n = norm(x)
                if not n:
                    continue
                amap[n] = eid
                # remember the spelling for future sources. If an untouched auto entry owns it, the tidy pass
                # wins (that entry was a variant); an entry you created or edited keeps its spelling.
                owner = c.execute("SELECT a.entity_id, e.origin, e.description_source FROM aliases a"
                                  " JOIN entities e ON e.id=a.entity_id WHERE a.norm=?", (n,)).fetchone()
                if not owner:
                    c.execute("INSERT INTO aliases VALUES(?,?)", (n, eid))
                elif owner[0] != eid and owner[1] == "auto" and owner[2] == "auto" and owner[0] not in amap.values():
                    if n != norm(self._name(c, owner[0])):
                        c.execute("UPDATE aliases SET entity_id=? WHERE norm=?", (eid, n))
                    else:  # the old entry IS this variant ("Hermes"): fold it into the canonical one
                        was = c.execute("SELECT origin FROM entities WHERE id=?", (eid,)).fetchone()[0]
                        self._merge(c, owner[0], eid)
                        c.execute("UPDATE entities SET origin=? WHERE id=?", (was, eid))  # automatic, not yours
            if e.get("parent", "").strip() and norm(e["parent"]) not in blocked:
                self._set_parent(c, eid, e["parent"], "auto", e.get("parent_kind", ""))
            if e.get("kind") in KNOWLEDGE and e.get("relevance") == "core":
                core_topics.append(eid)
            for t in e.get("tags", []):
                tid = self._tag_id(c, t)
                if tid:  # INSERT OR IGNORE: a tag you removed (origin='blocked') is never re-added
                    c.execute("INSERT OR IGNORE INTO entity_tags VALUES(?,?, 'auto')", (eid, tid))
        for t in canon.get("tags", []):
            tid = self._tag_id(c, t)
            if tid:
                c.execute("INSERT OR IGNORE INTO source_tags VALUES(?,?, 'auto')", (sid, tid))
        for nt in canon.get("new_tags", []):
            if nt.get("name", "").strip() and not c.execute("SELECT 1 FROM tags WHERE slug=?", (slugify(nt["name"]),)).fetchone():
                c.execute("INSERT INTO tags(slug,name,description,status,created) VALUES(?,?,?,'proposed',?)",
                          (slugify(nt["name"]), nt["name"].strip(), nt.get("description", ""), now()))
        keys = list(amap)

        def resolve(name):
            n = norm(name)
            if not n or n in dropped:
                return None
            if n in amap:
                return amap[n]
            close = difflib.get_close_matches(n, keys, n=1, cutoff=0.85)
            return amap[close[0]] if close else None

        mentioned = set()
        for s in analysis.get("segments", []):
            for e in s.get("entities", []):
                eid = resolve(e.get("name", ""))
                if eid:
                    c.execute("INSERT INTO mentions(entity_id,source_id,t,context) VALUES(?,?,?,?)",
                              (eid, sid, s.get("start"), e.get("note") or s.get("on_screen", "")[:300]))
                    mentioned.add(eid)
        for eid in set(amap.values()) - mentioned:
            c.execute("INSERT INTO mentions(entity_id,source_id,t,context) VALUES(?,?,NULL,?)",
                      (eid, sid, "covered in this source"))

        def first_t(eid):
            r = c.execute("SELECT MIN(t) FROM mentions WHERE entity_id=? AND source_id=?", (eid, sid)).fetchone()
            return r[0] if r else None

        for p in canon.get("principles", []):
            targets = [x for x in (resolve(n) for n in p.get("about", [])) if x] or core_topics[:1]
            for eid in dict.fromkeys(targets):
                c.execute("INSERT INTO insights(entity_id,source_id,scope,text,t,created,confidence,basis,label)"
                          " VALUES(?,?, 'principle', ?,?,?,?,?,?)",
                          (eid, sid, p["text"], p.get("t"), now(), _conf(p), p.get("confidence_basis", ""), _label(p)))
        for t in canon.get("tool_tips", []):
            eid = resolve(t.get("tool", ""))
            if eid:
                c.execute("INSERT INTO insights(entity_id,source_id,scope,text,t,created,confidence,basis,label)"
                          " VALUES(?,?, 'tip', ?,?,?,?,?,?)",
                          (eid, sid, t["text"], t.get("t") if t.get("t") is not None else first_t(eid), now(),
                           _conf(t), t.get("confidence_basis", ""), _label(t)))

    def _ingest_raw(self, c, sid, analysis):
        """v1 behaviour, for analyses without a tidy pass."""
        o = analysis.get("overview") or {}
        blocked = self._blocked(c)
        mentioned = set()
        for s in analysis.get("segments", []):
            for e in s.get("entities", []):
                if e.get("name", "").strip() and norm(e["name"]) not in blocked:
                    eid = self.upsert_entity(c, e["name"], e.get("kind", "concept"))
                    c.execute("INSERT INTO mentions(entity_id,source_id,t,context) VALUES(?,?,?,?)",
                              (eid, sid, s.get("start"), e.get("note") or s.get("on_screen", "")[:300]))
                    mentioned.add(eid)
        for e in o.get("entities", []):
            if e.get("name", "").strip() and norm(e["name"]) not in blocked:
                eid = self.upsert_entity(c, e["name"], e.get("kind", "concept"), e.get("description", ""), canonical=True)
                if eid not in mentioned:
                    c.execute("INSERT INTO mentions(entity_id,source_id,t,context) VALUES(?,?,NULL,?)",
                              (eid, sid, e.get("description", "")))
        for topic in o.get("topics", []):
            if norm(topic) in blocked:
                continue
            eid = self.upsert_entity(c, topic, "topic")
            c.execute("INSERT INTO mentions(entity_id,source_id,t,context) VALUES(?,?,NULL,?)",
                      (eid, sid, "topic of this source"))

    def purge_auto(self) -> int:
        """Before a rebuild: drop auto-created entries you never touched (no notes, no edits,
        not created by you, no external resources). Your entries, notes and aliases stay."""
        with self._lock, self._db() as c:
            c.execute("DELETE FROM mentions WHERE source_id IN (SELECT id FROM sources WHERE doc IS NOT NULL)")
            c.execute("DELETE FROM insights")
            c.execute("DELETE FROM entity_tags WHERE origin='auto'")
            ids = [r[0] for r in c.execute(
                "SELECT e.id FROM entities e WHERE e.origin='auto' AND e.description_source='auto'"
                " AND e.parent_source='auto'"
                " AND NOT EXISTS (SELECT 1 FROM notes n WHERE n.entity_id=e.id)"
                " AND NOT EXISTS (SELECT 1 FROM mentions m WHERE m.entity_id=e.id)")]
            for eid in ids:
                c.execute("DELETE FROM fts WHERE ref=?", (f"e:{eid}",))
            c.executemany("DELETE FROM entities WHERE id=?", [(i,) for i in ids])
            c.execute("UPDATE entities SET parent_id=NULL WHERE parent_source='auto'")
            c.execute("UPDATE entities SET relevance=''")
            return len(ids)

    # ================================================================ tidy
    def duplicates(self, limit: int = 80):
        """Likely-duplicate pairs (same prefix, contained name, or very similar spelling)."""
        with self._db() as c:
            ents = [dict(r) for r in c.execute(
                "SELECT e.id, e.slug, e.name, e.kind, (SELECT COUNT(*) FROM mentions m WHERE m.entity_id=e.id) n"
                " FROM entities e")]
            dismissed = {(r[0], r[1]) for r in c.execute("SELECT a, b FROM dismissed")}
        for e in ents:
            e["norm"] = norm(e["name"])
        pairs = []
        for i, a in enumerate(ents):
            for b in ents[i + 1:]:
                x, y = a["norm"], b["norm"]
                if not x or not y or (min(a["id"], b["id"]), max(a["id"], b["id"])) in dismissed:
                    continue
                short, long_ = sorted((x, y), key=len)
                score = 0.0
                if len(short) >= 4 and short in long_:
                    score = 0.9 if long_.startswith(short) else 0.8
                elif abs(len(x) - len(y)) <= 4:
                    r = difflib.SequenceMatcher(None, x, y).ratio()
                    if r >= 0.8:
                        score = r
                if score:
                    keep, dup = (a, b) if (a["n"], -len(a["name"])) >= (b["n"], -len(b["name"])) else (b, a)
                    pairs.append({"score": round(score, 2), "keep": keep, "dup": dup})
        pairs.sort(key=lambda p: -p["score"])
        return pairs[:limit]

    def dismiss(self, a_slug: str, b_slug: str):
        with self._lock, self._db() as c:
            a, b = self._eid(c, a_slug), self._eid(c, b_slug)
            c.execute("INSERT OR IGNORE INTO dismissed VALUES(?,?)", (min(a, b), max(a, b)))

    def orphans(self):
        with self._db() as c:
            return [dict(r) for r in c.execute(
                "SELECT e.slug, e.name, e.kind FROM entities e WHERE e.origin='auto'"
                " AND e.description_source='auto'"
                " AND NOT EXISTS (SELECT 1 FROM mentions m WHERE m.entity_id=e.id)"
                " AND NOT EXISTS (SELECT 1 FROM notes n WHERE n.entity_id=e.id)"
                " AND NOT EXISTS (SELECT 1 FROM entities ch WHERE ch.parent_id=e.id)"
                " ORDER BY e.name COLLATE NOCASE")]

    # ---------------------------------------------------------------- viewer attention (from the YouTube downloader)
    def set_engagement(self, ref: str, eng: dict, sections: list | None = None) -> int:
        """Store where viewers paid attention (replay curve, timestamped comments, chapters) on a source's document,
        without re-filing it. ref: source number, SRC id or URL."""
        sid = self.find_source(ref)
        if not sid:
            raise KeyError(ref)
        with self._lock, self._db() as c:
            doc = json.loads(c.execute("SELECT doc FROM sources WHERE id=?", (sid,)).fetchone()[0] or "{}")
            doc.setdefault("extra", {})["engagement"] = eng
            for seg in doc.get("segments", []):
                m = next((x for x in sections or [] if x.get("start") is not None and seg.get("start") is not None
                          and abs(x["start"] - seg["start"]) < 1), None)
                if m:
                    seg.update(attention=m.get("attention"), peak=m.get("peak", False), chapter=m.get("chapter") or seg.get("chapter", ""))
            c.execute("UPDATE sources SET doc=? WHERE id=?", (json.dumps(doc, ensure_ascii=False), sid))
        return sid

    def engagement(self, sid: int) -> dict | None:
        with self._db() as c:
            r = c.execute("SELECT doc FROM sources WHERE id=?", (sid,)).fetchone()
        try:
            return (json.loads(r[0]).get("extra") or {}).get("engagement") if r and r[0] else None
        except ValueError:
            return None

    @staticmethod
    def attention_at(eng: dict | None, t) -> float:
        """0..1: how much viewers rewatched / talked about the moment t (seconds)."""
        if not eng or t is None:
            return 0.0
        for b in eng.get("buckets", []):
            if b["start"] <= t < b["end"]:
                return b.get("attention", 0.0)
        return 0.0

    @staticmethod
    def peak_at(eng: dict | None, t) -> bool:
        return bool(eng and t is not None and any(p["start"] - 5 <= t <= p["end"] + 5 for p in eng.get("peaks", [])))

    def find_source(self, ref: str):
        """Source id from a number, an SRC id, or its URL."""
        ref = str(ref).strip()
        with self._db() as c:
            if ref.isdigit():
                r = c.execute("SELECT id FROM sources WHERE id=?", (int(ref),)).fetchone()
            elif ref.upper().startswith("SRC-"):
                r = c.execute("SELECT id FROM sources WHERE src_id=?", (ref.upper(),)).fetchone()
            else:
                r = c.execute("SELECT id FROM sources WHERE url=? ORDER BY id DESC", (ref,)).fetchone()
        return r[0] if r else None

    def delete_source(self, sid: int, reason: str = "", reviewer: str = OWNER) -> dict:
        """Remove a source, its sightings and insights, and the automatic entries that only it mentioned (R8.3:
        gone from search and indexes too; the review log keeps a tombstone). Your own entries stay. The SRC id is
        never reused."""
        with self._lock, self._db() as c:
            r = c.execute("SELECT src_id, title, url FROM sources WHERE id=?", (sid,)).fetchone()
            if not r:
                raise KeyError(sid)
            c.execute("DELETE FROM fts WHERE ref LIKE ?", (f"s:{sid}:%",))
            c.execute("DELETE FROM sources WHERE id=?", (sid,))
            c.execute("UPDATE inbox SET status='removed' WHERE source_id=?", (sid,))
            self.log_review(c, f"{r[0]} {r[1][:100]}", "source removal", "removed", reason or r[2] or "", reviewer)
        return {"src_id": r[0], "title": r[1], "entries_removed": self.delete_orphans()}

    def delete_orphans(self) -> int:
        n = 0
        for o in self.orphans():
            self.delete_entity(o["slug"], block=False)
            n += 1
        return n

    def add_suggestions(self, items: list[dict]):
        with self._lock, self._db() as c:
            for s in items:
                dup = c.execute("SELECT 1 FROM suggestions WHERE kind=? AND a=? AND IFNULL(b,'')=? AND status='open'",
                                (s["kind"], s["a"], s.get("b") or "")).fetchone()
                if not dup:
                    c.execute("INSERT INTO suggestions(kind,a,b,extra,reason,created) VALUES(?,?,?,?,?,?)",
                              (s["kind"], s["a"], s.get("b"), s.get("extra"), s.get("reason", ""), now()))

    def suggestions(self, status: str = "open", kinds: tuple | None = None):
        with self._db() as c:
            rows = [dict(r) for r in c.execute("SELECT * FROM suggestions WHERE status=? ORDER BY kind, id", (status,))]
        return [r for r in rows if not kinds or r["kind"] in kinds]

    def local_rules(self) -> str:
        f = self.path.parent / "RULES.local.md"
        return f.read_text(encoding="utf-8") if f.exists() else ""

    def resolve_suggestion(self, sid: int, accept: bool) -> str:
        with self._lock, self._db() as c:
            s = c.execute("SELECT * FROM suggestions WHERE id=?", (sid,)).fetchone()
            if not s or s["status"] != "open":
                return "gone"
            msg = "rejected"
            if s["kind"] == "rule" and not accept:
                self.log_review(c, f"house rules ({s['extra'] or 'new'})", "rule change", "not adopted", f"from {s['a']}")
            if accept:
                try:
                    a = self._eid(c, s["a"]) if s["kind"] != "rule" else None
                    if s["kind"] == "merge":
                        self._merge(c, a, self._eid(c, s["b"]))
                    elif s["kind"] == "rename":
                        other = self._find(c, s["b"])
                        if other and other != a:
                            self._merge(c, a, other)
                        else:
                            c.execute("UPDATE entities SET name=?, updated=? WHERE id=?", (s["b"], now(), a))
                            c.execute("INSERT OR REPLACE INTO aliases VALUES(?,?)", (norm(s["b"]), a))
                            self._curate(c, a)
                            self._reindex_entity(c, a)
                    elif s["kind"] == "kind" and s["b"] in KINDS:
                        c.execute("UPDATE entities SET kind=? WHERE id=?", (s["b"], a))
                        self._curate(c, a)
                    elif s["kind"] == "parent":
                        self._set_parent(c, a, s["b"], "internal", s["extra"] or "")
                        self._curate(c, a)
                    elif s["kind"] == "rule":   # R7.4: you adopt an imported rule -> RULES.local.md
                        f = self.path.parent / "RULES.local.md"
                        head = "" if f.exists() else ("# Rules adopted from imported libraries\n\n"
                                                      "Additions to RULES.md, accepted by the owner on the Review page.\n")
                        with f.open("a", encoding="utf-8") as fh:
                            fh.write(f"{head}\n- **{s['extra'] or 'new'}** {s['b']}  \n  *Adopted {now()[:10]} from {s['a']}"
                                     f" - {s['reason']}*\n")
                        self.log_review(c, f"house rules ({s['extra'] or 'new'})", "rule change", "adopted",
                                        f"from {s['a']}: {s['reason']}")
                    elif s["kind"] == "tag":
                        tid = self._tag_id(c, s["b"])
                        if tid:
                            c.execute("INSERT OR REPLACE INTO entity_tags VALUES(?,?, 'manual')", (a, tid))
                    elif s["kind"] == "remove":
                        self._block(c, a)
                        c.execute("DELETE FROM fts WHERE ref=?", (f"e:{a}",))
                        c.execute("DELETE FROM entities WHERE id=?", (a,))
                    msg = "applied"
                except KeyError:
                    msg = "entry no longer exists"
            c.execute("UPDATE suggestions SET status=? WHERE id=?", ("accepted" if accept else "rejected", sid))
            return msg

    def overview_for_ai(self):
        """Compact entity list for the AI tidy pass."""
        with self._db() as c:
            return [dict(r) for r in c.execute(
                "SELECT e.name, e.kind, IFNULL(p.name,'') AS parent, e.relevance,"
                " (SELECT COUNT(DISTINCT m.source_id) FROM mentions m WHERE m.entity_id=e.id) AS nsrc,"
                " IFNULL((SELECT GROUP_CONCAT(t.name, ', ') FROM entity_tags et JOIN tags t ON t.id=et.tag_id"
                "   WHERE et.entity_id=e.id AND et.origin!='blocked'),'') AS tags,"
                " substr(e.description,1,90) AS d FROM entities e LEFT JOIN entities p ON p.id=e.parent_id"
                " ORDER BY e.name COLLATE NOCASE")]

    # ================================================================ queries
    def _tree(self, c):
        """id -> {parent_id, kind, name, slug} for owner / sub-knowledge lookups."""
        return {r[0]: {"parent_id": r[1], "kind": r[2], "name": r[3], "slug": r[4]}
                for r in c.execute("SELECT id, parent_id, kind, name, slug FROM entities")}

    @staticmethod
    def _owner(tree, eid):
        """Nearest ancestor that is a product: knowledge under it is that product's knowledge."""
        seen, p = set(), tree.get(eid, {}).get("parent_id")
        while p and p not in seen and p in tree:
            if tree[p]["kind"] in PRODUCTS:
                return {"name": tree[p]["name"], "slug": tree[p]["slug"]}
            seen.add(p)
            p = tree[p]["parent_id"]
        return None

    @staticmethod
    def _sub_knowledge(tree, eid):
        """All knowledge-kind descendants of eid (depth-first, with depth)."""
        kids = {}
        for i, n in tree.items():
            kids.setdefault(n["parent_id"], []).append(i)
        out, stack = [], [(k, 1) for k in sorted(kids.get(eid, []), key=lambda k: tree[k]["name"].lower(), reverse=True)]
        seen = {eid}
        while stack:
            i, d = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            if tree[i]["kind"] not in KNOWLEDGE:
                continue  # a sub-product (e.g. Tango under AppLayer) owns its own knowledge
            out.append((i, d))
            stack += [(k, d + 1) for k in sorted(kids.get(i, []), key=lambda k: tree[k]["name"].lower(), reverse=True)]
        return out

    def entities(self, kinds=None, top_level_only: bool = False, tag: str | None = None):
        q = ("SELECT e.*, p.name AS parent_name, p.slug AS parent_slug,"
             " COUNT(DISTINCT m.source_id) AS nsrc, COUNT(m.id) AS nment,"
             " (SELECT COUNT(*) FROM notes n WHERE n.entity_id=e.id) AS nnotes,"
             " (SELECT COUNT(*) FROM insights i WHERE i.entity_id=e.id) AS ninsights,"
             " (SELECT COUNT(*) FROM entities ch WHERE ch.parent_id=e.id) AS nchildren"
             " FROM entities e LEFT JOIN entities p ON p.id=e.parent_id"
             " LEFT JOIN mentions m ON m.entity_id=e.id")
        args = []
        where = []
        if kinds:
            where.append(f"e.kind IN ({','.join('?' * len(kinds))})")
            args += list(kinds)
        if top_level_only:
            where.append("e.parent_id IS NULL")
        if tag:
            where.append("e.id IN (SELECT et.entity_id FROM entity_tags et JOIN tags t ON t.id=et.tag_id"
                         " WHERE t.slug=? AND et.origin!='blocked')")
            args.append(slugify(tag))
        if where:
            q += " WHERE " + " AND ".join(where)
        q += (" GROUP BY e.id ORDER BY (CASE e.relevance WHEN 'core' THEN 0 WHEN 'supporting' THEN 1 ELSE 2 END),"
              " nsrc DESC, nment DESC, e.name COLLATE NOCASE")
        with self._db() as c:
            rows = [dict(r) for r in c.execute(q, args)]
            tree = self._tree(c)
        tagmap = self._entity_tag_map()
        for r in rows:
            r["owner"] = self._owner(tree, r["id"]) if r["kind"] in KNOWLEDGE else None
            r["nknow"] = len(self._sub_knowledge(tree, r["id"])) if r["kind"] in PRODUCTS else 0
            r["tags"] = tagmap.get(r["id"], [])
        return rows

    def _entity_tag_map(self):
        with self._db() as c:
            out = {}
            for r in c.execute("SELECT et.entity_id, t.slug, t.name FROM entity_tags et JOIN tags t ON t.id=et.tag_id"
                               " WHERE et.origin!='blocked' AND t.status='active' ORDER BY t.name"):
                out.setdefault(r[0], []).append({"slug": r[1], "name": r[2]})
            return out

    def general_knowledge(self):
        return [e for e in self.entities(KNOWLEDGE) if not e["owner"]]

    def tool_knowledge(self):
        return [e for e in self.entities(KNOWLEDGE) if e["owner"]]

    def kind_counts(self):
        with self._db() as c:
            return {r[0]: r[1] for r in c.execute("SELECT kind, COUNT(*) FROM entities GROUP BY kind")}

    def entity(self, slug: str):
        with self._db() as c:
            e = c.execute("SELECT * FROM entities WHERE slug=?", (slug,)).fetchone()
            if not e:
                return None
            e = dict(e)
            chain, p = [], e["parent_id"]
            while p and len(chain) < 6:
                r = c.execute("SELECT id, slug, name, kind, parent_id FROM entities WHERE id=?", (p,)).fetchone()
                if not r:
                    break
                chain.insert(0, dict(r))
                p = r["parent_id"]
            e["ancestors"] = chain
            e["children"] = [dict(r) for r in c.execute(
                "SELECT slug, name, kind FROM entities WHERE parent_id=? ORDER BY name COLLATE NOCASE", (e["id"],))]
            tree = self._tree(c)
            e["owner"] = self._owner(tree, e["id"]) if e["kind"] in KNOWLEDGE else None
            e["sub_knowledge"] = []
            if e["kind"] in PRODUCTS:
                for i, d in self._sub_knowledge(tree, e["id"]):
                    r = c.execute("SELECT slug, name, kind, description,"
                                  " (SELECT COUNT(*) FROM insights x WHERE x.entity_id=entities.id) AS ninsights"
                                  " FROM entities WHERE id=?", (i,)).fetchone()
                    e["sub_knowledge"].append({**dict(r), "depth": d})
            e["aliases"] = [r[0] for r in c.execute("SELECT norm FROM aliases WHERE entity_id=?", (e["id"],))]
            e["tags"] = [dict(r) for r in c.execute(
                "SELECT t.slug, t.name, et.origin FROM entity_tags et JOIN tags t ON t.id=et.tag_id"
                " WHERE et.entity_id=? AND et.origin!='blocked' AND t.status='active' ORDER BY t.name", (e["id"],))]
            e["notes"] = [dict(r) for r in c.execute(
                "SELECT * FROM notes WHERE entity_id=? ORDER BY created DESC", (e["id"],))]
            e["insights"] = [dict(r) for r in c.execute(
                "SELECT i.id, i.scope, i.text, i.t, i.status, i.confidence, i.basis, i.label, i.reviewed, s.id AS sid, s.title, s.url,"
                " s.published, s.src_id, s.reputability FROM insights i"
                " JOIN sources s ON s.id=i.source_id WHERE i.entity_id=? AND i.status NOT IN ('rejected','retracted')"
                " ORDER BY i.scope, (i.status='accepted') DESC, s.published DESC",
                (e["id"],))]
            e["mentions"] = [dict(r) for r in c.execute(
                "SELECT m.t, m.context, s.id AS sid, s.kind, s.title, s.url, s.channel, s.published, s.local_path"
                " FROM mentions m JOIN sources s ON s.id=m.source_id WHERE m.entity_id=?"
                " ORDER BY s.published DESC, s.id, m.t", (e["id"],))]
            e["related"] = [dict(r) for r in c.execute(
                "SELECT e2.slug, e2.name, e2.kind, COUNT(DISTINCT m2.source_id) AS n"
                " FROM mentions m1 JOIN mentions m2 ON m1.source_id=m2.source_id AND m2.entity_id!=m1.entity_id"
                " JOIN entities e2 ON e2.id=m2.entity_id WHERE m1.entity_id=?"
                " GROUP BY e2.id ORDER BY n DESC LIMIT 15", (e["id"],))]
            return e

    def sources(self, kind: str | None = "video", tag: str | None = None, since: str | None = None, limit: int = 500):
        """Documents (not external resource links). kind=None = every document kind."""
        q = ("SELECT s.id, s.kind, s.title, s.url, s.channel, s.published, s.local_path, s.summary, s.created,"
             " s.extension, s.duration, s.src_id, s.namespace, s.reputability, s.status,"
             " COUNT(DISTINCT m.entity_id) AS nent FROM sources s"
             " LEFT JOIN mentions m ON m.source_id=s.id WHERE s.kind!='url'")
        args = []
        if kind:
            q += " AND s.kind=?"
            args.append(kind)
        if tag:
            q += (" AND s.id IN (SELECT st.source_id FROM source_tags st JOIN tags t ON t.id=st.tag_id"
                  " WHERE t.slug=? AND st.origin!='blocked')")
            args.append(slugify(tag))
        if since:
            q += " AND s.created>=?"
            args.append(since)
        q += " GROUP BY s.id ORDER BY s.created DESC, s.id DESC LIMIT ?"
        args.append(limit)
        with self._db() as c:
            rows = [dict(r) for r in c.execute(q, args)]
            for r in rows:
                r["tags"] = [dict(x) for x in c.execute(
                    "SELECT t.slug, t.name FROM source_tags st JOIN tags t ON t.id=st.tag_id"
                    " WHERE st.source_id=? AND st.origin!='blocked' AND t.status='active' ORDER BY t.name", (r["id"],))]
            return rows

    def source(self, sid: int):
        with self._db() as c:
            s = c.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()
            if not s:
                return None
            s = dict(s)
            s["entities"] = [dict(r) for r in c.execute(
                "SELECT e.slug, e.name, e.kind, e.relevance, COUNT(*) AS n, MIN(m.t) AS first FROM mentions m"
                " JOIN entities e ON e.id=m.entity_id WHERE m.source_id=? GROUP BY e.id"
                " ORDER BY (CASE e.relevance WHEN 'core' THEN 0 WHEN 'supporting' THEN 1 ELSE 2 END), e.kind, n DESC",
                (sid,))]
            s["insights"] = [dict(r) for r in c.execute(
                "SELECT MIN(i.id) AS id, i.scope, i.text, MIN(i.t) AS t, GROUP_CONCAT(e.name, ', ') AS about,"
                " MAX(i.status) AS status, MAX(i.confidence) AS confidence, MAX(i.basis) AS basis, MAX(i.label) AS label"
                " FROM insights i JOIN entities e ON e.id=i.entity_id WHERE i.source_id=?"
                " AND i.status NOT IN ('rejected','retracted') GROUP BY i.scope, i.text ORDER BY i.scope, t",
                (sid,))]
            s["tags"] = [dict(r) for r in c.execute(
                "SELECT t.slug, t.name, st.origin FROM source_tags st JOIN tags t ON t.id=st.tag_id"
                " WHERE st.source_id=? AND st.origin!='blocked' AND t.status='active' ORDER BY t.name", (sid,))]
            s["doc"] = json.loads(s["doc"]) if s.get("doc") else None
            s["canon"] = json.loads(s["canon"]) if s.get("canon") else None
            tree = self._tree(c)
            ids = {r[1]: r[0] for r in c.execute("SELECT id, slug FROM entities")}
            for e in s["entities"]:
                e["owner"] = self._owner(tree, ids[e["slug"]]) if e["kind"] in KNOWLEDGE else None
            return s

    def search(self, q: str, limit: int = 40, any_terms: bool = False):
        """Full-text search. any_terms=True ORs the meaningful words (for natural-language questions)."""
        terms = re.findall(r"[\w#+.-]+", q)
        if any_terms:
            terms = [t for t in terms if t.lower() not in STOPWORDS and len(t) > 2]
        if not terms:
            return []
        match = (" OR " if any_terms else " ").join('"' + t.replace('"', "") + '"' for t in terms)
        with self._db() as c:
            rows = c.execute(
                "SELECT ref, title, snippet(fts, 0, char(2), char(3), ' … ', 14) AS snip FROM fts"
                " WHERE fts MATCH ? ORDER BY rank LIMIT ?", (match, limit)).fetchall()
            out = []
            for r in rows:
                kind, _, rest = r["ref"].partition(":")
                hit = {"title": r["title"], "snippet": r["snip"], "kind": kind, "href": None}
                if kind == "e":
                    e = c.execute("SELECT slug FROM entities WHERE id=?", (int(rest),)).fetchone()
                    hit["href"] = f"/library/e/{e[0]}" if e else None
                elif kind == "n":
                    e = c.execute("SELECT e.slug FROM notes n JOIN entities e ON e.id=n.entity_id WHERE n.id=?",
                                  (int(rest),)).fetchone()
                    hit["href"] = f"/library/e/{e[0]}" if e else None
                else:
                    sid, _, t = rest.partition(":")
                    hit["href"] = f"/library/s/{sid}"
                    hit["t"] = None if t == "overview" else float(t)
                    s = c.execute("SELECT url FROM sources WHERE id=?", (int(sid),)).fetchone()
                    hit["watch"] = at_time(s[0], hit["t"]) if s else None
                if hit["href"]:
                    out.append(hit)
            return out

    # ================================================================ review (house rules R4-R6)
    def log_review(self, c, target: str, change_class: str, decision: str, basis: str = "", reviewer: str = OWNER):
        c.execute("INSERT INTO review_log(target,change_class,decision,reviewer,basis,created) VALUES(?,?,?,?,?,?)",
                  (target, change_class, decision, reviewer, basis, now()))

    def review_queue(self, limit: int = 200):
        """Unreviewed insights grouped by source, and sources whose rating is still a model draft."""
        with self._db() as c:
            groups = {}
            for r in c.execute(
                    "SELECT MIN(i.id) AS id, i.scope, i.text, i.t, i.confidence, i.basis, i.label,"
                    " GROUP_CONCAT(e.name, ', ') AS about, s.id AS sid, s.title, s.src_id, s.reputability,"
                    " s.assessed_by, s.namespace FROM insights i JOIN entities e ON e.id=i.entity_id"
                    " JOIN sources s ON s.id=i.source_id WHERE i.status='unreviewed'"
                    " GROUP BY s.id, i.scope, i.text ORDER BY s.created DESC, i.scope, i.t LIMIT ?", (limit,)):
                r = dict(r)
                groups.setdefault(r["sid"], {"sid": r["sid"], "title": r["title"], "src_id": r["src_id"],
                                             "reputability": r["reputability"], "assessed_by": r["assessed_by"],
                                             "namespace": r["namespace"], "items": []})["items"].append(r)
            unrated = [dict(r) for r in c.execute(
                "SELECT id, src_id, title, kind, namespace, reputability, assessed_by, assessment FROM sources"
                " WHERE status='unreviewed' AND kind NOT IN ('url','template','manifest','index','registry')"
                " ORDER BY created DESC LIMIT 100")]   # rating is for evidence, not packaging (R4.1)
            counts = {"insights": c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM insights WHERE status='unreviewed'"
                                            " GROUP BY source_id, scope, text)").fetchone()[0],
                      "sources": c.execute("SELECT COUNT(*) FROM sources WHERE status='unreviewed'"
                                           " AND kind NOT IN ('url','template','manifest','index','registry')").fetchone()[0]}
        for u in unrated:
            u["assessment"] = json.loads(u["assessment"]) if u.get("assessment") else {}
        # what viewers rewatched first: insights from attention peaks lead their source, and those sources lead the queue
        for g in groups.values():
            eng = self.engagement(g["sid"])
            for it in g["items"]:
                it["attention"] = self.attention_at(eng, it["t"])
                it["peak"] = self.peak_at(eng, it["t"])
            g["items"].sort(key=lambda it: (not it["peak"], -it["attention"]))
            g["peaks"] = sum(1 for it in g["items"] if it["peak"])
        ordered = sorted(groups.values(), key=lambda g: -g["peaks"])
        return {"groups": ordered, "sources": unrated, "counts": counts}

    def review_insight(self, iid: int, status: str, confidence: str | None = None, basis: str | None = None,
                       change_class: str = "low-risk addition", reviewer: str = OWNER):
        """Accept / reject / dispute ... an insight (all its rows: one per entry it is about)."""
        if status not in INSIGHT_STATES:
            raise ValueError(status)
        with self._lock, self._db() as c:
            r = c.execute("SELECT source_id, scope, text, confidence FROM insights WHERE id=?", (iid,)).fetchone()
            if not r:
                raise KeyError(iid)
            conf = confidence if confidence in CONFIDENCE else r[3]
            c.execute("UPDATE insights SET status=?, confidence=?, basis=COALESCE(?, basis), reviewed=? WHERE source_id=?"
                      " AND scope=? AND text=?", (status, conf, basis, f"{reviewer} {now()}", r[0], r[1], r[2]))
            src = c.execute("SELECT src_id FROM sources WHERE id=?", (r[0],)).fetchone()[0]
            self.log_review(c, f"{src} {r[1]}: {r[2][:120]}", change_class, f"{status} ({conf})",
                            basis or ("self-review" if reviewer == OWNER else ""), reviewer)

    def review_source_insights(self, sid: int, status: str = "accepted", reviewer: str = OWNER):
        with self._lock, self._db() as c:
            n = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM insights WHERE source_id=? AND status='unreviewed'"
                          " GROUP BY scope, text)", (sid,)).fetchone()[0]
            c.execute("UPDATE insights SET status=?, reviewed=? WHERE source_id=? AND status='unreviewed'",
                      (status, f"{reviewer} {now()}", sid))
            src = c.execute("SELECT src_id FROM sources WHERE id=?", (sid,)).fetchone()[0]
            self.log_review(c, f"{src}: all {n} unreviewed insights", "low-risk addition", status, "self-review (batch)", reviewer)

    def review_source(self, sid: int, reputability: str, basis: str = "", reviewer: str = OWNER):
        if reputability not in RATINGS:
            raise ValueError(reputability)
        with self._lock, self._db() as c:
            r = c.execute("SELECT src_id, assessment FROM sources WHERE id=?", (sid,)).fetchone()
            a = json.loads(r[1]) if r and r[1] else {}
            if basis:
                a["basis"] = basis
            a.update(method="KB-Reputability-v1", date=now()[:10], assessor=reviewer)
            c.execute("UPDATE sources SET reputability=?, assessment=?, assessed_by=?, status='reviewed' WHERE id=?",
                      (reputability, json.dumps(a), reviewer, sid))
            self.log_review(c, f"{r[0]} rating", "source assessment", reputability, basis or a.get("basis", ""), reviewer)

    def review_log(self, limit: int = 200):
        with self._db() as c:
            return [dict(r) for r in c.execute("SELECT * FROM review_log ORDER BY id DESC LIMIT ?", (limit,))]

    def snapshot_reviews(self):
        with self._db() as c:
            return [tuple(r) for r in c.execute(
                "SELECT source_id, scope, text, status, confidence, basis, reviewed, label FROM insights"
                " WHERE status!='unreviewed' OR reviewed!='' GROUP BY source_id, scope, text")]

    def restore_reviews(self, snap):
        with self._lock, self._db() as c:
            for sid, scope, text, st, conf, basis, rev, label in snap:
                c.execute("UPDATE insights SET status=?, confidence=?, basis=?, reviewed=?, label=COALESCE(NULLIF(?,''),label)"
                          " WHERE source_id=? AND scope=? AND text=?", (st, conf, basis, rev, label, sid, scope, text))

    def source_by_src_id(self, src_id: str):
        with self._db() as c:
            r = c.execute("SELECT id FROM sources WHERE src_id=?", (src_id.upper(),)).fetchone()
            return r[0] if r else None

    # ================================================================ libraries + ID map (R1.2, R7)
    def register_library(self, ns: str, name: str, owner: str = "", description: str = "", origin: str = "") -> str:
        ns = re.sub(r"[^A-Z0-9]", "", ns.upper())[:12] or "IMPORT"
        with self._lock, self._db() as c:
            c.execute("INSERT INTO libraries(namespace,name,owner,kind,description,origin,created) VALUES(?,?,?,?,?,?,?)"
                      " ON CONFLICT(namespace) DO UPDATE SET name=excluded.name, owner=excluded.owner,"
                      " description=excluded.description, origin=excluded.origin",
                      (ns, name, owner, "own" if ns == HOME_NS else "imported", description, origin, now()))
        return ns

    def set_library_report(self, ns: str, report: dict):
        with self._lock, self._db() as c:
            c.execute("UPDATE libraries SET report=? WHERE namespace=?", (json.dumps(report, ensure_ascii=False), ns))

    def libraries(self):
        with self._db() as c:
            out = []
            for r in c.execute("SELECT * FROM libraries ORDER BY (kind='own') DESC, created"):
                d = dict(r)
                d["report"] = json.loads(d["report"]) if d.get("report") else {}
                d["nsources"] = c.execute("SELECT COUNT(*) FROM sources WHERE namespace=? AND kind!='url'", (d["namespace"],)).fetchone()[0]
                d["nunreviewed"] = c.execute(
                    "SELECT COUNT(*) FROM (SELECT 1 FROM insights i JOIN sources s ON s.id=i.source_id"
                    " WHERE s.namespace=? AND i.status='unreviewed' GROUP BY i.source_id, i.scope, i.text)",
                    (d["namespace"],)).fetchone()[0]
                d["ids"] = [dict(x) for x in c.execute("SELECT old_id, new_id, note FROM id_map WHERE namespace=?"
                                                       " ORDER BY old_id", (d["namespace"],))]
                out.append(d)
            return out

    def library(self, ns: str):
        return next((l for l in self.libraries() if l["namespace"] == ns.upper()), None)

    def map_id(self, ns: str, old_id: str, new_id: str, note: str = ""):
        """R7.3: an explicit old -> new mapping; an old ID is never silently re-bound to other evidence."""
        with self._lock, self._db() as c:
            c.execute("INSERT OR IGNORE INTO id_map VALUES(?,?,?,?)", (ns.upper(), old_id, new_id, note))

    def src_id_of(self, sid: int) -> str | None:
        with self._db() as c:
            r = c.execute("SELECT src_id FROM sources WHERE id=?", (sid,)).fetchone()
            return r[0] if r else None

    # ================================================================ tags
    def tags(self, status: str = "active"):
        with self._db() as c:
            return [dict(r) for r in c.execute(
                "SELECT t.*, (SELECT COUNT(*) FROM entity_tags et WHERE et.tag_id=t.id AND et.origin!='blocked') AS nent,"
                " (SELECT COUNT(*) FROM source_tags st WHERE st.tag_id=t.id AND st.origin!='blocked') AS nsrc"
                " FROM tags t WHERE t.status=? ORDER BY t.name COLLATE NOCASE", (status,))]

    def tag(self, slug: str):
        with self._db() as c:
            t = c.execute("SELECT * FROM tags WHERE slug=?", (slugify(slug),)).fetchone()
            if not t:
                return None
            t = dict(t)
            t["insights"] = [dict(r) for r in c.execute(
                "SELECT i.scope, i.text, MIN(i.t) AS t, s.id AS sid, s.title, GROUP_CONCAT(e.name, ', ') AS about,"
                " MIN(e.slug) AS about_slug, MAX(i.status) AS status, MAX(i.confidence) AS confidence"
                " FROM insights i JOIN sources s ON s.id=i.source_id JOIN entities e ON e.id=i.entity_id"
                " WHERE i.status NOT IN ('rejected','retracted') AND (i.entity_id IN (SELECT entity_id FROM entity_tags WHERE tag_id=? AND origin!='blocked')"
                "    OR i.source_id IN (SELECT source_id FROM source_tags WHERE tag_id=? AND origin!='blocked'))"
                " GROUP BY s.id, i.scope, i.text ORDER BY s.created DESC LIMIT 60", (t["id"], t["id"]))]
        t["entities"] = self.entities(tag=slug)
        t["sources"] = self.sources(kind=None, tag=slug)
        return t

    def save_tag(self, name: str, description: str = "", old_slug: str | None = None) -> str:
        name = name.strip()
        with self._lock, self._db() as c:
            if old_slug:
                c.execute("UPDATE tags SET name=?, description=?, slug=? WHERE slug=?",
                          (name, description.strip(), slugify(name), old_slug))
            else:
                c.execute("INSERT OR IGNORE INTO tags(slug,name,description,status,created) VALUES(?,?,?,'active',?)",
                          (slugify(name), name, description.strip(), now()))
                c.execute("UPDATE tags SET status='active' WHERE slug=?", (slugify(name),))
            return slugify(name)

    def set_tag_status(self, slug: str, status: str):
        with self._lock, self._db() as c:
            if status == "deleted":
                c.execute("DELETE FROM tags WHERE slug=?", (slug,))
            else:
                c.execute("UPDATE tags SET status=? WHERE slug=?", (status, slug))

    def tag_entity(self, slug: str, tag: str, on: bool = True):
        with self._lock, self._db() as c:
            eid = self._eid(c, slug)
            r = c.execute("SELECT id FROM tags WHERE slug=?", (slugify(tag),)).fetchone()
            tid = r[0] if r else None
            if on and not tid:
                c.execute("INSERT INTO tags(slug,name,status,created) VALUES(?,?,'active',?)", (slugify(tag), tag.strip(), now()))
                tid = c.execute("SELECT id FROM tags WHERE slug=?", (slugify(tag),)).fetchone()[0]
            if tid:  # removing leaves a 'blocked' marker so the tidy pass won't put it back
                c.execute("INSERT OR REPLACE INTO entity_tags VALUES(?,?,?)", (eid, tid, "manual" if on else "blocked"))

    def tag_source(self, sid: int, tag: str, on: bool = True):
        with self._lock, self._db() as c:
            r = c.execute("SELECT id FROM tags WHERE slug=?", (slugify(tag),)).fetchone()
            tid = r[0] if r else None
            if on and not tid:
                c.execute("INSERT INTO tags(slug,name,status,created) VALUES(?,?,'active',?)", (slugify(tag), tag.strip(), now()))
                tid = c.execute("SELECT id FROM tags WHERE slug=?", (slugify(tag),)).fetchone()[0]
            if tid:
                c.execute("INSERT OR REPLACE INTO source_tags VALUES(?,?,?)", (sid, tid, "manual" if on else "blocked"))

    # ================================================================ inbox
    def inbox_add(self, doc: dict, extension: str = "") -> int:
        with self._lock, self._db() as c:
            return c.execute("INSERT INTO inbox(extension,title,doc,status,created,updated) VALUES(?,?,?,'pending',?,?)",
                             (extension or doc.get("extension", ""), doc["source"].get("title", ""),
                              json.dumps(doc, ensure_ascii=False), now(), now())).lastrowid

    def inbox_next(self):
        with self._db() as c:
            r = c.execute("SELECT * FROM inbox WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
            return dict(r) if r else None

    def inbox_set(self, iid: int, status: str, error: str = "", source_id: int | None = None):
        with self._lock, self._db() as c:
            c.execute("UPDATE inbox SET status=?, error=?, source_id=IFNULL(?, source_id), updated=? WHERE id=?",
                      (status, error, source_id, now(), iid))

    def inbox_item(self, iid: int):
        with self._db() as c:
            r = c.execute("SELECT id, extension, title, status, error, source_id, created, updated FROM inbox WHERE id=?",
                          (iid,)).fetchone()
            return dict(r) if r else None

    def inbox(self, limit: int = 50):
        with self._db() as c:
            return [dict(r) for r in c.execute(
                "SELECT id, extension, title, status, error, source_id, created, updated FROM inbox"
                " ORDER BY id DESC LIMIT ?", (limit,))]

    def inbox_retry_failed(self):
        with self._lock, self._db() as c:
            c.execute("UPDATE inbox SET status='pending', error='' WHERE status IN ('failed','working')")

    # ================================================================ changes feed
    def changes(self, since: str) -> dict:
        """Everything new since an ISO date/time - the building block for daily/weekly recaps."""
        since = since.replace("T", " ")
        with self._db() as c:
            ents = [dict(r) for r in c.execute(
                "SELECT slug, name, kind, description, relevance, created FROM entities WHERE created>=?"
                " ORDER BY created DESC", (since,))]
            ins = [dict(r) for r in c.execute(  # one row per insight, even when it is about several entries
                "SELECT i.scope, i.text, MIN(i.t) AS t, MAX(i.created) AS created, GROUP_CONCAT(e.name, ', ') AS about,"
                " MIN(e.slug) AS about_slug, s.id AS source_id, s.title, MAX(i.status) AS status, MAX(i.confidence) AS confidence"
                " FROM insights i JOIN entities e ON e.id=i.entity_id JOIN sources s ON s.id=i.source_id"
                " WHERE i.created>=? AND i.status NOT IN ('rejected','retracted')"
                " GROUP BY s.id, i.scope, i.text ORDER BY created DESC, t", (since,))]
            notes = [dict(r) for r in c.execute(
                "SELECT n.body, n.created, e.name AS about, e.slug AS about_slug FROM notes n"
                " JOIN entities e ON e.id=n.entity_id WHERE n.created>=? ORDER BY n.created DESC", (since,))]
            proposed = [dict(r) for r in c.execute(
                "SELECT slug, name, description, created FROM tags WHERE status='proposed' AND created>=?", (since,))]
        return {"since": since, "sources": self.sources(kind=None, since=since), "entities": ents,
                "insights": ins, "notes": notes, "proposed_tags": proposed}

    def stored_docs(self):
        with self._db() as c:
            return [(r[0], json.loads(r[1]), json.loads(r[2]) if r[2] else None, r[3]) for r in c.execute(
                "SELECT id, doc, canon, extension FROM sources WHERE doc IS NOT NULL ORDER BY id")]

    # ================================================================ virtual library
    def agent_update(self, name: str, location: str | None = None, activity: str | None = None,
                     role: str | None = None, color: str | None = None, present: bool = True):
        """An agent (or visitor) moved / started doing something. Shown live in the virtual library."""
        name = (name or "Agent").strip()[:40]
        with self._lock, self._db() as c:
            row = c.execute("SELECT name FROM agents WHERE name=?", (name,)).fetchone()
            if not row:
                c.execute("INSERT INTO agents(name, role, color, location, activity, entered, updated, present)"
                          " VALUES(?,?,?,?,?,?,?,1)", (name, role or "", color or "", location or "entrance",
                                                       activity or "arrived", now(), now()))
            else:
                c.execute("UPDATE agents SET role=COALESCE(?,role), color=COALESCE(?,color), location=COALESCE(?,location),"
                          " activity=COALESCE(?,activity), updated=?, present=?,"
                          " entered=CASE WHEN present=0 AND ?=1 THEN ? ELSE entered END WHERE name=?",
                          (role, color, location, activity, now(), int(present), int(present), now(), name))
            if activity or location:
                c.execute("INSERT INTO agent_log(name, location, text, created) VALUES(?,?,?,?)",
                          (name, location or "", activity or "", now()))
                c.execute("DELETE FROM agent_log WHERE id < (SELECT MAX(id) - 500 FROM agent_log)")

    def agents_present(self, minutes: int = 15):
        import datetime as dt

        cutoff = (dt.datetime.now() - dt.timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        with self._db() as c:
            return [dict(r) for r in c.execute(
                "SELECT name, role, color, location, activity, entered, updated FROM agents"
                " WHERE present=1 AND updated>=? ORDER BY entered", (cutoff,))]

    def agent_log(self, limit: int = 30):
        with self._db() as c:
            return [dict(r) for r in c.execute("SELECT * FROM agent_log ORDER BY id DESC LIMIT ?", (limit,))]

    def layout(self) -> dict:
        """The building: wings -> bookcases -> books. The 3D client turns this into geometry."""
        import datetime as dt

        ents = self.entities()
        recent = (dt.datetime.now() - dt.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

        def book(e):
            return {"slug": e["slug"], "name": e["name"], "kind": e["kind"], "nsrc": e["nsrc"],
                    "relevance": e["relevance"], "tags": [t["name"] for t in e["tags"]],
                    "owner": e["owner"]["name"] if e.get("owner") else None, "new": (e["created"] or "") >= recent,
                    "insights": e["ninsights"], "notes": e["nnotes"]}

        def chunked(cid, title, items, size=150):
            out = []
            for i in range(0, max(len(items), 1), size):
                part = items[i:i + size]
                if part:
                    out.append({"id": cid if i == 0 else f"{cid}~{i // size + 1}",
                                "title": title if i == 0 else f"{title} ({i // size + 1})", "books": part})
            return out

        gk = [e for e in ents if e["kind"] in KNOWLEDGE and not e.get("owner")]
        by_tag, untagged = {}, []
        for e in gk:  # a book lives on its first tag's shelf (it shows all its tags)
            if e["tags"]:
                by_tag.setdefault((e["tags"][0]["slug"], e["tags"][0]["name"]), []).append(book(e))
            else:
                untagged.append(book(e))
        gk_cases = []
        for (slug, name), bs in sorted(by_tag.items(), key=lambda x: (-len(x[1]), x[0][1].lower())):
            gk_cases += chunked(f"tag:{slug}", name, bs)
        topics = [b for b in untagged if b["kind"] == "topic"]
        rest = [b for b in untagged if b["kind"] != "topic"]
        gk_cases += chunked("topics", "Topics", topics) + chunked("concepts", "Concepts & techniques", rest)

        labels = {"tool": "Tools", "llm": "Models (LLMs)", "dataset": "Datasets", "service": "Services & platforms",
                  "library": "Libraries & SDKs",
                  "company": "Companies", "person": "People"}
        pr_cases = []
        for k, label in labels.items():
            pr_cases += chunked(f"kind:{k}", label, [book(e) for e in ents if e["kind"] == k])

        tk_cases = []
        owners = {}
        for e in ents:
            if e["kind"] in KNOWLEDGE and e.get("owner"):
                owners.setdefault((e["owner"]["slug"], e["owner"]["name"]), []).append(book(e))
        for (slug, name), bs in sorted(owners.items(), key=lambda x: -len(x[1])):
            tk_cases += chunked(f"tool:{slug}", f"{name} knowledge", bs)

        media = [{"id": s["id"], "title": s["title"], "kind": s["kind"], "author": s["channel"],
                  "tags": [t["name"] for t in s["tags"]], "new": (s["created"] or "") >= recent}
                 for s in self.sources(kind=None, limit=24)]
        return {"wings": [
            {"id": "general", "title": "General knowledge", "cases": gk_cases},
            {"id": "products", "title": "Tools & products", "cases": pr_cases},
            {"id": "toolknowledge", "title": "Tool-specific knowledge", "cases": tk_cases}],
            "media": media, "counts": {"entries": len(ents), "sources": len(media)},
            "kinds": KINDS}

    # ================================================================ export
    def export_markdown(self, out: Path) -> int:
        """Obsidian-style vault: index.md, entities/<slug>.md, sources/<id>.md."""
        out = Path(out)
        (out / "entities").mkdir(parents=True, exist_ok=True)
        (out / "sources").mkdir(parents=True, exist_ok=True)
        ents = self.entities()
        for row in ents:
            e = self.entity(row["slug"])
            parent = e["ancestors"][-1] if e["ancestors"] else None
            L = ["---", f"kind: {e['kind']}", f"aliases: [{', '.join(json.dumps(a) for a in e['aliases'])}]",
                 f"tags: [{', '.join(json.dumps(t['name']) for t in e['tags'])}]",
                 f"parent: {json.dumps(parent['name']) if parent else ''}", f"updated: {e['updated']}", "---",
                 f"# {e['name']}", ""]
            if e["ancestors"]:
                L += [" › ".join(f"[[entities/{a['slug']}|{a['name']}]]" for a in e["ancestors"]) + f" › {e['name']}", ""]
            L += [e["description"] or "*No description yet.*", ""]
            if e["sub_knowledge"]:
                L += [f"## {e['name']} knowledge", ""] + [
                    f"{'  ' * (x['depth'] - 1)}- [[entities/{x['slug']}|{x['name']}]] ({x['kind']}) {x['description'] or ''}"
                    for x in e["sub_knowledge"]] + [""]
            others = [c for c in e["children"] if c["kind"] not in KNOWLEDGE or e["kind"] in KNOWLEDGE]
            if others:
                L += ["## Includes", "", ", ".join(f"[[entities/{c['slug']}|{c['name']}]]" for c in others), ""]
            for scope, head in (("principle", "Principles"), ("tip", "Tool-specific tips")):
                xs = [i for i in e["insights"] if i["scope"] == scope]
                if xs:
                    L += [f"## {head}", ""] + [f"- {i['text']} — {i['status']}, {i['confidence']} confidence"
                                               f"{', ' + i['label'] if i['label'] else ''} · {i['src_id']} "
                                               f"[[sources/{i['sid']}|{i['title']}]]" for i in xs] + [""]
            if e["notes"]:
                L += ["## Internal notes", ""] + [f"- ({n['created'][:10]}) {n['body']}" for n in e["notes"]] + [""]
            res = [m for m in e["mentions"] if m["kind"] == "url"]
            if res:
                L += ["## Resources", ""] + [f"- [{m['title']}]({m['url']}) {m['context'] or ''}" for m in res] + [""]
            vids = [m for m in e["mentions"] if m["kind"] == "video"]
            if vids:
                L += ["## Seen in", ""]
                for sid in dict.fromkeys(m["sid"] for m in vids):
                    ms = [m for m in vids if m["sid"] == sid]
                    L.append(f"- [[sources/{sid}|{ms[0]['title']}]] ({ms[0]['published'] or '?'})")
                    L += [f"  - [{hms(m['t'])}]({at_time(m['url'], m['t'])}) {m['context'] or ''}"
                          for m in ms if m["t"] is not None]
                L.append("")
            if e["related"]:
                L += ["## Related", "", ", ".join(f"[[entities/{r['slug']}|{r['name']}]]" for r in e["related"]), ""]
            (out / "entities" / f"{e['slug']}.md").write_text("\n".join(L), encoding="utf-8")

        for s in self.sources(kind=None):
            d = self.source(s["id"])
            L = [f"# {d['title']}", "", " · ".join(x for x in [d["channel"], d["published"]] if x), ""]
            if d["url"]:
                L += [f"[Watch]({d['url']})", ""]
            if d["local_path"]:
                lp = Path(d["local_path"])
                L += [f"Lesson: `{lp.with_name(lp.stem + '.lesson.md')}`", ""]
            L += [d["summary"] or "", "", "## Entities", ""]
            L += [f"- [[entities/{e['slug']}|{e['name']}]] ({e['kind']}{', ' + e['relevance'] if e['relevance'] else ''})"
                  for e in d["entities"]]
            (out / "sources" / f"{d['id']}.md").write_text("\n".join(L), encoding="utf-8")

        reg = ["# Source registry", "", f"*Exported {now()} · ratings use KB-Reputability-v1 (see RULES.md R4)*", "",
               "| ID | Title | Author | Date | Kind | Rating | Assessed by | Status | Locator |", "|---|---|---|---|---|---|---|---|---|"]
        with self._db() as c:
            for r in c.execute("SELECT src_id, title, channel, published, kind, reputability, assessed_by, status, url"
                               " FROM sources ORDER BY src_id"):
                loc = r[8] if r[8] and not str(r[8]).startswith(("file:", "import:")) else "local / private"
                reg.append("| " + " | ".join(str(x or "").replace("|", "/") for x in (*r[:8], loc)) + " |")
        (out / "source-registry.md").write_text("\n".join(reg), encoding="utf-8")
        log = ["# Review log", "", "| Date | Target | Class | Decision | Reviewer | Basis |", "|---|---|---|---|---|---|"]
        log += [f"| {r['created'][:16]} | {r['target']} | {r['change_class']} | {r['decision']} | {r['reviewer']} | {r['basis']} |"
                for r in self.review_log(5000)]
        (out / "review-log.md").write_text("\n".join(log), encoding="utf-8")

        idx = ["# Reference library", "", f"*Exported {now()}* · [source registry](source-registry.md) · [review log](review-log.md)", ""]
        for title, group in (("General knowledge", KNOWLEDGE), ("Tools & products", PRODUCTS)):
            idx += [f"# {title}", ""]
            for k in group:
                ks = [e for e in ents if e["kind"] == k and not e.get("owner")]
                if ks:
                    idx += [f"## {k.title()} ({len(ks)})", ""]
                    for e in ks:
                        idx.append(f"- [[entities/{e['slug']}|{e['name']}]]"
                                   + (f" — part of [[entities/{e['parent_slug']}|{e['parent_name']}]]" if e["parent_slug"] else "")
                                   + f" · {e['nsrc']} source(s)")
                        if group is PRODUCTS:
                            idx += [f"    - knowledge: [[entities/{x['slug']}|{x['name']}]]"
                                    for x in ents if x.get("owner") and x["owner"]["slug"] == e["slug"]]
                    idx.append("")
        (out / "index.md").write_text("\n".join(idx), encoding="utf-8")
        return len(ents)




# =========================================================================== #
# document helpers + curation
# =========================================================================== #
def analysis_to_doc(a: dict, local_path: str) -> dict:
    """ytdl *.analysis.json -> KB document (same conversion the ytdl extension does)."""
    m = a["meta"]
    return {
        "contract": "kb-doc/1",
        "extension": "ytdl",
        "source": {"kind": "video", "title": m.get("title"), "url": m.get("url"), "external_id": m.get("id") or "",
                   "author": m.get("channel"), "published": m.get("upload_date"), "duration": m.get("duration"),
                   "local_path": local_path, "summary": (a.get("overview") or {}).get("summary", "")},
        "overview": a.get("overview") or {},
        "segments": [{"start": s.get("start"), "end": s.get("end"), "text": s.get("transcript", ""),
                      "on_screen": s.get("on_screen", ""), "steps": s.get("steps", []),
                      "verbatim": s.get("verbatim", []), "entities": s.get("entities", []),
                      "claims": s.get("claims", []), "frames": s.get("frames", [])} for s in a.get("sections", [])],
        "extra": {"model": a.get("model"), "analyzed_at": a.get("analyzed_at"), "perf": a.get("perf")},
    }


def curate(lib: "Library", doc: dict, extension: str = "", model: str | None = None, retidy: bool = True,
           canon: dict | None = None) -> int:
    """Run the tidy pass (if the model is available) and file the document. Returns source id."""
    import llm

    model = model or llm.DEFAULT_MODEL
    if doc.get("no_tidy"):       # templates, registries: kept as sources, nothing to extract
        return lib.ingest_doc(doc, None, extension)
    if retidy or not canon:
        ok, _ = llm.ollama_available(model)
        if ok:
            canon = llm.canonicalize(doc, lib.candidates(llm.raw_entity_names(doc)), lib.tags(), model,
                                     extra_rules=lib.local_rules())
    return lib.ingest_doc(doc, canon, extension)


def rebuild(lib: "Library", retidy: bool = False, progress=None) -> dict:
    """Re-file every stored document. retidy=True re-runs the tidy pass (slow; picks up new tags,
    new rules and the current library); otherwise each source's saved tidy result is reused."""
    import llm

    docs = lib.stored_docs()
    canons = {}
    model_ok = llm.ollama_available(llm.DEFAULT_MODEL)[0]
    for i, (sid, doc, canon, ext) in enumerate(docs, 1):
        stale = not canon or canon.get("version", 0) < llm.CANON_VERSION
        if doc.get("no_tidy"):
            canon = None
        elif (retidy or stale) and model_ok:
            if progress:
                progress(f"tidying {i}/{len(docs)}: {doc['source'].get('title', '')[:60]}")
            canon = llm.canonicalize(doc, lib.candidates(llm.raw_entity_names(doc)), lib.tags(),
                                     extra_rules=lib.local_rules())
        canons[sid] = canon
    if progress:
        progress("re-filing")
    reviews = lib.snapshot_reviews()     # your accept/reject decisions survive (R6)
    purged = lib.purge_auto()
    for sid, doc, _, ext in docs:
        lib.ingest_doc(doc, canons[sid], ext)
    lib.restore_reviews(reviews)
    return {"sources": len(docs), "purged": purged, "orphans_removed": lib.delete_orphans()}
