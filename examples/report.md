# Business data measurement

Produced with measure-data 0.4.0 (full mode). Counts only: no content, names, titles, paths or ids. Figures marked ~ are estimates scaled from a sample.

## 1. Headline

| source | label | unit | count | human share | first | last | pre-cutoff | peak people/month | tokens | size | full run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bigquery | starfall-analytics | rows | 2,840,000,000 | n/a | 2020-02-14 | 2024-06-30 | 100.0% | n/a | 0 | 1.8 TB | already full |
| files | drive-shared | files | 22,400 | n/a | 2015-05-02 | 2024-12-01 | 97.8% | n/a | 0 | 383.7 GB | already full |
| jira | starfall-jira | tickets | 14,820 | 93.0% | 2019-04-02 | 2024-08-01 | 100.0% | 13 | 2,350,000 | n/a | already full |
| mbox | founder-mail | messages | 61,200 | 93.0% | 2016-01-08 | 2025-03-02 | 99.2% | 2,029 | 0 | 17.6 GB | already full |
| notion | studio-wiki | pages | 3,890 | n/a | 2019-01-15 | 2024-10-03 | 100.0% | n/a | 5,425,000 | n/a | already full |
| slack | studio-slack | messages | 412,300 | 93.0% | 2018-06-04 | 2024-12-18 | 100.0% | 26 | 15,450,000 | n/a | already full |
| sql | players-db-2022-backup | rows | 33,100,000 | n/a | 2020-01-01 | 2022-12-31 | 100.0% | n/a | 0 | 5.8 GB | already full |
| sql | players-db-2023 | rows | 39,300,000 | n/a | 2020-01-01 | 2023-12-31 | 100.0% | n/a | 0 | 6.9 GB | already full |

Pre-cutoff = share of dated items before 2025-01-01. Tokens = characters / 4.

| source | label | pre-2025 items | pre-2025 share | pre-ChatGPT items | pre-ChatGPT share | label |
|---|---|---|---|---|---|---|
| bigquery | starfall-analytics | 1,586 | 100.0% | 998 | 62.9% | verified |
| files | drive-shared | 21,900 | 97.8% | 20,516 | 91.6% | estimated |
| jira | starfall-jira | 14,820 | 100.0% | 12,872 | 86.9% | verified |
| mbox | founder-mail | 60,700 | 99.2% | 51,516 | 84.2% | verified |
| notion | studio-wiki | 3,890 | 100.0% | 3,284 | 84.4% | verified |
| slack | studio-slack | 412,300 | 100.0% | 360,652 | 87.5% | verified |
| sql | players-db-2022-backup | 33,100,000 | 100.0% | 31,987,397 | 96.6% | estimated |
| sql | players-db-2023 | 39,000,000 | 100.0% | 20,000,000 | 51.3% | estimated |

Pre-2025 = before 2025-01-01; pre-ChatGPT = before 2022-11-30. Unknown is shown as n/a, never as 0.

## Category status

Every category of the studio checklist, with a status. None is dropped.

| category | status | evidence | sources | label |
|---|---|---|---|---|
| source control | self reported | reported by the owner | 0 | self_reported |
| work tracking | inspected | measured export | 1 | verified |
| design knowledge | inspected | measured export | 1 | verified |
| builds ci | exists inaccessible | exists, not accessible to this run | 0 | unknown |
| crash reports | inspected | files found in a measured folder | 1 | verified |
| profiling | unknown | not established | 0 | unknown |
| telemetry | inspected | measured export | 1 | verified |
| qa playtest | inspected | files found in a measured folder | 1 | verified |
| art source | self reported | reported by the owner | 0 | self_reported |
| engine content | self reported | reported by the owner | 0 | self_reported |
| audio | self reported | reported by the owner | 0 | self_reported |
| narrative localisation | inspected | files found in a measured folder | 1 | verified |
| production client | unknown | not established | 0 | unknown |
| communication | inspected | measured export | 2 | verified |
| player support community | confirmed not used | owner confirmed it is not used | 0 | self_reported |
| liveops backend | inspected | measured export | 2 | verified |
| business systems | unknown | not established | 0 | unknown |
| servers storage | inspected | measured export | 1 | verified |

## Connectors check

Telemetry, backends, stores and ads the agent asked about explicitly.

