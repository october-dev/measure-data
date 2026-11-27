# Tools data buyers ask about

A checklist of 249 tools and data sources across 13 categories. Go through it with the person who knows the company's stack and mark the ones in use. For each one, the table says which `measure-data` source reads it and what to export.

- **source** is the `measure_data.py` source to run. `export then files` means there is no direct parser: export the data (CSV, JSON, PDF, ...) into a folder and run `files` on that folder, which counts files, sizes, dates and working documents.
- **category** lists every category the tool fits; the table is grouped by the first one shown in bold.
- Code, art and design files are measured with [measure-code](https://github.com/october-dev/measure-code) and [measure-art](https://github.com/october-dev/measure-art); the rows for those tools say so.
- Export only what the company owns and is allowed to share. These are hints, not tutorials: menus change, so check the tool's own help.

The same list is in [`tools.json`](tools.json) for scripts and agents.

### Local signals

`tools.json` is the master list. Each tool also has a `local_signals` object: traces the tool leaves on a laptop or drive, used by [measure-disk](https://github.com/october-dev/measure-disk) to say which tools a company uses before anyone exports anything. It is empty when there is no trace we are confident about (most cloud-only tools). Every pattern matches case-insensitively; a pattern starting with `re:` is a regular expression, anything else is a shell-style glob.

| kind | matches | example |
|---|---|---|
| `files` | file names | `*.qbw`, `project.godot` |
| `folders` | folder names | `.svn`, `ChatExport_*` |
| `folder_contains` | a folder holding entries matching every pattern of one group | `["channels.json", "users.json"]` |
| `zip_contains` | a `.zip` whose member list (names only, nothing decompressed) matches every pattern of one group | `["messages/index.json", "servers/index.json"]` |
| `csv_header` | a `.csv` whose header line has every column of one group | `["Summary", "Issue key", "Issue id"]` |
| `file_head` | a file matching `files` whose first 4 KB contain `contains` | `{"files": "*.sql", "contains": "PostgreSQL database dump"}` |
| `app_data` | a folder under the desktop app-data roots (Application Support, Containers, Group Containers, `%APPDATA%`, `%LOCALAPPDATA%`, `~/.config`); `/` separates nested folders | `Slack`, `Microsoft/Teams` |

Only names, header lines and the first bytes of a file are read, in memory. Tools that read these signals must output counts only, never the matching names or paths.

### Web and mail domains

Each tool also has `domains` (hosts of its web app, e.g. `app.hubspot.com` is matched by `hubspot.com`) and `mail_domains` (domains its notification and billing mail comes from, e.g. `slack.com`, `atlassian.net`). A host matches itself and its subdomains, and each host belongs to one tool only. measure-disk's opt-in `--discover-tools` counts browser-history visits and mail by sender domain against these lists, and writes only tool names, counts and years. Both lists are empty where the tool has no dedicated domain (for example, tools that live under a shared google.com or microsoft.com host). Jira and Confluence Cloud share `atlassian.net`; it is listed under Jira.

### Connector prompts and studio categories

`connector_prompts` lists the connectors the agent must ask about explicitly before any output, in four groups: `telemetry`, `backends`, `stores` and `ads`. measure-data's `status` step records an answer for each one, and its report shows every connector with a status, so none is skipped silently.

`studio_category_map` maps each tool to one of the 18 studio data categories (source control, work tracking, design and knowledge, builds and CI, crash reports, profiling, telemetry, QA and playtest, art source, engine content, audio, narrative and localisation, production and client, communication, player support and community, live ops and backend, business systems, servers and storage): `by_category` gives the default for each of the 13 list categories and `by_tool` overrides it for single tools (for example Jenkins → builds and CI, Wwise → audio). measure-disk uses it to turn detected and owner-reported tools into category statuses.

## Categories

- [Messaging](#messaging) (20)
- [Emailing](#emailing) (15)
- [Project management](#project-management) (20)
- [Support](#support) (14)
- [CRM](#crm) (33)
- [Finance](#finance) (28)
- [Analytics](#analytics) (28)
- [Infra & databases](#infra--databases) (24)
- [Document storage](#document-storage) (18)
- [Code management](#code-management) (14)
- [Design](#design) (15)
- [Automation](#automation) (2)
- [Other](#other) (18)

## Messaging

| tool | category | source | what to export |
|---|---|---|---|
| ChatGPT | **Messaging**, Other | `export then files` | Settings data export: the conversations JSON in the zip. |
| Claude | **Messaging**, Other | `export then files` | Account data export: the conversations JSON in the zip. |
| Connecteam | **Messaging**, Other | `export then files` | CSV exports of chats, time clock and task records. |
| Discord | **Messaging** | `discord` | Per-channel JSON from DiscordChatExporter, or the account data package. |
| Facebook Messenger | **Messaging**, Support | `export then files` | Page inbox conversations via Meta Business data download (JSON). |
| Gemini | **Messaging**, Other | `export then files` | Google Takeout 'My Activity' for Gemini apps. |
| Google Chat | **Messaging** | `export then files` | Google Takeout (or Vault) export of spaces and DMs as JSON. |
| Grok | **Messaging**, Other | `export then files` | Account data export of conversations. |
| HipChat | **Messaging** | `export then files` | The legacy data export archive, if it was kept before shutdown. |
| Humanity | **Messaging** | `export then files` | CSV reports of shifts, schedules and staff messages. |
| Lark | **Messaging** | `export then files` | Admin data export of chats and docs. |
| Microsoft Teams | **Messaging** | `export then files` | Admin eDiscovery or Graph export of chats and channel posts as JSON or HTML. |
| OneSignal | **Messaging** | `export then files` | CSV of notifications sent and delivery stats. |
| Perplexity | **Messaging**, Other | `export then files` | Thread export or account data request. |
| Pumble | **Messaging** | `export then files` | Workspace message export (admin) as JSON or CSV. |
| Skype | **Messaging** | `export then files` | Account data export of conversations (JSON inside a tar). |
| Slack | **Messaging** | `slack` | Workspace export zip from the admin settings; DMs and private channels need a plan that allows them. |
| Telegram | **Messaging** | `export then files` | Telegram Desktop 'Export chat history' in machine-readable JSON. |
| WhatsApp | **Messaging** | `export then files` | Per-chat 'Export chat' text files, or the Business API message log. |
| Ytel | **Messaging** | `export then files` | Call and SMS logs as CSV. |

## Emailing

| tool | category | source | what to export |
|---|---|---|---|
| Attentive | **Emailing**, CRM | `export then files` | Subscriber and campaign performance CSVs. |
| Cordial | **Emailing** | `export then files` | Contact and message-event exports from the data jobs area. |
| Customer.io | **Emailing** | `export then files` | People and segment CSVs, plus delivery data exports. |
| Email archives (generic mbox / eml) | **Emailing** | `mbox` | Any mailbox saved as .mbox or .eml files (Thunderbird, Apple Mail export, old backups). |
| Gmail | **Emailing** | `mbox` | Google Takeout Mail as .mbox files, one per label. |
| Google Workspace | **Emailing**, Document storage | `mbox` | Admin data export or Vault: mail as mbox, Drive as a synced folder. |
| Klaviyo | **Emailing**, CRM | `export then files` | Profiles, lists and campaign or flow metrics as CSV. |
| Mailchimp | **Emailing** | `export then files` | Audience, campaign and report CSV exports. |
| Mailmodo | **Emailing** | `export then files` | Contact lists and campaign reports as CSV. |
| Microsoft 365 | **Emailing**, Document storage, Messaging | `mbox` | Mailboxes exported as PST and converted to mbox; OneDrive and SharePoint as a synced folder. |
| Outlook / Exchange Online | **Emailing** | `mbox` | Export mailboxes to PST, then convert each to mbox. |
| Postscript | **Emailing**, CRM | `export then files` | Subscriber list and campaign report CSVs. |
| SendGrid | **Emailing** | `export then files` | Contacts CSV plus the email activity feed export. |
| SiteGround Mail | **Emailing** | `mbox` | Pull the mailbox over IMAP into a local client, then save it as mbox. |
| Zoho Mail | **Emailing** | `mbox` | Per-folder export in EML or mbox format from the mail settings. |

## Project management

| tool | category | source | what to export |
|---|---|---|---|
| Airtable | **Project management**, Other | `export then files` | Each table's grid view downloaded as CSV. |
| Asana | **Project management** | `tickets` | Per-project CSV export of tasks. |
| Avaza | **Project management** | `tickets` | Task and timesheet reports as CSV. |
| Basecamp | **Project management**, Messaging | `tickets` | Account export archive; to-dos and messages as CSV or JSON. |
| ClickUp | **Project management** | `clickup` | Workspace CSV export, or task JSON pulled from the API. |
| FunctionFox | **Project management** | `tickets` | Project, task and timesheet reports as CSV. |
| Jira | **Project management** | `jira` | Issue search export as CSV with all fields, or XML. |
| Kantata | **Project management** | `tickets` | Project and task reports as CSV. |
| Linear | **Project management** | `tickets` | Workspace CSV export of issues. |
| Mantis | **Project management** | `tickets` | Issues view exported as CSV. |
| Monday.com | **Project management** | `tickets` | Board export to Excel, saved as CSV. |
| Procore | **Project management**, Document storage | `export then files` | Project documents and RFI or submittal logs as CSV and PDF. |
| Redmine | **Project management** | `tickets` | Issues list exported as CSV with all columns. |
| Shortcut | **Project management** | `tickets` | Stories CSV export from the workspace settings. |
| Smartsheet | **Project management** | `tickets` | Each sheet exported as CSV or Excel. |
| Teamwork | **Project management** | `tickets` | Tasks exported as CSV per project. |
| TestRail | **Project management** | `tickets` | Test cases, runs and results exported as CSV. |
| Ticketing and project management (generic, tool-agnostic) | **Project management** | `tickets` | Any ticket or task CSV with created, status and description columns. |
| Trello | **Project management** | `tickets` | Board JSON export (or CSV on paid plans). |
| Wrike | **Project management** | `tickets` | Task table exported to CSV or Excel. |

## Support

| tool | category | source | what to export |
|---|---|---|---|
| Aircall | **Support**, Other | `export then files` | Call history CSV, plus recordings if they are wanted. |
| Freshchat | **Support**, Messaging | `tickets` | Conversation reports exported as CSV. |
| Freshdesk | **Support** | `tickets` | Ticket export from the tickets view as CSV. |
| Help Scout | **Support**, Emailing | `tickets` | Conversations exported as CSV from reports or via the API. |
| Helpwise | **Support** | `tickets` | Conversation and contact exports as CSV. |
| In-house support platform | **Support** | `tickets` | A CSV or JSON dump of tickets with created dates and descriptions. |
| Intercom | **Support** | `tickets` | Conversation export (CSV) from the reports or data settings. |
| JustCall | **Support**, Messaging | `export then files` | Call and SMS logs as CSV. |
| LeadDesk | **Support**, Other | `export then files` | Call and campaign reports as CSV. |
| Plain | **Support** | `tickets` | Thread and customer data pulled from the API as JSON. |
| ProductFruits | **Support** | `export then files` | Usage and feedback reports as CSV. |
| RingCentral | **Support**, Other | `export then files` | Call log and message reports as CSV. |
| Ringover | **Support**, Other | `export then files` | Call history as CSV. |
| Zendesk | **Support** | `tickets` | Admin data export of tickets (JSON or CSV). |

## CRM

| tool | category | source | what to export |
|---|---|---|---|
| Amazon | **CRM**, Support | `export then files` | Seller Central order, inventory and business reports as CSV. |
| Ankorstore | **CRM**, Other | `export then files` | Order and retailer exports as CSV. |
| Attio | **CRM** | `export then files` | Each list or object exported as CSV. |
| BigCommerce | **CRM**, Other | `export then files` | Orders, customers and products as CSV. |
| Breely | **CRM**, Support | `export then files` | Bookings and client records as CSV. |
| ClickFunnels | **CRM**, Other | `export then files` | Contacts and order data as CSV. |
| Close CRM | **CRM** | `export then files` | Leads, opportunities and activities as CSV or JSON. |
| Copper | **CRM** | `export then files` | Records exported as CSV from settings. |
| CRM (generic, any CRM) | **CRM** | `export then files` | Every object (contacts, companies, deals, activities) as CSV. |
| DebtManager / CFT Pay | **CRM**, Finance | `export then files` | Account, payment and collections reports as CSV. |
| Deltek Vantagepoint | **CRM**, Finance, Project management | `export then files` | Project, billing and CRM reports as CSV. |
| Dynamics 365 | **CRM** | `export then files` | Entity views exported to Excel or CSV, or a Dataverse export. |
| FieldRoutes | **CRM** | `export then files` | Customer, appointment and billing reports as CSV. |
| GoHighLevel | **CRM**, Emailing | `export then files` | Contacts, opportunities and conversations as CSV. |
| Gorgias | **CRM**, Support | `tickets` | Ticket export as CSV from the views. |
| HousecallPro | **CRM** | `export then files` | Customers, jobs and invoices as CSV. |
| HubSpot | **CRM** | `export then files` | Export all records per object (contacts, companies, deals, tickets) as CSV. |
| iClosed | **CRM** | `export then files` | Bookings and contacts as CSV. |
| iON Pool Care | **CRM**, Support | `export then files` | Customer and service history reports as CSV. |
| JobNimbus | **CRM**, Project management | `export then files` | Contacts, jobs and tasks as CSV. |
| LeadSquared | **CRM** | `export then files` | Leads and activities as CSV. |
| LeadTruffle | **CRM** | `export then files` | Lead lists as CSV. |
| Luma | **CRM**, Other | `export then files` | Event guest lists and registrations as CSV. |
| Pipedrive | **CRM** | `export then files` | Deals, people, organizations and activities as CSV. |
| Salesflare | **CRM** | `export then files` | Contacts, accounts and opportunities as CSV. |
| Salesforce | **CRM** | `export then files` | Setup > Data Export: the weekly CSV zip of all objects. |
| ServiceTitan | **CRM** | `export then files` | Jobs, customers and invoices from reports as CSV. |
| Shopify | **CRM**, Other | `export then files` | Orders, customers and products as CSV from the admin. |
| SMRT | **CRM**, Finance, Other | `export then files` | Customer and transaction reports as CSV. |
| Total Office Manager | **CRM**, Other, Project management | `export then files` | Customer, job and invoice reports as CSV. |
| Vitally | **CRM**, Support | `export then files` | Accounts, users and notes as CSV. |
| Wodify | **CRM**, Support | `export then files` | Member, attendance and billing reports as CSV. |
| Zoho (Desk, CRM, Cliq) | **CRM**, Messaging, Support | `tickets` | Desk tickets as CSV; CRM modules and Cliq chats via the data backup. |

## Finance

| tool | category | source | what to export |
|---|---|---|---|
| Agicap | **Finance** | `export then files` | Cash-flow transactions as CSV or Excel. |
| AppFolio | **Finance**, CRM | `export then files` | Property, tenant and ledger reports as CSV. |
| Avalara | **Finance** | `export then files` | Transaction and filing reports as CSV. |
| Bexio | **Finance** | `export then files` | Invoices, contacts and bookings as CSV. |
| Bill.com | **Finance** | `export then files` | Bills, invoices and vendor lists as CSV. |
| Brex | **Finance** | `export then files` | Card and account transactions as CSV. |
| Chase Business | **Finance** | `export then files` | Account activity downloads as CSV. |
| DATEV | **Finance** | `export then files` | Bookings in the DATEV export format (CSV). |
| Epicor ERP | **Finance**, Infra & databases | `export then files` | BAQ or report exports as CSV. |
| FreshBooks | **Finance** | `export then files` | Invoices, expenses and clients as CSV. |
| Inkle | **Finance** | `export then files` | Bookkeeping and tax reports as CSV. |
| Kick | **Finance** | `export then files` | Transactions and reports as CSV. |
| Klarna | **Finance** | `export then files` | Settlement and order reports as CSV. |
| Mercury | **Finance** | `export then files` | Account transactions as CSV. |
| NetSuite | **Finance** | `export then files` | Saved searches of transactions and records as CSV. |
| Odoo | **Finance** | `export then files` | Records from any list view exported as CSV or Excel. |
| PayPal | **Finance** | `export then files` | Activity downloads as CSV. |
| QuickBooks | **Finance** | `export then files` | Reports (general ledger, transactions) and lists as Excel or CSV. |
| QuickBooks Desktop | **Finance** | `export then files` | Company file reports exported to Excel or CSV. |
| Ramp | **Finance** | `export then files` | Transactions and bills as CSV. |
| Sage 300 CRE | **Finance** | `export then files` | Job cost and ledger reports as CSV or Excel. |
| Sage Intacct | **Finance** | `export then files` | Reports and object lists as CSV. |
| Square | **Finance**, CRM | `export then files` | Transactions, items and customers as CSV. |
| Stripe | **Finance** | `export then files` | Payments, customers, invoices and balance reports as CSV. |
| Tally | **Finance** | `export then files` | Vouchers and ledgers exported as Excel or XML. |
| Unleashed | **Finance**, Other | `export then files` | Inventory, orders and invoices as CSV. |
| Xero | **Finance** | `export then files` | General ledger, invoices and contacts as CSV. |
| Zoho Books | **Finance** | `export then files` | Transactions and contacts as CSV. |

## Analytics

| tool | category | source | what to export |
|---|---|---|---|
| AdMob | **Analytics**, Finance | `export then files` | Network and mediation reports as CSV. |
| Amplitude | **Analytics** | `export then files` | Raw event export (JSON) or charts as CSV. |
| App Store Connect | **Analytics**, Finance | `export then files` | Sales and Trends, App Analytics and payments reports as CSV. |
| AppLovin | **Analytics**, Finance | `export then files` | MAX revenue and user-level ad reports as CSV. |
| Backtrace | **Analytics**, Code management | `export then files` | Crash and error groups from the API as JSON or CSV (counts by build and month). |
| BigQuery | **Analytics**, Infra & databases | `bigquery` | Table metadata only: `bq ls/show --format=json`, or INFORMATION_SCHEMA rows. |
| BugSplat | **Analytics**, Code management | `export then files` | Crash groups and reports from the API as JSON or CSV. |
| Datadog | **Analytics**, Infra & databases | `export then files` | Dashboards, monitors and log archive metadata as JSON. |
| GameAnalytics | **Analytics** | `export then files` | Raw event export (JSON) or dashboard reports as CSV. |
| Google Ads | **Analytics**, Other | `export then files` | Campaign, ad group and keyword reports as CSV. |
| Google Analytics | **Analytics** | `export then files` | Reports as CSV, or the BigQuery event export (then use bigquery). |
| Google Play Console | **Analytics**, Finance | `export then files` | Statistics, installs, ratings and earnings reports (Cloud Storage bucket download) as CSV. |
| Grafana | **Analytics** | `export then files` | Dashboard JSON models. |
| Meta Ads | **Analytics**, Other | `export then files` | Ads Manager reports as CSV. |
| Metabase | **Analytics** | `export then files` | Saved questions as CSV, plus the app database dump. |
| Mixpanel | **Analytics** | `export then files` | Raw event export (JSONL) per date range. |
| PostHog | **Analytics** | `export then files` | Event export as CSV or JSON, or a batch export to storage. |
| Power BI | **Analytics** | `export then files` | Report data exported as CSV, plus the .pbix files. |
| Segment | **Analytics** | `export then files` | Warehouse or storage destination files. |
| Semrush | **Analytics** | `export then files` | Project and position-tracking reports as CSV. |
| Sentry | **Analytics**, Code management | `export then files` | Issue lists and event data pulled from the API as JSON. |
| Snowflake | **Analytics**, Infra & databases | `export then files` | INFORMATION_SCHEMA.TABLES rows as CSV (sizes, row counts, dates). |
| Steam (Steamworks) | **Analytics**, Finance | `export then files` | Steamworks sales, wishlist, player and review reports as CSV. |
| SurveyMonkey | **Analytics** | `export then files` | Survey responses as CSV. |
| Tableau | **Analytics** | `export then files` | Workbooks (.twbx) and their data extracts. |
| Unity Ads | **Analytics**, Finance | `export then files` | Monetization and acquisition reports as CSV from the Unity dashboard or the stats API. |
| Unity Analytics | **Analytics** | `export then files` | Raw data export of events as JSON or CSV. |
| YouTube Analytics | **Analytics**, Other | `export then files` | Channel reports from YouTube Studio as CSV. |

## Infra & databases

| tool | category | source | what to export |
|---|---|---|---|
| AWS S3 | **Infra & databases** | `files` | Sync the bucket to a local folder (`aws s3 sync`). |
| Azure AI Search | **Infra & databases** | `export then files` | Index definitions and document counts as JSON. |
| Cloudflare D1 | **Infra & databases** | `export then files` | `wrangler d1 export` of each database (SQLite SQL), plus table row counts. |
| Cloudflare R2 | **Infra & databases** | `files` | Sync the bucket locally with an S3-compatible client. |
| Cloudflare Workers | **Infra & databases**, Analytics | `export then files` | Worker scripts go to measure-code; Workers Analytics and logs as JSON. |
| Databases (generic) | **Infra & databases** | `sql` | MySQL or PostgreSQL plain-SQL dumps; other engines as table CSVs. |
| DynamoDB | **Infra & databases** | `export then files` | Export to S3 (DynamoDB JSON), then sync it locally. |
| Firebase | **Infra & databases**, Analytics | `export then files` | Auth users export, Realtime Database JSON, Crashlytics and Analytics via the BigQuery export (then bigquery). |
| Firestore | **Infra & databases** | `export then files` | Managed export to Cloud Storage, or collections dumped as JSON. |
| Google Cloud Storage | **Infra & databases** | `files` | Copy the bucket locally (`gcloud storage cp -r`). |
| In-house platform database (generic) | **Infra & databases**, CRM, Support | `sql` | A plain SQL dump (MySQL or PostgreSQL). |
| Member portal | **Infra & databases**, CRM | `sql` | A plain SQL dump of the portal's database. |
| MongoDB | **Infra & databases** | `export then files` | `mongoexport` to JSON per collection. |
| MuleSoft | **Infra & databases** | `export then files` | API specs and flow definitions from the project files. |
| Nakama | **Infra & databases** | `sql` | `pg_dump` (or `cockroach dump`) of the Nakama database: accounts, storage, leaderboards, wallets. |
| Noloco | **Infra & databases**, Other | `export then files` | Collections as CSV. |
| OpenSearch | **Infra & databases** | `export then files` | Index stats and mappings as JSON, or a snapshot. |
| PlayFab | **Infra & databases**, Analytics | `export then files` | Player, economy and event data via Data Connections or the Admin API, saved as JSON or CSV. |
| PostgreSQL | **Infra & databases** | `sql` | `pg_dump` plain-SQL dump, gzipped is fine. |
| Redis | **Infra & databases** | `export then files` | Key counts and an RDB snapshot listing, not raw values. |
| SQL Server | **Infra & databases** | `export then files` | Tables as CSV (bcp or the export wizard); measure-data reads MySQL and PostgreSQL dumps only. |
| Supabase | **Infra & databases** | `sql` | `pg_dump` of the project database (plain SQL). |
| Warehouse / order management system (generic) | **Infra & databases**, Other | `sql` | A plain SQL dump of the system's database, or table CSVs. |
| Zilliz Cloud | **Infra & databases** | `export then files` | Collection stats and schema as JSON. |

## Document storage

| tool | category | source | what to export |
|---|---|---|---|
| Box | **Document storage** | `files` | The Box Drive folder or a full folder download. |
| Citrix ShareFile | **Document storage** | `files` | Download the folders, or sync them locally. |
| Coda | **Document storage**, Project management | `export then files` | Doc export (Markdown or HTML) and tables as CSV. |
| Confluence | **Document storage** | `export then files` | Space export as HTML or XML. |
| Crowdin | **Document storage**, Design | `export then files` | Project translations and string reports (XLIFF, CSV or JSON). |
| DocHub | **Document storage** | `export then files` | Documents downloaded as PDF. |
| DocuSign | **Document storage** | `export then files` | Completed envelopes downloaded as PDF, plus envelope reports as CSV. |
| Dropbox | **Document storage** | `files` | The synced Dropbox folder, files made available offline. |
| Google Drive | **Document storage** | `files` | The synced Drive folder, files made available offline (or Takeout). |
| Labstep | **Document storage**, Other | `export then files` | Experiments and protocols exported as PDF or JSON. |
| Legal drive | **Document storage** | `files` | The folder or synced drive holding the documents. |
| Local storage / PDF files | **Document storage** | `files` | Point it at the folder. |
| Lokalise | **Document storage**, Design | `export then files` | Key and translation export (JSON, XLIFF or CSV) per project. |
| Loom | **Document storage** | `export then files` | Video downloads plus transcripts. |
| Microsoft Excel | **Document storage** | `files` | The folder holding the workbooks. |
| Notion | **Document storage**, Project management | `notion` | Workspace export as Markdown & CSV, or page JSON saved from the API. |
| Research corpus | **Document storage** | `files` | The folder holding the papers, notes and datasets. |
| Wiki / documentation (generic) | **Document storage** | `export then files` | Wiki pages exported as Markdown or HTML. |

## Code management

| tool | category | source | what to export |
|---|---|---|---|
| Azure DevOps | **Code management**, Project management | `tickets` | Work-item query results as CSV; measure the code itself with measure-code. |
| Bitbucket | **Code management** | `tickets` | Issues and pull requests from the API; measure the code itself with measure-code. |
| Code repositories (generic, any git host) | **Code management** | `export then files` | Full clones of every repo; measure them with measure-code. |
| Cursor | **Code management** | `export then files` | Local chat and composer history from the app's storage. |
| GitHub | **Code management** | `tickets` | Issues and pull requests as JSON from the API; measure the code itself with measure-code. |
| GitLab | **Code management** | `tickets` | Issues exported as CSV; measure the code itself with measure-code. |
| GitLab wiki | **Code management** | `export then files` | Clone the wiki repository (it is Markdown in git). |
| Helix Swarm | **Code management** | `export then files` | Review records from the API as JSON. |
| Jenkins | **Code management** | `export then files` | Job configs and build history (the jobs folder). |
| Perforce | **Code management** | `export then files` | Depot history converted to git (git-p4), then measure-code. |
| Plastic SCM / Unity Version Control | **Code management** | `export then files` | Repository history (`cm log`, `cm find changeset`) or a git export, then measure-code. |
| Subversion (SVN) | **Code management** | `export then files` | Repository converted to git (git svn clone), then measure-code. |
| TeamCity | **Code management** | `export then files` | Build configurations and build history from the REST API as JSON; retained build logs. |
| Unreal Horde / UnrealGameSync | **Code management** | `export then files` | Job and build history from the Horde API as JSON; UGS badge and CIS history. |

## Design

| tool | category | source | what to export |
|---|---|---|---|
| 3D CAD files | **Design**, Document storage | `files` | The folder or share holding the models; measure-art counts them. |
| Adobe After Effects / Creative Cloud | **Design** | `files` | The project folders; measure-art counts them. |
| articy:draft | **Design**, Document storage | `files` | The articy project folder and its JSON or XML export; dialogue and story counts. |
| Blender | **Design** | `files` | The folder holding the .blend files; measure-art counts them. |
| Canva | **Design** | `export then files` | Designs downloaded as PDF or PNG; measure-art counts them. |
| Centric PLM | **Design**, Other, Project management | `export then files` | Product, material and style records as CSV or Excel. |
| Figma | **Design** | `export then files` | Files saved as .fig, plus comments from the API; measure-art counts the files. |
| FMOD | **Design** | `files` | The FMOD Studio project folder (.fspro, metadata, assets); measure-art counts the audio. |
| Godot | **Design**, Code management | `files` | The project folder; measure-art counts the assets and measure-code the scripts. |
| Lucid | **Design** | `export then files` | Documents exported as PDF or Visio, plus CSV of shape data. |
| Miro | **Design** | `export then files` | Boards exported as PDF or image, and CSV where offered. |
| Production asset files | **Design**, Document storage | `files` | The folder or NAS share; measure-art counts creative formats. |
| Unity | **Design**, Code management | `files` | The project folder; measure-art counts the assets and measure-code the scripts. |
| Unreal Engine | **Design**, Code management | `files` | The project folder; measure-art counts the assets and measure-code the C++ and config. |
| Wwise | **Design** | `files` | The Wwise project folder (.wproj, work units, originals); measure-art counts the audio. |

## Automation

| tool | category | source | what to export |
|---|---|---|---|
| Make | **Automation** | `export then files` | Scenario blueprints (JSON) and execution logs. |
| Zapier | **Automation** | `export then files` | Zap definitions and task history as JSON or CSV. |

## Other

| tool | category | source | what to export |
|---|---|---|---|
| 123 Formbuilder | **Other** | `export then files` | Form submissions as CSV. |
| Fathom | **Other** | `export then files` | Meeting transcripts and summaries. |
| Fireflies | **Other** | `export then files` | Transcripts exported as text, JSON or DOCX. |
| Google Calendar | **Other** | `export then files` | Calendars exported as .ics (Takeout). |
| Hubstaff | **Other** | `export then files` | Time and activity reports as CSV. |
| Instagram | **Other** | `export then files` | Account data download (JSON). |
| LinkedIn | **Other** | `export then files` | 'Get a copy of your data' archive (CSV). |
| Linnworks | **Other** | `export then files` | Orders and stock levels as CSV. |
| Nooks | **Other** | `export then files` | Call logs and transcripts as CSV. |
| Otter | **Other** | `export then files` | Transcripts exported as text or DOCX. |
| Read AI | **Other** | `export then files` | Meeting transcripts and reports. |
| Session transcripts | **Other** | `files` | The folder holding the transcript files. |
| ShipStation | **Other** | `export then files` | Orders and shipments as CSV. |
| SkuVault | **Other** | `export then files` | Inventory and sales reports as CSV. |
| Twilio | **Other** | `export then files` | Message and call logs exported as CSV or through BulkExport. |
| Webflow | **Other** | `export then files` | CMS collections and form submissions as CSV. |
| Zadarma | **Other** | `export then files` | Call statistics as CSV. |
| Zoom | **Other** | `export then files` | Cloud recording transcripts (VTT) and meeting reports as CSV. |
