"""
skills — the library's skill store. Agents come here to find and pull the skills they need.

A skill is an Agent Skills package: a folder with a SKILL.md (YAML frontmatter `name` and `description`,
then instructions) plus any scripts, references and assets it uses. Packages arrive as a .zip / .skill file,
a folder on this computer, or a GitHub repository (every SKILL.md found in it becomes a skill, so skill packs
and plugins work too). Each upload that changes a skill's files is a new version; old versions are kept.

House rules apply: a skill is instructions an agent will follow, so new skills and new versions arrive
**unreviewed**. Agents are served the version you approved (R6; R3.5 - nothing here grants permissions).
"""
import hashlib
import io
import json
import re
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from library import OWNER, now, slugify

SCHEMA = """
CREATE TABLE IF NOT EXISTS skills(
  name TEXT PRIMARY KEY, title TEXT, description TEXT DEFAULT '', latest TEXT, approved TEXT DEFAULT '',
  status TEXT DEFAULT 'unreviewed', tags TEXT DEFAULT '[]', about TEXT DEFAULT '[]', source TEXT DEFAULT '',
  license TEXT DEFAULT '', downloads INTEGER DEFAULT 0, created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS skill_versions(
  id INTEGER PRIMARY KEY, name TEXT REFERENCES skills(name) ON DELETE CASCADE, version TEXT, sha256 TEXT,
  size INTEGER, files TEXT, frontmatter TEXT, has_scripts INTEGER DEFAULT 0, source TEXT DEFAULT '',
  uploaded TEXT, uploaded_by TEXT DEFAULT '', status TEXT DEFAULT 'unreviewed', reviewed TEXT DEFAULT '',
  notes TEXT DEFAULT '', UNIQUE(name, version));
"""
STATES = ["unreviewed", "approved", "blocked"]
SCRIPT_EXT = {".py", ".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".ps1", ".bat", ".cmd", ".exe", ".dll", ".rb",
              ".pl", ".php", ".jar", ".so", ".dylib", ".vbs", ".applescript"}
TEXT_EXT = {".md", ".txt", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".csv", ".html", ".css",
            ".xml", ".ps1", ".bat", ".cfg", ".ini", ".sql", ".rst", ".mjs", ".cjs", ".tsx", ".jsx", ".r", ".rb"}
MAX_FILES, MAX_TOTAL, MAX_FILE = 800, 80 * 1024 * 1024, 40 * 1024 * 1024
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def setup(lib):
    with lib._db() as c:
        c.executescript(SCHEMA)


def store_dir(lib) -> Path:
    return Path(lib.path).parent / "skills"


def safe_name(n: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (n or "").lower()).strip("-")[:64]
    return s or "skill"


