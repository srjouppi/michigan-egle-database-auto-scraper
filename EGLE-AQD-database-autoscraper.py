#!/usr/bin/env python
# coding: utf-8

# ### Imports

import re
import time
import urllib.parse

import requests
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from pytz import timezone


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NSITE_BASE     = "https://mienviro.michigan.gov"
SETTINGS_URL   = f"{NSITE_BASE}/nsite/api/settings/getWslSettings"
DOCS_ENDPOINT  = (
    f"{NSITE_BASE}/nsite/ss/api/nsite-explorer/default-mode"
    "/profiles/4-documents/1-documents"
)
DOWNLOAD_BASE  = f"{NSITE_BASE}/ncore/downloadpdf"

# Map nSITE description → legacy doc_type code (best-effort; unmapped get a sanitised code)
DESC_TO_CODE = {
    "Staff Activity Report":                 "SAR",
    "Full Compliance Evaluation":            "FCE",
    "Stack Test":                            "TEST",
    "Stack Test Report":                     "TEST",
    "Violation Notice":                      "VN",
    "Response to Violation Notice":          "RVN",
    "Administrative Consent Order":          "ACO",
    "Enforcement Notice":                    "ENFN",
    "Stipulated Fines":                      "STIP",
    "Consent Judgment":                      "CJ",
    "Asbestos Violation Notice":             "ASBVN",
    "Response to Asbestos Violation Notice": "RASBVN",
    "Administrative Fine Order":             "AFO",
    "Civil Judgment":                        "CD",
    "Compliance Determination":              "CD",
}


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def make_session():
    """Return a requests.Session with a valid nSITE cookie."""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; EGLE-AQD-scraper/2.0)"})
    s.get(SETTINGS_URL, timeout=30)
    return s


def fetch_site_documents(session, nsite_id):
    """
    Return a list of raw document dicts from nSITE for a single site ID.
    Raises on HTTP error; returns [] if the site has no documents.
    """
    query_params = urllib.parse.quote(
        '{"filter":[{"id":"' + str(nsite_id) + '"}]}'
    )
    url = (
        f"{DOCS_ENDPOINT}"
        f"?responseContentType=application/json"
        f"&includeMetadataInResponse=true"
        f"&loadChildren=true"
        f"&queryParams={query_params}"
        f"&filterString="
    )
    referer = (
        f"{NSITE_BASE}/nsite/DEFAULT/map/results/detail/{nsite_id}/Documents"
    )

    for attempt in range(3):
        try:
            r = session.get(
                url,
                headers={"Referer": referer, "Accept": "application/json"},
                timeout=30,
            )
            data = r.json()
            return data.get("queryResults", [])
        except Exception:
            if attempt == 2:
                return []
            time.sleep(2 ** attempt)


def parse_doc_url(html_anchor):
    """Extract href from '<a href="URL">Download</a>' string."""
    m = re.search(r'href="([^"]+)"', html_anchor or "")
    return m.group(1) if m else html_anchor


def doc_to_row(raw_doc, srn, row_meta):
    """
    Convert a raw nSITE document dict to the output schema.
    row_meta is a Series from the source-list CSV for this SRN.
    """
    descr   = raw_doc.get("docMgmtDocDescr", "")
    srctype = raw_doc.get("docMgmtSourcetype", descr)
    date_str = raw_doc.get("docMgmtDocRvcdCreatedDate", "")

    # Derive the legacy doc_type code; fall back to a sanitised acronym
    doc_type = DESC_TO_CODE.get(descr) or DESC_TO_CODE.get(srctype)
    if not doc_type:
        doc_type = re.sub(r"[^A-Z0-9]", "", (descr or srctype).upper())[:8] or "UNK"

    try:
        date = pd.to_datetime(date_str).tz_localize(None).normalize()
    except Exception:
        date = pd.NaT

    doc_id  = raw_doc.get("docMgmtDocMgmtId", "")
    doc_url = parse_doc_url(raw_doc.get("docMgmtDocurl", "")) or f"{DOWNLOAD_BASE}/{doc_id}"

    return {
        "date":            date,
        "year":            date.year if pd.notna(date) else None,
        "facility_name":   row_meta.get("facility_name", ""),
        "doc_type":        doc_type,
        "type_name":       descr or srctype,
        "doc_url":         doc_url,
        "nsite_doc_id":    doc_id,
        "srn":             srn,
        "epa_class":       row_meta.get("epa_class", ""),
        "address_line1":   row_meta.get("address_line1", ""),
        "city":            row_meta.get("city", ""),
        "zip":             row_meta.get("zip", ""),
        "county":          row_meta.get("county", ""),
        "egle_district":   row_meta.get("egle_district", ""),
        "staff":           row_meta.get("staff", ""),
        "address_full":    row_meta.get("address_full", ""),
        # extra nSITE fields (useful for filtering / enrichment)
        "nsite_category":  raw_doc.get("docMgmtCategory", ""),
        "nsite_prog_area": raw_doc.get("docMgmtSourceprogramarea", ""),
        "nsite_func_area": raw_doc.get("docMgmtSourcefunctionalarea", ""),
    }


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

tz = timezone("EST")
today = datetime.now(tz)
today_str = today.strftime("%-m/%-d/%Y")
today_pd  = pd.Timestamp(today.date())


# ---------------------------------------------------------------------------
# Load supporting data
# ---------------------------------------------------------------------------