| group | connector | status | label |
|---|---|---|---|
| telemetry | Mixpanel | confirmed not used | self_reported |
| telemetry | Amplitude | unknown | unknown |
| telemetry | Google Analytics | unknown | unknown |
| telemetry | BigQuery | inspected | verified |
| telemetry | GameAnalytics | unknown | unknown |
| telemetry | Unity Analytics | unknown | unknown |
| telemetry | PostHog | unknown | unknown |
| backends | Supabase | unknown | unknown |
| backends | Firebase | self reported | self_reported |
| backends | Firestore | unknown | unknown |
| backends | PlayFab | unknown | unknown |
| backends | Nakama | unknown | unknown |
| backends | AWS S3 | unknown | unknown |
| backends | DynamoDB | unknown | unknown |
| backends | Google Cloud Storage | unknown | unknown |
| backends | Cloudflare R2 | unknown | unknown |
| backends | Cloudflare D1 | unknown | unknown |
| backends | Cloudflare Workers | unknown | unknown |
| stores | Google Play Console | exists inaccessible | unknown |
| stores | App Store Connect | exists inaccessible | unknown |
| stores | Steam (Steamworks) | unknown | unknown |
| ads | AdMob | self reported | self_reported |
| ads | Google Ads | unknown | unknown |
| ads | Meta Ads | unknown | unknown |
| ads | AppLovin | unknown | unknown |
| ads | Unity Ads | confirmed not used | self_reported |

## 2. bigquery: starfall-analytics

| metric | value |
|---|---|
| tables | 1,580 |
| views | 6 |
| datasets | 3 |
| bytes | 1.8 TB |
| table entries | 1,586 |
| rows | 2,840,000,000 |
| human items | n/a (n/a) |
| last human item | n/a |
| people (distinct, hashed) | 0 |
| bot accounts | 3 |
| peak active people in one month | n/a (n/a) |
| median active people, last 12 months | n/a |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 0 / 0 |
| dated share | 100.0% |
| active months | 55 |
| items in last 12 active months | 113,600,000 |

Restrictions (recorded, not ruled on): ownership own; no flag established.

| year | items |
|---|---|
| 2020 | 300 |
| 2021 | 365 |
| 2022 | 365 |
| 2023 | 365 |
| 2024 | 191 |

- daily-sharded table: 1,563 days, 2020-02-14 to 2024-06-30

_Note: Metadata only: table counts, rows and bytes as BigQuery reports them. Daily-sharded tables (events_YYYYMMDD) give the analytics date span._

## 3. files: drive-shared

| metric | value |
|---|---|
| folders | 3,100 |
| bytes | 383.7 GB |
| duplicate files | 1,900 |
| duplicate bytes | 21.4 GB |
| cloud only google docs | 2,600 |
| placeholders not downloaded | 0 |
| files | 22,400 |
| human items | n/a (n/a) |
| last human item | n/a |
| people (distinct, hashed) | 0 |
| bot accounts | 3 |
| peak active people in one month | n/a (n/a) |
| median active people, last 12 months | n/a |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 0 / 0 |
| dated share | 100.0% |
| active months | 110 |
| items in last 12 active months | 896 |

Studio files: build logs 0; CI configs 0; crash dumps 0; profiling captures 0; QA and certification documents 14; Wwise/FMOD projects 0; localisation files 22; engine content .uasset 0, .umap 0, .unity 0, .prefab 0, .tscn 0.

Restrictions (recorded, not ruled on): ownership own; flags: platform nda (estimated).

Version history: unknown (unknown).

| year | items |
|---|---|
| 2015 | 900 |
| 2016 | 1,500 |
| 2017 | 2,100 |
| 2018 | 2,900 |
| 2019 | 3,800 |
| 2020 | 4,100 |
| 2021 | 3,300 |
| 2022 | 2,100 |
| 2023 | 1,200 |
| 2024 | 500 |

| file family | files | size |
|---|---|---|
| image | 9,100 | 56.8 GB |
| document | 4,300 | 2.8 GB |
| video | 1,200 | 270.1 GB |
| spreadsheet | 2,100 | 858.3 MB |
| pdf | 3,100 | 8.4 GB |
| other | 2,600 | 44.8 GB |

Working documents: 9,500 files, 12.0 GB. Image, video and audio are 85.0% of bytes.


_Note: Dates are file modification times, which copies and syncs can reset. Duplicates are counted within this source only._

## 4. jira: starfall-jira

