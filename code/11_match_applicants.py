"""Match DOT's unfunded SS4A applicants (FY2022-FY2024) to counties.

Plain-language summary: reads the 630 eligible-but-unfunded applications from DOT's
"Other Applicants" lists, works out what kind of government each applicant is, and finds
it on the 2020 Census maps: counties by name, cities and towns as Census places (or, for
townships and New England towns, county subdivisions), tribes as Census tribal areas.
Each applicant is then assigned to every county holding at least 10% of its population
(block-group centers of population). Applicants the rules cannot place automatically are
placed from data/raw/applicant_county_overrides.csv, which records the reason for each.

Writes data/processed/unfunded_applicant_county_crosswalk.csv and
data/interim/applicant_match_review.csv (every match with its method, for review).
"""
import os, re, unicodedata
import geopandas as gpd
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
ST = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11",
      "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
      "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30",
      "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
      "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
      "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56", "PR": "72"}
STATE_NAMES = {"Alaska", "Alabama", "Arizona", "California", "Iowa", "Illinois", "Indiana", "Missouri", "Maryland",
               "Ohio", "Oklahoma", "Oregon", "Texas", "Utah", "Virginia", "Wisconsin", "Minnesota", "South Carolina",
               "Washington", "New York", "Connecticut"}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", "and").replace("saint ", "st ").replace("st. ", "st ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse(name, st):
    """Return (kind, key): kind in county/place/cousub/tribe/other."""
    n = name.replace("_x000D_", "").strip()
    n = re.sub(r"_\d+$", "", n)
    low = n.lower()
    if re.search(r"tribe|\bindian\b|band of|rancheria|native village|\bnation$|tribes\b", low):
        return "tribe", n
    if re.search(r"council of governments|planning commission|\bmpo\b|regional|commission of|authority|"
                 r"district|university|school|transit|frcog|incog|cog\b|organization|energy council|"
                 r"sports|board of trustees|police|fire", low) and not re.search(r"county (board|commission|council|road)", low):
        # police/fire/district applicants are placed by override (they serve a named jurisdiction)
        return "other", n
    m = (re.match(r"^(?:county of|parish of) (.+?)(?:,.*)?$", low) or
         re.match(r"^(.+?) (?:county|parish)\b", low))
    if m and not low.startswith(("city of", "town of", "village of")):
        nm = m.group(1)
        nm = re.sub(r"^(the|metro) ", "", nm)
        return "county", nm
    for pre in ("city and county of ", "city & county of ", "unified government of ", "metropolitan government of "):
        if low.startswith(pre):
            return "county_city", n[len(pre):]
    kind = "place"
    m = re.match(r"^(?:the )?(city|town|village|borough|township|inc village|municipio) (?:of )?(.+)$", low)
    core = n
    if m:
        if m.group(1) in ("township", "town") :
            kind = "place_or_cousub"
        core = n[m.end(1):].strip()
        core = re.sub(r"^of\s+", "", core, flags=re.I)
    else:
        m2 = re.match(r"^(.+?) (township|borough|city|town)\b(.*)$", n, flags=re.I)
        if m2 and not m2.group(1).lower().startswith("city"):
            core = m2.group(1)
            if m2.group(2).lower() in ("township", "town"):
                kind = "place_or_cousub"
    core = re.split(r"\s+-\s+|,\s*|\s+department\b|\s+engineering\b|\s+public works\b|\s+ss4a\b|\s+redevelopment\b|"
                    r"\s+police\b|\s+utilities\b|/", core, flags=re.I)[0]
    core = re.sub(r"\b(" + "|".join(ST) + r")$", "", core.strip()).strip()
    core = re.sub(r",?\s*(" + "|".join(STATE_NAMES) + r")$", "", core).strip()
    core = re.sub(r"\s+(ca|ct|ny|ut|md|wi)$", "", core, flags=re.I).strip()
    return kind, core


