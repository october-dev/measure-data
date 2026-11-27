"""Studio file detectors shared by measure-data (`files` source) and measure-disk (vendored copy).

Counts game-studio evidence from file and folder names, plus, when a peek function is given, the header line of
`.csv` files (string tables). Nothing that matched is kept: callers get counts only.

Categories (SPEC section 7): build and CI logs, crash dumps, profiling captures, QA and certification documents,
audio middleware, localisation, engine content, and Perforce / Plastic / SVN / git metadata.
Python 3.9+ standard library only. Keep measure-disk's copy identical (scripts/vendor_tools.py copies it).
"""
from __future__ import annotations

import re
from collections import Counter

PROFILING_EXTS = {".utrace": "unreal_insights", ".pix": "pix", ".wpix": "pix", ".rdc": "renderdoc", ".tracy": "tracy",
                  ".svt": "superluminal", ".nvreport": "nsight", ".ncu-rep": "nsight", ".etl": "windows_etw"}
CRASH_DUMP_EXTS = {".dmp", ".mdmp", ".hdmp", ".core"}
CRASH_REPORT_EXTS = {".crash", ".ips", ".ucrash", ".runtime-xml"}
CRASH_EXPORT_RX = re.compile(r"(sentry|crashlytics|backtrace|bugsplat|crash[ _-]?report|crashes)", re.I)
LOC_EXTS = {".po": "gettext", ".pot": "gettext", ".mo": "gettext", ".xliff": "xliff", ".xlf": "xliff", ".ink": "ink",
            ".yarn": "yarn", ".strings": "apple_strings", ".stringsdict": "apple_strings", ".resx": "resx",
            ".locres": "unreal_locres", ".archive": "unreal_loc_archive", ".manifest": None}
ENGINE_EXTS = (".uasset", ".umap", ".unity", ".prefab", ".tscn")
DOC_EXTS = {".doc", ".docx", ".odt", ".rtf", ".pdf", ".md", ".txt", ".xls", ".xlsx", ".xlsm", ".ods", ".csv", ".pages",
            ".numbers", ".ppt", ".pptx", ".key", ".gdoc", ".gsheet"}
QA_RX = re.compile(r"(test[ _-]?plans?|test[ _-]?cases?|test[ _-]?runs?|qa[ _-]?(report|pass|sign[ _-]?off|checklist)|"
                   r"bug[ _-]?reports?|playtest|compat(ibility)?[ _-]?report|certification|cert[ _-]?(report|pass|checklist)|"
                   r"(^|[^a-z])trc([^a-z]|$)|(^|[^a-z])xr[ _-]?\d*([^a-z]|$)|lotcheck|submission[ _-]?checklist|"
                   r"(^|[^a-z])(fqa|lqa)([^a-z]|$))", re.I)
CERT_RX = re.compile(r"((^|[^a-z])trc([^a-z]|$)|(^|[^a-z])xr[ _-]?\d*([^a-z]|$)|lotcheck|certification)", re.I)
BUILD_LOG_RX = re.compile(r"(build|jenkins|teamcity|buildkite|horde|ugs|uat|cook|package|ci)[^/]*\.(log|txt)$", re.I)
CI_CONFIG_NAMES = {"jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml", ".travis.yml",
                   "buildkite.yml", "teamcity-settings.kts", "unity-cloud-build.json", "codemagic.yaml", "appveyor.yml"}
HORDE_RX = re.compile(r"(unrealgamesync|^ugs[ _.-]|horde)", re.I)
SECRET_RX = re.compile(r"(^\.env(\..+)?$|\.pem$|\.p12$|\.pfx$|\.keystore$|\.jks$|^id_(rsa|ed25519|ecdsa|dsa)$|\.kdbx$|"
                       r"\.1pux$|^credentials(\.json)?$|service[-_]?account.*\.json$|\.mobileprovision$)", re.I)
LOCALE_RX = re.compile(r"^(en|fr|de|es|it|pt|ru|ja|ko|zh|pl|tr|nl|sv|ar|th|vi|id|cs|hu|uk|da|fi|no|nb|el|he|ro)"
                       r"([-_][A-Za-z]{2,4})?$", re.I)
LOC_KEY_COLS = {"key", "id", "string id", "string_id", "stringid", "text id", "loc key", "lockey", "source"}


def is_string_table(header: list) -> bool:
    """A CSV header that names two or more locales (en, fr-FR, ja ...), or a key column plus one locale."""
    cols = [c.strip().strip('"').strip() for c in header]
    locales = sum(1 for c in cols if LOCALE_RX.match(c) and c.lower() not in LOC_KEY_COLS)
    keys = sum(1 for c in cols if c.lower() in LOC_KEY_COLS)
    return locales >= 2 or (locales >= 1 and keys >= 1)


def ext_of(name: str) -> str:
    i = name.rfind(".")
    return name[i:].lower() if i > 0 else ""


