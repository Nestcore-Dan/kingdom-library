#!/usr/bin/env python3
"""
kb — the knowledge base service: the centre of the project.

Extensions (the YouTube downloader now; news recaps, dataset watchers and agents later)
send documents to POST /api/v1/ingest. A background worker curates each one with the local
model (tidy pass, tags, timestamps) and files it into the library. People browse it at
http://localhost:8090, scripts use the REST API (/docs), agents use the MCP server.

CLI:
    python kb.py serve [--host 127.0.0.1] [--port 8090]
    python kb.py import <folder> [...]      # file existing ytdl *.analysis.json
    python kb.py rebuild [--retidy]          # re-file every stored source (retidy = run the model again)
    python kb.py tidy                        # model suggests fixes (approve at /library/tidy)
    python kb.py changes [--days 1]          # what's new, as markdown (the seed of a recap)
    python kb.py export [folder]             # Obsidian-style markdown vault
    python kb.py ask "question"              # ask the librarian
    python kb.py import-library <zip|folder> --name "Eve's KB" --namespace ASTEL --owner Eve
    python kb.py review                      # what is waiting for your review

Env: KB_DB (default ./data/library.db) · KB_TOKEN (require a token for API writes)
     KB_OLLAMA_URL / KB_MODEL (see llm.py) · KB_EXTENSIONS ("Name=url;Name=url" for the nav)
"""
import argparse
import datetime as dt
import json
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import library as libmod  # noqa: E402
import llm  # noqa: E402
from library import KNOWLEDGE, PRODUCTS, Library, analysis_to_doc, hms  # noqa: E402

VERSION = "1.5"
DB_PATH = Path(os.environ.get("KB_DB") or HERE / "data" / "library.db")
TOKEN = os.environ.get("KB_TOKEN", "")
MEDIA_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".mp3", ".m4a", ".jpg", ".jpeg", ".png", ".webp", ".srt", ".txt", ".md"}


# --------------------------------------------------------------------------- #
# Worker: curates documents from the inbox, one at a time
# --------------------------------------------------------------------------- #
class Worker:
    def __init__(self, lib: Library):
        self.lib = lib
        self.wake = threading.Event()
        self.current = None
        with lib._db() as c:  # anything interrupted by a restart goes back in the queue
            c.execute("UPDATE inbox SET status='pending' WHERE status='working'")

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            item = self.lib.inbox_next()
            if not item:
                self.wake.wait(5)
                self.wake.clear()
                continue
            self.current = item["title"]
            self.lib.inbox_set(item["id"], "working")
            try:
                doc = json.loads(item["doc"])
                sid = libmod.curate(self.lib, doc, item["extension"], canon=doc.get("canon"),
                                    retidy=not doc.get("canon"))
                s = self.lib.source(sid)
                self.lib.inbox_set(item["id"], "done" if s.get("canon") else "done (not tidied - model offline)",
                                   source_id=sid)
            except Exception as e:  # noqa: BLE001
                self.lib.inbox_set(item["id"], "failed", str(e)[:500])
            finally:
                self.current = None


# --------------------------------------------------------------------------- #
# JSON views shared by the REST API and the MCP server
# --------------------------------------------------------------------------- #
def ent_out(e):
    keep = ("slug", "name", "kind", "description", "relevance", "parent_name", "nsrc", "ninsights", "nnotes")
    out = {k: e.get(k) for k in keep}
    out["tags"] = [t["name"] for t in e.get("tags", [])]
    out["owner"] = e["owner"]["name"] if e.get("owner") else None
    out["scope"] = ("products" if e["kind"] in PRODUCTS else "tool-knowledge" if e.get("owner") else "general-knowledge")
    out["url"] = f"/library/e/{e['slug']}"
    return out


def _ins(i):
    """An insight with its review state (house rules R5/R6)."""
    return {"text": i["text"], "status": i["status"], "confidence": i["confidence"], "basis": i["basis"],
            "label": i["label"], "source": i["title"], "source_id": i["sid"], "src_id": i["src_id"],
            "source_rating": i["reputability"], "t": i["t"]}


def entity_json(lib: Library, ref: str):
    """Full entry by slug, name or alias (None if missing)."""
    e = lib.entity(ref)
    if not e:
        try:
            with lib._db() as c:
                e = lib.entity(lib._slug(c, lib._eid(c, ref)))
        except KeyError:
            return None
    return {
        **{k: e[k] for k in ("slug", "name", "kind", "description", "relevance", "aliases")},
        "tags": [t["name"] for t in e["tags"]],
        "parents": [a["name"] for a in e["ancestors"]],
        "owner": e["owner"]["name"] if e["owner"] else None,
        "children": [c["name"] for c in e["children"]],
        "knowledge": [{"name": x["name"], "kind": x["kind"], "description": x["description"]} for x in e["sub_knowledge"]],
        "principles": [_ins(i) for i in e["insights"] if i["scope"] == "principle"],
        "tips": [_ins(i) for i in e["insights"] if i["scope"] == "tip"],
        "notes": [{"text": n["body"], "created": n["created"]} for n in e["notes"]],
        "resources": [{"title": m["title"], "url": m["url"], "note": m["context"]} for m in e["mentions"] if m["kind"] == "url"],
        "seen_in": [{"source_id": m["sid"], "title": m["title"], "t": m["t"], "context": m["context"],
                     "watch": f"/library/s/{m['sid']}" + (f"?t={int(m['t'])}" if m["t"] is not None else "")}
                    for m in e["mentions"] if m["kind"] != "url"],
        "related": [x["name"] for x in e["related"]],
        "url": f"/library/e/{e['slug']}",
    }


