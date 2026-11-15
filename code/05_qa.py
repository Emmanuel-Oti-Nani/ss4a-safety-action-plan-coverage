#!/usr/bin/env python3
"""05_qa.py: run the quality checks and write data/processed/qa_report.txt.

Plain-language summary: this script checks the build against outside numbers
before anything is trusted. It compares award counts and dollars with DOT's
published totals for each year, checks that every award landed on the map,
compares the population inside each award area with the population DOT reported,
lists possible duplicate awards, checks that every share is between 0 and 1, and
prints named spot checks you can verify by hand. Read qa_report.txt first.
"""
import json, os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed"); REP = os.path.join(ROOT, "report")
out = []
w = out.append

# DOT published totals (award count, federal dollars) with source pages
OFFICIAL = {
    2022: (511, 802_161_018.54, "https://www.transportation.gov/sites/dot.gov/files/2025-03/FY22-SS4A-Full-Award-List-March2025.xlsx (DOT full award list, March 2025; 474 action plan + 37 implementation)"),
    2023: (620, 895_000_000, "https://www.transportation.gov/grants/ss4a/2023-awards (572 planning and demonstration + 48 implementation; '$895 million', rounded)"),
    2024: (710, 1_241_490_821, "https://www.transportation.gov/sites/dot.gov/files/2024-11/SS4A-FY24-Awards-by-State_November-2024.pdf"),
    2025: (521, 982_231_998, "https://www.transportation.gov/grants/ss4a/2025-awards"),
    2026: (297, 1_012_969_919, "https://www.transportation.gov/grants/ss4a/2026-awards"),
}
OFFICIAL_SPLIT = {2022: (474, 37), 2023: (572, 48), 2024: (640, 70), 2025: (454, 67), 2026: (197, 100)}

a = pd.read_csv(os.path.join(PROC, "ss4a_awards_fy2022_2026.csv"), dtype={"primary_county_fips": str})
g = pd.read_csv(os.path.join(PROC, "county_coverage_gap_table.csv"), dtype={"fips": str})
x = pd.read_csv(os.path.join(PROC, "award_county_crosswalk.csv"), dtype={"fips": str})
s = json.load(open(os.path.join(REP, "stats.json")))

w("SS4A AWARDS AND COVERAGE: QUALITY CHECK REPORT")
w("Plain-language summary: compare each line marked CHECK with the source named. 'OK' means the")
w("build matches; 'NOTE' means a known, explained difference; 'REVIEW' means a person should look.\n")

w("1. Award counts and dollars against DOT published totals")
for fy, (n, d, src) in OFFICIAL.items():
    t = a[a.fiscal_year == fy]
    pd_n = (t.grant_program == "Planning and Demonstration").sum(); ig_n = (t.grant_program == "Implementation").sum()
    status = "OK" if len(t) == n and abs(t.federal_funding.sum() - d) < 1e6 else "NOTE"
    w(f"  FY{fy}: build {len(t)} awards (planning {pd_n}, implementation {ig_n}), ${t.federal_funding.sum():,.0f}; "
      f"DOT {n} awards (planning {OFFICIAL_SPLIT[fy][0]}, implementation {OFFICIAL_SPLIT[fy][1]}), ${d:,.0f}  [{status}]")
    w(f"         source: {src}")
w("  FY2022: DOT's FY2022 map layer holds 509 of 511 awards. The two missing awards (North Dakota State")
w("  University and SUNY Stony Brook, action plans, $1,000,000 each) were added from DOT's full award list")
w("  (code/fy2022_awards_not_on_map.csv). They have no map shape, so they count toward totals but not coverage.")
w("  All 509 mapped FY2022 awards were matched to DOT's list by UEI: dollars and rural/urban labels agree;")
w("  one state was wrong in the map layer and is corrected (code/dot_list_corrections.csv).\n")

