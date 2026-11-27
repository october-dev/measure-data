#!/usr/bin/env python3
"""add_dream.py: validate the "Why this is special" paragraph and insert it into the output.

Dream mode is the last step of a run. After the measurement and the report are complete, the agent
re-reads the report and what it inspected, then writes a short founder-style pitch: 4 to 6 casual
sentences about the taste, ambition, complexity and polish that counts miss. This helper checks the
draft and puts it in the slot the scripts leave for it: a `dream` block in measure.json and a
"Why this is special" section at the end of report.md.

    python3 add_dream.py draft.txt --out <out-dir> [--deny TERM ...]
    python3 add_dream.py draft.txt --out <out-dir> --check     # validate only, write nothing
    python3 add_dream.py --no-dream --out <out-dir>            # the user declined: record the skip

Checks (any failure writes nothing):
  - not empty; 4 to 6 sentences; at most 45 words per sentence and 160 words in all; one plain paragraph
  - no email addresses, URLs, @handles, file paths, file names, credential-like tokens or secrets
  - no person names: any --deny term (pass the names you saw while inspecting) and honorific-plus-name
    patterns
  - every number in the paragraph must already appear in the report or the measurement (no invented figures)
Superlatives are reported as warnings: keep them only for things the run actually inspected.

The paragraph is saved in <out-dir>/dream.json too, so a later re-run of the measurement keeps it
(it is validated again against the new numbers). Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL = "measure-data"
TARGET_JSON = "measure.json"
TARGET_REPORT = "report.md"
TITLE = "Why this is special"
BASIS = ("Founder-style pitch written by the AI agent after the audit, grounded only in what this run inspected. "
         "It is not a measurement and changes no count.")
MIN_SENTENCES, MAX_SENTENCES, MAX_SENTENCE_WORDS, MAX_WORDS, MAX_CHARS = 4, 6, 45, 160, 1200
SCRIPT_DIR = Path(__file__).resolve().parent

EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
URL_RX = re.compile(r"(?i)\b(?:https?://|ftp://|www\.)\S+|\b[a-z0-9-]+\.(?:com|io|net|org|dev|app|gg|co|ai)\b(?:/\S*)?")
HANDLE_RX = re.compile(r"(?:^|[\s(])@[A-Za-z0-9_][\w.-]*")
PATH_RX = re.compile(r"(?:^|[\s\"'(])(?:~|\.{1,2})?/[\w.-]+|[A-Za-z]:\\|\\[\w.-]+\\|\b[\w.-]+/[\w.-]+/|\b[\w-]+/[\w-]+\.[A-Za-z0-9]{1,5}\b")
FILE_EXTS = ("py|pyc|js|mjs|cjs|ts|tsx|jsx|cs|csproj|sln|cpp|cc|cxx|hpp|hh|h|c|m|mm|go|rs|java|kt|kts|swift|rb|php|lua|gd|"
             "shader|hlsl|glsl|json|jsonl|yaml|yml|toml|ini|cfg|conf|xml|plist|md|txt|csv|tsv|sql|db|sqlite|log|lock|env|pem|"
             "key|p12|pfx|crt|sh|bash|zsh|ps1|bat|exe|dll|so|dylib|apk|aab|ipa|zip|tar|gz|tgz|7z|rar|mbox|psd|psb|ai|aep|"
             "prproj|indd|fig|sketch|xd|blend|blend1|fbx|obj|glb|gltf|usd|usdz|stl|ma|mb|max|c4d|hip|ztl|spp|sbs|sbsar|kra|"
             "png|jpe?g|gif|tga|tiff?|exr|hdr|webp|svg|mp4|mov|avi|wav|mp3|ogg|ttf|otf|unity|prefab|mat|asset|meta|uasset|"
             "umap|uproject|tscn|tres|godot|dwg|dxf|skp|step|stp|iges|igs|sldprt|sldasm|3dm|ipt|pdf|docx?|xlsx?|pptx?|ipynb|"
             "tf|tfvars|dockerfile|gradle|pom")
FILE_RX = re.compile(r"(?i)(?<![\w.])[\w-]+(?:\.[\w-]+)*\.(?:" + FILE_EXTS + r")\b")
DOTFILE_RX = re.compile(r"(?<![\w.])\.(?:env|npmrc|pypirc|netrc|git|github|gitlab-ci|ssh|aws)\w*\b")
SECRET_RX = re.compile(r"AKIA[0-9A-Z]{16}|\bgh[pousr]_[A-Za-z0-9]{20,}|\bsk-[A-Za-z0-9_-]{16,}|\bxox[abprs]-[\w-]{10,}|"
                       r"-----BEGIN|\b[A-Fa-f0-9]{32,}\b|\b[A-Za-z0-9+/_=-]{40,}\b|(?i:\b(?:password|passwd|api[_ -]?key|"
                       r"secret[_ -]?key|access[_ -]?token|private[_ -]?key|bearer)\b\s*[:=])")
HONORIFIC_RX = re.compile(r"\b(?:Mr|Mrs|Ms|Mx|Dr|Prof|Sir|Dame)\.?\s+[A-Z][a-z]+")
TECH_NAMES = re.compile(r"(?i)\b(?:node|vue|next|nuxt|three|d3|express|react|angular|ember|chart|p5|babylon|phaser|pixi|socket)"
                        r"\.(?:js|io)\b|\basp\.net\b")
NUMBER_RX = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)([A-Za-z%]*)")
SUPERLATIVES = ("best", "greatest", "world-class", "world class", "unmatched", "unrivalled", "unrivaled", "unparalleled",
                "revolutionary", "unprecedented", "industry-leading", "industry leading", "game-changing", "groundbreaking",
                "ground-breaking", "flawless", "perfect", "the only", "number one", "#1", "most advanced", "first ever",
                "never before", "legendary", "iconic", "massive hit", "viral")


def log(msg: str) -> None:
    print(f"[add_dream] {msg}", file=sys.stderr, flush=True)


def canon(token: str):
    try:
        v = float(token.replace(",", ""))
    except ValueError:
        return None
    return ("%.6f" % v).rstrip("0").rstrip(".")


def known_numbers(ground: str) -> set:
    nums = set()
    for m in NUMBER_RX.finditer(ground):
        c = canon(m.group(1))
        if c is None:
            continue
        nums.add(c)
        nums.add(canon(c.split(".")[0]))
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if 0 < v <= 1 and "." in m.group(1):  # shares: 0.825 may be quoted as 82.5% or 83%
            nums.add(canon(str(round(v * 100, 1))))
            nums.add(canon(str(round(v * 100))))
    return nums


def sentences_of(text: str) -> list:
    flat = " ".join(text.split())
    return [s for s in re.split(r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]?[A-Z0-9])", flat) if s.strip()]


def validate(text, ground: str, deny=()) -> tuple:
    """Returns (errors, warnings, stats). `ground` is the report and measurement the paragraph may draw on."""
    errors, warnings = [], []
    if not isinstance(text, str) or not text.strip():
        return ["the paragraph is empty"], [], {}
    text = text.strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if any(re.match(r"\s*(#|[-*+>]\s|\d+[.)]\s|\|)", ln) for ln in lines):
        errors.append("write one plain paragraph: no headings, bullets, tables or quotes")
    if re.search(r"\n\s*\n", text):
        errors.append("write one paragraph, not several")
    if "`" in text or "**" in text or "](" in text:
        errors.append("no markdown formatting, code or links")
    sents = sentences_of(text)
    words = len(text.split())
    if not re.search(r"[.!?][\"')\]]*$", text):
        errors.append("end the last sentence with a full stop")
    if not MIN_SENTENCES <= len(sents) <= MAX_SENTENCES:
        errors.append(f"{len(sents)} sentences: write {MIN_SENTENCES} to {MAX_SENTENCES}")
    long_ = [i + 1 for i, s in enumerate(sents) if len(s.split()) > MAX_SENTENCE_WORDS]
    if long_:
        errors.append(f"sentence {', '.join(map(str, long_))} is over {MAX_SENTENCE_WORDS} words: keep it casual and simple")
    if words > MAX_WORDS or len(text) > MAX_CHARS:
        errors.append(f"{words} words: keep it under {MAX_WORDS}")
    scan = TECH_NAMES.sub("tech", text)
    for rx, what in ((EMAIL_RX, "an email address"), (URL_RX, "a URL or web address"), (HANDLE_RX, "an @handle"),
                     (PATH_RX, "a file path"), (FILE_RX, "a file name"), (DOTFILE_RX, "a credential or config file name"),
                     (SECRET_RX, "something that looks like a secret or token"), (HONORIFIC_RX, "a person's name")):
        m = rx.search(scan)
        if m:
            errors.append(f"contains {what} ({m.group(0).strip()[:3]}...): describe it in general terms")
    low = text.lower()
    for d in sorted({str(d).lower().strip() for d in deny if d and len(str(d).strip()) >= 4}):
        if re.search(r"(?<![a-z0-9])" + re.escape(d) + r"(?![a-z0-9])", low):
            errors.append("contains a person's name or email from the history or the deny list: never name people")
            break
    nums = known_numbers(ground)
    invented = []
    for m in NUMBER_RX.finditer(text):
        base, suffix = m.group(1), m.group(2)
        if suffix.lower() == "d" and len(base) == 1:  # 2D / 3D
            continue
        c = canon(base.rstrip(","))
        if c is not None and c not in nums:
            invented.append(m.group(0))
    if invented:
        errors.append("numbers not found in the report or the measurement: " + ", ".join(sorted(set(invented)))
                      + " (quote figures exactly as the report shows them, or leave them out)")
    for w in SUPERLATIVES:
        if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", low):
            warnings.append(f"superlative '{w}': keep it only if this run inspected what it claims")
    return errors, warnings, {"sentences": len(sents), "words": words}


def pending() -> dict:
    return {"title": TITLE, "status": "pending", "text": None, "sentences": None, "words": None, "skip_reason": None,
            "basis": "Not written yet: the agent adds it after the audit with add_dream.py; --no-dream skips it."}


def skipped(reason: str = "declined_by_user") -> dict:
    return {"title": TITLE, "status": "skipped", "text": None, "sentences": None, "words": None, "skip_reason": reason,
            "basis": "Skipped (--no-dream)."}


def written(text: str, stats: dict) -> dict:
    return {"title": TITLE, "status": "written", "text": " ".join(text.split()), "sentences": stats["sentences"],
            "words": stats["words"], "skip_reason": None, "basis": BASIS}


def needs_rewrite() -> dict:
    return {"title": TITLE, "status": "needs_rewrite", "text": None, "sentences": None, "words": None,
            "skip_reason": "failed_validation",
            "basis": "The saved paragraph no longer passes the checks against these numbers; write it again with add_dream.py."}


def section(dream) -> list:
    """Markdown lines for the end of the report (empty unless a paragraph was written)."""
    if not dream or dream.get("status") != "written" or not dream.get("text"):
        return []
    return [f"## {TITLE}", "",
            "_Founder-style pitch written by the AI agent after the audit, from what it inspected in this run. "
            "It is not a measurement and changes no count above._", "", dream["text"], ""]


def strip_section(report: str) -> str:
    i = report.find(f"\n## {TITLE}\n")
    return (report[:i].rstrip("\n") + "\n") if i >= 0 else report


def ground_text(doc: dict, report: str) -> str:
    d = {k: v for k, v in doc.items() if k != "dream"} if isinstance(doc, dict) else doc
    return strip_section(report) + "\n" + json.dumps(d)


def resolve(out: Path, ground: str, no_dream: bool = False, deny=()) -> dict:
    """The dream block for a (re-)run of the measurement: skipped, pending, or the saved paragraph re-validated."""
    if no_dream:
        return skipped()
    p = Path(out) / "dream.json"
    if not p.exists():
        return pending()
    try:
        saved = json.loads(p.read_text("utf-8"))
    except (OSError, ValueError):
        return pending()
    if saved.get("status") == "skipped":
        return skipped(saved.get("skip_reason") or "declined_by_user")
    errors, _, stats = validate(saved.get("text"), ground, deny)
    if errors:
        log("the saved 'Why this is special' paragraph no longer passes: " + "; ".join(errors))
        return needs_rewrite()
    return written(saved["text"], stats)


# --------------------------------------------------------------------------
# per-skill refresh: put the block into the output and re-render the report
# --------------------------------------------------------------------------

def _load_sibling(name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def deny_terms(a) -> set:
    deny = set(a.deny or [])
    if SKILL == "measure-code" and getattr(a, "repo", None):
        mc = _load_sibling("measure_code")
        deny |= mc.author_denylist(Path(a.repo).expanduser().resolve())
    return deny


def refresh(out: Path, doc: dict, report: str, a) -> str | None:
    """Writes the target JSON and report. Returns an error message instead when the output check refuses."""
    if SKILL == "measure-code":
        mc = _load_sibling("measure_code")
        doc["provenance"]["payload_digest"] = mc.payload_digest(doc)
        problems = mc.boundary(doc, deny_terms(a))
        if problems:
            return "; ".join(problems[:5])
        row = mc.summary_row(doc)
        mc.atomic_write(out / TARGET_JSON, json.dumps(doc, indent=2))
        mc.atomic_write(out / "summary_row.json", json.dumps(row, indent=2))
        import csv
        with (out / "summary_row.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            w.writeheader()
            w.writerow(row)
        mc.atomic_write(out / TARGET_REPORT, mc.render_report(doc))
        return None
    if SKILL == "measure-art":
        ma = _load_sibling("measure_art")
        if ma.privacy_problems(doc):
            return "the privacy check refused the document"
        ma.atomic_write(out / TARGET_JSON, json.dumps(doc, indent=2))
        ma.atomic_write(out / TARGET_REPORT, ma.render(doc))
        return None
    if SKILL == "measure-data":
        md = _load_sibling("measure_data")
        if md.privacy_scan(doc):
            return "the privacy check refused the document"
        md.atomic_write(out / TARGET_JSON, json.dumps(doc, indent=2))
        md.atomic_write(out / TARGET_REPORT, md.render(doc["sources"], doc.get("cutoff", "2025-01-01"), doc.get("dream")))
        return None
    # master-valuate: the overview cannot be rebuilt from valuation.json alone, so the section is replaced in place
    (out / TARGET_JSON).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    body = strip_section(report).rstrip("\n")
    sec = section(doc.get("dream"))
    (out / TARGET_REPORT).write_text(body + "\n" + ("\n" + "\n".join(sec) if sec else ""), encoding="utf-8")
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=f"Validate and insert the '{TITLE}' paragraph into {SKILL} output.")
    ap.add_argument("draft", nargs="?", type=Path, help="text file holding the paragraph ('-' reads stdin); keep it outside the repo")
    ap.add_argument("--out", type=Path, required=True, help=f"the output folder holding {TARGET_JSON} and {TARGET_REPORT}")
    if SKILL == "measure-code":
        ap.add_argument("--repo", type=Path, help="the measured repository: its author names and emails are refused")
    ap.add_argument("--deny", action="append", default=[], help="a name or term that must not appear (repeatable)")
    ap.add_argument("--check", action="store_true", help="validate only; write nothing")
    ap.add_argument("--no-dream", action="store_true", help="the user declined dream mode: record the skip and remove the section")
    a = ap.parse_args(argv)
    out = a.out.expanduser().resolve()
    tj, tr = out / TARGET_JSON, out / TARGET_REPORT
    if not tj.exists() or not tr.exists():
        ap.error(f"{TARGET_JSON} and {TARGET_REPORT} not found in --out: finish the measurement and the report first")
    doc = json.loads(tj.read_text("utf-8"))
    report = tr.read_text("utf-8")
    if a.no_dream:
        doc["dream"] = skipped()
        problem = refresh(out, doc, report, a)
        if problem:
            log(f"refused: {problem}")
            return 2
        (out / "dream.json").write_text(json.dumps({"status": "skipped", "skip_reason": "declined_by_user"}, indent=2), encoding="utf-8")
        log("dream mode skipped (--no-dream); the report has no 'Why this is special' section")
        return 0
    if a.draft is None:
        ap.error("give the draft file, or --no-dream")
    if (doc.get("dream") or {}).get("status") == "skipped" and not a.check:
        log("this output was run with --no-dream; re-run the measurement without it to add a paragraph")
        return 1
    text = sys.stdin.read() if str(a.draft) == "-" else a.draft.expanduser().read_text("utf-8")
    errors, warnings, stats = validate(text, ground_text(doc, report), deny_terms(a))
    for w in warnings:
        log("warning: " + w)
    if errors:
        log("refused, nothing written:")
        for e in errors:
            log("  - " + e)
        return 1
    if a.check:
        log(f"ok: {stats['sentences']} sentences, {stats['words']} words (check only, nothing written)")
        return 0
    doc["dream"] = written(text, stats)
    problem = refresh(out, doc, report, a)
    if problem:
        log(f"refused by the output check, nothing written: {problem}")
        return 2
    (out / "dream.json").write_text(json.dumps({"status": "written", "text": doc["dream"]["text"]}, indent=2), encoding="utf-8")
    log(f"inserted '{TITLE}' ({stats['sentences']} sentences, {stats['words']} words) into {TARGET_JSON} and {TARGET_REPORT}")
    print(f"REVIEW model-written: dream.text = {doc['dream']['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
