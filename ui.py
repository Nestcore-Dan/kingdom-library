"""
ui — the knowledge base's web pages (server-rendered; a little JS only on the watch page).
"""
import json
import os
import threading
from html import escape
from pathlib import Path
from urllib.parse import parse_qs, quote

from library import CONFIDENCE, INSIGHT_STATES, KINDS, KNOWLEDGE, PRODUCTS, RATINGS, Library, at_time, hms, slugify

EXTENSIONS = [  # shown in the nav; add future tools here (or via KB_EXTENSIONS="Name=url;Name=url")
    (n.split("=", 1)[0], n.split("=", 1)[1])
    for n in (os.environ.get("KB_EXTENSIONS") or "YouTube downloader=http://localhost:8080").split(";") if "=" in n
]

CSS = """
:root{--bg:#0f1115;--card:#181b22;--line:#2a2f3a;--fg:#e8eaf0;--mut:#8b92a3;--acc:#ff4d4d;--ok:#3ecf8e;--tag:#7aa2ff}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
main{max-width:1100px;margin:28px auto;padding:0 20px}a{color:var(--ok);text-decoration:none}a:hover{text-decoration:underline}
nav{display:flex;gap:18px;align-items:center;margin-bottom:22px;flex-wrap:wrap}nav b{font-size:20px}nav b span{color:var(--acc)}
nav .ext{margin-left:auto;font-size:13px;color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 14px}
.m{color:var(--mut);font-size:13px}.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;
padding:2px 10px;margin:2px;font-size:13px;color:var(--fg)}.chip.on{border-color:var(--acc)}
.tag{display:inline-block;background:#7aa2ff1f;color:var(--tag);border-radius:999px;padding:1px 9px;margin:2px;font-size:12px}
.tag button{background:none;color:var(--tag);padding:0 0 0 4px;font-size:12px}
input,textarea,select{width:100%;background:#0b0d11;color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:9px 11px;font:inherit}
textarea{min-height:80px}button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:8px 16px;font-weight:600;cursor:pointer}
button.g{background:#2a2f3a}button.s{padding:4px 10px;font-size:13px}
.row{display:flex;gap:10px;align-items:center}.row>*{flex:1}.row>button,.row>form{flex:0 0 auto}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:500;font-size:13px}mark{background:#ff4d4d33;color:var(--fg)}
.k{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:860px){.cols{grid-template-columns:1fr}}
.rel{font-size:11px;border-radius:4px;padding:0 5px;margin-left:4px}.rel.core{background:#3ecf8e22;color:var(--ok)}
.rel.supporting{background:#8b92a322;color:var(--mut)}
.ts{font-family:ui-monospace,Consolas,monospace;font-size:12px;background:#ff4d4d22;color:#ff8a8a;border-radius:5px;padding:1px 6px;
cursor:pointer;border:0;font-weight:600}.ts:hover{background:#ff4d4d44}
.player{position:sticky;top:0;z-index:5;background:var(--bg);padding:6px 0 10px}
.player video,.player iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:10px;background:#000;max-height:56vh}
.thumbs img{width:150px;border-radius:6px;border:1px solid var(--line);margin:2px;cursor:pointer;vertical-align:top}
pre{background:#0b0d11;border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto;font-size:13px}
details summary{cursor:pointer;color:var(--mut);font-size:13px}
.st{font-size:11px;border-radius:4px;padding:0 6px;margin-right:4px;white-space:nowrap}
.st.unreviewed{background:#f5b04122;color:#f5b041}.st.accepted{background:#3ecf8e22;color:var(--ok)}
.st.disputed,.st.stale,.st.superseded{background:#ff4d4d22;color:#ff8a8a}.st.conf{background:#7aa2ff1f;color:var(--tag)}
.rating{font-weight:600}.rating.Excellent,.rating.Good{color:var(--ok)}.rating.Mixed{color:#f5b041}
.rating.Weak,.rating.Unreliable{color:#ff8a8a}.rating.Unassessed{color:var(--mut)}
.inline{display:inline-flex;gap:6px;align-items:center}.inline select,.inline input{width:auto;padding:3px 6px;font-size:13px}
.prose h1{font-size:24px}.prose h2{font-size:18px;margin-top:22px}.prose li{margin:4px 0}
"""


LIBRARY_SECTIONS = [("/library", "Shelves"), ("/prompts", "Prompts"), ("/creators", "Creators"), ("/projects", "Projects"), ("/inbox", "Inbox")]
LIBRARY_MORE = [("/skills", "Skills"), ("/virtual", "Reading room ↗"), ("/whatsnew", "What's new"), ("/review", "Review"), ("/tags", "Tags"),
                ("/library/tidy", "Tidy"), ("/libraries", "Libraries"), ("/rules", "Rules"), ("/okf", "Open format")]
PLACE_NAMES = {"library": ("The Library", "/library"), "studio": ("Software Studio", "/kingdom/place/studio"),
               "business": ("Your business", "/kingdom/place/business"), "consulting": ("Consulting", "/kingdom/place/consulting"),
               "casework": ("Casework office", "/kingdom/place/casework"), "home": ("Home", "/kingdom/place/home"),
               "postoffice": ("The Post Office", "/kingdom/place/postoffice"), "office": ("Your office", "/kingdom/place/office"),
               "town": ("The town", "/kingdom/places")}
CREST = ("<svg viewBox='0 0 32 32' aria-hidden='true'><path d='M5 26V12l5 4 6-9 6 9 5-4v14z'/>"
         "<circle cx='16' cy='20' r='2.6'/></svg>")


def page(title: str, body: str, refresh: int = 0, place: str = "library", path: str = "") -> str:
    """Every room shares the Kingdom's bar: the crest goes back to the town, the place name to the room's door."""
    meta = f"<meta http-equiv=refresh content={refresh}>" if refresh else ""
    pname, phref = PLACE_NAMES.get(place, PLACE_NAMES["library"])
    secs = ""
    if place == "library":
        on = lambda h: "on" if path and (path == h or (h != "/library" and path.startswith(h))) else ""  # noqa: E731
        more = "".join(f"<a href='{h}' class='{on(h)}'>{t}</a>" for h, t in LIBRARY_MORE) + "".join(
            f"<a href='{escape(u)}'>{escape(n)} ↗</a>" for n, u in EXTENSIONS)
        secs = ("<nav class=sections aria-label='The Library'>"
                + "".join(f"<a href='{h}' class='{on(h)}'>{t}</a>" for h, t in LIBRARY_SECTIONS)
                + f"<details class=more><summary>More</summary><div class=more-menu>{more}</div></details></nav>")
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>{meta}"
            f"<meta name=viewport content='width=device-width,initial-scale=1'><title>{escape(title)} · The Kingdom</title>"
            f"<link rel=stylesheet href='/static/kingdom.css'></head><body class='room{' paper' if place == 'library' else ''}'>"
            f"<header class=bar><a class=crest href='/kingdom'>{CREST}<span>The Kingdom</span></a>"
            f"<a class=where href='{phref}'>{pname}</a>{secs}"
            f"<form class=jump action='/library' method=get role=search style='min-width:220px;max-width:320px'>"
            f"<input name=q placeholder='Search the library' aria-label='Search the library' "
            f"style='background:none;border:0;padding:0;color:var(--paper)'><kbd>/</kbd></form></header>"
            f"<main>{body}</main><script>addEventListener('keydown',e=>{{if(e.key==='/'&&!/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))"
            f"{{e.preventDefault();document.querySelector('.jump input').focus()}}}})</script></body></html>")


def attention_graph(eng, s, yt) -> str:
    """Where viewers paid attention, under the player: replay curve, timestamped-comment curve, chapters, peaks."""
    if not eng or not eng.get("buckets") or eng.get("signal") == "none":
        if eng and eng.get("signal") == "none":
            return ("<div class=m style='margin:-4px 0 12px'>No viewer-attention data: YouTube shows a replay curve only on "
                    "videos with enough views, and no comments mention a time.</div>")
        return ""
    bs, dur = eng["buckets"], eng.get("duration") or eng["buckets"][-1]["end"]
    W, H = 1000, 90

    def pts(key):
        return " ".join(f"{(b['start'] + b['end']) / 2 / dur * W:.1f},{H - 6 - b.get(key, 0) * (H - 14):.1f}" for b in bs)
    area = lambda key: f"0,{H} " + pts(key) + f" {W},{H}"  # noqa: E731
    peaks = "".join(f"<rect x='{p['start'] / dur * W:.1f}' y='0' width='{max(4, (p['end'] - p['start']) / dur * W):.1f}' height='{H}' "
                    f"fill='#f2b65a22'/>" for p in eng.get("peaks", []))
    chap = "".join(f"<line x1='{(c['start'] or 0) / dur * W:.1f}' x2='{(c['start'] or 0) / dur * W:.1f}' y1='0' y2='{H}' "
                   f"stroke='#ffffff18'><title>{escape(c['title'] or '')}</title></line>" for c in eng.get("chapters", []))
    svg = (f"<svg id=att viewBox='0 0 {W} {H}' preserveAspectRatio='none' data-dur='{dur}' role='img' "
           f"aria-label='Viewer attention across the video' style='width:100%;height:90px;cursor:pointer;display:block'>"
           f"{peaks}{chap}"
           + (f"<polygon points='{area('replay')}' fill='#f2b65a33'/><polyline points='{pts('replay')}' fill='none' stroke='#f2b65a' stroke-width='2' vector-effect='non-scaling-stroke'/>"
              if eng.get("has_replay") else "")
           + (f"<polyline points='{pts('talked')}' fill='none' stroke='#6fb3a2' stroke-width='1.5' stroke-dasharray='5 4' vector-effect='non-scaling-stroke'/>"
              if eng.get("has_talked") else "") + "</svg>")
    st = eng.get("stats") or {}
    chips = "".join(f"<button class=ts data-t='{int(p['at'])}' title='attention {p['score']}'>▶ {hms(p['start'])}</button> " for p in eng.get("peaks", []))
    legend = " · ".join(x for x in [
        "<span style='color:var(--lamp)'>━ rewatched (YouTube Most Replayed)</span>" if eng.get("has_replay") else "",
        "<span style='color:var(--verdigris)'>┅ mentioned in comments</span>" if eng.get("has_talked") else ""] if x)
    tops = "".join(f"<li>“{escape(c['text'][:180])}” <span class=m>{c['likes']} likes</span></li>" for c in eng.get("top_comments", [])[:3])
    return (f"<div class=card style='padding:12px 16px'><div class=row><div class=k style='flex:0 0 auto'>Where viewers paid attention</div>"
            f"<div class=m style='flex:1;text-align:right'>{legend}</div></div>{svg}"
            f"<div style='margin-top:6px'>{chips}<span class=m>{(st.get('views') or 0):,} views · {st.get('likes_per_1k_views') or '?'} likes per 1,000 views"
            f" · {st.get('timestamped_comments', 0)} comments mention a time</span></div>"
            + (f"<details style='margin-top:6px'><summary>What viewers said at those moments</summary><ul>{tops}</ul></details>" if tops else "")
            + "<script>document.getElementById('att').addEventListener('click',e=>{const r=e.currentTarget.getBoundingClientRect();"
              "const t=(e.clientX-r.left)/r.width*(+e.currentTarget.dataset.dur);if(typeof seek==='function')seek(Math.floor(t));});</script></div>")


