#!/usr/bin/env python3
"""04_outputs.py: write the final dataset, the coverage gap tables, and stats.json.

Plain-language summary: this script puts the pieces together. It writes
(1) the SS4A awards dataset, one row per award, with or without map shapes;
(2) the county coverage gap table, joining SS4A coverage to the county death
counts from Project 1 (U.S. Rural Road Fatality County Panel); (3) a table of
regional councils and metropolitan planning organizations with funded plans,
showing which counties their plans reach; (4) a state summary; and (5)
report/stats.json, the single file every number in the documents is read from.
You do not need to open this file.

Definitions used (see docs/CODING_RULES.md):
* Rural county: at least 50 percent of 2020 residents live outside Census 2020
  urban areas (pct_rural_2020 >= 50, Project 1).
* Fatality burden: deaths 2020-2024 per 100,000 residents per year (Project 1).
* High-fatality rural county: rural county in the top quarter of that rate among
  rural counties with at least MIN_DEATHS deaths in 2020-2024.
* Covered: at least 50 percent of the county's 2020 residents live inside at
  least one SS4A award area that funds developing or updating an action plan.
"""
import json, os, re
import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw"); INT = os.path.join(ROOT, "data", "interim")
PROC = os.path.join(ROOT, "data", "processed"); REP = os.path.join(ROOT, "report")
P1 = os.path.join(RAW, "project1", "Emmanuel-Oti-Nani-rural-road-fatality-panel-a806351",
                  "data", "processed", "panel_county_year_2015_2024.csv")
RURAL_PCT = 50
MIN_DEATHS = 5
HIGH_Q = 0.75
COVER = 0.5
os.makedirs(os.path.join(REP, "tables"), exist_ok=True)

# ---------- 1. awards dataset ----------
aw = gpd.read_file(os.path.join(INT, "awards.gpkg"))
geo = pd.read_csv(os.path.join(INT, "award_geo_summary.csv"), dtype={"primary_county_fips": str,
                  "primary_place_geoid": str})
aw = aw.merge(geo, on="award_id", how="left")
cols = [c for c in aw.columns if c != "geometry"]
pd.DataFrame(aw[cols]).to_csv(os.path.join(PROC, "ss4a_awards_fy2022_2026.csv"), index=False)
aw.to_file(os.path.join(PROC, "ss4a_awards_fy2022_2026.gpkg"), driver="GPKG", layer="awards")
web = aw[["award_id", "fiscal_year", "recipient_name", "state", "recipient_type", "grant_type",
          "federal_funding", "geometry"]].copy()
web["geometry"] = web.to_crs(5070).geometry.simplify(250).to_crs(4326)
web.to_file(os.path.join(PROC, "ss4a_awards_fy2022_2026_web.geojson"), driver="GeoJSON",
            COORDINATE_PRECISION=4)

# ---------- 2. county burden from Project 1 ----------
p = pd.read_csv(P1, dtype={"fips": str})
p5 = p[p.year.between(2020, 2024)]
b = p5.groupby("fips").agg(state=("state", "first"), county_name=("county_name", "first"),
                           pop2020_census=("pop2020_census", "first"), pct_rural_2020=("pct_rural_2020", "first"),
                           deaths_2020_2024=("deaths", "sum"), deaths_rural_2020_2024=("deaths_rural", "sum"),
                           person_years_2020_2024=("population", "sum"))
b["death_rate_per100k_yr"] = (b.deaths_2020_2024 / b.person_years_2020_2024 * 1e5).round(2)
b["rural_county"] = b.pct_rural_2020 >= RURAL_PCT
elig = b.rural_county & (b.deaths_2020_2024 >= MIN_DEATHS)
thr = float(b.loc[elig, "death_rate_per100k_yr"].quantile(HIGH_Q))
b["high_fatality_rural"] = elig & (b.death_rate_per100k_yr >= thr)
b["rate_rank_among_rural"] = b.loc[elig, "death_rate_per100k_yr"].rank(ascending=False, method="min")

cov = pd.read_csv(os.path.join(INT, "county_coverage.csv"), dtype={"fips": str})
g = b.join(cov.set_index("fips"), how="left")
share = g.share_action_plan_area_fy22_26.fillna(0)
g["coverage_status"] = np.select([share >= COVER, share > 0], ["covered", "partly covered"], "not covered")
s25 = g.share_action_plan_area_fy22_25.fillna(0)
g["coverage_status_fy22_25"] = np.select([s25 >= COVER, s25 > 0], ["covered", "partly covered"], "not covered")
sc = g.share_action_plan_area_conservative_fy22_26.fillna(0)
g["coverage_status_conservative"] = np.select([sc >= COVER, sc > 0], ["covered", "partly covered"], "not covered")
g["covered_any_ss4a_fy22_26"] = g.share_any_ss4a_area_fy22_26.fillna(0) >= COVER

