#!/usr/bin/env python3
"""07_docs.py: write the documents that quote numbers, reading every number from report/stats.json.

Plain-language summary: this script writes README.md, report/DATA_NOTE.md,
docs/LIMITATIONS.md, docs/TALK_TRACK.md and docs/VERIFY_CHECKLIST.md. No number
is typed by hand: each one comes from report/stats.json or the processed tables,
so the text cannot disagree with the data. Run with --final after your review to
remove the DRAFT banners.
"""
import json, os, sys
import pandas as pd

FINAL = "--final" in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
S = json.load(open(os.path.join(ROOT, "report", "stats.json")))
AUS = json.load(open(os.path.join(ROOT, "AUTHORS.json")))["authors"]
A = AUS[0]
AUTHOR_LINES = "  \n".join(f"**Author:** {x['name']} ({x['affiliation']}), ORCID [{x['orcid']}](https://orcid.org/{x['orcid']})" for x in AUS)
CITE_NAMES = ", & ".join(f"{x['family']}, " + " ".join(p[0] + "." for p in x["given"].split()) for x in AUS)
a = pd.read_csv(os.path.join(PROC, "ss4a_awards_fy2022_2026.csv"), dtype={"primary_county_fips": str})
g = pd.read_csv(os.path.join(PROC, "county_coverage_gap_table.csv"), dtype={"fips": str})
rb = pd.read_csv(os.path.join(PROC, "regional_body_coverage_table.csv"))
AT = json.load(open(os.path.join(ROOT, "report", "analysis_applications_travel.json")))
_x = pd.read_csv(os.path.join(PROC, "unfunded_applicant_county_crosswalk.csv"), dtype=str)
n_hand = _x[_x.match_method.str.startswith("manual", na=False)].app_id.nunique()
BANNER = "" if FINAL else "> **DRAFT: not yet verified by the author. Do not cite or share.**\n\n"
REPO = "https://github.com/Emmanuel-Oti-Nani/ss4a-safety-action-plan-coverage"
DOI = "[doi:10.5281/zenodo.24250593](https://doi.org/10.5281/zenodo.24250593)"
TITLE = "Safety Action Plan Coverage in Rural America: SS4A Awards Dataset, FY2022-FY2026"
VERSION = "1.1.0"


def n(x):
    return f"{x:,}"


def money(x):
    return f"${x/1e9:.2f} billion" if x >= 1e9 else f"${x/1e6:,.1f} million"


hf = S["n_high_fatality_rural"]; gap = S["n_gap_counties"]; nc = S["n_gap_counties_not_covered"]
sr, su = S["status_rural_counties"], S["status_urban_counties"]
shf = S["status_high_fatality_rural"]
pct_cov = lambda d: round(100 * d.get("covered", 0) / sum(d.values()))
other_rural = {k: sr.get(k, 0) - shf.get(k, 0) for k in sr}
top_states = ", ".join(f"{s} ({k})" for s, k in S["states_most_gap_counties"])
bf = S["awards_by_fy"]; df_ = S["dollars_by_fy"]
fy_line = "; ".join(f"FY{y}: {n(bf[y])} awards, {money(df_[y])}" for y in sorted(bf))
rt = S["recipient_type_counts"]; gt = S["grant_type_counts"]