def main():
    lines = open(P("data", "raw", "ss4a_other_applicants_fy22_fy24.txt")).read().splitlines()
    apps = pd.DataFrame([l.split("|") for l in lines],
                        columns=["round", "applicant", "state", "grant", "pd_activity", "dot_rural_urban", "applicant_type"])
    apps.insert(0, "app_id", [f"OA-{i+1:04d}" for i in range(len(apps))])
    apps["fiscal_year"] = apps["round"].str[:4].str.replace("FY", "20")
    apps["seeks_action_plan"] = apps.pd_activity.isin(["AP_NEW", "AP_UPD", "AP+SUP"])

    cty = gpd.read_file("zip://" + P("data", "raw", "cb_2020_us_county_500k.zip"))
    cty["key"] = cty.NAME.map(norm)
    plc = gpd.read_file("zip://" + P("data", "raw", "cb_2020_us_place_500k.zip"))
    plc["key"] = plc.NAME.map(norm)
    cs = gpd.read_file("zip://" + P("data", "raw", "cb_2020_us_cousub_500k.zip"))
    cs["key"] = cs.NAME.map(norm)
    ai = gpd.read_file("zip://" + P("data", "raw", "cb_2020_us_aiannh_500k.zip"))
    bg = pd.read_csv(P("data", "raw", "CenPop2020_Mean_BG.txt"), dtype=str, encoding="utf-8-sig")
    bg = gpd.GeoDataFrame(bg, geometry=gpd.points_from_xy(bg.LONGITUDE.astype(float), bg.LATITUDE.astype(float)), crs="EPSG:4326")
    bg["pop"] = bg.POPULATION.astype(int)
    bg["fips"] = bg.STATEFP + bg.COUNTYFP

    ov = pd.read_csv(P("data", "raw", "applicant_county_overrides.csv"), dtype=str).fillna("")
    ov = ov.set_index("app_id")

    out, review = [], []
    for r in apps.itertuples():
        sf = ST.get(r.state)
        kind, key = parse(r.applicant, r.state)
        geom, method, matched = None, "", ""
        if r.app_id in ov.index:
            o = ov.loc[r.app_id]
            for f in [x for x in o.county_fips.split(";") if x.strip()]:
                out.append((r.app_id, f.strip(), 1.0, "manual (" + o.certainty + ")"))
            review.append((r.app_id, r.applicant, r.state, kind, key, "override", o.matched_to, o.county_fips, o.reason))
            continue
        if sf is None:
            review.append((r.app_id, r.applicant, r.state, kind, key, "UNMATCHED", "", "", "state not recognised"))
            continue
        k = norm(key)
        if kind == "county":
            hit = cty[(cty.STATEFP == sf) & (cty.NAMELSAD.map(norm).isin([k + " county", k + " parish", k + " borough"]))]
            if len(hit) != 1:
                hit = cty[(cty.STATEFP == sf) & (cty.key == k)]
            if len(hit) == 1:
                out.append((r.app_id, hit.GEOID.iloc[0], 1.0, "county name"))
                review.append((r.app_id, r.applicant, r.state, kind, key, "county name", hit.NAMELSAD.iloc[0], hit.GEOID.iloc[0], ""))
                continue
        if kind == "county_city":
            hit = cty[(cty.STATEFP == sf) & (cty.key.str.startswith(k.split(" county")[0]))]
            if len(hit) == 1:
                out.append((r.app_id, hit.GEOID.iloc[0], 1.0, "consolidated city-county"))
                review.append((r.app_id, r.applicant, r.state, kind, key, "consolidated city-county", hit.NAMELSAD.iloc[0], hit.GEOID.iloc[0], ""))
                continue
        if kind in ("place", "place_or_cousub", "county_city"):
            hit = plc[(plc.STATEFP == sf) & (plc.key == k)]
            if len(hit) == 0:
                hit = plc[(plc.STATEFP == sf) & (plc.NAMELSAD.map(norm).isin([k + " city", k + " town", k + " village", k + " borough"]))]
            if len(hit) != 1 and kind == "place_or_cousub" or len(hit) == 0:
                h2 = cs[(cs.STATEFP == sf) & (cs.key == k)]
                if len(h2) == 1 and (len(hit) != 1):
                    hit, method = h2, "county subdivision name"
            if len(hit) == 1:
                geom = hit.geometry.iloc[0]
                method = method or "place name"
                matched = hit.NAMELSAD.iloc[0]
        if geom is None:
            review.append((r.app_id, r.applicant, r.state, kind, key, "UNMATCHED", "", "", "needs override"))
            continue
        pts = bg[(bg.STATEFP == sf) & bg.within(geom)]
        if pts["pop"].sum() == 0:
            cc = cty[cty.STATEFP == sf]
            f = cc[cc.contains(geom.representative_point())].GEOID
            shares = pd.Series({f.iloc[0]: 1.0}) if len(f) else pd.Series(dtype=float)
        else:
            shares = pts.groupby("fips")["pop"].sum() / pts["pop"].sum()
        shares = shares[shares >= 0.10]
        for f, s in shares.items():
            out.append((r.app_id, f, round(float(s), 4), method))
        review.append((r.app_id, r.applicant, r.state, kind, key, method, matched, ";".join(shares.index), ""))

    xw = pd.DataFrame(out, columns=["app_id", "county_fips", "pop_share", "match_method"])
    xw = apps.merge(xw, on="app_id", how="left")
    os.makedirs(P("data", "processed"), exist_ok=True)
    xw.to_csv(P("data", "processed", "unfunded_applicant_county_crosswalk.csv"), index=False)
    rv = pd.DataFrame(review, columns=["app_id", "applicant", "state", "parsed_kind", "parsed_name", "method",
                                       "matched_to", "county_fips", "note"])
    rv.to_csv(P("data", "interim", "applicant_match_review.csv"), index=False)
    print(rv.method.value_counts().to_string())
    print("unmatched:", (rv.method == "UNMATCHED").sum())


if __name__ == "__main__":
    main()