class StudioCounter:
    """Feed folders and files during a walk; `result()` returns counts only."""

    def __init__(self):
        self.c = Counter()
        self.profiling = Counter()
        self.loc = Counter()
        self.engine = Counter({e: 0 for e in ENGINE_EXTS})
        self.cert_docs = 0

    def folder(self, dirname: str, entry_names) -> None:
        names = set(entry_names)
        low = {n.lower() for n in names}
        if ".svn" in names:
            self.c["svn_working_copies"] += 1
        if ".plastic" in names or "plastic.workspace" in low:
            self.c["plastic_workspaces"] += 1
        if ".p4config" in low or "p4config.txt" in low or ".p4ignore" in low:
            self.c["perforce_workspaces"] += 1
        if ".git" in names:
            self.c["git_repos"] += 1
        if "config.xml" in names and "jobs" in names:
            self.c["jenkins_homes"] += 1
        if HORDE_RX.search(dirname):
            self.c["horde_ugs"] += 1
        if dirname == ".teamcity":
            self.c["ci_configs"] += 1

    def file(self, name: str, peek=None) -> None:
        """`peek` is an optional callable returning the first line of the file (only called for .csv)."""
        low = name.lower()
        e = ext_of(low)
        if e in PROFILING_EXTS:
            self.profiling[PROFILING_EXTS[e]] += 1
        elif e == ".data" and "profil" in low:
            self.profiling["unity_profiler"] += 1
        elif e == ".snap" and "memory" in low:
            self.profiling["unity_memory_profiler"] += 1
        if e in CRASH_DUMP_EXTS:
            self.c["dumps"] += 1
        elif e in CRASH_REPORT_EXTS or low.startswith("crashcontext"):
            self.c["crash_reports"] += 1
        elif e in (".csv", ".json", ".jsonl") and CRASH_EXPORT_RX.search(low):
            self.c["crash_exports"] += 1
        if e == ".log" and BUILD_LOG_RX.search(low):
            self.c["build_logs"] += 1
        if low in CI_CONFIG_NAMES:
            self.c["ci_configs"] += 1
        if HORDE_RX.search(low) and e in (".ini", ".json", ".log", ".exe", ".dll"):
            self.c["horde_ugs"] += 1
        if e in DOC_EXTS and QA_RX.search(low):
            self.c["qa_cert_docs"] += 1
            if CERT_RX.search(low):
                self.cert_docs += 1
        if e == ".wproj":
            self.c["wwise_projects"] += 1
        elif e == ".fspro":
            self.c["fmod_projects"] += 1
        elif e in (".bnk", ".bank"):
            self.c["sound_banks"] += 1
        fmt = LOC_EXTS.get(e)
        if fmt and not (e == ".archive" and "loc" not in low):
            self.loc[fmt] += 1
        elif "articy" in low and e in (".json", ".xml", ".adpr", ".articyue"):
            self.loc["articy"] += 1
        elif e == ".csv" and peek is not None:
            try:
                head = peek()
            except Exception:  # noqa: BLE001 - a header we cannot read is simply not a string table
                head = None
            if head and is_string_table(head.split(",")):
                self.c["string_tables_by_header"] += 1
        if e in self.engine:
            self.engine[e] += 1
        if SECRET_RX.search(low):
            self.c["secret_like_files"] += 1
        if e == ".unitypackage":
            self.c["asset_store_packages"] += 1

    def result(self) -> dict:
        c = self.c
        return {
            "build_ci": {"build_logs": c["build_logs"], "ci_configs": c["ci_configs"], "jenkins_homes": c["jenkins_homes"],
                         "horde_ugs": c["horde_ugs"]},
            "crash_dumps": {"dumps": c["dumps"], "crash_reports": c["crash_reports"], "crash_exports": c["crash_exports"]},
            "profiling": {"captures": sum(self.profiling.values()), "by_format": dict(sorted(self.profiling.items()))},
            "qa_cert_docs": c["qa_cert_docs"],
            "certification_docs": self.cert_docs,
            "audio_middleware": {"wwise_projects": c["wwise_projects"], "fmod_projects": c["fmod_projects"],
                                 "sound_banks": c["sound_banks"]},
            "localisation": {"files": sum(self.loc.values()) + c["string_tables_by_header"],
                             "by_format": dict(sorted(self.loc.items())),
                             "string_tables_by_header": c["string_tables_by_header"]},
            "engine_content": dict(self.engine),
            "vcs": {"perforce_workspaces": c["perforce_workspaces"], "svn_working_copies": c["svn_working_copies"],
                    "plastic_workspaces": c["plastic_workspaces"], "git_repos": c["git_repos"]},
            "secret_like_files": c["secret_like_files"],
            "asset_store_packages": c["asset_store_packages"],
        }


# category key -> how a StudioCounter result shows that the category exists in the scanned files
def categories_found(r: dict) -> dict:
    """{category_key: evidence count} for the studio categories these counts touch."""
    v = r["vcs"]
    out = {
        "source_control": v["perforce_workspaces"] + v["svn_working_copies"] + v["plastic_workspaces"] + v["git_repos"],
        "builds_ci": sum(r["build_ci"].values()),
        "crash_reports": sum(r["crash_dumps"].values()),
        "profiling": r["profiling"]["captures"],
        "qa_playtest": r["qa_cert_docs"],
        "audio": sum(r["audio_middleware"].values()),
        "narrative_localisation": r["localisation"]["files"],
        "engine_content": sum(r["engine_content"].values()),
    }
    return {k: n for k, n in out.items() if n}
