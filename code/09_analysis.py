#!/usr/bin/env python3
"""09_analysis.py: the extended analyses for the research article.

Plain-language summary: this script runs six further analyses on the finished
data set and writes every result to report/analysis.json, which the paper reads.
(1) Plan to construction: did places with early plans (FY2022-FY2023) later win
implementation grants? (2) What predicts coverage: regression models of county
coverage on death rate, population, rurality, poverty and income. (3) Dollars
against deaths: SS4A dollars per resident and per traffic death by county type.
(4) Which roads people die on in gap counties, by road owner and road class.
(5) Coverage round by round, FY2022 to FY2026. (6) Where gaps cluster on the
map (Moran's I and local clusters), and how much states differ, including
states FHWA documented as having statewide local road safety programs.
You do not need to open this file.
"""
import json, os, re, warnings
import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from libpysal.weights import Queen
from esda.moran import Moran, Moran_Local

warnings.filterwarnings("ignore")
np.random.seed(2026)  # fixed seed so permutation p-values are reproducible
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw"); INT = os.path.join(ROOT, "data", "interim")
PROC = os.path.join(ROOT, "data", "processed"); REP = os.path.join(ROOT, "report")
TAB = os.path.join(REP, "tables")
P1 = os.path.join(RAW, "project1", "Emmanuel-Oti-Nani-rural-road-fatality-panel-a806351",
                  "data", "processed", "panel_county_year_2015_2024.csv")
S = json.load(open(os.path.join(REP, "stats.json")))
OUT = {}

g = pd.read_csv(os.path.join(PROC, "county_coverage_gap_table.csv"), dtype={"fips": str}).set_index("fips")
a = pd.read_csv(os.path.join(PROC, "ss4a_awards_fy2022_2026.csv"))
ac = pd.read_csv(os.path.join(PROC, "award_county_crosswalk.csv"), dtype={"fips": str})
pairs = pd.read_csv(os.path.join(INT, "bg_award_pairs.csv.gz"), dtype={"fips": str, "bg_geoid": str})
bgpop = pd.read_csv(os.path.join(RAW, "CenPop2020_Mean_BG.txt"), dtype=str, encoding="utf-8-sig")
bgpop["fips"] = bgpop.STATEFP + bgpop.COUNTYFP
cpop = bgpop.assign(p=bgpop.POPULATION.astype(int)).groupby("fips").p.sum()
g["group"] = np.select([g.high_fatality_rural, g.rural_county], ["hf_rural", "other_rural"], "urban")
GROUPS = ["urban", "other_rural", "hf_rural"]
fy = a.set_index("award_id").fiscal_year
ap = set(a.loc[a.includes_action_plan, "award_id"])
ig = set(a.loc[a.includes_implementation, "award_id"])


def share_by_county(ids):
    s = pairs[pairs.award_id.isin(ids)].drop_duplicates("bg_geoid").groupby("fips").POPULATION.sum()
    return (s / cpop).reindex(g.index).fillna(0)


# ---------------------------------------------------------------- (5) rounds
rounds = {}
for y in [2022, 2023, 2024, 2025, 2026]:
    sh = share_by_county({x for x in ap if fy[x] <= y})
    r = {}
    for k in GROUPS:
        m = g.group == k
        r[k] = {"pct_counties_covered": round(100 * (sh[m] >= 0.5).mean(), 1),
                "pct_pop_covered": round(100 * (sh[m] * g.loc[m, "pop2020_census"]).sum() / g.loc[m, "pop2020_census"].sum(), 1)}
    rounds[y] = r
OUT["rounds"] = rounds
# gap between urban and rural (all rural) in percentage points, first and last year
rur = g.rural_county
gaps = {}
for y in [2022, 2026]:
    sh = share_by_county({x for x in ap if fy[x] <= y})
    gaps[y] = round(100 * ((sh[~rur] >= 0.5).mean() - (sh[rur] >= 0.5).mean()), 1)
OUT["urban_rural_gap_pp"] = gaps

# ---------------------------------------------------------------- (1) plan to implementation
early = share_by_county({x for x in ap if fy[x] <= 2023})
igl = share_by_county({x for x in ig if fy[x] >= 2023})
pipe = {}
for k in GROUPS:
    m = (g.group == k) & (early >= 0.5)
    pipe[k] = {"n_early_covered": int(m.sum()),
               "pct_later_impl_any": round(100 * (igl[m] > 0).mean(), 1) if m.sum() else None}
m = rur & (early >= 0.5); pipe["rural_all"] = {"n_early_covered": int(m.sum()), "pct_later_impl_any": round(100 * (igl[m] > 0).mean(), 1)}
m = (~rur) & (early >= 0.5); pipe["urban_all"] = {"n_early_covered": int(m.sum()), "pct_later_impl_any": round(100 * (igl[m] > 0).mean(), 1)}