def _snip(s: str) -> str:
    return escape(s or "").replace("\x02", "<mark>").replace("\x03", "</mark>")


def _short(s: str, n: int = 70) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def _rel(r):
    return f"<span class='rel {r}'>{r}</span>" if r in ("core", "supporting") else ""


def _post_btn(action: str, label: str, cls: str = "s", fields: dict | None = None) -> str:
    hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(v))}'>" for k, v in (fields or {}).items())
    return (f"<form method=post action='{action}' style='display:inline'>{hidden}"
            f"<button class='{cls}'>{label}</button></form>")


def _tags(tags, remove_action: str | None = None) -> str:
    out = ""
    for t in tags:
        x = _post_btn(remove_action, "×", "", {"tag": t["slug"]}) if remove_action else ""
        out += f"<span class=tag><a href='/tags/{t['slug']}' style='color:inherit'>{escape(t['name'])}</a>{x}</span>"
    return out


def badges(i) -> str:
    """Review state of an insight: house rules R3.4 (label), R5 (confidence), R6 (status)."""
    out = f"<span class='st {i.get('status') or 'unreviewed'}'>{escape(i.get('status') or 'unreviewed')}</span>"
    if i.get("label"):
        out += f"<span class='st conf'>{escape(i['label'])}</span>"
    if i.get("confidence"):
        out += f"<span class='st conf' title='{escape(i.get('basis') or '')}'>{escape(i['confidence'])} confidence</span>"
    return out


def watch(sid, t=None) -> str:
    """Link to the KB watch page, optionally at a timestamp."""
    return f"/library/s/{sid}" + (f"?t={int(t)}" if t is not None else "")


