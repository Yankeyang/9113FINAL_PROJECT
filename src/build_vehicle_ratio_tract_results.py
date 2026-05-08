"""Build statewide tract EVSE-to-vehicle ratio results.

This script prepares census-tract results for choosing a future charger
planning benchmark based on:

    current EVSE / light-duty vehicles * 1000

It does not choose the final benchmark threshold. Instead it outputs:

1. ZIP-level DMV vehicle counts.
2. R-squared comparison of ZIP light-duty vehicles vs ZCTA area and population.
3. Tract-level vehicle allocations using both area weighting and population
   weighting.
4. Statewide tract ranking and percentile tables for EVSE per 1,000 vehicles.
"""

from __future__ import annotations

import argparse
import json
import ssl
import time
import zipfile
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import urlopen

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"

DMV_RESOURCE_ID = "66b0121e-5eab-4fcf-aa0d-2b1dfb5510ab"
DMV_SQL_URL = "https://data.ca.gov/api/3/action/datastore_search_sql"
ZCTA_ZIP_URL = "https://www2.census.gov/geo/tiger/TIGER2024/ZCTA520/tl_2024_us_zcta520.zip"
ACS_TRACT_URL = "https://api.census.gov/data/2024/acs/acs5"
ACS_ZCTA_URL = "https://api.census.gov/data/2024/acs/acs5"

TRACT_CHARGERS_INPUT = PROCESSED_DIR / "ca_tract_charger_join_with_kde.gpkg"
ZCTA_ZIP_PATH = RAW_DIR / "tl_2024_us_zcta520.zip"
ZCTA_EXTRACT_DIR = RAW_DIR / "zcta_boundaries" / "tl_2024_us_zcta520"

RAW_DMV_ZIP_OUTPUT = RAW_DIR / "dmv_vehicle_counts_by_zip_2024.csv"
ACS_TRACT_POP_OUTPUT = PROCESSED_DIR / "acs_tract_population_ca_2024.csv"
ACS_ZCTA_POP_OUTPUT = PROCESSED_DIR / "acs_zcta_population_us_2024.csv"
ZIP_DIAGNOSTIC_OUTPUT = PROCESSED_DIR / "zip_vehicle_area_population_diagnostics.csv"
TRACT_RESULTS_OUTPUT = PROCESSED_DIR / "ca_tract_evse_vehicle_ratio_results.csv"
TRACT_RANKING_OUTPUT = TABLE_DIR / "ca_tract_evse_per_1000_vehicle_ranking.csv"
R2_OUTPUT = TABLE_DIR / "vehicle_allocation_weight_r2_comparison.csv"
PERCENTILE_OUTPUT = TABLE_DIR / "evse_per_1000_vehicle_percentiles.csv"
SCATTER_OUTPUT = FIGURE_DIR / "zip_light_duty_vehicle_r2_area_vs_population.png"

CRS_CA_ALBERS_FT = (
    "+proj=aea +lat_0=0 +lon_0=-120 +lat_1=34 +lat_2=40.5 "
    "+x_0=0 +y_0=-4000000 +datum=NAD83 +units=us-ft +no_defs"
)
SQFT_PER_SQMI = 27_878_400
SSL_CONTEXT = ssl._create_unverified_context()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate tract EVSE-to-light-duty-vehicle ratios."
    )
    parser.add_argument("--min-light-duty-for-ranking", type=float, default=500.0)
    return parser.parse_args()


