#!/usr/bin/env python3
"""08_paper.py: build the research article from the processed data.

Plain-language summary: draws the article's figures, fills the data-linked
numbers in code/paper_template.tex (the author's text) from report/stats.json
and report/analysis.json, checks the article's claims against the data, writes
paper/main.tex and compiles it to paper/main.pdf. After compiling, run
tools/audit_paper_numbers.py to recompute the headline figures from the
released CSV files.
The article carries a DRAFT watermark until you run it with --final after your
review. To add the Zenodo DOI once it exists:
    python code/08_paper.py --doi 10.5281/zenodo.NNNNNNN
Run code/09_analysis.py before this script. Requires TeX Live (lineno, natbib,
orcidlink, draftwatermark).
"""
import argparse, json, os, re, subprocess
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as ss

ap = argparse.ArgumentParser()
ap.add_argument("--final", action="store_true")
ap.add_argument("--doi", default=None)
args = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed"); RAW = os.path.join(ROOT, "data", "raw"); INT = os.path.join(ROOT, "data", "interim")
OUT = os.path.join(ROOT, "paper"); FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)
S = json.load(open(os.path.join(ROOT, "report", "stats.json")))
A = json.load(open(os.path.join(ROOT, "report", "analysis.json")))
AU = json.load(open(os.path.join(ROOT, "AUTHORS.json")))["authors"][0]
g = pd.read_csv(os.path.join(PROC, "county_coverage_gap_table.csv"), dtype={"fips": str})
a = pd.read_csv(os.path.join(PROC, "ss4a_awards_fy2022_2026.csv"))
REPO = "\\url{https://github.com/Emmanuel-Oti-Nani/ss4a-safety-action-plan-coverage}"
DOI = (f"\\href{{https://doi.org/{args.doi}}}{{doi:{args.doi}}}" if args.doi
       else "[DOI pending: assigned by Zenodo at release]")
C_COV, C_PART, C_NONE, C_GAP, C_URB, INK, INK2 = "#1c5cab", "#86b6ef", "#d3d2cd", "#eb6834", "#f3f2ee", "#0b0b0b", "#52514e"
C_OTH = "#86b6ef"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
GN = {"urban": "Urban", "other_rural": "Other rural", "hf_rural": "High-fatality rural", "gap": "Gap counties"}


def n(x):
    return f"{int(round(x)):,}".replace(",", "{,}")


def tex(s):
    return s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def money(x):
    return "\\$" + n(x)


def clean_axes(ax, left=False):
    for s_ in ["top", "right"] + (["left"] if left else []):
        ax.spines[s_].set_visible(False)


# ---------------- figure: coverage by group ----------------
grp = np.select([g.high_fatality_rural, g.rural_county], ["High-fatality rural", "Other rural"], "Urban")
order = ["Urban", "Other rural", "High-fatality rural"]
t = pd.crosstab(grp, g.coverage_status, normalize="index").reindex(order)[["covered", "partly covered", "not covered"]] * 100
cnt = pd.Series(grp).value_counts().reindex(order)
fig, ax = plt.subplots(figsize=(6.0, 2.3))
left = np.zeros(3)
for k, col in [("covered", C_COV), ("partly covered", C_PART), ("not covered", C_NONE)]:
    ax.barh(range(3), t[k], left=left, color=col, edgecolor="white", linewidth=1.5, height=0.6, label=k.capitalize())
    for i, v in enumerate(t[k]):
        if v >= 7:
            ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                    color="white" if k == "covered" else INK)
    left += t[k].values
ax.set_yticks(range(3)); ax.set_yticklabels([f"{o}\n({cnt[o]:,} counties)" for o in order], fontsize=8)
ax.set_xlim(0, 100); ax.set_xlabel("Percent of counties")
clean_axes(ax, left=True); ax.tick_params(axis="y", length=0)
ax.legend(ncol=3, frameon=False, loc="lower left", bbox_to_anchor=(-0.02, 1.0), fontsize=8, handlelength=1)
fig.savefig(os.path.join(FIG, "fig_groups.pdf"), bbox_inches="tight"); plt.close(fig)