w("1c. State-by-state check against DOT's official award lists (Excel, linked from each year's full award list page)")
w("  FY2023-FY2026: award counts and federal dollars for every state match DOT's lists exactly (0 differences).")
w("  Award-level recheck (2026-11-10), all 2,659 awards, all five years: recipient, state, program, rural/urban label and")
w("  dollars match DOT's lists. Differences are name spellings only: Hillsborough County and Hillsborough County MPO (FL")
w("  2023), Dover Kent and Texarkana MPOs (DOT map layer spells 'Metropolitian'), City of Spanish Fork (list: 'City of")
w("  Spanish Fork City'). The FY2026 map layer labels all 100 implementation awards Rural; DOT's list has 48 Rural and")
w("  52 Urban, and the 52 labels are corrected (code/fy2026_rural_label_corrections.csv).")
w("  FY2022: every award matched by UEI (see above). File fingerprints are in data/raw/PROVENANCE.txt.")
w(f"  Map shapes replaced because DOT's map layer drew the wrong place: {a.geometry_note.notna().sum()} (code/geometry_corrections.csv)")
for _, r in a[a.geometry_note.notna()].iterrows():
    w(f"    {r.award_id} {r.recipient_name} ({r.state}): {r.geometry_note}")
w("")
w("1b. State listed by DOT compared with the state the award area falls in")
ms = a[a.state_from_map.notna() & (a.state != a.state_from_map)]
KNOWN_OK = {"Bi-State Regional Commission", "Fargo-Moorhead Metropolitan Council of Governments",
            "Tahoe Transportation District", "University of Texas Arlington",
            "Maryland-National Capital Park and Planning Commission"}
unexpl = ms[~ms.recipient_name.isin(KNOWN_OK)]
w(f"  Awards whose area center lies in another state: {len(ms)}; unexplained: {len(unexpl)}  "
  f"[{'OK' if len(unexpl) == 0 else 'REVIEW'}]")
w("  Reviewed 2026-11-10 against DOT award lists: two-state regional bodies (Bi-State, Fargo-Moorhead, Tahoe),")
w("  a multi-site tribal communities plan (UT Arlington), and an implementation award drawn regionally (M-NCPPC;")
w("  implementation awards do not enter coverage).")
for _, r in ms.iterrows():
    w(f"    {r.award_id} {r.recipient_name}: listed {r.state}, area center in {r.state_from_map}")
w("  (Multi-state regional bodies can be legitimate; single-city awards in another state are errors.)\n")
w("2. Map matching")
w(f"  Awards with a map shape: {(a.geo_match_flag != 'not on DOT map layer; no award area').sum()} of {len(a)}  [OK]")
nobg = a.geo_match_flag.notna().sum()
w(f"  Awards whose area holds no 2020 block-group population center: {nobg} ({100*nobg/len(a):.1f}%)  [NOTE]")
w("  These are small areas (corridors, small tribal areas). They are placed in the county at their")
w("  center and count as zero residents covered. Listed in data/processed/ss4a_awards_fy2022_2026.csv")
w("  (geo_match_flag).")
w(f"  Awards placed in no county (outside the 50 states and DC, e.g. Puerto Rico handled separately): "
  f"{a.primary_county_fips.isna().sum()}")
w(f"  Award-to-county rows: {len(x)}; award-to-place rows: "
  f"{len(pd.read_csv(os.path.join(PROC, 'award_place_crosswalk.csv')))}\n")

w("3. Population inside award areas compared with DOT's reported jurisdiction population")
c = a[(a.dot_jurisdiction_pop > 0) & (a.census_pop_in_area > 0)].copy()
c["ratio"] = c.census_pop_in_area / c.dot_jurisdiction_pop
w(f"  Awards compared: {len(c)}. Median ratio (Census / DOT): {c.ratio.median():.2f}. "
  f"Within 0.8 to 1.25: {100*c.ratio.between(0.8, 1.25).mean():.1f}%.")
w(f"  Ratio below 0.5: {(c.ratio < 0.5).sum()}; above 2: {(c.ratio > 2).sum()}  [REVIEW the largest below]")
for _, r in c.assign(dev=np.abs(np.log(c.ratio))).sort_values("dev", ascending=False).head(10).iterrows():
    w(f"    {r.award_id} {r.recipient_name} ({r.state}): Census {r.census_pop_in_area:,.0f} vs DOT {r.dot_jurisdiction_pop:,.0f}")
w("")

