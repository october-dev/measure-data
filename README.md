# measure-data

An agent skill for Claude Code, Codex, Grok, Hermes and other coding agents that counts a company's SaaS and business data **from local exports**: Slack, Discord, Notion, ClickUp, Jira (and any ticket CSV), Gmail/mbox, SQL dumps, BigQuery metadata, and Drive or any other folder. It writes counts, date spans, the pre-2025 share and sizes. It never writes content. The report ends with a short, clearly labelled **"Why this is special"** pitch that the agent writes after the report (dream mode).

Part of the October measurement skills: [measure-code](https://github.com/october-dev/measure-code) · **measure-data** · [measure-art](https://github.com/october-dev/measure-art) · [measure-disk](https://github.com/october-dev/measure-disk) · [measure-studio](https://github.com/october-dev/measure-studio)

## Install

Requires Python 3.9+. No pip packages.

This is a plain agent skill: [`SKILL.md`](SKILL.md) holds the instructions and `scripts/` holds the tools, so any coding agent that can read files and run Python can use it.

- **Claude Code**: clone it into your skills folder and it is picked up as the `measure-data` skill:
  ```bash
  git clone https://github.com/october-dev/measure-data ~/.claude/skills/measure-data
  ```
- **Codex**: clone it into the Codex skills folder:
  ```bash
  git clone https://github.com/october-dev/measure-data ~/.codex/skills/measure-data
  ```
  Or clone it anywhere and point Codex at `SKILL.md`. When Codex works inside the repo, it reads `AGENTS.md`, which points to `SKILL.md`.
- **Grok, Hermes and other agents**: clone it anywhere and tell the agent: *"Read `<path>/SKILL.md` and follow it."*

The commands below use `$SKILL` for the folder you cloned into, for example `SKILL=~/.claude/skills/measure-data`.

## Use

**Not sure what the company has?** [`docs/TOOLS.md`](docs/TOOLS.md) lists 249 tools and data sources that data buyers commonly ask about, in 13 categories (messaging, email, project management, support, CRM, finance, analytics, databases, document storage, code, design, automation and other), with the source to use for each one and what to export. The agent walks you through it before measuring. [`docs/tools.json`](docs/tools.json) has the same list for scripts and is the master copy: its `local_signals` field lists the file, folder and app-data traces a tool leaves on disk, which [measure-disk](https://github.com/october-dev/measure-disk) uses to detect tools on a laptop or drive (see [Local signals](docs/TOOLS.md#local-signals)). Its `domains` and `mail_domains` fields list each tool's web-app hosts and mail sender domains, for measure-disk's opt-in browser-history and mail-header discovery.

Full mode is the default and reads every record. **Simple mode (optional): a fast sampled pass, used only when asked to do a quick look** (`--mode simple`); every figure it writes is labelled `estimated`.

In your coding agent (Claude Code, Codex, Grok, Hermes ...):

> Use measure-data to count our Slack export at ~/exports/slack.zip, the Gmail Takeout in ~/exports/mail, and the shop database dump at ~/backups/shop.sql.gz

Full runs, directly:

```bash
S=$SKILL/scripts/measure_data.py
python3 $S slack ~/exports/slack.zip       --out ./measure-out/data
python3 $S mbox  ~/exports/mail            --out ./measure-out/data --label founder-mail
python3 $S sql   ~/backups/shop.sql.gz     --out ./measure-out/data --label shop-db --tag project:shop
python3 $S files ~/Google\ Drive/Shared    --out ./measure-out/data --label drive-shared
python3 $S status --out ./measure-out/data --connector "Mixpanel=exists_inaccessible" --category audio=self_reported
python3 $S report --out ./measure-out/data
```

### Studio assessment

measure-data also covers what a games-studio data assessment asks for:

- **A label on every number** (`labels`): verified, estimated (with a method), self-reported, unknown (null, never 0) or not applicable.
- **Two cutoffs** (`cutoffs`): before 2025-01-01 (`--cutoff`) and before ChatGPT, 2022-11-30 (`--cutoff-early`).
- **Category status** (`category_status`): all 18 studio data categories, each `inspected`, `exists_inaccessible`, `self_reported`, `confirmed_not_used` or `unknown`. None is ever dropped.
- **Connectors check** (`connectors`): telemetry (Mixpanel, Amplitude, GA4/BigQuery, GameAnalytics, Unity Analytics, PostHog), backends (Supabase, Firebase, PlayFab, Nakama, AWS, Google Cloud, Cloudflare R2/D1/Workers), stores (Play Console, App Store Connect, Steam) and ads (AdMob, Google Ads, Meta, AppLovin, Unity Ads), from `connector_prompts` in `docs/tools.json`. Record answers with `status`; `--tag connector:<tool>` marks a measured export.
- **Restriction flags** (`restrictions`): client-owned, platform NDA, third-party middleware, player personal data, staff personal data, secrets. Recorded, not ruled on; ownership defaults to `own`. `--ownership` and `--flag` take the owner's answers.
- **Traceable work** (`traceable` on ticket sources): tickets by type (bug, task, story, other), resolved counts, and one-way hashes of resolved ticket keys (`PROJ-123`, `CU-<id>`, `#123`), which can be matched to measure-code's hashed commit references to count bug-to-fix links.
- **Studio files** (`studio_files` on the `files` source): build and CI logs, crash dumps and exports, profiling captures (`.utrace`, PIX, RenderDoc, Tracy, Superluminal, Unity profiler), QA and certification documents by file name, Wwise and FMOD projects and banks, localisation files (`.po`, XLIFF, Ink, Yarn, string-table CSVs by header) and engine content counts (`.uasset`, `.umap`, `.unity`, `.prefab`, `.tscn`).
- **Version history** (`version_history`) for document sources.

| source | reads |
|---|---|
| `slack` | workspace export (folder or zip) |
| `discord` | DiscordChatExporter JSON, or the Discord data package |
| `notion` | Markdown/CSV/HTML export, or saved API objects (`.json`/`.jsonl`) |
| `clickup`, `jira`, `tickets` | CSV, JSON or Jira XML exports; columns are matched by name |
| `mbox` | `.mbox` files or a folder of them |
| `sql` | MySQL or PostgreSQL plain dumps, optionally `.gz` |
| `bigquery` | table metadata from `bq ls/show --format=json` or `INFORMATION_SCHEMA` |
| `files` | any folder |
| `status` | records the owner's category and connector answers in `status.json` (not a source) |

Tools without a direct parser (CRMs, finance, analytics and most others in [`docs/TOOLS.md`](docs/TOOLS.md)) are measured as `export then files`: export their data into a folder and run `files` on it.

What each source reports: the headline unit, human items and share, distinct people (hashed), peak active people per month, date span and last human item, pre-cutoff share, characters and token estimate, export size and referenced attachment bytes. Source-specific extras: unique mail after Message-ID dedupe, ticket description share, SQL table categories and long-text volume, BigQuery projects, datasets and daily-shard span, and for local folders working documents, media share and zip contents.

Output:

```
measure-out/data/
├── sources/<source>--<label>.json   # one per run
├── measure.json                     # all sources, schema october.measure/v1, kind "data"
├── report.md                        # ends with "Why this is special" once the pitch is added
├── dream.json                       # the pitch, kept for re-runs of `report`
└── .state/                          # checkpoints for resuming; delete before sharing
```

See [`examples/`](examples/) for output built from **synthetic** data.

## Dream mode: "Why this is special"

Counts miss ambition, complexity and craft. So after the report, the agent re-reads it and writes a 4-6 sentence founder-style pitch for the company's data. It is on by default; `report --no-dream` (or telling the agent you don't want a pitch) skips it.

The pitch must be grounded only in what the run saw and in the counts; message text is never read, so it never describes what people said. `scripts/add_dream.py` validates it before inserting it: 4-6 sentences and no more than 160 words, no emails, URLs, handles, paths, file names, tokens or names you pass with `--deny`, and every number must already appear in the report. It is written to `measure.json` as `dream` and rendered as the last section of `report.md`, labelled as a pitch, so the counts stay neutral and credible. See [`examples/`](examples/) for a synthetic one.

```bash
python3 $SKILL/scripts/add_dream.py draft.txt --out ./measure-out/data
```

## Privacy

- No network calls. Read-only.
- Never emitted: message or page text, titles, subjects, file, channel or table names, paths, people's names, ids or emails.
- People are counted through one-way hashes.
- PII patterns (emails, phone numbers) are counted per item and never stored.
- Before each source file is written, a check fails the run if an email address or an absolute path made it into the output.

## Resuming

Every source checkpoints finished units (a channel, a mailbox, a dump, a top-level folder) in `.state/`. Re-run the same command to continue, or pass `--force` to start over.

## Test

```bash
bash tests/selftest.sh
```

It builds synthetic exports for every source, measures them and checks the counts and that nothing leaks, and covers dream mode: insert, validation, re-runs and `--no-dream`. It covers the studio-assessment blocks (labels, both cutoffs, restriction flags, category status, connectors, traceable ticket hashes, version history and the studio file detectors) and older source files. It also checks that `docs/tools.json` parses, has no duplicate tools, maps every tool to a valid source that every `local_signals` entry is well formed (known kinds, valid globs and regular expressions, no absolute paths), and that `domains` and `mail_domains` are bare host names owned by one tool each.

## License

MIT
