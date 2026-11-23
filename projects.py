"""
projects — a knowledge article for each of your own projects: what it is, where the code lives, its version
history and its decision log. A project is an entry of kind `project` (so anything filed under it - components,
sub-projects, its own concepts - is that project's sub-library); this module adds the structured parts.

Decisions are kept as short decision records (context, decision, alternatives, consequences, who decided).
Agents may *propose* decisions and log versions; only you accept a decision (house rules R6).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from library import OWNER, now, slugify

SCHEMA = """
CREATE TABLE IF NOT EXISTS project_info(
  entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'active', repo TEXT DEFAULT '', local_path TEXT DEFAULT '', homepage TEXT DEFAULT '',
  stack TEXT DEFAULT '', version TEXT DEFAULT '', started TEXT DEFAULT '', updated TEXT);
CREATE TABLE IF NOT EXISTS project_versions(
  id INTEGER PRIMARY KEY, entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
  version TEXT, date TEXT DEFAULT '', ref TEXT DEFAULT '', notes TEXT DEFAULT '', by TEXT DEFAULT '',
  created TEXT, seed_key TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS project_decisions(
  id INTEGER PRIMARY KEY, entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE, number INTEGER,
  title TEXT, date TEXT DEFAULT '', status TEXT DEFAULT 'accepted', context TEXT DEFAULT '', decision TEXT DEFAULT '',
  alternatives TEXT DEFAULT '', consequences TEXT DEFAULT '', by TEXT DEFAULT '', superseded_by INTEGER,
  created TEXT, updated TEXT, seed_key TEXT UNIQUE);
"""
STATUSES = ["idea", "active", "paused", "maintained", "done", "archived"]
DECISION_STATES = ["proposed", "accepted", "superseded", "rejected"]
SEED = Path(__file__).resolve().parent / "seeds" / "projects.json"


def setup(lib):
    with lib._db() as c:
        c.executescript(SCHEMA)
    seed(lib)


def _eid(lib, c, ref):
    return lib._eid(c, ref)


def did(slug: str, n: int) -> str:
    return f"D-{n:03d}"


# ------------------------------------------------------------------ read
def get(lib, ref: str) -> dict | None:
    """Everything about one project (None if `ref` isn't a project)."""
    with lib._db() as c:
        try:
            eid = _eid(lib, c, ref)
        except KeyError:
            return None
        e = c.execute("SELECT id, slug, name, kind, description FROM entities WHERE id=?", (eid,)).fetchone()
        if not e or e["kind"] != "project":
            return None
        info = c.execute("SELECT * FROM project_info WHERE entity_id=?", (eid,)).fetchone()
        info = dict(info) if info else {"status": "active", "repo": "", "local_path": "", "homepage": "", "stack": "",
                                         "version": "", "started": "", "updated": "", "office": ""}
        versions = [dict(r) for r in c.execute(
            "SELECT * FROM project_versions WHERE entity_id=? ORDER BY date DESC, id DESC", (eid,))]
        decisions = [dict(r) for r in c.execute(
            "SELECT * FROM project_decisions WHERE entity_id=? ORDER BY number", (eid,))]
        comps = [dict(r) for r in c.execute(
            "SELECT e.slug, e.name, e.kind, e.description, pi.status, pi.version FROM entities e"
            " LEFT JOIN project_info pi ON pi.entity_id=e.id WHERE e.parent_id=? AND e.kind NOT IN"
            " ('topic','concept','technique') ORDER BY (e.kind='project') DESC, e.name COLLATE NOCASE", (eid,))]
    for d in decisions:
        d["id_label"] = did(e["slug"], d["number"])
    cur = info.get("version") or (versions[0]["version"] if versions else "")
    return {"slug": e["slug"], "name": e["name"], "description": e["description"], "info": info,
            "version": cur, "versions": versions, "decisions": decisions, "components": comps}


def list_projects(lib) -> list[dict]:
    with lib._db() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT e.slug, e.name, e.description, p.slug AS parent_slug, p.name AS parent_name,"
            " IFNULL(pi.status,'active') AS status, IFNULL(pi.repo,'') AS repo, IFNULL(pi.version,'') AS version,"
            " (SELECT version FROM project_versions v WHERE v.entity_id=e.id ORDER BY date DESC, id DESC LIMIT 1) AS latest,"
            " (SELECT COUNT(*) FROM project_decisions d WHERE d.entity_id=e.id) AS ndecisions,"
            " (SELECT COUNT(*) FROM project_decisions d WHERE d.entity_id=e.id AND d.status='proposed') AS nproposed,"
            " (SELECT MAX(date) FROM project_decisions d WHERE d.entity_id=e.id) AS last_decision"
            " FROM entities e LEFT JOIN entities p ON p.id=e.parent_id LEFT JOIN project_info pi ON pi.entity_id=e.id"
            " WHERE e.kind='project' ORDER BY e.name COLLATE NOCASE")]
    for r in rows:
        r["version"] = r["version"] or r["latest"] or ""
    return rows


