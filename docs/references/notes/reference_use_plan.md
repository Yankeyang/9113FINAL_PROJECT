# Reference Use Plan for EV Charger Census Tract Project

## Project Framing

The project uses California census tracts as the main analysis unit. Existing public EV charger counts are the dependent variable. Census, ACS, housing, commuting, vehicle, and EV ownership variables are independent variables. KDE is used to identify charger concentration and justify benchmark regions such as Los Angeles, the Bay Area, and San Diego.

## Best References to Use

### 1. Zandbergen 2009: Geocoding Quality and Implications for Spatial Analysis

File:

```text
docs/references/readings/Geography Compass - 2009 - Zandbergen - Geocoding Quality and Implications for Spatial Analysis.pdf
```

Use in:

- Data cleaning
- Spatial join limitations
- Point-to-tract assignment uncertainty

Why it fits:

This article explains that geocoding errors can create positional error and incorrect assignment to geographic units. This directly supports why the project should check charger coordinates, CRS, and unmatched points after joining charger locations to census tracts.

How to cite in the report:

Use it to justify the GIS QA workflow: validating coordinates, using a consistent CRS, checking unmatched charger points, and acknowledging that point-to-polygon joins can inherit positional uncertainty.

### 2. U.S. Census Bureau 2020: Geography and the ACS

File:

```text
docs/references/readings/acs_geography_handbook_2020.pdf
```

Use in:

- Census tract analysis unit
- ACS data limitations
- Why ACS 5-year estimates are appropriate

Why it fits:

This handbook explains ACS geography, census tracts, block groups, and why small-area ACS estimates require 5-year data. This is essential for defending the choice of census tract as the project unit.

How to cite in the report:

Use it when describing the ACS variables and explaining that tract-level socioeconomic indicators come from ACS 5-year estimates.

### 3. Census Case Studies: ACS Transportation and Economic Opportunity

File:

```text
docs/references/readings/Census_case_studies.pdf
```

Use in:

- Variable selection
- Transportation and socioeconomic interpretation

Why it fits:

The case study uses ACS data to analyze transportation access, employment, income, and population. This is close to our logic of linking infrastructure access with socioeconomic variables.

How to cite in the report:

Use it to justify ACS variables such as income, commuting, population, employment, and vehicle availability.

### 4. Anselin 1995: Local Indicators of Spatial Association (LISA)

File:

```text
docs/references/readings/Geographical Analysis - April 1995 - Anselin - Local Indicators of Spatial Association LISA.pdf
```

Use in:

- Spatial clustering
- Hotspot interpretation
- Optional later-stage local Moran's I

Why it fits:

The paper introduces local spatial association statistics that identify local pockets of spatial clustering. This supports analyzing whether high charger counts or model residuals cluster spatially.

How to cite in the report:

Use it if we add local Moran's I or discuss clustered infrastructure patterns beyond visual KDE.

### 5. Ord and Getis 1995: Local Spatial Autocorrelation Statistics

File:

```text
docs/references/readings/Geographical Analysis - October 1995 - Ord - Local Spatial Autocorrelation Statistics  Distributional Issues and an.pdf
```

Use in:

- Hotspot statistics
- Getis-Ord Gi* style analysis
- Spatial clustering validation

Why it fits:

This paper develops local hotspot statistics and explicitly frames them as tools for detecting pockets of spatial association. It fits better than pure KDE if we want a statistically defensible hotspot layer.

How to cite in the report:

Use it for a later enhancement: after KDE visually identifies benchmark regions, Gi* can statistically test high-charger clusters.

### 6. Moran 1950: Notes on Continuous Stochastic Phenomena

File:

```text
docs/references/readings/Moran_1950.pdf
```

Use in:

- Spatial autocorrelation background
- Model diagnostics

Why it fits:

This is a classic foundation for spatial autocorrelation. It is useful if the final report includes Moran's I for model residuals or charger density.

How to cite in the report:

Use sparingly. It is foundational but older and mathematical. Anselin 1995 is easier to connect to our project.

### 7. Kortas et al. 2022: Multi-Scale Variability in Hotspot Mapping

File:

```text
docs/references/readings/Kortas_et_al_2022.pdf
```

Use in:

- KDE and hotspot scale sensitivity
- Explaining why full-state KDE and regional KDE show different stories

Why it fits:

The paper argues that hotspot interpretation depends on scale. This directly supports our decision to make both a statewide KDE map and regional benchmark-region KDE maps.

How to cite in the report:

Use it to justify that KDE bandwidth and map scale affect hotspot interpretation, so benchmark regions should be interpreted at multiple scales.

### 8. Rizwan et al. 2020: KDE and Urban Activity Patterns

File:

```text
docs/references/readings/Rizwan_et_al_2020.pdf
```

Use in:

- KDE precedent
- Urban point-pattern visualization

Why it fits:

The article uses KDE to estimate density and visualize urban activity patterns from geolocated point data. Our charger points are different, but methodologically similar as urban point events.

How to cite in the report:

Use it to support the use of KDE for exploratory mapping of charger concentration.

### 9. Li 2020 / GeoAI Chapter: GeoAI in Social Science

Files:

```text
docs/references/readings/Li_2020.pdf
docs/references/readings/GeoAI_Chapter.pdf
```

Use in:

- GeoAI framing
- Machine learning with spatial data
- Benchmark-region modeling

Why it fits:

The GeoAI chapter explains that GeoAI combines AI, geospatial big data, and computing, and that machine learning can support clustering, classification, and regression in social science contexts. It also notes challenges such as spatial uncertainty and geographic transferability.

