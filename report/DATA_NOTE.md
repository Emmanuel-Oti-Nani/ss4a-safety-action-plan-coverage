# Safety Action Plan Coverage in Rural America: SS4A Awards Dataset, FY2022-FY2026: Data Note

Emmanuel Oti Nani, Independent Researcher, Springfield, Missouri, USA; Sedinam Annie Barney, Independent Researcher

## Purpose

The Safe Streets and Roads for All (SS4A) program, created by the Infrastructure Investment and Jobs Act, funded local and regional road safety action plans and projects in fiscal years 2022 through 2026. DOT publishes the awards round by round. No single public table links each award to the places it covers or to local fatality burden. This data set fills that gap and asks one question: which high-fatality rural counties still have no SS4A-funded safety action plan?

## Data

The build combines DOT's own award map layers, which back the official SS4A awards maps, into 2,659 award records worth $4.93 billion: FY2022: 511 awards, $802.2 million; FY2023: 620 awards, $895.7 million; FY2024: 710 awards, $1.24 billion; FY2025: 521 awards, $982.2 million; FY2026: 297 awards, $1.01 billion. Counts and dollars match DOT's official award lists exactly for every year and every state. DOT's FY2022 map layer lacked 2 of the 511 FY2022 awards; they were added from DOT's award list. Three award areas that DOT's map layer drew in the wrong place were replaced with Census boundaries.

Recipients are coded as city (1,527), county (518), tribe (97), regional council (163), metropolitan planning organization (157), or other (197). Grant types are: action plan only (1,299), action plan with supplemental planning or demonstration (437), supplemental planning or demonstration only (601), and implementation (322).

Each award area is laid over 2020 Census block-group population centers, counties and places. A county counts as **covered** when at least half of its 2020 residents live inside one or more award areas that fund developing or updating an action plan. **Rural counties** are those where at least half of residents live outside 2020 Census urban areas (2,010 counties). **High-fatality rural counties** are the top quarter of rural counties by traffic deaths per 100,000 residents per year, 2020 to 2024, among rural counties with at least 5 deaths in that period. The rate threshold is 33.14 (448 counties).

## Findings

- About 70.7% of U.S. residents live inside an SS4A action plan area. The figure is 75.4% in urban counties and 42.6% in rural counties.
- 62% of urban counties are covered, compared with 37% of rural counties, even though rural counties have the higher death rate (21.9 against 10.7 deaths per 100,000 residents per year, 2020 to 2024).
- High-fatality rural counties are covered at about the same rate as other rural counties (35% and 37%). The program did not reach the deadliest rural counties any better than rural counties in general.
- 290 of 448 high-fatality rural counties (64.7%) are not covered, and 262 have no plan area at all. They recorded 8,361 deaths from 2020 to 2024.
- 130 of these gap counties border a county where a regional council or metropolitan planning organization already has a funded plan. That body is a natural partner for the next plan.
- The states with the most gap counties are TX (39), MS (26), GA (22), AR (20), CO (14).
- The result holds under stricter rules: 298 gap counties when 55 award areas that may be drawn larger than the plan are set aside, and 303 when only FY2022 to FY2025 awards are counted.

## Use

Regional councils and states can use the county gap table and the regional body table to see which high-fatality rural counties lack a funded plan and which neighboring bodies already have one. Researchers can join the award table to other county data by FIPS code.

## Availability

Data, code and documents: https://github.com/Emmanuel-Oti-Nani/ss4a-safety-action-plan-coverage; archived at [doi:10.5281/zenodo.24250593](https://doi.org/10.5281/zenodo.24250593). License: CC BY 4.0 (data and documents), MIT (code).
