# New data source: MiEnviro nSITE (September 2024 forward)

The legacy EGLE database at `egle.state.mi.us/aps/downloads/SRN/` stopped
receiving new documents in September 2024. As of that date, EGLE publishes
all new Air Quality Division documents exclusively through the
**MiEnviro nSITE portal** at `mienviro.michigan.gov`.

> The legacy site still serves documents uploaded before September 2024 and is
> unchanged. This scraper now pulls new documents from nSITE and appends them
> to the existing dataset.

---

## What is nSITE?

nSITE (the MiEnviro Map Explorer) is Michigan EGLE's cross-program document
and permit portal. For air quality purposes it is the successor to the legacy
`/aps/downloads/SRN/` directory. The new portal covers the same facilities and
document types, and in many cases has deeper history than the legacy site.

Facility URLs follow this pattern:

```
https://mienviro.michigan.gov/nsite/DEFAULT/map/results/detail/<site_id>/Documents
```

---

## How the scraper works now

### One-time setup: build the facility ID mapping

nSITE identifies each facility with an 18-digit numeric ID rather than the SRN
used by the legacy site. A helper script builds the lookup table by querying
nSITE's public map API:

```bash
pip install requests pandas tqdm pytz
python build_nsite_mapping.py
```

This tiles Michigan geographically, collects all AQD Air Facilities, and writes
`nsite_id_mapping.csv` — a CSV of `srn, nsite_id, facility_name`. A pre-built
copy is included in this repo and covers **94% of the source list**. Re-run the
script periodically to pick up newly registered facilities.

### Daily run

No changes to how you trigger the scraper. It still runs via GitHub Actions,
still reads `CMS-Subject-Sources-Simple.csv` as the facility list, and still
writes the same output files.

Internally it now:
1. Loads `nsite_id_mapping.csv` to translate SRNs to nSITE IDs.
2. Establishes an anonymous session with nSITE (no account required).
3. Fetches documents for each mapped facility.
4. Appends any document whose `docMgmtDocRvcdCreatedDate` matches today and
   whose ID has not been seen before.

---

## Output files

All four output files are preserved. Two columns were added and `doc_url` now
points to the nSITE download endpoint:

| Column | Change |
|--------|--------|
| `doc_url` | Now `mienviro.michigan.gov/ncore/downloadpdf/{id}` |
| `nsite_doc_id` | **New.** Internal document ID; used for deduplication |
| `nsite_category` | **New.** e.g. "Air Enforcement Documents" |
| `nsite_prog_area` | **New.** e.g. "AQD - Air" |
| `nsite_func_area` | **New.** e.g. "Compliance Action", "Evaluation" |

All other columns (`srn`, `facility_name`, `doc_type`, `date`, `county`, etc.)
are unchanged. Historical rows from the legacy scraper remain in the dataset
with their original URLs.

---

## Verifying a document URL

Legacy URL (still works for pre-Sept-2024 docs):
```
https://www.egle.state.mi.us/aps/downloads/SRN/N2688/N2688_VN_20230601.pdf
```

New URL format:
```
https://mienviro.michigan.gov/ncore/downloadpdf/-9155099477098116838
```

To view a facility's full document list on nSITE, find its `nsite_id` in
`nsite_id_mapping.csv` and open:
```
https://mienviro.michigan.gov/nsite/DEFAULT/map/results/detail/<nsite_id>/Documents
```