# ---------------- figure: rounds ----------------
yrs = [2022, 2023, 2024, 2025, 2026]
fig, ax = plt.subplots(figsize=(6.0, 3.0))
ends = {}
for k, col, mk in [("urban", "#52514e", "o"), ("other_rural", C_COV, "s"), ("hf_rural", C_GAP, "D")]:
    v = [A["rounds"][str(y)][k]["pct_counties_covered"] for y in yrs]
    ax.plot(yrs, v, color=col, lw=2, marker=mk, ms=6, markeredgecolor="white", markeredgewidth=1)
    ends[k] = v[-1]
pos = dict(ends)
ks = sorted(pos, key=pos.get)
for i in range(1, len(ks)):  # keep end labels at least 5 points apart
    if pos[ks[i]] - pos[ks[i - 1]] < 5:
        pos[ks[i]] = pos[ks[i - 1]] + 5
for k in ends:
    ax.text(2026.15, pos[k], f"{GN[k]} {ends[k]:.0f}%", va="center", fontsize=8, color=INK)
ax.set_xticks(yrs); ax.set_xticklabels([f"FY{y}" for y in yrs]); ax.set_xlim(2021.8, 2027.3)
ax.set_ylim(0, 70); ax.set_ylabel("Counties covered (%)")
ax.yaxis.grid(True, color="#e6e5e0", lw=0.6); ax.set_axisbelow(True); clean_axes(ax)
fig.savefig(os.path.join(FIG, "fig_rounds.pdf"), bbox_inches="tight"); plt.close(fig)

# ---------------- figure: dollars per death ----------------
D = A["dollars"]; keys = ["urban", "other_rural", "hf_rural", "gap"]
fig, ax = plt.subplots(figsize=(6.0, 2.4))
pl = [D[k]["plan_per_death"] / 1000 for k in keys]; im = [D[k]["impl_per_death"] / 1000 for k in keys]
y = np.arange(len(keys))[::-1]
ax.barh(y, pl, color=C_OTH, height=0.6, edgecolor="white", linewidth=1.5, label="Planning and demonstration")
ax.barh(y, im, left=pl, color=C_COV, height=0.6, edgecolor="white", linewidth=1.5, label="Implementation")
for yi, a_, b_ in zip(y, pl, im):
    ax.text(a_ + b_ + 0.4, yi, f"${(a_+b_):.1f}k", va="center", fontsize=8, color=INK)
ax.set_yticks(y); ax.set_yticklabels([GN[k] for k in keys], fontsize=8)
ax.set_xlabel("SS4A dollars per traffic death, 2020-2024 (thousands)")
clean_axes(ax, left=True); ax.tick_params(axis="y", length=0)
ax.legend(ncol=2, frameon=False, loc="lower left", bbox_to_anchor=(-0.02, 1.0), fontsize=8, handlelength=1)
fig.savefig(os.path.join(FIG, "fig_dollars.pdf"), bbox_inches="tight"); plt.close(fig)

# ---------------- maps ----------------
c = gpd.read_file("zip://" + os.path.join(RAW, "cb_2020_us_county_500k.zip"))
c = c[~c.STATEFP.isin(["02", "15", "60", "66", "69", "72", "78"])].merge(g, left_on="GEOID", right_on="fips").to_crs(5070)
stb = c.dissolve("STATEFP").boundary
c["cls"] = np.select([~c.rural_county, c.gap_flag, c.coverage_status.eq("covered"), c.coverage_status.eq("partly covered")],
                     ["urban", "gap", "cov", "part"], "none")
colr = {"urban": C_URB, "none": C_NONE, "part": C_PART, "cov": C_COV, "gap": C_GAP}
fig, ax = plt.subplots(figsize=(7.5, 4.6))
for k in ["urban", "none", "part", "cov", "gap"]:
    c[c.cls == k].plot(ax=ax, color=colr[k], edgecolor="white", linewidth=0.1)
stb.plot(ax=ax, color="white", linewidth=0.5); ax.set_axis_off()
lab = [(C_GAP, f"High-fatality rural, under half covered ({S['n_gap_counties']})"), (C_COV, "Rural, half or more covered"),
       (C_PART, "Rural, partly covered"), (C_NONE, "Rural, not covered"), (C_URB, "Urban county")]