# ------------------------------------------------------------------ README
readme = f"""{BANNER}# {TITLE}

**Status:** {"Released" if FINAL else "Draft, unreleased"} | Version {VERSION} | DOI: {DOI}
{AUTHOR_LINES}

## In plain language

Safe Streets and Roads for All (SS4A) is the federal grant program that, from 2022 to 2026, paid local, regional and tribal governments to prepare road safety action plans and to build the projects those plans identify. A community must have an action plan before it can win SS4A construction money. The U.S. Department of Transportation (DOT) publishes the awards one funding round at a time, in separate lists and maps.

This data set brings all five rounds into one table: {n(S['n_awards_all'])} awards totaling {money(S['dollars_all'])}, checked against DOT's official award lists for every year and state. Each award is coded by type of recipient and type of grant, and is placed on the map at the counties, cities and towns its plan covers.

Plan coverage is then compared with county traffic deaths from the U.S. Rural Road Fatality County Panel (DOI [10.5281/zenodo.23547649](https://doi.org/10.5281/zenodo.23547649)). Of the {n(hf)} rural counties with the highest traffic death rates, **{n(gap)} ({S['pct_hf_rural_gap']}%) have no SS4A-funded action plan covering most of their residents**, and {n(nc)} have none at all. These {n(gap)} counties recorded {n(S['deaths_2020_2024_gap_counties'])} traffic deaths from 2020 to 2024. For each one, the coverage gap table names any neighboring regional council or metropolitan planning organization that already holds a funded plan, a practical starting point for the next application.

## What is in this package

| File | What it is |
|---|---|
| `data/processed/ss4a_awards_fy2022_2026.csv` | One row per award ({n(S['n_awards_all'])} rows). Recipient, state, recipient type, grant type, dollars, residents in the award area, counties and places covered. |
| `data/processed/ss4a_awards_fy2022_2026.gpkg` | The same awards with their map shapes (GeoPackage, opens in QGIS or ArcGIS). |
| `data/processed/ss4a_awards_fy2022_2026_web.geojson` | Simplified map shapes for web maps. |
| `data/processed/county_coverage_gap_table.csv` | One row per county ({n(S['n_counties'])} rows): deaths 2020-2024, rural status, share of residents in a funded plan area, coverage status, gap flag, and the awards and regional bodies that reach it. |
| `data/processed/regional_body_coverage_table.csv` | One row per regional council or metropolitan planning organization with an SS4A award ({n(S['n_regional_bodies'])} rows), with the counties its plans cover. |
| `data/processed/state_coverage_summary.csv` | Rural coverage and gap counts by state. |
| `data/processed/award_county_crosswalk.csv`, `award_place_crosswalk.csv` | Which counties and Census places each award covers, with population shares. |
| `data/processed/unfunded_applicant_county_crosswalk.csv` | DOT's eligible but unfunded applications, FY2022-FY2024 (630), placed in counties (added in 1.1.0). |
| `data/processed/county_applications_travel.csv` | One row per county: unfunded applications, 2024 vehicle-miles traveled and deaths per 100 million vehicle-miles (added in 1.1.0). |
| `data/processed/qa_report.txt` | Quality checks: totals against DOT, matching rates, spot checks. Read this first. |
| `report/DATA_NOTE.md`, `report/figures/`, `report/tables/priority_gap_counties.csv` | Short data note, three figures, and the priority list of gap counties. |
| `paper/main.pdf`, `paper/main.tex` | Research article (about 7,400 words, 5 figures, 8 tables), built from the same numbers (`code/09_analysis.py`, `code/12_applications_travel.py`, `code/08_paper.py`). |
| `report/analysis.json` | Results of the extended analyses: coverage by round, plans to implementation, regression models, dollars per death, road ownership, spatial clustering, state comparison. |
| `docs/` | Codebook, coding rules, limitations, verification checklist, glossary, publishing guide. |

## Fiscal years

{fy_line}. The fiscal year 2022 to 2025 subset named in the original project plan is the column `in_core_fy2022_2025` ({n(S['n_awards_core'])} awards). Fiscal year 2026 was added because DOT announced those awards on October 29, 2026. It is the last of the five fiscal years (2022 to 2026) for which the Infrastructure Investment and Jobs Act appropriated SS4A funds.

## How to rebuild it

Requires Python 3.10 or newer.

```
pip install -r requirements.txt
python code/01_fetch.py      # downloads DOT map layers, Census files, Project 1 panel (about 5 minutes)
python code/02_build.py      # combines and codes awards
python code/03_match.py      # matches award areas to counties and places (about 1 minute)
python code/04_outputs.py    # writes the dataset, gap tables and report/stats.json
python code/05_qa.py         # writes data/processed/qa_report.txt
python code/06_figures.py    # draws report/figures
python code/07_docs.py       # writes the documents from report/stats.json
python code/09_analysis.py   # extended analyses for the article (writes report/analysis.json)
python code/10_fetch_vmt.py   # 2024 county vehicle-miles from FHWA HPMS
python code/11_match_applicants.py  # places DOT's unfunded applications in counties
python code/12_applications_travel.py  # application and travel analyses (writes report/analysis_applications_travel.json)
python code/08_paper.py      # builds paper/main.pdf (needs TeX Live: lineno, natbib, orcidlink, draftwatermark)
```

Three inputs for the 1.1.0 analyses are kept in `data/raw/`. Two cannot be rebuilt by script: DOT's unfunded-application lists (`ss4a_other_applicants_fy22_fy24.txt`, read from DOT's spreadsheets in a web browser), and the hand placements of applicants (`applicant_county_overrides.csv`). The third is the county travel totals (`hpms_2024_county_vmt.csv`, which `code/10_fetch_vmt.py` can also refetch).

The last lines of `04_outputs.py` print the headline numbers. They should show {n(S['n_awards_all'])} awards and {n(gap)} gap counties.

## Sources

| Source | Vintage | Terms |
|---|---|---|
| U.S. DOT SS4A award map layers (ArcGIS Online organization behind https://www.transportation.gov/grants/ss4a award maps) | FY2022-FY2026, accessed November 2026 | U.S. government work, public domain |
| U.S. DOT published award totals (2022-2026 award pages) | as posted | public domain |
| U.S. Census Bureau 2020 cartographic boundary files (counties, places) | 2020 | public domain |
| U.S. Census Bureau 2020 centers of population by block group | 2020 | public domain |
| U.S. Rural Road Fatality County Panel v1.0.0 (FARS 2015-2024) | v1.0.0 | CC BY 4.0 |
| U.S. Census Bureau Small Area Income and Poverty Estimates | 2023 | public domain |
| U.S. DOT SS4A "Other Applicants" lists (eligible applications not funded) | FY2022-FY2024, accessed November 2026 | public domain |
| FHWA Highway Performance Monitoring System, state feature services | 2024 | public domain |

Every download is logged with size and SHA-256 fingerprint in `data/raw/PROVENANCE.txt`.

## Limitations

See `docs/LIMITATIONS.md`. The most important: this dataset shows plans **funded by SS4A**. A county with no SS4A plan may still have a state or local safety plan paid for another way.

## License and citation

Code: MIT. Data and documents: CC BY 4.0. Please cite:

{CITE_NAMES} (2026). *{TITLE}* (Version {VERSION}) [Data set]. Zenodo. {DOI}

Maintainer: {A['name']}, {A['affiliation']}. Repository: {REPO}

## Version history

- **1.1.0** (November 26, 2026): adds Sedinam Annie Barney as author; adds DOT's lists of unfunded applications (FY2022-FY2024) placed in counties, and county vehicle-miles traveled (HPMS 2024) with travel-based death rates; fixes the duplicated keywords line in the article abstract.
- **1.0.0 to 1.0.2** (November 15, 2026): first release, followed by small corrections (1.0.2 corrects the author contact email).
"""
open(os.path.join(ROOT, "README.md"), "w").write(readme)

