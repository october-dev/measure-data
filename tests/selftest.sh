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
rows = [l for l in md.splitlines() if l.startswith("| ") and not l.startswith("| tool |")]
assert len(rows) == len(tools), (len(rows), len(tools))
for t in tools:
    assert "| %s |" % t["tool"] in md and "`%s`" % t["source"] in md, t["tool"]
print("selftest: tool list OK (%d tools, %d categories)" % (len(tools), len(cats)))
EOF
echo "selftest: passed"
