---
name: measure-data
description: Count a company's SaaS and business data from local exports (Slack, Discord, Notion, ClickUp, Jira and other ticket CSVs, Gmail/mbox, SQL dumps, BigQuery metadata, Google Drive or any local folder) and write counts only - items and human share, people (hashed, never named) and peak active people per month, date spans, pre-2025 share, characters and tokens, sizes - into measure.json + report.md, ending with a short, clearly labelled "Why this is special" pitch written after the report (dream mode, on by default, --no-dream skips it). Start with --mode simple (sampled, minutes) to see which sources deserve a full run. Use when the user asks to "count our Slack/Notion/email/DB", "inventory company data", "how much data do we have and how old is it", or to prepare inputs for master-valuate. Never reads content into the report.
---

# measure-data

Counts business data **on this machine** from exports the user already has. The script makes **no network calls**. It reads files, folders or zips and writes numbers. Message text, page titles, subjects, file names, table names, channel names, people and ids never reach the output.

## Two modes

| mode | what runs | time |
|---|---|---|
| `--mode simple` (**recommended first run**) | listing and metadata; parses a seeded sample of up to `--sample-files` files (default 200), or the first `--sample-mb` (default 64) of each mailbox or dump, and scales counts by size. Local folders are listed only, with no hashing and no zip reading. Estimates are marked `~`. Each source gets a **full-run recommendation**. | minutes |
| `--mode full` (default) | every record, plus duplicates, zip contents and fingerprints for master-valuate | depends on size |

## Steps

1. **List the sources.** Ask which systems the company used and where each export lives. One source is one tool plus one location, for example "Slack export zip from the old workspace". If there is no export yet, give the matching hint from *Getting an export* below. Do not log into anything on the user's behalf.
2. **Pick an output folder** outside the data, for example `./measure-out/data/`. Use one output folder for the whole company, because the `report` step merges everything inside it.
3. **Simple pass first, one command per source:**
   ```bash
   python3 <skill-dir>/scripts/measure_data.py <source> <path> --out <out-dir>/simple --label <label> --mode simple
   python3 <skill-dir>/scripts/measure_data.py report --out <out-dir>/simple
   ```
   The headline table's last column says, per source, whether a full run is recommended, optional or not worth it. Agree with the user which sources to run fully. Then **run the full pass** into a separate folder:
   ```bash
   python3 <skill-dir>/scripts/measure_data.py <source> <path> --out <out-dir> --label <label> [--tag project:<name>] [--cutoff 2025-01-01]
   ```
   `<source>` is one of `slack`, `discord`, `notion`, `clickup`, `jira`, `tickets`, `mbox`, `sql`, `bigquery` or `files`. Use a distinct `--label` when the same tool appears twice, for example `--label crm-db-2023` and `--label crm-db-2024`. For anything big (multi-GB mbox, SQL dumps, whole drives), run it in the background with `nohup ... > run.log 2>&1 &` and check `run.log`. Runs are **resumable**: finished units (channels, files, mailboxes, dumps, top folders) are checkpointed in `<out-dir>/.state/`. `--force` starts over.
4. **Build the report:**
   ```bash
   python3 <skill-dir>/scripts/measure_data.py report --out <out-dir>
   ```
5. **Dream: "Why this is special"** (on by default). Skip this step only if the user passed or asked for `--no-dream` (no pitch); then record the skip with `python3 <skill-dir>/scripts/add_dream.py --no-dream --out <out-dir>`, or pass `--no-dream` to the `report` step. Otherwise, once the full report is complete, dream: re-read `report.md` and recall what you actually saw during the run (which systems the company used, the volumes, the spans, how many people were active), then write a short founder-style pitch for the company's data.
   - **4 to 6 sentences, casual and simple**, not verbose. Say what the counts miss: ambition, complexity and craft. For example years of a team planning in the open, a live-ops economy whose analytics run for years, or a player base big enough to need a sharded warehouse.
   - **Grounded only in what you saw in this run** and in the counts. You never read message text, so never describe what people said. No invented facts. No number that is not in the report (quote figures as the report shows them). No superlatives about things you did not inspect.
   - **Same privacy rules as everything else**: no names of people, channels, tables or files, no paths, emails, URLs, ids or secrets. Describe the product or genre in general terms.
   - Save it in a draft text file outside the exports, then run `python3 <skill-dir>/scripts/add_dream.py draft.txt --out <out-dir> [--deny "<a name you saw>" ...]`. It checks that the paragraph is not empty, has 4 to 6 sentences and no more than 160 words, holds no email, URL, handle, path, file name, token or denied name, and that every number in it appears in the report or `measure.json`. It warns about superlatives. Then it writes the `dream` block into `measure.json` and adds the **Why this is special** section at the very end of `report.md`, labelled as a pitch and kept apart from the counts. If it refuses, fix what it names and run it again: never loosen a fact to get past a check. `--check` validates without writing. Re-running `report` keeps the paragraph and checks it again. Delete the draft afterwards.
