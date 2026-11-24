#!/usr/bin/env bash
# Measures synthetic exports for every source, in full and simple mode, and checks the output.
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
print("selftest: passed")
EOF