def create_router(lib: Library, state=None):
    import llm
    from fastapi import APIRouter, HTTPException, Request
    from fastapi.responses import HTMLResponse, RedirectResponse

    import library as libmod

    r = APIRouter()
    task = {"running": False, "what": "", "status": "", "result": ""}

    async def form(request: Request) -> dict:
        raw = (await request.body()).decode("utf-8", errors="replace")
        return {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}

    def tag_options():
        return "<datalist id=taglist>" + "".join(f"<option value='{escape(t['name'])}'>" for t in lib.tags()) + "</datalist>"

    def ent_lines(ents):
        """The calm version for shelves: name, then one short line. Details live on the entry page."""
        return "".join(
            f"<li><a href='/library/e/{e['slug']}'>{escape(e['name'])}</a>"
            + (f"<span class=m> · {escape(_short(e['description']))}</span>" if e["description"] else "") + "</li>"
            for e in ents)

    def ent_rows(ents):
        return "".join(
            f"<tr><td><a href='/library/e/{e['slug']}'>{escape(e['name'])}</a>{_rel(e['relevance'])}"
            + (f" <span class=m>· {escape(e['parent_name'])}</span>" if e["parent_name"] else "")
            + (f" <span class=m>· <a href='/library/e/{e['slug']}#knowledge'>{e['nknow']} knowledge</a></span>" if e.get("nknow") else "")
            + " " + _tags(e.get("tags", []))
            + f"<div class=m>{escape((e['description'] or '')[:120])}</div></td>"
            f"<td class=m>{e['kind']}</td><td class=m>{e['nsrc']} src"
            + (f" · {e['ninsights']} insights" if e["ninsights"] else "")
            + (f" · {e['nnotes']} notes" if e["nnotes"] else "") + "</td></tr>"
            for e in ents)

    def src_rows(srcs):
        return "".join(
            f"<tr><td><a href='{watch(s['id'])}'>{escape(s['title'])}</a> {_tags(s.get('tags', []))}"
            f"<div class=m>{escape(s['kind'])} · {escape(s['channel'] or '')} · {escape(s['published'] or '')}"
            f" · {s['nent']} entries</div></td></tr>" for s in srcs)

    # ================================================================== library
    @r.get("/", response_class=HTMLResponse)
    def home():
        return RedirectResponse("/kingdom", 303)

    @r.get("/library", response_class=HTMLResponse)
    def index(q: str = "", kind: str = "", tag: str = ""):
        counts = lib.kind_counts()
        gk, tk = lib.general_knowledge(), lib.tool_knowledge()
        np_ = sum(counts.get(k, 0) for k in PRODUCTS)
        chip = lambda k, href, label: f"<a class='chip {'on' if kind == k else ''}' href='{href}'>{label}</a>"  # noqa: E731
        chips = (chip("", "/library", "Overview") + chip("knowledge", "/library?kind=knowledge", f"Knowledge {len(gk)}")
                 + chip("products", "/library?kind=products", f"Tools &amp; products {np_}")
                 + chip("toolknowledge", "/library?kind=toolknowledge", f"Tool know-how {len(tk)}"))
        kindchips = "".join(chip(k, f"/library?kind={k}", f"{k} {counts[k]}") for k in KINDS if counts.get(k))
        tagchips = "".join(f"<a class=tag href='/tags/{t['slug']}'>{escape(t['name'])}</a>"
                           for t in lib.tags() if t["nent"] or t["nsrc"])
        browse = (f"<details class=browse{' open' if kind in KINDS else ''}><summary>By kind or tag</summary>"
                  f"<div>{kindchips}</div>" + (f"<div style='margin-top:6px'>{tagchips}</div>" if tagchips else "") + "</details>")
        body = (f"<form class='row lib-search' method=get action='/library'><input name=q value='{escape(q)}' "
                f"placeholder='Search the library'><button>Search</button></form>"
                f"<div class=shelf-chips>{chips}{browse}</div>")
        if q:
            hits = lib.search(q)
            rows = "".join(
                f"<tr><td><a href='{h['href'] if h['kind'] != 's' else watch(h['href'].split('/')[-1], h.get('t'))}'>{escape(h['title'])}</a>"
                + (f" <a class=ts href='{watch(h['href'].split('/')[-1], h['t'])}'>{hms(h['t'])}</a>" if h.get("t") is not None else "")
                + f"<div class=m>{_snip(h['snippet'])}</div></td></tr>" for h in hits)
            body += f"<div class=card><div class=k>{len(hits)} results for “{escape(q)}”</div><table>{rows}</table></div>"

        if kind == "toolknowledge":
            owners = {}
            for e in tk:
                owners.setdefault((e["owner"]["name"], e["owner"]["slug"]), []).append(e)
            for (oname, oslug), es in sorted(owners.items(), key=lambda x: x[0][0].lower()):
                body += (f"<section class='card shelf'><h2><a href='/library/e/{oslug}'>{escape(oname)}</a></h2>"
                         f"<ul class=lines>{ent_lines(es)}</ul></section>")
            if not owners:
                body += "<div class=card><p class=m>No tool-specific knowledge yet. Set a concept's parent to a tool to file it here.</p></div>"
        elif kind in ("knowledge", "products") or kind in KINDS:
            ents = gk if kind == "knowledge" else lib.entities(PRODUCTS if kind == "products" else [kind])
            body += (f"<section class='card shelf'><ul class=lines>"
                     f"{ent_lines(ents) or '<li class=m>Nothing here yet.</li>'}</ul></section>")
        else:
            if not q:
                prod, N = lib.entities(PRODUCTS), 12

                def shelf(title, ents, href):
                    more = f"<a class=all href='{href}'>All {len(ents)} →</a>" if len(ents) > N else ""
                    return (f"<section class='card shelf'><h2>{title}</h2>"
                            f"<ul class=lines>{ent_lines(ents[:N]) or '<li class=m>Nothing yet.</li>'}</ul>{more}</section>")
                body += ("<div class=cols>" + shelf("Knowledge", gk, "/library?kind=knowledge")
                         + shelf("Tools &amp; products", prod, "/library?kind=products") + "</div>")
                srcs = lib.sources(kind=None, limit=8)
                if srcs:
                    body += ("<section class='card shelf'><h2>Latest sources</h2><ul class=lines>" + "".join(
                        f"<li><a href='{watch(s['id'])}'>{escape(_short(s['title'], 90))}</a>"
                        f"<span class=m> · {escape(s['published'] or s['kind'])}</span></li>" for s in srcs) + "</ul></section>")
        body += ("<details class=add-entry><summary>Add your own entry</summary>"
                 "<form method=post action='/library/new' style='margin-top:10px'>"
                 "<div class=row><input name=name placeholder='Name (e.g. MCP, Qwen3-VL, LangGraph)' required>"
                 f"<select name=kind>{''.join(f'<option>{k}</option>' for k in KINDS)}</select>"
                 "<input name=parent placeholder='Part of… (optional)'></div>"
                 "<textarea name=description placeholder='Description (optional)' style='margin-top:8px'></textarea>"
                 "<div style='margin-top:8px'><button>Add</button></div></form></details>")
        return page("Library", body)

    @r.post("/library/new")
    async def new(request: Request):
        f = await form(request)
        slug = lib.create_entity(f.get("name", "").strip() or "untitled", f.get("kind", "concept"),
                                 f.get("description", ""), f.get("parent", ""))
        return RedirectResponse(f"/library/e/{slug}", 303)

    # ================================================================== entity
    @r.get("/library/e/{slug}", response_class=HTMLResponse)
    def entity(slug: str):
        e = lib.entity(slug)
        if not e:
            raise HTTPException(404)
        crumbs = " › ".join(f"<a href='/library/e/{a['slug']}'>{escape(a['name'])}</a>" for a in e["ancestors"])
        if e["kind"] in KNOWLEDGE:
            group = (f"<a href='/library/e/{e['owner']['slug']}'>{escape(e['owner']['name'])}</a> knowledge"
                     if e["owner"] else "General knowledge")
        elif e["kind"] == "project":
            group = "<a href='/projects'>Your projects</a>"
        else:
            group = "Tools &amp; products"
        src = "your description" if e["description_source"] == "internal" else "auto-generated — edit to make it yours"
        body = (f"<div class=card><div class=k>{group} · {e['kind']}{_rel(e['relevance'])}</div>"
                + (f"<div class=m style='margin-top:4px'>{crumbs} ›</div>" if crumbs else "")
                + f"<h1 style='margin:4px 0'>{escape(e['name'])}</h1>"
                f"<div>{_tags(e['tags'], f'/library/e/{slug}/untag')}"
                f"<form method=post action='/library/e/{slug}/tag' style='display:inline-flex;gap:6px;vertical-align:middle;margin-left:6px'>"
                f"<input name=tag list=taglist placeholder='+ tag' style='width:130px;padding:3px 8px;font-size:13px'>{tag_options()}"
                f"</form></div>"
                f"<p>{escape(e['description']) or '<span class=m>No description yet.</span>'}</p>"
                f"<div class=m>{src} · also known as: {escape(', '.join(e['aliases']))}</div>")
        others = [c for c in e["children"] if c["kind"] not in KNOWLEDGE or e["kind"] in KNOWLEDGE]
        if others:
            body += "<div style='margin-top:10px'><span class=k>Includes</span> " + "".join(
                f"<a class=chip href='/library/e/{c['slug']}'>{escape(c['name'])}</a>" for c in others) + "</div>"
        body += "</div>"
        import ui_extra

        if e["kind"] == "project":
            body += ui_extra.project_cards(lib, slug)
        body += ui_extra.skill_cards(lib, slug)
        import ui_prompts

        body += ui_prompts.entity_card(lib, slug)
        if e["kind"] in PRODUCTS:
            sk = e["sub_knowledge"]
            body += (f"<div class=card id=knowledge><div class=k>{escape(e['name'])} knowledge</div>"
                     f"<div class=m>Concepts, mechanisms and techniques specific to {escape(e['name'])}</div><table>"
                     + "".join(
                         f"<tr><td style='padding-left:{8 + 18 * (x['depth'] - 1)}px'><a href='/library/e/{x['slug']}'>"
                         f"{escape(x['name'])}</a> <span class=m>{x['kind']}"
                         + (f" · {x['ninsights']} insights" if x["ninsights"] else "")
                         + f"</span><div class=m>{escape((x['description'] or '')[:160])}</div></td></tr>" for x in sk)
                     + ("" if sk else "<tr><td class=m>Nothing filed here yet.</td></tr>")
                     + f"</table><form method=post action='/library/e/{slug}/adopt' class=row style='margin-top:8px'>"
                     f"<input name=name placeholder='File a concept under {escape(e['name'])} (e.g. Lease)' required>"
                     f"<button>File here</button></form></div>")

        for scope, head, hint in (("principle", "Principles", "tool-agnostic lessons from the sources"),
                                  ("tip", "Tool-specific tips", "how-tos and gotchas for this tool")):
            xs = [i for i in e["insights"] if i["scope"] == scope]
            if xs:
                body += (f"<div class=card><div class=k>{head}</div><div class=m>{hint}</div><table>" + "".join(
                    f"<tr><td>{badges(i)} {escape(i['text'])}<div class=m>"
                    + (f"<a class=ts href='{watch(i['sid'], i['t'])}'>▶ {hms(i['t'])}</a> " if i["t"] is not None else "")
                    + f"<a href='{watch(i['sid'])}'>{escape(i['title'])}</a> · {escape(i['src_id'] or '')} "
                    f"<span class='rating {escape(i['reputability'] or 'Unassessed')}'>{escape(i['reputability'] or '')}</span>"
                    + (f" · <a href='/review#i{i['id']}'>review</a>" if i["status"] == "unreviewed" else "")
                    + "</div></td></tr>" for i in xs) + "</table></div>")

        notes = "".join(f"<tr><td>{escape(n['body']).replace(chr(10), '<br>')}<div class=m>{n['created']} · "
                        + _post_btn(f"/library/note/{n['id']}/delete?back={slug}", "delete", "s g") + "</div></td></tr>"
                        for n in e["notes"])
        body += (f"<div class=card><div class=k>Internal notes</div><table>{notes}</table>"
                 f"<form method=post action='/library/e/{slug}/note' style='margin-top:8px'>"
                 f"<textarea name=body placeholder='Add what you know: gotchas, how you use it, links to your own work…'></textarea>"
                 f"<div style='margin-top:8px'><button>Add note</button></div></form></div>")

        res = [m for m in e["mentions"] if m["kind"] == "url"]
        body += ("<div class=card><div class=k>Resources</div><table>" + "".join(
            f"<tr><td><a href='{escape(m['url'])}' target=_blank>{escape(m['title'])}</a>"
            f"<div class=m>{escape(m['context'] or '')}</div></td></tr>" for m in res) + "</table>"
            f"<form method=post action='/library/e/{slug}/resource' class=row style='margin-top:8px'>"
            f"<input name=url placeholder='https://… (docs, repo, model card, paper)' required>"
            f"<input name=title placeholder='Title'><input name=note placeholder='Why it matters'><button>Add</button></form></div>")

        docs = [m for m in e["mentions"] if m["kind"] != "url"]
        if docs:
            body += "<div class=card><div class=k>Seen in</div><table>"
            for sid in dict.fromkeys(m["sid"] for m in docs):
                ms = [m for m in docs if m["sid"] == sid]
                times = "".join(
                    f"<div class=m><a class=ts href='{watch(sid, m['t'])}'>▶ {hms(m['t'])}</a> {escape(m['context'] or '')}</div>"
                    for m in ms if m["t"] is not None)
                body += (f"<tr><td><a href='{watch(sid)}'>{escape(ms[0]['title'])}</a>"
                         f"<div class=m>{escape(ms[0]['kind'])} · {escape(ms[0]['channel'] or '')} · {escape(ms[0]['published'] or '')}</div>"
                         f"{times}</td></tr>")
            body += "</table></div>"
        if e["related"]:
            body += "<div class=card><div class=k>Often appears with</div>" + "".join(
                f"<a class=chip href='/library/e/{x['slug']}'>{escape(x['name'])} ({x['n']})</a>" for x in e["related"]) + "</div>"

        parent_now = e["ancestors"][-1]["name"] if e["ancestors"] else ""
        body += (f"<div class=card><div class=k>Edit</div>"
                 f"<form method=post action='/library/e/{slug}/describe' style='margin-top:8px'>"
                 f"<textarea name=description>{escape(e['description'])}</textarea>"
                 f"<div style='margin-top:8px'><button>Save description</button></div></form>"
                 f"<form method=post action='/library/e/{slug}/rename' class=row style='margin-top:12px'>"
                 f"<input name=name value='{escape(e['name'])}'><button>Rename</button></form>"
                 f"<form method=post action='/library/e/{slug}/parent' class=row style='margin-top:12px'>"
                 f"<input name=parent value='{escape(parent_now)}' placeholder='Part of… (a tool = file as its knowledge; a topic = general; blank = none)'>"
                 f"<button>Set parent</button></form>"
                 f"<form method=post action='/library/e/{slug}/kind' class=row style='margin-top:12px'>"
                 f"<select name=kind>{''.join(('<option selected>' if k == e['kind'] else '<option>') + k + '</option>' for k in KINDS)}</select>"
                 f"<button>Change kind</button></form>"
                 f"<form method=post action='/library/e/{slug}/alias' class=row style='margin-top:12px'>"
                 f"<input name=alias placeholder='Add alias (other spelling it goes by)'><button>Add alias</button></form>"
                 f"<form method=post action='/library/e/{slug}/merge' class=row style='margin-top:12px'>"
                 f"<input name=into placeholder='Merge this duplicate into… (name of the main entry)'><button>Merge</button></form>"
                 f"<div style='margin-top:12px'>" + _post_btn(f"/library/e/{slug}/delete", "Delete entry (and never re-add it)", "s g")
                 + "</div></div>")
        return page(e["name"], body)

    def _post(path, fn):
        @r.post(path)
        async def handler(slug: str, request: Request):
            f = await form(request)
            try:
                target = fn(slug, f) or slug
            except KeyError:
                raise HTTPException(404)
            return RedirectResponse(target if target.startswith("/") else f"/library/e/{target}", 303)
        return handler

    _post("/library/e/{slug}/note", lambda s, f: lib.add_note(s, f.get("body", "")))
    _post("/library/e/{slug}/describe", lambda s, f: lib.set_description(s, f.get("description", "")))
    _post("/library/e/{slug}/resource", lambda s, f: lib.add_resource(s, f.get("url", ""), f.get("title", ""), f.get("note", "")))
    _post("/library/e/{slug}/alias", lambda s, f: lib.add_alias(s, f.get("alias", "")))
    _post("/library/e/{slug}/kind", lambda s, f: lib.set_kind(s, f.get("kind", "")))
    _post("/library/e/{slug}/rename", lambda s, f: lib.rename(s, f.get("name", "")))
    _post("/library/e/{slug}/parent", lambda s, f: lib.set_parent(s, f.get("parent", "")))
    _post("/library/e/{slug}/merge", lambda s, f: lib.merge(s, f.get("into", "").strip().rstrip("/").split("/")[-1]))
    _post("/library/e/{slug}/delete", lambda s, f: (lib.delete_entity(s), "/library")[1])
    _post("/library/e/{slug}/tag", lambda s, f: lib.tag_entity(s, f.get("tag", ""), True) if f.get("tag", "").strip() else None)
    _post("/library/e/{slug}/untag", lambda s, f: lib.tag_entity(s, f.get("tag", ""), False))

    def _adopt(s, f):
        name = f.get("name", "").strip()
        if name:
            try:
                lib.set_parent(name, lib.entity(s)["name"])
            except KeyError:
                lib.create_entity(name, "concept", parent=lib.entity(s)["name"])
        return s
    _post("/library/e/{slug}/adopt", _adopt)

    @r.post("/library/note/{nid}/delete")
    def del_note(nid: int, back: str):
        lib.delete_note(nid)
        return RedirectResponse(f"/library/e/{back}", 303)

    # ================================================================== watch / source page
    @r.get("/library/s/{sid}", response_class=HTMLResponse)
    def source(sid: int, t: float | None = None):
        s = lib.source(sid)
        if not s:
            raise HTTPException(404)
        doc = s["doc"] or {}
        src = doc.get("source", {})
        segs = doc.get("segments", [])
        ov = doc.get("overview") or {}
        local = libmod.local_file(s["local_path"])
        has_local = bool(local and local.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov", ".mp3", ".m4a")
                         and local.exists())
        yt = src.get("external_id") if "youtube.com" in (s["url"] or "") else None
        watchable = has_local or yt or any(x.get("start") is not None for x in segs)

        player = ""
        if has_local:
            tag_ = "video" if local.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov") else "audio"
            player = (f"<div class=player><{tag_} id=pl controls preload=metadata src='/media/{sid}/{quote(local.name)}'>"
                      f"</{tag_}><div class=m>Playing your local copy · "
                      + (f"<a href='{escape(s['url'])}' target=_blank>YouTube ↗</a>" if yt else "") + "</div></div>")
        elif yt:
            player = (f"<div class=player><iframe id=yt allow='autoplay; encrypted-media' allowfullscreen "
                      f"src='https://www.youtube-nocookie.com/embed/{escape(yt)}?start={int(t or 0)}'></iframe></div>")

        body = player + attention_graph(((doc.get("extra") or {}).get("engagement")), s, yt)
        a_ = json.loads(s["assessment"]) if s.get("assessment") else {}
        dims = " · ".join(f"{k}: {escape(str(a_[k]))}" for k in ("authority", "directness", "freshness", "independence",
                                                                  "conflicts", "origin_family") if a_.get(k))
        imp = doc.get("imported") or {}
        body += (f"<div class=card><div class=row><div><div class=k>Source record</div>"
                 f"<b>{escape(s['src_id'] or '')}</b> <span class=m>library {escape(s['namespace'] or 'KB')}"
                 + (f" · supersedes {escape(s['supersedes'])}" if s.get("supersedes") else "")
                 + f"</span><div>Rating: <span class='rating {escape(s['reputability'] or 'Unassessed')}'>{escape(s['reputability'] or 'Unassessed')}</span>"
                 f" <span class=m>({'drafted by the model' if s['assessed_by'] == 'model (draft)' else 'by ' + escape(s['assessed_by']) if s['assessed_by'] else 'not assessed'}"
                 f", {escape(s['status'] or 'unreviewed')})</span></div>"
                 + (f"<div class=m>{dims}</div>" if dims else "") + (f"<div class=m>{escape(a_.get('basis', ''))}</div>" if a_.get("basis") else "")
                 + (f"<div class=m>Imported from <a href='/libraries/{escape(imp.get('library', ''))}'>{escape(imp.get('library', ''))}</a>: "
                    f"{escape(imp.get('original_path', ''))} · checksum {escape(imp.get('checksum', ''))}"
                    + (f" · original metadata: {escape(json.dumps(imp.get('metadata')))}" if imp.get("metadata") else "") + "</div>" if imp else "")
                 + f"</div><form method=post action='/review/source/{sid}' class=inline style='flex:0 0 auto'>"
                 f"<select name=reputability>{''.join(('<option selected>' if r_ == (s['reputability'] or 'Unassessed') else '<option>') + r_ + '</option>' for r_ in RATINGS)}</select>"
                 f"<input name=basis placeholder='decisive dimensions' value='{escape(a_.get('basis', ''))}'><button class=s>Confirm rating</button></form>"
                 f"</div></div>")
        body += (f"<div class=card><div class=k>{escape(s['kind'])}{' · ' + escape(s['extension']) if s.get('extension') else ''}</div>"
                 f"<h1 style='margin:4px 0'>{escape(s['title'])}</h1>"
                 f"<div class=m>{escape(s['channel'] or '')} · {escape(s['published'] or '')}"
                 + (f" · {hms(s['duration'])}" if s.get("duration") else "")
                 + (f" · <a href='{escape(s['url'])}' target=_blank>original ↗</a>" if s["url"] and not s["url"].startswith("file:") else "")
                 + f"</div><div style='margin-top:6px'>{_tags(s['tags'], f'/library/s/{sid}/untag')}"
                 f"<form method=post action='/library/s/{sid}/tag' style='display:inline-flex;vertical-align:middle;margin-left:6px'>"
                 f"<input name=tag list=taglist placeholder='+ tag' style='width:130px;padding:3px 8px;font-size:13px'>{tag_options()}"
                 f"</form></div><p>{escape(s['summary'] or '')}</p>")
        if ov.get("core_method"):
            body += f"<div class=k>Core method</div><p>{escape(ov['core_method'])}</p>"
        if ov.get("key_takeaways"):
            body += "<div class=k>Key takeaways</div><ul>" + "".join(f"<li>{escape(x)}</li>" for x in ov["key_takeaways"]) + "</ul>"
        if ov.get("hype_check"):
            body += f"<div class=k>Hype check</div><p class=m>{escape(ov['hype_check'])}</p>"
        body += "</div>"

        for scope, head in (("principle", "Principles (tool-agnostic)"), ("tip", "Tool-specific tips")):
            xs = [i for i in s["insights"] if i["scope"] == scope]
            if xs:
                unrev = sum(1 for i in xs if i["status"] == "unreviewed")
                body += (f"<div class=card><div class=row><div class=k>{head}</div>"
                         + (_post_btn(f"/review/source/{sid}/accept-all", f"Accept all {unrev} unreviewed", "s") if unrev else "")
                         + "</div><table>" + "".join(
                    f"<tr id='i{i['id']}'><td>" + (f"<button class=ts data-t='{int(i['t'])}'>{hms(i['t'])}</button> " if i["t"] is not None else "")
                    + f"{badges(i)} {escape(i['text'])}<div class=m>{escape(i['about'] or '')}"
                    + (f" · {escape(i['basis'])}" if i.get("basis") else "") + "</div></td></tr>" for i in xs) + "</table></div>")

        groups = (("General knowledge", lambda e: e["kind"] in KNOWLEDGE and not e["owner"]),
                  ("Tool-specific knowledge", lambda e: e["kind"] in KNOWLEDGE and e["owner"]),
                  ("Tools & products", lambda e: e["kind"] in PRODUCTS))
        cols = ""
        for title, pick in groups:
            xs = [e for e in s["entities"] if pick(e)]
            if xs:
                cols += (f"<div class=card><div class=k>{escape(title)}</div><table>" + "".join(
                    f"<tr><td><a href='/library/e/{e['slug']}'>{escape(e['name'])}</a>{_rel(e['relevance'])}"
                    + (f" <span class=m>· {escape(e['owner']['name'])}</span>" if e.get("owner") else "")
                    + f"</td><td class=m>{e['kind']}</td><td>"
                    + (f"<button class=ts data-t='{int(e['first'])}'>{hms(e['first'])}</button>" if e["first"] is not None else "")
                    + "</td></tr>" for e in xs) + "</table></div>")
        body += f"<div class=cols>{cols}</div>" if cols else ""

        if segs:
            body += "<div class=card><div class=k>Walkthrough</div><table>"
            for g in segs:
                st = g.get("start")
                thumbs = "".join(
                    f"<img loading=lazy src='/media/{sid}/{quote(f['file'])}' data-t='{int(f['t'])}' title='{hms(f['t'])}'>"
                    for f in g.get("frames", []) if has_local or local)
                code = "".join(f"<div class=m>{escape(v.get('kind', ''))}</div><pre>{escape(v.get('text', ''))}</pre>"
                               for v in g.get("verbatim", []))
                claims = "".join(f"<div class=m>{'✅ shown' if c.get('demonstrated') else '⚠️ claimed'}: {escape(c.get('text', ''))}</div>"
                                 for c in g.get("claims", []))
                body += ("<tr><td style='width:70px'>"
                         + (f"<button class=ts data-t='{int(st)}'>{hms(st)}</button>" if st is not None else "")
                         + f"</td><td>{escape(g.get('on_screen', ''))}"
                         + ("<ol>" + "".join(f"<li>{escape(x)}</li>" for x in g.get("steps", [])) + "</ol>" if g.get("steps") else "")
                         + code + claims
                         + (f"<div class=thumbs>{thumbs}</div>" if thumbs else "")
                         + (f"<details><summary>Transcript</summary><p class=m>{escape(g.get('text', ''))}</p></details>" if g.get("text") else "")
                         + "</td></tr>")
            body += "</table></div>"

        if watchable:
            body += f"""<script>
const pl=document.getElementById('pl'), yt=document.getElementById('yt'), vid={json.dumps(yt or '')};
function seek(t){{ if(pl){{pl.currentTime=t; pl.play(); window.scrollTo({{top:0,behavior:'smooth'}});}}
  else if(yt){{yt.src='https://www.youtube-nocookie.com/embed/'+vid+'?autoplay=1&start='+t; window.scrollTo({{top:0,behavior:'smooth'}});}}
  else if({json.dumps(s['url'] or '')}.includes('youtube.com')) window.open({json.dumps(s['url'] or '')}+'&t='+t+'s','_blank'); }}
document.querySelectorAll('[data-t]').forEach(b=>b.addEventListener('click',()=>seek(+b.dataset.t)));
const t0={json.dumps(t)}; if(t0!==null && pl) pl.addEventListener('loadedmetadata',()=>{{pl.currentTime=t0;}},{{once:true}});
</script>"""
        body += ("<div class=card><div class=k>Remove</div><div class=m>Take this source out of the library: its insights and "
                 "sightings go, and so do automatic entries nothing else mentions. Entries you made or edited stay.</div>"
                 + _post_btn(f"/library/s/{sid}/delete", "Remove this source", "s g") + "</div>")
        return page(s["title"], body)

    @r.post("/library/s/{sid}/delete")
    def s_delete(sid: int):
        lib.delete_source(sid, "removed on the source page")
        return RedirectResponse("/library", 303)

    @r.post("/library/s/{sid}/tag")
    async def s_tag(sid: int, request: Request):
        f = await form(request)
        if f.get("tag", "").strip():
            lib.tag_source(sid, f["tag"], True)
        return RedirectResponse(watch(sid), 303)

    @r.post("/library/s/{sid}/untag")
    async def s_untag(sid: int, request: Request):
        lib.tag_source(sid, (await form(request)).get("tag", ""), False)
        return RedirectResponse(watch(sid), 303)

    # ================================================================== tags
    @r.get("/tags", response_class=HTMLResponse)
    def tags_page():
        act, prop = lib.tags("active"), lib.tags("proposed")
        body = ("<div class=card><div class=k>Tags</div><div class=m>Categories that cut across the library (e.g. "
                "Voice). The tidy pass applies them automatically from this list; you can tag by hand too. "
                "Edit a tag's description to steer what the model files under it.</div><table>"
                + "".join(f"<tr><td><a href='/tags/{t['slug']}'><b>{escape(t['name'])}</b></a>"
                          f"<div class=m>{escape(t['description'] or '')}</div></td>"
                          f"<td class=m style='white-space:nowrap'>{t['nent']} entries · {t['nsrc']} sources</td></tr>" for t in act)
                + "</table></div>")
        if prop:
            body += ("<div class=card><div class=k>Proposed by the model</div><table>" + "".join(
                f"<tr><td><b>{escape(t['name'])}</b><div class=m>{escape(t['description'] or '')}</div></td>"
                f"<td style='white-space:nowrap'>" + _post_btn(f"/tags/{t['slug']}/status", "Add to list", "s", {"status": "active"})
                + " " + _post_btn(f"/tags/{t['slug']}/status", "Dismiss", "s g", {"status": "dismissed"}) + "</td></tr>"
                for t in prop) + "</table><div class=m>New tags are applied on the next <a href='/library/tidy'>Re-tidy</a>.</div></div>")
        body += ("<form class=card method=post action='/tags/new'><div class=k>New tag</div><div class=row style='margin-top:8px'>"
                 "<input name=name placeholder='Name (e.g. Voice)' required><input name=description placeholder='What belongs here'>"
                 "<button>Add</button></div></form>")
        return page("Tags", body)

    @r.post("/tags/new")
    async def tag_new(request: Request):
        f = await form(request)
        slug = lib.save_tag(f.get("name", "untitled"), f.get("description", ""))
        return RedirectResponse(f"/tags/{slug}", 303)

    @r.post("/tags/{slug}/status")
    async def tag_status(slug: str, request: Request):
        lib.set_tag_status(slug, (await form(request)).get("status", "active"))
        return RedirectResponse("/tags", 303)

    @r.post("/tags/{slug}/edit")
    async def tag_edit(slug: str, request: Request):
        f = await form(request)
        new = lib.save_tag(f.get("name", slug), f.get("description", ""), old_slug=slug)
        return RedirectResponse(f"/tags/{new}", 303)

    @r.get("/tags/{slug}", response_class=HTMLResponse)
    def tag_page(slug: str):
        t = lib.tag(slug)
        if not t:
            raise HTTPException(404)
        es = t["entities"]
        gk = [e for e in es if e["kind"] in KNOWLEDGE and not e["owner"]]
        tk = [e for e in es if e["kind"] in KNOWLEDGE and e["owner"]]
        pr = [e for e in es if e["kind"] in PRODUCTS]
        body = (f"<div class=card><div class=k>Tag</div><h1 style='margin:4px 0'>{escape(t['name'])}</h1>"
                f"<p class=m>{escape(t['description'] or '')}</p></div>")
        if t["insights"]:
            body += ("<div class=card><div class=k>What the sources teach</div><table>" + "".join(
                f"<tr><td>{'🧭' if i['scope'] == 'principle' else '🔧'} {escape(i['text'])}<div class=m>"
                + (f"<a class=ts href='{watch(i['sid'], i['t'])}'>▶ {hms(i['t'])}</a> " if i["t"] is not None else "")
                + f"<a href='{watch(i['sid'])}'>{escape(i['title'])}</a> · <a href='/library/e/{i['about_slug']}'>{escape(i['about'])}</a>"
                f"</div></td></tr>" for i in t["insights"][:30]) + "</table></div>")
        cols = ""
        for title, xs in (("General knowledge", gk), ("Tool-specific knowledge", tk), ("Tools & products", pr)):
            if xs:
                cols += f"<div class=card><div class=k>{escape(title)}</div><table>{ent_rows(xs)}</table></div>"
        body += f"<div class=cols>{cols}</div>" if cols else ""
        if t["sources"]:
            body += f"<div class=card><div class=k>Sources</div><table>{src_rows(t['sources'])}</table></div>"
        body += (f"<form class=card method=post action='/tags/{t['slug']}/edit'><div class=k>Edit tag</div>"
                 f"<div class=row style='margin-top:8px'><input name=name value='{escape(t['name'])}'>"
                 f"<input name=description value='{escape(t['description'] or '')}' placeholder='What belongs here'>"
                 f"<button>Save</button></div></form>"
                 + _post_btn(f"/tags/{t['slug']}/status", "Delete tag", "s g", {"status": "deleted"}))
        return page(t["name"], body)

    # ================================================================== what's new
    @r.get("/whatsnew", response_class=HTMLResponse)
    def whatsnew(days: int = 7):
        import datetime as dt

        since = (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        ch = lib.changes(since)
        chips = "".join(f"<a class='chip {'on' if d == days else ''}' href='/whatsnew?days={d}'>{lbl}</a>"
                        for d, lbl in ((1, "today"), (7, "7 days"), (30, "30 days")))
        body = (f"<div class=card><div class=k>What's new</div>{chips}<div class=m>The raw material for daily/weekly recaps "
                f"(also at <a href='/api/v1/changes?since={since[:10]}'>/api/v1/changes</a> for bots).</div></div>")
        if ch["sources"]:
            body += "<div class=card><div class=k>New sources</div><table>" + "".join(
                f"<tr><td><a href='{watch(s['id'])}'><b>{escape(s['title'])}</b></a> {_tags(s['tags'])}"
                f"<div class=m>{escape(s['kind'])} · {escape(s['channel'] or '')} · added {s['created'][:16]}</div>"
                f"<div>{escape((s['summary'] or '')[:400])}</div></td></tr>" for s in ch["sources"]) + "</table></div>"
        if ch["insights"]:
            body += "<div class=card><div class=k>New insights</div><table>" + "".join(
                f"<tr><td>{'🧭' if i['scope'] == 'principle' else '🔧'} {escape(i['text'])}<div class=m>"
                + (f"<a class=ts href='{watch(i['source_id'], i['t'])}'>▶ {hms(i['t'])}</a> " if i["t"] is not None else "")
                + f"<a href='/library/e/{i['about_slug']}'>{escape(i['about'])}</a> · {escape(i['title'])}</div></td></tr>"
                for i in ch["insights"][:60]) + "</table></div>"
        if ch["entities"]:
            body += "<div class=card><div class=k>New entries</div>" + "".join(
                f"<a class=chip href='/library/e/{e['slug']}'>{escape(e['name'])} <span class=m>{e['kind']}</span></a>"
                for e in ch["entities"]) + "</div>"
        if ch["proposed_tags"]:
            body += "<div class=card><div class=k>Proposed tags</div>" + "".join(
                f"<span class=tag>{escape(t['name'])}</span>" for t in ch["proposed_tags"]) + " <a href='/tags'>review →</a></div>"
        if not any(ch[k] for k in ("sources", "insights", "entities", "notes")):
            body += "<div class=card><p class=m>Nothing new in this period.</p></div>"
        return page("What's new", body)

    # ================================================================== inbox
    @r.get("/inbox", response_class=HTMLResponse)
    def inbox_page():
        items = lib.inbox()
        working = any(i["status"] in ("pending", "working") for i in items)
        body = ("<div class=card><div class=row><div class=k>Inbox — documents sent by extensions</div>"
                + _post_btn("/inbox/retry", "Retry failed", "s g") + "</div><table>" + "".join(
                    f"<tr><td>{escape(i['title'] or '')}<div class=m>{escape(i['extension'] or '')} · {i['created']}"
                    + (f" · <a href='{watch(i['source_id'])}'>open</a>" if i["source_id"] else "")
                    + (f"<br><span style='color:var(--acc)'>{escape(i['error'])}</span>" if i["error"] else "")
                    + f"</div></td><td class=m>{i['status']}</td></tr>" for i in items)
                + ("" if items else "<tr><td class=m>Nothing received yet.</td></tr>") + "</table></div>")
        return page("Inbox", body, refresh=3 if working else 0)

    @r.post("/inbox/retry")
    def inbox_retry():
        lib.inbox_retry_failed()
        return RedirectResponse("/inbox", 303)

    # ================================================================== review (house rules R4-R6)
    @r.get("/review", response_class=HTMLResponse)
    def review(ns: str = ""):
        q = lib.review_queue()
        groups = [g for g in q["groups"] if not ns or g["namespace"] == ns.upper()]
        rules_ = lib.suggestions(kinds=("rule",))
        body = (f"<div class=card><div class=k>Review</div><p class=m>Everything machines file starts as <b>unreviewed</b>: "
                f"usable and searchable, but labelled (rule R6.1). Accept what you have checked; reject what is wrong; mark "
                f"<i>disputed</i> when sources disagree. Consequential claims (security, money, health, legal) need a fresher "
                f"or independent source first (R6.2). Your decisions survive rebuilds and are recorded in the "
                f"<a href='/review/log'>review log</a>.</p>"
                f"<div>{q['counts']['insights']} insights · {q['counts']['sources']} source ratings · {len(rules_)} rule proposals waiting"
                + (f" · showing library <b>{escape(ns.upper())}</b> (<a href='/review'>all</a>)" if ns else "") + "</div></div>")
        if rules_:
            body += ("<div class=card><div class=k>Rule proposals from imported libraries</div><div class=m>Adopting adds the "
                     "rule to your house rules (RULES.local.md) and the tidy pass starts following it.</div><table>" + "".join(
                         f"<tr><td><span class='st conf'>{escape(x['extra'] or 'new')}</span> {escape(x['b'])}"
                         f"<div class=m>{escape(x['reason'] or '')} — from {escape(x['a'])}</div></td><td style='white-space:nowrap'>"
                         + _post_btn(f"/library/tidy/suggestion/{x['id']}/yes?back=/review", "Adopt", "s") + " "
                         + _post_btn(f"/library/tidy/suggestion/{x['id']}/no?back=/review", "Not for us", "s g") + "</td></tr>"
                         for x in rules_) + "</table></div>")
        opts = "".join(f"<option>{c}</option>" for c in CONFIDENCE)
        for g in groups[:40]:
            body += (f"<div class=card><div class=row><div><a href='{watch(g['sid'])}'><b>{escape(g['title'])}</b></a>"
                     + (f" <span class='st unreviewed'>{g['peaks']} from the most-watched moments</span>" if g.get("peaks") else "")
                     + f" <span class=m>{escape(g['src_id'] or '')} · rated <span class='rating {escape(g['reputability'])}'>"
                     f"{escape(g['reputability'])}</span>{' (model draft)' if g['assessed_by'] == 'model (draft)' else ''}</span></div>"
                     + _post_btn(f"/review/source/{g['sid']}/accept-all?back=/review", f"Accept all {len(g['items'])}", "s")
                     + "</div><table>")
            for i in g["items"]:
                body += (f"<tr id='i{i['id']}'><td>{badges(i)}"
                         + ("<span class='st unreviewed' title='Viewers rewatched or talked about this moment most'>★ most watched</span>"
                            if i.get("peak") else "")
                         + f" <b>{'Principle' if i['scope'] == 'principle' else 'Tip'}:</b> "
                         f"{escape(i['text'])}<div class=m>about {escape(i['about'] or '')}"
                         + (f" · <a href='{watch(g['sid'], i['t'])}' target=_blank>▶ {hms(i['t'])}</a>" if i["t"] is not None else "")
                         + (f" · {escape(i['basis'])}" if i["basis"] else "") + "</div></td><td style='white-space:nowrap'>"
                         f"<form method=post action='/review/insight/{i['id']}' class=inline>"
                         f"<select name=confidence>{opts.replace('<option>' + (i['confidence'] or 'unknown') + '<', '<option selected>' + (i['confidence'] or 'unknown') + '<')}</select>"
                         f"<button class=s name=status value=accepted>Accept</button>"
                         f"<button class='s g' name=status value=disputed>Disputed</button>"
                         f"<button class='s g' name=status value=rejected>Reject</button></form></td></tr>")
            body += "</table></div>"
        srcs = [x for x in q["sources"] if not ns or x["namespace"] == ns.upper()]
        if srcs:
            body += ("<div class=card><div class=k>Source ratings to confirm</div><div class=m>Rate each source for the use it "
                     "is put to (R4.1). The model's draft is preselected.</div><table>" + "".join(
                         f"<tr><td><a href='{watch(x['id'])}'>{escape(x['title'])}</a><div class=m>{escape(x['src_id'] or '')} · "
                         f"{escape(x['kind'])} · {escape((x['assessment'] or {}).get('basis', ''))}</div></td><td>"
                         f"<form method=post action='/review/source/{x['id']}?back=/review' class=inline>"
                         f"<select name=reputability>{''.join(('<option selected>' if r_ == x['reputability'] else '<option>') + r_ + '</option>' for r_ in RATINGS)}</select>"
                         f"<input name=basis placeholder='basis' value='{escape((x['assessment'] or {}).get('basis', ''))}'>"
                         f"<button class=s>Confirm</button></form></td></tr>" for x in srcs[:60]) + "</table></div>")
        if not (groups or srcs or rules_):
            body += "<div class=card><p>Nothing waiting for review.</p></div>"
        return page("Review", body)

    def _back(request: Request, default: str):
        b = request.query_params.get("back")
        return b if b and b.startswith("/") else default

    @r.post("/review/insight/{iid}")
    async def review_insight(iid: int, request: Request):
        f = await form(request)
        try:
            lib.review_insight(iid, f.get("status", "accepted"), f.get("confidence"))
        except (KeyError, ValueError):
            raise HTTPException(404)
        return RedirectResponse(_back(request, "/review") + f"#i{iid}", 303)

    @r.post("/review/source/{sid}/accept-all")
    def review_accept_all(sid: int, request: Request):
        lib.review_source_insights(sid, "accepted")
        return RedirectResponse(_back(request, watch(sid)), 303)

    @r.post("/review/source/{sid}")
    async def review_source(sid: int, request: Request):
        f = await form(request)
        lib.review_source(sid, f.get("reputability", "Unassessed"), f.get("basis", ""))
        return RedirectResponse(_back(request, watch(sid)), 303)

    @r.get("/review/log", response_class=HTMLResponse)
    def review_log():
        rows = lib.review_log(500)
        body = ("<div class=card><div class=k>Review log</div><div class=m>Every review decision (R6.3).</div><table>"
                "<tr><th>When</th><th>What</th><th>Class</th><th>Decision</th><th>Basis</th></tr>" + "".join(
                    f"<tr><td class=m>{escape(x['created'][:16])}</td><td>{escape(x['target'])}</td><td class=m>{escape(x['change_class'])}</td>"
                    f"<td>{escape(x['decision'])}</td><td class=m>{escape(x['reviewer'])}: {escape(x['basis'] or '')}</td></tr>" for x in rows)
                + "</table></div>")
        return page("Review log", body)

    # ================================================================== rules
    @r.get("/rules", response_class=HTMLResponse)
    def rules_page():
        import markdown

        import importer
        html_ = markdown.markdown(importer.house_rules(lib), extensions=["tables"])
        return page("House rules", f"<div class='card prose'>{html_}</div>")

    import ui_extra

    ui_extra.add_routes(r, lib, state, form)
    import ui_kingdom

    ui_kingdom.add_routes(r, lib, state, form)
    import ui_prompts

    ui_prompts.add_routes(r, lib, state, form)

    # ================================================================== Open Knowledge Format
    @r.get("/okf", response_class=HTMLResponse)
    def okf_page(check: str = "", path: str = ""):
        import okf

        m = getattr(state, "okf", None)
        st = m.status() if m else {"dir": str(okf.default_dir(lib)), "last_sync": {}, "enabled": False, "error": ""}
        ls = st.get("last_sync") or {}
        body = ("<div class=card><div class=k>Open Knowledge Format</div>"
                "<h1 style='margin:4px 0'>Your library as an OKF v0.3 bundle</h1>"
                "<p>The knowledge base keeps a folder of plain Markdown files, one per entry and one per source, in "
                "Google's <a href='https://github.com/open-knowledge-format/open-knowledge-format'>Open Knowledge Format</a>. "
                "Agents and other tools can read it directly, you can keep it in git, and it updates itself a few seconds "
                "after anything changes here. Don't edit the files by hand: change things in the knowledge base.</p>"
                f"<p><b>Folder:</b> <code>{escape(st['dir'])}</code><br>"
                + (f"<b>Last updated:</b> {escape(ls.get('at', ''))} · {ls.get('concepts', 0)} concepts"
                   f" · {ls.get('deprecated', 0)} retired · {ls.get('files_written', 0)} file(s) written last time"
                   if ls else "<b>Not written yet.</b>") + "</p>"
                + (f"<p style='color:#ff8a8a'>Last update failed: {escape(st['error'])}</p>" if st.get("error") else "")
                + ("" if st.get("enabled", True) else "<p class=m>Automatic updates are off (KB_OKF=0).</p>")
                + "<div style='display:flex;gap:8px;align-items:center;flex-wrap:wrap'>"
                + _post_btn("/okf/sync", "Update now", "")
                + "<a class=chip href='/okf?check=1'>Check conformance</a>"
                  "<a class=chip href='/api/v1/okf/bundle.zip'>Download as .zip</a>"
                  "<a class=chip href='/api/v1/okf/concept?path=index.md'>Open index.md</a></div></div>")
        body += ("<div class=card><div class=k>How the library maps onto OKF</div><table>"
                 "<tr><th>Here</th><th>In the bundle</th></tr>"
                 "<tr><td>Entry kind</td><td><code>type</code>: Tool, LLM, Technique… Sources are <code>Reference</code></td></tr>"
                 "<tr><td>Tool-specific knowledge</td><td>Filed under its product: <code>tools/tango/lease.md</code></td></tr>"
                 "<tr><td>Where a claim came from</td><td><code>sources</code> plus a footnote such as <code>[^SRC-KB-0001]</code> on each insight</td></tr>"
                 "<tr><td>Written by the model, or by you</td><td><code>generated.by</code>: <code>kb-librarian/…</code> or <code>human:owner</code></td></tr>"
                 "<tr><td>Your accepted reviews</td><td><code>verified</code> by <code>human:owner</code>, which makes the entry human-reviewed. "
                 "If the content changes afterwards it drops back to unverified until you review it again.</td></tr>"
                 "<tr><td>Merged, moved or superseded</td><td><code>status: deprecated</code> with <code>superseded_by</code>; the old path keeps working</td></tr>"
                 "<tr><td>Your source rating, aliases, origin</td><td><code>x-kb-reputability</code>, <code>x-kb-aliases</code>, <code>x-kb-origin</code>. "
                 "OKF records objective signals, not scores, so the rating travels as a labelled extension.</td></tr>"
                 "</table><p class=m>Importing someone else's OKF bundle: use <a href='/import'>Import</a>. Their trust tiers and "
                 "statuses are kept as history; everything still arrives unreviewed here (house rules R7).</p></div>")
        if check:
            target = Path(path) if path else Path(st["dir"])
            if not target.exists():
                body += f"<div class=card><b>{escape(str(target))}</b> doesn't exist yet. Press Update now first.</div>"
            else:
                v = okf.validate(target)
                o = v.get("official") or {}
                ok = v["conformant"]
                body += (f"<div class=card><div class=k>Conformance check · {escape(str(target))}</div>"
                         f"<h2 style='margin:6px 0;color:{'var(--ok)' if ok else '#ff8a8a'}'>"
                         f"{'Conformant' if ok else 'Not conformant'} with OKF {escape(str(v['okf_version'] or '?'))}</h2>"
                         f"<p>{v['concepts']} concepts in {v['files']} files · {v['broken_links']} links to concepts not written yet</p>"
                         + (f"<p>Google's validator: {o['error']} errors, {o['warning']} warnings, {o['info']} info</p>"
                            if isinstance(o.get("error"), int) else f"<p class=m>{escape(str(o.get('error') or 'Google validator not available'))}</p>")
                         + "<div class=cols><div><b>Trust</b><table>" + "".join(
                             f"<tr><td>{escape(k)}</td><td>{n}</td></tr>" for k, n in v["trust_tiers"].items())
                         + "</table></div><div><b>Status</b><table>" + "".join(
                             f"<tr><td>{escape(k)}</td><td>{n}</td></tr>" for k, n in v["status"].items())
                         + "</table></div></div><p><b>Types</b> " + " ".join(
                             f"<span class=chip>{escape(k)} · {n}</span>" for k, n in v["types"].items()) + "</p>")
                issues = ([("error", x["path"], x["issue"]) for x in v["errors"]]
                          + [(f["level"], f["path"], f"{f['code']} {f['message']}") for f in o.get("findings", [])]
                          + [("warning", x["path"], x["issue"]) for x in v["warnings"]])
                if issues:
                    body += "<table><tr><th>Level</th><th>File</th><th>Issue</th></tr>" + "".join(
                        f"<tr><td>{escape(lv)}</td><td class=m>{escape(p_)}</td><td>{escape(msg)}</td></tr>"
                        for lv, p_, msg in issues[:200]) + "</table>"
                else:
                    body += "<p>No issues found.</p>"
                body += "</div>"
        body += ("<div class=card><div class=k>Check another bundle</div><form method=get action='/okf' class=row>"
                 "<input type=hidden name=check value=1><input name=path placeholder='Folder or .zip on this computer, "
                 "e.g. C:\\Users\\you\\Downloads\\friend-bundle.zip'><button>Check</button></form></div>")
        return page("Open Knowledge Format", body)

    @r.post("/okf/sync")
    def okf_sync():
        m = getattr(state, "okf", None)
        if m:
            m.sync_if_changed(force=True)
        else:
            import okf

            okf.Exporter(lib).sync()
        return RedirectResponse("/okf", 303)

    # ================================================================== libraries + import
    @r.get("/libraries", response_class=HTMLResponse)
    def libraries_page():
        libs = lib.libraries()
        body = ("<div class=card><div class=row><div class=k>Libraries</div><a class='chip on' href='/import'>Import a library</a></div>"
                "<div class=m>Your own knowledge base and the external libraries you have imported. Each has its own namespace, "
                "so source IDs never collide (R1.2, R3.1).</div><table>" + "".join(
                    f"<tr><td><a href='/libraries/{escape(l['namespace'])}'><b>{escape(l['name'])}</b></a> "
                    f"<span class=m>{escape(l['namespace'])} · {escape(l['kind'])}{' · ' + escape(l['owner']) if l['owner'] else ''}</span>"
                    f"<div class=m>{escape(l['description'] or '')}</div></td>"
                    f"<td class=m>{l['nsources']} sources · {l['nunreviewed']} unreviewed insights</td></tr>" for l in libs)
                + "</table></div>")
        return page("Libraries", body)

    @r.get("/libraries/{ns}", response_class=HTMLResponse)
    def library_page(ns: str):
        l = lib.library(ns)
        if not l:
            raise HTTPException(404)
        imp = (getattr(state, "imports", {}) or {}).get(l["namespace"]) if state else None
        running = imp and imp["status"] == "running"
        rep_ = (imp or {}).get("report") or l["report"] or {}
        body = (f"<div class=card><div class=k>{escape(l['kind'])} library · {escape(l['namespace'])}</div>"
                f"<h1 style='margin:4px 0'>{escape(l['name'])}</h1><div class=m>{escape(l['owner'] or '')} · added {escape(l['created'] or '')}"
                f"{' · from ' + escape(l['origin']) if l['origin'] else ''}</div><p>{escape(l['description'] or '')}</p>"
                f"<div>{l['nsources']} sources · {l['nunreviewed']} unreviewed insights · "
                f"<a href='/review?ns={escape(l['namespace'])}'>review this library</a></div></div>")
        if imp and imp["status"] != "done":
            body += f"<div class=card><div class=k>Import {escape(imp['status'])}</div><p>{escape(imp['progress'] or '')}</p></div>"
        if rep_:
            ck = rep_.get("checksums", {})
            body += (f"<div class=card><div class=k>Import report · {escape(rep_.get('imported', ''))}</div>"
                     f"<div class=m>{len(rep_.get('files', []))} files · checksums: {ck.get('verified', 0)} verified, "
                     f"{ck.get('mismatch', 0)} mismatched, {ck.get('not_listed', 0)} not listed · {rep_.get('proposals', 0)} rule proposals · "
                     f"{len(rep_.get('skipped', []))} skipped{'' if rep_.get('model_used') else ' · the local model was offline, so nothing was tidied yet: run Tidy → Re-tidy'}</div><table>"
                     "<tr><th>File</th><th>Filed as</th><th>Result</th></tr>" + "".join(
                         f"<tr><td>{escape(f_['path'])}<div class=m>{escape(f_['title'])}</div></td>"
                         f"<td>{escape(f_['kind'])}" + (f" · <a href='{watch(f_['source_id'])}'>{escape(f_['src_id'])}</a>" if f_.get("source_id") else "")
                         + f"</td><td class=m>{escape(f_['result'])} · checksum {escape(f_['checksum'])}"
                         + (f" · {f_['proposals']} proposals" if f_.get("proposals") else "") + "</td></tr>" for f_ in rep_.get("files", []))
                     + "</table>" + ("<details><summary>Skipped</summary><ul>" + "".join(
                         f"<li>{escape(x['path'])} — {escape(x['why'])}</li>" for x in rep_["skipped"]) + "</ul></details>" if rep_.get("skipped") else "")
                     + "</div>")
        ok_ = (rep_ or {}).get("okf")
        if ok_ and "conformant" in ok_:
            off = ok_.get("official") or {}
            body += (f"<div class=card><div class=k>Open Knowledge Format bundle</div><p>"
                     f"{'Conformant' if ok_['conformant'] else '<b>Not conformant</b>'} with OKF {escape(str(ok_.get('okf_version') or '?'))}"
                     f" · {ok_['concepts']} concepts · their trust: " + ", ".join(f"{escape(k)} {n}" for k, n in ok_["trust_tiers"].items())
                     + (f" · Google's validator: {off['error']} errors, {off['warning']} warnings" if isinstance(off.get("error"), int) else "")
                     + "</p><p class=m>Their verifications are kept with each source as history; here everything starts unreviewed (R7, R9.6).</p></div>")
        if l["ids"]:
            body += ("<div class=card><div class=k>ID map (R7.3)</div><table><tr><th>Their ID</th><th>Our ID</th><th>Note</th></tr>" + "".join(
                f"<tr><td>{escape(x['old_id'])}</td><td>{escape(x['new_id'] or 'unresolved')}</td><td class=m>{escape(x['note'])}</td></tr>"
                for x in l["ids"]) + "</table></div>")
        return page(l["name"], body, refresh=3 if running else 0)

    @r.get("/import", response_class=HTMLResponse)
    def import_page():
        body = """<div class=card><div class=k>Import an external library</div>
<p class=m>Upload a friend's knowledge base, an Obsidian vault or any folder of notes as a <b>.zip</b>. Every file is
read (Markdown, text, HTML, JSON, CSV, PDF), checked against any checksums it ships with, and processed against
your <a href='/rules'>house rules</a>: names, filing, tags, labels and ratings. It all arrives <b>unreviewed</b>
in its own namespace, with original paths, IDs and ratings kept as provenance. Rules and templates become
sources plus proposals you can adopt. Nothing in the archive is run.</p>
<form id=imp class=row style='flex-wrap:wrap;gap:10px;margin-top:10px'>
 <input name=name placeholder="Library name (e.g. Eve's knowledge base)" required style='flex:2 1 240px'>
 <input name=namespace placeholder='Namespace (e.g. ASTEL)' style='flex:1 1 120px'>
 <input name=owner placeholder='Owner (e.g. Eve)' style='flex:1 1 120px'>
 <input name=description placeholder='What it is' style='flex:3 1 300px'>
 <input type=file name=file accept='.zip' style='flex:2 1 260px'>
 <input name=path placeholder='…or a folder / .zip path on this computer' style='flex:2 1 260px'>
 <button>Import</button></form><p id=msg class=m></p></div>
<script>
document.getElementById('imp').onsubmit=async e=>{e.preventDefault();const f=e.target, m=document.getElementById('msg');
 const q=new URLSearchParams({name:f.name.value,namespace:f.namespace.value,owner:f.owner.value,description:f.description.value,path:f.path.value});
 const file=f.file.files[0]; if(!file&&!f.path.value){m.textContent='Choose a .zip or enter a path.';return;}
 m.textContent='Uploading…';
 const r=await fetch('/api/v1/import?'+q,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file||''});
 const d=await r.json(); if(!r.ok){m.textContent='Import failed: '+(d.detail||r.statusText);return;} location.href=d.page;};
</script>"""
        return page("Import", body)

    # ================================================================== tidy
    def run_bg(what, fn):
        def go():
            try:
                task["result"] = fn()
            except Exception as ex:  # noqa: BLE001
                task["result"] = f"failed: {ex}"
            finally:
                task.update(running=False, status="")

        if task["running"]:
            return
        task.update(running=True, what=what, status="starting", result="")
        threading.Thread(target=go, daemon=True).start()

    def status(msg):
        task["status"] = msg

    @r.get("/library/tidy", response_class=HTMLResponse)
    def tidy():
        body = ""
        if task["running"]:
            body += (f"<div class=card><div class=k>Working…</div><p>{escape(task['what'])}: "
                     f"{escape(task['status'])}</p><div class=m>This page refreshes every 3 seconds.</div></div>")
        elif task["result"]:
            body += f"<div class=card><div class=k>Last run · {escape(task['what'])}</div><p>{escape(str(task['result']))}</p></div>"
        body += ("<div class=card><div class=k>Clean up with the local model</div>"
                 "<p class=m><b>Re-file</b> rebuilds the library from every stored source using its saved tidy result (fast). "
                 "<b>Re-tidy</b> runs the tidy pass again on every source — picks up new tags and the current library (slow, "
                 "~30 s per source). <b>Suggest fixes</b> reviews the whole library and lists changes below for you to approve. "
                 "Your notes, descriptions, aliases, manual tags and own entries are always kept.</p>"
                 "<div class=row style='justify-content:flex-start;gap:8px'>"
                 + _post_btn("/library/tidy/rebuild", "Re-file", "g") + _post_btn("/library/tidy/retidy", "Re-tidy with model", "")
                 + _post_btn("/library/tidy/ai", "Suggest fixes", "g")
                 + f"<span class=m>model: {escape(llm.DEFAULT_MODEL)}</span></div></div>")

        sug = [x for x in lib.suggestions() if x["kind"] != "rule"]   # rule proposals live on the Review page
        if sug:
            label = {"merge": "Merge", "rename": "Rename", "kind": "Change kind", "parent": "Set parent",
                     "remove": "Remove", "tag": "Add tag"}

            def desc(s):
                a, b = f"<b>{escape(s['a'])}</b>", f"<b>{escape(s['b'] or '')}</b>"
                return {"merge": f"{a} → into {b}", "rename": f"{a} → {b}", "kind": f"{a} is a {b}",
                        "parent": f"{a} is part of {b}", "tag": f"{a} → tag {b}"}.get(s["kind"], a)
            body += (f"<div class=card><div class=row><div class=k>{len(sug)} suggested fixes</div>"
                     + _post_btn("/library/tidy/suggestions/all", "Approve all", "s") + " "
                     + _post_btn("/library/tidy/suggestions/none", "Reject all", "s g")
                     + "</div><table>" + "".join(
                         f"<tr><td class=m style='width:110px'>{label.get(s['kind'], s['kind'])}</td><td>{desc(s)}"
                         f"<div class=m>{escape(s['reason'] or '')}</div></td><td style='white-space:nowrap'>"
                         + _post_btn(f"/library/tidy/suggestion/{s['id']}/yes", "✓", "s") + " "
                         + _post_btn(f"/library/tidy/suggestion/{s['id']}/no", "✕", "s g") + "</td></tr>"
                         for s in sug) + "</table></div>")

        dups = lib.duplicates()
        if dups:
            body += (f"<div class=card><div class=k>Possible duplicates ({len(dups)})</div>"
                     "<div class=m>Spelling-based guesses. Merge keeps everything from both.</div><table>" + "".join(
                         f"<tr><td><a href='/library/e/{d['dup']['slug']}'>{escape(d['dup']['name'])}</a> "
                         f"<span class=m>{d['dup']['kind']} · {d['dup']['n']}</span> &nbsp;↔&nbsp; "
                         f"<a href='/library/e/{d['keep']['slug']}'>{escape(d['keep']['name'])}</a> "
                         f"<span class=m>{d['keep']['kind']} · {d['keep']['n']}</span></td><td style='white-space:nowrap'>"
                         + _post_btn("/library/tidy/merge", f"keep {escape(d['keep']['name'][:18])}", "s",
                                     {"a": d["dup"]["slug"], "b": d["keep"]["slug"]}) + " "
                         + _post_btn("/library/tidy/merge", f"keep {escape(d['dup']['name'][:18])}", "s g",
                                     {"a": d["keep"]["slug"], "b": d["dup"]["slug"]}) + " "
                         + _post_btn("/library/tidy/dismiss", "different", "s g",
                                     {"a": d["dup"]["slug"], "b": d["keep"]["slug"]})
                         + "</td></tr>" for d in dups) + "</table></div>")

        orph = lib.orphans()
        if orph:
            body += (f"<div class=card><div class=row><div class=k>Empty entries ({len(orph)})</div>"
                     + _post_btn("/library/tidy/orphans", "Delete all empty", "s")
                     + "</div><div class=m>Auto-created, no longer linked to any source, no notes.</div><div>"
                     + "".join(f"<a class=chip href='/library/e/{o['slug']}'>{escape(o['name'])}</a>" for o in orph)
                     + "</div></div>")
        bl = lib.blocked()
        if bl:
            body += (f"<div class=card><div class=k>Blocked ({len(bl)})</div><div class=m>Removed by you — never re-added "
                     "from sources.</div><table>" + "".join(
                         f"<tr><td>{escape(b['name'])}<div class=m>{escape(b['spellings'])}</div></td><td>"
                         + _post_btn("/library/tidy/unblock", "unblock", "s g", {"name": b["name"]}) + "</td></tr>"
                         for b in bl) + "</table></div>")
        return page("Tidy", body, refresh=3 if task["running"] else 0)

    def _need_model():
        ok, msg = llm.ollama_available(llm.DEFAULT_MODEL)
        return None if ok else msg

    @r.post("/library/tidy/rebuild")
    def do_rebuild():
        run_bg("Re-file", lambda: "done: {sources} source(s) re-filed, {purged} untouched old entries replaced, "
               "{orphans_removed} empty entries removed".format(**libmod.rebuild(lib, False, status)))
        return RedirectResponse("/library/tidy", 303)

    @r.post("/library/tidy/retidy")
    def do_retidy():
        err = _need_model()
        if err:
            task.update(what="Re-tidy", result=f"failed: {err}")
        else:
            run_bg("Re-tidy", lambda: "done: {sources} source(s) re-tidied, {purged} untouched old entries replaced, "
                   "{orphans_removed} empty entries removed".format(**libmod.rebuild(lib, True, status)))
        return RedirectResponse("/library/tidy", 303)

    @r.post("/library/tidy/ai")
    def do_ai():
        err = _need_model()
        if err:
            task.update(what="Suggest fixes", result=f"failed: {err}")
        else:
            run_bg("Suggest fixes", lambda: f"done: {llm.ai_tidy(lib, llm.DEFAULT_MODEL, status)} suggestion(s)")
        return RedirectResponse("/library/tidy", 303)

    @r.post("/library/tidy/suggestion/{sid}/{ans}")
    def do_suggestion(sid: int, ans: str, request: Request):
        lib.resolve_suggestion(sid, ans == "yes")
        return RedirectResponse(_back(request, "/library/tidy"), 303)

    @r.post("/library/tidy/suggestions/{ans}")
    def do_all(ans: str):
        order = {"merge": 0, "rename": 1, "remove": 2, "kind": 3, "parent": 4, "tag": 5}
        for s in sorted((x for x in lib.suggestions() if x["kind"] != "rule"), key=lambda s: (order.get(s["kind"], 9), s["id"])):
            lib.resolve_suggestion(s["id"], ans == "all")
        return RedirectResponse("/library/tidy", 303)

    @r.post("/library/tidy/merge")
    async def do_merge(request: Request):
        f = await form(request)
        try:
            lib.merge(f["a"], f["b"])
        except KeyError:
            pass
        return RedirectResponse("/library/tidy", 303)

    @r.post("/library/tidy/dismiss")
    async def do_dismiss(request: Request):
        f = await form(request)
        try:
            lib.dismiss(f["a"], f["b"])
        except KeyError:
            pass
        return RedirectResponse("/library/tidy", 303)

    @r.post("/library/tidy/unblock")
    async def do_unblock(request: Request):
        lib.unblock((await form(request)).get("name", ""))
        return RedirectResponse("/library/tidy", 303)

    @r.post("/library/tidy/orphans")
    def do_orphans():
        lib.delete_orphans()
        return RedirectResponse("/library/tidy", 303)

    return r
