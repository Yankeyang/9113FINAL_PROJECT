# California EV Charger Demand Prediction and Gap Analysis

## Project Goal

This project analyzes the spatial distribution of electric vehicle charging infrastructure and near-home public charging demand in California. The workflow combines California Energy Commission SB 1000 demand hexagons, existing public charger locations, census tract boundaries, socioeconomic variables, spatial hotspot analysis, and a predictive or explanatory model.

The final output will identify census tracts where modeled near-home charging demand is high but existing charger supply is low, with interpretation for equity, urban planning, commuting, housing, and infrastructure investment.

## Research Question

Where is near-home public EV charging demand concentrated in California, and which census tracts may need additional charging infrastructure?

## Project Structure

```text
EV_Charger_Final_Project/
├── data/
│   ├── raw/                 # Original downloaded datasets
│   └── processed/           # Cleaned, joined, and model-ready datasets
├── docs/                    # Notes, data dictionaries, workflow references
├── notebooks/               # Jupyter notebooks for analysis and modeling
├── outputs/
│   ├── figures/             # Maps, charts, KDE outputs, comparison figures
│   └── tables/              # Summary tables and model results
├── report/                  # Final written report and presentation materials
├── src/                     # Reusable Python scripts and helper functions
└── README.md
```

## Workflow

### 1. Define Research Question

Clarify the main analytical question:

- Where are EV chargers currently concentrated?
- Which census tracts have high predicted demand but low existing charger supply?
- Do infrastructure gaps relate to socioeconomic, housing, commuting, or urban form variables?

Expected output:

- A short research question statement in `docs/research_question.md`

### 2. Data Collection

Collect four main categories of data. The primary source is the California Energy Commission SB 1000 map supplied for this project.

#### 2.1 CEC Near-Home Charging Demand and Existing Chargers

Primary source:

- California Energy Commission, Near-Home Public Charging Demand From Electric Vehicles Without Home Charging

Project source URL:

```text
https://cecgis-caenergy.opendata.arcgis.com/maps/CAEnergy::near-home-public-charging-demand-from-electric-vehicles-without-home-charging/explore
```

Confirmed ArcGIS feature layers:

```text
High-utilization demand hexagons:
https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/sb_1000_results_high_2025/FeatureServer/0

Low-utilization demand hexagons:
https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/sb_1000_results_low_2025/FeatureServer/0

Existing public chargers as of March 2025:
https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/public_chargers_afdc_20250313/FeatureServer/0
```

Important demand fields:

- `ev_no_2mi`: 2024 EVs without home charging and without sufficient public Level 2 or DC fast charging within 2 miles
- `ev_no_walk`: 2024 EVs without home charging and without sufficient public Level 2 charging within walking distance
- `vf_nohome`: EVs in a 100% EV future without home charging

Important supply fields:

- `L1_evse`
- `L2_evse`
- `DCFC`
- `Charger_Type`

Save raw file to:

```text
data/raw/cec_sb1000_demand_high.geojson
data/raw/cec_sb1000_demand_low.geojson
data/raw/cec_existing_public_chargers.geojson
```

#### 2.2 Census Tract Boundaries

Recommended source:

- U.S. Census TIGER/Line shapefiles

Use:

- 2024 California census tracts

Required geography:

- California census tracts
- Los Angeles census tracts
- San Francisco census tracts

Save raw boundary files to:

```text
data/raw/census_tract_boundaries/
```

#### 2.3 Census Socioeconomic Variables

Recommended source:

- U.S. Census Bureau 2020-2024 American Community Survey 5-year estimates

Candidate variables:

- Total population
- Median household income
- Housing units
- Vehicle availability
- Commute mode
- Commute time
- Employment
- Population density
- Housing density
- Race and ethnicity variables, if equity analysis is included

Save raw ACS data to:

```text
data/raw/acs_socioeconomic_variables.csv
```

#### 2.4 CEC Equity and Urban-Rural Classifications

Recommended source:

- CEC SB 1000 population layer

Confirmed ArcGIS feature layer:

```text
https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/sb1000_2025_populations/FeatureServer/0
```

Important fields:

- `DAC`
- `Income_Group`
- `Priority_pop`
- `Pop_dens`
- `COUNTYFP`
- `Tract`

More detail is documented in:

```text
docs/data_sources_and_matching.md
```

### 3. Geocoding and Spatial Join

Convert CEC demand hexagons and charger point locations into a tract-level or hex-level analysis dataset.

Main tasks:

- Load CEC demand hexagons
- Load existing public charger points
- Load census tract polygons
- Set a consistent coordinate reference system
- Spatially join chargers to census tracts or demand hexagons
- Aggregate demand hexagons to census tracts if tract is the final unit
- Join ACS and CEC equity variables

Expected processed outputs:

```text
data/processed/tract_level_ev_gap_dataset.geojson
data/processed/ca_tract_model_dataset.csv
```

### 4. Exploratory Spatial Analysis

Explore charger distribution across California.

Main tasks:

- Map current charger distribution
- Calculate charger counts by tract
- Calculate charger density by population, area, or housing units
- Compare charger distribution with population and income patterns

Expected figures:

```text
outputs/figures/current_ev_charger_distribution.png
outputs/figures/charger_density_by_tract.png
```

### 5. Spatial Pattern Finding

Describe major spatial patterns from the exploratory maps.

Expected interpretation:

- EV chargers are likely concentrated in major urban and coastal regions
- Los Angeles, San Diego, and the San Francisco Bay Area are expected to show strong charger clusters
- Rural and lower-density regions may show lower charger coverage