def norm(n):
    n = str(n).lower().replace("_x000d_", "")
    n = re.sub(r"\(.*?\)", "", n).replace("council of governments", "cog").replace("metropolitian", "metropolitan")
    return re.sub(r"[^a-z0-9]+", "", n)


a["rkey"] = a.state + "|" + a.recipient_name.map(norm)
rec_early = a[a.includes_action_plan & a.fiscal_year.le(2023)].copy()
later_ig_keys = set(a.loc[a.includes_implementation & a.fiscal_year.ge(2023), "rkey"])
rec_early["later_ig"] = rec_early.rkey.isin(later_ig_keys)
rec_early["rural_dot"] = rec_early.dot_rural_urban.eq("Rural")
rr = rec_early.drop_duplicates("rkey")
pipe["recipients"] = {
    "n": int(len(rr)), "pct_later_impl": round(100 * rr.later_ig.mean(), 1),
    "n_rural": int(rr.rural_dot.sum()), "pct_rural_later_impl": round(100 * rr.loc[rr.rural_dot, "later_ig"].mean(), 1),
    "n_urban": int((~rr.rural_dot).sum()), "pct_urban_later_impl": round(100 * rr.loc[~rr.rural_dot, "later_ig"].mean(), 1)}
for t in ["city", "county", "regional_council", "mpo", "tribe"]:
    x = rr[rr.recipient_type == t]
    pipe["recipients"][f"pct_{t}_later_impl"] = round(100 * x.later_ig.mean(), 1) if len(x) else None
    pipe["recipients"][f"n_{t}"] = int(len(x))
from scipy import stats as ss
ct = pd.crosstab(rr.rural_dot, rr.later_ig)
pipe["recipients"]["chi2"] = round(float(ss.chi2_contingency(ct)[0]), 2)
pipe["recipients"]["p"] = float(ss.chi2_contingency(ct)[1])
OUT["pipeline"] = pipe

# ---------------------------------------------------------------- (4) dollars
acx = ac.merge(a[["award_id", "federal_funding", "grant_program", "census_pop_in_area"]].rename(
    columns={"census_pop_in_area": "apop"}), on="award_id")
acx = acx[acx.fips.isin(g.index)]
w = np.where(acx.apop > 0, acx.pop_in_award / acx.apop.replace(0, np.nan), 1.0)
acx["dollars"] = acx.federal_funding * np.nan_to_num(w, nan=1.0)
dol = acx.pivot_table(index="fips", columns="grant_program", values="dollars", aggfunc="sum").reindex(g.index).fillna(0)
dol.columns = ["impl" if c.startswith("Impl") else "plan" for c in dol.columns]
g["dol_plan"], g["dol_impl"] = dol.plan, dol.impl
dd = {}
tot_d = g.deaths_2020_2024.sum(); tot_dol = (g.dol_plan + g.dol_impl).sum()
for k in GROUPS + ["gap"]:
    m = g.gap_flag if k == "gap" else g.group == k
    d = g.loc[m]
    dd[k] = {"n": int(m.sum()), "pop": int(d.pop2020_census.sum()), "deaths": int(d.deaths_2020_2024.sum()),
             "dollars": float(d.dol_plan.sum() + d.dol_impl.sum()), "plan": float(d.dol_plan.sum()), "impl": float(d.dol_impl.sum()),
             "per_res": round((d.dol_plan.sum() + d.dol_impl.sum()) / d.pop2020_census.sum(), 2),
             "per_death": round((d.dol_plan.sum() + d.dol_impl.sum()) / d.deaths_2020_2024.sum(), 0),
             "plan_per_death": round(d.dol_plan.sum() / d.deaths_2020_2024.sum(), 0),
             "impl_per_death": round(d.dol_impl.sum() / d.deaths_2020_2024.sum(), 0),
             "pct_deaths": round(100 * d.deaths_2020_2024.sum() / tot_d, 1),
             "pct_dollars": round(100 * (d.dol_plan.sum() + d.dol_impl.sum()) / tot_dol, 1)}
dd["allocated_total"] = float(tot_dol)
dd["unallocated"] = float(a.federal_funding.sum() - tot_dol)
OUT["dollars"] = dd

# ---------------------------------------------------------------- (4b) road owner and class
p = pd.read_csv(P1, dtype={"fips": str})
p5 = p[p.year.between(2020, 2024)].groupby("fips").sum(numeric_only=True)
own = {"state": "deaths_own_state", "county": "deaths_own_county", "city_town": "deaths_own_town_city",
       "federal_tribal": "deaths_own_federal_tribal", "other": "deaths_own_other_public_private", "unknown": "deaths_own_owner_unknown"}