ax.legend([plt.Rectangle((0, 0), 1, 1, fc=k, ec="#9a9994", lw=0.3) for k, _ in lab], [l for _, l in lab],
          loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3, frameon=False, fontsize=8)
fig.savefig(os.path.join(FIG, "fig_map.pdf"), bbox_inches="tight"); plt.close(fig)

lisa = pd.read_csv(os.path.join(INT, "county_lisa.csv"), dtype={"fips": str}).set_index("fips").lisa
c["lisa"] = c.fips.map(lisa)
LC = {"LL": C_GAP, "HH": C_COV, "LH": "#f3b59a", "HL": C_PART, "ns": "#e9e8e4", "island": "#e9e8e4"}
fig, ax = plt.subplots(figsize=(7.5, 4.6))
for k in ["ns", "island", "HL", "LH", "HH", "LL"]:
    sub = c[c.lisa == k]
    if len(sub):
        sub.plot(ax=ax, color=LC[k], edgecolor="white", linewidth=0.1)
c[c.gap_flag].boundary.plot(ax=ax, color=INK, linewidth=0.45)
stb.plot(ax=ax, color="white", linewidth=0.5); ax.set_axis_off()
lab = [(LC["LL"], "Low coverage among low (low-low)"), (LC["HH"], "High among high (high-high)"),
       (LC["LH"], "Low among high"), (LC["HL"], "High among low"), (LC["ns"], "Not significant")]
hs = [plt.Rectangle((0, 0), 1, 1, fc=k, ec="#9a9994", lw=0.3) for k, _ in lab] + [plt.Rectangle((0, 0), 1, 1, fc="none", ec=INK, lw=0.8)]
ax.legend(hs, [l for _, l in lab] + ["Gap county (outline)"], loc="upper center", bbox_to_anchor=(0.5, 0.0),
          ncol=3, frameon=False, fontsize=8)
fig.savefig(os.path.join(FIG, "fig_lisa.pdf"), bbox_inches="tight"); plt.close(fig)

# ---------------- statistics ----------------
G = S["groups"]
cov_pct = {k: 100 * G[k]["main"].get("covered", 0) / G[k]["n"] for k in G}
rur_cov = G["hf_rural"]["main"].get("covered", 0) + G["other_rural"]["main"].get("covered", 0)
rur_n = G["hf_rural"]["n"] + G["other_rural"]["n"]
chi_ru = ss.chi2_contingency([[rur_cov, rur_n - rur_cov], [G["urban"]["main"]["covered"], G["urban"]["n"] - G["urban"]["main"]["covered"]]])
chi_hf = ss.chi2_contingency([[G["hf_rural"]["main"]["covered"], G["hf_rural"]["n"] - G["hf_rural"]["main"]["covered"]],
                              [G["other_rural"]["main"]["covered"], G["other_rural"]["n"] - G["other_rural"]["main"]["covered"]]])
el = g[g.rural_county & (g.deaths_2020_2024 >= S["min_deaths"])]
rho = ss.spearmanr(el.death_rate_per100k_yr, el.share_action_plan_area_fy22_26.fillna(0)).statistic


def ptxt(p):
    return "$p<0.001$" if p < 0.001 else f"$p={p:.2f}$" if p >= 0.01 else f"$p={p:.3f}$"


def stars(p):
    return "^{***}" if p < 0.001 else "^{**}" if p < 0.01 else "^{*}" if p < 0.05 else ""


R = A["reg"]
# ---- checks that the text's claims hold ----
assert chi_hf[1] > 0.05
assert S["rate_rural_counties"] / S["rate_urban_counties"] > 1.9
rb = [r["n_ap_regional"] for r in S["by_fy"]]
assert all(x > y for x, y in zip(rb, rb[1:]))
for f in ["06049", "38053"]:
    assert bool(g.loc[g.fips == f, "gap_flag"].iloc[0])
assert A["urban_rural_gap_pp"]["2026"] > A["urban_rural_gap_pp"]["2022"]
for v in ["rate10", "pov", "log_mhi"]:
    assert R["m1_logit_region"][v]["p"] > 0.05, v