# regional bodies with action plans that reach a neighboring county (where to look for a partner)
cg = gpd.read_file("zip://" + os.path.join(RAW, "cb_2020_us_county_500k.zip"))[["GEOID", "geometry"]]
cg = cg[cg.GEOID.isin(g.index)].to_crs(5070)
nb = gpd.sjoin(cg, cg, predicate="touches")
nb = nb[nb.GEOID_left != nb.GEOID_right][["GEOID_left", "GEOID_right"]]
rbmap = g.regional_body_action_plan_recipients.dropna()
nb = nb[nb.GEOID_right.isin(rbmap.index)]
nb["rb"] = nb.GEOID_right.map(rbmap)
adj = nb.groupby("GEOID_left").rb.apply(lambda s: "; ".join(sorted(set("; ".join(s).split("; ")))))
g["neighbor_regional_body_plans"] = adj
g["gap_flag"] = g.high_fatality_rural & g.coverage_status.ne("covered")
g.index.name = "fips"
keep = ["state", "county_name", "pop2020_census", "pct_rural_2020", "rural_county", "deaths_2020_2024",
        "deaths_rural_2020_2024", "person_years_2020_2024", "death_rate_per100k_yr", "rate_rank_among_rural",
        "high_fatality_rural", "share_action_plan_area_fy22_26", "share_action_plan_area_fy22_25",
        "share_action_plan_area_conservative_fy22_26", "share_any_ss4a_area_fy22_26", "share_regional_body_action_plan_fy22_26", "coverage_status",
        "coverage_status_fy22_25", "coverage_status_conservative", "covered_any_ss4a_fy22_26", "first_fy_action_plan_majority", "gap_flag",
        "n_action_plan_awards_touching", "action_plan_award_ids", "action_plan_recipients",
        "regional_body_action_plan_recipients", "neighbor_regional_body_plans", "n_any_ss4a_awards_touching"]
gt = g[keep].reset_index()
gt["first_fy_action_plan_majority"] = gt.first_fy_action_plan_majority.astype("Int64")
gt["rate_rank_among_rural"] = gt.rate_rank_among_rural.astype("Int64")
for c in ["n_action_plan_awards_touching", "n_any_ss4a_awards_touching"]:
    gt[c] = gt[c].fillna(0).astype(int)
gt.to_csv(os.path.join(PROC, "county_coverage_gap_table.csv"), index=False)
pri = gt[gt.gap_flag].sort_values(["deaths_2020_2024"], ascending=False)
pri.to_csv(os.path.join(REP, "tables", "priority_gap_counties.csv"), index=False)

# ---------- 3. regional body table ----------
attrs = pd.read_csv(os.path.join(PROC, "ss4a_awards_fy2022_2026.csv"), dtype=str)
for c in ["fiscal_year"]:
    attrs[c] = attrs[c].astype(int)
attrs["federal_funding"] = attrs.federal_funding.astype(float)
attrs["includes_action_plan"] = attrs.includes_action_plan.eq("True")
rb = attrs[attrs.is_regional_body.eq("True")].copy()


def norm(n):
    n = n.lower()
    n = re.sub(r"\(.*?\)", "", n)
    n = n.replace("council of governments", "cog").replace("metropolitian", "metropolitan")
    n = re.sub(r"\b(inc|the)\b", "", n)
    return re.sub(r"[^a-z0-9]+", " ", n).strip()


rb["body_key"] = rb.state + "|" + rb.recipient_name.map(norm)
ac = pd.read_csv(os.path.join(PROC, "award_county_crosswalk.csv"), dtype={"fips": str})
rows = []
for key, s in rb.groupby("body_key"):
    apids = s.loc[s.includes_action_plan, "award_id"]
    c = ac[ac.award_id.isin(apids)].groupby("fips").pop_in_award.sum()
    # counties where this body's plan areas hold at least half the residents
    c = c[c.index.isin(g.index)]
    maj = c[(c / g.loc[c.index, "pop2020_census"]).fillna(0) >= COVER].index
    gg = g.loc[maj]
    rows.append({
        "regional_body": s.recipient_name.value_counts().index[0],
        "name_variants": "; ".join(sorted(set(s.recipient_name))),
        "state": s.state.iloc[0],
        "recipient_type": s.recipient_type.value_counts().index[0],
        "fiscal_years": ";".join(map(str, sorted(set(s.fiscal_year)))),
        "award_ids": ";".join(sorted(s.award_id)),
        "n_awards": len(s), "n_action_plan_awards": int(s.includes_action_plan.sum()),
        "federal_funding_total": s.federal_funding.sum(),
        "n_counties_plan_majority": len(maj),
        "n_rural_counties_plan_majority": int(gg.rural_county.sum()),
        "n_high_fatality_rural_counties_plan_majority": int(gg.high_fatality_rural.sum()),
        "deaths_2020_2024_in_plan_majority_counties": int(gg.deaths_2020_2024.sum()),
        "plan_majority_county_fips": ";".join(sorted(maj)),
    })
