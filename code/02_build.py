#!/usr/bin/env python3
"""02_build.py: combine every SS4A award into one table and code it.

Plain-language summary: this script reads the raw DOT award layers saved by
01_fetch.py, puts every award (fiscal years 2022 to 2026) into one table with the
same column names, and codes two things for each award: what kind of recipient it
is (city, county, tribe, regional council, metropolitan planning organization,
other) and what the money pays for (action plan, supplemental planning,
demonstration, implementation). It writes data/processed/awards_attributes.csv
(one row per award, no map shapes) and data/interim/awards.gpkg (with shapes).
You do not need to open this file. The rules it applies are listed in
docs/CODING_RULES.md, and every award where a rule was overridden by hand is in
code/recipient_overrides.csv.
"""
import glob, os, re
import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
INT = os.path.join(ROOT, "data", "interim")
PROC = os.path.join(ROOT, "data", "processed")
os.makedirs(INT, exist_ok=True); os.makedirs(PROC, exist_ok=True)

# ---------- 1. read and harmonize ----------------------------------------------------------
SRC = {
    2022: ["ss4a_fy2022_crosscheck_ACTION_PLAN_IMPLEMENTATION_GRANTS_MERGE.geojson"],
    2023: ["ss4a_fy2023_planning_FY23_PDG_FinalAwards_ALL.geojson",
           "ss4a_fy2023_implementation_FY23_IG_FinalAwards.geojson"],
    2024: ["ss4a_fy2024_planning_FY24_PDG_FinalAwards_ALL.geojson",
           "ss4a_fy2024_implementation_FY24_IG_FinalAwards.geojson"],
    2025: ["ss4a_fy2025_all_SS4A_FY25_Jurisdiction_Areas_Final_Updated_12_16_2025.geojson"],
    2026: ["ss4a_fy2026_all_SS4A_FY26_Jurisdictions_Final.geojson"],
}


def col(g, *names, default=np.nan):
    for n in names:
        if n in g.columns:
            return g[n]
    return pd.Series(default, index=g.index)


def clean(s):
    return s.astype("string").str.replace(r"\s+", " ", regex=True).str.strip().str.strip(",").str.strip()


frames = []
for fy, files in SRC.items():
    for fn in files:
        g = gpd.read_file(os.path.join(RAW, fn)).to_crs(4326)
        svc = fn.split("_", 3)[3].replace(".geojson", "")
        d = gpd.GeoDataFrame({
            "fiscal_year": fy,
            "source_layer": svc,
            "source_objectid": col(g, "OBJECTID"),
            "dot_award_id": col(g, "SS4A_ID"),
            "uei": col(g, "UEI", "SAMUEI"),
            "recipient_name": clean(col(g, "Lead_Applicant", "Organization_Name")),
            "state_reported": clean(col(g, "State", "Primary_State")),
            "dot_recipient_type": clean(col(g, "APPLICANT_TYPE", "Applicant_Type", "Entity_Type")),
            "dot_rural_urban": clean(col(g, "Rural__Urban", "Rural_Urban", "Land_Use")),
            "dot_grant_program": clean(col(g, "GRANT_TYPE", "Grant_Type")),
            "dot_activity": clean(col(g, "AP_Type_of_Plan", "Application_Type", "Activity_Type")),
            "dot_pd_detail": clean(col(g, "PD_Type")),
            "dot_round": clean(col(g, "FY23_Round", "FY24_Round", "Award_Round").astype("string")),
            "project_name": clean(col(g, "Project_Name", "AP_Project_Title")),
            "federal_funding": pd.to_numeric(col(g, "Total_Federal_Funding", "Federal_Request__SF_"), errors="coerce"),
            "total_project_cost": pd.to_numeric(col(g, "Total_Project_Cost"), errors="coerce"),
            "action_plan_amount": pd.to_numeric(col(g, "Activity_A_Amount"), errors="coerce"),
            "dot_jurisdiction_pop": pd.to_numeric(col(g, "Jurisdiction_Population", "Population",
                                                      "Total_Jurisdiction_Population"), errors="coerce"),
        }, geometry=g.geometry, crs=4326)
        frames.append(d)
