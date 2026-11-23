"""
ui_kingdom — the town's pages: the map, a list of places (for keyboards, screen readers and browsers without WebGL),
building interiors, people, handoffs, and the calendars behind the two clocks.
"""
import os
from html import escape
from pathlib import Path
from urllib.parse import quote

import kingdom
import projects
from library import OWNER

HERE = Path(__file__).resolve().parent
KINGDOM_URL = os.environ.get("KB_KINGDOM_URL") or "http://localhost:8100"  # the new town, as your browser reaches it


def _status_badge(s: str) -> str:
    cls = {"active": "accepted", "maintained": "accepted", "doing": "unreviewed", "todo": "conf", "blocked": "disputed",
           "done": "accepted", "open": "unreviewed", "accepted": "accepted"}.get(s, "conf")
    return f"<span class='st {cls}'>{escape(s)}</span>"


def task_rows(ts: list[dict], back: str) -> str:
    from ui import _post_btn

    if not ts:
        return "<p class=empty-room>No actions yet.</p>"
    out = "<table><tr><th>Outcome</th><th>Owner</th><th>Done when</th><th>Status</th></tr>"
    for t in ts:
        nxt = {"todo": "doing", "doing": "done", "blocked": "doing"}.get(t["status"])
        acts = (_post_btn(f"/kingdom/task/{t['id']}/{nxt}?back={quote(back)}", "Start" if nxt == "doing" else "Done", "s g")
                if nxt else "")
        if t["status"] in ("todo", "doing"):
            acts += " " + _post_btn(f"/kingdom/task/{t['id']}/blocked?back={quote(back)}", "Blocked", "s g")
        out += (f"<tr><td>{escape(t['outcome'])}<div class=m>{escape(t.get('project') or '')}"
                f"{' · from ' + escape(t['source']) if t.get('source') else ''}</div></td><td>{escape(t['owner'])}</td>"
                f"<td class=m>{escape(t['done_when'] or '')}</td><td>{_status_badge(t['status'])} {acts}</td></tr>")
    return out + "</table>"


def task_form(project_slug: str, back: str) -> str:
    return (f"<details style='margin-top:8px'><summary>Add an action</summary>"
            f"<form method=post action='/kingdom/project/{project_slug}/task?back={quote(back)}' style='margin-top:8px'>"
            f"<input name=outcome placeholder='Outcome, e.g. Establish a monitoring pilot across three client sites' required>"
            f"<div class=row style='margin-top:6px'><input name=owner placeholder='Owner (a person or an agent)' value='{OWNER}'>"
            f"<input name=done_when placeholder='Done when…'><button>Add action</button></div></form></details>")


