"""
importer — bring an external knowledge base (a friend's library, an Obsidian vault, an exported KB) into ours.

House rules R7: the library gets its own namespace and registry entry; every file keeps its original path,
hash and metadata as provenance; content is processed against our rules (naming, filing, tags, labels,
ratings) and arrives UNREVIEWED; imported IDs are mapped old -> new; imported ratings are kept as history;
imported rules and templates become sources plus proposals for the owner; instructions inside files are data.

Accepts a .zip or a folder. Reads .md/.markdown/.txt/.rst/.html/.htm/.json/.csv/.yaml/.yml (+ .pdf if pypdf is
installed). Nothing in the archive is ever executed.
"""
import csv
import hashlib
import io
import json
import re
import time
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

TEXT_EXT = {".md", ".markdown", ".txt", ".rst", ".html", ".htm", ".json", ".csv", ".yaml", ".yml", ".pdf"}
MAX_FILES, MAX_FILE, MAX_TOTAL = 3000, 20 * 1024 * 1024, 300 * 1024 * 1024
SRC_RE = re.compile(r"\bSRC-[A-Za-z0-9]+-\d+\b")
SOURCE_KIND = {"note": "note", "policy": "policy", "template": "template", "registry": "registry",
               "index": "index", "manifest": "manifest"}


