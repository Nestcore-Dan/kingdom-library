"""
ui_extra — web pages for project articles and the skill store (mounted by ui.create_router).
"""
import json
import os
from html import escape
from urllib.parse import quote

import projects
import skills
from library import OWNER


def project_cards(lib, slug: str) -> str:
    """The structured part of a project's article, shown on its entry page."""
    from ui import _post_btn

    p = projects.get(lib, slug)
    if not p:
        return ""
    i = p["info"]
    st_opts = "".join(f"<option{' selected' if s == i.get('status') else ''}>{s}</option>" for s in projects.STATUSES)
    repo = i.get("repo") or ""
    repo_html = (f"<a href='{escape(repo)}' target=_blank>{escape(repo)}</a>" if repo.startswith("http")
                 else escape(repo) or "<span class=m>not set</span>")
    body = (f"<div class=card id=project><div class=k>Project</div><table>"
            f"<tr><th style='width:160px'>Status</th><td><span class='st {'accepted' if i.get('status') in ('active', 'maintained') else 'unreviewed'}'>"
            f"{escape(i.get('status') or 'active')}</span></td></tr>"
            f"<tr><th>Current version</th><td>{escape(p['version']) or '<span class=m>none yet</span>'}</td></tr>"
            f"<tr><th>Repository</th><td>{repo_html}</td></tr>"
            + (f"<tr><th>Folder</th><td><code>{escape(i['local_path'])}</code></td></tr>" if i.get("local_path") else "")
            + (f"<tr><th>Runs at</th><td><a href='{escape(i['homepage'])}'>{escape(i['homepage'])}</a></td></tr>" if i.get("homepage") else "")
            + (f"<tr><th>Stack</th><td>{escape(i['stack'])}</td></tr>" if i.get("stack") else "")
            + (f"<tr><th>Started</th><td>{escape(i['started'])}</td></tr>" if i.get("started") else "")
            + "</table>")
    if p["components"]:
        body += ("<div style='margin-top:10px'><span class=k>Components</span> " + "".join(
            f"<a class=chip href='/library/e/{c['slug']}'>{escape(c['name'])}"
            + (f" · {escape(c['version'])}" if c.get("version") else "") + "</a>" for c in p["components"]) + "</div>")
    body += (f"<details style='margin-top:10px'><summary>Edit project details</summary>"
             f"<form method=post action='/projects/{slug}/info' style='margin-top:8px'>"
             f"<div class=row><select name=status>{st_opts}</select><input name=version value='{escape(i.get('version') or '')}' placeholder='Current version'></div>"
             f"<div class=row style='margin-top:6px'><input name=repo value='{escape(repo)}' placeholder='Git repository URL'>"
             f"<input name=local_path value='{escape(i.get('local_path') or '')}' placeholder='Folder on this computer'></div>"
             f"<div class=row style='margin-top:6px'><input name=homepage value='{escape(i.get('homepage') or '')}' placeholder='Where it runs (URL)'>"
             f"<input name=started value='{escape(i.get('started') or '')}' placeholder='Started (YYYY-MM-DD)'></div>"
             f"<input name=stack style='margin-top:6px' value='{escape(i.get('stack') or '')}' placeholder='Stack: languages, frameworks, models'>"
             f"<label class=m style='display:block;margin-top:6px'>Building in the Kingdom <select name=office style='width:auto'>"
             + "".join(f"<option value='{pid}'{' selected' if (i.get('office') or '') == pid else ''}>{escape(nm)}</option>"
                       for pid, nm in [("", "(same as the parent project)")] + [(x["id"], x["name"]) for x in __import__("kingdom").PLACES
                                                                                 if x["id"] not in ("library", "office", "postoffice")])
             + "</select></label>"
             f"<div style='margin-top:8px'><button>Save details</button> "
             + "</div></form>" + _post_btn(f"/projects/{slug}/git", "Read versions from git", "s g")
             + "</details></div>")

    import kingdom
    import ui_kingdom

    body += (f"<div class=card id=actions><div class=k>Actions</div><div class=m>What's being done, by whom, and when it counts "
             f"as done. Agents add and move these with kb_add_action / kb_update_action.</div>"
             + ui_kingdom.task_rows(kingdom.tasks(lib, slug), f"/library/e/{slug}#actions")
             + ui_kingdom.task_form(slug, f"/library/e/{slug}#actions") + "</div>")
    rows = "".join(
        f"<tr><td><b>{escape(v['version'])}</b></td><td class=m style='white-space:nowrap'>{escape(v['date'] or '')}</td>"
        f"<td>{escape(v['notes'] or '')}<div class=m>{escape(v['ref'] or '')}{' · by ' + escape(v['by']) if v.get('by') and v['by'] != OWNER else ''}</div></td>"
        f"<td>{_post_btn(f'/projects/{slug}/versions/{v[chr(105) + chr(100)]}/delete', '×', 's g')}</td></tr>" for v in p["versions"])
    body += (f"<div class=card id=versions><div class=k>Version history</div><table>"
             f"<tr><th>Version</th><th>Date</th><th>What changed</th><th></th></tr>{rows or '<tr><td class=m colspan=4>No versions yet.</td></tr>'}</table>"
             f"<form method=post action='/projects/{slug}/versions' class=row style='margin-top:8px'>"
             f"<input name=version placeholder='Version' required style='max-width:110px'><input name=date placeholder='Date (blank = today)' style='max-width:170px'>"
             f"<input name=notes placeholder='What changed'><input name=ref placeholder='Tag / commit' style='max-width:150px'><button>Add</button></form></div>")

    ds = ""
    for d in p["decisions"]:
        cls = {"accepted": "accepted", "proposed": "unreviewed"}.get(d["status"], "superseded")
        parts = "".join(f"<p style='margin:6px 0'><b>{h}.</b> {escape(d[k])}</p>" for h, k in (
            ("Context", "context"), ("Decision", "decision"), ("Alternatives considered", "alternatives"),
            ("Consequences", "consequences")) if d.get(k))
        acts = ""
        if d["status"] == "proposed":
            acts = (_post_btn(f"/projects/{slug}/decisions/{d['number']}/accepted", "Accept", "s")
                    + " " + _post_btn(f"/projects/{slug}/decisions/{d['number']}/rejected", "Reject", "s g"))
        elif d["status"] == "accepted":
            acts = _post_btn(f"/projects/{slug}/decisions/{d['number']}/superseded", "Mark superseded", "s g")
        ds += (f"<tr id='d{d['number']}'><td style='width:70px' class=m>{d['id_label']}</td><td>"
               f"<span class='st {cls}'>{escape(d['status'])}</span> <b>{escape(d['title'])}</b>"
               f"<div class=m>{escape(d['date'] or 'undated')} · {escape(d['by'] or OWNER)}"
               + (f" · superseded by D-{d['superseded_by']:03d}" if d.get("superseded_by") else "") + "</div>"
               + (f"<div style='margin-top:4px'>{acts}</div>" if d["status"] == "proposed" else "")
               + f"<details><summary>Details</summary>{parts}" + ("" if d["status"] == "proposed" else acts) + "</details></td></tr>")
    sup_opts = "<option value=''>Supersedes… (optional)</option>" + "".join(
        f"<option value='{d['number']}'>{d['id_label']} {escape(d['title'][:60])}</option>" for d in p["decisions"] if d["status"] == "accepted")
    body += (f"<div class=card id=decisions><div class=k>Decision log</div><div class=m>What was decided, why, and what else was "
             f"considered. Agents can propose decisions; only you accept them.</div><table>{ds or '<tr><td class=m>No decisions recorded yet.</td></tr>'}</table>"
             f"<details style='margin-top:8px'><summary>Record a decision</summary><form method=post action='/projects/{slug}/decisions' style='margin-top:8px'>"
             f"<input name=title placeholder='Short title, e.g. Use SQLite for the store' required>"
             f"<textarea name=context placeholder='Context: what problem or situation led to this' style='margin-top:6px'></textarea>"
             f"<textarea name=decision placeholder='Decision: what you chose' required style='margin-top:6px'></textarea>"
             f"<textarea name=alternatives placeholder='Alternatives considered' style='margin-top:6px;min-height:50px'></textarea>"
             f"<textarea name=consequences placeholder='Consequences: trade-offs, follow-ups' style='margin-top:6px;min-height:50px'></textarea>"
             f"<div class=row style='margin-top:6px'><input name=date placeholder='Date (blank = today)'><select name=supersedes>{sup_opts}</select>"
             f"<button>Record decision</button></div></form></details></div>")
    return body