# ------------------------------------------------------------------ write
def create(lib, name: str, description: str = "", parent: str = "", **info) -> str:
    slug = lib.create_entity(name, "project", description, parent)
    lib.set_kind(slug, "project")
    update_info(lib, slug, **info)
    return slug


def update_info(lib, ref: str, **info):
    keys = ("status", "repo", "local_path", "homepage", "stack", "version", "started", "office")
    vals = {k: str(v).strip() for k, v in info.items() if k in keys and v is not None}
    if "status" in vals and vals["status"] not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    with lib._lock, lib._db() as c:
        eid = _eid(lib, c, ref)
        c.execute("UPDATE entities SET kind='project', origin='manual', updated=? WHERE id=?", (now(), eid))
        c.execute("INSERT OR IGNORE INTO project_info(entity_id, updated) VALUES(?,?)", (eid, now()))
        for k, v in vals.items():
            c.execute(f"UPDATE project_info SET {k}=?, updated=? WHERE entity_id=?", (v, now(), eid))


def add_version(lib, ref: str, version: str, date: str | None = None, ref_: str = "", notes: str = "", by: str = OWNER,
                seed_key: str | None = None, make_current: bool = True) -> int:
    version = version.strip()
    if not version:
        raise ValueError("version is required")
    with lib._lock, lib._db() as c:
        eid = _eid(lib, c, ref)
        cur = c.execute("INSERT OR IGNORE INTO project_versions(entity_id,version,date,ref,notes,by,created,seed_key)"
                        " VALUES(?,?,?,?,?,?,?,?)", (eid, version, now()[:10] if date is None else date, ref_, notes, by, now(), seed_key))
        if make_current and cur.rowcount:
            c.execute("INSERT OR IGNORE INTO project_info(entity_id, updated) VALUES(?,?)", (eid, now()))
            c.execute("UPDATE project_info SET version=?, updated=? WHERE entity_id=?", (version, now(), eid))
            c.execute("UPDATE entities SET updated=? WHERE id=?", (now(), eid))
        return cur.lastrowid if cur.rowcount else 0


def delete_version(lib, vid: int):
    with lib._lock, lib._db() as c:
        c.execute("DELETE FROM project_versions WHERE id=?", (vid,))


def add_decision(lib, ref: str, title: str, decision: str, context: str = "", alternatives: str = "",
                 consequences: str = "", by: str = OWNER, status: str = "accepted", date: str | None = None,
                 supersedes: int | None = None, seed_key: str | None = None) -> int:
    if status not in DECISION_STATES:
        raise ValueError(f"status must be one of {', '.join(DECISION_STATES)}")
    if not title.strip() or not decision.strip():
        raise ValueError("title and decision are required")
    with lib._lock, lib._db() as c:
        eid = _eid(lib, c, ref)
        if seed_key and c.execute("SELECT 1 FROM project_decisions WHERE seed_key=?", (seed_key,)).fetchone():
            return 0
        n = (c.execute("SELECT MAX(number) FROM project_decisions WHERE entity_id=?", (eid,)).fetchone()[0] or 0) + 1
        c.execute("INSERT INTO project_decisions(entity_id,number,title,date,status,context,decision,alternatives,"
                  "consequences,by,created,updated,seed_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (eid, n, title.strip(), now()[:10] if date is None else date, status, context, decision, alternatives, consequences,
                   by, now(), now(), seed_key))
        if supersedes:
            c.execute("UPDATE project_decisions SET status='superseded', superseded_by=?, updated=? WHERE entity_id=?"
                      " AND number=?", (n, now(), eid, int(supersedes)))
        c.execute("UPDATE entities SET updated=? WHERE id=?", (now(), eid))
        slug = lib._slug(c, eid)
        if status != "proposed":
            lib.log_review(c, f"{slug} {did(slug, n)}: {title[:100]}", "project decision", status, "", by or OWNER)
        return n


def set_decision_status(lib, ref: str, number: int, status: str, reviewer: str = OWNER):
    if status not in DECISION_STATES:
        raise ValueError(status)
    with lib._lock, lib._db() as c:
        eid = _eid(lib, c, ref)
        r = c.execute("SELECT title FROM project_decisions WHERE entity_id=? AND number=?", (eid, int(number))).fetchone()
        if not r:
            raise KeyError(number)
        c.execute("UPDATE project_decisions SET status=?, updated=? WHERE entity_id=? AND number=?",
                  (status, now(), eid, int(number)))
        c.execute("UPDATE entities SET updated=? WHERE id=?", (now(), eid))
        slug = lib._slug(c, eid)
        lib.log_review(c, f"{slug} {did(slug, int(number))}: {r[0][:100]}", "project decision", status, "", reviewer)


