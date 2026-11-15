#!/usr/bin/env python3
"""03_match.py: find which counties and places each award covers.

Plain-language summary: DOT gives a map shape for the area each award covers.
This script lays those shapes over 2020 Census maps. It counts how many people
live inside each award area (using the 2020 Census population centers of about
240,000 block groups, the small neighborhoods the Census uses), lists the
counties and Census places (cities, towns and unincorporated communities) each
award touches, and then works out, for every county, what share of its people
live inside at least one funded safety action plan area. You do not need to open
this file. Outputs go to data/processed/.

Method notes (technical):
* A block group counts as inside an award area when its 2020 population center
  falls inside the award polygon (EPSG:4326 point-in-polygon).
* A place is listed for an award when at least 50 percent of the place's land
  area (EPSG:5070) lies inside the award polygon.
* Award polygons containing no block-group center (small corridors, small
  tribal areas) are assigned to the county containing the polygon's
  representative point and flagged.
"""
import os
import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw"); INT = os.path.join(ROOT, "data", "interim")
PROC = os.path.join(ROOT, "data", "processed")

aw = gpd.read_file(os.path.join(INT, "awards.gpkg"))
bg = pd.read_csv(os.path.join(RAW, "CenPop2020_Mean_BG.txt"), dtype={"STATEFP": str, "COUNTYFP": str,
                 "TRACTCE": str, "BLKGRPCE": str}, encoding="utf-8-sig")
bg["bg_geoid"] = bg.STATEFP + bg.COUNTYFP + bg.TRACTCE + bg.BLKGRPCE
bg["fips"] = bg.STATEFP + bg.COUNTYFP
bgp = gpd.GeoDataFrame(bg[["bg_geoid", "fips", "POPULATION"]],
                       geometry=gpd.points_from_xy(bg.LONGITUDE, bg.LATITUDE), crs=4326)
cnty = gpd.read_file("zip://" + os.path.join(RAW, "cb_2020_us_county_500k.zip")).to_crs(4326)
cnty = cnty.rename(columns={"GEOID": "fips"})
cpop = bg.groupby("fips").POPULATION.sum().rename("county_pop2020")

# ---- block groups inside each award ----
pairs = gpd.sjoin(bgp, aw[["award_id", "geometry"]], how="inner", predicate="within")[
    ["bg_geoid", "fips", "POPULATION", "award_id"]]
pairs.to_csv(os.path.join(INT, "bg_award_pairs.csv.gz"), index=False)

# ---- award to county crosswalk ----
ac = pairs.groupby(["award_id", "fips"]).agg(pop_in_award=("POPULATION", "sum"),
                                             n_block_groups=("bg_geoid", "size")).reset_index()
apop = ac.groupby("award_id").pop_in_award.sum().rename("census_pop_in_area")
ac = ac.join(apop, on="award_id").join(cpop, on="fips")
ac["share_of_award_pop"] = (ac.pop_in_award / ac.census_pop_in_area).round(4)
ac["share_of_county_pop"] = (ac.pop_in_award / ac.county_pop2020).round(4)
ac["assignment"] = "block-group centers"

missing = aw[~aw.award_id.isin(ac.award_id) & aw.geometry.notna()].copy()
if len(missing):
    rp = missing[["award_id", "geometry"]].copy()
    rp["geometry"] = missing.to_crs(5070).geometry.representative_point().to_crs(4326)
    fb = gpd.sjoin(rp, cnty[["fips", "geometry"]], how="left", predicate="within")[["award_id", "fips"]]
    fb = fb.join(cpop, on="fips")
    fb["pop_in_award"] = 0; fb["n_block_groups"] = 0; fb["census_pop_in_area"] = 0
    fb["share_of_award_pop"] = np.nan; fb["share_of_county_pop"] = 0.0
    fb["assignment"] = "no block-group center inside; county from representative point"
    ac = pd.concat([ac, fb], ignore_index=True)
names = cnty.set_index("fips")[["NAMELSAD", "STUSPS"]]
ac = ac.join(names, on="fips").rename(columns={"NAMELSAD": "county_name", "STUSPS": "county_state"})
ac = ac.sort_values(["award_id", "pop_in_award"], ascending=[True, False])
ac.to_csv(os.path.join(PROC, "award_county_crosswalk.csv"), index=False)

# ---- award to place crosswalk ----
pl = gpd.read_file("zip://" + os.path.join(RAW, "cb_2020_us_place_500k.zip")).to_crs(5070)
pl = pl[["GEOID", "NAMELSAD", "STUSPS", "LSAD", "geometry"]].rename(columns={"GEOID": "place_geoid",
                                                                              "NAMELSAD": "place_name"})
pl["place_area"] = pl.area
aw5 = aw[["award_id", "geometry"]].to_crs(5070)
cand = gpd.sjoin(pl, aw5, how="inner", predicate="intersects")
geo_a = aw5.set_index("award_id").geometry
inter = [p.intersection(geo_a[a]).area for p, a in zip(cand.geometry, cand.award_id)]
cand["share_of_place_in_award"] = (np.array(inter) / cand.place_area).round(4)
apl = cand[cand.share_of_place_in_award >= 0.5][["award_id", "place_geoid", "place_name", "STUSPS", "LSAD",
                                                  "share_of_place_in_award"]].rename(columns={"STUSPS": "place_state"})
apl = apl.sort_values(["award_id", "place_geoid"])
apl.to_csv(os.path.join(PROC, "award_place_crosswalk.csv"), index=False)

