# Verification record

*Plain-language summary: what was checked against DOT's official sources before release, how, and what was found and fixed.*

**Date:** November 10, 2026. **Method:** DOT's official award lists (Excel files on transportation.gov) were opened in a web browser and compared with the data set. DOT's site refuses scripted downloads, so the files were read in the browser. Their size and SHA-256 fingerprints are logged in `data/raw/PROVENANCE.txt`.

| Year | DOT list | DOT total | Data set |
|---|---|---|---|
| FY2022 | FY22-SS4A-Full-Award-List-March2025.xlsx | 511 awards, $802,161,018.54 | 511, $802,161,019 |
| FY2023 | FY23-SS4A-Award-List-March2025.xlsx | 620, $895,717,979 | 620, $895,717,979 |
| FY2024 | FY24-SS4A-Award-List-March2025.xlsx | 710, $1,241,490,821 | 710, $1,241,490,821 |
| FY2025 | FY25-SS4A-Award-List-FY2025.xlsx | 521, $982,231,998 | 521, $982,231,998 |
| FY2026 | FY26_SS4A_AwardList.xlsx | 297, $1,012,969,919 | 297, $1,012,969,919 |

## Checks and results

1. **Missing FY2022 awards (checklist item 2.3).** DOT's FY2022 page and list now report 511 awards (474 action plan grants), not 510. Matching every FY2022 award by its Unique Entity ID (UEI) found two awards absent from all of DOT's FY2022 map layers:
   - North Dakota State University (ND), action plan, $1,000,000, rural (UEI EZ4WPGRE1RD5)
   - State University of New York at Stony Brook (NY), action plan, $1,000,000, urban (UEI MXLDJ7JKMBE1)

   Both were added (`code/fy2022_awards_not_on_map.csv`). DOT publishes no area for them, so they count in totals but not in county coverage.
2. **FY2022 award by award.** All 509 mapped awards matched DOT's list by UEI. Dollars and rural or urban labels agree for all 509. One state was wrong in DOT's map layer: City and Borough of Sitka was listed as AL; DOT's list says AK. Corrected (`code/dot_list_corrections.csv`).
3. **FY2023 to FY2026, state by state.** Award counts and federal dollars match DOT's lists in every state, with zero differences.
4. **Award areas in the wrong place.** A new check compares each award's listed state with the state its map area falls in. Nine awards were flagged. Three were confirmed against DOT's lists as DOT map errors, and their shapes were replaced with Census 2020 boundaries (`code/geometry_corrections.csv`):
   - City of Rutledge, TN (FY2024, $72,000 action plan) was drawn as Rutledge, GA
   - Town of Charlestown, NH (FY2025, $2,400,000 supplemental planning) was drawn over Springfield, VT
   - Beaverhead County, MT (FY2026, $140,000 countywide action plan) was drawn as Beaufort County, SC, with Beaufort's population

   The other six are legitimate: two-state regional bodies (Bi-State Regional Commission, Fargo-Moorhead Metropolitan COG twice, Tahoe Transportation District), a multi-site tribal communities plan (University of Texas Arlington), and a regionally drawn implementation award (Maryland-National Capital Park and Planning Commission), which does not enter coverage.
5. **Checklist rows.** All 16 awards listed in Part 3 (six Missouri awards, five extremes, five random) match DOT's lists on recipient, state, program and dollars. Two shapes that looked odd were confirmed as multi-county plans: Winneshiek County led a 97-county Iowa plan, and Chambers County leads a four-county Alabama plan.
6. **Top five gap counties.** All five DOT lists were searched for each county, its towns and nearby tribal and regional bodies. Robeson County, NC and Darlington County, SC have no SS4A award of any kind in any year. Navajo County and Apache County, AZ, and McKinley County, NM are reached only partly, by the Navajo Nation plans (FY2023, FY2024) and small city plans (Show Low, FY2024; Holbrook, FY2026). This matches their "partly covered" status.
7. **Reproducibility.** The full pipeline was re-run from the raw files in a fresh folder. Every output table and `report/stats.json` came out identical.

## Effect on results

| Measure | Before checks | After checks |
|---|---|---|
| Awards | 2,657 | 2,659 |
| Federal dollars | $4.93 billion | $4.93 billion (+$2.0 million) |
| High-fatality rural counties not covered (gap counties) | 291 | 290 |
| Deaths 2020-2024 in gap counties | 8,379 | 8,361 |
| Gap counties, conservative measure | 299 | 298 |

