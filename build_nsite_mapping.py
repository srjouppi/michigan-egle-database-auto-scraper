#!/usr/bin/env python3
"""
One-time script to build the SRN-to-nSITE-ID mapping table.

Run this once (or periodically to pick up newly registered facilities) and commit
the resulting nsite_id_mapping.csv to the repo. The main scraper reads from that file.

Usage:
    python build_nsite_mapping.py

Output:
    nsite_id_mapping.csv  (srn, nsite_id, facility_name)
"""

import re
import time
import json
import requests
import pandas as pd

NSITE_BASE = "https://mienviro.michigan.gov"
SETTINGS_URL = f"{NSITE_BASE}/nsite/api/settings/getWslSettings"
SEARCH_URL   = f"{NSITE_BASE}/nsite/ss/explorersites"

# 0.5-degree tiles covering Michigan's bounding box
MICH_LAT_MIN, MICH_LAT_MAX = 41.5, 48.6
MICH_LON_MIN, MICH_LON_MAX = -90.0, -82.0
TILE_SIZE = 0.5

SRN_PATTERN = re.compile(r'\(([A-Z]\d{4,})\)\s*$')


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; EGLE-scraper/2.0)"})
    s.get(SETTINGS_URL, timeout=30)
    return s


def search_tile(session, lat_min, lat_max, lon_min, lon_max):
    """Return a list of {siteId, siteName} dicts from nSITE within the given bounding box."""
    body = {
        "insertUpdateList": [{
            "displayHeight": 800,
            "displayWidth": 1200,
            "filterValuesJson": json.dumps([
                {"attributeName": "1H_Site Type", "attributeValue": "Air - Air Facility"}
            ]),
            "term": "",
            "modeId": "DEFAULT",
            "latitudeMax": lat_max,
            "latitudeMin": lat_min,
            "longitudeMax": lon_max,
            "longitudeMin": lon_min,
            "zoom": 22,
        }]
    }
    for attempt in range(3):
        try:
            r = session.post(
                SEARCH_URL,
                json=body,
                headers={"Referer": f"{NSITE_BASE}/nsite/DEFAULT/map/results",
                         "Accept": "application/json"},
                timeout=30,
            )
            data = r.json()
            break
        except Exception as exc:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

    total = data.get("totalSiteCount", 0)
    items = data.get("insertUpdateList", [])
    sites = []

    for item in items:
        if item.get("siteId"):
            sites.append({"siteId": item["siteId"], "siteName": item.get("siteName", "")})
        elif item.get("clusterSites"):
            try:
                cluster = json.loads(item["clusterSites"])
                for c in cluster:
                    sites.append({"siteId": c["siteId"], "siteName": c.get("siteName", "")})
            except (json.JSONDecodeError, KeyError):
                pass

    return total, sites


def collect_sites(session, lat_min, lat_max, lon_min, lon_max, depth=0):
    """Recursively tile the bbox until each sub-tile fits in one response."""
    total, sites = search_tile(session, lat_min, lat_max, lon_min, lon_max)

    # If total fits in what we got, we're done
    if total <= len(sites) or depth >= 4:
        return sites

    # Subdivide into quadrants
    lat_mid = (lat_min + lat_max) / 2
    lon_mid = (lon_min + lon_max) / 2

    result = []
    for (la, lb) in [(lat_min, lat_mid), (lat_mid, lat_max)]:
        for (lo, lob) in [(lon_min, lon_mid), (lon_mid, lon_max)]:
            result.extend(collect_sites(session, la, lb, lo, lob, depth + 1))
            time.sleep(0.1)
    return result


def extract_srn(site_name):
    """Extract SRN from 'Facility Name (N2688)' style name. Returns None if not found."""
    m = SRN_PATTERN.search(site_name)
    return m.group(1) if m else None


def main():
    print("Establishing nSITE session...")
    session = make_session()

    all_sites = {}  # siteId -> {siteName, srn}

    lat = MICH_LAT_MIN
    tile_count = 0
    while lat < MICH_LAT_MAX:
        lon = MICH_LON_MIN
        while lon < MICH_LON_MAX:
            tile_count += 1
            lat_max = min(lat + TILE_SIZE, MICH_LAT_MAX)
            lon_max = min(lon + TILE_SIZE, MICH_LON_MAX)

            sites = collect_sites(session, lat, lat_max, lon, lon_max)
            for s in sites:
                sid = s["siteId"]
                if sid not in all_sites:
                    all_sites[sid] = s["siteName"]

            print(f"Tile ({lat:.1f},{lon:.1f}): {len(sites)} sites | Total unique: {len(all_sites)}")
            time.sleep(0.15)
            lon += TILE_SIZE
        lat += TILE_SIZE

    print(f"\nScanned {tile_count} tiles, found {len(all_sites)} unique AQD Air Facilities")

    rows = []
    for nsite_id, name in all_sites.items():
        srn = extract_srn(name)
        rows.append({"srn": srn, "nsite_id": nsite_id, "facility_name": name})

    df = pd.DataFrame(rows)
    mapped = df.dropna(subset=["srn"])
    unmapped = df[df.srn.isna()]

    print(f"Sites with SRN in name: {len(mapped)}")
    print(f"Sites without SRN pattern: {len(unmapped)}")

    df.to_csv("nsite_id_mapping.csv", index=False)
    print("Wrote nsite_id_mapping.csv")


if __name__ == "__main__":
    main()