| metric | value |
|---|---|
| export files | 1 |
| subtasks | 3,100 |
| tickets closed | 12,900 |
| tickets edited after creation | 14,100 |
| tickets with comments | 8,800 |
| type bug | 6,100 |
| type story | 3,900 |
| type task | 4,200 |
| type epic | 120 |
| type other | 500 |
| tickets | 14,820 |
| human items | 13,782 (93.0%) |
| last human item | 2024-08-01 |
| people (distinct, hashed) | 19 |
| bot accounts | 3 |
| peak active people in one month | 13 (2020-11) |
| median active people, last 12 months | 3 |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 9,400,000 / 2,350,000 |
| dated share | 100.0% |
| active months | 66 |
| items in last 12 active months | 592 |

| ticket type | total | resolved | hashed resolved keys |
|---|---|---|---|
| bug | 6,100 | 5,700 | 5,700 |
| task | 4,200 | 3,700 | 3,700 |
| story | 3,900 | 3,500 | 3,500 |
| other | 620 | 0 | 0 |

_Traceable work: ticket type and resolution from the export's type, status and resolved-date columns; keys of resolved tickets hashed one-way (link_hash) so master-valuate can match them to commit messages (verified)._

Restrictions (recorded, not ruled on): ownership own; no flag established.

| year | items |
|---|---|
| 2019 | 1,800 |
| 2020 | 4,100 |
| 2021 | 4,600 |
| 2022 | 2,600 |
| 2023 | 1,300 |
| 2024 | 420 |


## 5. mbox: founder-mail

| metric | value |
|---|---|
| mailboxes | 3 |
| mailbox bytes | 17.6 GB |
| thread starters | 21,400 |
| attachments | 15,300 |
| label inbox | 30,100 |
| label sent | 16,900 |
| label spam | 2,100 |
| messages by bots | 19,800 |
| messages | 61,200 |
| human items | 56,916 (93.0%) |
| last human item | 2025-03-02 |
| people (distinct, hashed) | 2,900 |
| bot accounts | 3 |
| peak active people in one month | 2,029 (2020-11) |
| median active people, last 12 months | 580 |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 0 / 0 |
| dated share | 100.0% |
| active months | 110 |
| items in last 12 active months | 2,448 |

Restrictions (recorded, not ruled on): ownership own; no flag established.

| year | items |
|---|---|
| 2016 | 3,100 |
| 2017 | 5,200 |
| 2018 | 7,400 |
| 2019 | 9,100 |
| 2020 | 10,200 |
| 2021 | 9,400 |
| 2022 | 7,800 |
| 2023 | 5,200 |
| 2024 | 3,300 |
| 2025 | 500 |

- sender domains: 1,450; top domain share 31.0%

## 6. notion: studio-wiki

| metric | value |
|---|---|
| top level roots | 12 |
| databases | 41 |
| database rows | 6,120 |
| pages and rows | 10,010 |
| attachments | 2,300 |
| attachment bytes | 2.9 GB |
| items with email pattern | 160 |
| pages | 3,890 |
| human items | n/a (n/a) |
| last human item | n/a |
| people (distinct, hashed) | 0 |
| bot accounts | 3 |
| peak active people in one month | n/a (n/a) |
| median active people, last 12 months | n/a |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 21,700,000 / 5,425,000 |
| dated share | 100.0% |
| active months | 66 |
| items in last 12 active months | 155 |

Restrictions (recorded, not ruled on): ownership own; flags: staff personal data (estimated).

Version history: retained not exported (self_reported).

| year | items |
|---|---|
| 2019 | 600 |
| 2020 | 1,100 |
| 2021 | 1,000 |
| 2022 | 640 |
| 2023 | 380 |
| 2024 | 170 |


## 7. slack: studio-slack

| metric | value |
|---|---|
| conversations | 96 |
| conversations public | 58 |
| conversations private | 21 |
| conversations dm | 17 |
| threads | 18,400 |
| thread replies | 96,100 |
| files shared | 12,800 |
| reactions | 71,000 |
| items with email pattern | 2,100 |
| items with phone pattern | 340 |
| messages by bots | 30,100 |
| messages | 412,300 |
| human items | 383,439 (93.0%) |
| last human item | 2024-12-18 |
| people (distinct, hashed) | 38 |
| bot accounts | 3 |
| peak active people in one month | 26 (2020-11) |
| median active people, last 12 months | 7 |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 61,800,000 / 15,450,000 |
| dated share | 100.0% |
| active months | 77 |
| items in last 12 active months | 16,492 |