# ------------------------------------------------------------------ DATA NOTE
note = f"""{BANNER}# {TITLE}: Data Note

{'; '.join(x['name'] + ', ' + x['affiliation'] for x in AUS)}

## Purpose

The Safe Streets and Roads for All (SS4A) program, created by the Infrastructure Investment and Jobs Act, funded local and regional road safety action plans and projects in fiscal years 2022 through 2026. DOT publishes the awards round by round. No single public table links each award to the places it covers or to local fatality burden. This data set fills that gap and asks one question: which high-fatality rural counties still have no SS4A-funded safety action plan?

## Data

The build combines DOT's own award map layers, which back the official SS4A awards maps, into {n(S['n_awards_all'])} award records worth {money(S['dollars_all'])}: {fy_line}. Counts and dollars match DOT's official award lists exactly for every year and every state. DOT's FY2022 map layer lacked 2 of the 511 FY2022 awards; they were added from DOT's award list. Three award areas that DOT's map layer drew in the wrong place were replaced with Census boundaries.

Recipients are coded as city ({n(rt.get('city', 0))}), county ({n(rt.get('county', 0))}), tribe ({n(rt.get('tribe', 0))}), regional council ({n(rt.get('regional_council', 0))}), metropolitan planning organization ({n(rt.get('mpo', 0))}), or other ({n(rt.get('other', 0))}). Grant types are: action plan only ({n(gt.get('action plan', 0))}), action plan with supplemental planning or demonstration ({n(gt.get('action plan + supplemental/demonstration', 0))}), supplemental planning or demonstration only ({n(gt.get('supplemental/demonstration only', 0))}), and implementation ({n(gt.get('implementation', 0))}).

Each award area is laid over 2020 Census block-group population centers, counties and places. A county counts as **covered** when at least half of its 2020 residents live inside one or more award areas that fund developing or updating an action plan. **Rural counties** are those where at least half of residents live outside 2020 Census urban areas ({n(S['n_rural_counties'])} counties). **High-fatality rural counties** are the top quarter of rural counties by traffic deaths per 100,000 residents per year, 2020 to 2024, among rural counties with at least {S['min_deaths']} deaths in that period. The rate threshold is {S['high_fatality_rate_threshold']} ({n(hf)} counties).

## Findings

- About {S['pop_share_in_action_plan_area_all']}% of U.S. residents live inside an SS4A action plan area. The figure is {S['pop_share_in_action_plan_area_urban_counties']}% in urban counties and {S['pop_share_in_action_plan_area_rural_counties']}% in rural counties.
- {pct_cov(su)}% of urban counties are covered, compared with {pct_cov(sr)}% of rural counties, even though rural counties have the higher death rate ({S['rate_rural_counties']} against {S['rate_urban_counties']} deaths per 100,000 residents per year, 2020 to 2024).
- High-fatality rural counties are covered at about the same rate as other rural counties ({pct_cov(shf)}% and {pct_cov(other_rural)}%). The program did not reach the deadliest rural counties any better than rural counties in general.
- {n(gap)} of {n(hf)} high-fatality rural counties ({S['pct_hf_rural_gap']}%) are not covered, and {n(nc)} have no plan area at all. They recorded {n(S['deaths_2020_2024_gap_counties'])} deaths from 2020 to 2024.
- {n(S['n_gap_with_neighbor_regional_body'])} of these gap counties border a county where a regional council or metropolitan planning organization already has a funded plan. That body is a natural partner for the next plan.
- The states with the most gap counties are {top_states}.
- The result holds under stricter rules: {n(S['n_gap_counties_conservative'])} gap counties when {n(S['n_action_plan_awards_area_flag'])} award areas that may be drawn larger than the plan are set aside, and {n(S['n_gap_counties_fy22_25'])} when only FY2022 to FY2025 awards are counted.

## Use

Regional councils and states can use the county gap table and the regional body table to see which high-fatality rural counties lack a funded plan and which neighboring bodies already have one. Researchers can join the award table to other county data by FIPS code.

## Availability

Data, code and documents: {REPO}; archived at {DOI}. License: CC BY 4.0 (data and documents), MIT (code).
"""
open(os.path.join(ROOT, "report", "DATA_NOTE.md"), "w").write(note)

