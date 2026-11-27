#!/usr/bin/env python3
"""measure-data: count company SaaS and business data locally. Counts only, never content.

Usage:
  measure_data.py <source> <path> --out DIR [--mode simple|full] [--label NAME] [--cutoff 2025-01-01] [--force]
  measure_data.py report --out DIR [--no-dream]
  measure_data.py status --out DIR [--category KEY=STATUS ...] [--connector "TOOL=STATUS" ...]

Each source also takes --cutoff-early (default 2022-11-30, pre-ChatGPT), --ownership, --flag NAME (restriction
flags), --version-history and --link-salt (hashed ticket keys, shared with measure-code).

Modes:
  full    (default) every record is read.
  simple  optional, only when a quick look is asked for: listing and metadata, sampled: up to --sample-files files are parsed (or the first
          --sample-mb of one big mailbox or dump) and counts are scaled by size and marked
          as estimates. Minutes, not hours.

Sources (each reads a LOCAL export; the script makes no network calls):
  slack      Slack workspace export (folder or .zip)
  discord    DiscordChatExporter JSON files, or a Discord data package (folder or .zip)
  notion     Notion export (Markdown/CSV/HTML folder or .zip) or saved API objects (.json/.jsonl)
  clickup    ClickUp CSV or JSON export
  jira       Jira CSV, XML (RSS) or JSON search export
  tickets    any other ticket/task CSV (Linear, Asana, Trello CSV, ...)
  mbox       mbox files (Gmail Takeout, Thunderbird, ...) in a folder, or one .mbox
  sql        SQL dumps (.sql or .sql.gz; MySQL INSERT and PostgreSQL COPY)
  bigquery   BigQuery metadata saved as JSON/CSV (bq ls/show output, INFORMATION_SCHEMA rows)
  files      any local folder, synced Google Drive, Dropbox, OneDrive or NAS share

Each run writes <out>/sources/<source>--<label>.json. `report` merges every
source file into <out>/measure.json and <out>/report.md.

Dream mode: after the report the agent writes a short "Why this is special"
pitch with add_dream.py. It lands in the `dream` block of measure.json and in
the last section of report.md, labelled and kept apart from the counts.
`report --no-dream` skips it.

Never written: message or page text, titles, subjects, file names, paths,
table or channel names, people's names, ids or email addresses. People are
counted through one-way hashes. Progress is checkpointed in <out>/.state.

Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import random
import re
import sys
import time
import zipfile
from collections import Counter
from email.parser import BytesHeaderParser
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import studio_signals  # noqa: E402

TOOL = "measure-data"
VERSION = "0.4.0"
SCHEMA = "october.measure/v1"
SKETCH_K = 256
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PHONE_RX = re.compile(r"(?<!\d)(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{3,4}[\s.-]\d{3,4}(?:[\s.-]\d{2,4})?(?!\d)")
DATE_RX = re.compile(r"(19[89]\d|20[0-4]\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")


class Opts:
    simple = False
    sample_files = 200
    sample_bytes = 64 * 1024 * 1024
    seed = 7
    cutoff_early = dt.datetime(2022, 11, 30, tzinfo=dt.timezone.utc)
    source = ""
    link_salt = ""


OPTS = Opts()


def log(msg: str) -> None:
    print(f"[{TOOL}] {msg}", file=sys.stderr, flush=True)


def h(value, n: int = 16) -> str:
    return hashlib.sha256(str(value).encode("utf-8", "replace")).hexdigest()[:n]


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def to_dt(value) -> dt.datetime | None:
    """Best-effort timestamp parser: epoch s/ms, ISO 8601, RFC 2822, common CSV formats."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and re.fullmatch(r"\d{9,13}(\.\d+)?", value.strip())):
            x = float(value)
            if x > 1e11:
                x /= 1000.0
            return dt.datetime.fromtimestamp(x, tz=dt.timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None
    s = str(value).strip()
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        pass
    for f in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M", "%m/%d/%Y", "%d/%b/%y %I:%M %p", "%d/%b/%Y %I:%M %p",
              "%B %d, %Y %I:%M %p", "%B %d, %Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d.%m.%Y %H:%M",
              "%a, %d %b %Y %H:%M:%S %z", "%A, %B %d, %Y %I:%M:%S %p", "%Y-%m-%d %H:%M"):
        try:
            d = dt.datetime.strptime(s, f)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    try:
        d = parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    m = DATE_RX.search(s)
    if m:
        return dt.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=dt.timezone.utc)
    return None


# --------------------------------------------------------------------------
# accumulator: everything a source reports, mergeable and JSON-serialisable
# --------------------------------------------------------------------------