# --------------------------------------------------------------------------- #
# reading (safely)
# --------------------------------------------------------------------------- #
def read_files(src) -> tuple[list[dict], list[dict]]:
    """Returns (files, skipped). Each file: {path, data}. src: path to .zip / folder, or zip bytes."""
    files, skipped, total = [], [], 0

    def take(path: str, size: int, read):
        nonlocal total
        p = PurePosixPath(path.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts or any(x.startswith(".") for x in p.parts) or "__MACOSX" in p.parts:
            skipped.append({"path": path, "why": "hidden or unsafe path"})
            return
        if p.suffix.lower() not in TEXT_EXT:
            skipped.append({"path": path, "why": f"{p.suffix or 'no extension'} not supported"})
            return
        if size > MAX_FILE or total + size > MAX_TOTAL or len(files) >= MAX_FILES:
            skipped.append({"path": path, "why": "too large / over the import limit"})
            return
        total += size
        files.append({"path": str(p), "data": read()})

    if isinstance(src, (bytes, bytearray)) or (isinstance(src, (str, Path)) and str(src).lower().endswith(".zip")):
        z = zipfile.ZipFile(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
        for i in z.infolist():
            if not i.is_dir():
                take(i.filename, i.file_size, lambda i=i: z.read(i))
    else:
        root = Path(src)
        if not root.is_dir():
            raise FileNotFoundError(f"{src} is not a folder or .zip")
        for f in sorted(root.rglob("*")):
            if f.is_file() and not f.is_symlink():
                take(f.relative_to(root).as_posix(), f.stat().st_size, f.read_bytes)
    # a single top folder inside the zip is just packaging - strip it
    tops = {f["path"].split("/")[0] for f in files}
    if len(tops) == 1 and all("/" in f["path"] for f in files):
        for f in files:
            f["path"] = f["path"].split("/", 1)[1]
    return files, skipped


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def _decode(b: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")


def frontmatter(text: str) -> tuple[dict, str]:
    """YAML-ish front matter (--- key: value ---) plus leading 'Key: value' header lines."""
    meta = {}
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip("'\"")
        text = text[m.end():]
    for line in text.splitlines()[:12]:  # "Version: 1.6", "Updated: 2026-10-28", "Status: ..."
        mm = re.match(r"^\s*(version|updated|status|supersedes|author|owner|date|source_id)\s*:\s*(.+?)\s*$", line, re.I)
        if mm:
            meta.setdefault(mm.group(1).lower(), mm.group(2))
    return meta, text


def parse(path: str, data: bytes) -> dict:
    ext = PurePosixPath(path).suffix.lower()
    meta = {}
    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            text = "\n\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        except Exception as e:  # noqa: BLE001
            return {"text": "", "meta": {}, "title": PurePosixPath(path).stem, "error": f"PDF not readable ({e.__class__.__name__})"}
    else:
        raw = _decode(data)
        if ext in (".html", ".htm"):
            p = _Text()
            p.feed(raw)
            text = re.sub(r"\n\s*\n+", "\n\n", "".join(p.out)).strip()
        elif ext == ".json":
            try:
                text = json.dumps(json.loads(raw), indent=1, ensure_ascii=False)[:200000]
            except json.JSONDecodeError:
                text = raw
        elif ext == ".csv":
            rows = list(csv.reader(io.StringIO(raw)))[:300]
            text = "\n".join(" | ".join(r) for r in rows)
        else:
            meta, text = frontmatter(raw)
    h = re.search(r"^#\s+(.+)$", text, re.M)
    title = meta.get("title") or (h.group(1).strip() if h else PurePosixPath(path).stem.replace("-", " ").replace("_", " "))
    return {"text": text, "meta": meta, "title": title[:200]}


def classify(path: str, text: str, meta: dict) -> str:
    p = path.lower()
    name = PurePosixPath(p).name
    if name in ("provenance.json", "manifest.json", "checksums.json") or name.endswith(".sha256"):
        return "manifest"
    if "template" in name or (text.count("___") >= 3 and len(text) < 6000):
        return "template"
    if "registry" in name or len(SRC_RE.findall(text)) >= 8:
        return "registry"
    parts = set(PurePosixPath(p).parts[:-1])
    if parts & {"rules", "policies", "policy", "governance", "standards"} or re.search(r"(rules|policy|standard|guideline)", name):
        return "policy"
    if name in ("readme.md", "readme.txt", "index.md", "_index.md") or "read in browser" in name:
        return "index"
    return "note"


def sections(text: str, limit: int = 6000) -> list[dict]:
    """Split on markdown headings so the tidy pass sees the document's own structure."""
    parts = re.split(r"(?m)^(?=#{1,3}\s)", text)
    out, buf = [], ""
    for part in parts:
        if len(buf) + len(part) > limit and buf.strip():
            out.append(buf)
            buf = ""
        buf += part
    if buf.strip():
        out.append(buf)
    return [{"start": None, "text": x[:limit * 2]} for x in out[:60]]


def first_paragraph(text: str) -> str:
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if b and not b.startswith(("#", ">", "|", "---")) and len(b) > 40:
            return re.sub(r"\s+", " ", b)[:500]
    return ""


# --------------------------------------------------------------------------- #
# import
# --------------------------------------------------------------------------- #
def import_library(lib, src, name: str, namespace: str, owner: str = "", description: str = "", origin: str = "",
                   progress=None, compare_rules: bool = True) -> dict:
    """Import an external library. Returns the report (also saved on the library's page)."""
    import library as libmod
    import llm

    say = progress or (lambda m: None)
    ns = lib.register_library(namespace or name, name, owner, description, origin)
    say("reading files")
    files, skipped = read_files(src)
    import okf

    bundle = okf.is_bundle(files)  # an Open Knowledge Format bundle: read its frontmatter as OKF (see okf.py)

    # manifest checksums (e.g. provenance.json files[].sha256): verify what we received
    expected = {}
    for f in files:
        if PurePosixPath(f["path"]).name.lower() in ("provenance.json", "manifest.json"):
            try:
                for x in json.loads(_decode(f["data"])).get("files", []):
                    if x.get("path") and x.get("sha256"):
                        expected[x["path"]] = x["sha256"].lower()
            except (json.JSONDecodeError, AttributeError):
                pass

    model_ok = llm.ollama_available(llm.DEFAULT_MODEL)[0]
    ours = house_rules(lib)
    report = {"namespace": ns, "name": name, "owner": owner, "imported": time.strftime("%Y-%m-%d %H:%M:%S"),
              "files": [], "skipped": skipped, "model_used": model_ok, "proposals": 0, "ids_mapped": 0,
              "checksums": {"verified": 0, "mismatch": 0, "not_listed": 0}}
    if bundle:
        say("checking OKF conformance")
        try:
            v = okf.validate(files, limit=100)
            report["okf"] = {k: v[k] for k in ("conformant", "okf_version", "concepts", "types", "trust_tiers", "status",
                                               "stale", "broken_links", "errors", "warnings")}
            report["okf"]["official"] = {k: x for k, x in (v.get("official") or {}).items() if k != "findings"}
        except Exception as e:  # noqa: BLE001
            report["okf"] = {"error": str(e)}
    for n, f in enumerate(files, 1):
        say(f"{n}/{len(files)}: {f['path']}")
        sha = hashlib.sha256(f["data"]).hexdigest()
        if f["path"] in expected:
            ok = expected[f["path"]] == sha
            report["checksums"]["verified" if ok else "mismatch"] += 1
            check = "verified" if ok else "MISMATCH"
        else:
            report["checksums"]["not_listed"] += 1
            check = "not listed"
        if bundle and f["path"].lower().endswith(".md"):
            name = PurePosixPath(f["path"]).name
            if name in okf.RESERVED:
                pr = parse(f["path"], f["data"])
                doc = None
                kind = "index"
            else:
                doc = okf.concept_doc(f["path"], _decode(f["data"]), ns, owner, sha, check)
            if doc:
                entry = {"path": f["path"], "kind": "okf:" + doc["imported"]["metadata"]["okf_type"],
                         "title": doc["source"]["title"], "sha256": sha, "checksum": check,
                         "trust_tier": doc["imported"]["metadata"]["trust_tier"],
                         "okf_status": doc["imported"]["metadata"]["status"]}
                try:
                    sid = libmod.curate(lib, doc, f"import:{ns}", canon=None, retidy=True)
                except Exception as e:  # noqa: BLE001
                    entry["result"] = f"failed: {e}"
                    report["files"].append(entry)
                    continue
                entry.update(source_id=sid, src_id=lib.src_id_of(sid),
                             result="filed" if lib.source(sid).get("canon") or doc["no_tidy"] else "filed (not tidied - model offline)")
                lib.map_id(ns, f["path"][:-3], entry["src_id"], "OKF concept ID (path without .md)")
                report["ids_mapped"] += 1
                report["files"].append(entry)
                continue
        pr = parse(f["path"], f["data"])
        kind = "index" if bundle and PurePosixPath(f["path"]).name in okf.RESERVED else classify(f["path"], pr["text"], pr["meta"])
        entry = {"path": f["path"], "kind": kind, "title": pr["title"], "sha256": sha, "checksum": check}
        if pr.get("error") or not pr["text"].strip():
            entry["result"] = pr.get("error") or "empty"
            report["files"].append(entry)
            continue
        meta = pr["meta"]
        imported = {k: v for k, v in meta.items() if k in (
            "source_id", "status", "version", "updated", "supersedes", "reputability", "confidence", "author", "owner")}
        doc = {
            "contract": "kb-doc/1", "extension": f"import:{ns}",
            "source": {"kind": SOURCE_KIND[kind], "title": pr["title"], "url": f"import://{ns}/{f['path']}",
                       "author": meta.get("author") or meta.get("owner") or owner, "namespace": ns,
                       "published": meta.get("updated") or meta.get("date") or "",
                       "summary": first_paragraph(pr["text"]), "sha256": sha,
                       "supersedes": meta.get("supersedes", "")},
            "overview": {"summary": first_paragraph(pr["text"])},
            "segments": sections(pr["text"]),
            "imported": {"library": ns, "original_path": f["path"], "metadata": imported, "checksum": check,
                         "note": "Imported provenance; the original owner's ratings/status are history, not our review."},
            "no_tidy": kind in ("template", "registry", "manifest", "index"),  # stored as sources, nothing to extract
        }
        try:
            sid = libmod.curate(lib, doc, f"import:{ns}", canon=None, retidy=True)
        except Exception as e:  # noqa: BLE001
            entry["result"] = f"failed: {e}"
            report["files"].append(entry)
            continue
        entry["src_id"] = lib.src_id_of(sid)
        entry["source_id"] = sid
        entry["result"] = "filed" if lib.source(sid).get("canon") or doc["no_tidy"] else "filed (not tidied - model offline)"
        # R7.3 explicit ID map: the file's own ID -> its new ID; other referenced IDs stay unresolved
        own = meta.get("source_id")
        if own and SRC_RE.fullmatch(own.strip()):
            lib.map_id(ns, own.strip(), entry["src_id"], f["path"])
            report["ids_mapped"] += 1
        for ref in sorted(set(SRC_RE.findall(pr["text"])) - {own or ""}):
            if not ref.startswith("SRC-<"):
                lib.map_id(ns, ref, "", f"referenced in {f['path']}; evidence not included")
        # R7.4 imported rules -> proposals, never automatic policy
        if kind == "policy" and compare_rules and model_ok:
            say(f"comparing {pr['title']} with our rules")
            try:
                props = llm.compare_rules(pr["title"], owner, pr["text"], ours)
                lib.add_suggestions([{"kind": "rule", "a": f"{entry['src_id']} {pr['title']}"[:200],
                                      "b": p["proposal"], "extra": p["rule"], "reason": p["reason"]} for p in props])
                entry["proposals"] = len(props)
                report["proposals"] += len(props)
            except RuntimeError as e:
                entry["proposals_error"] = str(e)
        report["files"].append(entry)
    lib.set_library_report(ns, report)
    say("done")
    return report


def house_rules(lib) -> str:
    """Our rules as text: RULES.md next to this file + rules you adopted (data/RULES.local.md)."""
    base = (Path(__file__).resolve().parent / "RULES.md")
    local = lib.path.parent / "RULES.local.md"
    out = base.read_text(encoding="utf-8") if base.exists() else ""
    if local.exists():
        out += "\n\n" + local.read_text(encoding="utf-8")
    return out