def source_json(lib: Library, sid, segments: bool = True):
    if isinstance(sid, str) and not sid.isdigit():
        sid = lib.source_by_src_id(sid)
    s = lib.source(int(sid)) if sid else None
    if not s:
        return None
    sid = s["id"]
    doc = s["doc"] or {}
    out = {k: s[k] for k in ("id", "src_id", "namespace", "kind", "title", "url", "channel", "published", "summary",
                             "duration", "extension", "reputability", "assessed_by", "status", "sha256", "supersedes")}
    out["assessment"] = json.loads(s["assessment"]) if s.get("assessment") else None
    out["imported"] = doc.get("imported")
    out.update(tags=[t["name"] for t in s["tags"]], overview=doc.get("overview"),
               principles=[i for i in s["insights"] if i["scope"] == "principle"],
               tips=[i for i in s["insights"] if i["scope"] == "tip"],
               entities=[{"name": e["name"], "kind": e["kind"], "relevance": e["relevance"], "first_t": e["first"]}
                         for e in s["entities"]], watch=f"/library/s/{sid}")
    if segments:
        out["segments"] = [{k: g.get(k) for k in ("start", "end", "on_screen", "steps", "verbatim", "claims", "text")}
                           for g in doc.get("segments", [])]
    return out


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
def create_app(lib: Library | None = None, start_worker: bool = True):
    import re
    import zipfile

    from fastapi import Body, FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, JSONResponse

    import ui

    lib = lib or Library(DB_PATH)
    app = FastAPI(title="Knowledge base", version=VERSION,
                  description="The centre of your research tools. Extensions POST documents to /api/v1/ingest; "
                              "bots read via the endpoints below or the MCP server.")
    worker = Worker(lib)
    import okf

    mirror = okf.Mirror(lib)        # live Open Knowledge Format copy of the library (okf.py)
    import kingdom as kingmod

    if start_worker:
        worker.start()
        mirror.start()
        kingmod.CalendarSync(lib).start()
    app.state.lib, app.state.worker, app.state.okf = lib, worker, mirror

    @app.middleware("http")
    async def auth(request: Request, call_next):
        if TOKEN and request.url.path.startswith("/api/v1") and request.method != "GET":
            got = request.headers.get("x-kb-token") or request.headers.get("authorization", "").removeprefix("Bearer ")
            if got != TOKEN:
                return JSONResponse({"detail": "missing or wrong KB token"}, 401)
        return await call_next(request)

    app.state.imports = {}
    app.include_router(ui.create_router(lib, app.state))

    # ---------------------------------------------------------------- virtual library
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

    @app.get("/virtual")
    def virtual():
        # the Reading room is now the State Library inside the Kingdom app
        from fastapi.responses import RedirectResponse

        import ui_kingdom
        return RedirectResponse(ui_kingdom.KINGDOM_URL.rstrip("/") + "/?go=library", 307)

    @app.get("/virtual/old", response_class=HTMLResponse)
    def virtual_old():
        """The library as a 3D building you (and agents) can walk into."""
        return (HERE / "static" / "virtual.html").read_text(encoding="utf-8")

    @app.get("/api/v1/layout")
    def api_layout():
        return lib.layout()

    @app.get("/api/v1/agents")
    def api_agents(minutes: int = 15):
        return {"agents": lib.agents_present(minutes), "log": lib.agent_log(25)}

    @app.post("/api/v1/agents/{name}")
    def api_agent(name: str, body: dict = Body(default={})):
        """Agents announce themselves and where they are, e.g. {"location": "entry:tango",
        "activity": "studying Tango leases"}. Locations: entrance, catalogue, desk, new-arrivals,
        entry:<slug>, shelf:<case id>, source:<id>."""
        lib.agent_update(name, body.get("location"), body.get("activity"), body.get("role"), body.get("color"),
                         present=body.get("present", True))
        return {"ok": True}

    @app.delete("/api/v1/agents/{name}")
    def api_agent_leave(name: str):
        lib.agent_update(name, "entrance", "left the library", present=False)
        return {"ok": True}

    @app.post("/api/v1/ask")
    def api_ask(body: dict = Body(...)):
        """Ask the librarian. {"question": "...", "agent": "R&D bot"} -> answer with cited sources."""
        q = (body.get("question") or "").strip()
        if not q:
            raise HTTPException(422, "question is required")
        who = body.get("agent")
        if who:
            lib.agent_update(who, "desk", f"asking: {q[:80]}")
        ok, msg = llm.ollama_available(llm.DEFAULT_MODEL)
        if not ok:
            raise HTTPException(503, msg)
        res = llm.ask(lib, q)
        if who:
            lib.agent_update(who, "desk", f"got an answer ({res['confidence']} confidence)")
        return res

    # ---------------------------------------------------------------- media (local files of a source)
    @app.get("/media/{sid}/{path:path}")
    def media(sid: int, path: str):
        """Serve the local video and its companion files (frames, transcript) for a source -
        only files next to the source's own file and named after it."""
        s = lib.source(sid)
        if not s or not s.get("local_path"):
            raise HTTPException(404)
        main = libmod.local_file(s["local_path"])
        base = main.parent.resolve()
        target = (base / path).resolve()
        first = Path(path).parts[0] if Path(path).parts else ""
        if (base not in target.parents or not target.is_file() or not first.startswith(main.stem)
                or target.suffix.lower() not in MEDIA_EXTS):
            raise HTTPException(404)
        return FileResponse(target)

    # ---------------------------------------------------------------- API v1
    @app.get("/api/v1/health")
    def health():
        ok, msg = llm.ollama_available(llm.DEFAULT_MODEL)
        return {"ok": True, "version": VERSION, "db": str(DB_PATH), "model": llm.DEFAULT_MODEL, "model_ok": ok,
                "model_msg": msg, "working_on": worker.current,
                "pending": sum(1 for i in lib.inbox(500) if i["status"] == "pending")}

    @app.post("/api/v1/ingest", status_code=202)
    def ingest(doc: dict = Body(..., description="KB document - see README 'Document contract'")):
        src = doc.get("source") or {}
        if not src.get("title") and not src.get("url"):
            raise HTTPException(422, "doc.source needs at least a title or url")
        doc.setdefault("contract", "kb-doc/1")
        iid = lib.inbox_add(doc, doc.get("extension", ""))
        worker.wake.set()
        return {"inbox_id": iid, "status_url": f"/api/v1/inbox/{iid}"}

    @app.get("/inbox/{iid}")
    def inbox_go(iid: int):
        """Extensions link here right after sending: opens the source once it's curated."""
        from fastapi.responses import RedirectResponse

        i = lib.inbox_item(iid)
        return RedirectResponse(f"/library/s/{i['source_id']}" if i and i["source_id"] else "/inbox", 303)

    @app.get("/api/v1/inbox/{iid}")
    def inbox_item(iid: int):
        i = lib.inbox_item(iid)
        if not i:
            raise HTTPException(404)
        if i["source_id"]:
            i["watch_url"] = f"/library/s/{i['source_id']}"
        return i

    @app.get("/api/v1/search")
    def api_search(q: str, limit: int = 20):
        return [{"title": h["title"], "snippet": h["snippet"].replace("\x02", "**").replace("\x03", "**"),
                 "url": h["href"], "t": h.get("t"), "watch": h.get("watch")} for h in lib.search(q, limit)]

    @app.get("/api/v1/entities")
    def api_entities(kind: str | None = None, tag: str | None = None, scope: str | None = None):
        ents = lib.entities([kind] if kind else None, tag=tag)
        out = [ent_out(e) for e in ents]
        return [e for e in out if not scope or e["scope"] == scope]

    @app.get("/api/v1/entities/{ref}")
    def api_entity(ref: str):
        e = entity_json(lib, ref)
        if e is None:
            raise HTTPException(404)
        return e

    @app.post("/api/v1/entities")
    def api_new_entity(body: dict = Body(...)):
        slug = lib.create_entity(body["name"], body.get("kind", "concept"), body.get("description", ""), body.get("parent", ""))
        for t in body.get("tags", []):
            lib.tag_entity(slug, t)
        return {"slug": slug, "url": f"/library/e/{slug}"}

    def _write(ref, fn):
        try:
            with lib._db() as c:
                slug = lib._slug(c, lib._eid(c, ref))
            fn(slug)
            return {"ok": True, "slug": slug}
        except KeyError:
            raise HTTPException(404, f"no entry called {ref!r}")

    @app.post("/api/v1/entities/{ref}/notes")
    def api_note(ref: str, body: dict = Body(...)):
        return _write(ref, lambda s: lib.add_note(s, body["text"]))

    @app.post("/api/v1/entities/{ref}/resources")
    def api_resource(ref: str, body: dict = Body(...)):
        return _write(ref, lambda s: lib.add_resource(s, body["url"], body.get("title", ""), body.get("note", "")))

    @app.post("/api/v1/entities/{ref}/tags")
    def api_tag(ref: str, body: dict = Body(...)):
        return _write(ref, lambda s: lib.tag_entity(s, body["tag"], body.get("on", True)))

    @app.get("/api/v1/sources")
    def api_sources(kind: str | None = None, tag: str | None = None, since: str | None = None, limit: int = 100):
        return [{k: s[k] for k in ("id", "src_id", "namespace", "kind", "title", "url", "channel", "published", "summary",
                                   "created", "extension", "reputability", "status")}
                | {"tags": [t["name"] for t in s["tags"]], "watch": f"/library/s/{s['id']}"}
                for s in lib.sources(kind=kind, tag=tag, since=since, limit=limit)]

    @app.get("/api/v1/sources/{sid}")
    def api_source(sid: str, segments: bool = True):
        """By number or by stable ID (SRC-KB-0042)."""
        out = source_json(lib, sid, segments)
        if out is None:
            raise HTTPException(404)
        return out

    @app.post("/api/v1/sources/engagement")
    def api_source_engagement(body: dict = Body(...)):
        """Viewer attention for a video already in the library: {url (or ref), engagement, sections?}.
        Sent by the YouTube downloader; nothing is re-filed."""
        try:
            sid = lib.set_engagement(body.get("ref") or body.get("url") or "", body.get("engagement") or {}, body.get("sections"))
        except KeyError:
            raise HTTPException(404, "that video isn't in the library") from None
        return {"source_id": sid}

    @app.get("/api/v1/sources/{sid}/engagement")
    def api_source_engagement_get(sid: str):
        """Where viewers paid attention: replay curve, timestamped-comment curve, peaks, chapters, stats."""
        ref = lib.find_source(sid)
        eng = lib.engagement(ref) if ref else None
        if not eng:
            raise HTTPException(404, "no viewer-attention data for that source")
        return eng

    @app.delete("/api/v1/sources")
    def api_source_delete(ref: str, reason: str = ""):
        """Remove a source: ?ref= its number, SRC id or URL. Automatic entries only it mentioned go too."""
        sid = lib.find_source(ref)
        if not sid:
            raise HTTPException(404, f"no source {ref}")
        return lib.delete_source(sid, reason)

    # ---------------------------------------------------------------- house rules, review, libraries, import
    import importer

    imports = {}

    @app.get("/api/v1/rules")
    def api_rules():
        return {"rules": importer.house_rules(lib), "adopted": lib.local_rules()}

    @app.get("/api/v1/review")
    def api_review():
        q = lib.review_queue()
        q["rule_proposals"] = lib.suggestions(kinds=("rule",))
        return q

    @app.post("/api/v1/review/insights/{iid}")
    def api_review_insight(iid: int, body: dict = Body(...)):
        try:
            lib.review_insight(iid, body["status"], body.get("confidence"), body.get("basis"),
                               body.get("change_class", "low-risk addition"), body.get("reviewer", libmod.OWNER))
        except (KeyError, ValueError) as e:
            raise HTTPException(422, str(e))
        return {"ok": True}

    @app.post("/api/v1/review/sources/{sid}")
    def api_review_source(sid: int, body: dict = Body(...)):
        try:
            lib.review_source(sid, body["reputability"], body.get("basis", ""), body.get("reviewer", libmod.OWNER))
        except (KeyError, ValueError) as e:
            raise HTTPException(422, str(e))
        return {"ok": True}

    @app.get("/api/v1/libraries")
    def api_libraries():
        return [{k: l[k] for k in ("namespace", "name", "owner", "kind", "description", "origin", "created",
                                   "nsources", "nunreviewed")} for l in lib.libraries()]

    @app.get("/api/v1/libraries/{ns}")
    def api_library(ns: str):
        l = lib.library(ns)
        if not l:
            raise HTTPException(404)
        return {**l, "import": imports.get(l["namespace"])}

    @app.post("/api/v1/import", status_code=202)
    async def api_import(request: Request, name: str, namespace: str = "", owner: str = "", description: str = "",
                         path: str = ""):
        """Import an external library: send the .zip as the request body, or give ?path= to a .zip or folder
        on this computer. Runs in the background; poll /api/v1/libraries/{namespace}."""
        body = await request.body()
        ns = re.sub(r"[^A-Z0-9]", "", (namespace or name).upper())[:12] or "IMPORT"
        if imports.get(ns, {}).get("status") == "running":
            raise HTTPException(409, f"{ns} is already importing")
        if body:
            keep = DB_PATH.parent / "imports"
            keep.mkdir(parents=True, exist_ok=True)
            src = keep / f"{ns}-{time.strftime('%Y%m%d-%H%M%S')}.zip"   # the original archive is kept as evidence
            src.write_bytes(body)
            if not zipfile.is_zipfile(src):
                src.unlink()
                raise HTTPException(422, "the upload is not a .zip file")
        elif path:
            src = Path(path)
            if not src.exists():
                raise HTTPException(422, f"{path} does not exist on this computer")
        else:
            raise HTTPException(422, "send a .zip as the body, or ?path= to a .zip or folder")
        lib.register_library(ns, name, owner, description, str(src))   # visible right away, before the work starts
        state = imports[ns] = {"status": "running", "progress": "starting", "report": None, "archive": str(src)}

        def go():
            try:
                state["report"] = importer.import_library(lib, src, name, ns, owner, description, str(src),
                                                          lambda m: state.__setitem__("progress", m))
                state["status"] = "done"
            except Exception as e:  # noqa: BLE001
                state.update(status="failed", progress=str(e))

        threading.Thread(target=go, daemon=True).start()
        return {"namespace": ns, "status_url": f"/api/v1/libraries/{ns}", "page": f"/libraries/{ns}"}

    app.state.imports = imports

    @app.get("/api/v1/tags")
    def api_tags(status: str = "active"):
        return [{k: t[k] for k in ("slug", "name", "description", "nent", "nsrc")} for t in lib.tags(status)]

    @app.get("/api/v1/tags/{slug}")
    def api_tag_get(slug: str):
        t = lib.tag(slug)
        if not t:
            raise HTTPException(404)
        return {"name": t["name"], "description": t["description"], "entities": [ent_out(e) for e in t["entities"]],
                "sources": [{"id": s["id"], "title": s["title"], "kind": s["kind"]} for s in t["sources"]],
                "insights": t["insights"]}

    # ---------------------------------------------------------------- projects
    import projects as projmod
    import skills as skillmod

    @app.get("/api/v1/projects")
    def api_projects():
        """Your projects: status, current version, repo, number of decisions."""
        return projmod.list_projects(lib)

    @app.get("/api/v1/projects/{ref}")
    def api_project(ref: str):
        """A project's article: details, components, version history and decision log."""
        p = projmod.get(lib, ref)
        if not p:
            raise HTTPException(404, f"no project {ref}")
        return p

    @app.post("/api/v1/projects")
    def api_project_new(body: dict = Body(...)):
        """{name, description?, parent?, repo?, local_path?, homepage?, stack?, status?, started?}"""
        if not body.get("name"):
            raise HTTPException(400, "name is required")
        slug = projmod.create(lib, body["name"], body.get("description", ""), body.get("parent", ""),
                              **{k: body.get(k) for k in ("repo", "local_path", "homepage", "stack", "status", "started", "version")})
        return projmod.get(lib, slug)

    @app.post("/api/v1/projects/{ref}/info")
    def api_project_info(ref: str, body: dict = Body(...)):
        try:
            projmod.update_info(lib, ref, **body)
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e)) from None
        return projmod.get(lib, ref)

    @app.post("/api/v1/projects/{ref}/versions")
    def api_project_version(ref: str, body: dict = Body(...)):
        """{version, date?, ref?, notes?, by?} - e.g. a tool reporting its own release."""
        try:
            projmod.add_version(lib, ref, body.get("version", ""), body.get("date") or None, body.get("ref", ""),
                                body.get("notes", ""), body.get("by", "agent"))
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e)) from None
        return projmod.get(lib, ref)["versions"][:5]

    @app.post("/api/v1/projects/{ref}/decisions")
    def api_project_decision(ref: str, body: dict = Body(...)):
        """{title, decision, context?, alternatives?, consequences?, by?, status?} - arrives as 'proposed'
        unless status is given; you accept proposed decisions on the project page."""
        try:
            n = projmod.add_decision(lib, ref, body.get("title", ""), body.get("decision", ""), body.get("context", ""),
                                     body.get("alternatives", ""), body.get("consequences", ""), body.get("by", "agent"),
                                     body.get("status", "proposed"), body.get("date") or None, body.get("supersedes"))
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e)) from None
        return {"number": n, "id": projmod.did(ref, n)}

    # ---------------------------------------------------------------- the Kingdom (town map, agents, handoffs, actions, clocks)
    @app.get("/api/v1/kingdom")
    def api_kingdom(visit: bool = False):
        """Everything the town map shows. visit=1 also returns what changed since your previous visit."""
        since = None
        if visit:
            with lib._db() as c:
                r = c.execute("SELECT v FROM meta WHERE k='kingdom_last_visit'").fetchone()
                since = r[0] if r else None
                c.execute("INSERT OR REPLACE INTO meta VALUES('kingdom_last_visit', ?)", (libmod.now(),))
        return kingmod.state(lib, since)

    @app.post("/api/v1/agents/{name}/status")
    def api_agent_status(name: str, body: dict = Body(...)):
        """What an agent is doing: {task, next_update?, office? (studio, business, consulting, casework, home,
        library, postoffice), waiting_on? (a name, or "the owner"), role?, kind? (agent | human)}"""
        office = body.get("office")
        if office and office not in kingmod.PLACE:
            raise HTTPException(400, f"office must be one of {', '.join(kingmod.PLACE)}")
        kingmod.set_status(lib, name, body.get("task"), body.get("next_update"), office, body.get("waiting_on"),
                           body.get("role"), body.get("kind"), body.get("location"))
        return {"ok": True}

    @app.get("/api/v1/handoffs")
    def api_handoffs(all: bool = False, name: str = ""):
        return kingmod.handoffs(lib, not all, name)

    @app.post("/api/v1/handoffs")
    def api_handoff_new(body: dict = Body(...)):
        """A real handoff between agents or people: {from, to, what, owner?, due? (YYYY-MM-DD), project?}"""
        try:
            hid = kingmod.add_handoff(lib, body.get("from", "agent"), body.get("to", libmod.OWNER), body.get("what", ""),
                                      body.get("owner", ""), body.get("due", ""), body.get("project", ""),
                                      body.get("from_place", ""), body.get("to_place", ""))
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        return {"id": hid}

    @app.post("/api/v1/handoffs/{hid}")
    def api_handoff_update(hid: int, body: dict = Body(...)):
        """{status? (open, accepted, done, cancelled), message?, by?}"""
        try:
            kingmod.update_handoff(lib, hid, body.get("status"), body.get("message", ""), body.get("by", "agent"))
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e)) from None
        return {"ok": True}

    @app.get("/api/v1/tasks")
    def api_tasks(project: str = "", open_only: bool = True):
        """Project actions (the town's tickets until a ticketing tool is chosen)."""
        try:
            return kingmod.tasks(lib, project or None, open_only)
        except KeyError:
            raise HTTPException(404, f"no project {project}") from None

    @app.post("/api/v1/projects/{ref}/tasks")
    def api_task_new(ref: str, body: dict = Body(...)):
        """{outcome, owner?, done_when?, due?, source?}"""
        try:
            return {"id": kingmod.add_task(lib, ref, body.get("outcome", ""), body.get("owner", libmod.OWNER),
                                           body.get("done_when", ""), body.get("due", ""), body.get("source", "api"))}
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e)) from None

    @app.post("/api/v1/tasks/{tid}")
    def api_task_update(tid: int, body: dict = Body(...)):
        """{status? (todo, doing, blocked, done, dropped), owner?, outcome?, done_when?}"""
        try:
            kingmod.update_task(lib, tid, body.get("status"), body.get("owner"), body.get("outcome"), body.get("done_when"))
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e)) from None
        return {"ok": True}

    @app.get("/api/v1/calendar")
    def api_calendar(date: str = ""):
        """Both clocks for a day. Personal events show on the work clock only as 'Busy'."""
        return kingmod.day(lib, date or None)

    # ---------------------------------------------------------------- skill store
    @app.get("/api/v1/skills")
    def api_skills(q: str = "", include_unreviewed: bool = False):
        """Find skills. By default only skills with an approved version (what agents may use)."""
        return [{k: s[k] for k in ("name", "title", "description", "approved", "latest", "status", "tags", "about",
                                   "downloads", "has_scripts")} for s in skillmod.list_skills(lib, q, include_unreviewed)]

    @app.get("/api/v1/skills/{name}.zip")
    def api_skill_zip(name: str, version: str = "", unreviewed: bool = False, agent: str = ""):
        from fastapi.responses import Response

        s = skillmod.get(lib, name)
        if not s:
            raise HTTPException(404, f"no skill {name}")
        v = skillmod.servable(s, version, unreviewed)
        if not v:
            raise HTTPException(403, f"{name} has no approved version yet - the owner approves skills on /skills/{name}")
        skillmod.count_download(lib, s["name"], agent)
        return Response(skillmod.zip_bytes(lib, s["name"], v), media_type="application/zip",
                        headers={"Content-Disposition": f"attachment; filename={s['name']}-{v}.zip"})

    @app.get("/api/v1/skills/{name}/files/{path:path}")
    def api_skill_file(name: str, path: str, version: str = "", unreviewed: bool = False):
        from fastapi.responses import Response

        s = skillmod.get(lib, name)
        v = skillmod.servable(s, version, unreviewed) if s else None
        if not v:
            raise HTTPException(404 if not s else 403, "not found or not approved")
        try:
            return Response(skillmod.read_file(lib, s["name"], path, v), media_type="application/octet-stream")
        except FileNotFoundError:
            raise HTTPException(404, path) from None

    @app.get("/api/v1/skills/{name}")
    def api_skill(name: str, version: str = "", unreviewed: bool = False):
        """A skill's SKILL.md and file list (the approved version unless you ask otherwise)."""
        s = skillmod.get(lib, name)
        v = skillmod.servable(s, version, unreviewed) if s else None
        if not s:
            raise HTTPException(404, f"no skill {name}")
        if not v:
            raise HTTPException(403, f"{name} has no approved version yet")
        s = skillmod.get(lib, name, v)
        return {"name": s["name"], "title": s["title"], "description": s["description"], "version": v,
                "approved": s["approved"], "latest": s["latest"], "review": s["version"]["status"],
                "has_scripts": bool(s["version"]["has_scripts"]), "files": s["version"]["files"],
                "skill_md": s["skill_md"], "zip": f"/api/v1/skills/{s['name']}.zip", "about": s["about"]}

    @app.post("/api/v1/skills")
    async def api_skill_upload(request: Request, source: str = "api", by: str = "agent"):
        """Add skills: send a .zip/.skill as the body. Everything arrives unreviewed."""
        data = await request.body()
        if not data:
            raise HTTPException(400, "send the .zip as the request body")
        try:
            return skillmod.add_package(lib, data, source, by)
        except (ValueError, zipfile.BadZipFile) as e:
            raise HTTPException(400, str(e)) from None

    @app.post("/api/v1/skills/import")
    def api_skill_import(body: dict = Body(...)):
        """{url: GitHub repo/tree URL} or {path: folder or .zip on this computer}."""
        import ui_extra

        try:
            if body.get("url"):
                data, sub = skillmod.github_zip(body["url"], ui_extra._gh_token())
                return skillmod.add_package(lib, data, body["url"], body.get("by", "agent"), sub=sub)
            return skillmod.add_package(lib, body.get("path", ""), body.get("path", ""), body.get("by", "agent"))
        except (ValueError, FileNotFoundError, zipfile.BadZipFile) as e:
            raise HTTPException(400, str(e)) from None

    # ---------------------------------------------------------------- Open Knowledge Format
    @app.get("/api/v1/okf")
    def api_okf():
        """Where the live OKF v0.3 bundle is and when it was last brought up to date."""
        return mirror.status()

    @app.post("/api/v1/okf/sync")
    def api_okf_sync():
        return mirror.sync_if_changed(force=True)

    @app.get("/api/v1/okf/validate")
    def api_okf_validate(path: str = ""):
        """Conformance check (ours + Google's validator) of our bundle, or of a folder / .zip on this computer."""
        target = Path(path) if path else mirror.ex.root
        if not target.exists():
            raise HTTPException(404, f"{target} not found")
        return okf.validate(target)

    @app.get("/api/v1/okf/concept")
    def api_okf_concept(path: str):
        """One concept file as Markdown, e.g. path=tools/tango.md"""
        from fastapi.responses import PlainTextResponse

        try:
            return PlainTextResponse(mirror.ex.read(path), media_type="text/markdown")
        except FileNotFoundError:
            raise HTTPException(404, f"no concept {path}") from None

    @app.get("/api/v1/okf/bundle.zip")
    def api_okf_zip():
        from fastapi.responses import Response

        mirror.sync_if_changed()
        return Response(mirror.ex.zip_bytes(), media_type="application/zip",
                        headers={"Content-Disposition": "attachment; filename=kb-okf-bundle.zip"})

    @app.get("/api/v1/changes")
    def api_changes(since: str | None = None, days: float = 1):
        since = since or (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        return lib.changes(since)

    return app


# --------------------------------------------------------------------------- #
# CLI helpers
# --------------------------------------------------------------------------- #
def brief(lib: Library, days: float) -> str:
    """Plain markdown digest of what's new - the starting point for a recap bot."""
    since = (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    ch = lib.changes(since)
    L = [f"# Knowledge brief — last {days:g} day(s)", ""]
    for s in ch["sources"]:
        tags = ", ".join(t["name"] for t in s["tags"])
        L += [f"## {s['title']}", f"*{s['kind']} · {s['channel'] or ''}{' · ' + tags if tags else ''}* — "
              f"http://localhost:8090/library/s/{s['id']}", "", (s["summary"] or "").strip(), ""]
        ins = [i for i in ch["insights"] if i["source_id"] == s["id"]]
        for i in ins[:6]:
            at = f" [{hms(i['t'])}](http://localhost:8090/library/s/{s['id']}?t={int(i['t'])})" if i["t"] is not None else ""
            L.append(f"- {'🧭' if i['scope'] == 'principle' else '🔧'} {i['text']}{at}")
        L.append("")
    if ch["entities"]:
        L += ["## New entries", "", ", ".join(f"{e['name']} ({e['kind']})" for e in ch["entities"]), ""]
    if not ch["sources"] and not ch["entities"]:
        L.append("Nothing new.")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(prog="kb", description="Knowledge base service")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8090)
    im = sub.add_parser("import", help="file existing ytdl *.analysis.json files")
    im.add_argument("folders", nargs="+", type=Path)
    rb = sub.add_parser("rebuild")
    rb.add_argument("--retidy", action="store_true", help="run the tidy pass again on every source (slow)")
    sub.add_parser("tidy")
    ch = sub.add_parser("changes")
    ch.add_argument("--days", type=float, default=1)
    il = sub.add_parser("import-library", help="import an external knowledge base (.zip or folder)")
    il.add_argument("source", type=Path)
    il.add_argument("--name", required=True)
    il.add_argument("--namespace", default="")
    il.add_argument("--owner", default="")
    il.add_argument("--description", default="")
    sub.add_parser("review", help="what is waiting for your review")
    ak = sub.add_parser("ask", help="ask the librarian a question")
    ak.add_argument("question", nargs="+")
    ex = sub.add_parser("export", help="Obsidian-style vault (the OKF bundle is the standard export: kb okf)")
    ex.add_argument("folder", nargs="?", type=Path, default=HERE / "export")
    ip = sub.add_parser("import-prompts", help="add a creator's prompts from a Prompt Lab page (.html, or - for stdin)")
    ip.add_argument("file")
    ip.add_argument("--creator", default="", help="the creator's name (default: read from the page's credit line)")
    ok_ = sub.add_parser("okf", help="Open Knowledge Format: sync the bundle now, or check a bundle")
    ok_.add_argument("action", choices=["sync", "check"])
    ok_.add_argument("path", nargs="?", type=Path, help="sync: where to write (default kb\\okf); check: folder or .zip")
    a = p.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass

    lib = Library(DB_PATH)
    say = lambda m: print(f"   {m}", flush=True)  # noqa: E731
    if a.cmd == "serve":
        import uvicorn

        print(f"Knowledge base on http://{a.host}:{a.port}  (db: {DB_PATH})")
        uvicorn.run(create_app(lib), host=a.host, port=a.port)
    elif a.cmd == "import-prompts":
        import prompts

        text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
        r = prompts.import_prompt_lab(lib, text, a.creator)
        say(f"{r['creator']}: {r['prompts']} prompts in {r['sets']} sets  (/creators/{r['slug']})")
    elif a.cmd == "import":
        files = [f for d in a.folders for f in (sorted(d.rglob("*.analysis.json")) if d.is_dir() else [d])]
        for f in files:
            an = json.loads(f.read_text(encoding="utf-8"))
            stem = f.name[: -len(".analysis.json")]
            video = f.with_name(stem + Path(an.get("video_file", ".mp4")).suffix)
            doc = analysis_to_doc(an, str(video))
            canon = an.get("canon") if (an.get("canon") or {}).get("version", 0) >= llm.CANON_VERSION else None
            print(f"[..] {an['meta']['title'][:70]}", flush=True)
            sid = libmod.curate(lib, doc, "ytdl", canon=canon, retidy=canon is None)
            print(f"[ok] filed as source {sid}" + ("" if lib.source(sid).get("canon") else " (not tidied - model offline)"))
        gone = lib.delete_orphans()  # old auto entries no source mentions any more (your own ones stay)
        print(f"[ok] imported {len(files)} file(s); {gone} leftover empty entries removed")
    elif a.cmd == "rebuild":
        if a.retidy:
            ok, msg = llm.ollama_available(llm.DEFAULT_MODEL)
            if not ok:
                print(f"[x] {msg}", file=sys.stderr)
                return 1
        r = libmod.rebuild(lib, a.retidy, say)
        print(f"[ok] {r['sources']} source(s) re-filed, {r['purged']} old auto entries replaced, "
              f"{r['orphans_removed']} empty entries removed")
    elif a.cmd == "tidy":
        ok, msg = llm.ollama_available(llm.DEFAULT_MODEL)
        if not ok:
            print(f"[x] {msg}", file=sys.stderr)
            return 1
        n = llm.ai_tidy(lib, llm.DEFAULT_MODEL, say)
        print(f"[ok] {n} suggestion(s) - review them at http://localhost:8090/library/tidy")
    elif a.cmd == "changes":
        print(brief(lib, a.days))
    elif a.cmd == "import-library":
        import importer

        r = importer.import_library(lib, a.source, a.name, a.namespace or a.name, a.owner, a.description,
                                    str(a.source), say)
        print(f"[ok] {len(r['files'])} file(s) into namespace {r['namespace']} · checksums {r['checksums']} · "
              f"{r['proposals']} rule proposal(s) · {len(r['skipped'])} skipped")
        for f in r["files"]:
            print(f"   {f.get('src_id') or '-':14} {f['kind']:9} {f['result']:<10} {f['path']}")
        print(f"Review: http://localhost:8090/review?ns={r['namespace']}")
    elif a.cmd == "review":
        q = lib.review_queue()
        print(f"{q['counts']['insights']} insight(s) and {q['counts']['sources']} source rating(s) waiting; "
              f"{len(lib.suggestions(kinds=('rule',)))} rule proposal(s). http://localhost:8090/review")
    elif a.cmd == "ask":
        r = llm.ask(lib, " ".join(a.question))
        print(r["answer"], "\n")
        for s in r["sources"]:
            print(f"  [{s['n']}] {s['title']} - http://localhost:8090{s['link']}")
    elif a.cmd == "okf":
        import okf

        if a.action == "sync":
            r = okf.Exporter(lib, a.path).sync()
            print(f"[ok] {r['concepts']} concepts in {r['dir']} - {r['files_written']} file(s) written, "
                  f"{r['created']} new, {r['updated']} changed, {r['retired']} retired ({r['seconds']}s)")
        else:
            r = okf.validate(a.path or okf.default_dir(lib))
            o = r.get("official") or {}
            print(f"[{'ok' if r['conformant'] else 'x'}] {'conformant' if r['conformant'] else 'NOT conformant'} "
                  f"OKF {r['okf_version'] or '?'} - {r['concepts']} concepts, trust {r['trust_tiers']}, status {r['status']}")
            if isinstance(o.get("error"), int):
                print(f"   Google validator: {o['error']} errors, {o['warning']} warnings, {o['info']} info")
            for f in o.get("findings", [])[:40]:
                print(f"   {f['level']:7} {f['code']} {f['path']}: {f['message']}")
            for x in r["errors"] + r["warnings"]:
                print(f"   {x['path']}: {x['issue']}")
            return 0 if r["conformant"] else 1
    elif a.cmd == "export":
        n = lib.export_markdown(a.folder)
        print(f"[ok] exported {n} entries to {a.folder}")


if __name__ == "__main__":
    sys.exit(main())
