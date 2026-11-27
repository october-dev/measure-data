#!/usr/bin/env bash
# Measures synthetic exports for every source, in full and simple mode, and checks the output and dream mode.
set -euo pipefail
PY="${PY:-python3}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FX="$WORK/fixtures"
"$PY" "$HERE/tests/make_fixtures.py" "$FX"
M="$HERE/scripts/measure_data.py"
for MODE in full simple; do
  OUT="$WORK/$MODE"
  "$PY" "$M" slack    "$FX/slack.zip"    --out "$OUT" --mode $MODE
  "$PY" "$M" discord  "$FX/discord"      --out "$OUT" --mode $MODE
  "$PY" "$M" notion   "$FX/notion"       --out "$OUT" --mode $MODE
  "$PY" "$M" jira     "$FX/jira.csv"     --out "$OUT" --mode $MODE
  "$PY" "$M" clickup  "$FX/clickup.json" --out "$OUT" --mode $MODE
  "$PY" "$M" mbox     "$FX/mail"         --out "$OUT" --mode $MODE
  "$PY" "$M" sql      "$FX/shop.sql.gz"  --out "$OUT" --mode $MODE --label shop
  "$PY" "$M" sql      "$FX/pg.sql"       --out "$OUT" --mode $MODE --label pg
  "$PY" "$M" bigquery "$FX/bq.json"      --out "$OUT" --mode $MODE
  "$PY" "$M" files    "$FX/drive"        --out "$OUT" --mode $MODE
  "$PY" "$M" report --out "$OUT"
done
"$PY" "$M" slack "$FX/slack.zip" --out "$WORK/full"   # resume: reuses the checkpoint
# Simple mode on a bigger synthetic Slack export, so sampling and scaling actually kick in.
"$PY" - "$FX/big_slack" <<'EOF'
import json, sys, pathlib
root = pathlib.Path(sys.argv[1]); root.mkdir()
(root / "users.json").write_text(json.dumps([{"id": f"U{i}"} for i in range(5)]))
(root / "channels.json").write_text(json.dumps([{"id": "C1", "name": "c1"}]))
(root / "c1").mkdir()
for d in range(300):
    msgs = [{"ts": f"{1600000000 + d * 86400 + i}.000100", "user": f"U{i % 5}", "text": "message text"} for i in range(10)]
    (root / "c1" / f"2019-{1 + (d // 28) % 12:02d}-{1 + d % 28:02d}.json").write_text(json.dumps(msgs))
EOF
"$PY" "$M" slack "$FX/big_slack" --out "$WORK/bigsimple" --mode simple --sample-files 50
"$PY" - "$WORK" <<'EOF'
import json, sys, pathlib
w = pathlib.Path(sys.argv[1])
s = {p.stem: json.loads(p.read_text()) for p in (w / "full" / "sources").glob("*.json")}
sl = s["slack--slack"]
assert sl["primary_count"] == 4 and sl["human_count"] == 3, (sl["primary_count"], sl["human_count"])
assert sl["people"]["distinct"] == 2 and sl["people"]["bots"] == 1 and sl["people"]["peak_active_in_a_month"] == 2
assert sl["counts"]["items_with_email_pattern"] == 1 and sl["span"]["last_human"] == "2025-02-01"
assert s["discord--discord"]["primary_count"] == 2 and s["discord--discord"]["counts"]["servers"] == 1
assert s["notion--notion"]["counts"]["pages_and_rows"] == 3
j = s["jira--jira"]
assert j["primary_count"] == 2 and j["counts"]["type_bug"] == 1 and j["description_or_comment_share"] == 0.5, j
assert j["text"]["characters"] > 0
assert s["clickup--clickup"]["counts"]["subtasks"] == 1
mb = s["mbox--mbox"]
assert mb["primary_count"] == 3 and mb["counts"]["unique_messages"] == 2 and mb["counts"]["attachments"] == 1, mb["counts"]
assert s["sql--shop"]["counts"]["rows"] == 2
assert s["sql--pg"]["counts"]["rows"] == 2 and s["sql--pg"]["pre_cutoff"] == 2
assert s["bigquery--bigquery"]["sharded_tables"][0]["daily_shards"] == 10 and s["bigquery--bigquery"]["counts"]["projects"] == 0
fl = s["files--files"]
assert fl["counts"]["duplicate_files"] == 1 and fl["working_documents"]["files"] == 3, fl["working_documents"]
assert all(d["mode"] == "full" for d in s.values())
simple = {p.stem: json.loads(p.read_text()) for p in (w / "simple" / "sources").glob("*.json")}
assert all(d["mode"] == "simple" and d["recommendation"]["full_run"] in ("recommended", "optional", "not worth it") for d in simple.values())
assert simple["files--files"]["counts"].get("duplicate_files") is None
big = json.loads((w / "bigsimple" / "sources" / "slack--slack.json").read_text())
assert big["estimate"] and 2400 <= big["primary_count"] <= 3600, big["primary_count"]   # true count 3,000
assert big["counts"]["conversations"] == 1
text = "".join((w / m / f).read_text() for m in ("full", "simple") for f in ("measure.json", "report.md"))
for leak in ("example.com", "example.org", "general", "Workspace Home", "budget", "zq_", "analytics_1", "hello team", "crashes"):
    assert leak not in text, leak
