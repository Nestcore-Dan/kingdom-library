"""
kingdom — the town around the library: places (your businesses, home, the library, the post office), the people
and agents working in them, handoffs between them, project actions, and your two clocks (work and personal).

Everything shown comes from real records: agents report their task, handoffs are created by agents (or you),
actions belong to projects, calendars come from ICS feeds you paste in (Outlook and Google both publish one).
Places whose data isn't connected yet say what they need instead of showing anything made up.
"""
import datetime as dt
import json
import os
import re
import threading
import time
import urllib.request

from library import OWNER, now

SCHEMA = """
CREATE TABLE IF NOT EXISTS handoffs(
  id INTEGER PRIMARY KEY, from_name TEXT, to_name TEXT, from_place TEXT, to_place TEXT, what TEXT, owner TEXT,
  due TEXT DEFAULT '', status TEXT DEFAULT 'open', project TEXT DEFAULT '', thread TEXT DEFAULT '[]',
  created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS project_tasks(
  id INTEGER PRIMARY KEY, entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE, outcome TEXT, owner TEXT,
  done_when TEXT DEFAULT '', status TEXT DEFAULT 'todo', due TEXT DEFAULT '', source TEXT DEFAULT '',
  created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS calendar_feeds(
  id INTEGER PRIMARY KEY, clock TEXT, name TEXT, url TEXT, busy_on_work INTEGER DEFAULT 1, last_fetch TEXT DEFAULT '',
  error TEXT DEFAULT '', created TEXT);
CREATE TABLE IF NOT EXISTS calendar_events(
  feed_id INTEGER REFERENCES calendar_feeds(id) ON DELETE CASCADE, uid TEXT, start TEXT, end TEXT, all_day INTEGER,
  title TEXT, location TEXT, PRIMARY KEY(feed_id, uid, start));
"""
AGENT_COLS = [("office", "TEXT DEFAULT ''"), ("task", "TEXT DEFAULT ''"), ("next_update", "TEXT DEFAULT ''"),
              ("waiting_on", "TEXT DEFAULT ''"), ("kind", "TEXT DEFAULT 'agent'")]
TASK_STATES = ["todo", "doing", "blocked", "done", "dropped"]
HANDOFF_STATES = ["open", "accepted", "done", "cancelled"]

# The town. `x, z` are tile positions on the map (the square is at 0,0). `needs` lists what a place is waiting
# for before it can show live work; `office` is the value projects and agents use to belong to a place.
PLACES = [
    {"id": "library", "name": "The Library", "x": 0, "z": -14, "feel": "A central reading room with wings, shelves and private archives",
     "does": ["Browse libraries and sub-libraries by company or project", "Open a document at its source and see its latest version",
              "Tell an agent which materials it can use"], "enter": "/library", "live": True},
    {"id": "studio", "name": "Software Studio", "x": 15, "z": -4, "feel": "A converted factory with project bays, a test lab and a demo theatre",
     "does": ["Watch a build take shape", "See where one agent is waiting on another", "Walk into a demo with the team that built it"],
     "enter": "/kingdom/place/studio", "live": True},
    {"id": "business", "name": "Your business", "x": 13, "z": 12, "feel": "A service operations floor with a live wall of sites and systems",
     "does": ["See which agents are triaging tickets", "Check what changed at a client site", "Take over an escalation"],
     "enter": "/kingdom/place/business", "needs": ["a ticketing tool (not chosen yet)", "site monitoring"]},
    {"id": "consulting", "name": "Consulting", "x": -2, "z": 16, "feel": "A consulting studio with project boards and a workshop for site plans",
     "does": ["Review a proposal", "Compare options for a client", "Ask an agent to turn discovery notes into a scope of work"],
     "enter": "/kingdom/place/consulting", "needs": ["proposals and discovery notes (Microsoft 365 or Google Drive)"]},
    {"id": "casework", "name": "Casework office", "x": -15, "z": 8, "feel": "A quiet office with private meeting rooms and a casework desk",
     "does": ["Review follow-ups", "Prepare handovers", "Meet with a coordination agent"],
     "enter": "/kingdom/place/casework", "private": True,
     "needs": ["an authorised casework workspace - client details never come into the town"]},
    {"id": "home", "name": "Home", "x": -16, "z": -7, "feel": "A warm, quieter place with a kitchen calendar and a study",
     "does": ["Check personal plans", "Pick up creative projects", "Revisit conversations"],
     "enter": "/kingdom/place/home", "live": True},
    {"id": "postoffice", "name": "The Post Office", "x": -8, "z": -20, "feel": "A place to find people and pick up conversations",
     "does": ["Open an original thread from a person's character", "Hear a knock when there's a new message",
              "Keep drafts visibly yours until you send them"],
     "enter": "/kingdom/place/postoffice", "needs": ["mail and messages (Microsoft 365 / Outlook or Gmail)"]},
    {"id": "office", "name": "Your office", "x": 6, "z": 6, "feel": "Your desk on the square, where notes are left for you",
     "does": ["See every decision waiting on you", "Answer agents that are waiting", "Approve skills and finds"],
     "enter": "/kingdom/place/office", "live": True},
]
PLACE = {p["id"]: p for p in PLACES}
# Library-internal locations (the reading room) all count as being in the Library.
LIB_LOCS = ("entrance", "catalogue", "desk", "new-arrivals", "media", "entry:", "shelf:", "source:")


