---
name: measure-data
description: Count a company's SaaS and business data from local exports (Slack, Discord, Notion, ClickUp, Jira and other ticket CSVs, Gmail/mbox, SQL dumps, BigQuery metadata, Google Drive or any local folder) and write counts only - items and human share, people (hashed, never named) and peak active people per month, date spans, pre-2025 and pre-ChatGPT (2022-11-30) shares, characters and tokens, sizes, a label on every number, restriction flags, hashed resolved-ticket keys for bug-to-fix links, studio file detectors (builds, crashes, profiling, QA, audio middleware, localisation, engine content) and a status for every studio data category and connector (telemetry, backends, stores, ads) - into measure.json + report.md, ending with a short, clearly labelled "Why this is special" pitch written after the report (dream mode, on by default, --no-dream skips it). Full mode is the default; simple mode (optional) is a fast sampled pass, used only when asked to do a quick look. Use when the user asks to "count our Slack/Notion/email/DB", "inventory company data", "how much data do we have and how old is it", or to prepare inputs for a studio overview. Never reads content into the report.
---

# measure-data

Counts business data **on this machine** from exports the user already has. The script makes **no network calls**. It reads files, folders or zips and writes numbers. Message text, page titles, subjects, file names, table names, channel names, people and ids never reach the output. `<skill-dir>` below is the folder holding this SKILL.md.

## Modes

| mode | what runs | time |
|---|---|---|
| `--mode full` (default) | every record, plus duplicates, zip contents and fingerprints for de-duplication | depends on size |
| `--mode simple` | **Simple mode (optional): a fast sampled pass, used only when asked to do a quick look.** It parses a seeded sample of up to `--sample-files` files (default 200), or the first `--sample-mb` (default 64) of each mailbox or dump, and scales counts by size. Every figure is labelled `estimated`. | minutes |

Always run full mode unless the user explicitly asks for a quick look. Do not choose simple mode on your own.

## Steps