The change is Beaverhead County, MT, which now correctly shows its own countywide plan. Award IDs (`award_id`) were renumbered when the two FY2022 awards were added. Nothing had been released, so no published ID changed.

## Second recheck (November 10, 2026)

Everything was checked again in a web browser, this time award by award.

1. **DOT award lists unchanged.** All five Excel lists have the same SHA-256 fingerprints as on the first check.
2. **Every award, every field.** All 2,659 awards were compared with DOT's lists on recipient name, state, grant program, rural or urban label, and federal dollars. All match except five recipient-name spellings: Hillsborough County and Hillsborough County MPO, FL; Dover Kent and Texarkana MPOs, which DOT's map layer spells "Metropolitian"; and City of Spanish Fork, UT, which the list calls "City of Spanish Fork City". None affects any number.
3. **New finding: FY2026 rural and urban labels.** DOT's FY2026 map layer labels all 100 implementation awards "Rural". DOT's list has 48 rural and 52 urban, and its 52.2% rural share matches DOT's published "52 percent". The 52 labels were corrected (`code/fy2026_rural_label_corrections.csv`). The label is descriptive only, and no coverage result changed.
4. **DOT program facts.** The FY2026 press release is dated October 29, 2026 ($1,012,969,919, 297 projects). DOT's SS4A page says the law appropriated $5 billion over fiscal years 2022 to 2026, and its cumulative figure ($4.9 billion to more than 2,200 communities) agrees with the data set ($4.93 billion). DOT does not itself call FY2026 the "final round", so the README now says FY2026 is the last of the five fiscal years the law funded.
5. **All 290 gap counties searched by name** in all five DOT lists. Only three appear: Modoc County, CA and McKenzie County, ND (FY2022 implementation grants, which means each already had a plan funded another way) and a University of North Dakota supplemental project on western North Dakota rural roads. None funds an action plan, so all remain correctly classed. The paper names Modoc and McKenzie as examples of plans funded outside SS4A.
6. **Other sources.** The Project 1 Zenodo record is unchanged (version DOI 10.5281/zenodo.23547650, CC BY 4.0, same file size). The Census boundary files are unchanged (dated May 2023). DOT's map layers have the same last-edit dates as when they were fetched.
7. **Reproducibility.** The full pipeline, including the paper, was rebuilt from the raw files in a fresh folder, with identical outputs.

Headline results after the second recheck are unchanged: 2,659 awards, $4.93 billion, and 290 gap counties with 8,361 deaths.

## Expanded research article (November 10, 2026)

The paper was expanded into a full research article with six further analyses (`code/09_analysis.py`, results in `report/analysis.json`). One new source was added: Census Small Area Income and Poverty Estimates for 2023, logged in `data/raw/PROVENANCE.txt`. New references were checked against the publisher or agency record: Smith et al. (2025, *Public Administration Review*, doi:10.1111/puar.70025), Anderson et al. (2010, FHWA-SA-10-027, whose seven scan states are AL, GA, IL, MI, MN, NJ and WA), Beck et al. (2017, MMWR SS 66(17)), Henning-Smith and Kozhimannil (2018, *Health Equity* 2(1)), ITF (2016), Moran (1950), Anselin (1995), Papke and Wooldridge (1996), and the 2015 Minnesota HSIP report, which says Minnesota funded a county safety plan for each of its 87 counties. The article's build script checks each qualitative claim against the data before compiling, for example that death rate, poverty and income are not significant in Model 1 and that regional awards fell in every round. The build stops if any claim fails. A full rebuild in a fresh folder reproduced every table, both statistics files and the article source exactly.

## Release check (November 15, 2026)

1. **Author's text.** The article text was rewritten by the author. It was then rebuilt from the same template, so that the numbers linked to the data are still filled from `report/stats.json` and `report/analysis.json`, and the build's claim checks still pass.
2. **Independent recomputation.** `tools/audit_paper_numbers.py` recomputes 46 headline figures straight from the released CSV files, without using the statistics files the paper is built from. All 46 match the compiled article. Among them are the award and dollar totals, coverage by county group, the chi-square tests, the gap county counts and deaths, the states with the most gap counties, and dollars per death. The few numbers that are typed in the text, rather than filled from the data, were checked by hand against `report/analysis.json`: the Moran permutation p-values, the share of gap-county deaths on state-owned roads, and the urban–rural gap in the first and last rounds.
3. **DOT's rural share.** DOT's own rural or urban label gives a rural share of 49 to 52 percent of awards in each round. This supports the article's statement that about half of each round's awards went to communities DOT classes as rural.