# Awards on DOT's official FY2022 list but missing from the FY2022 map layer (no map shape)
sup = pd.read_csv(os.path.join(ROOT, "code", "fy2022_awards_not_on_map.csv"), dtype={"uei": str})
sup = sup.assign(source_layer="FY22-SS4A-Full-Award-List-March2025 (not on map layer)", source_objectid=pd.NA,
                 dot_award_id=pd.NA, dot_pd_detail=pd.NA, dot_round=pd.NA, project_name=pd.NA,
                 action_plan_amount=np.nan, dot_jurisdiction_pop=np.nan).rename(columns={"state": "state_reported"})
frames.append(gpd.GeoDataFrame(sup.drop(columns="source"), geometry=gpd.GeoSeries([None] * len(sup), crs=4326),
                               crs=4326))
aw = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326)
has_geom = aw.geometry.notna()
aw.loc[has_geom, "geometry"] = aw.loc[has_geom, "geometry"].make_valid()
# Map shapes replaced with Census boundaries where DOT's map layer draws the wrong place
gc = pd.read_csv(os.path.join(ROOT, "code", "geometry_corrections.csv"), dtype=str)
CEN = {"place": ("cb_2020_us_place_500k.zip", "GEOID"), "county": ("cb_2020_us_county_500k.zip", "GEOID"),
       "cousub": ("cb_2020_33_cousub_500k.zip", "GEOID")}
aw["geometry_note"] = pd.Series(pd.NA, index=aw.index, dtype="string")
for _, c in gc.iterrows():
    f, key = CEN[c.census_layer]
    shp = gpd.read_file("zip://" + os.path.join(RAW, f)).to_crs(4326)
    geom = shp.loc[shp[key] == c.census_geoid, "geometry"].iloc[0]
    m = aw.fiscal_year.eq(int(c.fiscal_year)) & aw.recipient_name.eq(c.uei_or_name) & aw.state_reported.eq(c.state)
    assert m.sum() == 1, c.uei_or_name
    aw.loc[m, "geometry"] = geom
    aw.loc[m, "geometry_note"] = f"shape replaced with Census 2020 {c.census_layer} {c.census_geoid}: {c.reason}"
# Corrections from DOT's official award lists where the map layer disagrees
cor = pd.read_csv(os.path.join(ROOT, "code", "dot_list_corrections.csv"), dtype=str)
aw["dot_list_correction"] = pd.Series(pd.NA, index=aw.index, dtype="string")
for _, c in cor.iterrows():
    m = aw.fiscal_year.eq(int(c.fiscal_year)) & aw.uei.eq(c.uei)
    aw.loc[m, c.field] = c.corrected_value
    aw.loc[m, "dot_list_correction"] = f"{c.field}: map layer {c.map_layer_value} -> {c.corrected_value} (DOT award list)"

# FY2022 program name: DOT called the planning track "Action Plan Grants" that year.
prog = aw.dot_grant_program.str.lower()
aw["grant_program"] = np.where(prog.str.contains("implement"), "Implementation", "Planning and Demonstration")
# FY2026 rural/urban labels: the map layer marks all implementation awards Rural; DOT's award list does not
rl = pd.read_csv(os.path.join(ROOT, "code", "fy2026_rural_label_corrections.csv"))
for _, c in rl.iterrows():
    m = (aw.fiscal_year.eq(c.fiscal_year) & aw.state_reported.eq(c.state) & aw.grant_program.eq("Implementation")
         & (aw.federal_funding - c.federal_funding).abs().lt(1))
    assert m.sum() == 1, c.dot_list_name
    aw.loc[m, "dot_rural_urban"] = c.dot_rural_urban
    aw.loc[m, "dot_list_correction"] = "dot_rural_urban: map layer Rural -> Urban (DOT award list)"

# ---------- 2. grant type ------------------------------------------------------------------
act = aw.dot_activity.fillna("").str.lower()
pdd = aw.dot_pd_detail.fillna("").str.lower()
is_ig = aw.grant_program.eq("Implementation")
has_pd_detail = pdd.str.contains("action plan|supplemental|demonstration")