cls = {"interstate_fwy": "deaths_interstate_fwy", "arterial": "deaths_arterial", "collector": "deaths_collector",
       "local": "deaths_local", "unknown": "deaths_road_unknown"}
roads = {}
for k in GROUPS + ["gap", "hf_covered"]:
    m = g.gap_flag if k == "gap" else ((g.group == "hf_rural") & ~g.gap_flag if k == "hf_covered" else g.group == k)
    sub = p5.loc[p5.index.isin(g.index[m])]
    t = sub.deaths.sum()
    roads[k] = {"deaths": int(t), "owner": {o: round(100 * sub[c].sum() / t, 1) for o, c in own.items()},
                "class": {o: round(100 * sub[c].sum() / t, 1) for o, c in cls.items()}}
OUT["roads"] = roads

# ---------------------------------------------------------------- (2) regression
sa = []
for x in open(os.path.join(RAW, "est23all.txt")).read().splitlines():
    if x[3:6].strip() != "0":
        sa.append((x[0:2] + x[3:6].strip().zfill(3), x[34:38], x[133:139]))
sa = pd.DataFrame(sa, columns=["fips", "pov", "mhi"]).set_index("fips").apply(pd.to_numeric, errors="coerce")
R = g.join(sa, how="left")
R["covered"] = (R.share_action_plan_area_fy22_26 >= 0.5).astype(int)
R["share"] = R.share_action_plan_area_fy22_26.clip(0, 1)
R["log_pop"] = np.log(R.pop2020_census)
R["rural10"] = R.pct_rural_2020 / 10
R["rate10"] = (R.death_rate_per100k_yr / 10).clip(upper=20)  # cap extreme small-county rates at 200 per 100k
R["pov"] = R.pov
R["log_mhi"] = np.log(R.mhi)
R["state_fips"] = R.index.str[:2]
REG = {"09": "NE", "23": "NE", "25": "NE", "33": "NE", "34": "NE", "36": "NE", "42": "NE", "44": "NE", "50": "NE",
       "17": "MW", "18": "MW", "19": "MW", "20": "MW", "26": "MW", "27": "MW", "29": "MW", "31": "MW", "38": "MW", "39": "MW", "46": "MW", "55": "MW",
       "01": "S", "05": "S", "10": "S", "11": "S", "12": "S", "13": "S", "21": "S", "22": "S", "24": "S", "28": "S", "37": "S", "40": "S", "45": "S", "47": "S", "48": "S", "51": "S", "54": "S",
       "02": "W", "04": "W", "06": "W", "08": "W", "15": "W", "16": "W", "30": "W", "32": "W", "35": "W", "41": "W", "49": "W", "53": "W", "56": "W"}
R["region"] = R.state_fips.map(REG)
D = R.dropna(subset=["pov", "log_mhi"]).copy()
OUT["reg_n"] = int(len(D)); OUT["reg_dropped"] = int(len(R) - len(D))
X = "log_pop + rural10 + rate10 + pov + log_mhi"
m1 = smf.glm(f"covered ~ {X} + C(region)", data=D, family=sm.families.Binomial()).fit(
    cov_type="cluster", cov_kwds={"groups": pd.factorize(D.state_fips)[0]})
m2 = smf.ols(f"covered ~ {X} + C(state_fips)", data=D).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(D.state_fips)[0]})
m3 = smf.glm(f"share ~ {X} + C(region)", data=D, family=sm.families.Binomial()).fit(
    cov_type="cluster", cov_kwds={"groups": pd.factorize(D.state_fips)[0]})
Dr = D[D.rural_county].copy()
m4 = smf.glm(f"covered ~ {X} + C(region)", data=Dr, family=sm.families.Binomial()).fit(
    cov_type="cluster", cov_kwds={"groups": pd.factorize(Dr.state_fips)[0]})
VARS = ["log_pop", "rural10", "rate10", "pov", "log_mhi"]


def summ(m, kind):
    res = {}
    me = None
    if kind == "logit":
        me = m.get_margeff(at="overall") if hasattr(m, "get_margeff") else None
    for v in VARS:
        res[v] = {"b": float(m.params[v]), "se": float(m.bse[v]), "p": float(m.pvalues[v])}
        if kind == "logit":
            res[v]["or"] = float(np.exp(m.params[v]))
    return res


def ame(m, data, v, eps=1e-4):
    d1 = data.copy(); d1[v] = d1[v] + eps
    return float((m.predict(d1) - m.predict(data)).mean() / eps)