print("selftest: counts OK")
EOF
# Dream mode: validate and insert "Why this is special", keep it on re-runs, refuse bad drafts, honour --no-dream.
D="$HERE/scripts/add_dream.py"
cat > "$WORK/dream.txt" <<'EOF'
This small export already covers the whole studio: chat, tickets, a wiki, mail, databases and shared files.
Slack alone holds 4 messages from a real team, with the bot noise counted apart.
The tickets carry real descriptions, and the mail comes with its attachments.
It is a compact but complete picture of how the team worked, counted without reading a word of it into the report.
EOF
"$PY" "$D" "$WORK/dream.txt" --out "$WORK/full" --check 2>/dev/null
"$PY" "$D" "$WORK/dream.txt" --out "$WORK/full" --deny "Zq Founder" >/dev/null 2>&1
"$PY" "$M" report --out "$WORK/full" 2>/dev/null   # a re-run of the report keeps it
refuse() {
  printf '%s\n' "$2" > "$WORK/bad.txt"
  if "$PY" "$D" "$WORK/bad.txt" --out "$WORK/full" --deny "Zq Founder" --check 2>/dev/null; then echo "dream accepted: $1"; exit 1; fi
}
refuse empty ""
refuse too-short "Lots of data. Real team."
refuse email "Slack holds 4 messages. Mail goes to founder@example.com mostly. It is complete. It is real."
refuse name "Slack holds 4 messages. Zq Founder wrote most of them. It is complete. It is real."
refuse path "Slack holds 4 messages. The export sits in /home/someone/exports today. It is complete. It is real."
refuse file-name "Slack holds 4 messages. The shop lives in shop.sql.gz now. It is complete. It is real."
refuse invented-number "Slack holds 4 messages. The game had 3,000,000 daily players. It is complete. It is real."
"$PY" "$M" report --out "$WORK/simple" --no-dream 2>/dev/null
cp -R "$WORK/full" "$WORK/declined" && "$PY" "$D" --no-dream --out "$WORK/declined" >/dev/null 2>&1
"$PY" "$D" "$HERE/examples/dream.txt" --out "$HERE/examples" --check 2>/dev/null
"$PY" - "$WORK" <<'EOF'
import json, sys, pathlib
w = pathlib.Path(sys.argv[1])
d = json.loads((w / "full/measure.json").read_text()); rep = (w / "full/report.md").read_text()
dr = d["dream"]
assert dr["status"] == "written" and dr["title"] == "Why this is special" and dr["sentences"] == 4, dr
assert rep.rstrip().endswith("into the report.") and rep.index("## Why this is special") > rep.index("## Caveats"), rep[-400:]
assert "not a measurement" in rep.split("## Why this is special")[1]
s = json.loads((w / "simple/measure.json").read_text())
assert s["dream"]["status"] == "skipped" and "Why this is special" not in (w / "simple/report.md").read_text()
dc = json.loads((w / "declined/measure.json").read_text())
assert dc["dream"]["status"] == "skipped" and "Why this is special" not in (w / "declined/report.md").read_text()
assert json.loads((w / "bigsimple/sources/slack--slack.json").read_text()).get("dream") is None, "the pitch belongs to the report, not a source"
print("selftest: dream mode OK")
EOF
# Studio assessment: labels, both cutoffs, restriction flags, category status, connectors, traceable work,
# version history and the studio file detectors.
SA="$WORK/studio"
"$PY" "$M" files    "$FX/studio" --out "$SA" --label studio-nas --version-history retained_not_exported 2>/dev/null
"$PY" "$M" jira     "$FX/jira.csv" --out "$SA" --flag staff_personal_data 2>/dev/null
"$PY" "$M" clickup  "$FX/cu.csv"   --out "$SA" --tag connector:PlayFab --ownership client_owned 2>/dev/null
"$PY" "$M" tickets  "$FX/gh.csv"   --out "$SA" --label gh-issues 2>/dev/null
"$PY" "$M" sql      "$FX/shop.sql.gz" --out "$SA" --label shop 2>/dev/null
"$PY" "$M" notion   "$FX/notion" --out "$SA" 2>/dev/null
"$PY" "$M" clickup  "$FX/cu.csv"   --out "$WORK/cusimple" --mode simple 2>/dev/null
"$PY" "$M" jira     "$FX/jira.csv" --out "$WORK/salted" --link-salt zqsalt 2>/dev/null
"$PY" "$M" status --out "$SA" --category audio=confirmed_not_used --category telemetry=self_reported \
  --category work_tracking=unknown --connector "Mixpanel=self_reported" --connector "steam (steamworks)=confirmed_not_used" 2>/dev/null