def skill_cards(lib, slug: str) -> str:
    sk = skills.for_entity(lib, slug)
    if not sk:
        return ""
    return ("<div class=card><div class=k>Skills</div>" + "".join(
        f"<a class=chip href='/skills/{s['name']}'>{escape(s['title'])}</a>" for s in sk) + "</div>")


def add_routes(r, lib, state, form):
    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, RedirectResponse

    from ui import _post_btn, page

    # ============================================================ projects
    @r.get("/projects", response_class=HTMLResponse)
    def projects_page():
        ps = projects.list_projects(lib)
        top = [p for p in ps if not p["parent_slug"] or p["parent_slug"] not in {x["slug"] for x in ps}]

        def row(p, depth=0):
            out = (f"<tr><td style='padding-left:{8 + 22 * depth}px'><a href='/library/e/{p['slug']}'><b>{escape(p['name'])}</b></a>"
                   f" <span class='st {'accepted' if p['status'] in ('active', 'maintained') else 'unreviewed'}'>{escape(p['status'])}</span>"
                   f"<div class=m>{escape((p['description'] or '')[:180])}</div></td>"
                   f"<td class=m>{escape(p['version'] or '-')}</td>"
                   f"<td class=m><a href='/library/e/{p['slug']}#decisions'>{p['ndecisions']} decision{'' if p['ndecisions'] == 1 else 's'}</a>"
                   + (f" · <b>{p['nproposed']} proposed</b>" if p["nproposed"] else "") + "</td>"
                   f"<td class=m>{'<a href=' + chr(39) + escape(p['repo']) + chr(39) + ' target=_blank>repo</a>' if p['repo'].startswith('http') else (escape(p['repo']) or 'no repo')}</td></tr>")
            for c in [x for x in ps if x["parent_slug"] == p["slug"]]:
                out += row(c, depth + 1)
            return out

        body = ("<div class=card><div class=k>Your projects</div><h1 style='margin:4px 0'>Projects</h1>"
                "<p class=m>Each project has a knowledge article: what it is, where the code lives, version history and the "
                "decisions behind it. Components and anything filed under a project form its sub-library.</p><table>"
                "<tr><th>Project</th><th>Version</th><th>Decisions</th><th>Code</th></tr>"
                + ("".join(row(p) for p in top) or "<tr><td class=m colspan=4>No projects yet.</td></tr>") + "</table></div>"
                "<div class=card><div class=k>New project</div><form method=post action='/projects/new'>"
                "<div class=row><input name=name placeholder='Project name' required><input name=parent placeholder='Part of (another project, optional)'></div>"
                "<textarea name=description placeholder='What it is and what it is for' style='margin-top:6px'></textarea>"
                "<div class=row style='margin-top:6px'><input name=repo placeholder='Git repository URL'><input name=local_path placeholder='Folder on this computer'></div>"
                "<div style='margin-top:8px'><button>Create project</button></div></form></div>")
        return page("Projects", body)

    @r.post("/projects/new")
    async def project_new(request: Request):
        f = await form(request)
        slug = projects.create(lib, f.get("name", "").strip(), f.get("description", ""), f.get("parent", ""),
                               repo=f.get("repo", ""), local_path=f.get("local_path", ""))
        return RedirectResponse(f"/library/e/{slug}", 303)

    @r.post("/projects/{slug}/info")
    async def project_info(slug: str, request: Request):
        f = await form(request)
        projects.update_info(lib, slug, **{k: f.get(k, "") for k in ("status", "repo", "local_path", "homepage", "stack", "version", "started", "office")})
        return RedirectResponse(f"/library/e/{slug}#project", 303)

    @r.post("/projects/{slug}/git")
    def project_git(slug: str):
        res = projects.from_git(lib, slug)
        lib.add_note(slug, f"Git: {res['message']}") if not res["ok"] else None
        return RedirectResponse(f"/library/e/{slug}#versions", 303)

    @r.post("/projects/{slug}/versions")
    async def project_version(slug: str, request: Request):
        f = await form(request)
        if f.get("version", "").strip():
            projects.add_version(lib, slug, f["version"], f.get("date") or None, f.get("ref", ""), f.get("notes", ""))
        return RedirectResponse(f"/library/e/{slug}#versions", 303)

    @r.post("/projects/{slug}/versions/{vid}/delete")
    def project_version_del(slug: str, vid: int):
        projects.delete_version(lib, vid)
        return RedirectResponse(f"/library/e/{slug}#versions", 303)

    @r.post("/projects/{slug}/decisions")
    async def project_decision(slug: str, request: Request):
        f = await form(request)
        try:
            n = projects.add_decision(lib, slug, f.get("title", ""), f.get("decision", ""), f.get("context", ""),
                                      f.get("alternatives", ""), f.get("consequences", ""), OWNER, "accepted",
                                      f.get("date") or None, int(f["supersedes"]) if f.get("supersedes") else None)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        return RedirectResponse(f"/library/e/{slug}#d{n}", 303)

    @r.post("/projects/{slug}/decisions/{n}/{status}")
    def project_decision_status(slug: str, n: int, status: str):
        projects.set_decision_status(lib, slug, n, status)
        return RedirectResponse(f"/library/e/{slug}#d{n}", 303)

    # ============================================================ skill store
    @r.get("/skills", response_class=HTMLResponse)
    def skills_page(q: str = ""):
        rows = skills.list_skills(lib, q)
        trs = "".join(
            f"<tr><td><a href='/skills/{s['name']}'><b>{escape(s['title'])}</b></a>" + (f" <span class=m>{escape(s['name'])}</span>" if s['title'] != s['name'] else "")
            + f"<div class=m>{escape((s['description'] or '')[:220])}</div>"
            + "".join(f"<span class=tag>{escape(t)}</span>" for t in s["tags"]) + "</td>"
            f"<td>{_badge(s)}</td><td class=m>{escape(s['approved'] or '-')} / {escape(s['latest'])}"
            f"<div>{s['nversions']} version{'' if s['nversions'] == 1 else 's'}</div></td><td class=m>{s['downloads']} pull{'' if s['downloads'] == 1 else 's'}"
            + ("<div style='color:#f5b041'>has scripts</div>" if s.get("has_scripts") else "") + "</td></tr>" for s in rows)
        body = ("<div class=card><div class=k>Skill store</div><h1 style='margin:4px 0'>Skills for agents</h1>"
                "<p class=m>Packaged skills (a folder with a SKILL.md) that agents can find and pull through the MCP server or the API. "
                "New skills and new versions arrive unreviewed: agents only get a version after you approve it.</p>"
                f"<form method=get class=row><input name=q value='{escape(q)}' placeholder='Find a skill: pdf, testing, deploy…'><button>Search</button></form>"
                "<table style='margin-top:8px'><tr><th>Skill</th><th>Review</th><th>Approved / latest</th><th>Use</th></tr>"
                + (trs or "<tr><td class=m colspan=4>No skills yet. Add a package below.</td></tr>") + "</table></div>"
                "<div class=card><div class=k>Add skills</div>"
                "<form id=up class=row onsubmit='return upl(event)'>"
                "<input type=file name=file accept='.zip,.skill' required><input name=source placeholder='Where it came from (optional)'>"
                "<button>Upload .zip / .skill</button></form>"
                "<script>async function upl(e){e.preventDefault();const f=e.target,file=f.file.files[0];if(!file)return false;"
                "const r=await fetch('/skills/upload?source='+encodeURIComponent(f.source.value||file.name),{method:'POST',"
                "headers:{'Content-Type':'application/octet-stream'},body:file});location.href='/skills';return false}</script>"
                "<form method=post action='/skills/import' class=row style='margin-top:8px'>"
                "<input name=url placeholder='GitHub repo or folder: https://github.com/owner/repo  ·  …/tree/main/skills/name'>"
                "<button>Import from GitHub</button></form>"
                "<form method=post action='/skills/import' class=row style='margin-top:8px'>"
                "<input name=path placeholder='Folder or .zip on this computer, e.g. C:\\Users\\you\\Downloads\\my-skills'>"
                "<button>Import from this computer</button></form>"
                "<p class=m>Every folder with a SKILL.md becomes a skill, so whole skill packs and plugins work. Uploading a "
                "skill again with changed files adds a new version.</p></div>")
        last = (getattr(state, "skill_report", None) or {})
        if last:
            body += ("<div class=card><div class=k>Last import · " + escape(last.get("source", "")) + "</div>"
                     + (f"<p>{escape(last['message'])}</p>" if last.get("message") else "") + "<table>" + "".join(
                         f"<tr><td><a href='/skills/{x['name']}'>{escape(x['name'])}</a></td><td>{escape(x['result'])} {escape(x['version'])}</td>"
                         f"<td class=m>{escape('; '.join(x.get('warnings') or []))}</td></tr>" for x in last.get("skills", []))
                     + "</table></div>")
        return page("Skill store", body)

    @r.post("/skills/upload")
    async def skills_upload(request: Request, source: str = "upload"):
        data = await request.body()
        if not data:
            raise HTTPException(400, "send a .zip or .skill file as the request body")
        state.skill_report = _run(lambda: skills.add_package(lib, data, source))
        return state.skill_report

    @r.post("/skills/import")
    async def skills_import(request: Request):
        f = await form(request)
        if f.get("url", "").strip():
            def go():
                data, sub = skills.github_zip(f["url"], _gh_token())
                return skills.add_package(lib, data, f["url"].strip(), sub=sub)
        else:
            def go():
                return skills.add_package(lib, f.get("path", "").strip().strip('"'), f.get("path", "").strip())
        state.skill_report = _run(go)
        return RedirectResponse("/skills", 303)

    @r.get("/skills/{name}", response_class=HTMLResponse)
    def skill_page(name: str, version: str = ""):
        import markdown

        from library import KINDS

        s = skills.get(lib, name, version)
        if not s:
            raise HTTPException(404)
        v = s["version"]
        okf_md = s["skill_md"]
        fm, body_md = (__import__("okf").split(okf_md))
        about = "".join(f"<a class=chip href='/library/e/{a}'>{escape(a)}</a>" for a in s["about"])
        vrows = "".join(
            f"<tr><td><a href='/skills/{s['name']}?version={quote(x['version'])}'>{escape(x['version'])}</a>"
            + (" <span class='st accepted'>serving</span>" if x["version"] == s["approved"] else "")
            + f"</td><td><span class='st {'accepted' if x['status'] == 'approved' else 'unreviewed' if x['status'] == 'unreviewed' else 'disputed'}'>{escape(x['status'])}</span></td>"
            f"<td class=m>{escape(x['uploaded'])} · {escape(x['source'] or '')}{' · scripts' if x['has_scripts'] else ''}"
            f"<div>{escape(x['notes'] or '')}</div></td><td>"
            + (_post_btn(f"/skills/{s['name']}/review", "Approve", "s", {"version": x["version"], "status": "approved"}) + " " if x["status"] != "approved" else "")
            + (_post_btn(f"/skills/{s['name']}/review", "Block", "s g", {"version": x["version"], "status": "blocked"}) if x["status"] != "blocked" else "")
            + "</td></tr>" for x in s["versions"])
        files = "".join(f"<tr><td><code>{escape(f_['path'])}</code></td><td class=m>{f_['size']} bytes</td>"
                        f"<td>{'<span style=\"color:#f5b041\">script</span>' if f_['script'] else ''}</td></tr>" for f_ in v["files"])
        warn = ("<p style='color:#f5b041'>This version contains scripts. Read them before approving: an agent that uses the "
                "skill may run them.</p>" if v["has_scripts"] else "")
        body = (f"<div class=card><div class=k>Skill · {escape(s['name'])}</div><h1 style='margin:4px 0'>{escape(s['title'])}</h1>"
                f"<div>{_badge(s)} <span class=m>showing version {escape(v['version'])} ({escape(v['status'])}) · "
                f"{s['downloads']} pulls{' · licence ' + escape(s['license']) if s['license'] else ''}"
                f"{' · from ' + escape(s['source']) if s['source'] else ''}</span></div>"
                f"<p>{escape(s['description'])}</p>{warn}"
                f"<div class=m>Agents: <code>kb_get_skill(\"{escape(s['name'])}\")</code> · "
                f"<a href='/api/v1/skills/{s['name']}.zip'>download approved version</a>"
                + (f" · <a href='/api/v1/skills/{s['name']}.zip?version={quote(v['version'])}&amp;unreviewed=1'>download this version</a>" if v["version"] != s["approved"] else "")
                + "</div>"
                f"<div style='margin-top:10px'><span class=k>Relates to</span> {about or '<span class=m>nothing yet</span>'}</div>"
                f"<form method=post action='/skills/{s['name']}/meta' class=row style='margin-top:8px'>"
                f"<input name=about value='{escape(', '.join(s['about']))}' placeholder='Entries or projects it relates to (comma separated)'>"
                f"<input name=tags value='{escape(', '.join(s['tags']))}' placeholder='Tags'><button>Save</button></form></div>"
                f"<div class=card><div class=k>Versions</div><table>{vrows}</table>"
                + _post_btn(f"/skills/{s['name']}/block", "Block this skill (all versions)", "s g")
                + " " + _post_btn(f"/skills/{s['name']}/delete", "Delete from the store", "s g") + "</div>"
                f"<div class=card><div class=k>Files</div><table>{files}</table></div>"
                f"<div class='card prose'><div class=k>SKILL.md</div>{markdown.markdown(body_md, extensions=['tables', 'fenced_code'])}"
                f"<details><summary>Frontmatter</summary><pre>{escape(fm or '')}</pre></details></div>")
        return page(s["title"], body)

    @r.post("/skills/{name}/review")
    async def skill_review(name: str, request: Request):
        f = await form(request)
        skills.review(lib, name, f.get("version", ""), f.get("status", ""))
        return RedirectResponse(f"/skills/{name}", 303)

    @r.post("/skills/{name}/meta")
    async def skill_meta(name: str, request: Request):
        f = await form(request)
        skills.set_meta(lib, name, [t for t in f.get("tags", "").split(",")], [a for a in f.get("about", "").split(",")])
        return RedirectResponse(f"/skills/{name}", 303)

    @r.post("/skills/{name}/block")
    def skill_block(name: str):
        skills.block_skill(lib, name)
        return RedirectResponse(f"/skills/{name}", 303)

    @r.post("/skills/{name}/delete")
    def skill_delete(name: str):
        skills.delete_skill(lib, name)
        return RedirectResponse("/skills", 303)


def _badge(s) -> str:
    if s["status"] == "blocked":
        return "<span class='st disputed'>blocked</span>"
    if s["approved"]:
        newer = s["latest"] != s["approved"]
        return "<span class='st accepted'>approved</span>" + ("<span class='st unreviewed'>new version to review</span>" if newer else "")
    return "<span class='st unreviewed'>unreviewed</span>"


def _run(fn) -> dict:
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - show the problem on the page
        return {"source": "", "skills": [], "message": f"Import failed: {e}"}


def _gh_token() -> str:
    """Reuse the Hub watcher's GitHub token if it has one (higher rate limits, private repos)."""
    import os
    from pathlib import Path

    t = os.environ.get("GITHUB_TOKEN", "")
    if t:
        return t
    p = (Path(os.environ["KB_HUB_DATA"]) if os.environ.get("KB_HUB_DATA")
         else Path(__file__).resolve().parent.parent / "hubwatch" / "data") / "tokens.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("GITHUB_TOKEN", "")
    except (OSError, ValueError):
        return ""