def from_git(lib, ref: str) -> dict:
    """Read tags (as versions) and the remote URL from the project's local git checkout, if it has one."""
    p = get(lib, ref)
    if not p:
        raise KeyError(ref)
    path = Path(p["info"].get("local_path") or "")
    git = shutil.which("git")
    if not git:
        return {"ok": False, "message": "git is not installed on this computer"}
    if not path.is_dir() or not (path / ".git").exists():
        return {"ok": False, "message": f"{path or 'No local folder set'} is not a git checkout"}

    def run(*args):
        r = subprocess.run([git, "-C", str(path), *args], capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else ""

    added = 0
    for line in run("tag", "--sort=creatordate", "--format=%(refname:short)|%(creatordate:short)|%(subject)").splitlines():
        tag, d, subj = (line.split("|", 2) + ["", ""])[:3]
        if tag and add_version(lib, ref, tag, d, f"git tag {tag}", subj, "git", seed_key=f"git:{p['slug']}:{tag}"):
            added += 1
    remote = run("remote", "get-url", "origin")
    if remote and not p["info"].get("repo"):
        update_info(lib, ref, repo=remote)
    head = run("log", "-1", "--format=%h %ad %s", "--date=short")
    return {"ok": True, "message": f"{added} new version(s) from git tags" + (f"; HEAD {head}" if head else ""),
            "remote": remote}


def seed(lib):
    """First-run articles for the projects in seeds/projects.json. Only adds what is missing: your edits stay."""
    if not SEED.exists():
        return 0
    data = json.loads(SEED.read_text(encoding="utf-8"))
    done = 0
    with lib._db() as c:
        have = {r[0] for r in c.execute("SELECT v FROM meta WHERE k LIKE 'seed:project:%'")}
    for p in data.get("projects", []):
        key = p["key"]
        if key in have:
            continue
        slug = create(lib, p["name"], p.get("description", ""), p.get("parent", ""), **p.get("info", {}))
        for a in p.get("aliases", []):
            lib.add_alias(slug, a)
        for t in p.get("tags", []):
            lib.tag_entity(slug, t, True)
        for i, v in enumerate(p.get("versions", [])):
            add_version(lib, slug, v["version"], v.get("date", ""), v.get("ref", ""), v.get("notes", ""),
                        v.get("by", OWNER), seed_key=f"seed:{key}:v:{v['version']}", make_current=False)
        for d in p.get("decisions", []):
            add_decision(lib, slug, d["title"], d["decision"], d.get("context", ""), d.get("alternatives", ""),
                         d.get("consequences", ""), d.get("by", OWNER), d.get("status", "accepted"), d.get("date", ""),
                         seed_key=f"seed:{key}:d:{slugify(d['title'])}")
        for n in p.get("notes", []):
            lib.add_note(slug, n)
        with lib._db() as c:
            c.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (f"seed:project:{key}", key))
        done += 1
    return done


# ------------------------------------------------------------------ OKF body
def okf_sections(p: dict) -> tuple[list[str], dict, str]:
    """-> (markdown lines, x-kb-project frontmatter, substance for change detection)."""
    i = p["info"]
    L = ["# Project", ""]
    for label, v in (("Status", i.get("status")), ("Current version", p["version"]), ("Repository", i.get("repo")),
                     ("Homepage", i.get("homepage")), ("Stack", i.get("stack")), ("Started", i.get("started"))):
        if v:
            L.append(f"* **{label}:** {v}")
    L.append("")
    if p["versions"]:
        L += ["# Version history", "", "| Version | Date | Ref | Notes |", "|---|---|---|---|"]
        L += [f"| {_cell(v['version'])} | {_cell(v['date'])} | {_cell(v['ref'])} | {_cell(v['notes'])} |" for v in p["versions"]]
        L.append("")
    if p["decisions"]:
        L += ["# Decision log", ""]
        for d in p["decisions"]:
            L += [f"## {d['id_label']} {d['title']}", "",
                  f"_{d['status']} · {d['date'] or 'undated'} · decided by {d['by'] or OWNER}"
                  + (f" · superseded by D-{d['superseded_by']:03d}" if d.get("superseded_by") else "") + "_", ""]
            for head, k in (("Context", "context"), ("Decision", "decision"), ("Alternatives", "alternatives"),
                            ("Consequences", "consequences")):
                if d.get(k):
                    L += [f"**{head}.** {d[k].strip()}", ""]
    x = {"status": i.get("status") or "active", "version": p["version"], "repo": i.get("repo") or "",
         "decisions": len(p["decisions"]), "versions": len(p["versions"])}
    sub = json.dumps([i.get(k) for k in ("status", "repo", "homepage", "stack", "version", "started")]
                     + [[v["version"], v["date"], v["notes"]] for v in p["versions"]]
                     + [[d["title"], d["status"], d["decision"], d["context"]] for d in p["decisions"]])
    return L, x, sub


def _cell(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).replace("|", "/")
