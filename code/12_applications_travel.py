"""Unfunded applicants and travel-based death rates (added in version 1.1.0).

Plain-language summary:
1. Applications. Joins DOT's lists of eligible but unfunded applicants (FY2022-FY2024) to
   counties, then (a) sorts the gap counties into "applied but not funded" and "no record
   of an application", and (b) compares how often applicants from urban, other rural and
   high-fatality rural counties were funded, using only rounds where DOT published both the
   funded and unfunded lists for that grant type.
2. Travel exposure. Divides 2020-2024 deaths by 2024 vehicle-miles traveled (FHWA HPMS),
   re-identifies the high-fatality rural counties on that basis, and recounts the gaps.

Writes report/analysis_applications_travel.json, data/processed/county_applications_travel.csv and
report/tables/applicant_success_by_group.csv.
"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats as ss

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
R = {}

c = pd.read_csv(P("data", "processed", "county_coverage_gap_table.csv"), dtype={"fips": str})
c["rural"] = c.rural_county.astype(bool)
c["hf"] = c.high_fatality_rural.astype(bool)
c["gap"] = c.gap_flag.astype(bool)
c["covered"] = c.coverage_status.eq("covered")
c["group"] = np.where(~c.rural, "urban", np.where(c.hf, "hf_rural", "other_rural"))

# ---------- 1. Unfunded applicants ----------
xw = pd.read_csv(P("data", "processed", "unfunded_applicant_county_crosswalk.csv"), dtype=str)
xw["pop_share"] = xw.pop_share.astype(float)
xw["regional"] = xw.match_method.str.contains("regional", na=False)
xw["seeks_action_plan"] = xw.seeks_action_plan.eq("True")
placed = xw.dropna(subset=["county_fips"])
per_cty = placed.groupby("county_fips").agg(
    n_unfunded_apps=("app_id", "nunique"),
    n_unfunded_direct=("regional", lambda s: int((~s).sum())),
    unfunded_rounds=("round", lambda s: ";".join(sorted(set(s)))),
    unfunded_applicants=("applicant", lambda s: "; ".join(sorted(set(s)))),
)
per_cty["unfunded_sought_plan"] = placed[placed.seeks_action_plan].groupby("county_fips").app_id.nunique()
per_cty = per_cty.fillna({"unfunded_sought_plan": 0})
c = c.merge(per_cty, left_on="fips", right_index=True, how="left")
for k in ("n_unfunded_apps", "n_unfunded_direct", "unfunded_sought_plan"):
    c[k] = c[k].fillna(0).astype(int)

g = c[c.gap]
R["applicants"] = {
    "n_lists_rows": int(xw.app_id.nunique()),
    "n_placed": int(placed.app_id.nunique()),
    "n_unassigned": int(xw[xw.county_fips.isna()].app_id.nunique()),
    "rows_by_round": xw.drop_duplicates("app_id").groupby("round").size().to_dict(),
    "gap_any_unfunded": int((g.n_unfunded_apps > 0).sum()),
    "gap_direct_unfunded": int((g.n_unfunded_direct > 0).sum()),
    "gap_no_record": int((g.n_unfunded_apps == 0).sum()),
    "gap_no_record_no_award": int(((g.n_unfunded_apps == 0) & (g.share_action_plan_area_fy22_26 == 0)).sum()),
    "gap_n": int(len(g)),
    "gap_with_unfunded_list": g[g.n_unfunded_apps > 0][["fips", "county_name", "state", "unfunded_applicants", "unfunded_rounds", "n_unfunded_direct"]].to_dict("records"),
}
# share of counties in each group touched by any unfunded applicant
R["applicants"]["share_with_unfunded_by_group"] = {k: round(100 * (d.n_unfunded_apps > 0).mean(), 1) for k, d in c.groupby("group")}

# applicant-level funding rates, by the county group of the applicant's main county
aw = pd.read_csv(P("data", "processed", "ss4a_awards_fy2022_2026.csv"), low_memory=False, dtype={"primary_county_fips": str})
aw["prog"] = np.where(aw.grant_program.eq("Implementation"), "IG", "PD")
grp = c.set_index("fips").group
aw["group"] = aw.primary_county_fips.map(grp)
main = placed.sort_values("pop_share", ascending=False).drop_duplicates("app_id")
main = main[~main.regional]  # direct applicants only, so each has one home county
main["fy"] = main.fiscal_year.astype(int)
main["prog"] = main.grant
main["group"] = main.county_fips.map(grp)
rows = []
for prog, years in (("IG", (2022, 2023, 2024)), ("PD", (2023, 2024))):
    f = aw[(aw.prog == prog) & aw.fiscal_year.isin(years) & ~aw.is_regional_body.astype(bool)]
    u = main[(main.prog == prog) & main.fy.isin(years)]
    for gname in ("urban", "other_rural", "hf_rural"):
        nf, nu = int((f.group == gname).sum()), int((u.group == gname).sum())
        rows.append({"grant": prog, "years": f"FY{years[0] % 100}-FY{years[-1] % 100}", "group": gname,
                     "funded": nf, "unfunded": nu, "funded_pct": round(100 * nf / (nf + nu), 1) if nf + nu else None})
    t = pd.DataFrame([r for r in rows if r["grant"] == prog])
    tab = t[["funded", "unfunded"]].to_numpy()
    if (tab.sum(axis=1) > 0).all():
        chi, p = ss.chi2_contingency(tab)[:2]
        R.setdefault("success_tests", {})[prog] = {"chi2": round(float(chi), 2), "p": round(float(p), 3), "df": 2}
succ = pd.DataFrame(rows)
os.makedirs(P("report", "tables"), exist_ok=True)
succ.to_csv(P("report", "tables", "applicant_success_by_group.csv"), index=False)
R["success"] = rows
R["pd_unfunded_fy23"] = int(((xw.drop_duplicates("app_id").grant == "PD") & (xw.drop_duplicates("app_id").fiscal_year == "2023")).sum())

# ---------- 2. Travel-based death rates ----------
v = pd.read_csv(P("data", "raw", "hpms_2024_county_vmt.csv"), dtype={"fips": str})
v["fips"] = v.fips.replace({"46113": "46102"})  # Oglala Lakota County code change
va = v[v.scope == "all"].groupby("fips")[["daily_vmt", "miles"]].sum()
c = c.merge(va, left_on="fips", right_index=True, how="left")
c["vmt_5yr_100m"] = c.daily_vmt * 365 * 5 / 1e8
c["rate_per_100m_vmt"] = c.deaths_2020_2024 / c.vmt_5yr_100m
elig = c[c.rural & (c.deaths_2020_2024 >= 5) & c.rate_per_100m_vmt.notna() & (c.vmt_5yr_100m > 0)]
thr = elig.rate_per_100m_vmt.quantile(0.75)
c["hf_vmt"] = c.fips.isin(elig[elig.rate_per_100m_vmt >= thr].fips)
c["gap_vmt"] = c.hf_vmt & ~c.covered
both = c.hf & c.hf_vmt
R["vmt"] = {
    "us_annual_vmt_billion": round(float(v[v.scope == "all"].daily_vmt.sum() * 365 / 1e9), 0),
    "counties_with_vmt": int(c.daily_vmt.notna().sum()),
    "threshold_per_100m": round(float(thr), 2),
    "n_hf_vmt": int(c.hf_vmt.sum()),
    "n_hf_both": int(both.sum()),
    "n_gap_vmt": int(c.gap_vmt.sum()),
    "n_gap_both": int((c.gap & c.gap_vmt).sum()),
    "pct_gap_vmt": round(100 * c.gap_vmt.sum() / c.hf_vmt.sum(), 1),
    "cov_hf_vmt_pct": round(100 * c[c.hf_vmt].covered.mean(), 1),
    "cov_other_rural_vmt_pct": round(100 * c[c.rural & ~c.hf_vmt].covered.mean(), 1),
    "rate_rural_per100m": round(float(c[c.rural].deaths_2020_2024.sum() / c[c.rural].vmt_5yr_100m.sum()), 2),
    "rate_urban_per100m": round(float(c[~c.rural].deaths_2020_2024.sum() / c[~c.rural].vmt_5yr_100m.sum()), 2),
    "gap_deaths_vmt": int(c[c.gap_vmt].deaths_2020_2024.sum()),
    "spearman_rate_resident_vs_vmt": round(float(ss.spearmanr(elig.death_rate_per100k_yr, elig.rate_per_100m_vmt)[0]), 2),
}
x = pd.crosstab(c[c.rural].hf_vmt, c[c.rural].covered)
R["vmt"]["chi2_hf_vs_other"] = round(float(ss.chi2_contingency(x)[0]), 2)
R["vmt"]["p_hf_vs_other"] = round(float(ss.chi2_contingency(x)[1]), 3)

keep = ["fips", "state", "county_name", "group", "gap", "n_unfunded_apps", "n_unfunded_direct", "unfunded_sought_plan",
        "unfunded_rounds", "unfunded_applicants", "daily_vmt", "rate_per_100m_vmt", "hf_vmt", "gap_vmt"]
c[keep].to_csv(P("data", "processed", "county_applications_travel.csv"), index=False)
json.dump(R, open(P("report", "analysis_applications_travel.json"), "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in R.items() if k != "applicants"}, indent=1, default=str))
print(json.dumps({k: v for k, v in R["applicants"].items() if k != "gap_with_unfunded_list"}, indent=1))