rbt = pd.DataFrame(rows).sort_values(["state", "regional_body"])
rbt.to_csv(os.path.join(PROC, "regional_body_coverage_table.csv"), index=False)

# ---------- 4. state summary ----------
ru = g[g.rural_county]
st = ru.groupby("state").agg(
    rural_counties=("county_name", "size"),
    rural_counties_covered=("coverage_status", lambda s: (s == "covered").sum()),
    rural_counties_partly=("coverage_status", lambda s: (s == "partly covered").sum()),
    rural_counties_not_covered=("coverage_status", lambda s: (s == "not covered").sum()),
    high_fatality_rural=("high_fatality_rural", "sum"),
    high_fatality_rural_gap=("gap_flag", "sum"),
    deaths_2020_2024_rural_counties=("deaths_2020_2024", "sum"),
)
st["deaths_2020_2024_in_gap_counties"] = g[g.gap_flag].groupby("state").deaths_2020_2024.sum()
st = st.fillna(0).astype(int).reset_index()
st.to_csv(os.path.join(PROC, "state_coverage_summary.csv"), index=False)

# ---------- 5. stats.json ----------
core = attrs[attrs.fiscal_year <= 2025]
hf = g[g.high_fatality_rural]


def pct(a, b_):
    return round(100 * a / b_, 1) if b_ else None


stats = {
    "n_awards_all": int(len(attrs)), "n_awards_core": int(len(core)),
    "dollars_all": float(attrs.federal_funding.sum()), "dollars_core": float(core.federal_funding.sum()),
    "awards_by_fy": {int(k): int(v) for k, v in attrs.groupby("fiscal_year").size().items()},
    "dollars_by_fy": {int(k): float(v) for k, v in attrs.groupby("fiscal_year").federal_funding.sum().items()},
    "n_action_plan_awards_all": int(attrs.includes_action_plan.sum()),
    "n_action_plan_awards_core": int(core.includes_action_plan.sum()),
    "recipient_type_counts": attrs.recipient_type.value_counts().to_dict(),
    "grant_type_counts": attrs.grant_type.value_counts().to_dict(),
    "n_counties": int(len(g)), "n_rural_counties": int(g.rural_county.sum()),
    "rural_pct_threshold": RURAL_PCT, "min_deaths": MIN_DEATHS, "high_quantile": HIGH_Q,
    "high_fatality_rate_threshold": round(thr, 2), "n_high_fatality_rural": int(len(hf)),
    "deaths_2020_2024_all": int(g.deaths_2020_2024.sum()),
    "deaths_2020_2024_rural_counties": int(g.loc[g.rural_county, "deaths_2020_2024"].sum()),
    "deaths_2020_2024_high_fatality_rural": int(hf.deaths_2020_2024.sum()),
    "status_all_counties": g.coverage_status.value_counts().to_dict(),
    "status_rural_counties": g.loc[g.rural_county, "coverage_status"].value_counts().to_dict(),
    "status_urban_counties": g.loc[~g.rural_county, "coverage_status"].value_counts().to_dict(),
    "status_high_fatality_rural": hf.coverage_status.value_counts().to_dict(),
    "status_high_fatality_rural_fy22_25": hf.coverage_status_fy22_25.value_counts().to_dict(),
    "status_high_fatality_rural_conservative": hf.coverage_status_conservative.value_counts().to_dict(),
    "n_gap_counties_conservative": int((g.high_fatality_rural & g.coverage_status_conservative.ne("covered")).sum()),
    "n_gap_counties_fy22_25": int((g.high_fatality_rural & g.coverage_status_fy22_25.ne("covered")).sum()),
    "n_action_plan_awards_area_flag": int((aw.includes_action_plan & aw.area_may_overstate_plan.fillna(False)).sum()),
    "n_gap_counties": int(g.gap_flag.sum()),
    "n_gap_counties_not_covered": int((g.gap_flag & g.coverage_status.eq("not covered")).sum()),
    "deaths_2020_2024_gap_counties": int(g.loc[g.gap_flag, "deaths_2020_2024"].sum()),
    "pct_hf_rural_gap": pct(g.gap_flag.sum(), len(hf)),
    "n_gap_with_neighbor_regional_body": int((g.gap_flag & g.neighbor_regional_body_plans.notna()).sum()),
    "n_gap_covered_by_any_ss4a": int((g.gap_flag & g.covered_any_ss4a_fy22_26).sum()),
    "pop_share_in_action_plan_area_all": pct((g.share_action_plan_area_fy22_26.fillna(0) * g.pop2020_census).sum(),
                                             g.pop2020_census.sum()),
    "pop_share_in_action_plan_area_rural_counties": pct(
        (g.share_action_plan_area_fy22_26.fillna(0) * g.pop2020_census)[g.rural_county].sum(),
        g.loc[g.rural_county, "pop2020_census"].sum()),
    "pop_share_in_action_plan_area_urban_counties": pct(
        (g.share_action_plan_area_fy22_26.fillna(0) * g.pop2020_census)[~g.rural_county].sum(),
        g.loc[~g.rural_county, "pop2020_census"].sum()),
    "rate_rural_counties": round(g.loc[g.rural_county, "deaths_2020_2024"].sum() /
                                 g.loc[g.rural_county, "person_years_2020_2024"].sum() * 1e5, 1),
    "rate_urban_counties": round(g.loc[~g.rural_county, "deaths_2020_2024"].sum() /
                                 g.loc[~g.rural_county, "person_years_2020_2024"].sum() * 1e5, 1),
    "n_regional_bodies": int(len(rbt)),
    "n_regional_bodies_with_action_plan": int((rbt.n_action_plan_awards > 0).sum()),
    "n_rural_counties_majority_via_regional_body": int(
        (g.rural_county & (g.share_regional_body_action_plan_fy22_26.fillna(0) >= COVER)).sum()),
    "states_most_gap_counties": st.sort_values("high_fatality_rural_gap", ascending=False)
                                  .head(5)[["state", "high_fatality_rural_gap"]].values.tolist(),
}
# ---- extra tables for the paper ----
byfy = []
for y, t in attrs.groupby("fiscal_year"):
    byfy.append({"fy": int(y), "n": int(len(t)), "dollars": float(t.federal_funding.sum()),
                 "n_ig": int(t.grant_program.eq("Implementation").sum()),
                 "n_ap": int(t.includes_action_plan.sum()),
                 "n_ap_regional": int((t.includes_action_plan & t.is_regional_body.eq("True")).sum()),
                 "pct_rural_dot": round(100 * t.dot_rural_urban.eq("Rural").mean(), 1)})