# ------------------------------------------------------------------ reading packages
def read_package(src) -> list[dict]:
    """zip bytes / .zip or .skill path / folder -> [{path, data}] (unsafe paths and hidden files dropped)."""
    files, total = [], 0

    def take(path, size, read):
        nonlocal total
        p = PurePosixPath(path.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts or "__MACOSX" in p.parts or any(x in (".git", ".DS_Store") for x in p.parts):
            return
        if size > MAX_FILE or total + size > MAX_TOTAL or len(files) >= MAX_FILES:
            raise ValueError("package too large (limit 800 files / 80 MB)")
        total += size
        files.append({"path": str(p), "data": read()})

    if isinstance(src, (bytes, bytearray)) or str(src).lower().endswith((".zip", ".skill")):
        z = zipfile.ZipFile(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
        for i in z.infolist():
            if not i.is_dir():
                take(i.filename, i.file_size, lambda i=i: z.read(i))
    else:
        root = Path(src)
        if not root.is_dir():
            raise FileNotFoundError(f"{src} is not a folder, .zip or .skill file")
        for f in sorted(root.rglob("*")):
            if f.is_file() and not f.is_symlink():
                take(f.relative_to(root).as_posix(), f.stat().st_size, f.read_bytes)
    return files


def github_zip(url: str, token: str = "") -> tuple[bytes, str]:
    """github.com/<owner>/<repo>[/tree/<branch>/<sub/path>] -> (zip bytes, sub path inside the repo)."""
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?(?:/tree/([^/\s]+)(?:/(.+?))?)?/?$",
                 url.strip())
    if not m and re.fullmatch(r"[\w.-]+/[\w.-]+", url.strip()):
        m = re.match(r"^([\w.-]+)/([\w.-]+)()()$", url.strip())
    if not m:
        raise ValueError("use a GitHub URL like https://github.com/owner/repo or .../tree/main/skills/name")
    owner, repo, branch, sub = m.group(1), m.group(2), m.group(3) or "HEAD", (m.group(4) or "").strip("/")
    req = urllib.request.Request(f"https://codeload.github.com/{owner}/{repo}/zip/{'refs/heads/' + branch if branch != 'HEAD' else 'HEAD'}",
                                 headers={"User-Agent": "kb-skill-store", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed host
            data = r.read(MAX_TOTAL + 1)
    except urllib.error.HTTPError as e:
        hint = (" - check the owner/repo and branch; a private repo needs a GitHub token (Hub watcher → Tokens)"
                if e.code in (401, 403, 404) else "")
        raise ValueError(f"GitHub said {e.code} {e.reason} for {owner}/{repo}@{branch}{hint}") from None
    except urllib.error.URLError as e:
        raise ValueError(f"couldn't reach GitHub: {e.reason}") from None
    if len(data) > MAX_TOTAL:
        raise ValueError("repository archive too large")
    return data, sub


def find_skills(files: list[dict], sub: str = "") -> list[dict]:
    """Every folder with a SKILL.md is a skill. Nested skills are separate; their files aren't counted twice."""
    import okf

    if files:  # codeload/zip packaging: one top folder
        tops = {f["path"].split("/")[0] for f in files}
        if len(tops) == 1 and all("/" in f["path"] for f in files):
            for f in files:
                f["path"] = f["path"].split("/", 1)[1]
    if sub:
        files = [dict(f, path=f["path"][len(sub) + 1:]) for f in files if f["path"].startswith(sub + "/")]
    roots = sorted({str(PurePosixPath(f["path"]).parent) for f in files if PurePosixPath(f["path"]).name.lower() == "skill.md"},
                   key=len, reverse=True)
    out, claimed = [], set()
    for root in roots:
        pre = "" if root == "." else root + "/"
        mine = [f for f in files if f["path"].startswith(pre) and f["path"] not in claimed]
        claimed |= {f["path"] for f in mine}
        sk = next(f for f in mine if f["path"][len(pre):].lower() == "skill.md")
        text = sk["data"].decode("utf-8", "replace")
        meta, body, err = okf.read_meta(text)
        meta = meta or {}
        name = safe_name(str(meta.get("name") or (PurePosixPath(root).name if root != "." else "skill")))
        warn = []
        if err:
            warn.append(err)
        if not meta.get("name"):
            warn.append("SKILL.md has no `name`; used the folder name")
        elif not NAME_RE.match(str(meta["name"])):
            warn.append(f"name {meta['name']!r} isn't lowercase-with-hyphens; stored as {name}")
        if not meta.get("description"):
            warn.append("SKILL.md has no `description` - agents use it to decide when to load the skill")
        rel = [{"path": f["path"][len(pre):], "data": f["data"]} for f in mine]
        rel = [f for f in rel if f["path"]]
        out.append({"name": name, "root": root, "meta": meta, "body": body, "files": rel, "warnings": warn})
    return sorted(out, key=lambda s: s["name"])


def _hash(files) -> str:
    h = hashlib.sha256()
    for f in sorted(files, key=lambda f: f["path"]):
        h.update(f["path"].encode() + b"\0" + hashlib.sha256(f["data"]).digest())
    return h.hexdigest()


# ------------------------------------------------------------------ storing
def add_package(lib, src, source: str = "", uploaded_by: str = OWNER, sub: str = "", only: list[str] | None = None) -> dict:
    files = read_package(src) if not isinstance(src, list) else src
    found = find_skills(files, sub)
    if only:
        found = [s for s in found if s["name"] in only]
    report = {"source": source, "skills": [], "found": len(found)}
    for s in found:
        report["skills"].append(_store(lib, s, source, uploaded_by))
    if not found:
        report["message"] = "No SKILL.md found - a skill is a folder with a SKILL.md file in it."
    return report


def _store(lib, s, source, uploaded_by) -> dict:
    sha = _hash(s["files"])
    meta = s["meta"]
    md = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    fm_ver = str(meta.get("version") or md.get("version") or "").strip()
    with lib._lock, lib._db() as c:
        cur = c.execute("SELECT * FROM skills WHERE name=?", (s["name"],)).fetchone()
        same = c.execute("SELECT version FROM skill_versions WHERE name=? AND sha256=?", (s["name"], sha)).fetchone()
        if same:
            return {"name": s["name"], "version": same[0], "result": "unchanged", "warnings": s["warnings"]}
        n = c.execute("SELECT COUNT(*) FROM skill_versions WHERE name=?", (s["name"],)).fetchone()[0]
        taken = fm_ver and c.execute("SELECT 1 FROM skill_versions WHERE name=? AND version=?", (s["name"], fm_ver)).fetchone()
        version = fm_ver if fm_ver and not taken else f"r{n + 1}"
        dest = store_dir(lib) / s["name"] / version
        if dest.exists():
            shutil.rmtree(dest)
        listing = []
        for f in s["files"]:
            p = dest / f["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(f["data"])
            listing.append({"path": f["path"], "size": len(f["data"]), "sha256": hashlib.sha256(f["data"]).hexdigest(),
                            "script": PurePosixPath(f["path"]).suffix.lower() in SCRIPT_EXT})
        scripts = any(x["script"] for x in listing)
        title = str(meta.get("title") or meta.get("name") or s["name"])
        desc = str(meta.get("description") or "").strip()
        lic = str(meta.get("license") or "")
        if not cur:
            c.execute("INSERT INTO skills(name,title,description,latest,status,source,license,about,created,updated)"
                      " VALUES(?,?,?,?,?,?,?,?,?,?)", (s["name"], title, desc, version, "unreviewed", source, lic,
                                                       json.dumps(_guess_about(lib, c, s["name"], desc)), now(), now()))
        elif cur["approved"]:   # agents keep seeing the approved version's name and description until you approve this one
            c.execute("UPDATE skills SET latest=?, updated=? WHERE name=?", (version, now(), s["name"]))
        else:
            c.execute("UPDATE skills SET title=?, description=?, latest=?, source=?, license=?, updated=? WHERE name=?",
                      (title, desc, version, source or cur["source"], lic or cur["license"], now(), s["name"]))
        c.execute("INSERT INTO skill_versions(name,version,sha256,size,files,frontmatter,has_scripts,source,uploaded,"
                  "uploaded_by,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                  (s["name"], version, sha, sum(x["size"] for x in listing), json.dumps(listing),
                   json.dumps(meta, default=str), int(scripts), source, now(), uploaded_by, "; ".join(s["warnings"])))
    return {"name": s["name"], "version": version, "result": "new skill" if not cur else "new version",
            "has_scripts": scripts, "files": len(listing), "warnings": s["warnings"]}


def _guess_about(lib, c, name, desc) -> list[str]:
    """Entries the skill obviously relates to: a project/tool whose name or alias appears in its name or description."""
    text = f" {name.replace('-', ' ')} {desc} ".lower()
    out = []
    for slug, nm, kind in c.execute("SELECT slug, name, kind FROM entities WHERE kind IN"
                                    " ('project','tool','library','llm','service','dataset')"):
        n = nm.lower()
        if len(n) >= 4 and re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", text):
            out.append(slug)
    return out[:8]


# ------------------------------------------------------------------ reading the store
def _row(r) -> dict:
    d = dict(r)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["about"] = json.loads(d.get("about") or "[]")
    return d


def list_skills(lib, q: str = "", include_unreviewed: bool = True, tag: str = "") -> list[dict]:
    with lib._db() as c:
        rows = [_row(r) for r in c.execute("SELECT s.*, (SELECT has_scripts FROM skill_versions v WHERE v.name=s.name"
                                           " AND v.version=IFNULL(NULLIF(s.approved,''), s.latest)) AS has_scripts,"
                                           " (SELECT COUNT(*) FROM skill_versions v WHERE v.name=s.name) AS nversions"
                                           " FROM skills s ORDER BY s.name")]
    if not include_unreviewed:
        rows = [r for r in rows if r["approved"] and r["status"] != "blocked"]
    if tag:
        rows = [r for r in rows if tag.lower() in [t.lower() for t in r["tags"]] or tag in r["about"]]
    if q.strip():
        words = [w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) > 1]
        for r in rows:
            hay = f"{r['name']} {r['title']} {r['description']} {' '.join(r['tags'])} {' '.join(r['about'])}".lower()
            r["score"] = sum((3 if w in r["name"] else 0) + hay.count(w) for w in words)
        rows = sorted((r for r in rows if r["score"]), key=lambda r: -r["score"])
    return rows


def get(lib, name: str, version: str = "") -> dict | None:
    with lib._db() as c:
        s = c.execute("SELECT * FROM skills WHERE name=?", (safe_name(name),)).fetchone()
        if not s:
            return None
        s = _row(s)
        s["versions"] = [dict(r) for r in c.execute(
            "SELECT id, version, sha256, size, has_scripts, source, uploaded, uploaded_by, status, reviewed, notes"
            " FROM skill_versions WHERE name=? ORDER BY id DESC", (s["name"],))]
        v = version or s["approved"] or s["latest"]
        row = c.execute("SELECT * FROM skill_versions WHERE name=? AND version=?", (s["name"], v)).fetchone()
    if not row:
        return None
    s["version"] = dict(row)
    s["version"]["files"] = json.loads(row["files"])
    s["version"]["frontmatter"] = json.loads(row["frontmatter"] or "{}")
    s["dir"] = str(store_dir(lib) / s["name"] / v)
    skill_md = next((f["path"] for f in s["version"]["files"] if f["path"].lower() == "skill.md"), None)
    s["skill_md"] = (Path(s["dir"]) / skill_md).read_text(encoding="utf-8", errors="replace") if skill_md else ""
    return s


def servable(s: dict, version: str = "", allow_unreviewed: bool = False) -> str | None:
    """Which version an agent may have: the approved one, unless the caller explicitly allows unreviewed."""
    if s["status"] == "blocked":
        return None
    if version:
        st = next((v["status"] for v in s["versions"] if v["version"] == version), None)
        return version if st == "approved" or (allow_unreviewed and st and st != "blocked") else None
    return s["approved"] or (s["latest"] if allow_unreviewed else None)


def read_file(lib, name: str, path: str, version: str = "") -> bytes:
    s = get(lib, name, version)
    if not s:
        raise FileNotFoundError(name)
    base = Path(s["dir"]).resolve()
    p = (base / path).resolve()
    if base not in p.parents or not p.is_file():
        raise FileNotFoundError(path)
    return p.read_bytes()


def zip_bytes(lib, name: str, version: str) -> bytes:
    s = get(lib, name, version)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in s["version"]["files"]:
            z.write(Path(s["dir"]) / f["path"], f"{s['name']}/{f['path']}")
    return buf.getvalue()


def count_download(lib, name: str, agent: str = ""):
    with lib._db() as c:
        c.execute("UPDATE skills SET downloads=downloads+1 WHERE name=?", (name,))
        if agent:
            c.execute("INSERT INTO agent_log(name, location, text, created) VALUES(?,?,?,?)",
                      (agent, "skills", f"pulled skill {name}", now()))


# ------------------------------------------------------------------ review + curation
def review(lib, name: str, version: str, status: str, reviewer: str = OWNER, note: str = ""):
    if status not in STATES:
        raise ValueError(status)
    with lib._lock, lib._db() as c:
        if not c.execute("SELECT 1 FROM skill_versions WHERE name=? AND version=?", (name, version)).fetchone():
            raise KeyError(f"{name} {version}")
        c.execute("UPDATE skill_versions SET status=?, reviewed=? WHERE name=? AND version=?",
                  (status, f"{reviewer} {now()}", name, version))
        if status == "approved":
            fm = json.loads(c.execute("SELECT frontmatter FROM skill_versions WHERE name=? AND version=?",
                                      (name, version)).fetchone()[0] or "{}")
            c.execute("UPDATE skills SET approved=?, status='approved', title=COALESCE(?, title),"
                      " description=COALESCE(?, description), updated=? WHERE name=?",
                      (version, str(fm.get("title") or fm.get("name") or "") or None,
                       str(fm.get("description") or "").strip() or None, now(), name))
        elif status == "blocked":
            r = c.execute("SELECT approved FROM skills WHERE name=?", (name,)).fetchone()
            if r and r[0] == version:  # fall back to the newest other approved version
                prev = c.execute("SELECT version FROM skill_versions WHERE name=? AND status='approved' ORDER BY id DESC"
                                 " LIMIT 1", (name,)).fetchone()
                c.execute("UPDATE skills SET approved=?, status=?, updated=? WHERE name=?",
                          (prev[0] if prev else "", "approved" if prev else "unreviewed", now(), name))
        lib.log_review(c, f"skill {name} {version}", "skill review", status, note, reviewer)


def block_skill(lib, name: str, reviewer: str = OWNER):
    with lib._lock, lib._db() as c:
        c.execute("UPDATE skills SET status='blocked', updated=? WHERE name=?", (now(), name))
        lib.log_review(c, f"skill {name}", "skill review", "blocked (all versions)", "", reviewer)


def set_meta(lib, name: str, tags: list[str] | None = None, about: list[str] | None = None):
    with lib._lock, lib._db() as c:
        if tags is not None:
            c.execute("UPDATE skills SET tags=?, updated=? WHERE name=?", (json.dumps(sorted(set(t.strip() for t in tags if t.strip()))), now(), name))
        if about is not None:
            slugs = []
            for a in about:
                if a.strip():
                    try:
                        slugs.append(lib._slug(c, lib._eid(c, a.strip())))
                    except KeyError:
                        pass
            c.execute("UPDATE skills SET about=?, updated=? WHERE name=?", (json.dumps(sorted(set(slugs))), now(), name))


def delete_skill(lib, name: str):
    with lib._lock, lib._db() as c:
        c.execute("DELETE FROM skill_versions WHERE name=?", (name,))
        c.execute("DELETE FROM skills WHERE name=?", (name,))
    shutil.rmtree(store_dir(lib) / name, ignore_errors=True)


def for_entity(lib, slug: str) -> list[dict]:
    return [s for s in list_skills(lib) if slug in s["about"]]


# ------------------------------------------------------------------ OKF concept
def okf_concepts(lib, epath: dict) -> dict:
    """skills/<name>.md concepts (type Skill) for the OKF mirror. -> {path: file dict for okf.Exporter}."""
    import okf

    out = {}
    for s0 in list_skills(lib):
        s = get(lib, s0["name"])
        if not s:
            continue
        v = s["version"]
        path = f"skills/{s['name']}.md"
        about = [a for a in s["about"] if a in epath]
        meta = {"type": "Skill", "title": s["title"], "description": okf.first_sentence(s["description"], 300),
                "resource": f"http://localhost:8090/api/v1/skills/{s['name']}.zip",
                "tags": s["tags"], "status": "deprecated" if s["status"] == "blocked" else "stable",
                "generated": {"by": "kb-skill-store/1", "at": None},
                "verified": ([{"by": okf.actor(v["reviewed"].split(" ", 1)[0]),
                               "at": okf.rfc3339(v["reviewed"].split(" ", 1)[1])}]
                             if v["status"] == "approved" and " " in (v.get("reviewed") or "") else []),
                "x-kb-skill": {"version": v["version"], "approved": s["approved"], "latest": s["latest"],
                               "review": s["status"], "has_scripts": bool(v["has_scripts"]), "sha256": v["sha256"],
                               "source": s["source"], "license": s["license"]}}
        L = [s["description"] or "_No description._", "",
             f"Version {v['version']} ({v['status']})" + (f", approved version {s['approved']}" if s["approved"] and s["approved"] != v["version"] else "")
             + (". **Contains scripts** - review before running." if v["has_scripts"] else "."), ""]
        if about:
            L += ["# Relates to", ""] + [f"* [{okf.mdtext(a)}]({okf.href(path, epath[a])})" for a in about] + [""]
        L += ["# How an agent gets it", "",
              f"* Download: `GET /api/v1/skills/{s['name']}.zip` (the approved version), or the MCP tool "
              f"`kb_get_skill(\"{s['name']}\")`.",
              f"* Install for Claude: unzip into `~/.claude/skills/{s['name']}/` (or the project's `.claude/skills/`).", "",
              "# Files", ""] + [f"* `{f['path']}` ({f['size']} bytes{', script' if f['script'] else ''})" for f in v["files"]] + [""]
        L += ["# SKILL.md", "", "~~~~markdown", s["skill_md"].replace("~~~~", "~~~ ~"), "~~~~", ""]
        out[path] = {"key": f"k:{s['name']}", "meta": meta, "body": "\n".join(L),
                     "substance": json.dumps([v["sha256"], s["status"], s["approved"], s["about"], s["tags"]]),
                     "created": s["created"], "norm": ""}
    return out
