# Codebook

*Plain-language summary: what every column in every file means and where it comes from. The rules behind the coded columns are in [CODING_RULES.md](CODING_RULES.md).*

## File 1: `data/processed/ss4a_awards_fy2022_2026.csv` (also `.gpkg` with map shapes)

One row per SS4A award, fiscal years 2022 to 2026.

| Column | Definition | Source |
|---|---|---|
| `award_id` | Project identifier, `SS4A-FY<yy>-<nnnn>`, numbered by state and recipient within each year | derived |
| `fiscal_year` | Fiscal year of the SS4A funding round (2022 to 2026) | DOT layer |
| `in_core_fy2022_2025` | True for FY2022 to FY2025, the scope of the original plan | derived |
| `dot_award_id` | DOT's own award ID where published (FY2025 and FY2026 only) | DOT `SS4A_ID` |
| `uei` | Recipient's Unique Entity ID in SAM.gov, where published (FY2022 to FY2024) | DOT `UEI` / `SAMUEI` |
| `recipient_name` | Lead applicant, as DOT lists it (spaces trimmed) | DOT `Lead_Applicant` / `Organization_Name` |
| `state` | Two-letter state code. Where DOT listed "Federally-recognized Tribe", the state containing the award area | DOT; Census 2020 |
| `state_note` | Explains any state taken from the map | derived |
| `recipient_type` | `city`, `county`, `tribe`, `regional_council`, `mpo` (metropolitan planning organization), `other` | coded (CODING_RULES.md, rule 2) |
| `recipient_subtype` | For `other`: university, emergency services or health, transportation agency, school district, special district, state agency, county agency or county group, city or consolidated government | coded |
| `is_regional_body` | True when `recipient_type` is `regional_council` or `mpo` | derived |
| `recipient_type_basis` | How the type was set: DOT type, name rule, or manual override (with reason) | derived |
| `dot_recipient_type` | DOT's applicant or entity type, as published | DOT |
| `grant_program` | `Planning and Demonstration` (called Action Plan Grants in FY2022) or `Implementation` | DOT |
| `grant_type` | `action plan`, `action plan + supplemental/demonstration`, `supplemental/demonstration only`, `implementation` | coded (rule 3) |
| `includes_action_plan` | Award funds developing or updating a comprehensive safety action plan | coded |
| `action_plan_is_update` | The action plan part is an update of an existing plan, where DOT says so | coded |
| `includes_supp_or_demo` | Award funds supplemental planning or demonstration activities | coded |
| `includes_supplemental`, `includes_demonstration` | Split of the above, only where DOT reported it (FY2022, FY2024); blank otherwise | coded |
| `includes_implementation` | Implementation grant | coded |
| `dot_activity`, `dot_pd_detail`, `dot_round` | DOT's activity text, planning detail, and announcement round, as published | DOT |
| `dot_rural_urban` | DOT's rural or urban label (SS4A notice definition: urban areas under 200,000 count as rural) | DOT |
| `project_name` | Project title, as published | DOT |
| `federal_funding` | Federal award amount, U.S. dollars | DOT `Total_Federal_Funding` / `Federal_Request__SF_` (FY2022) |
| `total_project_cost` | Total cost including local match, where published | DOT |
| `action_plan_amount` | Dollars for the action plan activity, where published (FY2023, FY2024) | DOT `Activity_A_Amount` |
| `dot_jurisdiction_pop` | Population DOT reported for the applicant's jurisdiction | DOT |
| `source_layer`, `source_objectid` | DOT map layer and record the row came from | DOT |
| `census_pop_in_area` | 2020 residents in block groups whose population center lies inside the award area | Census 2020 |
| `n_counties` | Counties with residents inside the award area | derived |
| `primary_county_fips`, `primary_county_name` | County holding the most award-area residents | derived |
| `county_fips_list` | All counties with residents inside the award area, separated by `;` | derived |
| `n_places` | Census places with at least half their land area inside the award area | Census 2020 |
| `primary_place_geoid`, `primary_place_name` | Matched place with the largest land area inside the award | Census 2020 |
| `geo_match_flag` | Note when the award area holds no block-group population center | derived |
| `area_pop_ratio` | `census_pop_in_area` divided by `dot_jurisdiction_pop` | derived |
| `area_may_overstate_plan` | True when `area_pop_ratio` is above 2 (map shape may be larger than the plan) | derived |

## File 2: `data/processed/county_coverage_gap_table.csv`

One row per county (3,143, the 50 states and DC, 2020 county geography, matching Project 1).