def setup(lib):
    with lib._db() as c:
        c.executescript(SCHEMA)
        cols = [r[1] for r in c.execute("PRAGMA table_info(agents)")]
        for col, decl in AGENT_COLS:
            if col not in cols:
                c.execute(f"ALTER TABLE agents ADD COLUMN {col} {decl}")
        pcols = [r[1] for r in c.execute("PRAGMA table_info(project_info)")]
        if "office" not in pcols:
            c.execute("ALTER TABLE project_info ADD COLUMN office TEXT DEFAULT ''")


DEFAULT_OFFICES = {}


def default_offices(lib):
    """Once: put the starting projects in their buildings (only where you haven't chosen one)."""
    with lib._db() as c:
        if c.execute("SELECT 1 FROM meta WHERE k='kingdom_offices_v1'").fetchone():
            return
        for name, office in DEFAULT_OFFICES.items():
            eid = lib._find(c, name)
            if eid:
                c.execute("INSERT OR IGNORE INTO project_info(entity_id, updated) VALUES(?,?)", (eid, now()))
                c.execute("UPDATE project_info SET office=? WHERE entity_id=? AND IFNULL(office,'')=''", (office, eid))
        c.execute("INSERT INTO meta VALUES('kingdom_offices_v1','1')")


def place_of(agent: dict) -> str:
    office = (agent.get("office") or "").strip().lower()
    loc = (agent.get("location") or "").lower()
    if loc.startswith("place:"):
        return loc.split(":", 1)[1] if loc.split(":", 1)[1] in PLACE else "library"
    if loc and (loc in LIB_LOCS or loc.startswith(LIB_LOCS)):
        return "library"
    return office if office in PLACE else "library"


# ================================================================== agents
def set_status(lib, name: str, task: str | None = None, next_update: str | None = None, office: str | None = None,
               waiting_on: str | None = None, role: str | None = None, kind: str | None = None, location: str | None = None):
    """What an agent is doing right now (shown on its character in the town)."""
    if office and not location:
        location = f"place:{office}"      # taking a desk walks you there; library tools walk you back to the library
    lib.agent_update(name, location, task, role)
    with lib._lock, lib._db() as c:
        for k, v in (("task", task), ("next_update", next_update), ("office", office), ("waiting_on", waiting_on),
                     ("kind", kind)):
            if v is not None:
                c.execute(f"UPDATE agents SET {k}=? WHERE name=?", (v.strip()[:300], name.strip()[:40]))


def agents(lib, minutes: int = 240) -> list[dict]:
    cutoff = (dt.datetime.now() - dt.timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    with lib._db() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM agents WHERE ((present=1 AND updated>=?) OR office!='') AND name!='Visitor' ORDER BY name",
            (cutoff,))]   # "Visitor" is you, walking the reading room
    for r in rows:
        r["place"] = place_of(r)
        r["active"] = bool(r["present"]) and r["updated"] >= cutoff
        r["task"] = r.get("task") or r.get("activity") or ""
    return rows


