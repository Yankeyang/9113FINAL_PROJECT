# Data Sources and Matching Plan

## Primary EV Charging / Demand Source

### California Energy Commission SB 1000 Near-Home Charging Demand Map

User-provided source:

https://cecgis-caenergy.opendata.arcgis.com/maps/CAEnergy::near-home-public-charging-demand-from-electric-vehicles-without-home-charging/explore

Official CEC documentation page:

https://www.energy.ca.gov/programs-and-topics/programs/clean-transportation-program/electric-vehicle-infrastructure/near-home

ArcGIS Web Map item:

https://caenergy.maps.arcgis.com/home/item.html?id=84a14cc9c59049f8abdf7f3f463e4823

This dataset is the best primary source for this project because it already contains modeled near-home public charging demand from EVs estimated to lack home charging and sufficient nearby public charging.

The CEC page states that the map displays quarter-mile hexagons and was last updated on February 4, 2026. It includes:

- 2024 EVs without home charging
- EVs in a 100% EV future without home charging
- Public nearby charging demand within 2 miles
- Public walking-distance Level 2 demand within 1/8 mile
- Existing public chargers as of March 2025
- Low-income or disadvantaged community layer
- Urban or rural layer
- Federally recognized tribal lands

## Confirmed ArcGIS Layers

### 1. High-Utilization Demand Hexagons

Feature service:

https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/sb_1000_results_high_2025/FeatureServer/0

Geometry:

- Polygon

Important fields:

- `sfh`: single-family homes within selected area
- `mfh`: multifamily homes within selected area
- `all_veh`: 2024 vehicles within selected area
- `vf_home`: EVs in 100% EV future with home charging
- `vf_nohome`: EVs in 100% EV future without home charging
- `ev_home`: 2024 EVs with home charging
- `ev_no_home`: 2024 EVs without home charging
- `ev_no_walk`: 2024 EVs without home charging and without sufficient public Level 2 charging within walking distance
- `ev_no_2mi`: 2024 EVs without home charging and without sufficient public Level 2 or DC fast charging within 2 miles

Recommended demand variables:

- Main demand target: `ev_no_2mi`
- Walking-distance demand target: `ev_no_walk`
- Future scenario target: `vf_nohome`

### 2. Low-Utilization Demand Hexagons

Feature service:

https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/sb_1000_results_low_2025/FeatureServer/0

Use this as a sensitivity scenario. The high-utilization layer can be the baseline, and the low-utilization layer can show how the gap changes when each charger is assumed to serve fewer EVs.

### 3. Existing Public Chargers

Feature service:

https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/public_chargers_afdc_20250313/FeatureServer/0

Geometry:

- Point

Important fields:

- `Latitude`
- `Longitude`
- `ID`
- `City`
- `ZIP`
- `L1_evse`
- `L2_evse`
- `DCFC`
- `Charger_Type`

Recommended supply variables:

- `l2_supply = L2_evse`
- `dcfc_supply = DCFC`
- `total_supply = L1_evse + L2_evse + DCFC`
- `nearby_supply_count`: charger points or EVSE ports spatially joined to each tract or hexagon

### 4. Low-Income / Disadvantaged / Urban-Rural Population Layer

Feature service:

https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/sb1000_2025_populations/FeatureServer/0

Geometry:

- Polygon, likely census tract geography

Important fields:

- `STATEFP`
- `COUNTYFP`
- `COUNTY`
- `Tract`
- `POPULATION_2019_5YR`
- `Pop_dens`
- `DAC`
- `Income_Group`
- `Priority_pop`

Recommended use:

- Equity classification
- Urban/rural classification
- Priority population overlay
- County filtering for Los Angeles and San Francisco

### 5. Federally Recognized Tribal Lands

Feature service:

https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/Tribal_Lands/FeatureServer/0

Use this as an overlay and interpretation layer, not as the main modeling unit.

## Matching Data Sources

### A. Census Tract Boundaries

Recommended source:

U.S. Census Bureau TIGER/Line Shapefiles, California census tracts.

Use year:

- 2024 TIGER/Line census tracts for consistency with 2024 ACS and 2024 EV estimates.

Official source:

https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2024.html

Suggested raw path:

```text
data/raw/census_tract_boundaries/tl_2024_06_tract/
```

Join key:

- `GEOID`

### B. ACS Socioeconomic Variables

Recommended source:

U.S. Census Bureau 2020-2024 ACS 5-year estimates.

Reason:

- Census tracts require ACS 5-year estimates.
- The 2020-2024 ACS 5-year estimates were released on January 29, 2026.
- These estimates align well with the CEC map's 2024 EV demand scenario.

Official source:

https://www.census.gov/programs-surveys/acs/news/data-releases/2024/release.html

Suggested API base:

```text
https://api.census.gov/data/2024/acs/acs5
```