def fetch_json(url: str, params: dict[str, str] | None = None) -> object:
    request_url = url if params is None else f"{url}?{urlencode(params)}"
    with urlopen(request_url, timeout=240, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_dmv_zip_counts() -> pd.DataFrame:
    sql = f"""
    SELECT
      "ZIP Code" AS zip_code,
      SUM(CASE WHEN "Fuel" IN ('Battery Electric', 'Plug-in Hybrid')
               AND "Duty" = 'Light' THEN "Vehicles" ELSE 0 END) AS ev_vehicles,
      SUM(CASE WHEN "Fuel" IN ('Battery Electric', 'Plug-in Hybrid', 'Hydrogen Fuel Cell')
               AND "Duty" = 'Light' THEN "Vehicles" ELSE 0 END) AS zev_vehicles,
      SUM(CASE WHEN "Duty" = 'Light' THEN "Vehicles" ELSE 0 END) AS light_duty_vehicles
    FROM "{DMV_RESOURCE_ID}"
    GROUP BY "ZIP Code"
    """
    payload = fetch_json(f"{DMV_SQL_URL}?sql={quote(sql)}")
    if not payload.get("success"):
        raise RuntimeError(payload)

    df = pd.DataFrame(payload["result"]["records"])
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)
    for col in ["ev_vehicles", "zev_vehicles", "light_duty_vehicles"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["ev_share_light_duty"] = df["ev_vehicles"] / df[
        "light_duty_vehicles"
    ].replace({0: pd.NA})
    df.to_csv(RAW_DMV_ZIP_OUTPUT, index=False)
    return df


def download_zctas() -> gpd.GeoDataFrame:
    if not ZCTA_ZIP_PATH.exists():
        with urlopen(ZCTA_ZIP_URL, timeout=300, context=SSL_CONTEXT) as response:
            ZCTA_ZIP_PATH.write_bytes(response.read())

    ZCTA_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    if not list(ZCTA_EXTRACT_DIR.glob("*.shp")):
        with zipfile.ZipFile(ZCTA_ZIP_PATH, "r") as archive:
            archive.extractall(ZCTA_EXTRACT_DIR)

    shp = next(ZCTA_EXTRACT_DIR.glob("*.shp"))
    zctas = gpd.read_file(shp)
    zcta_col = "ZCTA5CE20" if "ZCTA5CE20" in zctas.columns else "ZCTA5CE"
    zctas = zctas[[zcta_col, "geometry"]].rename(columns={zcta_col: "zip_code"})
    zctas["zip_code"] = zctas["zip_code"].astype(str).str.zfill(5)
    return zctas


def download_acs_tract_population() -> pd.DataFrame:
    params = {
        "get": "NAME,B01003_001E",
        "for": "tract:*",
        "in": "state:06",
    }
    rows = fetch_json(ACS_TRACT_URL, params)
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    df = df.rename(columns={"B01003_001E": "population"})
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df[["GEOID", "NAME", "population", "state", "county", "tract"]].to_csv(
        ACS_TRACT_POP_OUTPUT, index=False
    )
    return df[["GEOID", "population"]]


def download_acs_zcta_population() -> pd.DataFrame:
    params = {
        "get": "NAME,B01003_001E",
        "for": "zip code tabulation area:*",
    }
    rows = fetch_json(ACS_ZCTA_URL, params)
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df.rename(
        columns={
            "zip code tabulation area": "zip_code",
            "B01003_001E": "zcta_population",
        }
    )
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)
    df["zcta_population"] = pd.to_numeric(df["zcta_population"], errors="coerce")
    df[["zip_code", "NAME", "zcta_population"]].to_csv(ACS_ZCTA_POP_OUTPUT, index=False)
    return df[["zip_code", "zcta_population"]]


def r2_simple(x: pd.Series, y: pd.Series) -> float:
    valid = pd.concat([x, y], axis=1).dropna()
    valid = valid[(valid.iloc[:, 0] > 0) & (valid.iloc[:, 1] > 0)]
    model = LinearRegression()
    model.fit(valid.iloc[:, [0]], valid.iloc[:, 1])
    return float(model.score(valid.iloc[:, [0]], valid.iloc[:, 1]))