stats["by_fy"] = byfy
grp = np.select([g.high_fatality_rural, g.rural_county], ["hf_rural", "other_rural"], "urban")
gm = {}
for gname in ["urban", "other_rural", "hf_rural"]:
    m = grp == gname
    gm[gname] = {"n": int(m.sum()), "deaths": int(g.loc[m, "deaths_2020_2024"].sum()),
                 "rate": round(g.loc[m, "deaths_2020_2024"].sum() / g.loc[m, "person_years_2020_2024"].sum() * 1e5, 1)}
    for meas, col in [("main", "coverage_status"), ("fy22_25", "coverage_status_fy22_25"),
                      ("conservative", "coverage_status_conservative")]:
        gm[gname][meas] = {k: int(v) for k, v in g.loc[m, col].value_counts().items()}
    gm[gname]["any_ss4a_majority"] = int(g.loc[m, "covered_any_ss4a_fy22_26"].sum())
stats["groups"] = gm
stats["n_ap_regional_all"] = int((attrs.includes_action_plan & attrs.is_regional_body.eq("True")).sum())
stats["n_regional_body_counties_hf_rural"] = int((g.high_fatality_rural & (g.share_regional_body_action_plan_fy22_26.fillna(0) >= COVER)).sum())
stats["n_hf_covered_via_regional_body"] = stats["n_regional_body_counties_hf_rural"]
pri10 = g[g.gap_flag].sort_values("deaths_2020_2024", ascending=False).head(10)
stats["priority_top10"] = [{"fips": f, "county": r.county_name, "state": r.state, "deaths": int(r.deaths_2020_2024),
                            "rate": float(r.death_rate_per100k_yr), "status": r.coverage_status,
                            "share": float(r.share_action_plan_area_fy22_26 or 0),
                            "neighbor": (r.neighbor_regional_body_plans if isinstance(r.neighbor_regional_body_plans, str) else "")}
                           for f, r in pri10.iterrows()]
stats["deaths_rural_not_covered"] = int(g.loc[g.rural_county & g.coverage_status.ne("covered"), "deaths_2020_2024"].sum())
stats["n_states_with_gap"] = int((st.high_fatality_rural_gap > 0).sum())
stats["n_gap_not_covered_with_neighbor"] = int((g.gap_flag & g.coverage_status.eq("not covered") & g.neighbor_regional_body_plans.notna()).sum())
json.dump(stats, open(os.path.join(REP, "stats.json"), "w"), indent=1, default=int)
print(json.dumps(stats, indent=1, default=int))
