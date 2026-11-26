"""Independent check of the paper's headline figures.

Recomputes the main numbers straight from the released CSV files (not from
report/stats.json, which the paper build uses), then confirms that each one
appears in the compiled paper text. Run after code/08_paper.py:

    python tools/audit_paper_numbers.py

Exits with an error if a recomputed figure is missing from the paper.
"""
import os, re, subprocess, sys
import numpy as np
import pandas as pd
from scipy import stats as ss

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

aw = pd.read_csv(P("data", "processed", "ss4a_awards_fy2022_2026.csv"), low_memory=False)
cty = pd.read_csv(P("data", "processed", "county_coverage_gap_table.csv"), dtype={"fips": str})
dol = pd.read_csv(P("report", "tables", "county_dollars_lisa.csv"), dtype={"fips": str})
text = subprocess.run(["pdftotext", "-layout", P("paper", "main.pdf"), "-"], capture_output=True, text=True).stdout
text = "\n".join(re.sub(r"^\s*\d{1,3}\s{2,}", "", ln) for ln in text.splitlines())  # drop line numbers
text = re.sub(r"\s+", " ", text.split("References")[0]).replace("−", "-")

checks = []
def chk(label, value, *forms):
    ok = any(f in text for f in forms)
    checks.append((ok, label, value, forms[0]))

# Program totals
chk("awards", len(aw), f"{len(aw):,}")
chk("federal funding ($B)", aw.federal_funding.sum() / 1e9, f"${aw.federal_funding.sum()/1e9:.2f} billion")
ap = aw[aw.includes_action_plan.astype(bool)]
chk("action plan awards", len(ap), f"{len(ap):,}")
chk("action plan awards to regional bodies", int(ap.is_regional_body.astype(bool).sum()), f"{int(ap.is_regional_body.astype(bool).sum())}")
byfy = ap.groupby("fiscal_year").size()
chk("action plan awards FY2022", byfy.iloc[0], f"from {byfy.iloc[0]} in FY2022")
chk("action plan awards FY2026", byfy.iloc[-1], f"to {byfy.iloc[-1]} in FY2026")
rb = ap[ap.is_regional_body.astype(bool)].groupby("fiscal_year").size()
assert all(a > b for a, b in zip(rb, rb[1:])), "regional body action plan awards did not fall every round"
chk("regional body action plans first to last", (rb.iloc[0], rb.iloc[-1]), f"from {rb.iloc[0]} to {rb.iloc[-1]}")

# County groups
c = cty.copy()
c["rural"] = c.rural_county.astype(bool)
c["hf"] = c.high_fatality_rural.astype(bool)
c["covd"] = c.coverage_status.eq("covered")
urban, rural, hf = c[~c.rural], c[c.rural], c[c.hf]
oth = c[c.rural & ~c.hf]
pct = lambda d: 100 * d["covd"].mean()
chk("rural counties", len(rural), f"{len(rural):,} rural counties")
chk("counties total", len(c), f"{len(c):,} counties")
chk("high-fatality rural", len(hf), f"{len(hf)} high-fatality rural", f"{len(hf)} rural counties with the highest")
chk("urban covered %", pct(urban), f"{pct(urban):.0f}% of urban counties")
chk("other rural covered %", pct(oth), f"{pct(oth):.0f}% of other rural")
chk("hf rural covered %", pct(hf), f"{pct(hf):.0f}% of high-fatality rural")
chk("all rural covered %", pct(rural), f"{pct(rural):.0f}% of rural counties")
pop = lambda d: 100 * (d.pop2020_census * d.share_action_plan_area_fy22_26).sum() / d.pop2020_census.sum()
chk("population covered %", pop(c), f"about {pop(c):.0f}% of U.S. residents")
chk("urban residents covered %", pop(urban), f"{pop(urban):.0f}% of residents in urban")
chk("rural residents covered %", pop(rural), f"{pop(rural):.0f}% of those in rural")
rate = lambda d: d.deaths_2020_2024.sum() / d.person_years_2020_2024.sum() * 1e5
chk("rural death rate", rate(rural), f"{rate(rural):.1f} traffic deaths")
chk("urban death rate", rate(urban), f"{rate(urban):.1f} in urban")
assert 1.9 < rate(rural) / rate(urban) < 2.2, "abstract says rural death rate is twice as high"
x = pd.crosstab(~c.rural, c.covd); chi_ur = ss.chi2_contingency(x)[0]
chk("chi2 rural vs urban", chi_ur, f"χ²₁ = {chi_ur:.1f}", f"χ2 1 = {chi_ur:.1f}", f"{chi_ur:.1f}")
x = pd.crosstab(rural.hf, rural.covd); chi_hf, p_hf = ss.chi2_contingency(x)[:2]
chk("chi2 hf vs other rural", chi_hf, f"{chi_hf:.2f}", f"p = {p_hf:.2f}")
r5 = rural[rural.deaths_2020_2024 >= 5]
rho = ss.spearmanr(r5.death_rate_per100k_yr, r5.share_action_plan_area_fy22_26)[0]
chk("Spearman rho", rho, f"{rho:.2f}")

