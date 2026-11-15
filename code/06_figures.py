#!/usr/bin/env python3
"""06_figures.py: draw the report figures from the processed tables.

Plain-language summary: makes three pictures in report/figures/: (1) a map of
rural counties by safety action plan coverage, with high-fatality rural counties
that lack a plan shown in orange; (2) a bar chart comparing coverage for urban
counties, other rural counties and high-fatality rural counties; (3) the states
with the most high-fatality rural counties lacking a plan. Every figure says
DRAFT until you run this script with --final after your review.

Colors: covered #1c5cab, partly covered #86b6ef (ordinal blue ramp, validated),
not covered neutral gray #d3d2cd, gap counties orange #eb6834 (validated against
the dark blue, CVD and normal-vision separation pass). Urban counties are drawn in
a pale neutral so the rural pattern reads first.
"""
import json, os, sys
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

FINAL = "--final" in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw"); PROC = os.path.join(ROOT, "data", "processed")
FIG = os.path.join(ROOT, "report", "figures"); os.makedirs(FIG, exist_ok=True)
S = json.load(open(os.path.join(ROOT, "report", "stats.json")))
C_COV, C_PART, C_NONE, C_GAP, C_URB = "#1c5cab", "#86b6ef", "#d3d2cd", "#eb6834", "#f3f2ee"
INK, INK2, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})
SRC = ("Sources: U.S. DOT SS4A award map layers FY2022-FY2026 (accessed Nov. 2026); Census 2020; "
       "U.S. Rural Road Fatality County Panel v1.0.0 (FARS 2020-2024).")


def stamp(fig):
    if not FINAL:
        fig.text(0.99, 1.04, "DRAFT", ha="right", va="top", fontsize=14, color="#b42318", weight="bold")


g = pd.read_csv(os.path.join(PROC, "county_coverage_gap_table.csv"), dtype={"fips": str})

# ---- Figure 1: map ----
c = gpd.read_file("zip://" + os.path.join(RAW, "cb_2020_us_county_500k.zip"))
c = c[~c.STATEFP.isin(["02", "15", "60", "66", "69", "72", "78"])].merge(g, left_on="GEOID", right_on="fips")
c = c.to_crs(5070)


def cls(r):
    if not r.rural_county:
        return "urban"
    if r.gap_flag:
        return "gap"
    return {"covered": "cov", "partly covered": "part", "not covered": "none"}[r.coverage_status]


c["cls"] = c.apply(cls, axis=1)
col = {"urban": C_URB, "cov": C_COV, "part": C_PART, "none": C_NONE, "gap": C_GAP}
fig, ax = plt.subplots(figsize=(11, 7))
for k in ["urban", "none", "part", "cov", "gap"]:
    sub = c[c.cls == k]
    sub.plot(ax=ax, color=col[k], edgecolor=SURF, linewidth=0.15)
st = c.dissolve("STATEFP")
st.boundary.plot(ax=ax, color="#ffffff", linewidth=0.6)
ax.set_axis_off()
n = S["n_high_fatality_rural"]; gap = S["n_gap_counties"]
ax.set_title(f"{gap} of {n} high-fatality rural counties have no funded safety action plan for most residents",
             loc="left", fontsize=13, weight="bold", pad=24)
ax.text(0, 1.015, "Rural counties by share of 2020 residents inside an SS4A action plan award area, FY2022-FY2026. "
        "Contiguous U.S. shown; Alaska and Hawaii are in the table.", transform=ax.transAxes, fontsize=9, color=INK2)
labels = [(C_GAP, f"High-fatality rural, under half covered ({gap})"),
          (C_COV, "Rural, half or more covered"), (C_PART, "Rural, partly covered (under half)"),
          (C_NONE, "Rural, not covered"), (C_URB, "Urban county (not classed)")]
hs = [plt.Rectangle((0, 0), 1, 1, fc=k, ec="#9a9994", lw=0.4) for k, _ in labels]
ax.legend(hs, [l for _, l in labels], loc="lower left", frameon=False, fontsize=9, bbox_to_anchor=(0, -0.02))
fig.text(0.01, 0.01, SRC + f" High-fatality = top quarter of rural counties by deaths per 100,000 residents per "
         f"year (at least {S['high_fatality_rate_threshold']}), among those with {S['min_deaths']}+ deaths.",
         fontsize=7, color=INK2, wrap=True)
stamp(fig)
fig.savefig(os.path.join(FIG, "fig1_map_rural_coverage.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ---- Figure 2: coverage by county group ----
g["group"] = g.apply(lambda r: "High-fatality rural" if r.high_fatality_rural else
                     ("Other rural" if r.rural_county else "Urban"), axis=1)
order = ["Urban", "Other rural", "High-fatality rural"]
t = pd.crosstab(g.group, g.coverage_status, normalize="index").reindex(order)[
    ["covered", "partly covered", "not covered"]] * 100
cnt = g.group.value_counts().reindex(order)
fig, ax = plt.subplots(figsize=(9, 3.4))
left = pd.Series(0.0, index=order)
for k, colr in [("covered", C_COV), ("partly covered", C_PART), ("not covered", C_NONE)]:
    ax.barh(order, t[k], left=left, color=colr, edgecolor=SURF, linewidth=2, height=0.55, label=k.capitalize())
    for i, gname in enumerate(order):
        v = t.loc[gname, k]
        if v >= 7:
            ax.text(left[gname] + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9,
                    color="#ffffff" if k == "covered" else INK)
    left += t[k]
ax.set_yticks(range(3)); ax.set_yticklabels([f"{o}\n({cnt[o]:,} counties)" for o in order])
ax.set_xlim(0, 100); ax.set_xlabel("Percent of counties")
for s_ in ["top", "right", "left"]:
    ax.spines[s_].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.legend(ncol=3, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=9)
ax.set_title("Funded action plan coverage, by county group (half or more of residents = covered)",
             loc="left", fontsize=11, weight="bold", pad=30)
fig.text(0.01, -0.06, SRC, fontsize=7, color=INK2)
stamp(fig)
fig.savefig(os.path.join(FIG, "fig2_coverage_by_group.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ---- Figure 3: states with most gap counties ----
s = pd.read_csv(os.path.join(PROC, "state_coverage_summary.csv"))
s = s[s.high_fatality_rural_gap > 0].sort_values(["high_fatality_rural_gap", "state"], ascending=[True, False]).tail(12)
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.barh(s.state, s.high_fatality_rural_gap, color=C_GAP, height=0.6, edgecolor=SURF, linewidth=2)
for i, (v, hf) in enumerate(zip(s.high_fatality_rural_gap, s.high_fatality_rural)):
    ax.text(v + 0.4, i, f"{v} of {hf}", va="center", fontsize=8.5, color=INK2)
for s_ in ["top", "right", "left"]:
    ax.spines[s_].set_visible(False)
ax.tick_params(axis="y", length=0); ax.set_xlabel("High-fatality rural counties under half covered")
ax.xaxis.grid(True, color="#e6e5e0", lw=0.6); ax.set_axisbelow(True)
ax.set_title("States with the most high-fatality rural counties lacking a funded plan",
             loc="left", fontsize=11, weight="bold", pad=20)
ax.text(0, 1.01, "Label: gap counties of all high-fatality rural counties in the state", transform=ax.transAxes,
        fontsize=8.5, color=INK2)
fig.text(0.01, -0.03, SRC, fontsize=7, color=INK2)
stamp(fig)
fig.savefig(os.path.join(FIG, "fig3_states_gap_counties.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("figures written", "(final)" if FINAL else "(DRAFT)")