| Column | Definition | Source |
|---|---|---|
| `fips`, `state`, `county_name` | County identifiers | Project 1 |
| `pop2020_census`, `pct_rural_2020` | 2020 population; percent living outside 2020 urban areas | Project 1 (Census 2020) |
| `rural_county` | `pct_rural_2020` is 50 or more | derived |
| `deaths_2020_2024`, `deaths_rural_2020_2024` | Traffic deaths 2020-2024, all and outside urban areas | Project 1 (FARS) |
| `person_years_2020_2024` | Sum of yearly population estimates 2020-2024 | Project 1 |
| `death_rate_per100k_yr` | Deaths per 100,000 residents per year, 2020-2024 | derived |
| `rate_rank_among_rural` | Rank of the rate among rural counties with at least 5 deaths (1 = highest) | derived |
| `high_fatality_rural` | Rural county in the top quarter of that rate | derived |
| `share_action_plan_area_fy22_26` | Share of 2020 residents inside any SS4A action plan award area, FY2022-FY2026 (main measure) | derived |
| `share_action_plan_area_fy22_25` | Same, FY2022-FY2025 awards only | derived |
| `share_action_plan_area_conservative_fy22_26` | Same, leaving out awards flagged `area_may_overstate_plan` | derived |
| `share_any_ss4a_area_fy22_26` | Share inside any SS4A award area of any type | derived |
| `share_regional_body_action_plan_fy22_26` | Share inside action plan areas of regional councils or MPOs | derived |
| `coverage_status` | `covered` (share 0.5 or more), `partly covered` (above 0, under 0.5), `not covered` (0) | derived |
| `coverage_status_fy22_25`, `coverage_status_conservative` | The same status under the other two measures | derived |
| `covered_any_ss4a_fy22_26` | `share_any_ss4a_area_fy22_26` is 0.5 or more | derived |
| `first_fy_action_plan_majority` | First fiscal year in which the county reached 50% action plan coverage | derived |
| `gap_flag` | High-fatality rural county that is not covered (main measure) | derived |
| `n_action_plan_awards_touching`, `action_plan_award_ids`, `action_plan_recipients` | Action plan awards with any residents in the county | derived |
| `regional_body_action_plan_recipients` | Regional councils or MPOs among them | derived |
| `neighbor_regional_body_plans` | Regional councils or MPOs whose action plan areas reach a bordering county | derived |
| `n_any_ss4a_awards_touching` | Awards of any type with residents in the county | derived |

## File 3: `data/processed/regional_body_coverage_table.csv`

One row per regional council or MPO (grouped by state and normalized name).

| Column | Definition |
|---|---|
| `regional_body`, `name_variants` | Most common name, and every spelling DOT used |
| `state`, `recipient_type` | State and coded type |
| `fiscal_years`, `award_ids`, `n_awards`, `n_action_plan_awards`, `federal_funding_total` | The body's SS4A awards |
| `n_counties_plan_majority` | Counties where the body's action plan areas hold at least half the residents |
| `n_rural_counties_plan_majority`, `n_high_fatality_rural_counties_plan_majority` | Of those, rural and high-fatality rural counties |
| `deaths_2020_2024_in_plan_majority_counties` | Deaths 2020-2024 in those counties |
| `plan_majority_county_fips` | Their FIPS codes |

## File 4: `data/processed/state_coverage_summary.csv`

One row per state: rural counties by coverage status, high-fatality rural counties, gap counties, and deaths 2020-2024 in rural and gap counties.

## Files 5 and 6: crosswalks

- `award_county_crosswalk.csv`: one row per award and county. `pop_in_award` residents of the county inside the award area; `share_of_award_pop`, `share_of_county_pop`; `assignment` notes the 65 awards placed by location because their area holds no block-group center.
- `award_place_crosswalk.csv`: one row per award and Census place with at least half its land area inside the award area. `LSAD` is the Census legal or statistical description (city, town, CDP and so on).

## File 7: `data/processed/unfunded_applicant_county_crosswalk.csv` (added in version 1.1.0)

One row per unfunded application and county. Source: DOT's lists of eligible applications that were not funded, FY2022 to FY2024 (`data/raw/ss4a_other_applicants_fy22_fy24.txt`). The FY2022 list covers implementation applications only.

| Column | Definition |
|---|---|
| `app_id` | Application identifier, `OA-<nnnn>`, in list order |
| `round` | Funding round of the list (`FY22`, `FY23`, `FY24`) |
| `applicant`, `state` | Lead applicant and state, as DOT lists them |
| `grant` | `IG` implementation or `PD` planning and demonstration |
| `pd_activity` | DOT's planning activity code, where given (for example `AP_NEW` new action plan, `AP_UPD` update) |
| `dot_rural_urban` | DOT's rural or urban label |
| `applicant_type` | DOT's applicant type |
| `fiscal_year` | Fiscal year of the round |
| `seeks_action_plan` | The application asked for a new or updated action plan |
| `county_fips` | County the application was placed in (blank if it could not be placed) |
| `pop_share` | Share of the applicant's 2020 population in that county; applicants are placed in every county holding at least 10% |
| `match_method` | How the county was found: automatic name match (place, county subdivision or county), or `manual` with certainty (`sure`, `regional`, `uncertain`); hand placements and reasons are in `data/raw/applicant_county_overrides.csv` |

## File 8: `data/processed/county_applications_travel.csv` (added in version 1.1.0)

One row per county (3,143 rows).

| Column | Definition |
|---|---|
| `fips`, `state`, `county_name` | County identifiers |
| `group` | `urban`, `other_rural`, or `hf_rural` (high-fatality rural, as in the gap table) |
| `gap` | Gap county (high-fatality rural, under half of residents in a funded action plan area) |
| `n_unfunded_apps` | Unfunded applications placed in the county, FY2022 to FY2024 |
| `n_unfunded_direct` | Of those, applications from the county itself or a place within it (not regional councils or tribes) |
| `unfunded_sought_plan` | Of those, applications that asked for an action plan |
| `unfunded_rounds`, `unfunded_applicants` | Rounds and applicant names, separated by `;` |
| `daily_vmt` | Average daily vehicle-miles traveled in 2024 (HPMS: AADT times section length, summed over sections with traffic counts) |
| `rate_per_100m_vmt` | Traffic deaths 2020-2024 per 100 million vehicle-miles, using five times the 2024 annual travel |
| `hf_vmt` | Rural county with at least five deaths and a per-mile rate in the top quarter of such counties |
| `gap_vmt` | `hf_vmt` and under half of residents in a funded action plan area |

## File 9: `report/tables/applicant_success_by_group.csv` (added in version 1.1.0)

Funded and unfunded applicants by grant type and the county group of the applicant's main county, limited to rounds where DOT published both lists. Regional applicants are excluded. Columns: `grant`, `years`, `group`, `funded`, `unfunded`, `funded_pct`.