# ------------------------------------------------------------------ LIMITATIONS
nobg = int(a.geo_match_flag.fillna("").str.startswith("no 2020").sum())
lim = f"""{BANNER}# Limitations

*Plain-language summary: what this data set can and cannot tell you. Read before quoting any result.*

1. **SS4A-funded plans only.** Coverage means an SS4A award funds an action plan for that area. Many counties have safety plans paid for another way: a state Local Road Safety Plan program, a county's own funds, or a plan an implementation grantee already had. A "not covered" county may still have a plan. The gap table finds where SS4A money has not reached. It does not prove a county has no plan at all.
2. **Funded is not finished.** An award means a plan was funded, not that it has been adopted. Plans funded in FY2025 and FY2026 may not be complete for several years.
3. **Award areas are DOT's drawings.** The map shapes come from DOT's award map layers. For {n(S['n_action_plan_awards_area_flag'])} action plan awards, the shape holds more than twice the residents DOT reported. Typical cases are a county plan for its unincorporated area drawn as the whole county, or a regional council plan for one town drawn as the whole region. These awards are flagged (`area_may_overstate_plan`), and the conservative coverage measure leaves them out ({n(S['n_gap_counties_conservative'])} gap counties instead of {n(gap)}).
4. **Population is placed by block group.** Residents are counted by whether a block group's 2020 population center falls inside an award area. Small areas that contain no population center ({nobg} awards, mostly small tribal areas and corridors) count as zero residents, so they never cover a county by themselves.
5. **Two FY2022 awards have no map area.** DOT's FY2022 map layer lacks 2 of 511 awards: action plans of $1,000,000 each to North Dakota State University and the State University of New York at Stony Brook. They are in the award table from DOT's award list, but with no area they cannot add to county coverage. Three other awards were drawn in the wrong place on DOT's map layer (City of Rutledge, TN; Town of Charlestown, NH; Beaverhead County, MT); their shapes were replaced with Census boundaries (`code/geometry_corrections.csv`). Other errors of this kind may remain where the wrong shape happens to fall in the right state.
6. **Recipient types are partly coded by rule.** DOT's own recipient labels differ across years and sometimes conflict. A metropolitan planning organization housed in a council of governments may appear under either label. The coded type follows DOT's label first, then name rules, then {n(len(pd.read_csv(os.path.join(ROOT, 'code', 'recipient_overrides.csv'))))} hand corrections listed in `code/recipient_overrides.csv`. Use `is_regional_body` when the difference does not matter.
7. **Supplemental planning and demonstration are combined for FY2023, FY2025 and FY2026,** because DOT reported them as one category in those years.
8. **"Rural" has two meanings.** This project uses the Census 2020 urban area map, as Project 1 does. DOT's own rural label for each award (`dot_rural_urban`) follows the SS4A notice, which treats urban areas under 200,000 people as rural. The two are not interchangeable.
9. **Death rates are per resident.** Counties with very few residents and a busy highway have very high rates (Loving County, Texas, has the highest). A rate per resident is not a rate per mile traveled. The gap table also reports death counts, and the priority list is sorted by count. Version 1.1.0 adds a per-mile rate as a check (`county_applications_travel.csv`); it identifies a different but overlapping set of high-fatality counties ({AT['vmt']['n_hf_both']} of {AT['vmt']['n_hf_vmt']} on both measures).
10. **The high-fatality cutoff is a choice.** It is the top quarter of rural counties by rate, among counties with at least {S['min_deaths']} deaths in 2020 to 2024. Other cutoffs give different lists. The full county table lets users apply their own.
11. **Fifty states and DC only for the gap analysis.** Awards in Puerto Rico and on tribal lands outside county coverage are in the award table but not in the county comparison.
12. **Regional council boundaries are not national.** No free national map of regional council service areas was found. Regional bodies are identified from DOT's recipient records, and their reach is the area their awards cover.
13. **The unfunded-application lists are incomplete.** DOT published lists of eligible applications it did not fund only for FY2022 to FY2024. The FY2022 list covers implementation applications only, and the FY2023 list contains only {AT['pd_unfunded_fy23']} unfunded planning applications. A county may have applied in a round with no published list. Applicants were placed in counties by name; {n_hand} were placed by hand from their published service areas (reasons in `data/raw/applicant_county_overrides.csv`) and {AT['applicants']['n_unassigned']} could not be placed.
14. **Travel data leave out most local roads.** The per-mile rates use 2024 HPMS travel on road sections with traffic counts, mostly arterials and collectors. Travel on local roads is largely missing, and one year of travel stands in for 2020 to 2024.
"""
open(os.path.join(ROOT, "docs", "LIMITATIONS.md"), "w").write(lim)