# ================================================================== handoffs
def add_handoff(lib, from_name: str, to_name: str, what: str, owner: str = "", due: str = "", project: str = "",
                from_place: str = "", to_place: str = "") -> int:
    if not what.strip():
        raise ValueError("what is required")
    with lib._db() as c:
        def where(n, p):
            if p in PLACE:
                return p
            if n.strip().lower() in (OWNER.lower(), "you", "me"):
                return "office"
            r = c.execute("SELECT * FROM agents WHERE name=?", (n.strip(),)).fetchone()
            return place_of(dict(r)) if r else "library"
        fp, tp = where(from_name, from_place), where(to_name, to_place)
        cur = c.execute("INSERT INTO handoffs(from_name,to_name,from_place,to_place,what,owner,due,project,thread,created,updated)"
                        " VALUES(?,?,?,?,?,?,?,?,?,?,?)", (from_name.strip(), to_name.strip(), fp, tp, what.strip(),
                                                         (owner or to_name).strip(), due, project,
                                                         json.dumps([{"by": from_name, "at": now(), "text": what.strip()}]),
                                                         now(), now()))
        return cur.lastrowid


def update_handoff(lib, hid: int, status: str | None = None, message: str = "", by: str = OWNER):
    if status and status not in HANDOFF_STATES:
        raise ValueError(f"status must be one of {', '.join(HANDOFF_STATES)}")
    with lib._lock, lib._db() as c:
        r = c.execute("SELECT thread FROM handoffs WHERE id=?", (hid,)).fetchone()
        if not r:
            raise KeyError(hid)
        th = json.loads(r[0] or "[]")
        if message.strip():
            th.append({"by": by, "at": now(), "text": message.strip()})
        if status:
            th.append({"by": by, "at": now(), "text": f"marked {status}"})
        c.execute("UPDATE handoffs SET status=COALESCE(?, status), thread=?, updated=? WHERE id=?",
                  (status, json.dumps(th), now(), hid))


def handoffs(lib, open_only: bool = True, name: str = "") -> list[dict]:
    q = "SELECT * FROM handoffs" + (" WHERE status IN ('open','accepted')" if open_only else "") + " ORDER BY id DESC LIMIT 200"
    with lib._db() as c:
        rows = [dict(r) for r in c.execute(q)]
    today = now()[:10]
    for r in rows:
        r["thread"] = json.loads(r["thread"] or "[]")
        r["overdue"] = bool(r["due"]) and r["due"][:10] < today and r["status"] in ("open", "accepted")
    if name:
        n = name.lower()
        rows = [r for r in rows if n in (r["from_name"].lower(), r["to_name"].lower(), r["owner"].lower())]
    return rows


# ================================================================== project actions ("tickets" until a tool is chosen)
def add_task(lib, project: str, outcome: str, owner: str = OWNER, done_when: str = "", due: str = "", source: str = "") -> int:
    if not outcome.strip():
        raise ValueError("outcome is required")
    with lib._lock, lib._db() as c:
        eid = lib._eid(c, project)
        cur = c.execute("INSERT INTO project_tasks(entity_id,outcome,owner,done_when,due,source,created,updated)"
                        " VALUES(?,?,?,?,?,?,?,?)", (eid, outcome.strip(), owner.strip() or OWNER, done_when.strip(),
                                                    due, source, now(), now()))
        c.execute("UPDATE entities SET updated=? WHERE id=?", (now(), eid))
        return cur.lastrowid


def update_task(lib, tid: int, status: str | None = None, owner: str | None = None, outcome: str | None = None,
                done_when: str | None = None):
    if status and status not in TASK_STATES:
        raise ValueError(f"status must be one of {', '.join(TASK_STATES)}")
    with lib._lock, lib._db() as c:
        if not c.execute("SELECT 1 FROM project_tasks WHERE id=?", (tid,)).fetchone():
            raise KeyError(tid)
        for k, v in (("status", status), ("owner", owner), ("outcome", outcome), ("done_when", done_when)):
            if v is not None:
                c.execute(f"UPDATE project_tasks SET {k}=?, updated=? WHERE id=?", (v, now(), tid))


def tasks(lib, project: str | None = None, open_only: bool = False) -> list[dict]:
    q = ("SELECT t.*, e.slug AS project_slug, e.name AS project FROM project_tasks t JOIN entities e ON e.id=t.entity_id")
    args, where = [], []
    if project:
        with lib._db() as c:
            args.append(lib._eid(c, project))
        where.append("t.entity_id=?")
    if open_only:
        where.append("t.status NOT IN ('done','dropped')")
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY (t.status='done'), t.id DESC"
    with lib._db() as c:
        return [dict(r) for r in c.execute(q, args)]


