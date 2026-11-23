"""
ui_prompts — the prompt menu (/prompts), one prompt (/prompts/p/<id>), the creators (/creators, /creators/<slug>) and
their JSON API. Laid out like Prompt Lab: a big search, tabs, category chips and cards you can copy from.
"""
from html import escape
from urllib.parse import urlencode

import prompts as pm

COPY_JS = ("<script>document.addEventListener('click',async e=>{const b=e.target.closest('[data-copy]');if(!b)return;"
           "const t=document.getElementById(b.dataset.copy);if(!t)return;try{await navigator.clipboard.writeText(t.textContent);"
           "const o=b.textContent;b.textContent='Copied';b.classList.add('done');setTimeout(()=>{b.textContent=o;b.classList.remove('done')},1400)}"
           "catch(_){const r=document.createRange();r.selectNodeContents(t);getSelection().removeAllRanges();getSelection().addRange(r)}});"
           "addEventListener('keydown',e=>{if(e.key==='/'&&!/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)){const i=document.querySelector('.pl-search input');"
           "if(i){e.preventDefault();e.stopImmediatePropagation();i.focus()}}},true)</script>")


def _q(**kw) -> str:
    kw = {k: v for k, v in kw.items() if v}
    return "?" + urlencode(kw) if kw else ""


def card(p: dict, show_set: bool = False) -> str:
    kind = "img" if p["type"] == "image" else "txt"
    body = p["my_version"] or p["prompt"]
    return (f"<article class=pl-card><div class=pl-tags><span class='pl-tag {kind}'>{escape(p['category'] or p['type'])}</span>"
            + (" <span class='pl-tag mine'>your version</span>" if p["my_version"] else "")
            + ("<span class=pl-star title=Saved>★</span>" if p["saved"] else "") + "</div>"
            f"<h3><a href='/prompts/p/{p['id']}'>{escape(p['title'])}</a></h3>"
            f"<p>{escape(p['description'])}</p>"
            + (f"<div class=pl-from>From <a href='/creators/{p['creator_slug']}#set-{p['set_id']}'>{escape(p['set_title'])}</a></div>" if show_set else "")
            + f"<div class=pl-tool>For {escape(p['tool'] or 'any tool')}</div>"
            f"<pre hidden id=pr{p['id']}>{escape(body)}</pre>"
            f"<div class=pl-acts><button class=pl-btn data-copy=pr{p['id']}>Copy prompt</button>"
            f"<a class='pl-btn ghost' href='/prompts/p/{p['id']}'>View</a></div></article>")


def grid(ps: list[dict], show_set: bool = False) -> str:
    return "<div class=pl-grid>" + "".join(card(p, show_set) for p in ps) + "</div>" if ps else "<p class=pl-empty>Nothing matches.</p>"


def terms_box(terms: str, site: str) -> str:
    if not terms:
        return ""
    link = f" <a href='{escape(site)}' target=_blank rel=noreferrer>Visit the original site ↗</a>" if site else ""
    return f"<p class=pl-credit>{escape(terms)}{link}</p>"


def caution_box(text: str) -> str:
    return f"<div class=pl-warn><strong>⚠ Read before you run</strong>{escape(text)}</div>" if text else ""


def entity_card(lib, slug: str) -> str:
    """On a creator's entry: a door into their prompts."""
    cs = [c for c in pm.creators(lib) if c["slug"] == slug]
    if not cs:
        return ""
    c = cs[0]
    return (f"<div class=card><div class=k>Prompts by {escape(c['name'])}</div>"
            f"<p class=m>{c['prompts']} prompts in {c['sets']} sets, {c['videos']} of them from videos.</p>"
            f"<a href='/creators/{slug}'>Open the creator section →</a> · <a href='/prompts{_q(creator=slug)}'>Search their prompts</a></div>")