assert R["m1_logit_region"]["rural10"]["p"] < 0.05 and R["m1_logit_region"]["rural10"]["b"] < 0
assert all(R["m4_logit_rural"][v]["p"] > 0.05 for v in R["m4_logit_rural"])
assert 0.05 > R["m2_lpm_state"]["rate10"]["p"] or R["m2_lpm_state"]["rate10"]["p"] < 0.1
ps = A["pipeline"]["recipients"]
assert ps["p"] > 0.05 and ps["pct_regional_council_later_impl"] == 0 and ps["pct_mpo_later_impl"] == 0 and ps["pct_tribe_later_impl"] == 0
assert A["scan_states"]["p"] < 0.05 and A["scan_states"]["rural_covered_scan"] < A["scan_states"]["rural_covered_other"]
r22 = A["rounds"]["2022"]; r26 = A["rounds"]["2026"]
assert r22["hf_rural"]["pct_counties_covered"] < r22["other_rural"]["pct_counties_covered"]
assert r26["hf_rural"]["pct_counties_covered"] <= r26["other_rural"]["pct_counties_covered"]

# ---------------- tables ----------------
tabfy = "\n".join(f"FY{r['fy']} & {n(r['n'])} & {n(r['dollars']/1e6)} & {r['n_ig']} & {n(r['n_ap'])} & {r['n_ap_regional']} \\\\" for r in S["by_fy"])
tot = {k: sum(r[k] for r in S["by_fy"]) for k in ["n", "dollars", "n_ig", "n_ap", "n_ap_regional"]}
tabfy += f"\n\\midrule\nTotal & {n(tot['n'])} & {n(tot['dollars']/1e6)} & {tot['n_ig']} & {n(tot['n_ap'])} & {tot['n_ap_regional']} \\\\"
rows = []
for k in ["urban", "other_rural", "hf_rural"]:
    d = G[k]; pc = lambda m: 100 * d[m].get("covered", 0) / d["n"]
    rows.append(f"{GN[k]} & {n(d['n'])} & {d['rate']:.1f} & {pc('main'):.1f} & {pc('conservative'):.1f} & {pc('fy22_25'):.1f} \\\\")
tabcov = "\n".join(rows)
top = S["priority_top10"]
abbrev = lambda s: (s.replace("Metropolitan Planning Organization", "MPO").replace("Council of Governments", "COG")
                     .replace("Development District", "Dev. District").replace("Mid-Region COG MPO", "Mid-Region COG")
                     .replace("Myrtle Beach - Socastee", "Myrtle Beach").replace("Wilmington Urban Area", "Wilmington")
                     .split(";")[0].replace("(Flagstaff MPO)", "").strip())
tabtop = "\n".join(f"{tex(r['county'])}, {r['state']} & {r['deaths']} & {r['rate']:.1f} & {r['share']:.2f} & "
                   f"{tex(abbrev(r['neighbor'])) if r['neighbor'] else '--'} \\\\" for r in top)
nnone = sum(r["status"] == "not covered" for r in top)
part = [f"{r['county']}, {r['state']}" for r in top if r["status"] != "not covered"]
words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}
small = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
topnote = (f"{words[nnone]} of them have no funded plan area at all, and the other {small.get(len(part), len(part))} "
           f"({tex('; '.join(part))}) are reached only in part, by Navajo Nation plans and, in Navajo County, by the plans of two small cities.")
if not all(r["state"] in ("AZ", "NM") for r in top if r["status"] != "not covered"):
    topnote = f"{words[nnone]} of them have no funded plan area at all, and the others are reached only in part."
LAB = {"log_pop": "Log population", "rural10": "Rural share (per 10 pp)", "rate10": "Death rate (per 10)",
       "pov": "Poverty rate (\\%)", "log_mhi": "Log median household income"}
reg_rows = []
for v in ["log_pop", "rural10", "rate10", "pov", "log_mhi"]:
    cells = []
    for m in ["m1_logit_region", "m2_lpm_state", "m3_fraclogit_region", "m4_logit_rural"]:
        x = R[m][v]; cells.append(f"${x['b']:.3f}{stars(x['p'])}$ ({x['se']:.3f})")
    reg_rows.append(f"{LAB[v]} & " + " & ".join(cells) + " \\\\")