# Gap counties
g = c[c.gap_flag.astype(bool)]
chk("gap counties", len(g), f"{len(g)} (65%)", f"{len(g)} ({100*len(g)/len(hf):.0f}%)")
chk("gap share %", 100 * len(g) / len(hf), f"({100*len(g)/len(hf):.0f}%)")
chk("gap no residents covered", int((g.share_action_plan_area_fy22_26 == 0).sum()), f"{int((g.share_action_plan_area_fy22_26 == 0).sum())} had no residents")
chk("gap partly covered", int((g.share_action_plan_area_fy22_26 > 0).sum()), f"{int((g.share_action_plan_area_fy22_26 > 0).sum())} were partly")
chk("gap deaths", int(g.deaths_2020_2024.sum()), f"{int(g.deaths_2020_2024.sum()):,} traffic deaths")
chk("gap share of hf deaths %", 100 * g.deaths_2020_2024.sum() / hf.deaths_2020_2024.sum(), f"{100*g.deaths_2020_2024.sum()/hf.deaths_2020_2024.sum():.0f}% of deaths in high-fatality")
chk("gap share of national deaths %", 100 * g.deaths_2020_2024.sum() / c.deaths_2020_2024.sum(), f"{100*g.deaths_2020_2024.sum()/c.deaths_2020_2024.sum():.1f}% of")
chk("gap states", g.state.nunique(), f"across {g.state.nunique()} states")
vc = g.state.value_counts()
NAMES = {"TX": "Texas", "MS": "Mississippi", "GA": "Georgia", "AR": "Arkansas", "CO": "Colorado", "OK": "Oklahoma"}
for st, k in vc[vc >= vc.iloc[4]].items():  # top five, plus any state tied with fifth place
    tied = [NAMES[x] for x, v in vc.items() if v == k]
    form = f"{NAMES[st]} ({k})" if len(tied) == 1 else f"{' and '.join(tied)} ({k} each)"
    chk(f"gap counties in {st}", k, form, f"{NAMES[st]} has the largest number ({k})")
gc = c[c.hf & ~c.coverage_status_conservative.eq("covered")]
chk("gap, conservative", len(gc), f"{len(gc)} counties under the conservative")
g25 = c[c.hf & ~c.coverage_status_fy22_25.eq("covered")]
chk("gap, FY22-25", len(g25), f"{len(g25)} when the final round")
nb = g.neighbor_regional_body_plans.fillna("").str.len().gt(0).sum()
chk("gap counties with neighbor regional plan", nb, f"In {nb} of the {len(g)} gap")
t10 = g.sort_values("deaths_2020_2024", ascending=False).head(10)
nofund = int((t10.share_action_plan_area_fy22_26 == 0).sum())
assert nofund == 7, f"text says seven of the top ten have no coverage, data say {nofund}"
part = set(t10[t10.share_action_plan_area_fy22_26 > 0].county_name + ", " + t10[t10.share_action_plan_area_fy22_26 > 0].state)
for nm in ["Navajo County, AZ", "McKinley County, NM", "Apache County, AZ"]:
    assert nm in part, f"{nm} expected among the partly covered top ten"