def add_routes(r, lib, state, form):
    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, RedirectResponse

    from ui import page

    # ------------------------------------------------------------------ the prompt menu
    @r.get("/prompts", response_class=HTMLResponse)
    def prompt_menu(q: str = "", tab: str = "", category: str = "", creator: str = ""):
        n = pm.counts(lib, creator)
        tabs = [("videos", f"▶ From videos ({n['videos']})"), ("", f"All ({n['n'] - n['videos']})"),
                ("featured", f"★ Featured ({n['featured']})"), ("text", f"Text ({n['text']})"),
                ("image", f"Image ({n['image']})"), ("saved", f"♥ Saved ({n['saved']})")]
        lib_only = tab in ("", "featured", "text", "image") and not q
        ps = pm.find(lib, q=q, creator=creator, category=category, type_=tab if tab in pm.TYPES else "",
                     featured=tab == "featured", saved=tab == "saved", videos=tab == "videos")
        if lib_only:
            ps = [p for p in ps if p["set_kind"] == "library"]
        cs = pm.creators(lib)
        who = next((c for c in cs if c["slug"] == creator), None)
        body = ("<section class=pl-hero><div class=pl-eyebrow>// Prompt menu</div><h1>Prompts</h1>"
                f"<p class=pl-lede>{n['n']} prompts kept for future reference"
                + (f" from {escape(who['name'])}" if who else f" from {len(cs)} creator{'s' if len(cs) != 1 else ''}") + ". "
                "Search, filter by tab or category, copy one, or open it to keep your own edited version.</p>"
                + "".join(f"<a class=pl-chip href='/creators/{c['slug']}'>{escape(c['name'])} · {c['prompts']}</a>" for c in cs)
                + "</section>")
        body += (f"<div class=pl-controls><form class=pl-search action='/prompts' method=get role=search>"
                 f"<span aria-hidden=true>⌕</span><input name=q value='{escape(q)}' placeholder='Search every prompt, including the videos…' "
                 "aria-label='Search prompts'>" + (f"<input type=hidden name=creator value='{escape(creator)}'>" if creator else "")
                 + "<kbd>/</kbd></form><nav class=pl-tabs aria-label='Filter'>"
                 + "".join(f"<a class='{'on' if tab == t else ''} {'yt' if t == 'videos' else ''}' href='/prompts{_q(tab=t, creator=creator, q=q)}'>{escape(lbl)}</a>"
                           for t, lbl in tabs) + "</nav>")
        if tab in ("", "text", "image", "featured") and not q:
            body += "<div class=pl-cats>" + f"<a class='{'on' if not category else ''}' href='/prompts{_q(tab=tab, creator=creator)}'>All</a>" + "".join(
                f"<a class='{'on' if category == c else ''}' href='/prompts{_q(tab=tab, creator=creator, category=c)}'>{escape(c)} <span>{k}</span></a>"
                for c, k in pm.categories(lib, creator)) + "</div>"
        body += "</div>"
        if tab == "videos" and not q:
            for s in pm.sets(lib, creator):
                if s["kind"] != "video":
                    continue
                vps = [p for p in ps if p["set_id"] == s["id"]]
                body += (f"<section class=pl-video><div class=pl-eyebrow>// {escape(s['creator'] or '')} · video</div>"
                         f"<h2><a href='/creators/{s['creator_slug']}#set-{s['id']}'>{escape(s['title'])}</a></h2>"
                         f"<p class=pl-lede>{escape(s['description'])}</p><div class=pl-count>{len(vps)} prompts from this video</div>{grid(vps)}</section>")
        else:
            label = f"{len(ps)} result{'s' if len(ps) != 1 else ''}" + (f" for “{escape(q)}”" if q else "")
            body += f"<div class=pl-count>{label}</div>" + grid(ps, show_set=bool(q) or tab == "saved")
        return page("Prompts", body + COPY_JS, path="/prompts")

    @r.get("/prompts/p/{pid}", response_class=HTMLResponse)
    def prompt_page(pid: int):
        p = pm.get(lib, pid)
        if not p:
            raise HTTPException(404, "No such prompt")
        mine = p["my_version"]
        body = (f"<section class=pl-hero><div class=pl-eyebrow>// {escape(p['category'] or p['type'])} · for {escape(p['tool'] or 'any tool')}</div>"
                f"<h1>{escape(p['title'])}</h1><p class=pl-lede>{escape(p['description'])}</p>"
                f"<p class=pl-meta>By <a href='/library/e/{p['creator_slug']}'>{escape(p['creator'] or '')}</a> · "
                f"from <a href='/creators/{p['creator_slug']}#set-{p['set_id']}'>{escape(p['set_title'])}</a></p>"
                + terms_box(p["terms"], p["source_url"]) + "</section>"
                + (caution_box(p["caution"]) if p["set_kind"] == "video" else "")
                + f"<div class=pl-sheet><div class=pl-sheet-head><b>{'Your version' if mine else 'The prompt'}</b>"
                f"<button class=pl-btn data-copy=full>Copy prompt</button>"
                f"<form method=post action='/prompts/p/{pid}/save' style='display:inline'><button class='pl-btn ghost'>"
                f"{'★ Saved' if p['saved'] else '☆ Save'}</button></form></div>"
                f"<pre id=full class=pl-pre>{escape(mine or p['prompt'])}</pre></div>"
                f"<details class=pl-sheet {'open' if mine else ''}><summary>{'Edit your version' if mine else 'Keep your own edited version'}</summary>"
                f"<form method=post action='/prompts/p/{pid}/mine'><textarea name=text rows=14>{escape(mine or p['prompt'])}</textarea>"
                "<div class=pl-acts><button class=pl-btn>Save my version</button>"
                + (f"<button class='pl-btn ghost' name=reset value=1>Go back to the original</button>" if mine else "")
                + "</div></form>"
                + (f"<h4>The original</h4><pre class=pl-pre>{escape(p['prompt'])}</pre>" if mine else "") + "</details>")
        return page(p["title"], body + COPY_JS, path="/prompts")

    @r.post("/prompts/p/{pid}/save")
    def prompt_save(pid: int):
        p = pm.get(lib, pid)
        if p:
            pm.set_saved(lib, pid, not p["saved"])
        return RedirectResponse(f"/prompts/p/{pid}", 303)

    @r.post("/prompts/p/{pid}/mine")
    async def prompt_mine(pid: int, request: Request):
        f = await form(request)
        pm.set_my_version(lib, pid, "" if f.get("reset") else f.get("text", ""))
        return RedirectResponse(f"/prompts/p/{pid}", 303)

    # ------------------------------------------------------------------ creators
    @r.get("/creators", response_class=HTMLResponse)
    def creators_page():
        cs = pm.creators(lib)
        body = ("<section class=pl-hero><div class=pl-eyebrow>// Creators</div><h1>Creators</h1>"
                "<p class=pl-lede>People whose work you keep in the library: their prompt libraries, the prompts from each video, "
                "and where to find the originals.</p></section><div class=pl-grid>")
        body += "".join(
            f"<article class=pl-card><div class=pl-tags><span class='pl-tag txt'>creator</span></div>"
            f"<h3><a href='/creators/{c['slug']}'>{escape(c['name'])}</a></h3><p>{escape(c['description'] or '')}</p>"
            f"<div class=pl-tool>{c['prompts']} prompts · {c['videos']} videos</div>"
            f"<div class=pl-acts><a class=pl-btn href='/creators/{c['slug']}'>Open</a>"
            f"<a class='pl-btn ghost' href='/prompts{_q(creator=c['slug'])}'>Prompts</a></div></article>" for c in cs)
        body += "</div>" if cs else ("</div><p class=pl-empty>No creators yet. Import a Prompt Lab page with "
                                     "<code>python kb.py import-prompts prompt-lab.html</code>.</p>")
        return page("Creators", body, path="/creators")

    @r.get("/creators/{slug}", response_class=HTMLResponse)
    def creator_page(slug: str):
        c = next((x for x in pm.creators(lib) if x["slug"] == slug), None)
        if not c:
            raise HTTPException(404, "No prompts for this creator")
        ss = pm.sets(lib, slug)
        allp = pm.find(lib, creator=slug)
        first = ss[0] if ss else {}
        n = pm.counts(lib, slug)
        body = (f"<section class=pl-hero><div class=pl-eyebrow>// Creator</div><h1>{escape(c['name'])}</h1>"
                f"<p class=pl-lede>{n['n'] - n['videos']} everyday prompts ({n['text']} text, {n['image']} image), "
                f"plus {n['videos']} prompts from {c['videos']} videos.</p>"
                f"<p class=pl-meta><a href='/library/e/{slug}'>Library entry</a>"
                + (f" · <a href='{escape(c['site'])}' target=_blank rel=noreferrer>{escape(c['site'])} ↗</a>" if c["site"] else "")
                + f" · <a href='/prompts{_q(creator=slug)}'>Search these prompts</a> · imported {escape((c['imported'] or '')[:10])}</p>"
                + terms_box(first.get("terms", ""), c["site"] or "") + "</section>")
        body += "<nav class=pl-toc>" + "".join(f"<a href='#set-{s['id']}'>{'▶ ' if s['kind'] == 'video' else ''}{escape(s['title'])} <span>{s['n']}</span></a>" for s in ss) + "</nav>"
        body += caution_box(first.get("caution", ""))
        for s in ss:
            ps = [p for p in allp if p["set_id"] == s["id"]]
            links = "".join(f"<a class=pl-link href='{escape(l.get('href', ''))}' target=_blank rel=noreferrer><b>{escape(l.get('title', ''))}</b>"
                            + (f"<small>{escape(l.get('sub', ''))}</small>" if l.get("sub") else "") + "</a>" for l in s["links"])
            if s["kind"] == "library":
                shown = [p for p in ps if p["featured"]] or ps[:9]
                body += (f"<section class=pl-video id=set-{s['id']}><div class=pl-eyebrow>// Everyday library</div><h2>{escape(s['title'])}</h2>"
                         f"<p class=pl-lede>{escape(s['description'])} Showing the featured ones; "
                         f"<a href='/prompts{_q(creator=slug)}'>all {len(ps)} are in the prompt menu →</a></p>{grid(shown)}</section>")
            else:
                body += (f"<section class=pl-video id=set-{s['id']}><div class=pl-eyebrow>// YouTube video</div><h2>{escape(s['title'])}</h2>"
                         f"<p class=pl-lede>{escape(s['description'])}</p>"
                         + (f"<div class=pl-links>{links}</div>" if links else "")
                         + (f"<details class=pl-sheet><summary>Before you start &amp; notes</summary><pre class=pl-notes>{escape(s['details'])}</pre></details>" if s["details"] else "")
                         + f"<div class=pl-count>{len(ps)} prompts from this video</div>{grid(ps)}"
                         + (f"<p class=pl-foot>{escape(s['footer'])}</p>" if s["footer"] else "") + "</section>")
        return page(c["name"], body + COPY_JS, path="/creators")

    # ------------------------------------------------------------------ JSON, for agents and the Kingdom
    @r.get("/api/v1/prompts")
    def api_prompts(q: str = "", type: str = "", creator: str = "", category: str = "", limit: int = 50):
        return [{k: p[k] for k in ("id", "title", "category", "type", "tool", "description", "creator", "set_title")}
                | {"url": f"/prompts/p/{p['id']}"} for p in pm.find(lib, q=q, type_=type, creator=creator, category=category, limit=limit)]

    @r.get("/api/v1/prompts/{pid}")
    def api_prompt(pid: int):
        p = pm.get(lib, pid)
        if not p:
            raise HTTPException(404, "No such prompt")
        return p | {"url": f"/prompts/p/{pid}"}

    @r.get("/api/v1/creators")
    def api_creators():
        return pm.creators(lib)