How to cite in the report:

Use it to frame the model as a spatially informed machine learning or GeoAI workflow rather than a generic regression.

### 10. Song et al. 2023: Advances in Geocomputation and GeoAI for Mapping

File:

```text
docs/references/readings/Advances in geocomputation and geospatial artificial intelligence (GeoAI) for mapping.pdf
```

Use in:

- GeoAI mapping background
- Spatial prediction and decision-making
- Explaining why spatial structure matters in AI models

Why it fits:

The article reviews GeoAI and geocomputation for mapping, including spatial patterns, spatial factors, spatial prediction, and decision-making. It is a strong conceptual reference for using machine learning to map expected charger deployment and infrastructure gaps.

How to cite in the report:

Use it in the introduction or methodology to justify the overall geocomputation/GeoAI workflow.

### 11. Monmonier 2005: Lying with Maps

File:

```text
docs/references/readings/Monmonier - Lying with Maps.pdf
```

Use in:

- Map design caution
- Choropleth/KDE interpretation

Why it fits:

This article is useful for a short methods note that map design choices, classification, scale, and generalization affect interpretation.

How to cite in the report:

Use it when explaining map classification decisions, avoiding overclaiming from KDE visuals, and making maps transparent.

### 12. Boeing 2025: OSMnx Urban Networks and Amenities

File:

```text
docs/references/readings/Boeing_2025_ Geographical Analysis_Modeling and Analyzing Urban Networks and Amenities With OSMnx.pdf
```

Use in:

- Optional network/accessibility extension
- Built environment and amenity modeling

Why it fits:

This is useful if we later add network-based measures, such as distance to chargers, street-network accessibility, or OSM amenities. It is not necessary for the current tract-level join, but helpful for a stronger future extension.

How to cite in the report:

Use only if the project adds OSMnx or network accessibility.

## Useful but Secondary

### Oliver et al. 2007: Circular vs Network Buffers

Use if:

- We compare Euclidean buffers with road-network buffers around chargers or tract centroids.

Do not use if:

- The project stays at simple tract-level aggregation.

### Polisciuc et al. 2016: Hexagonal Gridded Maps

Use if:

- We discuss why CEC demand maps use hexagons or why hex grids can be useful for visualizing spatial layers.

Do not use as a main source:

- Our final analysis unit is census tract, not hexagon.

### Birch et al. 2007: Rectangular and Hexagonal Grids

Use if:

- We need a conceptual justification for hex grids.

Do not use as a main source:

- It is about ecology and grids, not urban infrastructure.

### Zandbergen / ChatGPT Geocoding

Use if:

- We geocode addresses ourselves.

Do not emphasize:

- Our charger dataset already has coordinates, so the geocoding step is not central.

## Low Priority for This Project

These readings are interesting but less directly useful for the current project:

- `GeoAI collapse  Ethical implications of synthetic geospatial data use.pdf`
- `kounadi-resch-2018-a-geoprivacy-by-design-guideline...pdf`
- `Ye_et_al_2025 - Copy.pdf`
- `Ye_et_el_2025.pdf`
- `Artificial intelligence in urban science why does it matter.pdf`
- `Advancing Urban Analytics_GeoAI Applications.pdf`
- `When_Machine_Learning_Meets_Geospatial_Data_A_Comprehensive_GeoAI_Review.pdf`
- `Spatially-Explicit_GeoAI_2025.pdf`

They can support a broad introduction about GeoAI and ethics, but they may make the report feel too general unless the instructor expects a heavy GeoAI literature section.

## Recommended Citation Set for the Final Report

Use this core set:

1. Zandbergen 2009 for geocoding / spatial data quality.
2. U.S. Census Bureau 2020 ACS geography handbook for census tract and ACS methodology.
3. Census case studies for ACS transportation and socioeconomic variables.
4. Rizwan et al. 2020 or Kortas et al. 2022 for KDE/hotspot mapping.
5. Anselin 1995 for local spatial clustering.
6. Ord and Getis 1995 for hotspot statistics if Gi* is added.
7. Li 2020 / GeoAI Chapter for GeoAI regression and transfer framing.
8. Song et al. 2023 for geocomputation and GeoAI mapping.
9. Monmonier 2005 for responsible map interpretation.

## How These Fit Our Report Structure

### Introduction

Use:

- Song et al. 2023
- Li 2020 / GeoAI Chapter

Purpose:

Frame the project as a geocomputation and GeoAI workflow for urban infrastructure analysis.

### Data and GIS Cleaning

Use:

- Zandbergen 2009
- U.S. Census Bureau 2020 ACS geography handbook

Purpose:

Justify point data cleaning, CRS consistency, point-to-tract spatial joins, and ACS tract-level variables.

### Exploratory Spatial Analysis and KDE

Use:

- Rizwan et al. 2020
- Kortas et al. 2022
- Monmonier 2005

Purpose:

Support KDE as exploratory point-pattern visualization, while acknowledging scale and cartographic interpretation issues.

### Spatial Pattern / Benchmark Regions

Use:

- Anselin 1995
- Ord and Getis 1995

Purpose:

Support later hotspot statistics and the idea that local clusters can define benchmark regions.

### Modeling and Transfer

Use:

- Li 2020 / GeoAI Chapter
- Song et al. 2023

Purpose:

Frame benchmark-region modeling as a GeoAI-inspired transfer task, while acknowledging geographic transferability as a limitation.

