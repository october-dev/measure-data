#!/usr/bin/env python3
"""Write tiny synthetic exports for every measure-data source into a folder.

All names, ids, text and addresses are made up for testing.
"""
import gzip
import json
import sys
import zipfile
from pathlib import Path

root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)

# Slack export (zip)
with zipfile.ZipFile(root / "slack.zip", "w") as z:
    z.writestr("users.json", json.dumps([{"id": "U1"}, {"id": "U2"}, {"id": "B1", "is_bot": True}]))
    z.writestr("channels.json", json.dumps([{"id": "C1", "name": "general"}]))
    z.writestr("general/2024-03-01.json", json.dumps([
        {"ts": "1709280000.000100", "user": "U1", "text": "hello team", "reply_count": 1},
        {"ts": "1709280100.000100", "user": "U2", "text": "reach me at someone@example.com", "thread_ts": "1709280000.000100"},
        {"ts": "1709280200.000100", "bot_id": "B1", "user": "B1", "text": "build passed", "files": [{"name": "log.txt"}]},
    ]))
    z.writestr("general/2025-02-01.json", json.dumps([{"ts": "1738368000.000100", "user": "U1", "text": "new year"}]))

# DiscordChatExporter JSON
d = root / "discord"
d.mkdir(exist_ok=True)
(d / "chan.json").write_text(json.dumps({"guild": {"id": "900"}, "channel": {"id": "901"}, "messages": [
    {"id": "1", "timestamp": "2023-05-05T18:19:23.207+00:00", "author": {"id": "a1", "isBot": False}, "content": "gg",
     "attachments": [{"fileName": "clip.mp4"}], "type": "Default"},
    {"id": "2", "timestamp": "2025-06-01T10:00:00+00:00", "author": {"id": "a2", "isBot": True}, "content": "", "type": "Default"},
]}))

# Notion Markdown/CSV export
n = root / "notion" / "Workspace Home"
n.mkdir(parents=True, exist_ok=True)
(n / "Plan abc123.md").write_text("# Plan\n\nCreated: March 3, 2023 4:12 PM\n\nSome text here.\n")
(n / "Tasks db.csv").write_text("Name,Created,Created by\nOne,\"March 4, 2023 9:00 AM\",Person A\nTwo,\"January 9, 2025 9:00 AM\",Person B\n")
(n / "image.png").write_bytes(b"\x89PNG fake")

# Jira CSV and ClickUp JSON
(root / "jira.csv").write_text("Issue key,Summary,Description,Issue Type,Status,Created,Updated,Resolved,Reporter\n"
                               "AB-1,Crash on load,The client crashes when the save file is empty,Bug,Done,2022-01-05 10:00,2022-01-06 10:00,2022-01-06 10:00,r1\n"
                               "AB-2,Polish,,Story,Open,2025-03-01 10:00,2025-03-01 10:00,,r2\n")
(root / "clickup.json").write_text(json.dumps({"tasks": [
    {"id": "t1", "date_created": "1672531200000", "date_updated": "1672617600000", "date_closed": "1672617600000",
     "creator": {"id": 1}}, {"id": "t2", "date_created": "1740787200000", "parent": "t1", "creator": {"id": 2}}]}))

# mbox: two mailboxes that share one message
(root / "mail").mkdir(exist_ok=True)
(root / "mail" / "copy.mbox").write_text(
    "From x@example.com Mon Jan  1 00:00:00 2024\nFrom: Sender One <one@example.org>\nDate: Mon, 1 Jan 2024 10:00:00 +0000\n"
    "Message-ID: <m1@example.org>\nSubject: hi\n\nbody\n")
(root / "mail" / "mail.mbox").write_text(
    "From x@example.com Mon Jan  1 00:00:00 2024\nFrom: Sender One <one@example.org>\nDate: Mon, 1 Jan 2024 10:00:00 +0000\n"
    "Message-ID: <m1@example.org>\nX-Gmail-Labels: Inbox,Important\nSubject: hi\n\nbody\n"
    "Content-Disposition: attachment; filename=\"q.pdf\"\n\n"
    "From y@example.com Tue Jan  2 00:00:00 2025\nFrom: two@example.net\nDate: Thu, 2 Jan 2025 10:00:00 +0000\n"
    "Message-ID: <m2@example.net>\nIn-Reply-To: <m1@example.org>\nSubject: re\n\nreply\n")

# SQL dumps: MySQL (gz) and PostgreSQL COPY
with gzip.open(root / "shop.sql.gz", "wt") as f:
    f.write("CREATE DATABASE `shop`;\nUSE `shop`;\nCREATE TABLE `zq_members` (\n  `id` int,\n  `email` varchar(9),\n  `created` datetime,\n"
            "  PRIMARY KEY (`id`)\n);\nINSERT INTO `zq_members` VALUES (1,'a@example.com','2021-04-01 00:00:00'),(2,'b,(x)','2025-04-01 00:00:00');\n")
(root / "pg.sql").write_text("CREATE TABLE public.zq_purchases (\n    id integer,\n    placed date\n);\n"
                             "COPY public.zq_purchases (id, placed) FROM stdin;\n1\t2020-01-01\n2\t2024-12-31\n\\.\n")

# BigQuery metadata (bq ls --format=json style)
(root / "bq.json").write_text(json.dumps(
    [{"tableReference": {"datasetId": "analytics_1", "tableId": f"events_202401{d:02d}"}, "type": "TABLE",
      "numRows": "1000", "numBytes": "50000", "creationTime": "1704067200000"} for d in range(1, 11)]
    + [{"tableReference": {"datasetId": "app", "tableId": "summary"}, "type": "VIEW", "creationTime": "1735689600000"}]))

# Plain files
fdir = root / "drive" / "Finance"
fdir.mkdir(parents=True, exist_ok=True)
(fdir / "budget.xlsx").write_bytes(b"fake spreadsheet")
(fdir / "budget copy.xlsx").write_bytes(b"fake spreadsheet")
(root / "drive" / "Notes.gdoc").write_text('{"doc_id": "x"}')
print("fixtures written to", root)