Suggested geography:

```text
for=tract:*&in=state:06
```

Recommended ACS variables:

| Theme | Variable | Description |
|---|---:|---|
| Population | `B01003_001E` | Total population |
| Income | `B19013_001E` | Median household income |
| Housing | `B25001_001E` | Total housing units |
| Housing | `B25003_002E` | Owner-occupied units |
| Housing | `B25003_003E` | Renter-occupied units |
| Housing | `B25024_002E` | 1-unit detached structures |
| Housing | `B25024_007E` | 20 or more unit structures |
| Vehicles | `B08201_001E` | Households by vehicles available, total |
| Vehicles | `B08201_002E` | Households with no vehicle available |
| Commuting | `B08301_001E` | Means of transportation to work, total |
| Commuting | `B08301_010E` | Public transportation commuters |
| Commuting | `B08301_021E` | Worked from home |
| Commuting | `B08303_001E` | Travel time to work, total |

Derived variables:

- `population_density = total_population / tract_area`
- `housing_density = housing_units / tract_area`
- `renter_share = renter_occupied / occupied_housing_units`
- `owner_share = owner_occupied / occupied_housing_units`
- `large_multifamily_share = structures_20plus_units / total_housing_units`
- `zero_vehicle_share = zero_vehicle_households / total_households`
- `public_transit_commute_share = public_transit_commuters / total_workers`
- `work_from_home_share = worked_from_home / total_workers`

### C. Equity and Environmental Justice Context

Recommended source:

Use the CEC `sb1000_2025_populations` layer first because it is already included in the project map and contains `DAC`, `Income_Group`, and `Priority_pop`.

Optional extension:

- CalEnviroScreen 4.0 census tract scores
- SB 535 disadvantaged communities
- AB 1550 low-income communities

Use these only if the final report needs a stronger environmental justice section.

### D. County / Region Selection

The original workflow uses:

- Training region: Los Angeles County census tracts
- Test / transfer region: San Francisco County census tracts

Recommended county filters:

- Los Angeles County: `COUNTYFP = 037`
- San Francisco County: `COUNTYFP = 075`

## Spatial Matching Strategy

The CEC demand layer uses quarter-mile hexagons, while ACS variables are at census tract scale. There are two possible analysis units.

### Option 1: Census Tract as Final Unit

Recommended for the final class project.

Steps:

1. Download CEC demand hexagons.
2. Download CEC existing public charger points.
3. Download Census tract boundaries.
4. Spatially join charger points to census tracts.
5. Areal-weight or centroid-join CEC demand hexagons to census tracts.
6. Join ACS variables by tract `GEOID`.
7. Calculate tract-level demand, supply, and gap.

Advantages:

- Easy to explain.
- Matches ACS socioeconomic data.
- Supports equity and policy interpretation.
- Works well for Los Angeles and San Francisco comparison.

Main output:

```text
data/processed/tract_level_ev_gap_dataset.geojson
```

### Option 2: Hexagon as Final Unit

Use this if the instructor prefers higher spatial resolution.

Steps:

1. Keep CEC quarter-mile hexagons as the base geometry.
2. Spatially join ACS tract attributes to each hexagon.
3. Count nearby charger supply per hexagon.
4. Calculate hex-level demand and gap.

Advantages:

- Preserves the CEC map's original resolution.
- Better for fine-grained maps.

Limitation:

- ACS variables are still tract-level, so socioeconomic values are repeated across hexagons in the same tract.

## Recommended Final Variable Design

### Demand

Primary:

```text
demand_2mi = ev_no_2mi
```

Secondary:

```text
demand_walk = ev_no_walk
future_no_home_demand = vf_nohome
```

### Supply

```text
l2_supply = sum(L2_evse)
dcfc_supply = sum(DCFC)
total_supply = sum(L1_evse + L2_evse + DCFC)
```

### Gap

```text
gap_2mi = demand_2mi - total_supply
gap_walk = demand_walk - l2_supply
```

### Priority Classification

Example:

```text
underserved = gap_2mi > 0 and demand_2mi is in the top 25 percent
well_served = gap_2mi <= 0
over_served = gap_2mi < 0 and total_supply is high
```

## Updated Project Logic

Because the CEC source already provides modeled demand, the project does not need to build demand entirely from scratch. The modeling section should be reframed as:

1. Use CEC demand estimates as the target or benchmark.
2. Use ACS and SB1000 socioeconomic variables to explain spatial variation in demand and gaps.
3. Train a regression model in Los Angeles to predict CEC demand or gap from tract-level variables.
4. Test model transfer in San Francisco.
5. Compare model predictions, CEC demand, and existing charger supply.

This is stronger than predicting charger demand only from charger locations because the CEC data already includes home-charging access and public-near-home access assumptions.