6. **Review with the user.** Read `report.md` together, including the pitch. Point out a source that shows `0` where the user expected data, a `dated_share` well under 100%, and `placeholders_not_downloaded` (cloud-only files that were never counted). These usually mean an incomplete export, not a lack of data.
7. **Hand off.** `measure.json` goes to **master-valuate**. Delete `.state/` before sharing.

## Getting an export (hints, not a tutorial)

| tool | what to point the script at |
|---|---|
| Slack | the workspace export zip from workspace settings (an admin can export public channels; private channels and DMs need a plan that allows it) |
| Discord | JSON from DiscordChatExporter, one file per channel, or your personal data package |
| Notion | *Export → Markdown & CSV* (drops most timestamps), or JSON/JSONL pages saved from the API by your own tooling |
| ClickUp | the workspace CSV export, or task JSON saved from the API |
| Jira | issue search → export CSV (all fields), XML, or JSON from the REST search endpoint |
| Linear, Asana, Trello, ... | use `tickets` on the CSV export; columns are matched by name |
| Gmail / mail | Google Takeout mbox files, or any `.mbox` folder (Thunderbird, Apple Mail export) |
| MySQL / PostgreSQL | `mysqldump` / `pg_dump` plain-SQL dumps, gzipped is fine |
| BigQuery | `bq ls --format=json` / `bq show --format=json` output, or `INFORMATION_SCHEMA.TABLES` / `TABLE_STORAGE` rows saved as CSV/JSON; metadata only, no table data |
| Drive, Dropbox, OneDrive, NAS | the synced folder; make files available offline first, or they show up as `placeholders_not_downloaded` |

## Reading the numbers

- `human_count` / `human_share`: items not written by bots and not system events (joins, topic changes). `span.last_human` is the latest human item.
- `people.peak_active_in_a_month` (with `peak_month`) and `people.median_active_last_12_months` count distinct humans with a dated item in a month.
- `text.characters` / `text.token_estimate` (characters / 4) cover human text. For SQL they cover long string values of 100+ characters. For mail they cover body text outside attachments.
- Size figures are kept apart and never added together: `export_bytes` (the export on disk), `attachment_bytes_referenced` (sizes the export lists but does not contain), and `attachment_bytes` (attachments held inside the export).
- Mail: `counts.unique_messages` deduplicates on Message-ID across mailboxes, and `dedupe.overlap_share` shows how much the mailboxes overlap.
- Tickets: `description_or_comment_share` is the share of tickets with a real description (20+ characters) or a comment.
- Local folders: `working_documents` (documents, spreadsheets, presentations, PDFs) and `media_bytes_share`, so nobody quotes the disk total as the dataset. Zip contents are listed from the member index (`zip_members`, `zip_uncompressed_bytes`) and never extracted.

- `primary_count` is the headline unit: messages, pages or rows, tickets, rows or files.
- `pre_cutoff_share` is the share of *dated* items before `--cutoff`. `dated_share` says how many items carried a date at all.
- `people.distinct` counts hashed account ids or emails. `top1_share` and `top5_share` show how concentrated the activity is.
- SQL dates are the first date-like value in each row, so they are year-granular and approximate. Top tables are listed by rank and category (users, orders, events, ...), never by name.
- `fingerprints` (item sketches, table keys, schema signatures) let master-valuate find the same mailbox, database or folder measured twice.
- `items_with_email_pattern` and `items_with_phone_pattern` count items that **contain** such a pattern. They help flag PII. Matches are never stored.

## Hard rules

- Read-only. Never modify, move or upload the user's data.
- Never paste message text, titles, names or ids into the chat or the report, even when asked to "show an example". Offer counts instead.
- If a source cannot be read, report it as unreadable with the reason, never as zero.