OUT["reg"] = {"m1_logit_region": summ(m1, "logit"), "m2_lpm_state": summ(m2, "lpm"),
              "m3_fraclogit_region": summ(m3, "logit"), "m4_logit_rural": summ(m4, "logit"),
              "n": {"m1": int(m1.nobs), "m2": int(m2.nobs), "m3": int(m3.nobs), "m4": int(m4.nobs)},
              "ame_m1": {v: ame(m1, D, v) for v in VARS}, "ame_m4": {v: ame(m4, Dr, v) for v in VARS},
              "r2_m2": float(m2.rsquared),
              "pseudo_r2_m1": float(1 - m1.deviance / m1.null_deviance)}
# share of variance in rural coverage explained by state alone
mstate = smf.ols("covered ~ C(state_fips)", data=R[R.rural_county]).fit()
OUT["state_r2_rural"] = round(float(mstate.rsquared), 3)

# ---------------------------------------------------------------- (6) spatial
c = gpd.read_file("zip://" + os.path.join(RAW, "cb_2020_us_county_500k.zip"))
c = c[c.GEOID.isin(g.index)].set_index("GEOID").loc[g.index].to_crs(5070)
W = Queen.from_dataframe(c.reset_index(), use_index=False, silence_warnings=True)
W.transform = "r"
y = g.share_action_plan_area_fy22_26.fillna(0).values
isl = set(W.islands)
mi = Moran(y, W, permutations=999)
OUT["moran_share"] = {"I": round(float(mi.I), 3), "p_sim": float(mi.p_sim), "n_islands": len(isl)}
yg = g.gap_flag.astype(float).values
mg = Moran(yg, W, permutations=999)
OUT["moran_gap"] = {"I": round(float(mg.I), 3), "p_sim": float(mg.p_sim)}
lm = Moran_Local(y, W, permutations=999, seed=2026)
sig = lm.p_sim < 0.05
q = np.where(sig, lm.q, 0)  # 1 HH, 2 LH, 3 LL, 4 HL
g["lisa"] = pd.Series(q, index=g.index).map({0: "ns", 1: "HH", 2: "LH", 3: "LL", 4: "HL"})
g.loc[g.index.isin([g.index[i] for i in isl]), "lisa"] = "island"
OUT["lisa"] = {k: int(v) for k, v in g.lisa.value_counts().items()}
OUT["lisa_gap"] = {k: int(v) for k, v in g.loc[g.gap_flag, "lisa"].value_counts().items()}
OUT["lisa_ll_rural_pct"] = round(100 * (g.loc[g.lisa == "LL", "rural_county"]).mean(), 1)
OUT["pct_gap_in_ll"] = round(100 * (g.loc[g.gap_flag, "lisa"] == "LL").mean(), 1)
g[["lisa"]].to_csv(os.path.join(INT, "county_lisa.csv"))
# states with statewide local road safety programs documented by FHWA (Anderson et al. 2010)
SCAN = ["AL", "GA", "IL", "MI", "MN", "NJ", "WA"]
sc = g.state.isin(SCAN)
ru = g.rural_county
OUT["scan_states"] = {
    "states": SCAN,
    "rural_covered_scan": round(100 * g.loc[ru & sc, "coverage_status"].eq("covered").mean(), 1),
    "rural_covered_other": round(100 * g.loc[ru & ~sc, "coverage_status"].eq("covered").mean(), 1),
    "n_rural_scan": int((ru & sc).sum()), "n_rural_other": int((ru & ~sc).sum()),
    "hf_gap_pct_scan": round(100 * g.loc[g.high_fatality_rural & sc, "gap_flag"].mean(), 1),
    "hf_gap_pct_other": round(100 * g.loc[g.high_fatality_rural & ~sc, "gap_flag"].mean(), 1),
    "n_hf_scan": int((g.high_fatality_rural & sc).sum()),
    "by_state": {s: round(100 * g.loc[ru & (g.state == s), "coverage_status"].eq("covered").mean(), 1) for s in SCAN}}
ct2 = pd.crosstab(sc[ru], g.loc[ru, "coverage_status"].eq("covered"))
OUT["scan_states"]["chi2"] = round(float(ss.chi2_contingency(ct2)[0]), 2)
OUT["scan_states"]["p"] = float(ss.chi2_contingency(ct2)[1])
st = g[ru].groupby("state").coverage_status.apply(lambda s: 100 * s.eq("covered").mean())
OUT["state_rural_cov_range"] = {"min": round(float(st.min()), 1), "max": round(float(st.max()), 1),
                                "n_states_zero": int((st == 0).sum()), "n_states_ge75": int((st >= 75).sum()),
                                "iqr": [round(float(st.quantile(.25)), 1), round(float(st.quantile(.75)), 1)]}

json.dump(OUT, open(os.path.join(REP, "analysis.json"), "w"), indent=1, default=float)
g[["group", "dol_plan", "dol_impl", "lisa"]].to_csv(os.path.join(TAB, "county_dollars_lisa.csv"))
print(json.dumps(OUT, indent=1, default=float)[:6000])