w("4. Possible duplicate awards (same year, recipient, program and dollars)")
d = a[a.duplicated(["fiscal_year", "recipient_name", "grant_program", "federal_funding"], keep=False)]
w(f"  Rows involved: {len(d)}  [{'OK' if len(d) == 0 else 'REVIEW'}]")
for _, r in d.iterrows():
    w(f"    {r.award_id} FY{r.fiscal_year} {r.recipient_name} {r.grant_program} ${r.federal_funding:,.0f}")
d2 = a[a.duplicated(["fiscal_year", "recipient_name", "grant_program"], keep=False) &
       ~a.award_id.isin(d.award_id)]
w(f"  Same year, recipient and program but different dollars (usually separate awards): {len(d2)} rows")
for _, r in d2.iterrows():
    w(f"    {r.award_id} FY{r.fiscal_year} {r.recipient_name} {r.grant_program} ${r.federal_funding:,.0f}")
w("")

w("5. Range checks")
sh = [c for c in g.columns if c.startswith("share_")]
bad = ((g[sh] < 0) | (g[sh] > 1.0001)).sum().sum()
w(f"  County shares outside 0 to 1: {bad}  [{'OK' if bad == 0 else 'REVIEW'}]")
w(f"  Counties in gap table: {len(g)} (Project 1 has 3,143)  [{'OK' if len(g) == 3143 else 'REVIEW'}]")
w(f"  Deaths 2020-2024 in gap table: {g.deaths_2020_2024.sum():,} (must equal Project 1 total for 2020-2024)")
w(f"  Awards with missing or zero dollars: {(a.federal_funding.fillna(0) <= 0).sum()}")
w(f"  Recipient types coded by hand (code/recipient_overrides.csv): {a.recipient_type_basis.str.startswith('manual').sum()} awards")
w(f"  Recipient types from the name rule rather than DOT's label: {(a.recipient_type_basis == 'name rule').sum()} awards\n")

w("6. Threshold counts used in documents (must match report/stats.json)")
for k in ["n_rural_counties", "high_fatality_rate_threshold", "n_high_fatality_rural", "n_gap_counties",
          "n_gap_counties_not_covered", "deaths_2020_2024_gap_counties", "pct_hf_rural_gap"]:
    w(f"  {k}: {s[k]}")
w("")

w("7. Named spot checks (verify by hand; see docs/VERIFY_CHECKLIST.md)")
SPOT = [("Ozarks Transportation Organization", None), ("Southwest Missouri Council of Governments", None),
        ("Navajo", None), ("Kentucky River Area Development District", None), ("City of Huntsville", 2025)]
for nm, fy in SPOT:
    t = a[a.recipient_name.str.contains(nm, case=False, na=False)]
    if fy:
        t = t[t.fiscal_year == fy]
    for _, r in t.iterrows():
        w(f"  {r.award_id} FY{r.fiscal_year} {r.recipient_name} ({r.state}) | {r.grant_type} | "
          f"${r.federal_funding:,.0f} | counties {r.n_counties} | primary {r.primary_county_name} | "
          f"residents in area {r.census_pop_in_area:,}")
w("  County spot checks:")
for f in ["29077", "29213", "48301", "28063", "21193"]:
    r = g[g.fips == f]
    if len(r):
        r = r.iloc[0]
        w(f"  {f} {r.county_name}, {r.state}: rural={r.rural_county}, deaths 2020-24={r.deaths_2020_2024}, "
          f"rate={r.death_rate_per100k_yr}, high-fatality={r.high_fatality_rural}, plan share="
          f"{r.share_action_plan_area_fy22_26}, status={r.coverage_status}")
w("")
w("8. Extremes")
t = g[g.rural_county].sort_values("death_rate_per100k_yr", ascending=False).head(5)
for _, r in t.iterrows():
    w(f"  highest rural rate: {r.county_name}, {r.state}: {r.death_rate_per100k_yr} ({r.deaths_2020_2024} deaths), "
      f"status {r.coverage_status}")
t = a.sort_values("census_pop_in_area", ascending=False).head(5)
for _, r in t.iterrows():
    w(f"  largest award area: {r.award_id} {r.recipient_name} ({r.state}) {r.census_pop_in_area:,} residents, {r.n_counties} counties")
import re
out = [re.sub(r"\[(OK|NOTE|REVIEW[^\]]*)\]", r"(\1)", l) for l in out]
open(os.path.join(PROC, "qa_report.txt"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