Restrictions (recorded, not ruled on): ownership own; flags: staff personal data (estimated).

| year | items |
|---|---|
| 2018 | 21,000 |
| 2019 | 88,000 |
| 2020 | 104,000 |
| 2021 | 92,000 |
| 2022 | 61,000 |
| 2023 | 34,000 |
| 2024 | 12,300 |

Attachments by family: image 8,100, pdf 1,900, video 1,100, document 900, other 800


## 8. sql: players-db-2022-backup

| metric | value |
|---|---|
| dump files | 1 |
| dump bytes | 5.8 GB |
| databases | 1 |
| tables | 48 |
| tables with rows | 44 |
| rows | 33,100,000 |
| human items | n/a (n/a) |
| last human item | n/a |
| people (distinct, hashed) | 0 |
| bot accounts | 3 |
| peak active people in one month | n/a (n/a) |
| median active people, last 12 months | n/a |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 0 / 0 |
| dated share | 99.2% |
| active months | 44 |
| items in last 12 active months | 1,572,000 |

Restrictions (recorded, not ruled on): ownership own; flags: player personal data (estimated).

| year | items |
|---|---|
| 2020 | 6,100,000 |
| 2021 | 13,900,000 |
| 2022 | 13,100,000 |

Dump with 48 tables and 33,100,000 rows. Largest tables (names withheld):

| rank | category | rows | columns | years |
|---|---|---|---|---|
| 1 | events | 26,300,000 | 9 | 2020-2022 |
| 2 | games | 5,400,000 | 14 | 2020-2022 |
| 3 | users | 1,180,000 | 22 | 2020-2022 |
| 4 | payments | 214,000 | 11 | 2020-2022 |


_Note: A row's date is the first date-like value in it, so dates are an approximation of when rows were written._

## 9. sql: players-db-2023

| metric | value |
|---|---|
| dump files | 1 |
| dump bytes | 6.9 GB |
| databases | 1 |
| tables | 48 |
| tables with rows | 44 |
| rows | 39,300,000 |
| human items | n/a (n/a) |
| last human item | n/a |
| people (distinct, hashed) | 0 |
| bot accounts | 3 |
| peak active people in one month | n/a (n/a) |
| median active people, last 12 months | n/a |
| top person share / top 5 | 22.0% / 61.0% |
| characters / token estimate | 0 / 0 |
| dated share | 99.2% |
| active months | 44 |
| items in last 12 active months | 1,572,000 |

Restrictions (recorded, not ruled on): ownership own; flags: player personal data (estimated).

| year | items |
|---|---|
| 2020 | 6,100,000 |
| 2021 | 13,900,000 |
| 2022 | 11,800,000 |
| 2023 | 7,200,000 |

Dump with 48 tables and 39,300,000 rows. Largest tables (names withheld):

| rank | category | rows | columns | years |
|---|---|---|---|---|
| 1 | events | 31,200,000 | 9 | 2020-2023 |
| 2 | games | 6,400,000 | 14 | 2020-2023 |
| 3 | users | 1,180,000 | 22 | 2020-2023 |
| 4 | payments | 214,000 | 11 | 2020-2023 |


_Note: A row's date is the first date-like value in it, so dates are an approximation of when rows were written._

## Caveats

- People are counted by hashed account id or email; one person with two accounts counts twice.
- Peak active people counts distinct humans with a dated item in a month; sources that record only creators give a floor.
- `items_with_email_pattern` and `items_with_phone_pattern` count items that contain such a pattern. Matches are never stored.
- Attachment bytes are what the export references; files that are not in the export were not downloaded.
- Every number carries a label in measure.json (`labels`): verified, estimated (with a method), self-reported, unknown or not applicable. Unknown is null, never 0.

## Why this is special

_Founder-style pitch written by the AI agent after the audit, from what it inspected in this run. It is not a measurement and changes no count above._

This is the operating memory of a working game studio, not a pile of exports. 412,300 Slack messages, 14,820 tickets and 3,890 wiki pages show a team that planned, argued and shipped in the open for years. A player database of 39,300,000 rows and 2,840,000,000 analytics rows say there were real players behind the game. At its peak 26 people were talking in Slack in a single month. Nearly all of it predates 2025, so it is genuine human work history that is very hard to recreate.
