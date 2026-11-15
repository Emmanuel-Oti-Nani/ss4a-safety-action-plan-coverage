# Coding and matching rules

*Plain-language summary: the rules the build follows to combine awards, label recipients and grant types, place each award on the map, and decide whether a county is covered. Emmanuel Oti Nani reviews and approves these rules. Any change is recorded here first, then in the code.*

## Rule 1: Which records are awards

- One row per record in DOT's final award map layers: FY2022 `ACTION_PLAN_IMPLEMENTATION_GRANTS_MERGE` (action plan and implementation grants together, 509 records), FY2023 and FY2024 final planning and implementation layers, FY2025 `SS4A_FY25_Jurisdiction_Areas_Final_Updated_12_16_2025`, FY2026 `SS4A_FY26_Jurisdictions_Final`.
- FY2022 uses the merged layer rather than the separate action plan layer because the separate layer holds only 450 of the action plan grants.
- Two FY2022 awards on DOT's official award list but missing from every FY2022 map layer are added from that list (`code/fy2022_awards_not_on_map.csv`), with no map shape.
- Where DOT's map layer disagrees with DOT's official award list, the list wins (`code/dot_list_corrections.csv`). Where the map layer draws the wrong place, the shape is replaced with the Census 2020 boundary of the place named on the list (`code/geometry_corrections.csv`).
- Two awards to the same recipient in the same year are kept as two rows. DOT lists them separately with different dollars and projects; they are listed in the QA report.
- Contact names, email addresses and DOT internal notes in the source layers are not copied.

## Rule 2: Recipient type

Applied in order; the first match wins.

1. DOT lists a tribal government type: **tribe**.
2. DOT lists Metropolitan Planning Organization: **mpo**.
3. The name contains an MPO term (Metropolitan Planning, MPO, TPO, Transportation Planning Organization, Transportation Study, Metropolitan Council, Metroplan and similar): **mpo**.
4. The name contains a regional council term (Council of Governments, COG, Regional Council, Regional Commission, Regional Planning, Planning Commission, Planning District, Development District, Association of Governments, Area Council, Planning and Development and similar), unless it names a single county's planning commission or department: **regional_council**.
5. DOT lists City or Township: **city**. DOT lists County: **county**.
6. DOT lists Regional Organization: **regional_council**, unless the name begins or ends with City, Town or Village (**city**).
7. Anything else: **other**, with a subtype.
8. Hand corrections in `code/recipient_overrides.csv` replace the result, each with a reason.

Many MPOs are run by regional councils, so DOT's label for the same body can change between years. `is_regional_body` treats both as one group, and the regional body table and coverage measures use it.

## Rule 3: Grant type

- **Implementation** for every Implementation Grant.
- **Action plan** when DOT's activity says the award develops a new plan, develops or updates a plan, or updates an existing plan to meet SS4A requirements. FY2022 Action Plan Grants count as action plans unless DOT marked them Supplemental Planning.
- **Supplemental/demonstration** when the activity includes supplemental planning or demonstration. These are split into separate flags only where DOT reported them separately (FY2022, FY2024 detail field).
- The summary `grant_type` combines these flags.

## Rule 4: Placing awards on the map

- Award shapes are DOT's, simplified to about 20 meters, in longitude and latitude (EPSG:4326).
- Residents inside an award: a 2020 block group counts when its 2020 Census population center lies inside the shape.
- Counties for an award: every county with at least one such block group. An award with no block-group center inside is placed in the county containing its interior point and counts zero residents.
- Places for an award: every 2020 Census place with at least half its land area inside the shape (measured in the USA Contiguous Albers projection, EPSG:5070).
- State: DOT's state code, upper-cased. Where DOT wrote "Federally-recognized Tribe", the state containing the award's interior point.

## Rule 5: County coverage

- A block group is in a plan area when it lies inside at least one award with `includes_action_plan = True`. Overlapping awards are not double counted.
- County share = residents of covered block groups divided by 2020 county population.
- **Covered**: share 0.5 or more. **Partly covered**: above 0 and under 0.5. **Not covered**: 0.
- Variants: FY2022-FY2025 only; conservative (leaving out awards whose area holds more than twice the residents DOT reported); any SS4A award; regional bodies only.

## Rule 6: Rural and high-fatality counties

- **Rural county**: 50% or more of 2020 residents outside 2020 Census urban areas (Project 1 `pct_rural_2020`).
- **Fatality burden**: deaths 2020-2024 divided by summed yearly population estimates, times 100,000 (Project 1).
- **High-fatality rural county**: rural, at least 5 deaths in 2020-2024, and a rate at or above the 75th percentile of that group.
- **Gap county**: high-fatality rural and not covered.

## Rule 7: Neighboring regional bodies

For each county, the regional councils and MPOs whose action plan areas reach any county sharing a border with it (counties touching at a boundary line or point).