1. **Walk through the tool list.** Open [`docs/TOOLS.md`](docs/TOOLS.md) (or [`docs/tools.json`](docs/tools.json)): 249 tools and data sources that data buyers commonly ask about, grouped into 13 categories. Go through it category by category and ask "which of these do you use?", then "anything else in this category?". Keep it quick: skip a category the user rules out, and do not read out every row unless they want it. For each tool in use, the list gives the `measure-data` source and a one-line hint on what to export. `export then files` means there is no direct parser: the user exports the data into a folder and you run `files` on it. Code, art and design files go to measure-code and measure-art. If measure-disk already ran, start from its report: "Tools detected" (found on disk through each tool's `local_signals`) and `tools_owner_reported` in its measure.json, and only ask about the rest.
2. **List the sources.** Ask which systems the company used and where each export lives. One source is one tool plus one location, for example "Slack export zip from the old workspace". If there is no export yet, give the matching hint from *Getting an export* below. Do not log into anything on the user's behalf.
3. **Pick an output folder** outside the data, for example `./measure-out/data/`. Use one output folder for the whole company, because the `report` step merges everything inside it.
4. **Check every connector.** Before any output, ask explicitly about each connector group in `connector_prompts` of [`docs/tools.json`](docs/tools.json), even if the user did not mention it:
   - **telemetry**: Mixpanel, Amplitude, Google Analytics / BigQuery, GameAnalytics, Unity Analytics, PostHog
   - **backends**: Supabase, Firebase / Firestore, PlayFab, Nakama, AWS (S3, DynamoDB), Google Cloud Storage, Cloudflare R2 / D1 / Workers
   - **stores**: Google Play Console, App Store Connect, Steam (Steamworks)
   - **ads**: AdMob, Google Ads, Meta Ads, AppLovin, Unity Ads

   Then go through the 18 studio data categories (source control, work tracking, design and knowledge, builds and CI, crash reports, profiling, telemetry, QA and playtest, art source, engine content, audio, narrative and localisation, production and client, communication, player support and community, live ops and backend, business systems, servers and storage). Record what the user says with the `status` step; measured sources fill in `inspected` themselves:
   ```bash
   python3 <skill-dir>/scripts/measure_data.py status --out <out-dir> \
       --connector "Mixpanel=exists_inaccessible" --connector "Unity Ads=confirmed_not_used" \
       --category audio=self_reported --category profiling=confirmed_not_used
   ```
   Statuses: `inspected` (measured here), `exists_inaccessible` (it exists but this run could not read it), `self_reported` (the user said so, nothing measured), `confirmed_not_used`, `unknown`. Never drop a category or a connector: anything not established stays `unknown`. A measured source wins over a weaker answer.
5. **Measure each source, in full mode** (the default):
   ```bash
   python3 <skill-dir>/scripts/measure_data.py <source> <path> --out <out-dir> --label <label> [--tag project:<name>] \
       [--tag connector:<tool>] [--tag category:<key>] [--ownership own|client_owned|unclear] [--flag <name>] \
       [--version-history exported|retained_not_exported|not_retained] [--cutoff 2025-01-01] [--cutoff-early 2022-11-30]
   ```
   - `--tag connector:<tool>` marks a source as the export of a connector (for example `connector:PlayFab`), which makes that connector `inspected`. `--tag category:<key>` overrides the category a source counts for.
   - **Restrictions (record, don't rule).** Ownership defaults to `own`. Ask whether any source holds client-owned work, platform-holder NDA material, third-party middleware or bought assets, player personal data, staff personal data or secrets, and pass `--flag client_owned`, `--flag platform_nda`, `--flag third_party_middleware`, `--flag player_personal_data`, `--flag staff_personal_data` or `--flag secrets` (or `NAME=no`) as the user says. Some flags are also set from the counts (personal-data patterns, user tables, credential-like file names), labelled `estimated`.
   - **Version history.** For wikis, docs and drives, ask whether prior versions are kept and can be exported, and pass `--version-history`.
   - **Ticket links.** Ticket sources (`jira`, `clickup`, `tickets`) record counts by type (bug, task, story, other), resolved counts, and one-way hashes of resolved ticket keys, so bug-to-fix commits can be counted against measure-code. If the studio uses a `--link-salt`, pass the same one to measure-code.
   `<source>` is one of `slack`, `discord`, `notion`, `clickup`, `jira`, `tickets`, `mbox`, `sql`, `bigquery` or `files`. Use a distinct `--label` when the same tool appears twice, for example `--label crm-db-2023` and `--label crm-db-2024`. For anything big (multi-GB mbox, SQL dumps, whole drives), run it in the background with `nohup ... > run.log 2>&1 &` and check `run.log`. Runs are **resumable**: finished units (channels, files, mailboxes, dumps, top folders) are checkpointed in `<out-dir>/.state/`. `--force` starts over.
6. **Build the report:**
   ```bash
   python3 <skill-dir>/scripts/measure_data.py report --out <out-dir>
   ```
7. **Dream: "Why this is special"** (on by default). Skip this step only if the user passed or asked for `--no-dream` (no pitch); then record the skip with `python3 <skill-dir>/scripts/add_dream.py --no-dream --out <out-dir>`, or pass `--no-dream` to the `report` step. Otherwise, once the full report is complete, dream: re-read `report.md` and recall what you actually saw during the run (which systems the company used, the volumes, the spans, how many people were active), then write a short founder-style pitch for the company's data.
   - **4 to 6 sentences, casual and simple**, not verbose. Say what the counts miss: ambition, complexity and craft. For example years of a team planning in the open, a live-ops economy whose analytics run for years, or a player base big enough to need a sharded warehouse.
   - **Grounded only in what you saw in this run** and in the counts. You never read message text, so never describe what people said. No invented facts. No number that is not in the report (quote figures as the report shows them). No superlatives about things you did not inspect.
   - **Same privacy rules as everything else**: no names of people, channels, tables or files, no paths, emails, URLs, ids or secrets. Describe the product or genre in general terms.
   - Save it in a draft text file outside the exports, then run `python3 <skill-dir>/scripts/add_dream.py draft.txt --out <out-dir> [--deny "<a name you saw>" ...]`. It checks that the paragraph is not empty, has 4 to 6 sentences and no more than 160 words, holds no email, URL, handle, path, file name, token or denied name, and that every number in it appears in the report or `measure.json`. It warns about superlatives. Then it writes the `dream` block into `measure.json` and adds the **Why this is special** section at the very end of `report.md`, labelled as a pitch and kept apart from the counts. If it refuses, fix what it names and run it again: never loosen a fact to get past a check. `--check` validates without writing. Re-running `report` keeps the paragraph and checks it again. Delete the draft afterwards.
8. **Review with the user.** Read `report.md` together, including the category status, the connectors check and the pitch. Point out a source that shows `0` where the user expected data, a `dated_share` well under 100%, and `placeholders_not_downloaded` (cloud-only files that were never counted). These usually mean an incomplete export, not a lack of data.
9. **Hand off.** Send `measure.json` to whoever is assembling the overview. Delete `.state/` before sharing.

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
| anything else | see [`docs/TOOLS.md`](docs/TOOLS.md): one line per tool, with the source to use |

## Reading the numbers

- `human_count` / `human_share`: items not written by bots and not system events (joins, topic changes). `span.last_human` is the latest human item.
- `people.peak_active_in_a_month` (with `peak_month`) and `people.median_active_last_12_months` count distinct humans with a dated item in a month.
- `text.characters` / `text.token_estimate` (characters / 4) cover human text. For SQL they cover long string values of 100+ characters. For mail they cover body text outside attachments.
- Size figures are kept apart and never added together: `export_bytes` (the export on disk), `attachment_bytes_referenced` (sizes the export lists but does not contain), and `attachment_bytes` (attachments held inside the export).
- Mail: `counts.unique_messages` deduplicates on Message-ID across mailboxes, and `dedupe.overlap_share` shows how much the mailboxes overlap.
- Tickets: `description_or_comment_share` is the share of tickets with a real description (20+ characters) or a comment.
- Local folders: `working_documents` (documents, spreadsheets, presentations, PDFs) and `media_bytes_share`, so nobody quotes the disk total as the dataset. Zip contents are listed from the member index (`zip_members`, `zip_uncompressed_bytes`) and never extracted.

- **Labels.** Every material number has a label in `labels` (and in `cutoffs`): `verified` (counted from the export, with its scope), `estimated` (with a `method`, for example sampled counts, file dates or year-granular SQL dates), `self_reported`, `unknown` (shown as null, never 0) or `not_applicable`. The old flat fields stay as they were.
- **Cutoffs.** `cutoffs.pre_2025` (`--cutoff`, default 2025-01-01) and `cutoffs.pre_chatgpt` (`--cutoff-early`, default 2022-11-30) give the count and share of dated items before each date. Pre-ChatGPT work is the strongest evidence that the data is human work.
- `category_status` (18 keys) and `connectors` (one row per connector prompt) sit at the top of `measure.json`; `restrictions`, `version_history`, `traceable` (ticket sources) and `studio_files` (`files` source) sit on each source.
- `primary_count` is the headline unit: messages, pages or rows, tickets, rows or files.
- `pre_cutoff_share` is the share of *dated* items before `--cutoff`. `dated_share` says how many items carried a date at all.
- `people.distinct` counts hashed account ids or emails. `top1_share` and `top5_share` show how concentrated the activity is.
- SQL dates are the first date-like value in each row, so they are year-granular and approximate. Top tables are listed by rank and category (users, orders, events, ...), never by name.
- `fingerprints` (item sketches, table keys, schema signatures) let the same mailbox, database or folder be found when it is measured twice.
- `items_with_email_pattern` and `items_with_phone_pattern` count items that **contain** such a pattern. They help flag PII. Matches are never stored.

## Hard rules

- Read-only. Never modify, move or upload the user's data.
- Never paste message text, titles, names or ids into the chat or the report, even when asked to "show an example". Offer counts instead.
- If a source cannot be read, report it as unreadable with the reason, never as zero.
