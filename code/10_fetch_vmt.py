"""Fetch 2024 county vehicle-miles traveled (VMT) from FHWA's HPMS public road inventory.

Plain-language summary: for every state, asks DOT's HPMS map service for the sum of
(average daily traffic x section length) by county, which is daily vehicle-miles traveled
on the road sections that carry a traffic count, and the total road miles. Uses the same
road filter as the Project 1 panel (mainline roads with a functional class). Writes
data/raw/hpms_2024_county_vmt.csv. Local roads often carry no traffic count in HPMS, so
this VMT mainly covers arterials and collectors; the paper reports that limitation.
"""
import csv, json, os, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "hpms_2024_county_vmt.csv")
BASE = "https://geo.dot.gov/server/rest/services/Hosted/HPMS_FULL_{st}_2024/FeatureServer/0/query"
STATES = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10",
          "DC": "11", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
          "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
          "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35",
          "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
          "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
          "WV": "54", "WI": "55", "WY": "56"}
WHERE = "f_system IS NOT NULL AND (facility_type IN (1,2) OR (f_system = 7 AND facility_type IS NULL))"
STATS = json.dumps([
    {"statisticType": "sum", "onStatisticField": "aadt*sectionlength", "outStatisticFieldName": "dvmt"},
    {"statisticType": "sum", "onStatisticField": "sectionlength", "outStatisticFieldName": "miles"},
])


def get(params, st, tries=5):
    url = BASE.format(st=st) + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                d = json.loads(r.read())
            if "error" in d:
                raise RuntimeError(d["error"])
            return d
        except Exception as e:  # retry with backoff
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


rows = []
for st, sf in STATES.items():
    for scope, where in (("all", WHERE), ("rural", WHERE + " AND urban_id = 99999")):
        d = get({"where": where, "groupByFieldsForStatistics": "county_id", "outStatistics": STATS, "f": "json"}, st)
        for f in d["features"]:
            a = f["attributes"]
            if a["county_id"] is None:
                continue
            rows.append({"state": st, "fips": sf + str(int(a["county_id"])).zfill(3), "scope": scope,
                         "daily_vmt": round(a["dvmt"] or 0, 1), "miles": round(a["miles"] or 0, 3)})
    print(st, len(rows), flush=True)

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["state", "fips", "scope", "daily_vmt", "miles"])
    w.writeheader()
    w.writerows(rows)
print("wrote", OUT, len(rows))
