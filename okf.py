"""
okf — the library as an Open Knowledge Format (OKF v0.3) bundle.

https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md

The SQLite database stays the working store (reviews, search, the reading room). This module keeps an
OKF-conformant folder in step with it - a "live mirror" that agents, git and other tools can read directly -
and reads OKF bundles that other people give us.

Bundle layout (paths are concept IDs, so they stay stable; a concept that moves or is merged leaves a
deprecated stub with superseded_by at its old path, as SPEC §5.4 recommends):

    okf/
      index.md                     bundle metadata (okf_version "0.3") + top-level listing
      log.md                       dated history of changes
      AGENTS.md                    how to read this bundle (not a concept: no frontmatter)
      topics/ concepts/ techniques/                  general knowledge
      tools/ libraries/ llms/ datasets/ services/ companies/ people/
      tools/<tool>/<entry>.md      knowledge that belongs to a product, filed under it
      references/SRC-KB-0042.md    one per source (video, dataset, repo, imported file)
      policies/house-rules.md      RULES.md (+ the rules you adopted)

How our data maps onto OKF:
    kind                 -> type (Tool, LLM, Technique, ...; sources are type Reference)
    sources              -> sources[] (id = SRC id, resource = /references/<id>.md) + [^SRC-...] footnotes per claim
    model / extension    -> generated {by: kb-librarian/<model>, at}     (at = last *meaningful* change)
    your reviews         -> verified [{by: human:owner, at}]             (gives the human-reviewed trust tier)
    merged / moved / superseded -> status: deprecated + superseded_by
    reputability rating, confidence, labels, aliases, origin -> x-kb-* extension keys (OKF stores signals, not
                            scores, so our rating travels as a clearly labelled extension)
"""
import io
import json
import os
import posixpath
import re
import threading
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse

OKF_VERSION = "0.3"
PRODUCER = "kb"
FOLDER = {"topic": "topics", "concept": "concepts", "technique": "techniques", "tool": "tools",
          "library": "libraries", "llm": "llms", "dataset": "datasets", "service": "services",
          "company": "companies", "person": "people", "project": "projects"}
TYPE = {k: ("LLM" if k == "llm" else k.title()) for k in FOLDER}
FOLDER_TITLE = {"topics": "Topics", "concepts": "Concepts", "techniques": "Techniques", "tools": "Tools",
                "libraries": "Libraries", "llms": "LLMs", "datasets": "Datasets", "services": "Services",
                "companies": "Companies", "people": "People", "references": "References", "policies": "Policies",
                "projects": "Projects", "skills": "Skills"}
RESERVED = ("index.md", "log.md")
STATE_SQL = """
CREATE TABLE IF NOT EXISTS okf_paths(
  path TEXT PRIMARY KEY, key TEXT, type TEXT, title TEXT, norm TEXT, status TEXT DEFAULT 'live',
  hash TEXT DEFAULT '', generated_at TEXT, first TEXT, last TEXT);
CREATE TABLE IF NOT EXISTS okf_log(id INTEGER PRIMARY KEY, day TEXT, kind TEXT, text TEXT);
"""


# =========================================================================== #
# small helpers
# =========================================================================== #
def default_dir(lib) -> Path:
    if os.environ.get("KB_OKF_DIR"):
        return Path(os.environ["KB_OKF_DIR"])
    d = Path(lib.path).resolve().parent
    return (d.parent if d.name == "data" else d) / "okf"


def rfc3339(ts) -> str | None:
    """Our timestamps ('2026-11-20 07:36:00', local time) -> RFC 3339 with offset."""
    if not ts:
        return None
    s = str(ts).strip()
    if re.fullmatch(r"\d{8}", s):
        s = f"{s[:4]}-{s[4:6]}-{s[6:]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.astimezone()
    return d.isoformat(timespec="seconds")


def parse_ts(v):
    """OKF timestamp -> aware datetime, or None if it can't be read (SPEC §5 timestamp forms)."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    s = str(v).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})", s):
        return None
    try:
        return datetime.fromisoformat(s.replace("z", "+00:00").replace("Z", "+00:00"))
    except ValueError:
        return None


def actor(name: str) -> str:
    """A person in our review records -> an OKF actor (SPEC §7)."""
    import library as libmod

    n = (name or "").strip()
    if not n:
        return ""
    if re.match(r"^[a-z][a-z0-9+.-]*:", n) or "/" in n:
        return n
    if n.lower() == libmod.OWNER.lower():
        return f"human:{libmod.OWNER.lower()}"
    return "agent:" + re.sub(r"[^a-z0-9._-]+", "-", n.lower()).strip("-")


def model_actor() -> str:
    import llm

    return f"kb-librarian/{re.sub(r'[^A-Za-z0-9._-]+', '-', llm.DEFAULT_MODEL)}"


def author_actor(url: str, author: str) -> str:
    a = (author or "").strip()
    if not a:
        return ""
    if re.match(r"^[a-z][a-z0-9+.-]*:", a):
        return re.sub(r"\s+", "-", a)
    host = urlparse(url or "").netloc.lower()
    scheme = ("youtube" if "youtu" in host else "huggingface" if "huggingface" in host
              else "github" if "github" in host else "author")
    return f"{scheme}:{re.sub(r'\s+', '-', a)}"


def first_sentence(s: str, n: int = 240) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    s = m.group(1) if m and len(m.group(1)) >= 20 else s
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def public_url(url: str) -> str:
    return url if url and re.match(r"^https?://", url) else ""


def href(frm: str, to: str) -> str:
    """Relative link from the file `frm` to the file `to` (both bundle paths), percent-encoded (SPEC §6)."""
    rel = posixpath.relpath(to, posixpath.dirname(frm) or ".")
    return quote(rel, safe="/._-~")


def mdtext(s: str) -> str:
    """Text inside link labels / list items: no accidental links, wikilinks or footnotes."""
    return re.sub(r"([\[\]])", r"\\\1", (s or "").replace("\n", " ")).strip()


# ---------------------------------------------------------------- YAML out
_PLAIN = re.compile(r"^[A-Za-z_][A-Za-z0-9 _./+()'-]*$")
_YAML_WORDS = {"y", "n", "yes", "no", "on", "off", "true", "false", "null", "none", "~"}


def scalar(v) -> str:
    """One YAML scalar that reads back as the same string/number in YAML 1.1 and 1.2 parsers."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    s = str(v)
    if _PLAIN.match(s) and s.lower() not in _YAML_WORDS and not s.endswith(" ") and ": " not in s and " #" not in s:
        return s
    return json.dumps(s, ensure_ascii=False)


def flow(v) -> str:
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k}: {flow(x)}" for k, x in v.items() if x not in (None, "", [], {})) + " }"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(flow(x) for x in v) + "]"
    return scalar(v)


