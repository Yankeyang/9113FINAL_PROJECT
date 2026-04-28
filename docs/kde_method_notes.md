# KDE Method Notes

## Why the KDE Method Was Revised

The first KDE map used a single automatic bandwidth over the full state. It showed broad charger concentration, but it was hard to interpret because California is large and charger clusters occur at different spatial scales.

The revised method follows two ideas from the course readings:

1. KDE should be interpreted as an exploratory point-pattern method rather than a precise demand measure.
2. Hotspot results are scale-sensitive, so more than one search radius should be tested.

## Reading-Inspired Method

Caetano et al. (2024) used multiple KDE radii and classified intensity into quartiles. Kortas et al. (2022) emphasized that hotspot patterns can change when the scale of analysis changes.

Following this logic, this project now uses:

- A fixed-radius quartic kernel.
- EVSE-weighted charger points.
- Multiple search radii: 2 miles, 5 miles, and 10 miles.
- Census tract centroids as the KDE evaluation locations.
- Quartile classes among tracts with nonzero KDE values.

## KDE Formula

For each census tract centroid, charger points within a search radius contribute to the KDE value. Chargers closer to the tract centroid receive more weight, while chargers near the edge of the search radius receive less weight.

The project uses a quartic kernel:

```text
KDE_i = sum_j [ 3 / (pi * r^2) * w_j * (1 - (d_ij / r)^2)^2 ]
```

Where:

- `i` is a census tract centroid.
- `j` is a charger point within the search radius.
- `r` is the search radius.
- `d_ij` is the distance between tract centroid `i` and charger point `j`.
- `w_j` is the EVSE weight at charger point `j`.
- Output units are EVSE intensity per square mile.

## Why Use EVSE Weights

The charger point layer contains both station locations and EVSE port counts. A station with many ports has more infrastructure capacity than a station with one port. Therefore, KDE is weighted by:

```text
total_evse = L1_evse + L2_evse + DCFC
```

If a point has zero recorded EVSE, it receives a minimum weight of 1 so that the station still contributes to the point-pattern surface.

## Why Use 2, 5, and 10 Miles

The radii are used to reveal different spatial meanings:

- 2 miles: neighborhood-scale concentration.
- 5 miles: urban district / local travel-shed concentration.
- 10 miles: metropolitan-scale infrastructure concentration.

The 5-mile KDE is recommended as the main benchmark-region map because it balances local detail and regional readability.

## How to Interpret KDE Values

KDE values do not represent the exact number of chargers inside a tract. They represent the relative local intensity of charger infrastructure around each tract centroid.

Higher KDE values mean:

- More nearby charger infrastructure.
- More EVSE capacity nearby.
- Stronger local charger clustering.

Lower KDE values mean:

- Sparse nearby charger infrastructure.
- Weaker local clustering.

## How KDE Supports the Project

KDE is used to identify EV charging infrastructure benchmark regions. These are areas where existing charger deployment is relatively mature and spatially concentrated.

The KDE outputs support the selection of:

- Los Angeles region
- San Francisco Bay Area
- San Diego region

These benchmark regions can then be used to train a model that learns the relationship between census tract characteristics and existing charger deployment.

## Outputs

Tract-level KDE dataset:

```text
data/processed/ca_tract_charger_join_with_kde.gpkg
data/processed/ca_tract_charger_join_with_kde.csv
```

New fields:

```text
kde_evse_2mi
kde_evse_2mi_q
kde_evse_5mi
kde_evse_5mi_q
kde_evse_10mi
kde_evse_10mi_q
```

Figures:

```text
outputs/figures/ca_tract_multiscale_kde_quartiles.png
outputs/figures/benchmark_regions_5mi_kde_quartiles.png
```

## Suggested Report Language

Kernel Density Estimation (KDE) was used to explore the spatial concentration of existing public EV charging infrastructure. Following a multi-scale hotspot mapping approach, EVSE-weighted KDE values were calculated at census tract centroids using 2-mile, 5-mile, and 10-mile search radii. The KDE values represent relative charger infrastructure intensity rather than exact charger counts. The 2-mile radius captures neighborhood-scale clustering, the 5-mile radius captures local urban infrastructure concentration, and the 10-mile radius captures broader metropolitan-scale patterns. Because hotspot patterns are sensitive to analytical scale, the multi-radius approach provides a more robust basis for identifying EV charging infrastructure benchmark regions.

