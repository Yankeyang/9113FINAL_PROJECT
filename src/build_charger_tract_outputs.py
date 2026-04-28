"""Build tract-level EV charger outputs for the California project.

Pipeline:
1. Download CEC public charger points.
2. Download 2024 California census tract boundaries.
3. Clean geometries and project to California Albers.
4. Spatially join chargers to tracts.
5. Export processed GeoJSON/CSV and stage-one figures.
"""

from __future__ import annotations

import json
import math
import shutil
import ssl
import time
import zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, urlretrieve

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import gaussian_kde
from shapely.geometry import box
from shapely.geometry import shape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"

CEC_CHARGERS_URL = (
    "https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/"
    "public_chargers_afdc_20250313/FeatureServer/0/query"
)
CENSUS_TRACT_ZIP_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_06_tract.zip"
)

CRS_WGS84 = "EPSG:4326"
# California Albers is appropriate for statewide California analysis.
# EPSG:3310 is meter-based; this custom equivalent uses US survey feet,
# matching the project requirement to work in feet-based units.
CRS_CA_ALBERS_FT = (
    "+proj=aea +lat_0=0 +lon_0=-120 +lat_1=34 +lat_2=40.5 "
    "+x_0=0 +y_0=-4000000 +datum=NAD83 +units=us-ft +no_defs"
)

SSL_CONTEXT = ssl._create_unverified_context()
FT_PER_MILE = 5280