ap_from_act = act.str.contains("action plan") & ~act.str.startswith("conduct demonstration")
ap_from_act |= act.str.startswith("update/add")
aw["includes_action_plan"] = np.where(has_pd_detail, pdd.str.contains("new action plan"), ap_from_act & ~is_ig)
aw["action_plan_is_update"] = act.str.startswith("update/add") | act.str.contains("develop or update")
aw.loc[~aw.includes_action_plan, "action_plan_is_update"] = False
sd_from_act = act.str.contains("supplemental|demonstration")
aw["includes_supp_or_demo"] = np.where(has_pd_detail, pdd.str.contains("supplemental|demonstration"), sd_from_act)
# Separate supplemental and demonstration flags exist only where DOT reported them (FY2022, FY2024).
aw["includes_supplemental"] = pd.Series(pd.NA, index=aw.index, dtype="boolean")
aw["includes_demonstration"] = pd.Series(pd.NA, index=aw.index, dtype="boolean")
m = has_pd_detail
aw.loc[m, "includes_supplemental"] = pdd[m].str.contains("supplemental")
aw.loc[m, "includes_demonstration"] = pdd[m].str.contains("demonstration")
m22 = aw.fiscal_year.eq(2022) & ~is_ig
aw.loc[m22, "includes_supplemental"] = act[m22].str.contains("supplemental")
aw.loc[m22, "includes_demonstration"] = False
aw.loc[m22, "includes_action_plan"] = act[m22].str.contains("action plan")
aw.loc[m22, "includes_supp_or_demo"] = act[m22].str.contains("supplemental")
aw["includes_implementation"] = is_ig


def gtype(r):
    if r.includes_implementation:
        return "implementation"
    if r.includes_action_plan and r.includes_supp_or_demo:
        return "action plan + supplemental/demonstration"
    if r.includes_action_plan:
        return "action plan"
    return "supplemental/demonstration only"


aw["grant_type"] = aw.apply(gtype, axis=1)

# ---------- 3. recipient type --------------------------------------------------------------
MPO_RE = re.compile(r"metropolitan planning|metropolitan area planning|\bmpo\b|\btpo\b|\bapo\b|"
                    r"transportation planning organization|transportation study|metropolitan council|"
                    r"metropolitan interstate|area transportation|metropolitan transportation commission|"
                    r"metroplan|area planning agency|urban area metropolitan", re.I)
RC_RE = re.compile(r"council of (local )?governments|\bcog\b|regional council|regional commission|"
                   r"regional planning|planning commission|planning district|development district|"
                   r"development commission|planning (and|&) development|association of governments|"
                   r"area council|intergovernmental|coordinating council|economic development district|"
                   r"planning council|planning board|development association|rural planning organization|"
                   r"regional planning organization|economic and community development|development agency|"
                   r"area development|planning organization", re.I)
CITY_RE = re.compile(r"^(city|town|village|township|borough|inc\.? village|incorporated village|municipality)\b|"
                     r"\b(city|town|village|township|borough)$", re.I)


def rtype(r):
    t = (r.dot_recipient_type or "").lower()
    n = r.recipient_name or ""
    if "tribal" in t:
        return "tribe", "DOT type"
    if "metropolitan planning organization" in t:
        return "mpo", "DOT type"
    if MPO_RE.search(n):
        return "mpo", "name rule"
    if RC_RE.search(n) and not re.search(r"\bcounty planning (commission|department)\b", n, re.I):
        return "regional_council", "name rule"
    if t.startswith("city or township"):
        return "city", "DOT type"
    if t.startswith("county"):
        return "county", "DOT type"
    if t.startswith("regional organization"):
        return ("city", "name rule") if CITY_RE.search(n) else ("regional_council", "DOT type")
    return "other", "DOT type"


def other_sub(r):
    if r.recipient_type != "other":
        return pd.NA
    t = (r.dot_recipient_type or "").lower(); n = (r.recipient_name or "").lower()
    if "higher education" in t or re.search(r"universit|college|regents|board of trustees", n):
        return "university"
    if re.search(r"ems|ambulance|fire|emergency|rescue|hospital|health|trauma|medical", n):
        return "emergency services or health"
    if re.search(r"transit|transportation (authority|commission|agency|council|district)|rail|thruway|airport|port of|mobility authority", n):
        return "transportation agency"
    if re.search(r"school", n):
        return "school district"
    if CITY_RE.search(n) or re.search(r"consolidated government|city and county", n):
        return "city or consolidated government"
    if re.search(r"county", n):
        return "county agency or county group"
    if "state government" in t:
        return "state agency"
    if re.search(r"district|authority|management", n):
        return "special district"
    return "other"