reg_rows.append("\\midrule")
reg_rows.append("Fixed effects & Region & State & Region & Region \\\\")
reg_rows.append(f"Counties & {n(R['n']['m1'])} & {n(R['n']['m2'])} & {n(R['n']['m3'])} & {n(R['n']['m4'])} \\\\")
tabreg = "\n".join(reg_rows)
P = A["pipeline"]
tabpipe = "\n".join([
    f"\\quad Urban counties & {n(P['urban']['n_early_covered'])} & {P['urban']['pct_later_impl_any']:.1f} \\\\",
    f"\\quad Rural counties & {n(P['rural_all']['n_early_covered'])} & {P['rural_all']['pct_later_impl_any']:.1f} \\\\",
    f"\\quad\\quad of which high-fatality rural & {n(P['hf_rural']['n_early_covered'])} & {P['hf_rural']['pct_later_impl_any']:.1f} \\\\",
    "\\multicolumn{3}{l}{\\textit{Early action plan recipients; later implementation grant to the same recipient}} \\\\",
    f"\\quad All recipients & {n(ps['n'])} & {ps['pct_later_impl']:.1f} \\\\",
    f"\\quad Cities & {ps['n_city']} & {ps['pct_city_later_impl']:.1f} \\\\",
    f"\\quad Counties & {ps['n_county']} & {ps['pct_county_later_impl']:.1f} \\\\",
    f"\\quad Regional councils and MPOs & {ps['n_regional_council'] + ps['n_mpo']} & 0.0 \\\\",
    f"\\quad Tribes & {ps['n_tribe']} & {ps['pct_tribe_later_impl']:.1f} \\\\"])
tabdol = "\n".join(f"{GN[k]} & {D[k]['pct_deaths']:.1f} & {D[k]['pct_dollars']:.1f} & {D[k]['per_res']:.2f} & "
                   f"{n(D[k]['per_death'])} & {n(D[k]['plan_per_death'])} & {n(D[k]['impl_per_death'])} \\\\" for k in keys)
RD = A["roads"]
tabroads = "\n".join(
    f"{GN[k]} & {RD[k]['owner']['state']:.1f} & {RD[k]['owner']['county']:.1f} & {RD[k]['owner']['city_town']:.1f} & "
    f"{RD[k]['owner']['federal_tribal']:.1f} & {RD[k]['class']['interstate_fwy']:.1f} & {RD[k]['class']['arterial']:.1f} & "
    f"{RD[k]['class']['collector'] + RD[k]['class']['local']:.1f} \\\\" for k in keys)
SC = A["scan_states"]; SR = A["state_rural_cov_range"]
STN = {"TX": "Texas", "MS": "Mississippi", "GA": "Georgia", "AR": "Arkansas", "CO": "Colorado", "NC": "North Carolina",
       "OK": "Oklahoma", "SD": "South Dakota", "KS": "Kansas", "MT": "Montana", "NE": "Nebraska", "AL": "Alabama"}