def build_zip_diagnostics(
    zip_counts: pd.DataFrame, zctas: gpd.GeoDataFrame, zcta_pop: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    zcta_area = zctas.to_crs(CRS_CA_ALBERS_FT).copy()
    zcta_area["zcta_area_sq_mi"] = zcta_area.geometry.area / SQFT_PER_SQMI
    diagnostic = (
        zip_counts.merge(
            zcta_area[["zip_code", "zcta_area_sq_mi"]], on="zip_code", how="left"
        )
        .merge(zcta_pop, on="zip_code", how="left")
        .copy()
    )
    diagnostic.to_csv(ZIP_DIAGNOSTIC_OUTPUT, index=False)

    r2_rows = [
        {
            "candidate_weight_basis": "zcta_area_sq_mi",
            "r_squared_explaining_zip_light_duty_vehicles": r2_simple(
                diagnostic["zcta_area_sq_mi"], diagnostic["light_duty_vehicles"]
            ),
        },
        {
            "candidate_weight_basis": "zcta_population",
            "r_squared_explaining_zip_light_duty_vehicles": r2_simple(
                diagnostic["zcta_population"], diagnostic["light_duty_vehicles"]
            ),
        },
    ]
    r2_table = pd.DataFrame(r2_rows)
    r2_table.to_csv(R2_OUTPUT, index=False)
    plot_r2_scatter(diagnostic, r2_table)
    return diagnostic, r2_table


def plot_r2_scatter(diagnostic: pd.DataFrame, r2_table: pd.DataFrame) -> None:
    plot_df = diagnostic.dropna(
        subset=["light_duty_vehicles", "zcta_area_sq_mi", "zcta_population"]
    )
    plot_df = plot_df[plot_df["light_duty_vehicles"] > 0]
    area_r2 = r2_table.loc[
        r2_table["candidate_weight_basis"] == "zcta_area_sq_mi",
        "r_squared_explaining_zip_light_duty_vehicles",
    ].iloc[0]
    pop_r2 = r2_table.loc[
        r2_table["candidate_weight_basis"] == "zcta_population",
        "r_squared_explaining_zip_light_duty_vehicles",
    ].iloc[0]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor="white")
    axes[0].scatter(
        plot_df["zcta_area_sq_mi"],
        plot_df["light_duty_vehicles"],
        s=8,
        alpha=0.35,
        linewidths=0,
        color="#4C78A8",
    )
    axes[0].set_title(f"Light-duty vehicles vs ZCTA area\nR² = {area_r2:.3f}")
    axes[0].set_xlabel("ZCTA area, sq mi")
    axes[0].set_ylabel("ZIP light-duty vehicles")
    axes[0].grid(alpha=0.25)

    axes[1].scatter(
        plot_df["zcta_population"],
        plot_df["light_duty_vehicles"],
        s=8,
        alpha=0.35,
        linewidths=0,
        color="#54A24B",
    )
    axes[1].set_title(f"Light-duty vehicles vs ZCTA population\nR² = {pop_r2:.3f}")
    axes[1].set_xlabel("ZCTA population")
    axes[1].set_ylabel("ZIP light-duty vehicles")
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(SCATTER_OUTPUT, dpi=220)
    plt.close(fig)


def allocate_zip_counts_to_tracts(
    zip_counts: pd.DataFrame, zctas: gpd.GeoDataFrame, tract_pop: pd.DataFrame
) -> pd.DataFrame:
    tracts = gpd.read_file(TRACT_CHARGERS_INPUT).to_crs(CRS_CA_ALBERS_FT)
    tracts["GEOID"] = tracts["GEOID"].astype(str)
    tracts = tracts.merge(tract_pop, on="GEOID", how="left")
    tracts["tract_area_sq_ft"] = tracts.geometry.area

    zctas = zctas.to_crs(CRS_CA_ALBERS_FT).merge(zip_counts, on="zip_code", how="inner")
    minx, miny, maxx, maxy = tracts.total_bounds
    zctas = zctas.cx[minx:maxx, miny:maxy].copy()
    zctas["zcta_area_sq_ft"] = zctas.geometry.area

    intersections = gpd.overlay(
        tracts[["GEOID", "population", "tract_area_sq_ft", "geometry"]],
        zctas[
            [
                "zip_code",
                "ev_vehicles",
                "zev_vehicles",
                "light_duty_vehicles",
                "zcta_area_sq_ft",
                "geometry",
            ]
        ],
        how="intersection",
        keep_geom_type=True,
    )
    intersections["intersection_area_sq_ft"] = intersections.geometry.area
    intersections["area_share_of_zcta"] = (
        intersections["intersection_area_sq_ft"] / intersections["zcta_area_sq_ft"]
    )
    intersections["area_share_of_tract"] = (
        intersections["intersection_area_sq_ft"] / intersections["tract_area_sq_ft"]
    )
    intersections["overlap_population_proxy"] = (
        intersections["population"] * intersections["area_share_of_tract"]
    )
    zip_overlap_pop = intersections.groupby("zip_code")[
        "overlap_population_proxy"
    ].transform("sum")
    intersections["population_weight_within_zcta"] = (
        intersections["overlap_population_proxy"] / zip_overlap_pop.replace({0: pd.NA})
    )
    intersections["population_weight_within_zcta"] = intersections[
        "population_weight_within_zcta"
    ].fillna(intersections["area_share_of_zcta"])

    for col in ["ev_vehicles", "zev_vehicles", "light_duty_vehicles"]:
        intersections[f"{col}_area_weighted"] = (
            intersections[col] * intersections["area_share_of_zcta"]
        )
        intersections[f"{col}_population_weighted"] = (
            intersections[col] * intersections["population_weight_within_zcta"]
        )

    allocated = (
        intersections.groupby("GEOID", as_index=False)
        .agg(
            ev_vehicles_area_weighted=("ev_vehicles_area_weighted", "sum"),
            zev_vehicles_area_weighted=("zev_vehicles_area_weighted", "sum"),
            light_duty_vehicles_area_weighted=(
                "light_duty_vehicles_area_weighted",
                "sum",
            ),
            ev_vehicles_population_weighted=("ev_vehicles_population_weighted", "sum"),
            zev_vehicles_population_weighted=("zev_vehicles_population_weighted", "sum"),
            light_duty_vehicles_population_weighted=(
                "light_duty_vehicles_population_weighted",
                "sum",
            ),
        )
    )

    base_cols = [
        "GEOID",
        "NAMELSAD",
        "COUNTYFP",
        "TRACTCE",
        "tract_area_sq_mi",
        "station_count",
        "total_evse",
        "stations_per_sq_mi",
        "evse_per_sq_mi",
        "population",
    ]
    result = tracts[[col for col in base_cols if col in tracts.columns]].merge(
        allocated, on="GEOID", how="left"
    )
    vehicle_cols = [col for col in result.columns if "vehicles_" in col]
    result[vehicle_cols] = result[vehicle_cols].fillna(0)

    for method in ["area_weighted", "population_weighted"]:
        result[f"evse_per_1000_light_duty_vehicles_{method}"] = (
            result["total_evse"]
            / result[f"light_duty_vehicles_{method}"].replace({0: pd.NA})
            * 1000
        )
        result[f"ev_share_light_duty_{method}"] = (
            result[f"ev_vehicles_{method}"]
            / result[f"light_duty_vehicles_{method}"].replace({0: pd.NA})
        )
    return result