rt = aw.apply(rtype, axis=1, result_type="expand")
aw["recipient_type"], aw["recipient_type_basis"] = rt[0], rt[1]

ov = pd.read_csv(os.path.join(ROOT, "code", "recipient_overrides.csv"), dtype=str)
for _, o in ov.iterrows():
    m = aw.recipient_name.str.lower().eq(o.recipient_name.lower())
    aw.loc[m, "recipient_type"] = o.recipient_type
    aw.loc[m, "recipient_type_basis"] = "manual override: " + o.reason
aw["recipient_subtype"] = aw.apply(other_sub, axis=1)
# Many MPOs are housed in regional councils, so DOT's label for the same body can differ by year.
aw["is_regional_body"] = aw.recipient_type.isin(["mpo", "regional_council"])

# ---------- 4. ids, state, order -----------------------------------------------------------
cnty = gpd.read_file("zip://" + os.path.join(RAW, "cb_2020_us_county_500k.zip")).to_crs(4326)
st = cnty.dissolve("STUSPS")[["geometry"]].reset_index() if "STUSPS" in cnty else None
if st is None:  # county file carries STATEFP only; map to postal codes
    fips2 = pd.read_csv(os.path.join(ROOT, "code", "state_codes.csv"), dtype=str)
    cnty = cnty.merge(fips2, left_on="STATEFP", right_on="state_fips", how="left")
    st = cnty.dissolve("state")[["geometry"]].reset_index().rename(columns={"state": "STUSPS"})
rp = aw[has_geom].copy(); rp["geometry"] = rp.to_crs(5070).geometry.representative_point().to_crs(4326)
j = gpd.sjoin(rp[["geometry"]], st, how="left", predicate="within")
aw["state_from_map"] = j.groupby(level=0).STUSPS.first()
aw["state_reported"] = aw.state_reported.where(~aw.state_reported.str.fullmatch(r"[A-Za-z]{2}", na=False),
                                               aw.state_reported.str.upper())
valid_state = aw.state_reported.str.fullmatch(r"[A-Z]{2}", na=False)
aw["state"] = aw.state_reported.where(valid_state, aw.state_from_map)
aw["state_note"] = np.where(valid_state, "", "state taken from award location (DOT listed: " +
                            aw.state_reported.fillna("blank") + ")")

aw = aw.sort_values(["fiscal_year", "state", "recipient_name", "grant_program", "federal_funding"]).reset_index(drop=True)
aw["award_id"] = ["SS4A-FY%02d-%04d" % (fy % 100, i + 1) for fy, i in
                  zip(aw.fiscal_year, aw.groupby("fiscal_year").cumcount())]
aw["in_core_fy2022_2025"] = aw.fiscal_year.le(2025)

order = ["award_id", "fiscal_year", "in_core_fy2022_2025", "dot_award_id", "uei", "recipient_name", "state",
         "state_note", "state_from_map", "recipient_type", "recipient_subtype", "is_regional_body", "recipient_type_basis", "dot_recipient_type",
         "grant_program", "grant_type", "includes_action_plan", "action_plan_is_update", "includes_supp_or_demo",
         "includes_supplemental", "includes_demonstration", "includes_implementation", "dot_activity",
         "dot_pd_detail", "dot_round", "dot_rural_urban", "project_name", "federal_funding", "total_project_cost",
         "action_plan_amount", "dot_jurisdiction_pop", "dot_list_correction", "geometry_note", "source_layer", "source_objectid", "geometry"]
aw = aw[order]
aw.to_file(os.path.join(INT, "awards.gpkg"), driver="GPKG")
pd.DataFrame(aw.drop(columns="geometry")).to_csv(os.path.join(INT, "awards_coded.csv"), index=False)
print(aw.groupby("fiscal_year").agg(n=("award_id", "size"), dollars=("federal_funding", "sum")))
print(aw.recipient_type.value_counts()); print(aw.grant_type.value_counts())