def frontmatter(meta: dict) -> str:
    """Deterministic frontmatter (stable diffs). Empty values are left out (SPEC §11.2: same as absent)."""
    out = ["---"]
    for k, v in meta.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list) and v and isinstance(v[0], dict):
            out.append(f"{k}:")
            out += [f"  - {flow(x)}" for x in v]
        else:
            out.append(f"{k}: {flow(v)}")
    out.append("---")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- YAML in
def _yaml():
    try:
        import yaml
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("PyYAML is needed to read OKF bundles: run setup.bat (pip install pyyaml)") from e

    class Loader(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        keys = set()
        for k, _ in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in keys:
                raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", k.start_mark)
            keys.add(key)
        return loader.construct_mapping(node, deep)

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return yaml, Loader


def split(text: str):
    """-> (frontmatter text or None, body). The file must start with a line that is exactly '---' (SPEC §4)."""
    text = text.lstrip("﻿")
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r") == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return None, text  # never closed: not frontmatter


def read_meta(text: str):
    """-> (meta dict | None, body, error | None)."""
    fm, body = split(text)
    if fm is None:
        return None, body, None
    yaml, Loader = _yaml()
    try:
        m = yaml.load(fm, Loader=Loader)  # noqa: S506 - SafeLoader subclass
    except yaml.YAMLError as e:
        return None, body, f"frontmatter does not parse: {str(e).splitlines()[0]}"
    if m is None:
        m = {}
    if not isinstance(m, dict):
        return None, body, "frontmatter is not a YAML mapping"
    return m, body, None


def as_list(v):
    """SPEC §11.2: one item is a list of one; null / '' / [] mean absent."""
    if v in (None, "", []):
        return []
    return v if isinstance(v, list) else [v]


def trust_tier(meta: dict) -> str:
    """SPEC §5.3: only verification events at/after generated.at count."""
    gen = meta.get("generated") if isinstance(meta.get("generated"), dict) else None
    g_at = parse_ts(gen.get("at")) if gen else None
    tier = "unverified"
    for ev in as_list(meta.get("verified")):
        if not isinstance(ev, dict) or not ev.get("by") or not ev.get("at"):
            continue
        at = parse_ts(ev["at"])
        if at is None or (g_at and at < g_at):
            continue
        if str(ev["by"]).startswith("human:"):
            return "human-reviewed"
        tier = "machine-confirmed"
    return tier


def lifecycle(meta: dict, at: datetime | None = None) -> dict:
    status = meta.get("status") or "stable"
    sa = meta.get("stale_after")
    stale = None
    if sa not in (None, ""):
        t = parse_ts(sa)
        stale = "malformed" if t is None else ((at or datetime.now(timezone.utc)) >= t)
    return {"status": str(status), "current": status == "stable", "stale": stale}


# =========================================================================== #
# export: database -> bundle
# =========================================================================== #
class Exporter:
    def __init__(self, lib, root: Path | None = None):
        import library as libmod

        self.lib, self.L = lib, libmod
        self.root = Path(root) if root else default_dir(lib)
        with lib._db() as c:
            c.executescript(STATE_SQL)
        self.lock = threading.Lock()
        self.last = {}

    # ------------------------------------------------------------ paths
    def plan_paths(self):
        """slug -> path, src_id -> path for everything live right now."""
        ents = self.lib.entities()
        kinds = {e["slug"]: e["kind"] for e in ents}
        epath = {}
        for e in ents:
            own = e.get("owner")
            if e["kind"] in self.L.KNOWLEDGE and own and own["slug"] in kinds:
                epath[e["slug"]] = f"{FOLDER[kinds[own['slug']]]}/{own['slug']}/{e['slug']}.md"
            else:
                epath[e["slug"]] = f"{FOLDER.get(e['kind'], 'concepts')}/{e['slug']}.md"
        srcs = [s for s in self.lib.sources(kind=None, limit=100000) if s.get("src_id")]
        spath = {s["src_id"]: f"references/{s['src_id']}.md" for s in srcs}
        return ents, epath, srcs, spath

    # ------------------------------------------------------------ concepts
    def entity_file(self, slug, path, epath, spath):
        e = self.lib.entity(slug)
        L = self.L
        owner_actor = actor(L.OWNER)
        ins = e["insights"]
        cited = list(dict.fromkeys(i["src_id"] for i in ins if i.get("src_id")))
        seen_src = {}
        for m in e["mentions"]:
            if m["kind"] != "url":
                seen_src.setdefault(m["sid"], m)
        with self.lib._db() as c:
            src_ids = {r[0]: r[1] for r in c.execute("SELECT id, src_id FROM sources")}
        mentioned = [src_ids.get(sid) for sid in seen_src if src_ids.get(sid)]
        all_src = list(dict.fromkeys(cited + mentioned))
        sources = []
        for sid_ in all_src:
            title = next((i["title"] for i in ins if i["src_id"] == sid_), None) or next(
                (m["title"] for s_, m in seen_src.items() if src_ids.get(s_) == sid_), "")
            sources.append({"id": sid_, "resource": "/" + spath.get(sid_, f"references/{sid_}.md"), "title": title})
        resources = [m for m in e["mentions"] if m["kind"] == "url"]
        human = e.get("origin") == "manual" or e.get("description_source") == "manual"
        parent = e["ancestors"][-1] if e["ancestors"] else None
        # substance: what counts as a meaningful change (SPEC §5.2) - new sightings do not
        substance = json.dumps([e["name"], e["kind"], e["description"], parent and parent["slug"],
                                sorted((i["scope"], i["text"]) for i in ins), sorted(n["body"] for n in e["notes"])])
        # verified: when every visible insight has been accepted, at the moment the last one was
        verified = []
        if ins and all(i["status"] == "accepted" for i in ins):
            revs = [self._rev(i.get("reviewed"), i) for i in ins]
            revs = [r for r in revs if r]
            if revs:
                by = owner_actor if all(r[0] == owner_actor for r in revs) else revs[-1][0]
                verified.append({"by": by, "at": max(r[1] for r in revs)})
        meta = {
            "type": TYPE.get(e["kind"], "Concept"),
            "title": e["name"],
            "description": first_sentence(e["description"]),
            "resource": public_url(resources[0]["url"]) if e["kind"] in L.PRODUCTS and resources else "",
            "tags": [t["name"] for t in e["tags"]],
            "status": "stable",
            "sources": sources,
            "generated": {"by": owner_actor if human else model_actor(), "at": None},  # filled by sync
            "verified": verified,
            "x-kb-kind": e["kind"],
            "x-kb-slug": e["slug"],
            "x-kb-origin": e.get("origin") or "auto",
            "x-kb-aliases": sorted(a for a in e["aliases"] if a != L.norm(e["name"])),
            "x-kb-parent": "/" + epath[parent["slug"]] if parent and parent["slug"] in epath else "",
            "x-kb-relevance": e.get("relevance") or "",
        }
        B = []
        if e["ancestors"]:
            crumbs = [f"[{mdtext(a['name'])}]({href(path, epath[a['slug']])})" for a in e["ancestors"] if a["slug"] in epath]
            B += [" › ".join(crumbs + [mdtext(e["name"])]), ""]
        B += [e["description"].strip() if e["description"] else "_No description yet._", ""]
        if e["kind"] == "project":
            import projects

            pj = projects.get(self.lib, slug)
            if pj:
                lines, xp, sub = projects.okf_sections(pj)
                B += lines
                meta["x-kb-project"] = xp
                if public_url(pj["info"].get("repo") or ""):
                    meta["resource"] = pj["info"]["repo"]
                substance += sub
        import skills

        sk = [x for x in skills.for_entity(self.lib, slug) if x["status"] != "blocked"]
        if sk:
            B += ["# Skills", ""] + [f"* [{mdtext(x['title'])}]({href(path, 'skills/' + x['name'] + '.md')})"
                                      + (f" - {mdtext(first_sentence(x['description'], 160))}" if x["description"] else "")
                                      for x in sk] + [""]
        if e["sub_knowledge"]:
            B += [f"# {e['name']} knowledge", ""]
            B += [f"{'  ' * (x['depth'] - 1)}* [{mdtext(x['name'])}]({href(path, epath[x['slug']])})"
                  + (f" - {mdtext(first_sentence(x['description'], 160))}" if x["description"] else "")
                  for x in e["sub_knowledge"] if x["slug"] in epath] + [""]
        kids = [k for k in e["children"] if k["slug"] in epath and not (k["kind"] in L.KNOWLEDGE and e["kind"] in L.PRODUCTS)]
        if kids:
            B += ["# Includes", "", ", ".join(f"[{mdtext(k['name'])}]({href(path, epath[k['slug']])})" for k in kids), ""]
        for scope, head in (("principle", "Principles"), ("tip", "Tool-specific tips")):
            xs = [i for i in ins if i["scope"] == scope]
            if xs:
                B += [f"# {head}", ""]
                for i in xs:
                    badge = ", ".join(x for x in [i["status"], f"{i['confidence']} confidence" if i.get("confidence") else "",
                                                  i.get("label") or ""] if x)
                    at = f" [{L.hms(i['t'])}]({L.at_time(i['url'], i['t'])})" if i.get("t") and public_url(i.get("url")) else ""
                    B.append(f"* {mdtext(i['text'])}[^{i['src_id']}] _({badge})_{at}")
                B.append("")
        if e["notes"]:
            B += ["# Internal notes", ""] + [f"* ({n['created'][:10]}, {L.OWNER}) {mdtext(n['body'])}" for n in e["notes"]] + [""]
        if resources:
            B += ["# Resources", ""] + [f"* [{mdtext(m['title'] or m['url'])}]({m['url']})"
                                         + (f" - {mdtext(m['context'])}" if m.get("context") else "") for m in resources
                                         if public_url(m["url"])] + [""]
        vids = [m for m in e["mentions"] if m["kind"] != "url"]
        if vids:
            B += ["# Seen in", ""]
            for sid in dict.fromkeys(m["sid"] for m in vids):
                ms = [m for m in vids if m["sid"] == sid]
                ref = src_ids.get(sid)
                tgt = href(path, spath[ref]) if ref in spath else ""
                B.append(f"* [{mdtext(ms[0]['title'])}]({tgt})" + (f" ({ms[0]['published']})" if ms[0].get("published") else ""))
                B += [f"  * [{L.hms(m['t'])}]({L.at_time(m['url'], m['t'])}) {mdtext(m['context'] or '')}".rstrip()
                      for m in ms if m["t"] is not None and public_url(m["url"])]
            B.append("")
        rel = [r for r in e["related"] if r["slug"] in epath]
        if rel:
            B += ["# Related", "", ", ".join(f"[{mdtext(r['name'])}]({href(path, epath[r['slug']])})" for r in rel), ""]
        if cited:
            B += [f"[^{s['id']}]: [{mdtext(s['title'] or s['id'])}]({href(path, s['resource'][1:])})"
                  for s in sources if s["id"] in cited] + [""]
        return {"key": f"e:{slug}", "meta": meta, "body": "\n".join(B), "substance": substance,
                "created": e["created"], "norm": L.norm(e["name"])}

    def source_file(self, s, path, epath, spath, superseded_by):
        L = self.L
        d = self.lib.source(s["id"])
        url = public_url(d.get("url") or "")
        doc = d.get("doc") or {}
        ov = doc.get("overview") or {}
        imp = doc.get("imported") or {}
        assess = json.loads(d["assessment"]) if d.get("assessment") else {}
        owner_actor = actor(L.OWNER)
        verified = []
        with self.lib._db() as c:
            for r in c.execute("SELECT reviewer, created, decision, target FROM review_log WHERE target=? OR target LIKE ?"
                               " ORDER BY created", (f"{d['src_id']} rating", f"{d['src_id']}: all %")):
                if r[3].endswith(" rating") or r[2] == "accepted":
                    verified.append({"by": actor(r[0]), "at": rfc3339(r[1])})
        if d.get("canon"):
            gen_by = model_actor()
        else:
            ext = (d.get("extension") or "extension").split(":")[0]
            gen_by = f"{re.sub(r'[^A-Za-z0-9._-]+', '-', ext)}/kb-doc-1"
        published = rfc3339(d.get("published"))
        published = published if published and parse_ts(published) else ""
        eng = (doc.get("extra") or {}).get("engagement") or {}
        est = eng.get("stats") or {}
        meta = {
            "type": "Reference",
            "title": d["title"] or d["src_id"],
            "description": first_sentence(d.get("summary") or ov.get("summary") or ""),
            "resource": url,
            "tags": [t["name"] for t in d["tags"]],
            "status": "deprecated" if superseded_by else "stable",
            "superseded_by": "/" + superseded_by if superseded_by else "",
            "sources": [{"id": d["src_id"], "resource": url or f"{d['kind']} (local / private copy)",
                         "title": d["title"], "author": author_actor(d.get("url"), d.get("channel")),
                         "last_modified": published, "usage_count": est.get("views"),
                         # views are lifetime counts: the window runs from publication to when they were read
                         "usage_window": {"from": published, "to": rfc3339(((doc.get("extra") or {}).get("analyzed_at") or "")[:10])}
                         if est.get("views") and published and (doc.get("extra") or {}).get("analyzed_at") else None}],
            "generated": {"by": gen_by, "at": None},
            "verified": verified,
            "x-kb-src-id": d["src_id"],
            "x-kb-kind": d["kind"],
            "x-kb-namespace": d.get("namespace") or L.HOME_NS,
            "x-kb-reputability": {"rating": d.get("reputability") or "Unassessed",
                                  "assessed_by": d.get("assessed_by") or "", "method": assess.get("method", ""),
                                  "basis": first_sentence(assess.get("basis", ""), 300),
                                  "note": "KB house rules R4; a judgement, not an OKF credibility signal"},
            "x-kb-review-status": d.get("status") or "unreviewed",
            "x-kb-engagement": {"signal": eng.get("signal"), "likes": est.get("likes"), "comments": est.get("comments"),
                                "likes_per_1k_views": est.get("likes_per_1k_views"),
                                "peaks": [f"{L.hms(p['start'])}-{L.hms(p['end'])}" for p in eng.get("peaks", [])]}
            if eng and eng.get("signal") not in (None, "none") else None,
            "x-kb-extension": d.get("extension") or "",
            "x-kb-duration": d.get("duration"),
            "x-kb-sha256": d.get("sha256") or "",
            "x-kb-supersedes": d.get("supersedes") or "",
            "x-kb-imported-from": imp.get("original_path", "") and f"{imp.get('library')}:{imp.get('original_path')}",
        }
        B = [d.get("summary") or ov.get("summary") or "_No summary._", ""]
        if eng.get("peaks"):
            B += ["# Where viewers paid attention", "",
                  f"From {eng['signal']} (YouTube's Most Replayed curve and comments that mention a time).", ""]
            B += [f"* [{L.hms(p['start'])}–{L.hms(p['end'])}]({L.at_time(url, p['at'])}) attention {p['score']:.2f}"
                  if url else f"* {L.hms(p['start'])}–{L.hms(p['end'])} attention {p['score']:.2f}" for p in eng["peaks"]]
            B.append("")
        if ov.get("core_method"):
            B += ["# Core method", "", ov["core_method"], ""]
        if ov.get("key_takeaways"):
            B += ["# Key takeaways", ""] + [f"* {mdtext(x)}" for x in ov["key_takeaways"]] + [""]
        if d["insights"]:
            B += ["# Insights", ""]
            for i in d["insights"]:
                at = f"[{L.hms(i['t'])}]({L.at_time(url, i['t'])}) " if url and i.get("t") else ""
                badge = ", ".join(x for x in [i.get("status"), f"{i['confidence']} confidence" if i.get("confidence") else "",
                                              i.get("label") or ""] if x)
                B.append(f"* {at}{mdtext(i['text'])} _({i['scope']}; {badge}; about {mdtext(i['about'])})_")
            B.append("")
        if d["entities"]:
            B += ["# Covers", ""] + [f"* [{mdtext(x['name'])}]({href(path, epath[x['slug']])}) - {x['kind']}"
                                      + (f", {x['relevance']}" if x.get("relevance") else "")
                                      for x in d["entities"] if x["slug"] in epath] + [""]
        B += ["# Our rating", "",
              f"{d.get('reputability') or 'Unassessed'}"
              + (f" (assessed by {d['assessed_by']})" if d.get("assessed_by") else "")
              + ". KB house rules R4 - see the [house rules](" + href(path, "policies/house-rules.md") + ").", ""]
        substance = json.dumps([d["title"], d.get("summary"), ov.get("core_method"), ov.get("key_takeaways"), eng.get("peaks"),
                                sorted((i["scope"], i["text"]) for i in d["insights"]), superseded_by])
        return {"key": f"s:{d['src_id']}", "meta": meta, "body": "\n".join(B), "substance": substance,
                "created": d["created"], "norm": ""}

    def policy_file(self):
        import importer

        text = importer.house_rules(self.lib)
        meta = {"type": "Policy", "title": "House rules",
                "description": "How this library names, files, rates, reviews and imports knowledge.",
                "tags": ["governance"], "status": "stable",
                "generated": {"by": actor(self.L.OWNER), "at": None}}
        return {"key": "p:house-rules", "meta": meta, "body": text, "substance": text, "created": None, "norm": ""}

    def _rev(self, reviewed, i=None):
        """insights.reviewed ('the owner 2026-11-20 07:36:00') -> (actor, rfc3339)."""
        if not reviewed:
            return None
        m = re.match(r"^(.*?)\s+(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2})?)$", reviewed.strip())
        if not m:
            return None
        return actor(m.group(1)), rfc3339(m.group(2))

    # ------------------------------------------------------------ sync
    def fingerprint(self) -> str:
        with self.lib._db() as c:
            row = c.execute(
                "SELECT (SELECT COUNT(*)||'|'||IFNULL(MAX(updated),'')||'|'||TOTAL(parent_id)||'|'||TOTAL(LENGTH(description))"
                "        ||'|'||GROUP_CONCAT(kind||origin, '') FROM entities),"
                " (SELECT COUNT(*)||'|'||IFNULL(MAX(id),0)||'|'||GROUP_CONCAT(IFNULL(reputability,'')||IFNULL(status,''), '')"
                "        ||'|'||TOTAL(LENGTH(doc)) FROM sources),"
                " (SELECT COUNT(*) FROM review_log), (SELECT COUNT(*)||'|'||IFNULL(MAX(id),0) FROM notes),"
                " (SELECT COUNT(*)||'|'||GROUP_CONCAT(status||confidence, '') FROM insights),"
                " (SELECT COUNT(*) FROM entity_tags), (SELECT COUNT(*) FROM source_tags), (SELECT COUNT(*) FROM aliases),"
                " (SELECT COUNT(*) FROM mentions), (SELECT COUNT(*)||GROUP_CONCAT(name||status,'') FROM tags),"
                " (SELECT COUNT(*)||IFNULL(MAX(updated),'') FROM project_info), (SELECT COUNT(*) FROM project_versions),"
                " (SELECT COUNT(*)||IFNULL(MAX(updated),'') FROM project_decisions),"
                " (SELECT COUNT(*)||IFNULL(MAX(updated),'') FROM skills), (SELECT COUNT(*)||GROUP_CONCAT(status,'') FROM skill_versions)").fetchone()
        import hashlib

        rules = Path(__file__).resolve().parent / "RULES.md"
        local = Path(self.lib.path).parent / "RULES.local.md"
        extra = "".join(str(p.stat().st_mtime) for p in (rules, local) if p.exists())
        return hashlib.sha1((json.dumps(list(row)) + extra + str(self.root)).encode()).hexdigest()

    def sync(self, force: bool = False) -> dict:
        import hashlib

        with self.lock:
            t0 = time.time()
            ents, epath, srcs, spath = self.plan_paths()
            # a newer source supersedes an older one (sources.supersedes holds the old SRC id)
            sup = {}
            with self.lib._db() as c:
                for old, new in c.execute("SELECT supersedes, src_id FROM sources WHERE supersedes!=''"):
                    if old in spath and new in spath:
                        sup[old] = spath[new]
            files = {}
            for e in ents:
                files[epath[e["slug"]]] = self.entity_file(e["slug"], epath[e["slug"]], epath, spath)
            for s in srcs:
                files[spath[s["src_id"]]] = self.source_file(s, spath[s["src_id"]], epath, spath, sup.get(s["src_id"]))
            files["policies/house-rules.md"] = self.policy_file()
            import skills

            files.update(skills.okf_concepts(self.lib, epath))

            stamp = self.L.now()
            day = stamp[:10]
            with self.lib._db() as c:
                prev = {r["path"]: dict(r) for r in c.execute("SELECT * FROM okf_paths")}
                first_run = not prev
                logs, written, created, updated, retired = [], 0, 0, 0, 0
                for path, f in files.items():
                    h = hashlib.sha1(f["substance"].encode()).hexdigest()
                    p = prev.get(path)
                    if not p:
                        gen_at = rfc3339(f["created"]) or rfc3339(stamp)
                        c.execute("INSERT INTO okf_paths(path,key,type,title,norm,status,hash,generated_at,first,last)"
                                  " VALUES(?,?,?,?,?,?,?,?,?,?)", (path, f["key"], f["meta"]["type"], f["meta"]["title"],
                                                                 f["norm"], "live", h, gen_at, stamp, stamp))
                        created += 1
                        if not first_run:
                            logs.append(("Creation", f"Added [{mdtext(f['meta']['title'])}]({quote(path)})."))
                    else:
                        gen_at = p["generated_at"]
                        if p["hash"] != h or p["status"] != "live":
                            gen_at = rfc3339(stamp)
                            if p["status"] != "live":
                                logs.append(("Restoration", f"[{mdtext(f['meta']['title'])}]({quote(path)}) is back."))
                            else:
                                updated += 1
                                logs.append(("Update", f"[{mdtext(f['meta']['title'])}]({quote(path)}) changed."))
                        c.execute("UPDATE okf_paths SET key=?, type=?, title=?, norm=?, status='live', hash=?, generated_at=?,"
                                  " last=? WHERE path=?", (f["key"], f["meta"]["type"], f["meta"]["title"], f["norm"], h,
                                                          gen_at, stamp, path))
                    f["meta"]["generated"]["at"] = gen_at
                    text = frontmatter(f["meta"]) + "\n" + f["body"].rstrip() + "\n"
                    written += self._write(path, text)

                # concepts that left: deprecated stub at the old path (links keep working - SPEC §5.4)
                live_keys = {f["key"]: p for p, f in files.items()}
                for path, p in prev.items():
                    if path in files or p["status"] != "live":
                        continue
                    repl = live_keys.get(p["key"])            # moved (re-parented, kind changed)
                    if not repl and p["norm"]:                # merged: its name is now an alias elsewhere
                        r = c.execute("SELECT e.slug FROM aliases a JOIN entities e ON e.id=a.entity_id WHERE a.norm=?",
                                      (p["norm"],)).fetchone()
                        repl = epath.get(r[0]) if r else None
                    why = (f"Moved or merged into [{mdtext(files[repl]['meta']['title'])}]({href(path, repl)})."
                           if repl else f"Removed from the library on {day}.")
                    meta = {"type": p["type"] or "Concept", "title": p["title"], "status": "deprecated",
                            "superseded_by": "/" + repl if repl else "",
                            "generated": {"by": f"{PRODUCER}/okf-mirror", "at": rfc3339(stamp)},
                            "x-kb-retired": day}
                    written += self._write(path, frontmatter(meta) + "\n" + why + "\n")
                    c.execute("UPDATE okf_paths SET status='deprecated', last=? WHERE path=?", (stamp, path))
                    retired += 1
                    logs.append(("Deprecation", f"[{mdtext(p['title'])}]({quote(path)})" + (
                        f" moved or merged into [{mdtext(files[repl]['meta']['title'])}]({quote(repl)})." if repl
                        else f" removed from the library.")))
                if first_run:
                    logs.append(("Initialization", f"Exported {len(files)} concepts from the knowledge base as an "
                                                   f"OKF {OKF_VERSION} bundle."))
                for kind, text in logs:
                    c.execute("INSERT INTO okf_log(day, kind, text) VALUES(?,?,?)", (day, kind, text))
                c.execute("DELETE FROM okf_log WHERE id NOT IN (SELECT id FROM okf_log ORDER BY id DESC LIMIT 3000)")
                state = {r["path"]: dict(r) for r in c.execute("SELECT * FROM okf_paths")}
                log_rows = [dict(r) for r in c.execute("SELECT day, kind, text FROM okf_log ORDER BY id DESC")]

            written += self._indexes(files, state, ents, epath)
            written += self._write("log.md", self._log(log_rows))
            written += self._write("AGENTS.md", frontmatter({"type": "Guide", "title": "How to read this bundle", "description": "For agents and people: layout, IDs, citations, trust and extension keys of this bundle.", "generated": {"by": f"{PRODUCER}/okf-mirror", "at": "2026-11-20T00:00:00Z"}}) + "\n" + AGENTS_MD)
            self.last = {"at": stamp, "seconds": round(time.time() - t0, 2), "concepts": len(files),
                         "deprecated": sum(1 for p in state.values() if p["status"] != "live"),
                         "created": created, "updated": updated, "retired": retired, "files_written": written,
                         "dir": str(self.root)}
            return self.last

    def _write(self, rel: str, text: str) -> int:
        p = self.root / rel
        if p.exists() and p.read_text(encoding="utf-8") == text:
            return 0
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f".{p.name}.tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, p)
        return 1

    def _indexes(self, files, state, ents, epath) -> int:
        """index.md in every directory (SPEC §8) - progressive disclosure for people and agents."""
        dirs = {}
        for path, p in state.items():
            d = posixpath.dirname(path)
            f = files.get(path)
            desc = (f["meta"].get("description") if f else "") or ""
            dirs.setdefault(d, []).append((path, p["title"], desc, p["status"], (f or {}).get("meta", {}).get("type", p["type"])))
        for d in list(dirs):  # make sure every ancestor directory is listed
            while d:
                d = posixpath.dirname(d)
                dirs.setdefault(d, [])
        n = 0
        by_slug = {e["slug"]: e for e in ents}
        for d, items in dirs.items():
            if d == "":
                continue
            sub = sorted(x for x in dirs if x and posixpath.dirname(x) == d)
            live = sorted((x for x in items if x[3] == "live"), key=lambda x: x[1].lower())
            gone = sorted((x for x in items if x[3] != "live"), key=lambda x: x[1].lower())
            name = posixpath.basename(d)
            parent_slug = name if d.count("/") == 1 else None
            head = (f"{by_slug[parent_slug]['name']} knowledge" if parent_slug in by_slug
                    else FOLDER_TITLE.get(name, name.title()))
            L = [f"# {head}", ""]
            if parent_slug in by_slug:
                L += [f"Knowledge that belongs to [{mdtext(by_slug[parent_slug]['name'])}](../{quote(parent_slug)}.md).", ""]
            L += [f"* [{mdtext(t)}]({quote(posixpath.basename(p))})" + (f" - {mdtext(ds)}" if ds else "")
                  for p, t, ds, _, _ in live] or ["_Nothing here yet._"]
            if sub:
                L += ["", "# Filed under these entries", ""]
                for s in sub:
                    sl = posixpath.basename(s)
                    cnt = sum(1 for x in dirs.get(s, []) if x[3] == "live")
                    nm = by_slug[sl]["name"] if sl in by_slug else sl
                    L.append(f"* [{mdtext(nm)} knowledge]({quote(sl)}/) - {cnt} entr{'y' if cnt == 1 else 'ies'}")
            if gone:
                L += ["", "# Retired", ""] + [f"* [{mdtext(t)}]({quote(posixpath.basename(p))}) - deprecated"
                                              for p, t, _, _, _ in gone]
            n += self._write(f"{d}/index.md", "\n".join(L) + "\n")
        # bundle root: keep whatever frontmatter is already there (SPEC §8.1 MUST)
        old = {}
        ip = self.root / "index.md"
        if ip.exists():
            try:
                m, _, _ = read_meta(ip.read_text(encoding="utf-8"))
                old = m or {}
            except RuntimeError:
                old = {}
        meta = {"okf_version": OKF_VERSION,
                "title": old.get("title") or f"{self.L.OWNER}'s reference library",
                "description": old.get("description") or (
                    "Subjects, techniques, tools, LLMs and datasets for software development and AI agents, filed "
                    "from videos, Hugging Face, GitHub and imported libraries. Use it to look up how a tool or "
                    "technique works and where it was demonstrated."),
                **{k: v for k, v in old.items() if k not in ("okf_version", "title", "description")}}
        meta.setdefault("x-kb-producer", f"{PRODUCER}/okf-mirror")
        top = {d: len([x for x in items if x[3] == "live"]) for d, items in dirs.items() if d and "/" not in d}
        sub_counts = {d: sum(len([x for x in items if x[3] == "live"]) for dd, items in dirs.items()
                             if dd == d or dd.startswith(d + "/")) for d in top}
        L = ["# General knowledge", ""]
        L += [f"* [{FOLDER_TITLE[f]}]({f}/) - {sub_counts[f]} entries" for f in ("topics", "concepts", "techniques") if f in top] or ["_None yet._"]
        L += ["", "# Tools and products", ""]
        L += [f"* [{FOLDER_TITLE[f]}]({f}/) - {sub_counts[f]} entries, including the knowledge filed under each"
              for f in ("tools", "libraries", "llms", "datasets", "services", "companies", "people") if f in top] or ["_None yet._"]
        L += ["", "# Your projects", ""]
        L += ([f"* [Projects](projects/) - {sub_counts['projects']} projects with their details, repositories, version "
               "history and decision log"] if "projects" in top else ["_None yet._"])
        L += ["", "# Skills", ""]
        L += ([f"* [Skill store](skills/) - {top['skills']} skills agents can pull"] if "skills" in top else ["_None yet._"])
        L += ["", "# Sources", ""]
        if "references" in top:
            L.append(f"* [References](references/) - {top['references']} sources: videos, datasets, repositories, imported files")
        L += ["", "# Rules", "",
              "* [House rules](policies/house-rules.md) - how this library names, files, rates, reviews and imports knowledge",
              "* [Change log](log.md) - what changed, newest first", ""]
        n += self._write("index.md", frontmatter(meta) + "\n" + "\n".join(L))
        return n

    def _log(self, rows) -> str:
        """SPEC §9: no frontmatter, ## YYYY-MM-DD headings, newest first. Reviews come from the review log."""
        import library as libmod

        events = [(r["day"], 1, f"* **{r['kind']}**: {r['text']}") for r in rows]
        for r in self.lib.review_log(3000):
            events.append((r["created"][:10], 0, f"* **Review**: {mdtext(r['target'])} - {mdtext(r['decision'])}"
                                                   f" ({mdtext(r['reviewer'] or libmod.OWNER)})"))
        days = {}
        for d, _, line in events:
            days.setdefault(d, []).append(line)
        L = ["# Directory Update Log", ""]
        for d in sorted(days, reverse=True)[:365]:
            L += [f"## {d}"] + days[d] + [""]
        return "\n".join(L)

    def zip_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(self.root.rglob("*")):
                rel = p.relative_to(self.root).as_posix()
                if p.is_file() and not any(x.startswith(".") for x in rel.split("/")):
                    z.write(p, f"okf/{rel}")
        return buf.getvalue()

    def read(self, rel: str) -> str:
        p = (self.root / rel.lstrip("/")).resolve()
        if self.root.resolve() not in p.parents or p.suffix != ".md":
            raise FileNotFoundError(rel)
        return p.read_text(encoding="utf-8")


class Mirror:
    """Keeps the bundle in step with the database: checks every few seconds, writes only what changed."""

    def __init__(self, lib, root: Path | None = None, every: float = 15):
        self.ex = Exporter(lib, root)
        self.every, self.fp, self.error, self.wake = every, None, "", threading.Event()
        self.enabled = os.environ.get("KB_OKF", "1") != "0"

    def start(self):
        if self.enabled:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        time.sleep(3)
        while True:
            try:
                self.sync_if_changed()
                self.error = ""
            except Exception as e:  # noqa: BLE001 - keep the mirror alive; the page shows the error
                self.error = f"{e.__class__.__name__}: {e}"
            self.wake.wait(self.every)
            self.wake.clear()

    def sync_if_changed(self, force: bool = False):
        fp = self.ex.fingerprint()
        if force or fp != self.fp:
            r = self.ex.sync()
            self.fp = fp
            return r
        return None

    def status(self) -> dict:
        return {"enabled": self.enabled, "dir": str(self.ex.root), "okf_version": OKF_VERSION,
                "last_sync": self.ex.last, "error": self.error}


# =========================================================================== #
# conformance check (SPEC §11) - for our bundle and for bundles people give us
# =========================================================================== #
LINK_RE = re.compile(r"(?<!\!)\[(?:[^\]\\]|\\.)*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
WIKI_RE = re.compile(r"\[\[[^\]]+\]\]")
TS_KEYS = ("stale_after",)


def bundle_files(src) -> list[dict]:
    """A folder or zip -> [{path, data}] (dot files, symlinks out of the bundle and non-text skipped)."""
    if isinstance(src, (list, tuple)):
        return list(src)
    files = []
    if isinstance(src, (bytes, bytearray)) or str(src).lower().endswith(".zip"):
        z = zipfile.ZipFile(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
        for i in z.infolist():
            p = PurePosixPath(i.filename)
            if not i.is_dir() and not p.is_absolute() and ".." not in p.parts:
                files.append({"path": str(p), "data": z.read(i)})
        tops = {f["path"].split("/")[0] for f in files}
        if len(tops) == 1 and all("/" in f["path"] for f in files):
            for f in files:
                f["path"] = f["path"].split("/", 1)[1]
    else:
        root = Path(src).resolve()
        for f in sorted(root.rglob("*")):
            if f.is_file() and root in f.resolve().parents:
                files.append({"path": f.relative_to(root).as_posix(), "data": f.read_bytes()})
    return [f for f in files if not any(x.startswith(".") for x in f["path"].split("/"))]


def is_bundle(files) -> bool:
    mds = [f for f in files if f["path"].lower().endswith(".md")]
    for f in mds:
        if f["path"] == "index.md":
            fm, _ = split(f["data"].decode("utf-8", "replace"))
            if fm and re.search(r"(?m)^okf_version\s*:", fm):
                return True
    typed = sum(1 for f in mds if PurePosixPath(f["path"]).name not in RESERVED
                and re.match(r"\A﻿?---\r?\n(?:.*\n)*?type\s*:\s*\S", f["data"].decode("utf-8", "replace")))
    return len(mds) >= 3 and typed >= 0.6 * len(mds)


def official_check(root: Path, limit: int = 300) -> dict | None:
    """Google's own validator (vendor/okf_validate.py, Apache-2.0, from the OKF repo's okf-generate skill)."""
    import importlib.util
    from dataclasses import asdict

    vp = Path(__file__).resolve().parent / "vendor" / "okf_validate.py"
    if not vp.exists():
        return None
    spec = importlib.util.spec_from_file_location("okf_validate", vp)
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["okf_validate"] = mod   # dataclasses look their module up here
    spec.loader.exec_module(mod)
    ch = mod.Checker(Path(root).resolve(), datetime.now(timezone.utc))
    ch.run()
    fs = [asdict(f) for f in ch.findings]
    count = {lv: sum(f["level"] == lv for f in fs) for lv in ("error", "warning", "info")}
    return {"files_checked": ch.files_checked, **count, "findings": fs[:limit]}


def validate(src, limit: int = 300) -> dict:
    """Our checks (trust tiers, lifecycle, links) + Google's official validator. src: folder, .zip, bytes or files."""
    import tempfile

    rep = _validate(src, limit)
    try:
        if isinstance(src, (str, Path)) and Path(src).is_dir():
            off = official_check(Path(src), limit)
        else:
            with tempfile.TemporaryDirectory() as td:
                for f in bundle_files(src):
                    p = Path(td) / f["path"]
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(f["data"])
                off = official_check(Path(td), limit)
    except Exception as e:  # noqa: BLE001
        off = {"error": f"official validator failed: {e}"}
    rep["official"] = off
    if off and isinstance(off.get("error"), int) and off["error"]:
        rep["conformant"] = False
    return rep


def _validate(src, limit: int = 300) -> dict:
    files = bundle_files(src)
    paths = {f["path"] for f in files}
    errors, warnings, notes = [], [], []
    concepts, types, tiers, statuses = {}, {}, {}, {}
    stale = broken = 0
    version = None

    def add(lst, path, msg):
        if len(lst) < limit:
            lst.append({"path": path, "issue": msg})

    for f in files:
        path = f["path"]
        if not path.lower().endswith(".md"):
            continue
        try:
            text = f["data"].decode("utf-8")
        except UnicodeDecodeError:
            add(errors, path, "not UTF-8")
            continue
        name = PurePosixPath(path).name
        fm, body = split(text)
        meta, _, err = read_meta(text)
        if err:
            add(errors, path, err)
            continue
        if name == "index.md":
            if posixpath.dirname(path) and fm is not None:
                add(errors, path, "an index.md below the bundle root must not have frontmatter (§8)")
            if path == "index.md" and meta is not None:
                version = meta.get("okf_version")
                if version is not None and not isinstance(version, str):
                    add(warnings, path, "okf_version should be a quoted string, e.g. \"0.3\" (§4)")
            continue
        if name == "log.md":
            if fm is not None:
                add(errors, path, "log.md must not have frontmatter (§9)")
            for h in re.findall(r"(?m)^##\s+(.+?)\s*$", body):
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", h):
                    add(errors, path, f"log heading '{h}' is not YYYY-MM-DD (§9)")
            continue
        if meta is None or not meta.get("type"):
            add(notes, path, "no frontmatter `type` - not a concept, skipped (§3.2)")
            continue
        if not isinstance(meta["type"], str):
            add(warnings, path, "`type` should be a string")
        concepts[path] = meta
        types[str(meta["type"])] = types.get(str(meta["type"]), 0) + 1
        gen = meta.get("generated")
        if gen not in (None, "", {}) and (not isinstance(gen, dict) or not gen.get("by")):
            add(warnings, path, "`generated` has no `by` (§5.2)")
        if isinstance(gen, dict) and gen.get("at") not in (None, "") and parse_ts(gen.get("at")) is None:
            add(warnings, path, f"generated.at '{gen.get('at')}' is not an RFC 3339 timestamp (§5)")
        for ev in as_list(meta.get("verified")):
            if not isinstance(ev, dict) or not ev.get("by") or not ev.get("at"):
                add(warnings, path, "a `verified` event without both `by` and `at` is ignored (§5.2)")
            elif parse_ts(ev["at"]) is None:
                add(warnings, path, f"verified.at '{ev['at']}' is not an RFC 3339 timestamp")
        for s in as_list(meta.get("sources")):
            if not isinstance(s, dict) or not s.get("resource"):
                add(warnings, path, "a `sources` entry without `resource` is ignored (§5.1)")
            elif s.get("last_modified") not in (None, "") and parse_ts(s["last_modified"]) is None:
                add(warnings, path, f"sources[].last_modified '{s['last_modified']}' is not a timestamp")
        lc = lifecycle(meta)
        statuses[lc["status"]] = statuses.get(lc["status"], 0) + 1
        if lc["status"] not in ("draft", "stable", "deprecated"):
            add(warnings, path, f"status '{lc['status']}' is not draft/stable/deprecated - treated as not current (§5.4)")
        if lc["stale"] == "malformed":
            add(warnings, path, f"stale_after '{meta.get('stale_after')}' cannot be read - treated as stale (§5.5)")
        elif lc["stale"]:
            stale += 1
        sb = meta.get("superseded_by")
        if sb not in (None, ""):
            if lc["status"] != "deprecated":
                add(warnings, path, "superseded_by only has a meaning with status: deprecated (§5.4)")
            tgt = _resolve(path, str(sb))
            if tgt and tgt not in paths:
                add(warnings, path, f"superseded_by '{sb}' is not in the bundle")
        tiers[trust_tier(meta)] = tiers.get(trust_tier(meta), 0) + 1
        body = re.sub(r"(?ms)^(```|~~~).*?^\1", "", body)   # code is not prose: no links in it
        body = re.sub(r"`[^`\n]*`", "", body)
        if WIKI_RE.search(body):
            add(warnings, path, "[[wikilinks]] are not links in OKF - use [text](path.md) (§6.1)")
        for tgt in LINK_RE.findall(body):
            r = _resolve(path, tgt)
            if r is None:
                continue
            if r == "..":
                add(warnings, path, f"link '{tgt}' points outside the bundle")
            elif r not in paths and r.rstrip("/") + "/index.md" not in paths and not any(p.startswith(r.rstrip("/") + "/") for p in paths):
                broken += 1
                add(notes, path, f"link to '{tgt}' has no target yet (allowed - §6.1)")
    if version is None:
        add(notes, "index.md", "no bundle-root index.md with okf_version (recommended - §8.1)")
    return {"conformant": not errors, "okf_version": version, "files": len(files), "concepts": len(concepts),
            "types": dict(sorted(types.items(), key=lambda x: -x[1])), "trust_tiers": tiers, "status": statuses,
            "stale": stale, "broken_links": broken, "errors": errors, "warnings": warnings, "notes": notes[:limit]}


def _resolve(frm: str, target: str):
    """SPEC §6 resolution -> bundle path, None for external URLs/anchors, '..' for outside the bundle."""
    from urllib.parse import unquote

    t = target.split("#", 1)[0]
    if not t or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", t):
        return None
    t = unquote(t)
    p = posixpath.normpath(t.lstrip("/") if t.startswith("/") else posixpath.join(posixpath.dirname(frm), t))
    if p == ".." or p.startswith("../"):
        return ".."
    return "" if p == "." else p


# =========================================================================== #
# import: someone's OKF bundle -> our library (via importer.import_library, house rules R7)
# =========================================================================== #
KIND_GUESS = [(r"\bllm\b|language model|\bmodel\b", "llm"), (r"dataset|table|corpus", "dataset"),
              (r"librar|package|sdk|framework", "library"), (r"service|api|endpoint|platform", "service"),
              (r"tool|app|cli|repo", "tool"), (r"company|organi[sz]ation|vendor", "company"),
              (r"person|people|author", "person"), (r"technique|method|playbook|pattern|procedure|recipe", "technique"),
              (r"topic|area|domain", "topic")]


def kind_for(okf_type: str) -> str:
    t = (okf_type or "").strip().lower()
    for k, v in TYPE.items():
        if t == v.lower():
            return k
    for pat, k in KIND_GUESS:
        if re.search(pat, t):
            return k
    return "concept"


def concept_doc(path: str, text: str, ns: str, owner: str, sha: str, check: str):
    """One OKF concept -> a kb-doc/1 document, or None if the file is not a concept. Their trust, lifecycle and
    sources are kept as imported history (R7) - their 'human-reviewed' is not our review."""
    meta, body, err = read_meta(text)
    if err or not meta or not meta.get("type") or PurePosixPath(path).name in RESERVED:
        return None
    import importer

    title = str(meta.get("title") or PurePosixPath(path).stem.replace("-", " ").replace("_", " "))[:200]
    res = str(meta.get("resource") or "")
    gen = meta.get("generated") if isinstance(meta.get("generated"), dict) else {}
    lc = lifecycle(meta)
    okf_type = str(meta["type"])
    is_ref = okf_type.lower() in ("reference", "source", "document", "article", "paper")
    desc = str(meta.get("description") or "") or importer.first_paragraph(body)
    segs = importer.sections(body)
    if segs and not is_ref:
        segs[0]["entities"] = [{"name": title, "kind": kind_for(okf_type)}]
    hist = {"okf_type": okf_type, "okf_path": path, "tags": [str(x) for x in as_list(meta.get("tags"))],
            "status": lc["status"], "stale": lc["stale"], "trust_tier": trust_tier(meta),
            "generated": _plain(gen), "verified": _plain(as_list(meta.get("verified"))),
            "sources": _plain(as_list(meta.get("sources")))[:50],
            "superseded_by": str(meta.get("superseded_by") or ""),
            "extensions": _plain({k: v for k, v in meta.items() if str(k).startswith("x-")})}
    return {
        "contract": "kb-doc/1", "extension": f"import:{ns}",
        "source": {"kind": "okf", "title": title,
                   "url": res if re.match(r"^https?://", res) else f"okf://{ns}/{path}",
                   "author": str(gen.get("by") or owner or ""), "namespace": ns,
                   "published": str(gen.get("at") or "")[:10], "summary": desc[:500], "sha256": sha},
        "overview": {"summary": desc[:500]},
        "segments": segs,
        "imported": {"library": ns, "original_path": path, "metadata": hist, "checksum": check,
                     "note": "Imported OKF concept; its trust tier, status and sources are the producer's history, "
                             "not our review (R7)."},
        "no_tidy": lc["status"] == "deprecated",
    }


def _plain(v):
    return json.loads(json.dumps(v, default=str))


AGENTS_MD = """# Reading this bundle

This folder is an [Open Knowledge Format](https://github.com/open-knowledge-format/open-knowledge-format) v0.3
bundle, kept in step with the knowledge base automatically. Don't edit it by hand - change things in the
knowledge base (web UI, REST API or MCP tools) and the mirror rewrites the files within a few seconds.

* Start at [index.md](index.md), then each folder's `index.md`. Every concept is one Markdown file with YAML
  frontmatter; its path (without `.md`) is its ID.
* `type` says what it is (Tool, LLM, Technique, Reference, ...). Knowledge that belongs to a product is filed
  under it, e.g. `tools/<tool>/<entry>.md`.
* Claims cite sources with footnotes such as `[^SRC-KB-0042]`; the label is the `id` of an entry in the
  concept's `sources`, which points at `references/SRC-KB-0042.md`.
* Trust: `generated` says who wrote the content, `verified` who confirmed it. Only a `human:` verification at
  or after `generated.at` makes a concept human-reviewed. Most content is machine-written and unverified.
* `status: deprecated` with `superseded_by` means the concept moved or was merged - follow the link.
* Keys starting with `x-kb-` are this library's own: `x-kb-reputability` is the owner's rating of a source
  (house rules R4), which OKF itself does not store.
"""