def write_rankings_and_percentiles(result: pd.DataFrame, min_light_duty: float) -> None:
    result.to_csv(TRACT_RESULTS_OUTPUT, index=False)

    ranking = result[
        result["light_duty_vehicles_population_weighted"] >= min_light_duty
    ].copy()
    ranking = ranking.sort_values(
        "evse_per_1000_light_duty_vehicles_population_weighted", ascending=False
    )
    ranking["rank_population_weighted_ratio"] = range(1, len(ranking) + 1)
    ranking.to_csv(TRACT_RANKING_OUTPUT, index=False)

    rows = []
    for method in ["area_weighted", "population_weighted"]:
        col = f"evse_per_1000_light_duty_vehicles_{method}"
        valid = result[result[f"light_duty_vehicles_{method}"] >= min_light_duty][col].dropna()
        for p in [50, 60, 70, 75, 80, 85, 90, 95, 97.5, 99]:
            rows.append(
                {
                    "method": method,
                    "min_light_duty_vehicles": min_light_duty,
                    "percentile": p,
                    "evse_per_1000_light_duty_vehicles": valid.quantile(p / 100),
                    "n_tracts": len(valid),
                }
            )
    pd.DataFrame(rows).to_csv(PERCENTILE_OUTPUT, index=False)


def main() -> None:
    args = parse_args()
    for directory in [RAW_DIR, PROCESSED_DIR, TABLE_DIR, FIGURE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    zip_counts = fetch_dmv_zip_counts()
    zctas = download_zctas()
    tract_pop = download_acs_tract_population()
    zcta_pop = download_acs_zcta_population()
    _, r2_table = build_zip_diagnostics(zip_counts, zctas, zcta_pop)
    result = allocate_zip_counts_to_tracts(zip_counts, zctas, tract_pop)
    write_rankings_and_percentiles(result, args.min_light_duty_for_ranking)

    recommended = r2_table.sort_values(
        "r_squared_explaining_zip_light_duty_vehicles", ascending=False
    ).iloc[0]
    print(f"Wrote {TRACT_RESULTS_OUTPUT}")
    print(f"Wrote {TRACT_RANKING_OUTPUT}")
    print(f"Wrote {PERCENTILE_OUTPUT}")
    print(f"Wrote {R2_OUTPUT}")
    print(
        "Higher R² basis: "
        f"{recommended['candidate_weight_basis']} "
        f"({recommended['r_squared_explaining_zip_light_duty_vehicles']:.3f})"
    )


if __name__ == "__main__":
    main()
