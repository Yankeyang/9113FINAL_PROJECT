# Modeling and Matching Strategy

## Analysis Unit

The recommended final analysis unit is the census tract.

Reason:

- ACS socioeconomic variables are available at census tract scale.
- Equity and policy interpretation is easier at tract scale.
- Los Angeles and San Francisco can be compared consistently.

The original CEC quarter-mile hexagons should be preserved in raw and intermediate files, but summarized to census tracts for the final model.

## Target Variables

Use CEC modeled demand as the target or benchmark.

Primary target:

```text
ev_no_2mi
```

Meaning:

2024 EVs without home charging and without sufficient public Level 2 or DC fast charging within 2 miles.

Secondary targets:

```text
ev_no_walk
vf_nohome
```

## Supply Variables

From the CEC existing public charger point layer:

```text
l2_supply = sum(L2_evse)
dcfc_supply = sum(DCFC)
total_supply = sum(L1_evse + L2_evse + DCFC)
```

These should be spatially joined or aggregated to census tracts.

## Gap Variables

Baseline gap:

```text
gap_2mi = demand_2mi - total_supply
```

Walking-distance gap:

```text
gap_walk = demand_walk - l2_supply
```

Priority flag:

```text
underserved = gap_2mi > 0 and demand_2mi is in the top 25 percent
```

## Predictors

Use ACS 2020-2024 5-year variables and CEC SB1000 classifications.

Recommended predictors:

- Total population
- Population density
- Median household income
- Housing density
- Renter share
- Owner share
- Multifamily housing share
- Zero-vehicle household share
- Public transit commute share
- Work-from-home share
- CEC disadvantaged community flag
- CEC income group
- CEC priority population flag
- Urban/rural classification

## Model Design

### Baseline

Train a multilinear regression model using Los Angeles census tracts.

Target options:

- `demand_2mi`
- `gap_2mi`

### Transfer Test

Apply the Los Angeles-trained model to San Francisco census tracts.

Compare:

- Predicted demand or gap
- CEC observed demand
- Existing charger supply
- Residuals

### Optional Extensions

- Random forest regression
- Gradient boosting
- Spatial autocorrelation check on residuals
- Separate models for high-utilization and low-utilization scenarios

## Expected Outputs

```text
data/processed/tract_level_ev_gap_dataset.geojson
outputs/tables/model_performance.csv
outputs/tables/top_underserved_tracts.csv
outputs/figures/demand_supply_gap_map.png
outputs/figures/model_residuals_map.png
```

