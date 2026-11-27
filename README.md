# measure-data

A Claude Code skill that counts a company's SaaS and business data **from local exports**: Slack, Discord, Notion, ClickUp, Jira (and any ticket CSV), Gmail/mbox, SQL dumps, BigQuery metadata, and Drive or any other folder. It writes counts, date spans, the pre-2025 share and sizes. It never writes content. The report ends with a short, clearly labelled **"Why this is special"** pitch that Claude writes after the report (dream mode).

Part of the October measurement skills: [measure-code](https://github.com/october-dev/measure-code) · **measure-data** · [measure-art](https://github.com/october-dev/measure-art) · [master-valuate](https://github.com/october-dev/master-valuate)

## Install

Requires Python 3.9+. No pip packages.

```bash
git clone https://github.com/october-dev/measure-data ~/.claude/skills/measure-data
```

## Use

**Start with simple mode.** It samples each export, takes minutes, and recommends which sources deserve a full run:

```bash
S=~/.claude/skills/measure-data/scripts/measure_data.py
python3 $S slack ~/exports/slack.zip --out ./measure-out/data-simple --mode simple
python3 $S report --out ./measure-out/data-simple
```

Then run the full pass (the default mode) on the sources worth it.

In Claude Code:

> Use measure-data to count our Slack export at ~/exports/slack.zip, the Gmail Takeout in ~/exports/mail, and the shop database dump at ~/backups/shop.sql.gz

Full runs, directly:

```bash
S=~/.claude/skills/measure-data/scripts/measure_data.py
python3 $S slack ~/exports/slack.zip       --out ./measure-out/data
python3 $S mbox  ~/exports/mail            --out ./measure-out/data --label founder-mail
python3 $S sql   ~/backups/shop.sql.gz     --out ./measure-out/data --label shop-db --tag project:shop
python3 $S files ~/Google\ Drive/Shared    --out ./measure-out/data --label drive-shared
python3 $S report --out ./measure-out/data
```

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

Counts miss ambition, complexity and craft. So after the report, Claude re-reads it and writes a 4-6 sentence founder-style pitch for the company's data. It is on by default; `report --no-dream` (or telling Claude you don't want a pitch) skips it.

The pitch must be grounded only in what the run saw and in the counts; message text is never read, so it never describes what people said. `scripts/add_dream.py` validates it before inserting it: 4-6 sentences and no more than 160 words, no emails, URLs, handles, paths, file names, tokens or names you pass with `--deny`, and every number must already appear in the report. It is written to `measure.json` as `dream` and rendered as the last section of `report.md`, labelled as a pitch, so the counts stay neutral and credible. See [`examples/`](examples/) for a synthetic one.

```bash
python3 ~/.claude/skills/measure-data/scripts/add_dream.py draft.txt --out ./measure-out/data
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

It builds synthetic exports for every source, measures them and checks the counts and that nothing leaks, and covers dream mode: insert, validation, re-runs and `--no-dream`.

## License

MIT