def add_routes(r, lib, state, form):
    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, RedirectResponse

    from ui import _post_btn, page

    @r.get("/kingdom", response_class=HTMLResponse)
    def kingdom_map():
        # The town now lives in its own app (the Kingdom app). Every "back to the square" link lands there.
        return RedirectResponse(KINGDOM_URL, 307)

    @r.get("/kingdom/old", response_class=HTMLResponse)
    def kingdom_old_map():
        """The first town map, kept for reference until the new Kingdom covers every place."""
        return (HERE / "static" / "kingdom.html").read_text(encoding="utf-8")

    @r.get("/kingdom/places", response_class=HTMLResponse)
    def places_list():
        s = kingdom.state(lib)
        body = ("<div class=room-head><div><h1>The town</h1><p>Every place on the map, what's happening there, and who's in it.</p></div>"
                "<a class=back href='/kingdom'>Back to the map</a></div><div class=doors>")
        for p in s["places"]:
            body += (f"<a class=door-card href='{p['enter']}'><b>{escape(p['name'])}"
                     + (f" <span class='st disputed'>{p['attention']} waiting</span>" if p["attention"] else "") + "</b>"
                     f"<span>{escape(p['feel'])}</span>"
                     + "".join(f"<div class=m>{escape(x)}</div>" for x in p["lines"])
                     + ("" if p["live"] else "<div class=m>Not connected yet</div>")
                     + (f"<div class=m>Here now: {escape(', '.join(p['agents']))}</div>" if p["agents"] else "") + "</a>")
        body += "</div>"
        return page("The town", body, place="town")

    def room_head(p: dict) -> str:
        return (f"<div class=room-head><div><h1>{escape(p['name'])}</h1><p>{escape(p['feel'])}</p></div>"
                f"<a class=back href='/kingdom'>Back to the square</a></div>")

    @r.get("/kingdom/place/{pid}", response_class=HTMLResponse)
    def place_page(pid: str):
        if pid == "library":
            return RedirectResponse("/library", 303)
        p = kingdom.PLACE.get(pid)
        if not p:
            raise HTTPException(404)
        st = kingdom.state(lib)
        sp = next(x for x in st["places"] if x["id"] == pid)
        body = room_head(p)
        here = [a for a in st["agents"] if a["place"] == pid]
        if pid == "office":
            body += office_room(st)
        elif pid == "home":
            body += home_room(st, sp)
        elif pid == "postoffice":
            body += postoffice_room(st)
        else:
            if p.get("private"):
                body += ("<div class='card' style='border-left:3px solid var(--verdigris)'><h2>Private office</h2><p>Casework stays in "
                         "its authorised workspace. The town only shows that this office needs attention; no participant "
                         "names, plans or notes are copied here, and agents working here only see what that workspace "
                         "gives them.</p></div>")
            body += bays(lib, sp["projects"], st, pid)
            if not sp["live"] or p.get("needs"):
                body += ("<div class=connect><h2>Not connected yet</h2><p>"
                         + escape(p["name"]) + " lights up when it has " + " and ".join(escape(n) for n in p.get("needs", []))
                         + ".</p><p class=m>Until then you can file projects here (set a project's building on its page), "
                         "give agents a desk here (<code>kb_set_status(office=\"" + pid + "\")</code>) and hand work in and out.</p></div>"
                         if p.get("needs") else "")
        body += people_card(here, pid)
        body += handoff_card(st, pid)
        body += ("<div class=card><h2>What you can do here</h2><ul>" + "".join(f"<li>{escape(d)}</li>" for d in p["does"]) + "</ul></div>")
        return page(p["name"], body, place=pid)

    def bays(lib, prj: list[dict], st, pid) -> str:
        if not prj:
            return "<div class=card><h2>Project bays</h2><p class=empty-room>No projects in this building yet.</p></div>"
        top = [x for x in prj]
        out = "<div class=bays>"
        for x in top:
            pj = projects.get(lib, x["slug"])
            if not pj:
                continue
            ts = kingdom.tasks(lib, x["slug"], open_only=True)
            hs = [h for h in st["couriers"] if h["kind"] == "handoff" and x["name"].lower() in (h["what"] + " ").lower()]
            lit = bool(ts) or any(a["place"] == pid and x["name"].lower() in (a["task"] or "").lower() for a in st["agents"])
            dec = [d for d in pj["decisions"] if d["status"] in ("accepted", "proposed")][-2:]
            out += (f"<section class='bay{' lit' if lit else ''}'><h3><a href='/library/e/{x['slug']}'>{escape(x['name'])}</a></h3>"
                    f"<div class=sub>{_status_badge(x['status'])}{' version ' + escape(x['version']) if x['version'] else ''}"
                    f"{' · ' + str(len(pj['components'])) + ' components' if pj['components'] else ''}</div>"
                    f"<div class=m>{escape((pj['description'] or '')[:180])}</div>")
            if ts:
                out += "<h4>Underway</h4><ul>" + "".join(f"<li>{escape(t['outcome'])} <small class=m>{escape(t['owner'])} · {escape(t['status'])}</small></li>" for t in ts[:4]) + "</ul>"
            if dec:
                out += "<h4>Latest decisions</h4><ul>" + "".join(
                    f"<li><a href='/library/e/{x['slug']}#d{d['number']}'>{d['id_label']}</a> {escape(d['title'])}"
                    + (" <span class='st unreviewed'>proposed</span>" if d["status"] == "proposed" else "") + "</li>" for d in dec) + "</ul>"
            if hs:
                out += "<h4>Handoffs</h4><ul>" + "".join(f"<li><a href='{h['link']}'>{escape(h['what'][:80])}</a></li>" for h in hs[:3]) + "</ul>"
            out += task_form(x["slug"], f"/kingdom/place/{pid}") + "</section>"
        return out + "</div><div style='height:16px'></div>"

    def people_card(here, pid) -> str:
        if not here:
            return ("<div class=card><h2>Who's here</h2><p class=empty-room>Nobody at a desk here right now. Agents take a desk "
                    f"with <code>kb_set_status(office=\"{pid}\", task=…)</code>.</p></div>")
        return ("<div class=card><h2>Who's here</h2><table>" + "".join(
            f"<tr><td><a href='/kingdom/agent/{quote(a['name'])}'><b>{escape(a['name'])}</b></a><div class=m>{escape(a['role'] or '')}</div></td>"
            f"<td>{escape(a['task'] or '')}<div class=m>{'next update ' + escape(a['next_update']) if a['next_update'] else ''}"
            f"{' · waiting on ' + escape(a['waiting_on']) if a['waiting_on'] else ''}</div></td></tr>" for a in here) + "</table></div>")

    def handoff_card(st, pid) -> str:
        hs = [h for h in st["couriers"] if h["kind"] == "handoff" and pid in (h["from"], h["to"])]
        out = "<div class=card><h2>Handoffs in and out</h2>"
        out += ("<table>" + "".join(
            f"<tr><td><a href='{h['link']}'>{escape(h['what'])}</a><div class=m>{escape(h['who'])} → {escape(h['owner'])}</div></td>"
            f"<td class=m>{kingdom.PLACE.get(h['from'], {}).get('name', '')} → {kingdom.PLACE.get(h['to'], {}).get('name', '')}</td>"
            f"<td>{_status_badge(h['status'])}{' <span class=\"st disputed\">overdue</span>' if h['overdue'] else ''}</td></tr>" for h in hs)
                + "</table>") if hs else "<p class=empty-room>Nothing travelling to or from here.</p>"
        out += (f"<details><summary>Hand something over</summary><form method=post action='/kingdom/handoff/new' style='margin-top:8px'>"
                f"<input type=hidden name=from_place value='{pid}'><div class=row><input name=to placeholder='To (agent or person)' required>"
                f"<select name=to_place>" + "".join(f"<option value='{p['id']}'>{escape(p['name'])}</option>" for p in kingdom.PLACES) + "</select></div>"
                f"<input name=what placeholder='What you need or are delivering' required style='margin-top:6px'>"
                f"<div class=row style='margin-top:6px'><input name=due placeholder='Due (YYYY-MM-DD, optional)'><button>Send courier</button></div></form></details>")
        return out + "</div>"

    def office_room(st) -> str:
        notes = st["notes"]
        if not notes:
            return "<div class=card><h2>Notes on the door</h2><p class=empty-room>Nothing is waiting on you.</p></div>"
        return ("<div class=card><h2>Notes on the door</h2><table>" + "".join(
            f"<tr class='{'waiting-note' if n.get('overdue') else ''}'><td><a href='{escape(n['link'])}'>{escape(n['title'])}</a>"
            f"<div class=m>from {escape(n['from'])}{' · ' + escape(n['at']) if n['at'] else ''}</div></td>"
            f"<td class=m>{escape(n['kind'])}</td></tr>" for n in notes) + "</table></div>")

    def home_room(st, sp) -> str:
        c = st["clocks"]
        fs = kingdom.feeds(lib)
        out = "<div class=cols><div class=card><h2>Today, personal</h2>"
        out += ("<ol class=day>" + "".join(f"<li class=personal><time>{'All day' if e['all_day'] else escape(e['start'][11:]) + '–' + escape(e['end'][11:])}</time>"
                                           f"<span>{escape(e['title'])}</span></li>" for e in c["personal"]) + "</ol>") if c["personal"] else "<p class=empty-room>Nothing on.</p>"
        out += "</div><div class=card><h2>Today, work</h2>"
        out += ("<ol class=day>" + "".join(f"<li class='{'personal private' if e['private'] else 'work'}'><time>{'All day' if e['all_day'] else escape(e['start'][11:]) + '–' + escape(e['end'][11:])}</time>"
                                           f"<span>{escape(e['title'])}</span></li>" for e in c["work"]) + "</ol>") if c["work"] else "<p class=empty-room>Nothing on.</p>"
        out += "</div></div>"
        out += bays(lib, sp["projects"], st, "home")
        rows = "".join(
            f"<tr><td><b>{escape(f['name'])}</b><div class=m>{escape(f['clock'])} clock · {f['nevents']} events"
            f"{' · personal events show as Busy at work' if f['clock'] == 'personal' and f['busy_on_work'] else ''}</div>"
            f"{'<div style=\"color:var(--seal)\">' + escape(f['error']) + '</div>' if f['error'] else ''}</td>"
            f"<td class=m>{escape(f['last_fetch'])}</td><td>{_post_btn(f'/kingdom/calendars/{f[chr(105) + chr(100)]}/delete', 'Remove', 's g')}</td></tr>"
            for f in fs)
        out += (f"<div class=card id=calendars><h2>Calendars behind the clocks</h2>"
                f"{'<table>' + rows + '</table>' if rows else '<p class=empty-room>No calendars yet.</p>'}"
                "<form method=post action='/kingdom/calendars' style='margin-top:10px'><div class=row>"
                "<select name=clock style='max-width:150px'><option value=work>Work clock</option><option value=personal>Personal clock</option></select>"
                "<input name=name placeholder='Name, e.g. Work Outlook'></div>"
                "<input name=url placeholder='Calendar ICS address (https://… or webcal://…)' required style='margin-top:6px'>"
                "<div class=row style='margin-top:6px'><label class=m style='flex:1'><input type=checkbox name=busy checked style='width:auto'> "
                "Personal events reserve the time on the work clock (shown only as Busy)</label><button>Add calendar</button></div></form>"
                "<details style='margin-top:10px'><summary>Where to find the ICS address</summary><ul class=m>"
                "<li><b>Outlook / Microsoft 365:</b> Outlook on the web → Settings → Calendar → Shared calendars → Publish a calendar → "
                "choose the calendar and 'Can view all details' (or 'Can view titles and locations') → Publish → copy the ICS link.</li>"
                "<li><b>Google Calendar:</b> Settings → your calendar → Integrate calendar → Secret address in iCal format.</li>"
                "<li>The address is kept in the knowledge base's database only. It's refreshed every 15 minutes.</li></ul></details>"
                + _post_btn("/kingdom/calendars/refresh", "Refresh now", "s g") + "</div>")
        return out

    def postoffice_room(st) -> str:
        people = [a for a in st["agents"]]
        out = ("<div class=connect><h2>Not connected yet</h2><p>The Post Office opens your real threads once Microsoft 365 "
               "(Outlook, Teams) or Gmail is connected to the knowledge base. A character's words will always come from the actual "
               "thread, and drafts stay visibly yours until you send them.</p><p class=m>That connection needs an app registration "
               "with read-only mail access in your Microsoft 365 and Google accounts; it's the next step for this building.</p></div>")
        out += ("<div class=card><h2>People in town</h2>" + ("<table>" + "".join(
            f"<tr><td><a href='/kingdom/agent/{quote(a['name'])}'>{escape(a['name'])}</a></td><td class=m>{escape(a['role'] or a['kind'] or '')}</td>"
            f"<td class=m>{escape(kingdom.PLACE.get(a['place'], {}).get('name', ''))}</td></tr>" for a in people) + "</table>"
            if people else "<p class=empty-room>No one has checked in yet.</p>") + "</div>")
        return out

    @r.get("/kingdom/agent/{name}", response_class=HTMLResponse)
    def agent_page(name: str):
        ags = {a["name"]: a for a in kingdom.agents(lib, minutes=60 * 24 * 365)}
        a = ags.get(name)
        if not a:
            raise HTTPException(404)
        hs = kingdom.handoffs(lib, False, name)
        with lib._db() as c:
            log = [dict(x) for x in c.execute("SELECT * FROM agent_log WHERE name=? ORDER BY id DESC LIMIT 40", (name,))]
        body = (f"<div class=room-head><div><h1>{escape(a['name'])}</h1><p>{escape(a['role'] or a['kind'] or 'agent')} · desk at "
                f"<a href='/kingdom/place/{a['place']}'>{escape(kingdom.PLACE.get(a['place'], {}).get('name', ''))}</a></p></div>"
                f"<a class=back href='/kingdom'>Back to the square</a></div>"
                f"<div class=card><h2>Now</h2><p><b>{escape(a['task'] or 'No current task')}</b></p>"
                f"<p class=m>{'Next update ' + escape(a['next_update']) + ' · ' if a['next_update'] else ''}"
                f"{'Waiting on ' + escape(a['waiting_on']) + ' · ' if a['waiting_on'] else ''}last seen {escape(a['updated'])}</p></div>")
        body += ("<div class=card><h2>Handoffs</h2>" + ("<table>" + "".join(
            f"<tr><td><a href='/kingdom/handoff/{h['id']}'>{escape(h['what'])}</a><div class=m>{escape(h['from_name'])} → {escape(h['to_name'])}</div></td>"
            f"<td>{_status_badge(h['status'])}</td></tr>" for h in hs) + "</table>" if hs else "<p class=empty-room>None.</p>") + "</div>")
        body += ("<div class=card><h2>Recently</h2><table>" + "".join(
            f"<tr><td class=m style='white-space:nowrap'>{escape(x['created'])}</td><td>{escape(x['text'])}</td></tr>" for x in log) + "</table></div>")
        return page(a["name"], body, place="town")

    @r.get("/kingdom/handoff/{hid}", response_class=HTMLResponse)
    def handoff_page(hid: int):
        h = next((x for x in kingdom.handoffs(lib, False) if x["id"] == hid), None)
        if not h:
            raise HTTPException(404)
        fp, tp = kingdom.PLACE.get(h["from_place"], {}), kingdom.PLACE.get(h["to_place"], {})
        body = (f"<div class=room-head><div><h1>{escape(h['what'])}</h1><p>{escape(h['from_name'])} at {escape(fp.get('name', ''))} → "
                f"{escape(h['to_name'])} at {escape(tp.get('name', ''))}</p></div><a class=back href='/kingdom'>Back to the square</a></div>"
                f"<div class=card><table><tr><th>Asked by</th><td>{escape(h['from_name'])}</td></tr><tr><th>Owns the response</th><td>{escape(h['owner'])}</td></tr>"
                f"<tr><th>Due</th><td>{escape(h['due'] or 'no date')}{' <span class=\"st disputed\">overdue</span>' if h['overdue'] else ''}</td></tr>"
                f"<tr><th>Status</th><td>{_status_badge(h['status'])}</td></tr></table></div>"
                "<div class=card><h2>Conversation</h2><table>" + "".join(
                    f"<tr><td style='width:160px'><b>{escape(m['by'])}</b><div class=m>{escape(m['at'])}</div></td><td>{escape(m['text'])}</td></tr>"
                    for m in h["thread"]) + "</table>"
                f"<form method=post action='/kingdom/handoff/{hid}' style='margin-top:10px'><textarea name=message placeholder='Reply'></textarea>"
                "<div class=row style='margin-top:6px'><select name=status style='max-width:220px'><option value=''>Keep it open</option>"
                "<option value=accepted>Accept it</option><option value=done>Mark done</option><option value=cancelled>Cancel</option></select>"
                "<button>Send</button></div></form></div>")
        return page("Handoff", body, place="town")

    @r.post("/kingdom/handoff/new")
    async def handoff_new(request: Request):
        f = await form(request)
        hid = kingdom.add_handoff(lib, OWNER, f.get("to", ""), f.get("what", ""), f.get("to", ""), f.get("due", ""), "",
                                  f.get("from_place", ""), f.get("to_place", ""))
        return RedirectResponse(f"/kingdom/handoff/{hid}", 303)

    @r.post("/kingdom/handoff/{hid}")
    async def handoff_reply(hid: int, request: Request):
        f = await form(request)
        kingdom.update_handoff(lib, hid, f.get("status") or None, f.get("message", ""), OWNER)
        return RedirectResponse(f"/kingdom/handoff/{hid}", 303)

    @r.post("/kingdom/project/{slug}/task")
    async def task_new(slug: str, request: Request, back: str = ""):
        f = await form(request)
        kingdom.add_task(lib, slug, f.get("outcome", ""), f.get("owner", OWNER), f.get("done_when", ""), "", "you")
        return RedirectResponse(back or f"/library/e/{slug}#actions", 303)

    @r.post("/kingdom/task/{tid}/{status}")
    def task_status(tid: int, status: str, back: str = "/kingdom"):
        kingdom.update_task(lib, tid, status)
        return RedirectResponse(back, 303)

    @r.post("/kingdom/calendars")
    async def cal_add(request: Request):
        f = await form(request)
        try:
            kingdom.add_feed(lib, f.get("clock", "work"), f.get("name", ""), f.get("url", ""), "busy" in f)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        return RedirectResponse("/kingdom/place/home#calendars", 303)

    @r.post("/kingdom/calendars/{fid}/delete")
    def cal_del(fid: int):
        kingdom.delete_feed(lib, fid)
        return RedirectResponse("/kingdom/place/home#calendars", 303)

    @r.post("/kingdom/calendars/refresh")
    def cal_refresh():
        for f in kingdom.feeds(lib):
            kingdom.fetch_feed(lib, f["id"])
        return RedirectResponse("/kingdom/place/home#calendars", 303)