# ================================================================== places and their projects
def projects_by_place(lib) -> dict:
    import projects

    out = {p["id"]: [] for p in PLACES}
    with lib._db() as c:
        offices = {r[0]: (r[1] or "") for r in c.execute(
            "SELECT e.slug, pi.office FROM entities e LEFT JOIN project_info pi ON pi.entity_id=e.id WHERE e.kind='project'")}
    for p in projects.list_projects(lib):
        office = offices.get(p["slug"]) or ""
        if not office and p.get("parent_slug"):
            office = offices.get(p["parent_slug"]) or ""
        out.setdefault(office if office in PLACE else "studio", []).append(p)
    return out


def set_office(lib, project: str, office: str):
    import projects

    if office and office not in PLACE:
        raise ValueError(f"office must be one of {', '.join(PLACE)}")
    projects.update_info(lib, project)
    with lib._lock, lib._db() as c:
        c.execute("UPDATE project_info SET office=? WHERE entity_id=?", (office, lib._eid(c, project)))


# ================================================================== what needs you
def waiting_on_you(lib) -> list[dict]:
    """Every decision or answer the town is waiting for, as notes for your office door."""
    import skills

    notes = []
    with lib._db() as c:
        for r in c.execute("SELECT d.number, d.title, d.by, d.created, e.slug, e.name FROM project_decisions d"
                           " JOIN entities e ON e.id=d.entity_id WHERE d.status='proposed' ORDER BY d.id"):
            notes.append({"kind": "decision", "title": f"{r[5]}: {r[1]}", "from": r[2] or "agent", "at": r[3],
                          "link": f"/library/e/{r[4]}#d{r[0]}"})
        n = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM insights WHERE status='unreviewed' GROUP BY source_id, scope, text)").fetchone()[0]
        if n:
            notes.append({"kind": "review", "title": f"{n} insight{'s' if n != 1 else ''} to review", "from": "the librarian",
                          "at": "", "link": "/review"})
        fails = c.execute("SELECT COUNT(*) FROM inbox WHERE status='failed'").fetchone()[0]
        if fails:
            notes.append({"kind": "inbox", "title": f"{fails} document{'s' if fails != 1 else ''} failed to file",
                          "from": "the inbox", "at": "", "link": "/inbox"})
        ntag = c.execute("SELECT COUNT(*) FROM tags WHERE status='proposed'").fetchone()[0]
        if ntag:
            notes.append({"kind": "tags", "title": f"{ntag} proposed tag{'s' if ntag != 1 else ''}", "from": "the tidy pass",
                          "at": "", "link": "/tags"})
    for s in skills.list_skills(lib):
        if s["status"] != "blocked" and s["latest"] != s["approved"]:
            notes.append({"kind": "skill", "title": f"Skill {s['name']} {s['latest']} to approve", "from": s["source"] or "upload",
                          "at": s["updated"], "link": f"/skills/{s['name']}"})
    for h in handoffs(lib):
        if h["to_name"].lower() in (OWNER.lower(), "you") or h["owner"].lower() == OWNER.lower():
            notes.append({"kind": "handoff", "title": h["what"][:120], "from": h["from_name"], "at": h["created"],
                          "link": f"/kingdom/handoff/{h['id']}", "overdue": h["overdue"]})
    for a in agents(lib):
        if (a.get("waiting_on") or "").lower() in (OWNER.lower(), "you"):
            notes.append({"kind": "agent", "title": f"{a['name']} is waiting on you: {a['task'][:100]}", "from": a["name"],
                          "at": a["updated"], "link": f"/kingdom/agent/{a['name']}"})
    hub = service_status("hubwatch")
    if hub and (hub.get("counts") or {}).get("waiting"):
        notes.append({"kind": "finds", "title": f"{hub['counts']['waiting']} Hub watcher finds waiting", "from": "Hub watcher",
                      "at": "", "link": "http://localhost:8070/"})
    return notes


# ================================================================== extensions (other containers)
_svc_cache: dict = {}


def service_url(name: str) -> str:
    for pair in (os.environ.get("KB_SERVICES") or "ytdl=http://127.0.0.1:8080").split(";"):
        if pair.startswith(name + "="):
            return pair.split("=", 1)[1].rstrip("/")
    return ""