def ensure_dirs() -> None:
    for directory in [RAW_DIR, PROCESSED_DIR, FIGURE_DIR, TABLE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def fetch_json(url: str, params: dict[str, object]) -> dict:
    request_url = f"{url}?{urlencode(params)}"
    with urlopen(request_url, timeout=120, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def download_cec_chargers() -> gpd.GeoDataFrame:
    raw_path = RAW_DIR / "cec_existing_public_chargers.geojson"

    count_payload = fetch_json(
        CEC_CHARGERS_URL,
        {
            "where": "1=1",
            "returnCountOnly": "true",
            "f": "json",
        },
    )
    total = int(count_payload["count"])
    page_size = 2000
    pages = math.ceil(total / page_size)

    records = []
    for page in range(pages):
        payload = fetch_json(
            CEC_CHARGERS_URL,
            {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": 4326,
                "f": "geojson",
                "resultRecordCount": page_size,
                "resultOffset": page * page_size,
                "orderByFields": "OBJECTID",
            },
        )
        records.extend(payload.get("features", []))
        time.sleep(0.1)

    geojson = {"type": "FeatureCollection", "features": records}
    raw_path.write_text(json.dumps(geojson), encoding="utf-8")

    chargers = gpd.read_file(raw_path)
    chargers = chargers.set_crs(CRS_WGS84, allow_override=True)
    return chargers


def download_census_tracts() -> gpd.GeoDataFrame:
    zip_path = RAW_DIR / "tl_2024_06_tract.zip"
    extract_dir = RAW_DIR / "census_tract_boundaries" / "tl_2024_06_tract"

    if not zip_path.exists():
        with urlopen(CENSUS_TRACT_ZIP_URL, timeout=180, context=SSL_CONTEXT) as response:
            zip_path.write_bytes(response.read())

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    shp_path = next(extract_dir.glob("*.shp"))
    tracts = gpd.read_file(shp_path)
    tracts = tracts.to_crs(CRS_WGS84)
    return tracts


def clean_chargers(chargers: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    keep_cols = [
        "OBJECTID",
        "ID",
        "City",
        "ZIP",
        "Latitude",
        "Longitude",
        "L1_evse",
        "L2_evse",
        "DCFC",
        "Charger_Type",
        "geometry",
    ]
    chargers = chargers[[col for col in keep_cols if col in chargers.columns]].copy()
    chargers = chargers[chargers.geometry.notna() & ~chargers.geometry.is_empty].copy()
    chargers = chargers.dropna(subset=["Latitude", "Longitude"])

    for col in ["L1_evse", "L2_evse", "DCFC"]:
        if col not in chargers.columns:
            chargers[col] = 0
        chargers[col] = pd.to_numeric(chargers[col], errors="coerce").fillna(0)

    chargers["total_evse"] = chargers[["L1_evse", "L2_evse", "DCFC"]].sum(axis=1)
    chargers["station_count"] = 1
    return chargers.to_crs(CRS_CA_ALBERS_FT)


def clean_tracts(tracts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    keep_cols = [
        "STATEFP",
        "COUNTYFP",
        "TRACTCE",
        "GEOID",
        "NAME",
        "NAMELSAD",
        "ALAND",
        "AWATER",
        "geometry",
    ]
    tracts = tracts[[col for col in keep_cols if col in tracts.columns]].copy()
    tracts = tracts[tracts.geometry.notna() & ~tracts.geometry.is_empty].copy()
    tracts["geometry"] = tracts.geometry.make_valid()
    tracts = tracts.to_crs(CRS_CA_ALBERS_FT)
    tracts["tract_area_sq_ft"] = tracts.geometry.area
    tracts["tract_area_sq_mi"] = tracts["tract_area_sq_ft"] / 27_878_400
    tracts["tract_area_sq_km"] = tracts["tract_area_sq_ft"] * 0.09290304 / 1_000_000
    return tracts


def spatial_join_chargers_to_tracts(
    chargers: gpd.GeoDataFrame, tracts: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    joined = gpd.sjoin(
        chargers,
        tracts[["GEOID", "COUNTYFP", "TRACTCE", "NAMELSAD", "geometry"]],
        how="left",
        predicate="within",
    )
    joined_path = PROCESSED_DIR / "chargers_joined_to_tracts.geojson"
    joined.to_file(joined_path, driver="GeoJSON")
    joined.to_file(
        PROCESSED_DIR / "chargers_joined_to_tracts.gpkg",
        layer="chargers_joined_to_tracts",
        driver="GPKG",
    )

    unmatched = joined[joined["GEOID"].isna()].copy()
    if not unmatched.empty:
        unmatched.to_file(PROCESSED_DIR / "chargers_not_joined_to_ca_tracts.geojson")
        unmatched.to_file(
            PROCESSED_DIR / "chargers_not_joined_to_ca_tracts.gpkg",
            layer="unmatched_chargers",
            driver="GPKG",
        )

    summary = (
        joined.dropna(subset=["GEOID"])
        .groupby("GEOID", as_index=False)
        .agg(
            station_count=("station_count", "sum"),
            l1_evse=("L1_evse", "sum"),
            l2_evse=("L2_evse", "sum"),
            dcfc=("DCFC", "sum"),
            total_evse=("total_evse", "sum"),
        )
    )

    tract_chargers = tracts.merge(summary, on="GEOID", how="left")
    fill_cols = ["station_count", "l1_evse", "l2_evse", "dcfc", "total_evse"]
    tract_chargers[fill_cols] = tract_chargers[fill_cols].fillna(0)
    tract_chargers["stations_per_sq_mi"] = (
        tract_chargers["station_count"] / tract_chargers["tract_area_sq_mi"]
    )
    tract_chargers["evse_per_sq_mi"] = (
        tract_chargers["total_evse"] / tract_chargers["tract_area_sq_mi"]
    )

    tract_chargers.to_file(
        PROCESSED_DIR / "ca_tract_charger_join.geojson", driver="GeoJSON"
    )
    tract_chargers.to_file(
        PROCESSED_DIR / "ca_tract_charger_join.gpkg",
        layer="ca_tract_charger_join",
        driver="GPKG",
    )
    tract_chargers.drop(columns="geometry").to_csv(
        PROCESSED_DIR / "ca_tract_charger_join.csv", index=False
    )
    return joined, tract_chargers


def quartic_kde_at_points(
    source_xy: np.ndarray,
    target_xy: np.ndarray,
    weights: np.ndarray,
    radius_ft: float,
) -> np.ndarray:
    """Evaluate a quartic kernel density at target coordinates.

    Output is weight density per square mile. The quartic kernel follows the
    common GIS form where weights decline smoothly to zero at the search radius.
    """
    tree = cKDTree(source_xy)
    radius_sq_mi = (radius_ft / FT_PER_MILE) ** 2
    normalizer = 3 / (math.pi * radius_sq_mi)
    values = np.zeros(len(target_xy), dtype=float)

    neighbors = tree.query_ball_point(target_xy, r=radius_ft)
    for idx, neighbor_idx in enumerate(neighbors):
        if not neighbor_idx:
            continue
        src = source_xy[neighbor_idx]
        d = np.linalg.norm(src - target_xy[idx], axis=1)
        u = d / radius_ft
        kernel = (1 - u**2) ** 2
        values[idx] = normalizer * np.sum(weights[neighbor_idx] * kernel)
    return values


def add_multiscale_kde_to_tracts(
    chargers: gpd.GeoDataFrame, tract_chargers: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Add EVSE-weighted KDE values at tract centroids for several radii."""
    tract_chargers = tract_chargers.copy()
    centroids = tract_chargers.geometry.centroid
    target_xy = np.column_stack([centroids.x, centroids.y])
    source_xy = np.column_stack([chargers.geometry.x, chargers.geometry.y])
    weights = chargers["total_evse"].replace(0, 1).to_numpy()

    for radius_mi in [2, 5, 10]:
        col = f"kde_evse_{radius_mi}mi"
        qcol = f"kde_evse_{radius_mi}mi_q"
        tract_chargers[col] = quartic_kde_at_points(
            source_xy, target_xy, weights, radius_mi * FT_PER_MILE
        )
        positive = tract_chargers[col] > 0
        tract_chargers[qcol] = "No nearby EVSE"
        if positive.any():
            tract_chargers.loc[positive, qcol] = pd.qcut(
                tract_chargers.loc[positive, col],
                q=4,
                labels=["Q1 low", "Q2", "Q3", "Q4 high"],
                duplicates="drop",
            ).astype(str)

    tract_chargers.to_file(
        PROCESSED_DIR / "ca_tract_charger_join_with_kde.gpkg",
        layer="ca_tract_charger_join_with_kde",
        driver="GPKG",
    )
    tract_chargers.drop(columns="geometry").to_csv(
        PROCESSED_DIR / "ca_tract_charger_join_with_kde.csv", index=False
    )
    return tract_chargers


def plot_tract_join_map(tract_chargers: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 13))
    tract_chargers.plot(
        column="total_evse",
        ax=ax,
        cmap="viridis",
        linewidth=0.05,
        edgecolor="#f7f7f7",
        legend=True,
        scheme="UserDefined",
        classification_kwds={"bins": [0, 2, 5, 10, 25, 50, 100]},
        missing_kwds={"color": "#efefef"},
        legend_kwds={"title": "EVSE ports by tract"},
    )
    ax.set_title(
        "Existing Public EV Chargers Joined to California Census Tracts",
        fontsize=16,
        pad=12,
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "ca_tract_charger_join_map.png", dpi=220)
    plt.close(fig)


def plot_kde_map(chargers: gpd.GeoDataFrame, tracts: gpd.GeoDataFrame) -> None:
    points = chargers.geometry
    weights = chargers["total_evse"].replace(0, 1).to_numpy()
    xy = np.vstack([points.x.to_numpy(), points.y.to_numpy()])
    kde = gaussian_kde(xy, weights=weights)

    minx, miny, maxx, maxy = tracts.total_bounds
    nx = 420
    ny = 520
    x_grid = np.linspace(minx, maxx, nx)
    y_grid = np.linspace(miny, maxy, ny)
    xx, yy = np.meshgrid(x_grid, y_grid)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)

    fig, ax = plt.subplots(figsize=(11, 13))
    tracts.boundary.plot(ax=ax, linewidth=0.03, color="#d9d9d9", alpha=0.35)
    image = ax.imshow(
        zz,
        extent=[minx, maxx, miny, maxy],
        origin="lower",
        cmap="inferno",
        alpha=0.82,
    )
    chargers.plot(ax=ax, markersize=0.25, color="white", alpha=0.25)
    fig.colorbar(image, ax=ax, fraction=0.032, pad=0.01, label="KDE intensity")
    ax.set_title(
        "KDE Hotspot Map of Existing Public EV Chargers in California",
        fontsize=16,
        pad=12,
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "ca_ev_charger_kde_hotspot_map.png", dpi=220)
    plt.close(fig)


def _kde_grid(
    chargers: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float],
    nx: int = 360,
    ny: int = 360,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    minx, miny, maxx, maxy = bounds
    subset = chargers.cx[minx:maxx, miny:maxy].copy()
    if len(subset) < 5:
        return np.array([]), np.array([]), np.array([])

    points = subset.geometry
    weights = subset["total_evse"].replace(0, 1).to_numpy()
    xy = np.vstack([points.x.to_numpy(), points.y.to_numpy()])
    kde = gaussian_kde(xy, weights=weights)

    x_grid = np.linspace(minx, maxx, nx)
    y_grid = np.linspace(miny, maxy, ny)
    xx, yy = np.meshgrid(x_grid, y_grid)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    return xx, yy, zz


def plot_clean_kde_map(chargers: gpd.GeoDataFrame, tracts: gpd.GeoDataFrame) -> None:
    minx, miny, maxx, maxy = tracts.total_bounds
    _, _, zz = _kde_grid(chargers, (minx, miny, maxx, maxy), nx=440, ny=540)
    x_grid = np.linspace(minx, maxx, zz.shape[1])
    y_grid = np.linspace(miny, maxy, zz.shape[0])

    threshold = np.nanpercentile(zz, 72)
    zz_masked = np.where(zz >= threshold, zz, np.nan)
    vmax = np.nanpercentile(zz_masked, 99.7)

    fig, ax = plt.subplots(figsize=(11, 13), facecolor="white")
    tracts.dissolve().boundary.plot(ax=ax, linewidth=0.8, color="#555555")
    tracts.boundary.plot(ax=ax, linewidth=0.02, color="#d6d6d6", alpha=0.25)
    image = ax.imshow(
        zz_masked,
        extent=[minx, maxx, miny, maxy],
        origin="lower",
        cmap="magma",
        alpha=0.9,
        vmax=vmax,
    )
    fig.colorbar(image, ax=ax, fraction=0.032, pad=0.01, label="High-density KDE intensity")
    ax.set_title(
        "California EV Charger KDE Hotspots\nHigh-density areas only",
        fontsize=16,
        pad=12,
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "ca_ev_charger_kde_hotspot_map_clean.png", dpi=240)
    plt.close(fig)


def plot_multiscale_tract_kde_maps(tract_chargers: gpd.GeoDataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 7), facecolor="white")
    bins = {
        "No nearby EVSE": "#f1f1f1",
        "Q1 low": "#d9f0d3",
        "Q2": "#addd8e",
        "Q3": "#41ab5d",
        "Q4 high": "#005a32",
    }

    for ax, radius_mi in zip(axes, [2, 5, 10]):
        qcol = f"kde_evse_{radius_mi}mi_q"
        plot_df = tract_chargers.copy()
        plot_df["_color"] = plot_df[qcol].map(bins).fillna("#f1f1f1")
        plot_df.plot(ax=ax, color=plot_df["_color"], linewidth=0.02, edgecolor="#ffffff")
        tract_chargers.dissolve().boundary.plot(ax=ax, linewidth=0.6, color="#555555")
        ax.set_title(f"{radius_mi}-mile KDE radius", fontsize=13)
        ax.set_axis_off()

    handles = [
        plt.Line2D([0], [0], marker="s", color="none", markerfacecolor=color, markersize=10, label=label)
        for label, color in bins.items()
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False)
    fig.suptitle(
        "Multi-Scale EVSE-Weighted KDE by Census Tract Centroid",
        fontsize=17,
        y=0.96,
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.93])
    fig.savefig(FIGURE_DIR / "ca_tract_multiscale_kde_quartiles.png", dpi=240)
    plt.close(fig)


def plot_benchmark_region_kde_quartile_maps(tract_chargers: gpd.GeoDataFrame) -> None:
    regions = {
        "Los Angeles Region": (-119.1, 33.45, -117.55, 34.45),
        "San Francisco Bay Area": (-122.65, 37.15, -121.65, 38.05),
        "San Diego Region": (-117.45, 32.45, -116.75, 33.15),
    }
    bins = {
        "No nearby EVSE": "#f4f4f4",
        "Q1 low": "#fee8c8",
        "Q2": "#fdbb84",
        "Q3": "#e34a33",
        "Q4 high": "#7f0000",
    }

    fig, axes = plt.subplots(1, 3, figsize=(17, 6), facecolor="white")
    for ax, (title, lonlat_bounds) in zip(axes, regions.items()):
        region_poly = gpd.GeoSeries([box(*lonlat_bounds)], crs=CRS_WGS84).to_crs(
            CRS_CA_ALBERS_FT
        )
        minx, miny, maxx, maxy = tuple(region_poly.total_bounds)
        region = tract_chargers.cx[minx:maxx, miny:maxy].copy()
        region["_color"] = region["kde_evse_5mi_q"].map(bins).fillna("#f4f4f4")
        region.plot(ax=ax, color=region["_color"], linewidth=0.16, edgecolor="#ffffff")
        region.boundary.plot(ax=ax, linewidth=0.12, color="#686868", alpha=0.45)
        ax.set_title(title, fontsize=13)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_axis_off()

    handles = [
        plt.Line2D([0], [0], marker="s", color="none", markerfacecolor=color, markersize=10, label=label)
        for label, color in bins.items()
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False)
    fig.suptitle(
        "Benchmark Region KDE Classes Using a 5-mile Search Radius",
        fontsize=17,
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.93])
    fig.savefig(FIGURE_DIR / "benchmark_regions_5mi_kde_quartiles.png", dpi=240)
    plt.close(fig)


def plot_regional_kde_maps(chargers: gpd.GeoDataFrame, tracts: gpd.GeoDataFrame) -> None:
    regions = {
        "Los Angeles Region": (-119.1, 33.45, -117.55, 34.45),
        "San Francisco Bay Area": (-122.65, 37.15, -121.65, 38.05),
        "San Diego Region": (-117.45, 32.45, -116.75, 33.15),
    }

    fig, axes = plt.subplots(1, 3, figsize=(17, 6), facecolor="white")
    for ax, (title, lonlat_bounds) in zip(axes, regions.items()):
        region_poly = gpd.GeoSeries([box(*lonlat_bounds)], crs=CRS_WGS84).to_crs(
            CRS_CA_ALBERS_FT
        )
        bounds = tuple(region_poly.total_bounds)
        minx, miny, maxx, maxy = bounds
        region_tracts = tracts.cx[minx:maxx, miny:maxy]
        region_chargers = chargers.cx[minx:maxx, miny:maxy]
        _, _, zz = _kde_grid(region_chargers, bounds, nx=300, ny=300)

        if zz.size:
            threshold = np.nanpercentile(zz, 62)
            zz_masked = np.where(zz >= threshold, zz, np.nan)
            vmax = np.nanpercentile(zz_masked, 99.5)
            ax.imshow(
                zz_masked,
                extent=[minx, maxx, miny, maxy],
                origin="lower",
                cmap="magma",
                alpha=0.88,
                vmax=vmax,
            )
        region_tracts.boundary.plot(ax=ax, linewidth=0.12, color="#bdbdbd", alpha=0.6)
        region_chargers.plot(ax=ax, markersize=1.0, color="#1f2933", alpha=0.28)
        ax.set_title(title, fontsize=13, pad=8)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_axis_off()

    fig.suptitle(
        "EV Charging Infrastructure Benchmark Regions Identified by KDE",
        fontsize=17,
        y=0.98,
    )
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "ca_ev_charger_regional_kde_benchmark_regions.png", dpi=240)
    plt.close(fig)


def write_summary(chargers: gpd.GeoDataFrame, tract_chargers: gpd.GeoDataFrame) -> None:
    rows = [
        {"metric": "charger_stations", "value": int(len(chargers))},
        {"metric": "l1_evse", "value": float(chargers["L1_evse"].sum())},
        {"metric": "l2_evse", "value": float(chargers["L2_evse"].sum())},
        {"metric": "dcfc", "value": float(chargers["DCFC"].sum())},
        {"metric": "total_evse", "value": float(chargers["total_evse"].sum())},
        {"metric": "california_tracts", "value": int(len(tract_chargers))},
        {
            "metric": "tracts_with_at_least_one_station",
            "value": int((tract_chargers["station_count"] > 0).sum()),
        },
        {
            "metric": "tracts_with_zero_station",
            "value": int((tract_chargers["station_count"] == 0).sum()),
        },
    ]
    pd.DataFrame(rows).to_csv(TABLE_DIR / "stage1_charger_join_summary.csv", index=False)


def main() -> None:
    ensure_dirs()
    chargers_raw = download_cec_chargers()
    tracts_raw = download_census_tracts()
    chargers = clean_chargers(chargers_raw)
    tracts = clean_tracts(tracts_raw)

    chargers.to_file(PROCESSED_DIR / "cec_existing_public_chargers_clean.geojson")
    chargers.to_file(
        PROCESSED_DIR / "cec_existing_public_chargers_clean.gpkg",
        layer="cec_existing_public_chargers_clean",
        driver="GPKG",
    )
    tracts.to_file(PROCESSED_DIR / "ca_census_tracts_2024_clean.geojson")
    tracts.to_file(
        PROCESSED_DIR / "ca_census_tracts_2024_clean.gpkg",
        layer="ca_census_tracts_2024_clean",
        driver="GPKG",
    )

    _, tract_chargers = spatial_join_chargers_to_tracts(chargers, tracts)
    tract_chargers = add_multiscale_kde_to_tracts(chargers, tract_chargers)
    write_summary(chargers, tract_chargers)
    plot_tract_join_map(tract_chargers)
    plot_kde_map(chargers, tracts)
    plot_clean_kde_map(chargers, tracts)
    plot_regional_kde_maps(chargers, tracts)
    plot_multiscale_tract_kde_maps(tract_chargers)
    plot_benchmark_region_kde_quartile_maps(tract_chargers)


if __name__ == "__main__":
    main()