hfd = S["deaths_2020_2024_high_fatality_rural"]
lp = R["ame_m1"]["log_pop"]
T = {
    "NAME": AU["name"], "ORCID": AU["orcid"], "EMAIL": AU["email"], "REPO": REPO, "DOI": DOI,
    "DRAFTPKG": "" if args.final else "\\usepackage{draftwatermark}\\SetWatermarkText{DRAFT}\\SetWatermarkScale{1.5}\\SetWatermarkColor[gray]{0.9}",
    "NAWARDS": n(S["n_awards_all"]), "DOLLARSB": f"{S['dollars_all']/1e9:.2f}",
    "POPALL": f"{S['pop_share_in_action_plan_area_all']:.0f}", "POPURB": f"{S['pop_share_in_action_plan_area_urban_counties']:.0f}",
    "POPRUR": f"{S['pop_share_in_action_plan_area_rural_counties']:.0f}",
    "CURB": f"{cov_pct['urban']:.0f}", "CRUR": f"{100*rur_cov/rur_n:.0f}", "CHF": f"{cov_pct['hf_rural']:.0f}", "COTH": f"{cov_pct['other_rural']:.0f}",
    "RATERUR": f"{S['rate_rural_counties']:.1f}", "RATEURB": f"{S['rate_urban_counties']:.1f}",
    "NHF": n(S["n_high_fatality_rural"]), "NGAP": n(S["n_gap_counties"]), "PCTGAP": f"{S['pct_hf_rural_gap']:.0f}",
    "NGAPNONE": n(S["n_gap_counties_not_covered"]), "NGAPPART": n(S["n_gap_counties"] - S["n_gap_counties_not_covered"]),
    "DGAP": n(S["deaths_2020_2024_gap_counties"]), "PCTDGAP": f"{100*S['deaths_2020_2024_gap_counties']/hfd:.0f}",
    "NRULAB": str(int(a.dot_list_correction.fillna("").str.startswith("dot_rural_urban").sum())),
    "NGEOM": str(int(a.geometry_note.notna().sum())),
    "NBG": n(sum(1 for _ in open(os.path.join(RAW, "CenPop2020_Mean_BG.txt"), encoding="utf-8-sig")) - 1),
    "NOVR": str(len(pd.read_csv(os.path.join(ROOT, "code", "recipient_overrides.csv")))),
    "NFLAG": str(S["n_action_plan_awards_area_flag"]), "NRUR": n(S["n_rural_counties"]), "NCTY": n(S["n_counties"]),
    "MIND": str(S["min_deaths"]), "THR": f"{S['high_fatality_rate_threshold']:.1f}",
    "NAP": n(S["n_action_plan_awards_all"]), "NAPRB": n(S["n_ap_regional_all"]),
    "AP22": n(S["by_fy"][0]["n_ap"]), "AP26": n(S["by_fy"][-1]["n_ap"]), "RB22": str(rb[0]), "RB26": str(rb[-1]),
    "TESTRU": f"$\\chi^2_1={chi_ru[0]:.1f}$, {ptxt(chi_ru[1])}", "TESTHF": f"$\\chi^2_1={chi_hf[0]:.2f}$, {ptxt(chi_hf[1])}",
    "RHO": f"{rho:.2f}", "NSTGAP": str(S["n_states_with_gap"]),
    "TOPSTATES": ", ".join(f"{STN.get(s, s)} ({k})" for s, k in S["states_most_gap_counties"]),
    "NGAPCONS": n(S["n_gap_counties_conservative"]), "NGAP2225": n(S["n_gap_counties_fy22_25"]),
    "NGAPNB": n(S["n_gap_with_neighbor_regional_body"]),
    "NNOBG": str(int(a.geo_match_flag.fillna("").str.startswith("no 2020").sum())),
    "GAP22": f"{A['urban_rural_gap_pp']['2022']:.0f}", "GAP26": f"{A['urban_rural_gap_pp']['2026']:.0f}",
    "R22U": f"{r22['urban']['pct_counties_covered']:.0f}", "R22O": f"{r22['other_rural']['pct_counties_covered']:.0f}",
    "R22H": f"{r22['hf_rural']['pct_counties_covered']:.0f}", "R26U": f"{r26['urban']['pct_counties_covered']:.0f}",
    "R26O": f"{r26['other_rural']['pct_counties_covered']:.0f}", "R26H": f"{r26['hf_rural']['pct_counties_covered']:.0f}",
    "PCTDGAPALL": f"{D['gap']['pct_deaths']:.1f}", "PCTDOLGAP": f"{D['gap']['pct_dollars']:.1f}",
    "PIPEURB": f"{P['urban']['pct_later_impl_any']:.0f}", "PIPERUR": f"{P['rural_all']['pct_later_impl_any']:.0f}",
    "PIPEHF": f"{P['hf_rural']['pct_later_impl_any']:.0f}", "PIPENU": n(P["urban"]["n_early_covered"]),
    "PIPENR": n(P["rural_all"]["n_early_covered"]), "PIPENH": n(P["hf_rural"]["n_early_covered"]),
    "PIPEREC": f"{ps['pct_later_impl']:.1f}", "PIPERECN": n(ps["n"]),
    "PIPETEST": f"{ps['pct_rural_later_impl']:.1f}\\% against {ps['pct_urban_later_impl']:.1f}\\%; $\\chi^2_1={ps['chi2']:.2f}$, {ptxt(ps['p'])}",
    "OWNSTGAP": f"{RD['gap']['owner']['state']:.0f}", "OWNSTURB": f"{RD['urban']['owner']['state']:.0f}",
    "OWNLOCGAP": f"{RD['gap']['owner']['county'] + RD['gap']['owner']['city_town']:.0f}",
    "CLSACGAP": f"{RD['gap']['class']['arterial'] + RD['gap']['class']['collector']:.0f}",
    "AMERUR": f"{-100*R['ame_m1']['rural10']:.1f}", "PRUR1": ptxt(R["m1_logit_region"]["rural10"]["p"]),
    "AMEPOP2": f"{100*lp*np.log(2):.1f}", "PRATE2": ptxt(R["m2_lpm_state"]["rate10"]["p"]),
    "STATER2": f"{100*A['state_r2_rural']:.0f}",
    "PCTDOLURB": f"{D['urban']['pct_dollars']:.0f}", "PCTDURB": f"{D['urban']['pct_deaths']:.0f}",
    "PCTDOLHF": f"{D['hf_rural']['pct_dollars']:.1f}", "PCTDHF": f"{D['hf_rural']['pct_deaths']:.1f}",
    "DPDURB": money(D["urban"]["per_death"]), "DPDHF": money(D["hf_rural"]["per_death"]), "DPDGAP": money(D["gap"]["per_death"]),
    "DPRMIN": f"\\${min(D[k]['per_res'] for k in ['urban','other_rural','hf_rural']):.0f}",
    "DPRMAX": f"\\${max(D[k]['per_res'] for k in ['urban','other_rural','hf_rural']):.0f}",
    "MORAN": f"{A['moran_share']['I']:.2f}", "MORANP": f"{A['moran_share']['p_sim']:.3f}",
    "MORANGAP": f"{A['moran_gap']['I']:.2f}", "MORANGAPP": f"{A['moran_gap']['p_sim']:.3f}",
    "LISALL": n(A["lisa"].get("LL", 0)), "LISALLRUR": f"{A['lisa_ll_rural_pct']:.0f}", "PCTGAPLL": f"{A['pct_gap_in_ll']:.0f}",
    "STMIN": f"{SR['min']:.0f}", "STMAX": f"{SR['max']:.0f}", "STZERO": str(SR["n_states_zero"]),
    "STIQR": f"{SR['iqr'][0]:.0f} to {SR['iqr'][1]:.0f}\\%",
    "SCANCOV": f"{SC['rural_covered_scan']:.0f}", "SCANOTH": f"{SC['rural_covered_other']:.0f}",
    "SCANTEST": f"$\\chi^2_1={SC['chi2']:.1f}$, {ptxt(SC['p'])}",
    "SCANGAP": f"{SC['hf_gap_pct_scan']:.0f}", "SCANGAPO": f"{SC['hf_gap_pct_other']:.0f}",
    "REGN": n(A["reg_n"]),
    "TABFY": tabfy, "TABCOV": tabcov, "TABTOP": tabtop, "TOPNOTE": topnote, "TABREG": tabreg, "TABPIPE": tabpipe,
    "TABDOL": tabdol, "TABROADS": tabroads,
}
json.dump({k: v for k, v in T.items() if not k.startswith("TAB") and k != "TOPNOTE"}, open(os.path.join(ROOT, "data", "interim", "paper_tokens.json"), "w"), indent=0)
assert A["reg_dropped"] == 9, "Methods text says eight Connecticut counties and Kalawao County are omitted"
src = open(os.path.join(ROOT, "code", "paper_template.tex")).read()
for _ in range(2):
    for k, v in T.items():
        src = src.replace(f"<<{k}>>", v)
left = re.findall(r"<<[A-Z0-9]+>>", src)
assert not left, left
open(os.path.join(OUT, "main.tex"), "w").write(src)
for _ in range(3):
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=OUT, capture_output=True, text=True)
if r.returncode != 0 or not os.path.exists(os.path.join(OUT, "main.pdf")):
    print(r.stdout[-3000:]); raise SystemExit("pdflatex failed")
for ext in ["aux", "out", "blg", "bbl"]:
    p = os.path.join(OUT, f"main.{ext}")
    if os.path.exists(p):
        os.remove(p)
print("article written:", os.path.join(OUT, "main.pdf"), "(final)" if args.final else "(DRAFT)")