# ---- award-level summary columns ----
top = ac.drop_duplicates("award_id").set_index("award_id")
summ = pd.DataFrame(index=aw.award_id)
summ["census_pop_in_area"] = apop.reindex(summ.index).fillna(0).astype(int)
summ["n_counties"] = ac.groupby("award_id").fips.nunique().reindex(summ.index)
summ["primary_county_fips"] = top.fips.reindex(summ.index)
summ["primary_county_name"] = (top.county_name + ", " + top.county_state).reindex(summ.index)
summ["county_fips_list"] = ac.groupby("award_id").fips.apply(lambda s: ";".join(s.dropna())).reindex(summ.index)
summ["n_places"] = apl.groupby("award_id").size().reindex(summ.index).fillna(0).astype(int)
# primary place for city and town recipients: the matched place with the largest land area inside the award
if len(apl):
    big = cand[cand.share_of_place_in_award >= 0.5].copy()
    big["a"] = big.place_area * big.share_of_place_in_award
    pp = big.sort_values("a", ascending=False).drop_duplicates("award_id").set_index("award_id")
    summ["primary_place_geoid"] = pp.place_geoid.reindex(summ.index)
    summ["primary_place_name"] = (pp.place_name + ", " + pp.STUSPS).reindex(summ.index)
nogeom = set(aw.loc[aw.geometry.isna(), "award_id"])
summ["geo_match_flag"] = np.where(summ.index.isin(nogeom), "not on DOT map layer; no award area",
                                  np.where(summ.census_pop_in_area.eq(0),
                                           "no 2020 block-group center inside award area", ""))
_a = pd.read_csv(os.path.join(INT, "awards_coded.csv")).set_index("award_id")
summ["area_pop_ratio"] = (summ.census_pop_in_area / _a.dot_jurisdiction_pop.where(_a.dot_jurisdiction_pop > 0)
                          .reindex(summ.index)).round(2)
# Mapped area holds more than twice the residents DOT reported: the shape may be larger than the plan.
summ["area_may_overstate_plan"] = summ.area_pop_ratio > 2
summ.reset_index().to_csv(os.path.join(INT, "award_geo_summary.csv"), index=False)

# ---- county coverage ----
attrs = pd.read_csv(os.path.join(INT, "awards_coded.csv"))
ap_ids = set(attrs.loc[attrs.includes_action_plan, "award_id"])
core_ids = set(attrs.loc[attrs.in_core_fy2022_2025, "award_id"])
rb_ids = set(attrs.loc[attrs.is_regional_body, "award_id"])
fy = attrs.set_index("award_id").fiscal_year


def covered(ids):
    s = pairs[pairs.award_id.isin(ids)].drop_duplicates("bg_geoid")
    return s.groupby("fips").POPULATION.sum()


cov = pd.DataFrame(index=cpop.index); cov["county_pop2020"] = cpop
cov["pop_in_action_plan_area_fy22_26"] = covered(ap_ids)
cov["pop_in_action_plan_area_fy22_25"] = covered(ap_ids & core_ids)
cov["pop_in_any_ss4a_area_fy22_26"] = covered(set(attrs.award_id))
cov["pop_in_any_ss4a_area_fy22_25"] = covered(core_ids)
cov["pop_in_regional_body_action_plan_fy22_26"] = covered(ap_ids & rb_ids)
over = set(summ.index[summ.area_may_overstate_plan.fillna(False)])
cov["pop_in_action_plan_area_conservative_fy22_26"] = covered(ap_ids - over)
cov = cov.fillna(0)
for c in [c for c in cov.columns if c.startswith("pop_in_")]:
    cov["share_" + c[7:]] = (cov[c] / cov.county_pop2020).round(4)
# first fiscal year in which the county reached 50 percent action-plan coverage
first = {}
for y in [2022, 2023, 2024, 2025, 2026]:
    s = covered({a for a in ap_ids if fy[a] <= y}) / cpop
    for f in s[s >= 0.5].index:
        first.setdefault(f, y)
cov["first_fy_action_plan_majority"] = pd.Series(first)
# which awards and which regional bodies reach each county (any population share)
acs = ac[ac.share_of_county_pop.fillna(0) > 0].merge(
    attrs[["award_id", "recipient_name", "fiscal_year", "includes_action_plan", "is_regional_body"]], on="award_id")
apl_c = acs[acs.includes_action_plan]
cov["n_action_plan_awards_touching"] = apl_c.groupby("fips").award_id.nunique()
cov["action_plan_award_ids"] = apl_c.groupby("fips").award_id.apply(lambda s: ";".join(sorted(s)))
cov["action_plan_recipients"] = apl_c.groupby("fips").recipient_name.apply(lambda s: "; ".join(sorted(set(s))))
rbs = apl_c[apl_c.is_regional_body]
cov["regional_body_action_plan_recipients"] = rbs.groupby("fips").recipient_name.apply(lambda s: "; ".join(sorted(set(s))))
cov["n_any_ss4a_awards_touching"] = acs.groupby("fips").award_id.nunique()
cov.index.name = "fips"
cov.reset_index().to_csv(os.path.join(INT, "county_coverage.csv"), index=False)
print("pairs", len(pairs), "awards matched", ac.award_id.nunique(), "of", len(aw),
      "fallback", len(missing), "place rows", len(apl))
print(cov[["share_action_plan_area_fy22_26", "share_any_ss4a_area_fy22_26"]].describe())
