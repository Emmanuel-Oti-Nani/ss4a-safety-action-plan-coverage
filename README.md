# Safety Action Plan Coverage in Rural America: SS4A Awards Dataset, FY2022-FY2026

**Status:** Released | Version 1.0.2 | DOI: [doi:10.5281/zenodo.24250593](https://doi.org/10.5281/zenodo.24250593)
**Author:** Emmanuel Oti Nani (Independent Researcher, Springfield, Missouri, USA), ORCID [0009-0009-4175-8962](https://orcid.org/0009-0009-4175-8962)

## In plain language

Safe Streets and Roads for All (SS4A) is the federal grant program that, from 2022 to 2026, paid local, regional and tribal governments to prepare road safety action plans and to build the projects those plans identify. A community must have an action plan before it can win SS4A construction money. The U.S. Department of Transportation (DOT) publishes the awards one funding round at a time, in separate lists and maps.

This data set brings all five rounds into one table: 2,659 awards totaling $4.93 billion, checked against DOT's official award lists for every year and state. Each award is coded by type of recipient and type of grant, and is placed on the map at the counties, cities and towns its plan covers.

Plan coverage is then compared with county traffic deaths from the U.S. Rural Road Fatality County Panel (DOI [10.5281/zenodo.23547649](https://doi.org/10.5281/zenodo.23547649)). Of the 448 rural counties with the highest traffic death rates, **290 (64.7%) have no SS4A-funded action plan covering most of their residents**, and 262 have none at all. These 290 counties recorded 8,361 traffic deaths from 2020 to 2024. For each one, the coverage gap table names any neighboring regional council or metropolitan planning organization that already holds a funded plan, a practical starting point for the next application.

## What is in this package

| File | What it is |
|---|---|
| `data/processed/ss4a_awards_fy2022_2026.csv` | One row per award (2,659 rows). Recipient, state, recipient type, grant type, dollars, residents in the award area, counties and places covered. |
| `data/processed/ss4a_awards_fy2022_2026.gpkg` | The same awards with their map shapes (GeoPackage, opens in QGIS or ArcGIS). |
| `data/processed/ss4a_awards_fy2022_2026_web.geojson` | Simplified map shapes for web maps. |
| `data/processed/county_coverage_gap_table.csv` | One row per county (3,143 rows): deaths 2020-2024, rural status, share of residents in a funded plan area, coverage status, gap flag, and the awards and regional bodies that reach it. |
| `data/processed/regional_body_coverage_table.csv` | One row per regional council or metropolitan planning organization with an SS4A award (271 rows), with the counties its plans cover. |
| `data/processed/state_coverage_summary.csv` | Rural coverage and gap counts by state. |
| `data/processed/award_county_crosswalk.csv`, `award_place_crosswalk.csv` | Which counties and Census places each award covers, with population shares. |
| `data/processed/qa_report.txt` | Quality checks: totals against DOT, matching rates, spot checks. Read this first. |
| `report/DATA_NOTE.md`, `report/figures/`, `report/tables/priority_gap_counties.csv` | Short data note, three figures, and the priority list of gap counties. |
| `paper/main.pdf`, `paper/main.tex` | Research article (about 6,700 words, 5 figures, 7 tables), built from the same numbers (`code/09_analysis.py`, `code/08_paper.py`). |
| `report/analysis.json` | Results of the extended analyses: coverage by round, plans to implementation, regression models, dollars per death, road ownership, spatial clustering, state comparison. |
| `docs/` | Codebook, coding rules, limitations, verification checklist, glossary, publishing guide. |

## Fiscal years

FY2022: 511 awards, $802.2 million; FY2023: 620 awards, $895.7 million; FY2024: 710 awards, $1.24 billion; FY2025: 521 awards, $982.2 million; FY2026: 297 awards, $1.01 billion. The fiscal year 2022 to 2025 subset named in the original project plan is the column `in_core_fy2022_2025` (2,362 awards). Fiscal year 2026 was added because DOT announced those awards on October 29, 2026. It is the last of the five fiscal years (2022 to 2026) for which the Infrastructure Investment and Jobs Act appropriated SS4A funds.

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
python code/08_paper.py      # builds paper/main.pdf (needs TeX Live: lineno, natbib, orcidlink, draftwatermark)
```

The last lines of `04_outputs.py` print the headline numbers. They should show 2,659 awards and 290 gap counties.

## Sources

| Source | Vintage | Terms |
|---|---|---|
| U.S. DOT SS4A award map layers (ArcGIS Online organization behind https://www.transportation.gov/grants/ss4a award maps) | FY2022-FY2026, accessed November 2026 | U.S. government work, public domain |
| U.S. DOT published award totals (2022-2026 award pages) | as posted | public domain |
| U.S. Census Bureau 2020 cartographic boundary files (counties, places) | 2020 | public domain |
| U.S. Census Bureau 2020 centers of population by block group | 2020 | public domain |
| U.S. Rural Road Fatality County Panel v1.0.0 (FARS 2015-2024) | v1.0.0 | CC BY 4.0 |

Every download is logged with size and SHA-256 fingerprint in `data/raw/PROVENANCE.txt`.

## Limitations

See `docs/LIMITATIONS.md`. The most important: this dataset shows plans **funded by SS4A**. A county with no SS4A plan may still have a state or local safety plan paid for another way.

## License and citation

Code: MIT. Data and documents: CC BY 4.0. Please cite:

Emmanuel Oti Nani. (2026). *Safety Action Plan Coverage in Rural America: SS4A Awards Dataset, FY2022-FY2026* (Version 1.0.2) [Data set]. Zenodo. [doi:10.5281/zenodo.24250593](https://doi.org/10.5281/zenodo.24250593)

Maintainer: Emmanuel Oti Nani, Independent Researcher, Springfield, Missouri, USA. Repository: https://github.com/Emmanuel-Oti-Nani/ss4a-safety-action-plan-coverage