Expected output:

```text
docs/spatial_pattern_notes.md
```

### 6. Hotspot Identification

Use KDE or other hotspot methods to identify charger concentration areas.

Main tasks:

- Run Kernel Density Estimation on charger point locations
- Map KDE intensity surface
- Identify major hotspot regions
- Compare hotspots with census tract boundaries

Expected figures:

```text
outputs/figures/kde_hotspot_map_california.png
outputs/figures/kde_hotspot_map_los_angeles.png
outputs/figures/kde_hotspot_map_san_francisco.png
```

### 7. Modeling Strategy Design

Use hotspot-rich urban regions to guide model development and cross-city transfer.

Planned strategy:

- Train the model using Los Angeles census tracts
- Test or transfer the model to San Francisco census tracts
- Use socioeconomic and urban variables as predictors
- Use charger count or charger density as the target variable

Expected output:

```text
docs/modeling_strategy.md
```

### 8. Region Selection

Define training and test regions.

Training region:

- Los Angeles census tracts

Test / transfer region:

- San Francisco census tracts

Expected processed outputs:

```text
data/processed/la_model_dataset.csv
data/processed/sf_model_dataset.csv
```

### 9. Model Inputs

Prepare predictor and target variables.

Predictor examples:

- Population
- Population density
- Median household income
- Housing density
- Commute mode
- Commute time
- Vehicle availability
- Employment density
- Urban characteristics

Target examples:

- EV charger count per census tract
- EV charger density per census tract
- EV charging ports per population, if port count is available

Expected output:

```text
data/processed/model_input_features.csv
```

### 10. Model Development

Train a model to estimate charger demand.

Baseline model:

- Multilinear regression

Possible extension:

- Semi-supervised learning
- Random forest regression
- Gradient boosting
- Spatial lag or spatial error model

Evaluation metrics:

- RMSE
- MAE
- R-squared
- Residual maps

Expected outputs:

```text
outputs/tables/model_performance.csv
outputs/figures/model_residuals_map.png
```

### 11. Demand Prediction

Use the trained model to predict expected EV charger demand for each census tract.

Main tasks:

- Predict demand for Los Angeles census tracts
- Transfer model to San Francisco census tracts
- Compare predicted values against current charger supply

Expected output:

```text
data/processed/predicted_charger_demand_by_tract.csv
```

### 12. Comparison Analysis

Compare predicted charger demand with actual charger distribution.

Main tasks:

- Map predicted demand
- Map actual charger supply
- Calculate demand-supply gap
- Rank census tracts by under-service

Expected figures:

```text
outputs/figures/predicted_charger_demand.png
outputs/figures/actual_charger_distribution.png
outputs/figures/demand_supply_gap_map.png
```

Expected table:

```text
outputs/tables/top_underserved_tracts.csv
```

### 13. Gap Identification

Identify locations where predicted demand is high but existing charger supply is low.

Classification examples:

- Underserved census tracts
- Well-served census tracts
- Over-served areas

Possible gap score:

```text
gap_score = predicted_charger_demand - actual_charger_supply
```

Expected output:

```text
data/processed/tract_gap_classification.geojson
```

### 14. Interpretation

Interpret the gap results through four lenses.

#### 14.1 Equity Issues

Evaluate whether underserved areas overlap with lower-income communities, disadvantaged communities, or areas with limited transportation access.

#### 14.2 Urban Planning Factors

Consider land use, density, urban form, and regional development patterns.

#### 14.3 Income, Housing, and Commuting Patterns

Assess how predicted demand and infrastructure gaps relate to:

- Income
- Housing density
- Vehicle access
- Commute distance or time
- Transit use

#### 14.4 Infrastructure Investment Gaps

Discuss where public or private charging investment may be missing.

Expected output:

```text
docs/interpretation_notes.md
```

### 15. Conclusion

Summarize where chargers are needed but missing and provide policy or planning recommendations.

Final deliverables:

```text
report/final_report.md
report/final_presentation.pptx
outputs/figures/final_gap_map.png
outputs/tables/final_priority_tracts.csv
```

The conclusion should answer:

- Where are EV chargers needed but missing?
- Which census tracts should be prioritized?
- What social or spatial factors explain the gaps?
- What policy or planning actions are recommended?

## Suggested Notebook Order

```text
notebooks/01_data_collection_and_cleaning.ipynb
notebooks/02_spatial_join_and_tract_aggregation.ipynb
notebooks/03_exploratory_spatial_analysis.ipynb
notebooks/04_kde_hotspot_analysis.ipynb
notebooks/05_model_training_los_angeles.ipynb
notebooks/06_model_transfer_san_francisco.ipynb
notebooks/07_gap_analysis_and_interpretation.ipynb
```

## Suggested Python Libraries

```text
pandas
geopandas
numpy
matplotlib
seaborn
scikit-learn
contextily
shapely
pyproj
folium
osmnx
```

## Final Project Checklist

- [ ] Research question finalized
- [ ] EV charger dataset downloaded
- [ ] Census tract boundary data downloaded
- [ ] ACS socioeconomic variables downloaded
- [ ] Charger points spatially joined to census tracts
- [ ] Charger counts and densities calculated
- [ ] KDE hotspot maps created
- [ ] Los Angeles training dataset prepared
- [ ] San Francisco test dataset prepared
- [ ] Baseline regression model trained
- [ ] Predicted demand calculated
- [ ] Actual supply compared with predicted demand
- [ ] Underserved tracts identified
- [ ] Equity and planning interpretation completed
- [ ] Final report and presentation completed