def service_status(name: str, ttl: int = 20):
    hit = _svc_cache.get(name)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    path = {"ytdl": "/api/info", "hubwatch": "/api/status"}.get(name, "/")
    try:
        with urllib.request.urlopen(service_url(name) + path, timeout=1.5) as r:
            val = json.loads(r.read())
    except Exception:  # noqa: BLE001 - an extension being off is normal
        val = None
    _svc_cache[name] = (time.time(), val)
    return val


# ================================================================== calendars (ICS feeds)
def add_feed(lib, clock: str, name: str, url: str, busy_on_work: bool = True) -> int:
    if clock not in ("work", "personal"):
        raise ValueError("clock must be work or personal")
    url = url.strip().replace("webcal://", "https://", 1)
    if not re.match(r"^https?://", url):
        raise ValueError("paste the calendar's ICS address (https://… or webcal://…)")
    with lib._db() as c:
        fid = c.execute("INSERT INTO calendar_feeds(clock,name,url,busy_on_work,created) VALUES(?,?,?,?,?)",
                        (clock, name.strip() or clock.title(), url, int(busy_on_work), now())).lastrowid
    fetch_feed(lib, fid)
    return fid


def delete_feed(lib, fid: int):
    with lib._db() as c:
        c.execute("DELETE FROM calendar_events WHERE feed_id=?", (fid,))
        c.execute("DELETE FROM calendar_feeds WHERE id=?", (fid,))


def feeds(lib) -> list[dict]:
    with lib._db() as c:
        rows = [dict(r) for r in c.execute("SELECT id, clock, name, busy_on_work, last_fetch, error,"
                                           " (SELECT COUNT(*) FROM calendar_events e WHERE e.feed_id=f.id) AS nevents"
                                           " FROM calendar_feeds f ORDER BY clock, id")]
    return rows  # the secret ICS address is never sent back to the browser