class Acc:
    def __init__(self, cutoff: dt.datetime):
        self.cutoff = cutoff
        self.c = Counter()
        self.years = Counter()
        self.months = Counter()
        self.month_people = {}      # "YYYY-MM" -> set of hashed humans active that month
        self.first = self.last = self.last_human = None
        self.dated = 0
        self.pre = 0
        self.pre_early = 0
        self.people = Counter()
        self.bots = set()
        self.chars = 0
        self.sketch = set()
        self.exts = Counter()

    def item(self, when: dt.datetime | None, person=None, bot=False, text: str = "", key=None, kind="items", system=False):
        self.c[kind] += 1
        human = bool(person) and not bot and not system
        if bot:
            self.c[kind + "_by_bots"] += 1
        if system:
            self.c[kind + "_system"] += 1
        if when is not None and 1980 <= when.year <= 2100:
            self.dated += 1
            self.years[str(when.year)] += 1
            mon = when.strftime("%Y-%m")
            self.months[mon] += 1
            iso = when.strftime("%Y-%m-%d")
            self.first = iso if self.first is None or iso < self.first else self.first
            self.last = iso if self.last is None or iso > self.last else self.last
            if human:
                self.last_human = iso if self.last_human is None or iso > self.last_human else self.last_human
                self.month_people.setdefault(mon, set()).add(h(person, 12))
            if when < self.cutoff:
                self.pre += 1
            if when < OPTS.cutoff_early:
                self.pre_early += 1
        if person:
            hp = h(person)
            if bot:
                self.bots.add(hp)
            elif not system:
                self.people[hp] += 1
        if text:
            if human or not person:
                self.chars += len(text)
            if EMAIL_RX.search(text):
                self.c["items_with_email_pattern"] += 1
            if PHONE_RX.search(text):
                self.c["items_with_phone_pattern"] += 1
        if key is not None:
            self.add_key(key)

    def add_key(self, key) -> None:
        self.sketch.add(h(key))
        if len(self.sketch) > SKETCH_K * 4:
            self.sketch = set(sorted(self.sketch)[:SKETCH_K])

    def to_dict(self) -> dict:
        return {"c": dict(self.c), "years": dict(self.years), "months": dict(self.months),
                "month_people": {k: sorted(v) for k, v in self.month_people.items()}, "first": self.first,
                "last": self.last, "last_human": self.last_human, "dated": self.dated, "pre": self.pre,
                "pre_early": self.pre_early,
                "people": dict(self.people), "bots": sorted(self.bots), "chars": self.chars,
                "sketch": sorted(self.sketch)[:SKETCH_K], "exts": dict(self.exts)}

    def merge(self, d: dict) -> None:
        self.c.update(d["c"]); self.years.update(d["years"]); self.months.update(d["months"])
        self.people.update(d["people"]); self.exts.update(d["exts"]); self.bots.update(d["bots"])
        for k, v in d.get("month_people", {}).items():
            self.month_people.setdefault(k, set()).update(v)
        self.dated += d["dated"]; self.pre += d["pre"]; self.chars += d["chars"]
        self.pre_early += d.get("pre_early", 0)
        for k, newer in (("first", False), ("last", True), ("last_human", True)):
            v = d.get(k)
            if v:
                cur = getattr(self, k)
                if cur is None or (v > cur if newer else v < cur):
                    setattr(self, k, v)
        self.sketch.update(d["sketch"])
        self.sketch = set(sorted(self.sketch)[:SKETCH_K])

    def summary(self, primary: str, dated_basis: str | None = None) -> dict:
        counts = sorted(self.people.values(), reverse=True)
        tot = sum(counts) or 1
        n = self.c.get(primary, 0)
        basis = self.c.get(dated_basis, 0) if dated_basis else n
        human = max(0, n - self.c.get(primary + "_by_bots", 0) - self.c.get(primary + "_system", 0))
        newest = max(self.months) if self.months else None
        last12 = peak = peak_month = median12 = None
        if newest:
            y, m = map(int, newest.split("-"))
            keys = [f"{(y * 12 + m - 1 - i) // 12}-{(y * 12 + m - 1 - i) % 12 + 1:02d}" for i in range(12)]
            last12 = sum(self.months.get(k, 0) for k in keys)
            if self.month_people:
                peak_month, ppl = max(self.month_people.items(), key=lambda kv: (len(kv[1]), kv[0]))
                peak = len(ppl)
                recent = sorted(len(self.month_people.get(k, ())) for k in keys)
                median12 = recent[len(recent) // 2]
        return {
            "primary_unit": primary,
            "primary_count": n,
            "human_count": human if self.people or self.bots else None,
            "human_share": round(human / n, 3) if n and (self.people or self.bots) else None,
            "counts": dict(sorted(self.c.items())),
            "span": {"first": self.first, "last": self.last, "last_human": self.last_human},
            "dated_share": round(self.dated / basis, 3) if basis else None,
            "by_year": dict(sorted(self.years.items())),
            "active_months": len(self.months),
            "last_12_months": last12,
            "pre_cutoff": self.pre,
            "pre_cutoff_share": round(self.pre / self.dated, 3) if self.dated else None,
            "pre_chatgpt": self.pre_early,
            "pre_chatgpt_share": round(self.pre_early / self.dated, 3) if self.dated else None,
            "people": {"distinct": len(counts), "bots": len(self.bots),
                       "top1_share": round(counts[0] / tot, 3) if counts else None,
                       "top5_share": round(sum(counts[:5]) / tot, 3) if counts else None,
                       "with_10plus_items": sum(1 for x in counts if x >= 10),
                       "peak_active_in_a_month": peak, "peak_month": peak_month,
                       "median_active_last_12_months": median12},
            "text": {"characters": self.chars, "token_estimate": self.chars // 4},
            "attachments_by_family": dict(self.exts.most_common()),
            "fingerprints": {"item_sketch": sorted(self.sketch)[:SKETCH_K]},
        }


class Checkpoint:
    """Remembers finished units (a channel, a file, a folder) and their partial results."""

    def __init__(self, out: Path, source: str, label: str, force: bool, mode: str):
        self.path = out / ".state" / f"{source}--{safe(label)}--{mode}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if force and self.path.exists():
            self.path.unlink()
        self.done = {}
        if self.path.exists():
            for line in self.path.read_text("utf-8").splitlines():
                try:
                    rec = json.loads(line)
                    self.done[rec["unit"]] = rec
                except (ValueError, KeyError):
                    continue  # a half-written last line from a crash

    def has(self, unit: str) -> bool:
        return h(unit) in self.done

    def save(self, unit: str, acc: Acc, extra=None) -> None:
        rec = {"unit": h(unit), "acc": acc.to_dict(), "extra": extra or {}}
        self.done[rec["unit"]] = rec
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def merged(self, cutoff) -> tuple:
        acc = Acc(cutoff)
        extras = []
        for rec in self.done.values():
            acc.merge(rec["acc"])
            extras.append(rec["extra"])
        return acc, extras


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-") or "x"


# --------------------------------------------------------------------------
# inputs: folders and zips look the same; simple mode samples
# --------------------------------------------------------------------------


class Tree:
    def __init__(self, path: Path):
        self.path = path
        self.zip = zipfile.ZipFile(path) if path.is_file() and zipfile.is_zipfile(path) else None

    def files(self):
        if self.zip:
            for info in self.zip.infolist():
                if not info.is_dir():
                    yield info.filename, info.file_size
        elif self.path.is_file():
            yield self.path.name, self.path.stat().st_size
        else:
            for root, dirs, files in os.walk(self.path):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                for f in sorted(files):
                    p = Path(root, f)
                    try:
                        yield p.relative_to(self.path).as_posix(), p.stat().st_size
                    except OSError:
                        continue

    def open(self, rel: str):
        if self.zip:
            return self.zip.open(rel)
        if self.path.is_file():
            return self.path.open("rb")
        return (self.path / rel).open("rb")

    def read_json(self, rel: str):
        with self.open(rel) as f:
            return json.loads(f.read().decode("utf-8", "replace"))


def sample(items: list, size_of=lambda x: x[1]) -> tuple:
    """Simple mode: a seeded sample of the bulk files plus the factor that scales it to the whole."""
    total = sum(size_of(x) for x in items) or 1
    if not OPTS.simple or len(items) <= OPTS.sample_files:
        return items, 1.0
    chosen = random.Random(OPTS.seed).sample(items, OPTS.sample_files)
    got = sum(size_of(x) for x in chosen) or 1
    return chosen, total / got


FAMILY = {
    "document": {"doc", "docx", "odt", "rtf", "txt", "md", "pages", "gdoc"},
    "spreadsheet": {"xls", "xlsx", "xlsm", "ods", "csv", "tsv", "numbers", "gsheet"},
    "presentation": {"ppt", "pptx", "odp", "key", "gslides"},
    "pdf": {"pdf"},
    "image": {"png", "jpg", "jpeg", "gif", "webp", "heic", "tif", "tiff", "bmp", "svg", "raw", "cr2", "nef", "dng"},
    "video": {"mp4", "mov", "avi", "mkv", "webm", "m4v", "wmv"},
    "audio": {"mp3", "wav", "m4a", "aac", "flac", "ogg", "opus"},
    "archive": {"zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz", "dmg", "iso"},
    "email": {"eml", "msg", "mbox", "pst", "ost"},
    "database": {"sql", "db", "sqlite", "sqlite3", "mdb", "accdb", "bak", "dump", "parquet", "avro"},
    "code": {"py", "js", "ts", "java", "cs", "cpp", "c", "h", "go", "rs", "rb", "php", "swift", "kt", "html", "css", "ipynb"},
    "design": {"psd", "ai", "fig", "sketch", "xd", "indd", "blend", "fbx", "obj", "dwg", "dxf", "skp", "aep"},
    "data": {"json", "jsonl", "xml", "yaml", "yml", "ndjson", "log"},
}
WORKING_DOCS = {"document", "spreadsheet", "presentation", "pdf"}
MEDIA = {"image", "video", "audio"}


def family(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    for fam, exts in FAMILY.items():
        if ext in exts:
            return fam
    return "other"


# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------


def src_slack(path: Path, ck: Checkpoint, cutoff) -> dict:
    t = Tree(path)
    listing = list(t.files())
    files = [f for f, _ in listing]
    root = next((f[: -len("users.json")] for f in files if f.endswith("users.json")), "")
    bots_ids = set()
    users_total = users_bot = users_deleted = 0
    if root + "users.json" in files:
        for u in t.read_json(root + "users.json"):
            users_total += 1
            if u.get("is_bot") or u.get("id") == "USLACKBOT":
                users_bot += 1
                bots_ids.add(u.get("id"))
            users_deleted += bool(u.get("deleted"))
    kinds = {}
    for name, kind in (("channels.json", "public"), ("groups.json", "private"), ("dms.json", "dm"), ("mpims.json", "group_dm")):
        if root + name in files:
            for ch in t.read_json(root + name):
                kinds[ch.get("name") or ch.get("id")] = kind
    days = [(f, s) for f, s in listing if f[len(root):].count("/") == 1 and re.search(r"/\d{4}-\d{2}-\d{2}\.json$", f)]
    chosen, factor = sample(days)
    by_channel = {}
    for f, _ in chosen:
        by_channel.setdefault(f[len(root):].split("/")[0], []).append(f)
    channels_all = {f[len(root):].split("/")[0] for f, _ in days}
    log(f"slack: {len(channels_all)} conversations, {len(chosen)} of {len(days)} day files to read")
    for ch, day_files in sorted(by_channel.items()):
        if ck.has(ch):
            continue
        acc = Acc(cutoff)
        for f in day_files:
            try:
                msgs = t.read_json(f)
            except ValueError:
                acc.c["unreadable_files"] += 1
                continue
            for m in msgs if isinstance(msgs, list) else []:
                user = m.get("user") or m.get("bot_id")
                bot = bool(m.get("bot_id")) or m.get("subtype") == "bot_message" or user in bots_ids
                system = m.get("subtype") in ("channel_join", "channel_leave", "channel_topic", "channel_purpose", "channel_name", "pinned_item")
                acc.item(to_dt(m.get("ts")), person=user, bot=bot, system=system, text=m.get("text") or "",
                         key=f"{ch}:{m.get('ts')}", kind="messages")
                if m.get("thread_ts") and m.get("thread_ts") != m.get("ts"):
                    acc.c["thread_replies"] += 1
                if m.get("reply_count"):
                    acc.c["threads"] += 1
                for fl in m.get("files") or []:
                    acc.c["files_shared"] += 1
                    acc.c["attachment_bytes_referenced"] += int(fl.get("size") or 0)
                    acc.exts[family(fl.get("name") or fl.get("filetype") or "")] += 1
                acc.c["reactions"] += sum(r.get("count", 0) for r in m.get("reactions") or [])
        ck.save(ch, acc)
    acc, _ = ck.merged(cutoff)
    out = acc.summary("messages")
    out["counts"].update({f"conversations_{k}": n for k, n in Counter(kinds.get(c, "unknown") for c in channels_all).items()})
    out["counts"]["conversations"] = len(channels_all)
    out["counts"]["export_bytes"] = sum(s for _, s in listing)
    out["workspace"] = {"user_accounts": users_total, "bot_accounts": users_bot, "deactivated_accounts": users_deleted}
    return finish(out, factor, f"{len(chosen)} of {len(days)} day files read")


def src_discord(path: Path, ck: Checkpoint, cutoff) -> dict:
    t = Tree(path)
    listing = [(f, s) for f, s in t.files() if f.lower().endswith((".json", ".csv"))]
    chosen, factor = sample(listing)
    guilds = set()
    for f, _ in chosen:
        if ck.has(f):
            continue
        acc = Acc(cutoff)
        try:
            if f.lower().endswith(".json"):
                data = t.read_json(f)
                if isinstance(data, dict) and isinstance(data.get("messages"), list):  # DiscordChatExporter
                    acc.c["channels"] += 1
                    gid = (data.get("guild") or {}).get("id")
                    for m in data["messages"]:
                        a = m.get("author") or {}
                        system = (m.get("type") or "Default") not in ("Default", "Reply")
                        acc.item(to_dt(m.get("timestamp")), person=a.get("id"), bot=bool(a.get("isBot")), system=system,
                                 text=m.get("content") or "", key=m.get("id"), kind="messages")
                        for at in m.get("attachments") or []:
                            acc.c["attachments"] += 1
                            acc.c["attachment_bytes_referenced"] += int(at.get("fileSizeBytes") or 0)
                            acc.exts[family(at.get("fileName") or at.get("url") or "")] += 1
                        if m.get("reference"):
                            acc.c["replies"] += 1
                        acc.c["reactions"] += sum(r.get("count", 0) for r in m.get("reactions") or [])
                    ck.save(f, acc, {"guild": h(gid, 10) if gid else None})
                    continue
                if isinstance(data, list) and data and isinstance(data[0], dict) and "Timestamp" in data[0]:
                    acc.c["channels"] += 1
                    for m in data:
                        acc.item(to_dt(m.get("Timestamp")), person="self", text=m.get("Contents") or "", key=m.get("ID"), kind="messages")
                        if m.get("Attachments"):
                            acc.c["attachments"] += len(str(m["Attachments"]).split())
            else:
                with t.open(f) as raw:
                    rdr = csv.DictReader(io.TextIOWrapper(raw, "utf-8", errors="replace"))
                    if rdr.fieldnames and "Timestamp" in rdr.fieldnames:
                        acc.c["channels"] += 1
                        for m in rdr:
                            acc.item(to_dt(m.get("Timestamp")), person="self", text=m.get("Contents") or "", key=m.get("ID"), kind="messages")
                            if m.get("Attachments"):
                                acc.c["attachments"] += len(m["Attachments"].split())
        except (ValueError, OSError, UnicodeDecodeError):
            acc.c["unreadable_files"] += 1
        ck.save(f, acc)
    acc, extras = ck.merged(cutoff)
    guilds = {e.get("guild") for e in extras if e.get("guild")}
    out = acc.summary("messages")
    out["counts"]["servers"] = len(guilds)
    out["counts"]["export_bytes"] = sum(s for _, s in listing)
    if OPTS.simple:
        out["counts"]["channels"] = len(listing)
    return finish(out, factor, f"{len(chosen)} of {len(listing)} channel files read")


NOTION_CREATED = re.compile(r"^(Created|Created time|Date created)\s*:\s*(.+)$", re.I | re.M)
NOTION_EDITED = re.compile(r"^(Last edited time|Last edited|Updated)\s*:\s*(.+)$", re.I | re.M)


def src_notion(path: Path, ck: Checkpoint, cutoff) -> dict:
    t = Tree(path)
    listing = list(t.files())
    api_objects = [f for f, _ in listing if f.endswith((".jsonl", ".json"))]
    chosen, factor = sample([x for x in listing if not x[0].endswith((".json", ".jsonl"))])
    by_root = {}
    for f, size in chosen:
        by_root.setdefault(f.split("/")[0] if "/" in f else "_top", []).append((f, size))
    for root, items in sorted(by_root.items()):
        if ck.has(root):
            continue
        acc = Acc(cutoff)
        for f, size in items:
            low = f.lower()
            if low.endswith((".md", ".html")):
                text = t.open(f).read().decode("utf-8", "replace")
                body = re.sub(r"<[^>]+>", " ", text) if low.endswith(".html") else text
                m = NOTION_CREATED.search(body)
                acc.item(to_dt(m.group(2)) if m else None, text=body, key=f, kind="pages")
                if NOTION_EDITED.search(body):
                    acc.c["pages_with_edit_time"] += 1
            elif low.endswith(".csv"):
                acc.c["databases"] += 1
                with t.open(f) as raw:
                    rdr = csv.DictReader(io.TextIOWrapper(raw, "utf-8-sig", errors="replace"))
                    cols = rdr.fieldnames or []
                    ccol = next((c for c in cols if c.lower() in ("created", "created time", "date created")), None)
                    pcol = next((c for c in cols if c.lower() in ("created by", "owner", "assignee")), None)
                    for row in rdr:
                        acc.item(to_dt(row.get(ccol)) if ccol else None, person=row.get(pcol) if pcol else None,
                                 text=" ".join(v for v in row.values() if isinstance(v, str)), kind="database_rows")
            else:
                acc.c["attachments"] += 1
                acc.exts[family(f)] += 1
                acc.c["attachment_bytes"] += size
        ck.save(root, acc)
    for f in api_objects:  # saved API objects carry real timestamps and authors; small, never sampled
        if ck.has("api:" + f):
            continue
        acc = Acc(cutoff)
        with t.open(f) as raw:
            text = raw.read().decode("utf-8", "replace")
        objs = []
        if f.endswith(".jsonl"):
            for line in text.splitlines():
                try:
                    objs.append(json.loads(line))
                except ValueError:
                    pass
        else:
            try:
                data = json.loads(text)
                objs = data.get("results", [data]) if isinstance(data, dict) else data
            except ValueError:
                pass
        for o in objs:
            if not isinstance(o, dict) or o.get("in_trash") or o.get("archived"):
                continue
            kind = {"page": "pages", "block": "blocks", "comment": "comments", "database": "databases",
                    "data_source": "databases"}.get(o.get("object"))
            if not kind:
                continue
            if kind == "pages" and (o.get("parent") or {}).get("type") in ("database_id", "data_source_id"):
                kind = "database_rows"
            who = o.get("created_by") or {}
            acc.item(to_dt(o.get("created_time")), person=who.get("id"), bot=who.get("object") == "bot" or who.get("type") == "bot",
                     key=o.get("id"), kind=kind)
        ck.save("api:" + f, acc)
    acc, _ = ck.merged(cutoff)
    primary = "pages" if acc.c["pages"] >= acc.c["database_rows"] else "database_rows"
    out = acc.summary(primary)
    out["counts"]["pages_and_rows"] = acc.c["pages"] + acc.c["database_rows"]
    out["counts"]["top_level_roots"] = len({f.split("/")[0] for f, _ in listing if "/" in f})
    out["counts"]["export_bytes"] = sum(s for _, s in listing)
    out["note"] = ("Notion's Markdown/CSV export drops most timestamps; dates come from 'Created' properties "
                   "where present. Saved API objects carry full timestamps.")
    return finish(out, factor, f"{len(chosen)} of {len(listing) - len(api_objects)} export files read")


TICKET_COLS = {
    "created": ("created", "date created", "created at", "created_at", "creation date", "date_created", "created date"),
    "updated": ("updated", "date updated", "updated at", "last modified", "date_updated", "last updated"),
    "closed": ("resolved", "date closed", "closed at", "completed at", "done date", "resolution date", "date_done"),
    "person": ("reporter", "creator", "created by", "assignee", "assignees", "owner"),
    "parent": ("parent id", "parent", "parent key", "parent task", "parent_id"),
    "type": ("issue type", "type", "task type", "issuetype"),
    "key": ("issue key", "task id", "id", "key", "issue id", "task_id"),
    "comments": ("comments", "comment count", "comment"),
    "status": ("status", "state", "list", "column"),
    "text": ("summary", "description", "task name", "name", "title", "content", "text", "notes", "comment", "comments"),
}
KNOWN_TYPES = {"bug", "story", "task", "epic", "sub-task", "subtask", "feature", "improvement", "incident", "milestone", "spike"}


TICKET_KEY_RX = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
DONE_STATUSES = {"done", "closed", "resolved", "complete", "completed", "fixed", "released", "shipped", "verified"}
TRACE_TYPES = ("bug", "task", "story", "other")
TRACE_CAP = 50_000


def link_hash(kind: str, value: str, salt: str = "") -> str:
    """One-way key shared with measure-code: the same ticket key hashes the same way on both sides."""
    return hashlib.sha256(f"{salt}|{kind}|{value}".encode("utf-8", "replace")).hexdigest()[:16]


def trace_type(typ) -> str:
    t = (typ or "").strip().lower()
    if t in ("bug", "defect", "crash", "incident", "regression", "issue - bug") or "bug" in t:
        return "bug"
    if t in ("story", "user story", "feature", "improvement", "enhancement", "epic"):
        return "story"
    if t in ("task", "sub-task", "subtask", "chore", "spike", "technical task"):
        return "task"
    return "other"


def linkable_key(key) -> str | None:
    """The ticket key a commit message would carry: PROJ-123 (Jira, Linear, YouTrack), CU-<id> (ClickUp), #123."""
    if key is None or isinstance(key, (dict, list)):
        return None
    k = str(key).strip().upper()
    if not k:
        return None
    if OPTS.source == "clickup":
        return k if k.startswith("CU-") else "CU-" + k
    if TICKET_KEY_RX.match(k):
        return k
    if k.isdigit():
        return "#" + k
    return None


def new_trace() -> dict:
    return {"by_type": {t: {"total": 0, "resolved": 0} for t in TRACE_TYPES}, "keys": {t: [] for t in TRACE_TYPES},
            "unlinkable": 0}


def ticket_row(acc: Acc, created, updated, closed, person, parent, typ, key, comments, description="", text="",
               status=None, trace=None):
    acc.item(to_dt(created), person=person, key=key, kind="tickets", text=text or "")
    if parent:
        acc.c["subtasks"] += 1
    if closed:
        acc.c["tickets_closed"] += 1
    if trace is not None:
        tt = trace_type(typ)
        resolved = bool(closed) or str(status or "").strip().lower() in DONE_STATUSES
        trace["by_type"][tt]["total"] += 1
        if resolved:
            trace["by_type"][tt]["resolved"] += 1
            lk = linkable_key(key)
            if lk is None:
                trace["unlinkable"] += 1
            else:
                trace["keys"][tt].append(link_hash("ticket", lk, OPTS.link_salt))
    if updated and created and str(updated) != str(created):
        acc.c["tickets_edited_after_creation"] += 1
    t = (typ or "").strip().lower()
    if t:
        acc.c["type_" + (t.replace(" ", "_") if t in KNOWN_TYPES else "other")] += 1
    if comments:
        acc.c["tickets_with_comments"] += 1
    if len((description or "").strip()) >= 20 or comments:
        acc.c["tickets_with_description_or_comment"] += 1


def merge_traces(traces: list) -> dict:
    """Ticket counts by type and the hashed keys of resolved tickets, for bug -> fix links against measure-code."""
    by_type = {t: {"total": 0, "resolved": 0} for t in TRACE_TYPES}
    keys = {t: set() for t in TRACE_TYPES}
    unlinkable = 0
    for tr in traces:
        for t in TRACE_TYPES:
            by_type[t]["total"] += tr["by_type"][t]["total"]
            by_type[t]["resolved"] += tr["by_type"][t]["resolved"]
            keys[t].update(tr["keys"][t])
        unlinkable += tr.get("unlinkable", 0)
    capped = any(len(v) > TRACE_CAP for v in keys.values())
    return {"label": "estimated" if OPTS.simple else "verified",
            "method": "ticket type and resolution from the export's type, status and resolved-date columns; keys of "
                      "resolved tickets hashed one-way (link_hash) so they can be matched to commit messages"
                      + ("; simple mode reads a sample, so the sets are partial" if OPTS.simple else ""),
            "key_salt_used": bool(OPTS.link_salt), "by_type": by_type,
            "resolved_key_hashes": {t: sorted(v)[:TRACE_CAP] for t, v in keys.items()},
            "resolved_without_linkable_key": unlinkable, "capped": capped}


def src_tickets(path: Path, ck: Checkpoint, cutoff) -> dict:
    t = Tree(path)
    listing = list(t.files())
    for f, size in listing:
        low = f.lower()
        if not low.endswith((".csv", ".json", ".xml")) or ck.has(f):
            continue
        acc = Acc(cutoff)
        acc.c["export_files"] += 1
        acc.c["export_bytes"] += size
        tr = new_trace()
        try:
            if low.endswith(".csv"):
                with t.open(f) as raw:
                    rdr = csv.reader(io.TextIOWrapper(raw, "utf-8-sig", errors="replace"))
                    header = next(rdr, [])
                    idx = {k: [i for i, c in enumerate(header) if c.lower().strip() in v] for k, v in TICKET_COLS.items()}
                    desc = [i for i, c in enumerate(header) if c.lower().strip() == "description"]
                    first = lambda row, k: next((row[i] for i in idx[k] if i < len(row) and row[i]), None)  # noqa: E731
                    for n, row in enumerate(rdr):
                        if OPTS.simple and n >= 20_000:
                            acc.c["_rows_not_read"] += 1
                            continue
                        ticket_row(acc, first(row, "created"), first(row, "updated"), first(row, "closed"),
                                   first(row, "person"), first(row, "parent"), first(row, "type"), first(row, "key"),
                                   first(row, "comments"), " ".join(row[i] for i in desc if i < len(row)),
                                   " ".join(row[i] for i in idx["text"] if i < len(row)), first(row, "status"), tr)
            elif low.endswith(".json"):
                data = t.read_json(f)
                items = (data.get("tasks") or data.get("issues") or data.get("data") or []) if isinstance(data, dict) else data
                for it in items if isinstance(items, list) else []:
                    if not isinstance(it, dict):
                        continue
                    fl = it.get("fields") or it
                    who = fl.get("creator") or fl.get("reporter") or (fl.get("assignees") or [None])[0]
                    who = (who.get("accountId") or who.get("id") or who.get("email")) if isinstance(who, dict) else who
                    typ = fl.get("issuetype")
                    typ = typ.get("name") if isinstance(typ, dict) else typ
                    desc = fl.get("description") or it.get("text_content") or ""
                    desc = desc if isinstance(desc, str) else json.dumps(desc)
                    stt = fl.get("status") or it.get("status")
                    stt = (stt.get("name") or stt.get("status") or stt.get("type")) if isinstance(stt, dict) else stt
                    ticket_row(acc, fl.get("created") or it.get("date_created"), fl.get("updated") or it.get("date_updated"),
                               fl.get("resolutiondate") or it.get("date_closed") or it.get("date_done"), who,
                               fl.get("parent") or it.get("parent"), typ, it.get("key") or it.get("custom_id") or it.get("id"),
                               fl.get("comment") or it.get("comments"), desc, (fl.get("summary") or it.get("name") or "") + " " + desc,
                               stt, tr)
            else:  # Jira RSS/XML, read with regexes so no XML parser is needed
                text = t.open(f).read().decode("utf-8", "replace")
                for item in re.findall(r"<item>(.*?)</item>", text, re.S):
                    g = lambda tag: (re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", item, re.S) or [None, None])[1]  # noqa: E731
                    desc = re.sub(r"<[^>]+>|&\w+;", " ", g("description") or "")
                    ticket_row(acc, g("created"), g("updated"), g("resolved"), g("reporter"), g("parent"),
                               g("type"), g("key"), "<comment" in item, desc, (g("summary") or "") + " " + desc,
                               g("status"), tr)
        except (ValueError, OSError, UnicodeDecodeError, csv.Error):
            acc.c["unreadable_files"] += 1
        ck.save(f, acc, {"trace": tr})
    acc, extras = ck.merged(cutoff)
    out = acc.summary("tickets")
    out["traceable"] = merge_traces([e.get("trace") for e in extras if e.get("trace")])
    n = out["primary_count"]
    out["description_or_comment_share"] = round(acc.c["tickets_with_description_or_comment"] / n, 3) if n else None
    factor = (n + acc.c["_rows_not_read"]) / n if n else 1.0
    return finish(out, factor, "first 20,000 rows of each export read" if acc.c["_rows_not_read"] else None)


GMAIL_SYSTEM = {"inbox", "sent", "spam", "trash", "draft", "drafts", "chat", "important", "starred", "archived", "opened", "unread"}


def _looks_mbox(p: Path) -> bool:
    if p.suffix:
        return False
    try:
        with p.open("rb") as f:
            return f.read(5) == b"From "
    except OSError:
        return False


def src_mbox(path: Path, ck: Checkpoint, cutoff) -> dict:
    boxes = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and (
        p.suffix.lower() in (".mbox", ".mbx") or p.name == "mbox" or _looks_mbox(p)))
    parser = BytesHeaderParser()
    total_size = read_size = 0
    for box in boxes:
        unit = str(box.relative_to(path) if path.is_dir() else box.name)
        size = box.stat().st_size
        total_size += size
        if ck.has(unit):
            read_size += ck.done[h(unit)]["extra"].get("bytes_read", size)
            continue
        acc = Acc(cutoff)
        acc.c["mailboxes"] += 1
        acc.c["mailbox_bytes"] += size
        domains, ids = Counter(), []
        st = {"header": [], "attach": 0, "in_header": False, "in_attach": False, "body_chars": 0}

        def flush():
            if not st["header"]:
                return
            msg = parser.parsebytes(b"".join(st["header"]))
            frm = msg.get("From", "") or ""
            m = EMAIL_RX.search(frm)
            sender = m.group(0).lower() if m else frm.strip().lower()
            if m:
                domains[h(sender.split("@")[1], 12)] += 1
            when = None
            try:
                when = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
                if when and when.tzinfo is None:
                    when = when.replace(tzinfo=dt.timezone.utc)
            except (TypeError, ValueError, IndexError):
                pass
            bot = bool(re.search(r"no-?reply|mailer-daemon|notifications?@|bounce", sender))
            mid = (msg.get("Message-ID") or "").strip() or None
            acc.item(when, person=sender or None, bot=bot, key=mid, kind="messages")
            if mid:
                ids.append(h(mid, 16))
            if not bot:
                acc.chars += st["body_chars"]
            if not msg.get("In-Reply-To") and not msg.get("References"):
                acc.c["thread_starters"] += 1
            for lab in (msg.get("X-Gmail-Labels") or "").split(","):
                lab = lab.strip().lower()
                if lab in GMAIL_SYSTEM:
                    acc.c["label_" + lab] += 1
            acc.c["attachments"] += st["attach"]

        read = 0
        with box.open("rb") as f:
            prev_blank = True
            for line in f:
                read += len(line)
                if line.startswith(b"From ") and prev_blank:
                    flush()
                    if OPTS.simple and read > OPTS.sample_bytes:
                        break
                    st.update(header=[], attach=0, in_header=True, in_attach=False, body_chars=0)
                elif st["in_header"]:
                    if line in (b"\n", b"\r\n"):
                        st["in_header"] = False
                    else:
                        st["header"].append(line)
                else:
                    low = line[:40].lower()
                    if low.startswith(b"content-disposition") and b"attachment" in line.lower():
                        st["attach"] += 1
                        st["in_attach"] = True
                        fm = re.search(rb'filename="?([^";\r\n]+)', line)
                        if fm:
                            acc.exts[family(fm.group(1).decode("utf-8", "replace"))] += 1
                    elif line.startswith(b"--"):
                        st["in_attach"] = False
                    elif st["in_attach"]:
                        acc.c["attachment_bytes"] += int(len(line.strip()) * 0.75)  # base64 decoded size
                    elif not re.match(rb"^[A-Za-z0-9+/=]{60,}\s*$", line) and not low.startswith(b"content-"):
                        st["body_chars"] += len(line.strip())
                prev_blank = line in (b"\n", b"\r\n")
            else:
                flush()
        read_size += read
        ck.save(unit, acc, {"domains": dict(domains), "ids": sorted(set(ids)), "bytes_read": read})
    acc, extras = ck.merged(cutoff)
    dom, seen, raw = Counter(), set(), 0
    for e in extras:
        dom.update(e.get("domains", {}))
        raw += len(e.get("ids", []))
        seen.update(e.get("ids", []))
    out = acc.summary("messages")
    top = dom.most_common(1)[0][1] if dom else 0
    out["senders"] = {"distinct_domains": len(dom), "top_domain_share": round(top / sum(dom.values()), 3) if dom else None}
    out["dedupe"] = {"messages_with_id": raw, "unique_message_ids": len(seen),
                     "overlap_share": round(1 - len(seen) / raw, 3) if raw else None}
    out["counts"]["unique_messages"] = len(seen) + (out["primary_count"] - raw)
    factor = total_size / read_size if read_size else 1.0
    return finish(out, factor, f"first {OPTS.sample_bytes // 2**20} MB of each mailbox read" if factor > 1.01 else None)


SQL_STR = re.compile(r"'(?:[^'\\]|\\.|'')*'")
TABLE_HINTS = {
    "users": ("user", "member", "account", "customer", "player", "profile"), "orders": ("order", "cart", "checkout"),
    "payments": ("payment", "invoice", "transaction", "charge", "billing", "subscription"),
    "events": ("event", "analytics", "track", "metric", "session", "click", "view"),
    "logs": ("log", "audit", "history", "activity"), "messages": ("message", "chat", "comment", "notification", "mail"),
    "content": ("post", "article", "page", "content", "media", "image", "video", "file"),
    "catalog": ("product", "item", "sku", "catalog", "inventory", "category"),
    "games": ("match", "game", "score", "level", "tournament", "team", "leaderboard"),
    "auth": ("token", "password", "auth", "permission", "role", "oauth"),
    "config": ("setting", "config", "option", "meta", "migration"),
}


def table_category(name: str) -> str:
    n = name.lower()
    for cat, keys in TABLE_HINTS.items():
        if any(k in n for k in keys):
            return cat
    return "other"


def _tkey(db, name):
    clean = name.replace("`", "").replace('"', "")
    return clean if "." in clean else db + "." + clean


def _tnew(name):
    return {"rows": 0, "cols": 0, "dated": 0, "y0": None, "y1": None, "category": table_category(name.split(".")[-1])}


def _sql_row(acc: Acc, tb: dict, year) -> None:
    if year is None or not 1980 <= year <= 2100:
        return
    tb["dated"] += 1
    tb["y0"] = year if tb["y0"] is None else min(tb["y0"], year)
    tb["y1"] = year if tb["y1"] is None else max(tb["y1"], year)
    acc.dated += 1
    acc.years[str(year)] += 1
    if year < acc.cutoff.year:  # row dates are year-granular
        acc.pre += 1
    if year < OPTS.cutoff_early.year:  # a floor: rows from the cutoff's own year are not counted
        acc.pre_early += 1
    s, e = f"{year}-01-01", f"{year}-12-31"
    acc.first = s if acc.first is None or s < acc.first else acc.first
    acc.last = e if acc.last is None or e > acc.last else acc.last


def src_sql(path: Path, ck: Checkpoint, cutoff) -> dict:
    dumps = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and p.name.lower().endswith((".sql", ".sql.gz")))
    total_size = read_size = 0
    for d in dumps:
        unit = d.name + ":" + str(d.stat().st_size)
        size = d.stat().st_size
        total_size += size
        if ck.has(unit):
            read_size += ck.done[h(unit)]["extra"].get("bytes_read", size)
            continue
        acc = Acc(cutoff)
        acc.c["dump_files"] += 1
        acc.c["dump_bytes"] += size
        tables, dbs = {}, set()
        cur_db, cur_table, copy_table, create_cols = "_default", None, None, None
        raw = d.open("rb")
        stream = gzip.GzipFile(fileobj=raw) if d.name.lower().endswith(".gz") else raw
        f = io.TextIOWrapper(stream, encoding="utf-8", errors="replace")
        t0 = time.time()
        for n, line in enumerate(f):
            if OPTS.simple and n % 1000 == 0 and raw.tell() > OPTS.sample_bytes:
                break
            if copy_table is not None:
                if line.startswith("\\."):
                    copy_table = None
                    continue
                tables[copy_table]["rows"] += 1
                m = DATE_RX.search(line)
                _sql_row(acc, tables[copy_table], int(m.group(1)) if m else None)
                for fld in line.split("\t"):
                    if len(fld) >= 100:
                        acc.c["long_text_values"] += 1
                        acc.c["long_text_chars"] += len(fld)
                continue
            if create_cols is not None:
                if line.lstrip().startswith(")"):
                    tables[cur_table]["cols"] = create_cols
                    create_cols = None
                elif line.strip() and not re.match(r"\s*(PRIMARY|KEY|UNIQUE|CONSTRAINT|INDEX|FOREIGN|FULLTEXT)\b", line, re.I):
                    create_cols += 1
                continue
            up = line[:40].upper()
            if up.startswith(("USE ", "CREATE DATABASE", "\\CONNECT", "CREATE SCHEMA")):
                m = re.search(r"[`\"]?([\w$-]+)[`\"]?\s*;?\s*$", line.strip().rstrip(";"))
                cur_db = m.group(1) if m else cur_db
                dbs.add(cur_db)
            elif up.startswith("CREATE TABLE"):
                m = re.search(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([`\"\w.$-]+)", line, re.I)
                if m:
                    cur_table = _tkey(cur_db, m.group(1))
                    tables.setdefault(cur_table, _tnew(m.group(1)))
                    create_cols = 0
            elif up.startswith(("INSERT INTO", "REPLACE INTO", "INSERT IGNORE")):
                m = re.search(r"INTO\s+([`\"\w.$-]+)", line, re.I)
                if not m:
                    continue
                tb = tables.setdefault(_tkey(cur_db, m.group(1)), _tnew(m.group(1)))
                values = line[line.upper().find("VALUES") + 6:] if "VALUES" in line.upper() else line

                def mark(s):
                    v = s.group(0)
                    if len(v) >= 102:
                        acc.c["long_text_values"] += 1
                        acc.c["long_text_chars"] += len(v) - 2
                    dm = DATE_RX.search(v) if len(v) < 40 else None
                    return "D" + dm.group(1) if dm else "S"

                for tup in SQL_STR.sub(mark, values).split("),("):
                    tb["rows"] += 1
                    ym = re.search(r"D(\d{4})", tup)
                    _sql_row(acc, tb, int(ym.group(1)) if ym else None)
            elif up.startswith("COPY "):
                m = re.match(r"COPY\s+([\w.\"$-]+)", line, re.I)
                if m:
                    copy_table = _tkey(cur_db, m.group(1))
                    tables.setdefault(copy_table, _tnew(m.group(1)))
            if n % 500_000 == 0 and n:
                log(f"sql: {n:,} lines read ({time.time() - t0:.0f}s)")
        read = raw.tell() or size
        raw.close()
        read_size += read
        acc.c["databases"] += max(1, len(dbs))
        acc.c["tables"] += len(tables)
        acc.c["tables_with_rows"] += sum(1 for tb in tables.values() if tb["rows"])
        acc.c["rows"] += sum(tb["rows"] for tb in tables.values())
        sig = sorted(f"{h(k, 10)}:{tb['cols']}" for k, tb in tables.items())
        top = sorted(tables.values(), key=lambda tb: -tb["rows"])[:25]
        extra = {"schema_signature": h("|".join(sig), 24), "table_keys": sorted(h(k, 12) for k in tables),
                 "row_vector": sorted([h(k, 12), tb["rows"]] for k, tb in tables.items()), "bytes_read": read,
                 "top_tables": [{"rank": i + 1, "category": tb["category"], "rows": tb["rows"], "columns": tb["cols"],
                                 "dated_rows": tb["dated"], "first_year": tb["y0"], "last_year": tb["y1"]}
                                for i, tb in enumerate(top)]}
        ck.save(unit, acc, extra)
    acc, extras = ck.merged(cutoff)
    out = acc.summary("rows")
    out["text"] = {"characters": acc.c["long_text_chars"], "token_estimate": acc.c["long_text_chars"] // 4,
                   "note": "long text = string values of 100+ characters"}
    out["dumps"] = [{"schema_signature": e["schema_signature"], "tables": len(e["table_keys"]),
                     "rows": sum(r for _, r in e["row_vector"]), "top_tables": e["top_tables"]} for e in extras]
    out["fingerprints"]["table_keys"] = sorted({k for e in extras for k in e["table_keys"]})
    out["fingerprints"]["schema_signatures"] = sorted({e["schema_signature"] for e in extras})
    out["note"] = "A row's date is the first date-like value in it, so dates are year-granular approximations."
    factor = total_size / read_size if read_size else 1.0
    return finish(out, factor, f"first {OPTS.sample_bytes // 2**20} MB of each dump read; table count is a floor"
                  if factor > 1.01 else None, keep=("tables", "tables_with_rows", "databases", "dump_files", "dump_bytes"))


def src_bigquery(path: Path, ck: Checkpoint, cutoff) -> dict:
    t = Tree(path)
    acc = Acc(cutoff)
    datasets, projects = set(), set()
    shards, shard_days = Counter(), {}
    for f, _ in t.files():
        low = f.lower()
        rows = []
        try:
            if low.endswith((".json", ".jsonl")):
                raw = t.open(f).read().decode("utf-8", "replace")
                try:
                    data = json.loads(raw)
                    rows = data if isinstance(data, list) else data.get("tables") or data.get("rows") or [data]
                except ValueError:
                    rows = [json.loads(x) for x in raw.splitlines() if x.strip().startswith("{")]
            elif low.endswith(".csv"):
                with t.open(f) as rawf:
                    rows = list(csv.DictReader(io.TextIOWrapper(rawf, "utf-8-sig", errors="replace")))
        except (ValueError, OSError):
            acc.c["unreadable_files"] += 1
            continue
        for r in rows:
            if not isinstance(r, dict):
                continue
            ref = r.get("tableReference") or {}
            ds = ref.get("datasetId") or r.get("table_schema") or r.get("dataset_id") or r.get("datasetId")
            pj = ref.get("projectId") or r.get("table_catalog") or r.get("project_id")
            name = ref.get("tableId") or r.get("table_name") or r.get("table_id") or r.get("tableId")
            if not name:
                continue
            datasets.add(h(f"{pj}.{ds}"))
            if pj:
                projects.add(h(pj))
            kind = str(r.get("type") or r.get("table_type") or "TABLE").upper()
            acc.c["views" if "VIEW" in kind else "tables"] += 1
            try:
                acc.c["rows"] += int(float(r.get("numRows") or r.get("row_count") or r.get("total_rows") or 0))
                acc.c["bytes"] += int(float(r.get("numBytes") or r.get("size_bytes") or r.get("total_logical_bytes") or 0))
            except ValueError:
                pass
            acc.item(to_dt(r.get("creationTime") or r.get("creation_time")), key=f"{pj}.{ds}.{name}", kind="table_entries")
            m = re.match(r"(.*?)_?(\d{8})$", name)
            if m:
                base = h(f"{ds}.{m.group(1)}", 10)
                shards[base] += 1
                day = m.group(2)
                lo, hi = shard_days.get(base, (day, day))
                shard_days[base] = (min(lo, day), max(hi, day))
    out = acc.summary("rows", dated_basis="table_entries")
    out["counts"]["datasets"] = len(datasets)
    out["counts"]["projects"] = len(projects)
    fmt_day = lambda d: f"{d[:4]}-{d[4:6]}-{d[6:]}"  # noqa: E731
    out["sharded_tables"] = [{"daily_shards": n, "first_day": fmt_day(shard_days[b][0]), "last_day": fmt_day(shard_days[b][1])}
                             for b, n in shards.most_common(20) if n >= 7]
    if out["sharded_tables"]:
        out["span"]["first"] = min([s["first_day"] for s in out["sharded_tables"]] + [out["span"]["first"] or "9999"])
        out["span"]["last"] = max([s["last_day"] for s in out["sharded_tables"]] + [out["span"]["last"] or "0000"])
    out["note"] = "Metadata only: tables, rows and bytes as BigQuery reports them. Daily-sharded tables give the analytics date span."
    return finish(out, 1.0, None)


def _quick_fp(p: Path, size: int) -> str | None:
    """Size + first and last 64 KiB: cheap enough for millions of files, good enough to spot copies."""
    if size == 0:
        return None
    try:
        with p.open("rb") as f:
            head = f.read(65536)
            if size > 131072:
                f.seek(-65536, 2)
                head += f.read(65536)
        return hashlib.sha256(str(size).encode() + head).hexdigest()[:24]
    except OSError:
        return None


def _first_line(p: Path) -> str | None:
    """The header line of a CSV, read in memory to recognise string tables. Never stored."""
    st = p.stat()
    if st.st_size > 0 and getattr(st, "st_blocks", 1) == 0:
        return None  # a cloud placeholder: reading it would download it
    with p.open("rb") as f:
        return f.read(4096).split(b"\n", 1)[0].decode("utf-8-sig", "replace")


def sum_nested(items: list):
    """Add up dicts of counts (nested dicts allowed)."""
    if not items:
        return None
    out = {}
    for d in items:
        for k, v in d.items():
            if isinstance(v, dict):
                out[k] = sum_nested([out.get(k) or {}, v])
            else:
                out[k] = out.get(k, 0) + v
    return out


def src_files(path: Path, ck: Checkpoint, cutoff) -> dict:
    tops = sorted(p for p in path.iterdir() if not p.name.startswith(".")) if path.is_dir() else [path]
    for top in tops:
        unit = top.name
        if ck.has(unit):
            continue
        acc = Acc(cutoff)
        seen = set()
        studio = studio_signals.StudioCounter()
        walker = [(str(top.parent), [], [top.name])] if top.is_file() else os.walk(top)
        for root, dirs, files in walker:
            studio.folder(Path(root).name, list(dirs) + list(files))
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
            acc.c["folders"] += 1
            for name in files:
                p = Path(root, name)
                studio.file(name, None if OPTS.simple else (lambda p=p: _first_line(p)))
                try:
                    st = p.lstat()
                except OSError:
                    acc.c["unreadable_files"] += 1
                    continue
                if not p.is_file() or name.startswith("."):
                    continue
                fam = family(name)
                acc.item(dt.datetime.fromtimestamp(st.st_mtime, tz=dt.timezone.utc), kind="files")
                acc.c["bytes"] += st.st_size
                acc.c["files_" + fam] += 1
                acc.c["bytes_" + fam] += st.st_size
                if name.lower().endswith((".gdoc", ".gsheet", ".gslides", ".gform", ".gdraw")):
                    acc.c["cloud_only_google_docs"] += 1
                if st.st_size > 0 and getattr(st, "st_blocks", 1) == 0:
                    acc.c["placeholders_not_downloaded"] += 1
                    continue
                if OPTS.simple:
                    continue  # listing only: no content is opened
                if name.lower().endswith(".zip"):
                    try:
                        with zipfile.ZipFile(p) as z:
                            members = [i for i in z.infolist() if not i.is_dir()]
                            acc.c["zip_members"] += len(members)
                            acc.c["zip_uncompressed_bytes"] += sum(i.file_size for i in members)
                    except (zipfile.BadZipFile, OSError, RuntimeError):
                        acc.c["unreadable_zips"] += 1
                fp = _quick_fp(p, st.st_size)
                if fp:
                    acc.add_key(fp)
                    if fp in seen:
                        acc.c["duplicate_files"] += 1
                        acc.c["duplicate_bytes"] += st.st_size
                    seen.add(fp)
        ck.save(unit, acc, {"studio": studio.result()})
    acc, extras = ck.merged(cutoff)
    out = acc.summary("files")
    out["studio_files"] = sum_nested([e["studio"] for e in extras if e.get("studio")]) or studio_signals.StudioCounter().result()
    fams = {k[6:]: v for k, v in acc.c.items() if k.startswith("files_")}
    out["by_family"] = {f: {"files": n, "bytes": acc.c.get("bytes_" + f, 0)} for f, n in sorted(fams.items(), key=lambda kv: -kv[1])}
    total = acc.c["bytes"] or 1
    out["working_documents"] = {"files": sum(fams.get(f, 0) for f in WORKING_DOCS),
                                "bytes": sum(acc.c.get("bytes_" + f, 0) for f in WORKING_DOCS)}
    out["media_bytes_share"] = round(sum(acc.c.get("bytes_" + f, 0) for f in MEDIA) / total, 3)
    out["counts"] = {k: v for k, v in out["counts"].items() if not k.startswith(("files_", "bytes_"))}
    out["note"] = "Dates are file modification times, which copies and syncs can reset. Duplicates are counted within this source only."
    if OPTS.simple:
        out["fingerprints"] = {"item_sketch": []}
    return finish(out, 1.0, "listing only: no fingerprints, duplicates or zip contents" if OPTS.simple else None)


SOURCES = {
    "slack": src_slack, "discord": src_discord, "notion": src_notion, "clickup": src_tickets,
    "jira": src_tickets, "tickets": src_tickets, "mbox": src_mbox, "sql": src_sql,
    "bigquery": src_bigquery, "files": src_files,
}
STRUCTURAL = {"conversations", "channels", "servers", "top_level_roots", "databases", "tables", "tables_with_rows", "dump_files",
              "dump_bytes", "mailboxes", "mailbox_bytes", "export_files", "export_bytes", "datasets", "projects", "folders"}
UNIT_THRESHOLDS = {"messages": 10_000, "tickets": 1_000, "pages": 500, "database_rows": 2_000, "rows": 100_000, "files": 1_000}


def finish(out: dict, factor: float, note: str | None, keep=()) -> dict:
    """Scale sampled counts to the whole source (simple mode) and attach mode, estimate flags and a recommendation."""
    out["counts"] = {k: v for k, v in out["counts"].items() if not k.startswith("_")}
    if factor > 1.01:
        sc = lambda v: int(round(v * factor)) if isinstance(v, (int, float)) and not isinstance(v, bool) else v  # noqa: E731
        out["primary_count"] = sc(out["primary_count"])
        out["human_count"] = sc(out["human_count"])
        out["counts"] = {k: (v if k.startswith(tuple(STRUCTURAL)) or k in keep else sc(v)) for k, v in out["counts"].items()}
        out["by_year"] = {k: sc(v) for k, v in out["by_year"].items()}
        out["pre_cutoff"] = sc(out["pre_cutoff"])
        if out.get("pre_chatgpt") is not None:
            out["pre_chatgpt"] = sc(out["pre_chatgpt"])
        out["last_12_months"] = sc(out["last_12_months"])
        out["text"] = {k: sc(v) for k, v in out["text"].items()}
        out["people"]["note"] = "people counts come from a sample and are a floor"
    out["estimate"] = factor > 1.01 or (OPTS.simple and note is not None)
    out["sample_note"] = note
    n = out["primary_count"] or 0
    unit = out["primary_unit"]
    reasons = []
    if n >= UNIT_THRESHOLDS.get(unit, 1_000):
        reasons.append(f"{UNIT_THRESHOLDS.get(unit, 1_000):,}+ {unit}")
    if (out.get("pre_cutoff_share") or 0) >= 0.3:
        reasons.append("30%+ dated before the cutoff")
    if (out["people"]["distinct"] or 0) >= 3:
        reasons.append("3+ people")
    if (out.get("dated_share") or 0) >= 0.8:
        reasons.append("most items carry dates")
    size = max(out["counts"].get(k, 0) for k in ("export_bytes", "mailbox_bytes", "dump_bytes", "bytes")) if out["counts"] else 0
    out["recommendation"] = {
        "full_run": "already full" if not OPTS.simple else ("recommended" if len(reasons) >= 3 else "optional" if len(reasons) == 2 else "not worth it"),
        "reasons": reasons, "estimated_full_run_minutes": int(1 + size / (40 * 2**20) / 60)}
    out["mode"] = "simple" if OPTS.simple else "full"
    return out


# --------------------------------------------------------------------------
# labels, cutoffs, restrictions, version history, category status (studio assessment)
# --------------------------------------------------------------------------

LABELS = ("verified", "estimated", "self_reported", "unknown", "not_applicable")
CATEGORY_KEYS = ("source_control", "work_tracking", "design_knowledge", "builds_ci", "crash_reports", "profiling",
                 "telemetry", "qa_playtest", "art_source", "engine_content", "audio", "narrative_localisation",
                 "production_client", "communication", "player_support_community", "liveops_backend",
                 "business_systems", "servers_storage")
CATEGORY_STATUSES = ("inspected", "exists_inaccessible", "self_reported", "confirmed_not_used", "unknown")
STATUS_RANK = {s: i for i, s in enumerate(reversed(CATEGORY_STATUSES))}  # unknown 0 ... inspected 4
STATUS_LABEL = {"inspected": "verified", "exists_inaccessible": "unknown", "self_reported": "self_reported",
                "confirmed_not_used": "self_reported", "unknown": "unknown"}
SOURCE_CATEGORY = {"slack": "communication", "discord": "communication", "mbox": "communication",
                   "notion": "design_knowledge", "clickup": "work_tracking", "jira": "work_tracking",
                   "tickets": "work_tracking", "sql": "liveops_backend", "bigquery": "telemetry", "files": "servers_storage"}
FLAG_KEYS = ("client_owned", "platform_nda", "third_party_middleware", "player_personal_data", "staff_personal_data", "secrets")
OWNERSHIP = ("own", "client_owned", "unclear")
VERSION_HISTORY = ("exported", "retained_not_exported", "not_retained", "unknown", "not_applicable")
DOC_SOURCES = {"notion", "files"}
SIZE_KEYS = ("export_bytes", "bytes", "dump_bytes", "mailbox_bytes")


def lab(label: str, method: str | None = None, scope: str | None = None) -> dict:
    out = {"label": label}
    if method:
        out["method"] = method
    if scope:
        out["scope"] = scope
    return out


def source_labels(doc: dict) -> dict:
    """Label every material number of one source (SPEC section 1). Unknown numbers are null with label unknown."""
    src = doc.get("source")
    est = bool(doc.get("estimate"))
    sample = doc.get("sample_note") or "simple mode: a sample of the export, scaled by size"
    base = lab("estimated", sample) if est else lab("verified", scope=f"this {src} export only")
    dates = base
    if src == "sql":
        dates = lab("estimated", "a row's date is the first date-like value in it (year-granular)")
    elif src == "files":
        dates = lab("estimated", "file modification times, which copies and syncs can reset")
    people = dict(base)
    if est:
        people = lab("estimated", "people seen in a sample; a floor")
    out = {"primary_count": base, "human_count": base if doc.get("human_count") is not None else lab("unknown"),
           "people.distinct": people if (doc.get("people") or {}).get("distinct") is not None else lab("unknown"),
           "people.peak_active_in_a_month": people if (doc.get("people") or {}).get("peak_active_in_a_month") is not None else lab("unknown"),
           "text.token_estimate": lab("estimated", "characters / 4"),
           "span": dates if (doc.get("span") or {}).get("first") else lab("unknown"),
           "pre_cutoff": dates, "pre_cutoff_share": dates,
           "pre_chatgpt": dates if doc.get("pre_chatgpt") is not None else lab("unknown"),
           "pre_chatgpt_share": dates if doc.get("pre_chatgpt_share") is not None else lab("unknown")}
    for k in SIZE_KEYS:
        if k in (doc.get("counts") or {}):
            out["counts." + k] = lab("verified", scope="bytes on disk of this export")
    if src == "sql":
        out["pre_chatgpt"] = lab("estimated", "year-granular row dates: rows from the cutoff's own year are not counted (a floor)")
    if doc.get("traceable"):
        out["traceable.by_type"] = lab(doc["traceable"]["label"], doc["traceable"]["method"])
    return out


def cutoffs_block(doc: dict, early: str) -> dict:
    lb = doc.get("labels") or source_labels(doc)
    late = {"date": doc.get("cutoff"), "count": doc.get("pre_cutoff"), "share": doc.get("pre_cutoff_share"),
            "label": lb["pre_cutoff"]["label"] if doc.get("pre_cutoff_share") is not None else "unknown"}
    e = {"date": doc.get("cutoff_early") or early, "count": doc.get("pre_chatgpt"), "share": doc.get("pre_chatgpt_share"),
         "label": lb["pre_chatgpt"]["label"] if doc.get("pre_chatgpt") is not None else "unknown"}
    return {"pre_2025": late, "pre_chatgpt": e}


def flag(value=None, label="unknown", method=None, count=None) -> dict:
    out = {"value": value, "label": label}
    if method:
        out["method"] = method
    if count is not None:
        out["count"] = count
    return out


def parse_flags(items: list) -> dict:
    """--flag NAME or --flag NAME=yes|no, self-reported by the owner."""
    out = {}
    for it in items or []:
        name, _, val = it.partition("=")
        name = name.strip().lower()
        if name not in FLAG_KEYS:
            raise ValueError(f"unknown restriction flag {name!r}; use one of {', '.join(FLAG_KEYS)}")
        v = val.strip().lower()
        if v not in ("", "yes", "true", "no", "false"):
            raise ValueError(f"--flag {name}= takes yes or no")
        out[name] = v in ("", "yes", "true")
    return out


def restrictions_block(doc: dict, ownership: str | None = None, flags: dict | None = None) -> dict:
    """Restriction flags (SPEC section 4): recorded, not ruled on. Unknown unless measured or self-reported."""
    f = {k: flag() for k in FLAG_KEYS}
    src, c = doc.get("source"), doc.get("counts") or {}
    pii = (c.get("items_with_email_pattern") or 0) + (c.get("items_with_phone_pattern") or 0)
    users_tables = sum(1 for d in doc.get("dumps") or [] for t in d.get("top_tables") or [] if t.get("category") == "users")
    if src in ("sql", "bigquery") and (users_tables or pii):
        f["player_personal_data"] = flag(True, "estimated", "user-like tables or email/phone patterns found; the database "
                                         "may hold player accounts", count=users_tables or pii)
    elif src in ("slack", "discord", "mbox", "jira", "clickup", "tickets", "notion") and pii:
        f["staff_personal_data"] = flag(True, "estimated", "items holding email or phone patterns (personal data of "
                                        "staff or contacts)", count=pii)
    sf = doc.get("studio_files") or {}
    if sf.get("secret_like_files"):
        f["secrets"] = flag(True, "estimated", "credential-like file names (.env, keys, keystores, password vaults)",
                            count=sf["secret_like_files"])
    if sf.get("certification_docs"):
        f["platform_nda"] = flag(True, "estimated", "platform certification documents by file name", count=sf["certification_docs"])
    am = sf.get("audio_middleware") or {}
    mw = sum(am.values()) + sf.get("asset_store_packages", 0) if sf else 0
    if mw:
        f["third_party_middleware"] = flag(True, "estimated", "audio middleware projects or Asset Store packages", count=mw)
    own = ownership or "own"
    for k, v in (flags or {}).items():
        f[k] = flag(v, "self_reported")
    if own == "client_owned":
        f["client_owned"] = flag(True, "self_reported")
    return {"ownership": own, "ownership_basis": "self_reported" if ownership else "default (the seller owns its data)",
            "flags": f}


def version_history_block(doc: dict, status: str | None = None) -> dict:
    src = doc.get("source")
    if status:
        return {"status": status, "label": "self_reported"}
    if src not in DOC_SOURCES:
        return {"status": "not_applicable", "label": "not_applicable", "method": "not a document source"}
    note = ("a Markdown/CSV export carries the current version of each page only; ask whether page history is kept in the tool"
            if src == "notion" else "file listings show the current version only; ask whether the storage keeps versions")
    return {"status": "unknown", "label": "unknown", "method": note}


def annotate(doc: dict, early: str, ownership=None, flags=None, version_history=None) -> dict:
    """Add the studio-assessment blocks to one source doc. Old flat fields are kept as they are."""
    doc.setdefault("cutoff_early", early)
    if "pre_chatgpt" not in doc:
        doc["pre_chatgpt"] = None
        doc["pre_chatgpt_share"] = None
    doc["labels"] = source_labels(doc)
    doc["cutoffs"] = cutoffs_block(doc, early)
    if "restrictions" not in doc or ownership or flags:
        doc["restrictions"] = restrictions_block(doc, ownership, flags)
    if "version_history" not in doc or version_history:
        doc["version_history"] = version_history_block(doc, version_history)
    return doc


def load_status(out: Path) -> dict:
    p = out / "status.json"
    if p.exists():
        return json.loads(p.read_text("utf-8"))
    return {"categories": {}, "connectors": {}}


def tool_list() -> dict:
    return json.loads((Path(__file__).resolve().parent.parent / "docs" / "tools.json").read_text("utf-8"))


def best(a: str, b: str) -> str:
    return a if STATUS_RANK[a] >= STATUS_RANK[b] else b


def category_status(docs: list, status: dict) -> dict:
    """Every category of the studio checklist with a status (SPEC section 3). Never drops one."""
    cs = {k: {"status": "unknown", "evidence": "not established", "sources": 0} for k in CATEGORY_KEYS}
    for d in docs:
        tag = next((t.split(":", 1)[1] for t in d.get("tags") or [] if t.startswith("category:")), None)
        key = tag if tag in cs else SOURCE_CATEGORY.get(d.get("source"))
        found = {key: 1} if key else {}
        if d.get("studio_files"):
            for k in studio_signals.categories_found(d["studio_files"]):
                found.setdefault(k, 1)
        for k in found:
            cs[k]["sources"] += 1
            if cs[k]["status"] != "inspected":
                cs[k].update(status="inspected", evidence="measured export" if k == key else "files found in a measured folder")
    for k, st in (status.get("categories") or {}).items():
        if k in cs:
            new = best(cs[k]["status"], st)
            if new != cs[k]["status"]:
                cs[k].update(status=new, evidence={"exists_inaccessible": "exists, not accessible to this run",
                                                   "self_reported": "reported by the owner",
                                                   "confirmed_not_used": "owner confirmed it is not used"}.get(new, cs[k]["evidence"]))
    for v in cs.values():
        v["label"] = STATUS_LABEL[v["status"]]
    return cs


def connectors_block(docs: list, status: dict, tools: dict) -> dict:
    """The explicit connector check (SPEC section 8): telemetry, backends, stores and ads, each with a status."""
    tagged = {t.split(":", 1)[1].lower() for d in docs for t in d.get("tags") or [] if t.startswith("connector:")}
    out = {}
    reported = {k.lower(): v for k, v in (status.get("connectors") or {}).items()}
    for group, names in tools.get("connector_prompts", {}).items():
        for n in names:
            st = "inspected" if n.lower() in tagged else "unknown"
            st = best(st, reported.get(n.lower(), "unknown"))
            out[n] = {"group": group, "status": st, "label": STATUS_LABEL[st]}
    return out


def cmd_status(out: Path, cats: list, conns: list) -> int:
    """Record owner answers: category statuses and connector statuses, merged into <out>/status.json."""
    tools = tool_list()
    names = {t["tool"].lower(): t["tool"] for t in tools["tools"]}
    st = load_status(out)
    for item in cats or []:
        k, _, v = item.partition("=")
        k, v = k.strip(), v.strip()
        if k not in CATEGORY_KEYS or v not in CATEGORY_STATUSES:
            log(f"refused {item!r}: use KEY=STATUS with KEY one of {', '.join(CATEGORY_KEYS)} and STATUS one of {', '.join(CATEGORY_STATUSES)}")
            return 2
        st.setdefault("categories", {})[k] = v
    for item in conns or []:
        k, _, v = item.rpartition("=")
        k, v = k.strip(), v.strip()
        if k.lower() not in names or v not in CATEGORY_STATUSES:
            log(f"refused {item!r}: use \"TOOL=STATUS\" with a tool name from docs/tools.json and STATUS one of {', '.join(CATEGORY_STATUSES)}")
            return 2
        st.setdefault("connectors", {})[names[k.lower()]] = v
    out.mkdir(parents=True, exist_ok=True)
    atomic_write(out / "status.json", json.dumps(st, indent=2, sort_keys=True))
    log(f"wrote {out / 'status.json'} ({len(st.get('categories', {}))} categories, {len(st.get('connectors', {}))} connectors); "
        "run `report` to merge")
    return 0


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


def fmt(n) -> str:
    if n is None:
        return "n/a"
    if isinstance(n, float):
        return f"{n:.1%}"
    return f"{n:,}"


def human_bytes(n) -> str:
    if not n:
        return "n/a"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.1f} {unit}"
        n /= 1024


def render(docs: list, cutoff: str, dream: dict | None = None, cats: dict | None = None, conns: dict | None = None,
           early: str = "2022-11-30") -> str:
    modes = {d.get("mode", "full") for d in docs}
    lines = ["# Business data measurement", "",
             f"Produced with {TOOL} {VERSION} ({', '.join(sorted(modes))} mode). Counts only: no content, names, titles, paths or ids. "
             "Figures marked ~ are estimates scaled from a sample.", "",
             "## 1. Headline", "",
             "| source | label | unit | count | human share | first | last | pre-cutoff | peak people/month | tokens | size | full run |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in docs:
        c = d["counts"]
        size = c.get("export_bytes") or c.get("bytes") or c.get("dump_bytes") or c.get("mailbox_bytes")
        est = "~" if d.get("estimate") else ""
        lines.append(f"| {d['source']} | {d['label']} | {d['primary_unit']} | {est}{fmt(d['primary_count'])} | {fmt(d.get('human_share'))} | "
                     f"{d['span']['first'] or 'n/a'} | {d['span']['last'] or 'n/a'} | {fmt(d['pre_cutoff_share'])} | "
                     f"{fmt(d['people'].get('peak_active_in_a_month'))} | {est}{fmt(d['text']['token_estimate'])} | {human_bytes(size)} | "
                     f"{d.get('recommendation', {}).get('full_run', 'n/a')} |")
    lines += ["", f"Pre-cutoff = share of dated items before {cutoff}. Tokens = characters / 4.", ""]
    lines += ["| source | label | pre-2025 items | pre-2025 share | pre-ChatGPT items | pre-ChatGPT share | label |",
              "|---|---|---|---|---|---|---|"]
    for d in docs:
        co = d.get("cutoffs") or {}
        a, b = co.get("pre_2025") or {}, co.get("pre_chatgpt") or {}
        lines.append(f"| {d['source']} | {d['label']} | {fmt(a.get('count'))} | {fmt(a.get('share'))} | {fmt(b.get('count'))} | "
                     f"{fmt(b.get('share'))} | {b.get('label', 'unknown')} |")
    lines += ["", f"Pre-2025 = before {cutoff}; pre-ChatGPT = before {early}. Unknown is shown as n/a, never as 0.", ""]
    if cats:
        lines += ["## Category status", "", "Every category of the studio checklist, with a status. None is dropped.", "",
                  "| category | status | evidence | sources | label |", "|---|---|---|---|---|"]
        lines += [f"| {k.replace('_', ' ')} | {v['status'].replace('_', ' ')} | {v['evidence']} | {v['sources']} | {v['label']} |"
                  for k, v in cats.items()] + [""]
    if conns:
        lines += ["## Connectors check", "", "Telemetry, backends, stores and ads the agent asked about explicitly.", "",
                  "| group | connector | status | label |", "|---|---|---|---|"]
        lines += [f"| {v['group']} | {k} | {v['status'].replace('_', ' ')} | {v['label']} |" for k, v in conns.items()] + [""]
    for i, d in enumerate(docs, 2):
        lines += [f"## {i}. {d['source']}: {d['label']}" + (" (estimate)" if d.get("estimate") else ""), ""]
        if d.get("sample_note"):
            lines += [f"_Sample: {d['sample_note']}._", ""]
        lines += ["| metric | value |", "|---|---|"]
        for k, v in d["counts"].items():
            lines.append(f"| {k.replace('_', ' ')} | {human_bytes(v) if k.endswith('bytes') or k.endswith('bytes_referenced') else fmt(v)} |")
        p = d["people"]
        sp = d["span"]
        lines += [f"| human items | {fmt(d.get('human_count'))} ({fmt(d.get('human_share'))}) |",
                  f"| last human item | {sp.get('last_human') or 'n/a'} |",
                  f"| people (distinct, hashed) | {fmt(p['distinct'])} |", f"| bot accounts | {fmt(p['bots'])} |",
                  f"| peak active people in one month | {fmt(p.get('peak_active_in_a_month'))} ({p.get('peak_month') or 'n/a'}) |",
                  f"| median active people, last 12 months | {fmt(p.get('median_active_last_12_months'))} |",
                  f"| top person share / top 5 | {fmt(p['top1_share'])} / {fmt(p['top5_share'])} |",
                  f"| characters / token estimate | {fmt(d['text']['characters'])} / {fmt(d['text']['token_estimate'])} |",
                  f"| dated share | {fmt(d['dated_share'])} |", f"| active months | {fmt(d['active_months'])} |",
                  f"| items in last 12 active months | {fmt(d['last_12_months'])} |", ""]
        tr = d.get("traceable")
        if tr:
            bt = tr["by_type"]
            lines += ["| ticket type | total | resolved | hashed resolved keys |", "|---|---|---|---|"]
            lines += [f"| {t} | {fmt(bt[t]['total'])} | {fmt(bt[t]['resolved'])} | {fmt(len(tr['resolved_key_hashes'][t]))} |"
                      for t in bt] + ["", f"_Traceable work: {tr['method']} ({tr['label']})._", ""]
        sf = d.get("studio_files")
        if sf:
            bits = [f"build logs {fmt(sf['build_ci']['build_logs'])}", f"CI configs {fmt(sf['build_ci']['ci_configs'])}",
                    f"crash dumps {fmt(sf['crash_dumps']['dumps'])}", f"profiling captures {fmt(sf['profiling']['captures'])}",
                    f"QA and certification documents {fmt(sf['qa_cert_docs'])}",
                    f"Wwise/FMOD projects {fmt(sf['audio_middleware']['wwise_projects'] + sf['audio_middleware']['fmod_projects'])}",
                    f"localisation files {fmt(sf['localisation']['files'])}",
                    "engine content " + ", ".join(f"{k} {fmt(v)}" for k, v in sf["engine_content"].items())]
            lines += ["Studio files: " + "; ".join(bits) + ".", ""]
        rs = d.get("restrictions")
        if rs:
            on = [f"{k.replace('_', ' ')} ({v['label']})" for k, v in rs["flags"].items() if v["value"]]
            lines += [f"Restrictions (recorded, not ruled on): ownership {rs['ownership'].replace('_', ' ')}; "
                      + ("flags: " + ", ".join(on) if on else "no flag established") + ".", ""]
        vh = d.get("version_history")
        if vh and vh.get("status") != "not_applicable":
            lines += [f"Version history: {vh['status'].replace('_', ' ')} ({vh['label']}).", ""]
        if d.get("description_or_comment_share") is not None:
            lines += [f"Tickets with a real description or comment: {fmt(d['description_or_comment_share'])}.", ""]
        if d.get("dedupe"):
            dd = d["dedupe"]
            lines += [f"Unique messages after Message-ID dedupe: {fmt(d['counts'].get('unique_messages'))} "
                      f"(overlap {fmt(dd['overlap_share'])} across mailboxes).", ""]
        if d["by_year"]:
            lines += ["| year | items |", "|---|---|"] + [f"| {y} | {fmt(n)} |" for y, n in d["by_year"].items()] + [""]
        if d.get("by_family"):
            lines += ["| file family | files | size |", "|---|---|---|"]
            lines += [f"| {f} | {fmt(v['files'])} | {human_bytes(v['bytes'])} |" for f, v in d["by_family"].items()] + [""]
            lines += [f"Working documents: {fmt(d['working_documents']['files'])} files, {human_bytes(d['working_documents']['bytes'])}. "
                      f"Image, video and audio are {fmt(d['media_bytes_share'])} of bytes.", ""]
        if d.get("attachments_by_family"):
            lines += ["Attachments by family: " + ", ".join(f"{k} {fmt(v)}" for k, v in d["attachments_by_family"].items()), ""]
        for dump in d.get("dumps", []):
            lines += [f"Dump with {fmt(dump['tables'])} tables and {fmt(dump['rows'])} rows. Largest tables (names withheld):", "",
                      "| rank | category | rows | columns | years |", "|---|---|---|---|---|"]
            for tb in dump["top_tables"][:10]:
                yrs = f"{tb['first_year']}-{tb['last_year']}" if tb["first_year"] else "n/a"
                lines.append(f"| {tb['rank']} | {tb['category']} | {fmt(tb['rows'])} | {fmt(tb['columns'])} | {yrs} |")
            lines.append("")
        for s in d.get("sharded_tables", [])[:5]:
            lines.append(f"- daily-sharded table: {fmt(s['daily_shards'])} days, {s['first_day']} to {s['last_day']}")
        if d.get("senders"):
            lines.append(f"- sender domains: {fmt(d['senders']['distinct_domains'])}; top domain share {fmt(d['senders']['top_domain_share'])}")
        r = d.get("recommendation")
        if r and d.get("mode") == "simple":
            lines += ["", f"**Full run: {r['full_run']}** ({'; '.join(r['reasons']) or 'little data'}); about {r['estimated_full_run_minutes']} minutes."]
        if d.get("note"):
            lines += ["", f"_Note: {d['note']}_"]
        lines.append("")
    lines += ["## Caveats", "",
              "- People are counted by hashed account id or email; one person with two accounts counts twice.",
              "- Peak active people counts distinct humans with a dated item in a month; sources that record only creators give a floor.",
              "- `items_with_email_pattern` and `items_with_phone_pattern` count items that contain such a pattern. Matches are never stored.",
              "- Attachment bytes are what the export references; files that are not in the export were not downloaded.",
              "- Every number carries a label in measure.json (`labels`): verified, estimated (with a method), self-reported, "
              "unknown or not applicable. Unknown is null, never 0.", ""]
    lines += dream_mod().section(dream)
    return "\n".join(lines)


def dream_mod():
    """add_dream.py next to this script: the "Why this is special" slot, its validation and its report section."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("add_dream", Path(__file__).resolve().parent / "add_dream.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def privacy_scan(doc) -> list:
    bad = []
    stack = [("", doc)]
    while stack:
        p, o = stack.pop()
        if isinstance(o, dict):
            stack.extend((f"{p}.{k}", v) for k, v in o.items())
        elif isinstance(o, list):
            stack.extend((f"{p}[{i}]", v) for i, v in enumerate(o))
        elif isinstance(o, str) and not p.endswith((".label", ".note")):
            if EMAIL_RX.search(o) or re.search(r"(^|\s)/(Users|home|Volumes|private|tmp|var)/|[A-Za-z]:\\", o):
                bad.append(p)
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Count company data exports locally. Counts only.")
    ap.add_argument("source", choices=sorted(SOURCES) + ["report", "status"])
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=["simple", "full"], default="full",
                    help="full = every record (default); simple = optional fast sampled pass, only when a quick look is asked for")
    ap.add_argument("--label", help="name for this source in the report (default: source name)")
    ap.add_argument("--tag", action="append", default=[], help="free-form tag for cross-linking, e.g. project:alpha")
    ap.add_argument("--cutoff", default="2025-01-01", help="later cutoff for pre-cutoff counts (default 2025-01-01)")
    ap.add_argument("--cutoff-early", default="2022-11-30",
                    help="earlier cutoff for pre-ChatGPT counts (default 2022-11-30, the public release of ChatGPT)")
    ap.add_argument("--link-salt", default="", help="optional salt for hashed ticket keys; use the same one in measure-code")
    ap.add_argument("--ownership", choices=OWNERSHIP, help="who owns this source (default: own)")
    ap.add_argument("--flag", action="append", default=[],
                    help="self-reported restriction flag, repeatable: " + ", ".join(FLAG_KEYS) + " (NAME or NAME=no)")
    ap.add_argument("--version-history", choices=VERSION_HISTORY, help="self-reported version history for a document source")
    ap.add_argument("--category", action="append", default=[], help="status: KEY=STATUS for a studio category (repeatable)")
    ap.add_argument("--connector", action="append", default=[], help="status: \"TOOL=STATUS\" for a connector (repeatable)")
    ap.add_argument("--sample-files", type=int, default=200, help="simple mode: files parsed per source")
    ap.add_argument("--sample-mb", type=int, default=64, help="simple mode: MB read from each mailbox or dump")
    ap.add_argument("--force", action="store_true", help="discard checkpoints and recount")
    ap.add_argument("--no-dream", action="store_true",
                    help="report: skip dream mode (no 'Why this is special' pitch after the report)")
    a = ap.parse_args(argv)
    out = a.out.expanduser().resolve()
    cutoff = dt.datetime.strptime(a.cutoff, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    OPTS.cutoff_early = dt.datetime.strptime(a.cutoff_early, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    OPTS.link_salt = a.link_salt
    OPTS.source = a.source
    try:
        flags = parse_flags(a.flag)
    except ValueError as e:
        ap.error(str(e))
    if a.source == "status":
        return cmd_status(out, a.category, a.connector)
    OPTS.simple = a.mode == "simple"
    OPTS.sample_files = a.sample_files
    OPTS.sample_bytes = a.sample_mb * 2**20

    if a.source == "report":
        docs = [json.loads(p.read_text("utf-8")) for p in sorted((out / "sources").glob("*.json"))]
        if not docs:
            ap.error(f"no source files in {out / 'sources'}")
        for d in docs:  # source files from older versions get the new blocks; their numbers are not changed
            annotate(d, a.cutoff_early)
        st = load_status(out)
        cats = category_status(docs, st)
        conns = connectors_block(docs, st, tool_list())
        bundle = {"schema": SCHEMA, "kind": "data", "tool": TOOL, "tool_version": VERSION,
                  "measured_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "cutoff": a.cutoff, "cutoff_early": a.cutoff_early, "category_status": cats, "connectors": conns,
                  "sources": docs}
        rend = lambda dr=None: render(docs, a.cutoff, dr, cats, conns, a.cutoff_early)  # noqa: E731
        dm = dream_mod()
        bundle["dream"] = dm.pending()
        bundle["dream"] = dm.resolve(out, dm.ground_text(bundle, rend()), a.no_dream)
        bad = privacy_scan(bundle)
        if bad:
            log("privacy check FAILED, nothing written: " + ", ".join(bad[:10]))
            return 2
        atomic_write(out / "measure.json", json.dumps(bundle, indent=2))
        atomic_write(out / "report.md", rend(bundle["dream"]))
        log(f"wrote {out / 'measure.json'} and {out / 'report.md'} ({len(docs)} sources)")
        return 0

    if a.path is None or not a.path.exists():
        ap.error("path does not exist")
    label = a.label or a.source
    ck = Checkpoint(out, a.source, label, a.force, a.mode)
    t0 = time.time()
    result = SOURCES[a.source](a.path.expanduser().resolve(), ck, cutoff)
    doc = {"schema": SCHEMA, "kind": "data", "tool": TOOL, "tool_version": VERSION,
           "measured_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "source": a.source, "label": label, "tags": a.tag, "cutoff": a.cutoff, "cutoff_early": a.cutoff_early, **result}
    annotate(doc, a.cutoff_early, a.ownership, flags, a.version_history)
    bad = privacy_scan(doc)
    if bad:
        log("privacy check FAILED, nothing written: " + ", ".join(bad[:10]))
        return 2
    target = out / "sources" / f"{a.source}--{safe(label)}.json"
    atomic_write(target, json.dumps(doc, indent=2))
    log(f"{a.source} ({a.mode}): {result['primary_count']:,} {result['primary_unit']} in {time.time() - t0:.1f}s -> {target}")
    if OPTS.simple:
        log(f"full run: {result['recommendation']['full_run']}")
    log("run `measure_data.py report --out DIR` to build the combined report")
    return 0


if __name__ == "__main__":
    sys.exit(main())