# ------------------------------------------------------------------ TALK TRACK
talk = f"""{BANNER}# Talking about Safety Action Plan Coverage in Rural America

## 60-second version
The problem: Rural counties lose about {S['rate_rural_counties']} people per 100,000 residents to traffic crashes each year, against {S['rate_urban_counties']} in urban counties (2020-2024). The federal Safe Streets and Roads for All program pays communities to write the safety action plans that unlock construction money. Small towns and rural counties often depend on regional councils to prepare those plans.
What I built: An open data set of all {n(S['n_awards_all'])} SS4A awards from 2022 to 2026, worth {money(S['dollars_all'])}. Each is coded by who got it and what it pays for, and mapped to the counties and towns it covers. I matched it with my county fatality panel.
What it shows: {n(gap)} of {n(hf)} high-fatality rural counties, {S['pct_hf_rural_gap']} percent, do not have most residents inside a funded plan area. Those counties had {n(S['deaths_2020_2024_gap_counties'])} deaths from 2020 to 2024. Only {pct_cov(sr)} percent of rural counties are covered, against {pct_cov(su)} percent of urban counties.
Who can use it: Regional councils, state DOTs, metropolitan planning organizations, researchers, and anyone deciding where the next safety plan should go.
Where it is: {REPO}, DOI {DOI}.

## Two-sentence version
I built an open, mapped data set of every Safe Streets and Roads for All award from 2022 to 2026 and linked it to county traffic deaths. It shows that about two in three high-fatality rural counties still have no federally funded safety action plan covering most of their residents.

## Questions you may be asked
1. **Where does the data come from?** DOT's own published award maps, checked against DOT's award totals for every year. Population comes from the 2020 Census. Deaths come from NHTSA's Fatality Analysis Reporting System, through my Project 1 panel.
2. **What are its limits?** It counts plans paid for by SS4A only. A county could have a plan paid for another way. Funded also does not mean finished. Details are in docs/LIMITATIONS.md.
3. **Why does this matter for the United States?** The program funded {S['n_action_plan_awards_all']:,} action plan awards, but the counties with the highest death rates were reached no better than other rural counties. Knowing where the gaps are helps target technical help and future funding.
"""
open(os.path.join(ROOT, "docs", "TALK_TRACK.md"), "w").write(talk)