def fetch_feed(lib, fid: int):
    with lib._db() as c:
        f = c.execute("SELECT * FROM calendar_feeds WHERE id=?", (fid,)).fetchone()
    if not f:
        return
    try:
        req = urllib.request.Request(f["url"], headers={"User-Agent": "kingdom-calendar"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - your own calendar address
            data = r.read(20 * 1024 * 1024)
        events = parse_ics(data)
        with lib._db() as c:
            c.execute("DELETE FROM calendar_events WHERE feed_id=?", (fid,))
            c.executemany("INSERT OR REPLACE INTO calendar_events VALUES(?,?,?,?,?,?,?)",
                          [(fid, e["uid"], e["start"], e["end"], int(e["all_day"]), e["title"], e["location"]) for e in events])
            c.execute("UPDATE calendar_feeds SET last_fetch=?, error='' WHERE id=?", (now(), fid))
    except Exception as e:  # noqa: BLE001 - keep the error for the page
        with lib._db() as c:
            c.execute("UPDATE calendar_feeds SET last_fetch=?, error=? WHERE id=?", (now(), f"{e.__class__.__name__}: {e}"[:300], fid))


def parse_ics(data: bytes, days_back: int = 1, days_ahead: int = 21) -> list[dict]:
    """Events (recurrences expanded) from an ICS file, in local time."""
    import icalendar
    import recurring_ical_events

    cal = icalendar.Calendar.from_ical(data)
    start = dt.datetime.now().astimezone() - dt.timedelta(days=days_back)
    end = start + dt.timedelta(days=days_back + days_ahead)
    out = []
    for ev in recurring_ical_events.of(cal).between(start, end):
        s, e = ev.get("DTSTART").dt, (ev.get("DTEND").dt if ev.get("DTEND") else None)
        all_day = not isinstance(s, dt.datetime)
        if all_day:
            s_txt, e_txt = s.isoformat(), (e or s + dt.timedelta(days=1)).isoformat()
        else:
            s = s.astimezone() if s.tzinfo else s
            e = (e.astimezone() if e and e.tzinfo else e) or s + dt.timedelta(hours=1)
            s_txt, e_txt = s.strftime("%Y-%m-%d %H:%M"), e.strftime("%Y-%m-%d %H:%M")
        if str(ev.get("STATUS", "")).upper() == "CANCELLED" or str(ev.get("TRANSP", "")).upper() == "TRANSPARENT" and all_day:
            continue
        out.append({"uid": str(ev.get("UID", "")) or f"{s_txt}-{ev.get('SUMMARY', '')}", "start": s_txt, "end": e_txt,
                    "all_day": all_day, "title": str(ev.get("SUMMARY", "") or "(no title)")[:200],
                    "location": str(ev.get("LOCATION", "") or "")[:200]})
    return out


def day(lib, date: str | None = None) -> dict:
    """Both clocks for one day. On the work clock, personal events that reserve time show only as 'Busy'."""
    d = date or dt.date.today().isoformat()
    nxt = (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()
    with lib._db() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT e.*, f.clock, f.name AS feed, f.busy_on_work FROM calendar_events e JOIN calendar_feeds f ON f.id=e.feed_id"
            " WHERE e.start < ? AND e.end > ? ORDER BY e.start", (nxt, d))]
    work = [dict(r, private=False) for r in rows if r["clock"] == "work"]
    personal = [r for r in rows if r["clock"] == "personal"]
    work_view = work + [{"start": r["start"], "end": r["end"], "all_day": r["all_day"], "title": "Busy", "location": "",
                         "clock": "personal", "private": True, "feed": ""} for r in personal if r["busy_on_work"] and not r["all_day"]]
    work_view.sort(key=lambda r: r["start"])
    nowt = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    def next_of(evs):
        return next(({"title": e["title"], "start": e["start"], "in_minutes": _mins(nowt, e["start"])}
                     for e in evs if not e["all_day"] and e["start"] >= nowt), None)
    return {"date": d, "now": nowt, "work": work_view, "personal": personal, "next_work": next_of(work_view),
            "next_personal": next_of(personal), "feeds": len(feeds(lib))}


def _mins(a: str, b: str) -> int:
    f = "%Y-%m-%d %H:%M"
    return int((dt.datetime.strptime(b, f) - dt.datetime.strptime(a, f)).total_seconds() // 60)


class CalendarSync:
    def __init__(self, lib, every: int = 900):
        self.lib, self.every = lib, every

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            for f in feeds(self.lib):
                fetch_feed(self.lib, f["id"])
            time.sleep(self.every)


# ================================================================== the whole town, for the map
def state(lib, since: str | None = None) -> dict:
    by_place = projects_by_place(lib)
    ags = agents(lib)
    hs = handoffs(lib)
    notes = waiting_on_you(lib)
    with lib._db() as c:
        inbox = [dict(r) for r in c.execute("SELECT id, extension, title, status, updated FROM inbox"
                                            " WHERE status IN ('pending','working') ORDER BY id")]
        recent = [dict(r) for r in c.execute("SELECT name, location, text, created FROM agent_log ORDER BY id DESC LIMIT 30")]
        open_tasks = [dict(r) for r in c.execute(
            "SELECT t.id, t.outcome, t.owner, t.status, e.slug FROM project_tasks t JOIN entities e ON e.id=t.entity_id"
            " WHERE t.status IN ('todo','doing','blocked')")]
        nsrc = c.execute("SELECT COUNT(*) FROM sources WHERE kind!='url'").fetchone()[0]
        nent = c.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    task_by_project = {}
    for t in open_tasks:
        task_by_project.setdefault(t["slug"], []).append(t)
    ytdl, hub = service_status("ytdl"), service_status("hubwatch")
    places = []
    for p in PLACES:
        prj = by_place.get(p["id"], [])
        here = [a for a in ags if a["place"] == p["id"] and a["active"]]
        busy = len(here) + sum(len(task_by_project.get(x["slug"], [])) for x in prj if True)
        lines = []
        if p["id"] == "library":
            lines.append(f"{nent} entries · {nsrc} sources")
            if inbox:
                lines.append(f"{len(inbox)} document{'s' if len(inbox) != 1 else ''} being filed")
            busy += len(inbox)
        if p["id"] == "studio":
            lines += [f"{x['name']}{' ' + x['version'] if x['version'] else ''} · {x['status']}" for x in prj[:4]]
            if ytdl and ytdl.get("jobs_active"):
                lines.append(f"YouTube downloader: {ytdl['jobs_active']} job(s) running")
        if p["id"] == "office":
            lines.append(f"{len(notes)} note{'s' if len(notes) != 1 else ''} on the door" if notes else "Nothing waiting on you")
        if p["id"] not in ("library", "studio", "office"):
            lines += [f"{x['name']} · {x['status']}" for x in prj[:3]]
        places.append({**{k: p[k] for k in ("id", "name", "x", "z", "feel", "does", "enter")},
                       "live": bool(p.get("live")) or bool(prj), "private": bool(p.get("private")), "needs": p.get("needs", []),
                       "projects": [{"slug": x["slug"], "name": x["name"], "status": x["status"], "version": x["version"],
                                     "open_tasks": len(task_by_project.get(x["slug"], []))} for x in prj],
                       "agents": [a["name"] for a in here], "activity": busy, "lines": lines,
                       "attention": len(notes) if p["id"] == "office" else 0})
    couriers = [{"id": f"h{h['id']}", "kind": "handoff", "from": h["from_place"], "to": h["to_place"], "what": h["what"],
                 "who": h["from_name"], "owner": h["owner"], "due": h["due"], "overdue": h["overdue"], "status": h["status"],
                 "link": f"/kingdom/handoff/{h['id']}"} for h in hs]
    for i in inbox:   # documents travelling from an extension to the library
        frm = "studio"
        couriers.append({"id": f"i{i['id']}", "kind": "document", "from": frm, "to": "library", "what": i["title"] or "a document",
                         "who": (i["extension"] or "extension").split(":")[0], "owner": "the librarian", "due": "",
                         "overdue": False, "status": i["status"], "link": f"/inbox/{i['id']}"})
    return {"now": now(), "owner": OWNER, "places": places,
            "agents": [{k: a.get(k) for k in ("name", "role", "color", "place", "task", "next_update", "waiting_on", "kind",
                                               "updated", "active", "location")} for a in ags],
            "couriers": couriers, "notes": notes, "clocks": day(lib), "recent": recent,
            "since": changes_since(lib, since) if since else None,
            "services": {"ytdl": bool(ytdl), "hubwatch": bool(hub)}}


def changes_since(lib, since: str) -> dict:
    since = since.replace("T", " ")[:19]
    with lib._db() as c:
        moved = {
            "sources": c.execute("SELECT COUNT(*) FROM sources WHERE created>=? AND kind!='url'", (since,)).fetchone()[0],
            "entries": c.execute("SELECT COUNT(*) FROM entities WHERE created>=?", (since,)).fetchone()[0],
            "decisions": c.execute("SELECT COUNT(*) FROM project_decisions WHERE created>=?", (since,)).fetchone()[0],
            "tasks_done": c.execute("SELECT COUNT(*) FROM project_tasks WHERE status='done' AND updated>=?", (since,)).fetchone()[0],
            "versions": c.execute("SELECT COUNT(*) FROM project_versions WHERE created>=?", (since,)).fetchone()[0],
        }
        stalled = [dict(r) for r in c.execute(
            "SELECT id, outcome AS what, owner, updated FROM project_tasks WHERE status IN ('todo','doing','blocked')"
            " AND updated < ? ORDER BY updated LIMIT 8", (since,))]
        items = [dict(r) for r in c.execute(
            "SELECT 'source' AS kind, title AS what, created AS at, '/library/s/' || id AS link FROM sources WHERE created>=? AND kind!='url'"
            " UNION ALL SELECT 'version', e.name || ' ' || v.version, v.created, '/library/e/' || e.slug || '#versions'"
            "  FROM project_versions v JOIN entities e ON e.id=v.entity_id WHERE v.created>=?"
            " UNION ALL SELECT 'decision', e.name || ': ' || d.title, d.created, '/library/e/' || e.slug || '#d' || d.number"
            "  FROM project_decisions d JOIN entities e ON e.id=d.entity_id WHERE d.created>=?"
            " UNION ALL SELECT 'done', e.name || ': ' || t.outcome, t.updated, '/library/e/' || e.slug || '#actions'"
            "  FROM project_tasks t JOIN entities e ON e.id=t.entity_id WHERE t.status='done' AND t.updated>=?"
            " ORDER BY at DESC LIMIT 25", (since, since, since, since))]
    overdue = [h for h in handoffs(lib) if h["overdue"]]
    return {"since": since, "moved": moved, "items": items, "stalled": stalled,
            "overdue": [{"id": h["id"], "what": h["what"], "owner": h["owner"], "due": h["due"]} for h in overdue]}
