#!/usr/bin/env python3
"""01_fetch.py: download every raw input and log where it came from.

Plain-language summary: this script saves copies of the U.S. Department of
Transportation (DOT) SS4A award map layers, the Census boundary and population
files, and the Project 1 county fatality panel into data/raw/. Each download is
recorded in data/raw/PROVENANCE.txt with its size, fingerprint (SHA-256), web
address and date. You do not need to open this file; run it once.

SS4A award layers are read from DOT's public ArcGIS Online feature services
(organization xOi1kZaI0eWDREZv), which back the official awards maps at
https://www.transportation.gov/grants/ss4a. Layers were discovered from the
services directory https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services
and from the FY2025 awards map (ArcGIS Experience 492a0b9ec878435f841236c43e08a7d6).
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
LOG = os.path.join(RAW, "PROVENANCE.txt")
BASE = "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services"

# (fiscal year, layer role, service name)
LAYERS = [
    (2022, "planning", "FY22_ActionPlan_FinalAwards"),
    (2022, "implementation", "FY22_IG_FinalAwards"),
    (2022, "crosscheck", "ACTION_PLAN_IMPLEMENTATION_GRANTS_MERGE"),
    (2023, "planning", "FY23_PDG_FinalAwards_ALL"),
    (2023, "implementation", "FY23_IG_FinalAwards"),
    (2024, "planning", "FY24_PDG_FinalAwards_ALL"),
    (2024, "implementation", "FY24_IG_FinalAwards"),
    (2025, "all", "SS4A_FY25_Jurisdiction_Areas_Final_Updated_12_16_2025"),
    (2026, "all", "SS4A_FY26_Jurisdictions_Final"),
]

# Fields never copied into the dataset (personal contact details, internal notes).
DROP = {"Primary_Contact", "Primary_Email", "Alternate_Email",
        "Flags___Internal_Notes", "Match_Check", "Source_Notes"}

CENSUS = [
    ("cb_2020_us_county_500k.zip",
     "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_county_500k.zip"),
    ("cb_2020_us_place_500k.zip",
     "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_place_500k.zip"),
    ("cb_2020_33_cousub_500k.zip",
     "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_33_cousub_500k.zip"),
    ("CenPop2020_Mean_BG.txt",
     "https://www2.census.gov/geo/docs/reference/cenpop2020/blkgrp/CenPop2020_Mean_BG.txt"),
]
PROJECT1 = ("rural-road-fatality-panel-v1.0.0.zip",
            "https://zenodo.org/api/records/23547650/files/Emmanuel-Oti-Nani/rural-road-fatality-panel-v1.0.0.zip/content",
            "Project 1 panel v1.0.0, DOI 10.5281/zenodo.23547650 (concept DOI 10.5281/zenodo.23547649)")


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception as e:  # network hiccup: back off and retry
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def prov(path, url, note=""):
    subprocess.run([sys.executable, os.path.join(ROOT, "code", "provenance.py"), path, url,
                    "--log", LOG, "--note", note], check=True, stdout=subprocess.DEVNULL)


def fetch_layer(fy, role, svc):
    out = os.path.join(RAW, f"ss4a_fy{fy}_{role}_{svc}.geojson")
    if os.path.exists(out):
        return out
    lyr = f"{BASE}/{svc}/FeatureServer/0"
    meta = json.loads(get(lyr + "?f=json"))
    fields = [f["name"] for f in meta["fields"] if f["name"] not in DROP]
    oid = meta.get("objectIdField", "OBJECTID")
    ids = json.loads(get(lyr + "/query?where=1%3D1&returnIdsOnly=true&f=json"))["objectIds"]
    ids.sort()
    feats = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        q = urllib.parse.urlencode({
            "objectIds": ",".join(map(str, chunk)), "outFields": ",".join(fields),
            "outSR": 4326, "geometryPrecision": 6, "maxAllowableOffset": 0.0002,
            "f": "geojson"})
        feats += json.loads(get(lyr + "/query?" + q))["features"]
    fc = {"type": "FeatureCollection", "features": feats,
          "_source": {"service": svc, "layer_url": lyr,
                      "last_edit_ms": meta.get("editingInfo", {}).get("lastEditDate"),
                      "record_count": len(ids)}}
    with open(out, "w") as f:
        json.dump(fc, f)
    prov(out, lyr, f"FY{fy} {role}; {len(feats)} features; geometry simplified to 0.0002 deg (~20 m); "
                   f"contact/internal-note fields dropped; layer last edited (ms) {fc['_source']['last_edit_ms']}")
    print(f"FY{fy} {role:15s} {svc}: {len(feats)} features")
    return out


def main():
    os.makedirs(RAW, exist_ok=True)
    for fy, role, svc in LAYERS:
        fetch_layer(fy, role, svc)
    for name, url in CENSUS:
        p = os.path.join(RAW, name)
        if not os.path.exists(p):
            open(p, "wb").write(get(url)); prov(p, url, "U.S. Census Bureau, 2020 vintage")
            print("saved", name)
    name, url, note = PROJECT1
    p = os.path.join(RAW, name)
    if not os.path.exists(p):
        open(p, "wb").write(get(url)); prov(p, url, note)
        print("saved", name)
    with zipfile.ZipFile(p) as z:
        z.extractall(os.path.join(RAW, "project1"))


if __name__ == "__main__":
    main()