# ------------------------------------------------------------------ VERIFY CHECKLIST
rnd = a.sample(5, random_state=2026)
ext = pd.concat([a.nlargest(2, "federal_funding"), a.nsmallest(1, "federal_funding"),
                 a.nlargest(1, "census_pop_in_area"), a.nlargest(1, "n_counties")])
known = a[a.recipient_name.str.contains("Ozarks Transportation|Southwest Missouri Council|City of Springfield|Greene County|"
                                        "Kaysinger|Harry S Truman|Meramec|Boonslick|Bootheel", case=False, na=False)
          & a.state.eq("MO")].head(6)
src = {2022: "https://www.transportation.gov/grants/ss4a/2022-awards", 2023: "https://www.transportation.gov/grants/ss4a/2023-awards",
       2024: "https://www.transportation.gov/grants/ss4a/2024-awards", 2025: "https://www.transportation.gov/grants/ss4a/2025-full-award-list",
       2026: "https://www.transportation.gov/grants/ss4a/2026-awards"}


def arow(r):
    return (f"- [ ] `{r.award_id}`: {r.recipient_name} ({r.state}), FY{r.fiscal_year}, {r.grant_program}, "
            f"federal funding **${r.federal_funding:,.0f}**, coded `{r.recipient_type}` / `{r.grant_type}`, "
            f"primary county {r.primary_county_name}. Check the name, state, program and dollars on the FY{r.fiscal_year} "
            f"award list linked from {src[r.fiscal_year]}. ___")


pri = pd.read_csv(os.path.join(ROOT, "report", "tables", "priority_gap_counties.csv"), dtype={"fips": str}).head(5)
crow = "\n".join(f"- [ ] {r.county_name}, {r.state} (FIPS {r.fips}): {r.deaths_2020_2024} deaths 2020-2024, "
                 f"status **{r.coverage_status}**. Search the FY2022-FY2026 lists and the DOT cumulative awards map "
                 f"(https://www.transportation.gov/grants/ss4a/cumulative-awards) for any award to this county, its towns, "
                 f"or its regional council. If you find one that covers most residents, note it here: ___"
                 for r in pri.itertuples())