if "$PY" "$M" status --out "$SA" --category made_up=inspected 2>/dev/null; then echo "bad category accepted"; exit 1; fi
if "$PY" "$M" status --out "$SA" --connector "NotATool=inspected" 2>/dev/null; then echo "bad connector accepted"; exit 1; fi
if "$PY" "$M" jira "$FX/jira.csv" --out "$WORK/badflag" --flag nonsense 2>/dev/null; then echo "bad flag accepted"; exit 1; fi
"$PY" "$M" report --out "$SA" --no-dream 2>/dev/null
# An older source file (no labels, cutoffs or restrictions) still loads; the blocks are added, numbers unchanged.
mkdir -p "$WORK/old/sources" && cp "$HERE/examples/sources/jira--starfall-jira.json" "$WORK/old/sources/"
"$PY" - "$WORK/old/sources/jira--starfall-jira.json" <<'PYOLD'
import json, sys
d = json.load(open(sys.argv[1]))
for k in ("labels", "cutoffs", "restrictions", "version_history", "cutoff_early", "pre_chatgpt", "pre_chatgpt_share", "traceable"):
    d.pop(k, None)
json.dump(d, open(sys.argv[1], "w"))
PYOLD
"$PY" "$M" report --out "$WORK/old" --no-dream 2>/dev/null
"$PY" - "$WORK" "$HERE" <<'PYCHK'
import hashlib, json, sys, pathlib, importlib.util
w, here = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("measure_data", here / "scripts" / "measure_data.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
b = json.loads((w / "studio/measure.json").read_text()); rep = (w / "studio/report.md").read_text()
S = {d["label"]: d for d in b["sources"]}
assert b["cutoff_early"] == "2022-11-30" and b["cutoff"] == "2025-01-01"
# category status: all 18 keys in order, never dropped; precedence keeps inspected over a weaker answer
assert list(b["category_status"]) == list(m.CATEGORY_KEYS) and len(m.CATEGORY_KEYS) == 18
cs = {k: v["status"] for k, v in b["category_status"].items()}
assert cs["work_tracking"] == "inspected" and cs["design_knowledge"] == "inspected" and cs["liveops_backend"] == "inspected", cs
assert cs["servers_storage"] == "inspected" and cs["builds_ci"] == "inspected" and cs["crash_reports"] == "inspected", cs
assert cs["profiling"] == cs["qa_playtest"] == cs["narrative_localisation"] == cs["engine_content"] == "inspected", cs
assert cs["source_control"] == "inspected" and cs["audio"] == "inspected", ("files found beat the owner's 'not used'", cs)
assert cs["telemetry"] == "self_reported" and cs["communication"] == "unknown" and cs["business_systems"] == "unknown", cs
assert all(v["label"] in m.LABELS for v in b["category_status"].values())
# connectors: every prompt has a status; tags and owner answers land
cn = b["connectors"]
tools = json.loads((here / "docs/tools.json").read_text())
assert set(cn) == {n for g in tools["connector_prompts"].values() for n in g}
assert cn["PlayFab"]["status"] == "inspected" and cn["PlayFab"]["group"] == "backends"
assert cn["Mixpanel"]["status"] == "self_reported" and cn["Steam (Steamworks)"]["status"] == "confirmed_not_used"
assert cn["Supabase"]["status"] == "unknown" and cn["Supabase"]["label"] == "unknown"
# traceable work: ticket types, resolved counts and hashed keys that measure-code can match
tr = S["jira"]["traceable"]
assert tr["by_type"]["bug"] == {"total": 1, "resolved": 1} and tr["by_type"]["story"] == {"total": 1, "resolved": 0}, tr
lh = lambda k, salt="": hashlib.sha256(f"{salt}|ticket|{k}".encode()).hexdigest()[:16]
assert tr["resolved_key_hashes"]["bug"] == [lh("AB-1")] and m.link_hash("ticket", "AB-1") == lh("AB-1")
assert tr["key_salt_used"] is False
sl = json.loads((w / "salted/sources/jira--jira.json").read_text())["traceable"]
assert sl["key_salt_used"] is True and sl["resolved_key_hashes"]["bug"] == [lh("AB-1", "zqsalt")]
cu = S["clickup"]["traceable"]
assert cu["by_type"]["bug"] == {"total": 2, "resolved": 2} and cu["by_type"]["story"]["resolved"] == 0, cu
assert sorted(cu["resolved_key_hashes"]["bug"]) == sorted([lh("CU-ABC1"), lh("CU-ABC3")]), cu
gh = S["gh-issues"]["traceable"]
assert gh["resolved_key_hashes"]["bug"] == [lh("#17")] and gh["by_type"]["other"]["total"] == 1, gh
assert json.loads((w / "cusimple/sources/clickup--clickup.json").read_text())["traceable"]["label"] == "estimated"
assert "traceable" not in S["shop"]
# labels and both cutoffs
j = S["jira"]
assert j["cutoffs"]["pre_2025"] == {"date": "2025-01-01", "count": 1, "share": 0.5, "label": "verified"}, j["cutoffs"]
assert j["cutoffs"]["pre_chatgpt"] == {"date": "2022-11-30", "count": 1, "share": 0.5, "label": "verified"}, j["cutoffs"]
assert j["labels"]["primary_count"]["label"] == "verified" and j["labels"]["text.token_estimate"]["method"]
assert S["shop"]["labels"]["pre_chatgpt"]["label"] == "estimated" and S["shop"]["cutoffs"]["pre_chatgpt"]["count"] == 1
assert S["studio-nas"]["labels"]["span"]["label"] == "estimated"
for d in b["sources"]:
    for k, v in d["labels"].items():
        assert v["label"] in m.LABELS and (v["label"] != "estimated" or v.get("method")), (d["label"], k, v)
# restrictions: recorded, not ruled on; default ownership own; flags measured or self-reported
r = S["jira"]["restrictions"]
assert r["ownership"] == "own" and r["flags"]["staff_personal_data"] == {"value": True, "label": "self_reported"}
assert r["flags"]["client_owned"] == {"value": None, "label": "unknown"} and set(r["flags"]) == set(m.FLAG_KEYS)
assert S["clickup"]["restrictions"]["ownership"] == "client_owned" and S["clickup"]["restrictions"]["flags"]["client_owned"]["value"] is True
sf = S["studio-nas"]["restrictions"]["flags"]
assert sf["secrets"]["value"] is True and sf["secrets"]["count"] == 1 and sf["secrets"]["label"] == "estimated", sf
assert sf["platform_nda"]["value"] is True and sf["third_party_middleware"]["count"] == 3, sf
assert S["shop"]["restrictions"]["flags"]["player_personal_data"]["value"] is True
# version history
assert S["studio-nas"]["version_history"] == {"status": "retained_not_exported", "label": "self_reported"}
assert S["notion"]["version_history"]["status"] == "unknown" and S["jira"]["version_history"]["status"] == "not_applicable"
# studio detectors
st = S["studio-nas"]["studio_files"]
assert st["build_ci"] == {"build_logs": 2, "ci_configs": 1, "jenkins_homes": 1, "horde_ugs": 0}, st["build_ci"]
assert st["crash_dumps"] == {"dumps": 1, "crash_reports": 1, "crash_exports": 1}, st["crash_dumps"]
assert st["profiling"] == {"captures": 2, "by_format": {"renderdoc": 1, "unreal_insights": 1}}, st["profiling"]
assert st["qa_cert_docs"] == 2 and st["certification_docs"] == 1, st
assert st["audio_middleware"] == {"wwise_projects": 1, "fmod_projects": 0, "sound_banks": 1}, st["audio_middleware"]
assert st["localisation"] == {"files": 3, "by_format": {"gettext": 1, "ink": 1}, "string_tables_by_header": 1}, st["localisation"]
assert st["engine_content"][".uasset"] == 1 and st["engine_content"][".umap"] == 1 and st["vcs"]["svn_working_copies"] == 1, st
assert "## Category status" in rep and "## Connectors check" in rep and "pre-ChatGPT" in rep and "| bug | 2 | 2 | 2 |" in rep
o = json.loads((w / "old/measure.json").read_text())["sources"][0]
assert o["primary_count"] == 14820 and o["cutoffs"]["pre_chatgpt"]["label"] == "unknown" and o["cutoffs"]["pre_chatgpt"]["count"] is None
assert o["restrictions"]["ownership"] == "own" and o["labels"]["primary_count"]["label"] == "verified"
text = (w / "studio/measure.json").read_text() + rep + (w / "salted/sources/jira--jira.json").read_text()
for leak in ("zq", "Zq", "AB-1", "abc1", "CU-ABC", "Bonjour", "Test Plan", "TRC checklist", "wc.db", "ZQ_KEY"):
    assert leak not in text, leak
print("selftest: studio assessment (labels, cutoffs, restrictions, categories, connectors, traceable, studio files) OK")
PYCHK
# Buyer tool list: docs/tools.json parses, has no duplicates, and maps every tool to a real source.
"$PY" - "$HERE" <<'EOF'
import json, sys, pathlib, importlib.util
here = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("measure_data", here / "scripts" / "measure_data.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
valid = set(m.SOURCES) | {"export then files"}
doc = json.loads((here / "docs" / "tools.json").read_text(encoding="utf-8"))
tools, cats = doc["tools"], doc["categories"]
assert len(tools) >= 200 and set(doc["sources"]) == valid, (len(tools), doc["sources"])
names = [t["tool"].strip().lower() for t in tools]
dupes = sorted({n for n in names if names.count(n) > 1})
assert not dupes, dupes
assert len(set(cats)) == len(cats)
for t in tools:
    assert t["tool"] and t["tool"] == t["tool"].strip() and not t["tool"].lower().startswith(("http://", "https://")), t
    assert t["source"] in valid, t
    assert t["category"] in t["categories"] and set(t["categories"]) <= set(cats), t
    assert t["export"].strip() and "\n" not in t["export"], t
md = (here / "docs" / "TOOLS.md").read_text(encoding="utf-8")
rows = [l for l in md.split("\n## Categories\n", 1)[1].splitlines() if l.startswith("| ") and not l.startswith("| tool |")]
assert len(rows) == len(tools), (len(rows), len(tools))
for t in tools:
    assert "| %s |" % t["tool"] in md and "`%s`" % t["source"] in md, t["tool"]
print("selftest: tool list OK (%d tools, %d categories)" % (len(tools), len(cats)))
# local_signals: every tool has the field; only known kinds; patterns are valid and never absolute paths.
import fnmatch, re
kinds = doc["local_signal_kinds"]
assert kinds == ["files", "folders", "folder_contains", "zip_contains", "csv_header", "file_head", "app_data"], kinds
def pat_ok(p, slash_ok):
    assert isinstance(p, str) and p and p.strip() == p, p
    body = p[3:] if p.startswith("re:") else p
    assert not body.startswith(("/", "~")) and not re.match(r"[A-Za-z]:", body), p
    assert p.startswith("re:") or "\\" not in p, p
    if p.startswith("re:"):
        re.compile(p[3:])
    else:
        fnmatch.translate(p)
        assert slash_ok or "/" not in p, p
with_signals = 0
for t in tools:
    sig = t["local_signals"]
    assert isinstance(sig, dict) and set(sig) <= set(kinds), t["tool"]
    with_signals += bool(sig)
    for k, v in sig.items():
        assert isinstance(v, list) and v, (t["tool"], k)
        for item in v:
            if k in ("files", "folders"):
                pat_ok(item, False)
            elif k == "app_data":
                pat_ok(item, True)
                assert not item.startswith("re:") and ".." not in item.split("/"), item
            elif k in ("folder_contains", "zip_contains", "csv_header"):
                assert isinstance(item, list) and item, (t["tool"], k)
                for p in item:
                    pat_ok(p, k in ("zip_contains", "csv_header"))
            else:
                assert set(item) == {"files", "contains"} and item["contains"].strip(), (t["tool"], item)
                pat_ok(item["files"], False)
# spot checks: a Slack export zip, an mbox and a Unity project are recognisable
by = {t["tool"]: t["local_signals"] for t in tools}
assert ["channels.json", "users.json"] in by["Slack"]["zip_contains"]
assert any(fnmatch.fnmatch("founder.mbox", p) for p in by["Email archives (generic mbox / eml)"]["files"])
assert ["Assets", "ProjectSettings"] in by["Unity"]["folder_contains"]
assert by["QuickBooks Desktop"]["files"] and by["Microsoft Teams"]["app_data"] and by["HubSpot"]["csv_header"]
assert with_signals >= 40, with_signals
assert "Local signals" in md and "`local_signals`" in md
print("selftest: local_signals OK (%d of %d tools have local signals)" % (with_signals, len(tools)))
# domains and mail_domains: bare lowercase host names, each owned by one tool only.
host_re = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
generic = {"google.com", "microsoft.com", "facebook.com", "amazon.com", "apple.com", "gmail.com", "outlook.com",
           "live.com", "yahoo.com", "icloud.com", "office.com", "youtube.com", "sendgrid.net", "mcsv.net",
           "amazonses.com", "mailgun.org", "mandrillapp.com"}
for key in ("domains", "mail_domains"):
    owner = {}
    for t in tools:
        v = t[key]
        assert isinstance(v, list) and len(v) == len(set(v)), (t["tool"], key)
        for h in v:
            assert host_re.match(h) and h not in generic, (t["tool"], key, h)
            assert h not in owner, (key, h, owner.get(h), t["tool"])
            owner[h] = t["tool"]
    for h in owner:   # no host may sit under another tool's host, or visits would be ambiguous
        parts = h.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            assert parent not in owner or owner[parent] == owner[h], (key, h, parent)
nd = sum(1 for t in tools if t["domains"]); nm = sum(1 for t in tools if t["mail_domains"])
assert by["Slack"] and {"HubSpot", "Stripe", "Mixpanel"} <= {t["tool"] for t in tools if t["domains"]}
assert "slack.com" in [t for t in tools if t["tool"] == "Slack"][0]["mail_domains"]
assert nd >= 150 and nm >= 90, (nd, nm)
assert "`domains`" in md and "`mail_domains`" in md
cp_ = doc["connector_prompts"]; scm = doc["studio_category_map"]
assert set(cp_) == {"telemetry", "backends", "stores", "ads"} and all(set(v) <= set(by) for v in cp_.values()), cp_
for need in ("Mixpanel", "Amplitude", "Google Analytics", "GameAnalytics", "Unity Analytics", "PostHog", "Supabase", "Firebase",
             "PlayFab", "Nakama", "Cloudflare R2", "Cloudflare D1", "Cloudflare Workers", "Google Play Console",
             "App Store Connect", "Steam (Steamworks)", "AdMob", "Google Ads", "Meta Ads", "AppLovin", "Unity Ads"):
    assert any(need in v for v in cp_.values()), need
assert set(scm["by_category"]) == set(cats) and set(scm["by_tool"]) <= set(by), "studio_category_map"
assert set(scm["by_category"].values()) | set(scm["by_tool"].values()) <= set(m.CATEGORY_KEYS)
print("connectors and studio category map OK")
print("selftest: domains OK (%d tools with web domains, %d with mail sender domains)" % (nd, nm))
EOF
echo "selftest: passed"