checks.append((all(nm in text for nm in part), "top-ten partly covered names", sorted(part), "each name in the text"))

# Dollars by county group (allocation already done in code/09_analysis.py)
d = dol.merge(c[["fips", "rural", "hf", "gap_flag", "deaths_2020_2024", "pop2020_census"]], on="fips", how="left", suffixes=("", "_c"))
d["dol_total"] = d.dol_plan + d.dol_impl
dcol = ["dol_total"]
if dcol:
    tot = d[dcol[0]].sum()
    grp = {"urban": ~d.rural, "hf": d.hf, "gap": d.gap_flag.astype(bool)}
    deaths_all = c.deaths_2020_2024.sum()
    for k, m in grp.items():
        share = 100 * d.loc[m, dcol[0]].sum() / tot
        per_death = d.loc[m, dcol[0]].sum() / d.loc[m, "deaths_2020_2024"].sum()
        chk(f"{k} share of dollars %", share, f"{share:.0f}%" if k == "urban" else f"{share:.1f}%")
        chk(f"{k} dollars per death", per_death, f"${per_death:,.0f}")
    chk("urban share of deaths %", 100 * d.loc[~d.rural, "deaths_2020_2024"].sum() / deaths_all, f"{100*d.loc[~d.rural,'deaths_2020_2024'].sum()/deaths_all:.0f}% of traffic deaths")
else:
    checks.append((False, "dollar columns", None, "no total dollar column found in county_dollars_lisa.csv"))

# ---------- unfunded applications and travel figures (recomputed from released CSVs, not from analysis_applications_travel.json) ----------
xp = P("data", "processed", "unfunded_applicant_county_crosswalk.csv")
if os.path.exists(xp):
    ux = pd.read_csv(xp, dtype=str)
    ux["regional"] = ux.match_method.str.contains("regional", na=False)
    gf = set(g.fips)
    hit = ux[ux.county_fips.isin(gf)]
    n_any, n_dir = hit.county_fips.nunique(), hit[~hit.regional].county_fips.nunique()
    chk("gap counties with an unfunded application", n_any, f"Only {n_any} of the {len(g)} gap")
    chk("of which direct", n_dir, f"in only {n_dir} of them")
    chk("gap counties with no record", len(g) - n_any, f"remaining {len(g) - n_any} gap")
    chk("unfunded list rows", ux.app_id.nunique(), f"contain {ux.app_id.nunique()} applications")
    vv = pd.read_csv(P("data", "raw", "hpms_2024_county_vmt.csv"), dtype={"fips": str})
    vv["fips"] = vv.fips.replace({"46113": "46102"})
    va = vv[vv.scope == "all"].groupby("fips").daily_vmt.sum()
    cc = c.copy(); cc["vmt100m"] = cc.fips.map(va) * 365 * 5 / 1e8
    cc["rv"] = cc.deaths_2020_2024 / cc.vmt100m
    el = cc[cc.rural & (cc.deaths_2020_2024 >= 5) & cc.rv.notna() & (cc.vmt100m > 0)]
    hv = el[el.rv >= el.rv.quantile(0.75)]
    gv = hv[~hv.covd]
    nboth = int(hv.fips.isin(cty.loc[cty.high_fatality_rural.astype(str).eq("True"), "fips"]).sum())
    chk("travel-based high-fatality counties", len(hv), f"identifies {len(hv)} counties", f"{len(hv)} counties, {nboth} of which are also high-fatality")
    chk("travel-based gap counties", len(gv), f"and {len(gv)} of them ({100*len(gv)/len(hv):.0f}%)")
    rr = cc[cc.rural].deaths_2020_2024.sum() / cc[cc.rural].vmt100m.sum()
    chk("rural deaths per 100M VMT", rr, f"recorded {rr:.2f} deaths per 100 million")


bad = [x for x in checks if not x[0]]
for ok, label, val, form in checks:
    print(("ok   " if ok else "MISS ") + f"{label}: {val}  [looked for: {form}]")
print(f"\n{len(checks) - len(bad)} of {len(checks)} recomputed figures found in the paper")
if bad:
    sys.exit(1)