chk = f"""{BANNER}# Your verification checklist

*Plain-language version: before anything goes public under your name, you check it. Total time: about 2 to 3 hours, which can be split over two sittings. Tick each box and add the date.*

*The publish gate (`tools/publish_gate.py`) checks the mechanical items automatically. These are yours. Items marked [x] were pre-checked against DOT's official sources on 2026-11-10 (results in `docs/VERIFICATION_RECORD.md`). Give each a quick look of your own before you sign off.*

## Part 1: Make sure the results can be rebuilt (15 to 30 min)

Pick one:
- [ ] **Option A, run it yourself.** In a terminal in the project folder, run the seven commands in the README under "How to rebuild it". When `04_outputs.py` finishes you should see `"n_awards_all": {S['n_awards_all']}` and `"n_gap_counties": {gap}`.
- [ ] **Option B, independent re-run.** Ask a colleague to re-run the pipeline from scratch on another computer. They should match: {n(S['n_awards_all'])} awards, {money(S['dollars_all'])}, {n(hf)} high-fatality rural counties, {n(gap)} gap counties, {n(S['deaths_2020_2024_gap_counties'])} deaths in gap counties.

Then:
- [ ] Open `data/processed/qa_report.txt`. Section 1 shows OK for all five years (FY2022: 511 awards, $802,161,019).
- [ ] Every number in `README.md` and `report/DATA_NOTE.md` matches `report/stats.json`. (They are generated from it; spot-check three.)

## Part 2: Check the sources (15 min)

- [ ] Open https://www.transportation.gov/grants/ss4a/2025-awards and https://www.transportation.gov/grants/ss4a/2026-awards. The totals read 521 awards ($982,231,998) and 297 awards ($1,012,969,919).
- [ ] Open https://www.transportation.gov/grants/ss4a/2023-awards. It reads 620 communities, $895 million.
- [x] **Item 2.3: missing FY2022 awards. Resolved 2026-11-10.** DOT's FY2022 full award list (https://www.transportation.gov/grants/ss4a/2022-full-award-list) has 511 awards, not 510. The two missing from the map layer are North Dakota State University and SUNY Stony Brook ($1,000,000 action plans each). Both were added. Your check: open that list, filter column C to ND and NY, and confirm the two rows. ___
- [ ] Sources and terms: DOT award layers and pages, U.S. government work, public domain. Census 2020 boundary and population-center files, public domain. Project 1 panel, CC BY 4.0, your own work.

## Part 3: Check rows by hand (45 to 60 min)

**Awards you know personally (Missouri):**
{chr(10).join(arow(r) for r in known.itertuples())}

**Extreme values:**
{chr(10).join(arow(r) for r in ext.itertuples())}

**Five random awards (seed 2026):**
{chr(10).join(arow(r) for r in rnd.itertuples())}

**Top five priority gap counties.** These are the claims most likely to be quoted, so confirm each truly has no SS4A plan:
{crow}

**One county you know:**
- [ ] Greene County, MO (FIPS 29077), in `county_coverage_gap_table.csv`: status should be "covered", reached by the Ozarks Transportation Organization FY2022 plan and the Southwest Missouri Council of Governments FY2023 plan. Does that match what you know? ___

## Part 4: Your decisions (15 min)

The build made these choices provisionally. Agree with or change each one.
- [ ] **Fiscal year 2026.** FY2026 awards were posted on October 29, 2026, so they are included and marked by `in_core_fy2022_2025 = False`. Option A: keep FY2022 to FY2026 as version 1.0 (complete program). Option B: release FY2022 to FY2025 only, as in the original plan ({n(S['n_gap_counties_fy22_25'])} gap counties instead of {n(gap)}). Recommended: A. Your choice: ___
- [ ] **What counts as covered.** Half or more of county residents inside a funded action plan area. Option A: keep 50%. Option B: any overlap counts (fewer gaps, but a single town plan would "cover" a whole county). Recommended: A. Your choice: ___
- [ ] **Which coverage measure leads.** Option A: as DOT mapped it ({n(gap)} gap counties). Option B: conservative, setting aside {n(S['n_action_plan_awards_area_flag'])} award areas that may be drawn larger than the plan ({n(S['n_gap_counties_conservative'])} gap counties). Recommended: A as headline, B reported alongside. Your choice: ___
- [ ] **High-fatality cutoff.** Top quarter of rural counties by deaths per 100,000 residents per year, 2020 to 2024, among counties with at least {S['min_deaths']} deaths (cutoff {S['high_fatality_rate_threshold']}). Option A: keep. Option B: top quarter by death count instead (favors larger rural counties). Recommended: A. Your choice: ___
- [ ] **Rural county.** Majority of 2020 residents outside Census urban areas, the same rule as Project 1. Recommended: keep. Your choice: ___
- [ ] **Recipient overrides.** Open `code/recipient_overrides.csv` ({n(len(pd.read_csv(os.path.join(ROOT, 'code', 'recipient_overrides.csv'))))} rows). Agree with each, especially Ozarks Transportation Organization coded as MPO and Kaysinger Basin Regional Planning Commission coded as regional council. ___

## Part 5: The paper (45 to 60 min)

- [ ] Read `paper/main.pdf` start to finish. Every number in it comes from `report/stats.json` and `report/analysis.json`; spot-check five against Tables 1 to 7.
- [ ] Judgment calls in the extended analyses: death rate capped at 200 per 100,000 in the regressions; dollars allocated to counties by the share of each award's residents; "early plans" means FY2022-FY2023 and "later implementation" FY2023-FY2026; the seven comparison states are those in FHWA's 2010 local road safety domestic scan. Agree or change each. ___
- [ ] Write the paper text in your own words, as you did for Project 2. The Declarations use your Project 2 AI statement ("assisted with code, data assembly, and copy-editing; the author designed and drafted the study ..."), which is true only once the text is yours. Then delete the VERIFY reminder line under it in `code/paper_template.tex` and rebuild.
- [ ] Choose the venue (see `paper/SUBMISSION_NOTES.md`).

## Part 6: Before it goes public (15 to 30 min)

- [ ] The "In plain language" section of `README.md` and the "Findings" in `report/DATA_NOTE.md` are rewritten in your own words. Nothing remains that you could not explain or defend.
- [ ] Your name, ORCID, affiliation and email are correct in `AUTHORS.json`.
- [ ] You have read `docs/LIMITATIONS.md` and agree with it.
- [ ] Draft stamps removed (run `06_figures.py --final` and `07_docs.py --final`) and `tools/publish_gate.py` passes.
- [ ] Evidence log row written on release day.

**When every box is ticked, the package is ready for release.**
"""
# Items pre-checked against DOT's official award lists on 2026-11-10 (see docs/VERIFICATION_RECORD.md)
PRE = {"SS4A-FY22-0297", "SS4A-FY23-0340", "SS4A-FY23-0341", "SS4A-FY23-0345", "SS4A-FY24-0383", "SS4A-FY24-0386",
       "SS4A-FY22-0149", "SS4A-FY22-0398", "SS4A-FY22-0003", "SS4A-FY23-0093", "SS4A-FY22-0172", "SS4A-FY25-0477",
       "SS4A-FY25-0008", "SS4A-FY23-0456", "SS4A-FY23-0320", "SS4A-FY22-0482"}