sourceList = pd.read_csv("CMS-Subject-Sources-Simple.csv")

try:
    mapping = pd.read_csv("nsite_id_mapping.csv")
except FileNotFoundError:
    raise SystemExit(
        "nsite_id_mapping.csv not found. "
        "Run build_nsite_mapping.py first to generate it."
    )

# Build SRN → nSITE ID dict (skip rows with no SRN)
srn_to_nsite = (
    mapping.dropna(subset=["srn"])
    .set_index("srn")["nsite_id"]
    .to_dict()
)

# Build SRN → source-list row dict for metadata lookup
srn_meta = sourceList.set_index("srn").to_dict("index")

# ---------------------------------------------------------------------------
# Load existing datasets
# ---------------------------------------------------------------------------

oldDocs    = pd.read_csv("output/EGLE-AQD-document-dataset-full.csv")
oldExtras  = pd.read_csv("output/EGLE-AQD-extra-documents.csv")
oldReport  = pd.read_csv("output/EGLE-AQD-scraper-report.csv")
oldReport.date = pd.to_datetime(oldReport.date)

# Deduplication sets
if "nsite_doc_id" in oldDocs.columns:
    seen_ids = set(oldDocs["nsite_doc_id"].dropna().astype(str))
else:
    seen_ids = set()

# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------

session = make_session()

allNewRows    = []
sourcesUpdated = []
mistakes      = []

srns_in_list = sourceList.srn.to_list()

for srn in tqdm(srns_in_list, desc="Checking facilities"):
    nsite_id = srn_to_nsite.get(srn)
    if not nsite_id:
        continue  # not yet in mapping – run build_nsite_mapping.py to add it

    raw_docs = fetch_site_documents(session, nsite_id)
    if not raw_docs:
        continue

    meta = srn_meta.get(srn, {})
    new_for_site = []

    for raw in raw_docs:
        doc_id = str(raw.get("docMgmtDocMgmtId", ""))
        if not doc_id or doc_id in seen_ids:
            continue

        date_str = raw.get("docMgmtDocRvcdCreatedDate", "")
        try:
            doc_date = pd.to_datetime(date_str).tz_localize(None).normalize()
        except Exception:
            doc_date = pd.NaT

        # Only record documents received today (matching original scraper behaviour)
        if pd.isna(doc_date) or doc_date != today_pd:
            continue

        try:
            row = doc_to_row(raw, srn, meta)
            new_for_site.append(row)
            seen_ids.add(doc_id)
        except Exception as exc:
            mistakes.append({"srn": srn, "doc_id": doc_id, "error": str(exc)})

    if new_for_site:
        allNewRows.extend(new_for_site)
        sourcesUpdated.append(srn)

    time.sleep(0.05)   # be polite to the server

# ---------------------------------------------------------------------------
# Merge document code key (type_simple / type_name_simple)
# ---------------------------------------------------------------------------

if allNewRows:
    newDocs = pd.DataFrame(allNewRows)
    newDocs.date = pd.to_datetime(newDocs.date)
    newDocs["year"] = newDocs.date.dt.year

    key = pd.read_csv("EGLE-AQD-document-code-key.csv")
    newDocs = newDocs.merge(key[["doc_type", "type_simple", "type_name_simple"]],
                            on="doc_type", how="left")

    # Patch column order to match existing dataset
    oldDocs.date = pd.to_datetime(oldDocs.date)
    allDocs = pd.concat([oldDocs, newDocs], axis=0, ignore_index=True)
    allDocs = allDocs.sort_values("date", ascending=False, ignore_index=True)

    allDocs.to_csv("output/EGLE-AQD-document-dataset-full.csv", index=False)

    # 90-day subset
    allDocs["duration"] = (today_pd - allDocs.date).dt.days
    (allDocs.query("duration < 91")
             .drop(columns=["duration"])
             .sort_values("date", ascending=False)
             .to_csv("output/EGLE-AQD-document-dataset-90days.csv", index=False))

    newDocsURLs = newDocs["doc_url"].to_list()
else:
    newDocsURLs = []

# ---------------------------------------------------------------------------
# Scrape report
# ---------------------------------------------------------------------------

docTypes = ["SAR","FCE","TEST","VN","RVN","ACO","ENFN","STIP","CJ",
            "ASBVN","AFO","RASBVN","CD"]

data = {
    "date":            today_pd,
    "sources_updated": len(sourcesUpdated),
    "docs_found":      len(newDocsURLs),
    "extras_found":    0,
    "mistakes_found":  len(mistakes),
    "mistakes":        mistakes if mistakes else None,
}

if newDocsURLs and allNewRows:
    newDocs_ref = pd.DataFrame(allNewRows)
    newDocs_ref = newDocs_ref.merge(
        pd.read_csv("EGLE-AQD-document-code-key.csv")[["doc_type", "type_simple"]],
        on="doc_type", how="left"
    )
    type_counts = newDocs_ref["type_simple"].value_counts().to_dict()
    for dt in docTypes:
        data[dt] = type_counts.get(dt)
else:
    for dt in docTypes:
        data[dt] = None

newReport = pd.concat(
    [oldReport, pd.DataFrame([data])], axis=0, ignore_index=True
).sort_values("date", ascending=False)

newReport.to_csv("output/EGLE-AQD-scraper-report.csv", index=False)
