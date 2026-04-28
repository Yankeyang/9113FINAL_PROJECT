# Stage 1 Outputs: Charger Points Joined to Census Tracts

## Goal

This stage uses the California Energy Commission public charger point layer as the current EV charger distribution dataset. The charger points are spatially joined to 2024 California census tracts.

The census tract is the main analysis unit for the project:

```text
one row = one census tract
```

The current charger count or EVSE count is the dependent variable for later modeling.

## Data Downloaded

### Existing Public Chargers

Source:

```text
https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/public_chargers_afdc_20250313/FeatureServer/0
```

Raw output:

```text
data/raw/cec_existing_public_chargers.geojson
```

### 2024 California Census Tracts

Source:

```text
https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_06_tract.zip
```

Raw output:

```text
data/raw/tl_2024_06_tract.zip
```

## GIS Cleaning

Cleaning steps:

- Removed records without valid point geometry.
- Converted charger EVSE fields to numeric values.
- Created `total_evse = L1_evse + L2_evse + DCFC`.
- Validated census tract geometries.
- Projected spatial data to a California Albers projection using US survey feet.
- Calculated tract area in square feet, square miles, and square kilometers.
- Spatially joined charger points to census tracts using the `within` predicate.

Primary CRS for GIS outputs:

```text
California Albers, NAD83, US survey foot
```

GeoPackage outputs preserve this feet-based CRS. GeoJSON outputs are also provided for easy sharing.

## Key Results

| Metric | Value |
|---|---:|
| Charger station points downloaded | 17,186 |
| Charger station points joined to California tracts | 17,185 |
| California census tracts | 9,129 |
| Tracts with at least one charger station | 3,510 |
| Tracts with zero charger stations | 5,619 |
| L1 EVSE | 60 |
| L2 EVSE | 37,151 |
| DCFC | 13,587 |
| Total EVSE downloaded | 50,798 |
| Total EVSE joined to tracts | 50,796 |

One charger point did not fall inside a 2024 California census tract polygon. It is saved separately for review.

## Processed Data Outputs

Primary GIS outputs:

```text
data/processed/ca_tract_charger_join.gpkg
data/processed/chargers_joined_to_tracts.gpkg
data/processed/cec_existing_public_chargers_clean.gpkg
data/processed/ca_census_tracts_2024_clean.gpkg
data/processed/chargers_not_joined_to_ca_tracts.gpkg
```

Shareable GeoJSON / CSV outputs:

```text
data/processed/ca_tract_charger_join.geojson
data/processed/ca_tract_charger_join.csv
data/processed/chargers_joined_to_tracts.geojson
data/processed/cec_existing_public_chargers_clean.geojson
data/processed/ca_census_tracts_2024_clean.geojson
data/processed/chargers_not_joined_to_ca_tracts.geojson
```

Summary table:

```text
outputs/tables/stage1_charger_join_summary.csv
```

## Figure Outputs

Tract-level charger join map:

```text
outputs/figures/ca_tract_charger_join_map.png
```

KDE hotspot map:

```text
outputs/figures/ca_ev_charger_kde_hotspot_map.png
```

## Script

The full reproducible pipeline is:

```text
src/build_charger_tract_outputs.py
```

Run from the project root:

```bash
python3 src/build_charger_tract_outputs.py
```

## Next Step

The next stage should add tract-level explanatory variables:

- ACS population
- income
- housing units
- renter share
- multifamily housing share
- commuting variables
- vehicle availability
- EV ownership or ZEV registration if available

These variables will become the independent variables for modeling current charger deployment patterns in benchmark regions.