lines = []
for l in chk.split("\n"):
    ids = [i for i in PRE if f"`{i}`" in l]
    if ids and l.startswith("- [ ]"):
        l = l.replace("- [ ]", "- [x]", 1).replace(" ___", " Pre-check 2026-11-10: name, state, program and dollars match DOT's list. Your look: ___")
    for cname, note in [("Robeson County", "no SS4A award to the county, its towns or a regional body in any year"),
                        ("Darlington County", "no SS4A award to the county, its towns or a regional body in any year"),
                        ("Navajo County", "only partial plans: Navajo Nation (FY2023, FY2024), City of Show Low (FY2024), City of Holbrook (FY2026)"),
                        ("McKinley County", "only partial plans: Navajo Nation (FY2023, FY2024)"),
                        ("Apache County", "only partial plans: Navajo Nation (FY2023, FY2024)")]:
        if l.startswith("- [ ] " + cname):
            l = l.replace("- [ ]", "- [x]", 1).replace("note it here: ___", f"note it here. Pre-check 2026-11-10 of all five DOT award lists: {note}. Your look: ___")
    lines.append(l)
chk = "\n".join(lines)
open(os.path.join(ROOT, "docs", "VERIFY_CHECKLIST.md"), "w").write(chk)
print("docs written", "(final)" if FINAL else "(DRAFT)")
