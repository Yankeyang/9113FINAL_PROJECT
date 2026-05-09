from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from gis_map_utils import add_map_credits, add_north_arrow, add_scale_bar


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"

FEATURES = [
    "population",
    "tract_area_sq_mi",
    "light_duty_vehicles_population_weighted",
    "ev_vehicles_population_weighted",
]
TARGET = "total_evse"
BENCHMARK_COL = "evse_per_1000_light_duty_vehicles_population_weighted"
BENCHMARK_LOWER = 20
BENCHMARK_UPPER = 100
CRS_CA_ALBERS = "EPSG:3310"
GAP_BINS = [-0.1, 0, 10, 25, 50, 100, 250, 500, 1000, np.inf]
GAP_LABELS = [
    "0",
    "1-10",
    "11-25",
    "26-50",
    "51-100",
    "101-250",
    "251-500",
    "501-1000",
    ">1000",
]
GAP_COLORS = [
    "#fff5f0",
    "#fee0d2",
    "#fcbba1",
    "#fc9272",
    "#fb6a4a",
    "#ef3b2c",
    "#cb181d",
    "#a50f15",
    "#67000d",
]
BENCHMARK_BINS = [-0.1, 0, 1, 5, 10, 20, 50, 100, np.inf]
BENCHMARK_LABELS = ["0", "0-1", "1-5", "5-10", "10-20", "20-50", "50-100", ">100"]
BENCHMARK_COLORS = [
    "#ffffcc",
    "#c7e9b4",
    "#7fcdbb",
    "#41b6c4",
    "#1d91c0",
    "#225ea8",
    "#253494",
    "#081d58",
]


def build_model() -> Pipeline:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocess = ColumnTransformer([("num", numeric, FEATURES)])
    regressor = TransformedTargetRegressor(
        regressor=Ridge(alpha=10.0),
        func=np.log1p,
        inverse_func=np.expm1,
    )
    return Pipeline([("preprocess", preprocess), ("model", regressor)])


def plot_benchmark_value_map(geo: gpd.GeoDataFrame, statewide: pd.DataFrame) -> None:
    map_df = geo.merge(
        statewide[["GEOID", BENCHMARK_COL, "is_benchmark_20to100"]],
        on="GEOID",
        how="left",
    ).to_crs(CRS_CA_ALBERS)
    map_df["benchmark_value_bin"] = pd.cut(
        map_df[BENCHMARK_COL],
        bins=BENCHMARK_BINS,
        labels=BENCHMARK_LABELS,
        include_lowest=True,
    )

    fig, ax = plt.subplots(figsize=(8.5, 10.5), facecolor="white")
    map_df.plot(ax=ax, color="#eeeeee", linewidth=0)
    for label, color in zip(BENCHMARK_LABELS, BENCHMARK_COLORS):
        map_df[map_df["benchmark_value_bin"] == label].plot(
            ax=ax,
            color=color,
            linewidth=0,
        )
    map_df.boundary.plot(ax=ax, linewidth=0.025, color="#ffffff", alpha=0.42)
    map_df.dissolve().boundary.plot(ax=ax, linewidth=0.9, color="#27313d")

    handles = [
        Patch(facecolor=color, edgecolor="#4b5563", linewidth=0.25, label=f"{label} EVSE / 1,000 vehicles")
        for label, color in zip(BENCHMARK_LABELS, BENCHMARK_COLORS)
    ]
    ax.legend(
        handles=handles,
        title="EV charger benchmark value",
        loc="lower right",
        bbox_to_anchor=(0.98, 0.065),
        fontsize=7,
        title_fontsize=8,
        frameon=True,
        framealpha=0.94,
        borderpad=0.7,
    )
    add_scale_bar(ax, 200_000, "200 km", location=(0.50, 0.055), anchor="center")
    add_north_arrow(ax, x=0.075, y=0.86)
    add_map_credits(ax, "Projection: California Albers (EPSG:3310)")
    ax.set_title(
        "EV Charger Benchmark Value by California Census Tract\nEVSE per 1,000 population-weighted light-duty vehicles",
        fontsize=13,
        pad=12,
    )
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(FIGURES / "ca_ev_charger_benchmark_value_by_tract.png", dpi=240)
    plt.close()


def plot_final_gap_map(geo: gpd.GeoDataFrame, statewide: pd.DataFrame) -> None:
    map_df = geo.merge(
        statewide[
            [
                "GEOID",
                "planning_gap_evse_non_benchmark_only",
                "planning_gap_bin",
                "is_benchmark_20to100",
                "is_above_standard_gt100",
                "application_group",
            ]
        ],
        on="GEOID",
        how="left",
    ).to_crs(CRS_CA_ALBERS)

    fig, ax = plt.subplots(figsize=(8.5, 10.5), facecolor="white")
    map_df.plot(ax=ax, color="#f3f4f6", linewidth=0)
    map_df[map_df["is_benchmark_20to100"]].plot(
        ax=ax,
        color="#9ecae1",
        linewidth=0,
    )
    map_df[map_df["is_above_standard_gt100"]].plot(
        ax=ax,
        color="#006d77",
        linewidth=0,
    )
    for label, color in zip(GAP_LABELS, GAP_COLORS):
        map_df[map_df["planning_gap_bin"] == label].plot(
            ax=ax,
            color=color,
            linewidth=0,
        )
    map_df.boundary.plot(ax=ax, linewidth=0.025, color="#ffffff", alpha=0.40)
    map_df.dissolve().boundary.plot(ax=ax, linewidth=0.9, color="#27313d")

    legend_handles = [
        Patch(
            facecolor="#9ecae1",
            edgecolor="#2166ac",
            linewidth=0.25,
            label="Benchmark standard 20-100",
        ),
        Patch(
            facecolor="#f3f4f6",
            edgecolor="#9ca3af",
            linewidth=0.25,
            label="No vehicle-ratio data, excluded",
        ),
        Patch(
            facecolor="#006d77",
            edgecolor="#003c43",
            linewidth=0.25,
            label="Above standard >100, excluded",
        ),
    ]
    legend_handles += [
        Patch(facecolor=color, edgecolor="#4b5563", linewidth=0.25, label=f"Gap {label} EVSE")
        for label, color in zip(GAP_LABELS, GAP_COLORS)
    ]
    ax.legend(
        handles=legend_handles,
        title="Planning gap bins",
        loc="lower right",
        bbox_to_anchor=(0.98, 0.065),
        fontsize=7,
        title_fontsize=8,
        frameon=True,
        framealpha=0.94,
        borderpad=0.7,
    )
    add_scale_bar(ax, 200_000, "200 km", location=(0.50, 0.055), anchor="center")
    add_north_arrow(ax, x=0.075, y=0.86)
    add_map_credits(ax, "Projection: California Albers (EPSG:3310)")
    ax.set_title(
        "Final Model EVSE Planning Gap for Below-Standard Census Tracts\nGap = predicted target EVSE - current EVSE",
        fontsize=13,
        pad=12,
    )
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(FIGURES / "final_scale_model_nonbenchmark_gap_map.png", dpi=240)
    plt.close()


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    ratio_path = DATA / "processed" / "ca_tract_evse_vehicle_ratio_results.csv"
    ratio = pd.read_csv(ratio_path, dtype={"GEOID": str})
    ratio["is_benchmark_20to100"] = ratio[BENCHMARK_COL].between(
        BENCHMARK_LOWER,
        BENCHMARK_UPPER,
        inclusive="both",
    )
    ratio["is_above_standard_gt100"] = ratio[BENCHMARK_COL] > BENCHMARK_UPPER
    ratio["is_below_standard_lt20"] = ratio[BENCHMARK_COL] < BENCHMARK_LOWER

    benchmark = ratio[ratio["is_benchmark_20to100"]].copy()
    train, test = train_test_split(benchmark, test_size=0.25, random_state=2)

    model = build_model()
    model.fit(train[FEATURES], train[TARGET])

    test_pred = np.clip(model.predict(test[FEATURES]), 0, None)
    test_pred_round = np.rint(test_pred)
    performance = pd.DataFrame(
        [
            {
                "benchmark_definition": "20 <= ev_charger_benchmark_value <= 100",
                "target": TARGET,
                "features": ", ".join(FEATURES),
                "benchmark_tracts": len(benchmark),
                "train_tracts": len(train),
                "test_tracts": len(test),
                "mae": mean_absolute_error(test[TARGET], test_pred),
                "rmse": mean_squared_error(test[TARGET], test_pred) ** 0.5,
                "r2": r2_score(test[TARGET], test_pred),
            }
        ]
    )
    performance.to_csv(TABLES / "final_scale_model_performance.csv", index=False)

    test_out = test[
        ["GEOID", "NAMELSAD", TARGET, BENCHMARK_COL, *FEATURES]
    ].copy()
    test_out["predicted_target_evse_count"] = test_pred_round
    test_out["prediction_error"] = test_out["predicted_target_evse_count"] - test_out[TARGET]
    test_out.to_csv(TABLES / "final_scale_model_test_set_predictions.csv", index=False)

    order = np.arange(len(test_out))
    plt.figure(figsize=(15, 6))
    plt.scatter(order, test_out[TARGET], s=28, label="Actual EVSE count", alpha=0.85)
    plt.scatter(order, test_out["predicted_target_evse_count"], s=28, label="Predicted EVSE count", alpha=0.85)
    plt.xticks(order, test_out["GEOID"], rotation=90, fontsize=6)
    plt.ylabel("EV charger / EVSE count")
    plt.xlabel("Census tract in test set")
    plt.title("Final Benchmark Model: Test Set Actual vs Predicted EVSE Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "final_scale_model_test_set_predicted_vs_actual.png", dpi=220)
    plt.close()

    statewide = ratio.copy()
    statewide["predicted_target_evse_count"] = np.rint(
        np.clip(model.predict(statewide[FEATURES]), 0, None)
    )
    statewide["current_total_evse"] = statewide[TARGET]
    statewide["model_gap_evse_all_tracts"] = (
        statewide["predicted_target_evse_count"] - statewide["current_total_evse"]
    ).clip(lower=0)
    statewide["application_group"] = np.select(
        [
            statewide["is_benchmark_20to100"],
            statewide["is_above_standard_gt100"],
            statewide["is_below_standard_lt20"],
        ],
        [
            "benchmark_training_standard",
            "above_standard_excluded",
            "below_standard_gap_application",
        ],
        default="excluded_no_vehicle_ratio",
    )
    statewide["planning_gap_evse_non_benchmark_only"] = np.where(
        statewide["is_below_standard_lt20"],
        statewide["model_gap_evse_all_tracts"],
        np.nan,
    )
    statewide["planning_gap_bin"] = pd.cut(
        statewide["planning_gap_evse_non_benchmark_only"],
        bins=GAP_BINS,
        labels=GAP_LABELS,
        include_lowest=True,
    )
    statewide.to_csv(
        DATA / "processed" / "final_scale_model_statewide_gap_results_nonbenchmark_flagged.csv",
        index=False,
    )

    nonbenchmark = statewide[statewide["is_below_standard_lt20"]].copy()
    gap_bin_counts = (
        nonbenchmark["planning_gap_bin"]
        .value_counts(sort=False)
        .rename_axis("planning_gap_evse_bin")
        .reset_index(name="tract_count")
    )
    gap_bin_counts.to_csv(TABLES / "final_scale_model_gap_bin_counts.csv", index=False)
    nonbenchmark.sort_values("planning_gap_evse_non_benchmark_only", ascending=False).head(100).to_csv(
        TABLES / "top_100_nonbenchmark_gap_tracts.csv",
        index=False,
    )
    nonbenchmark[nonbenchmark["current_total_evse"] == 0].sort_values(
        "planning_gap_evse_non_benchmark_only", ascending=False
    ).head(100).to_csv(TABLES / "top_100_zero_current_nonbenchmark_gap_tracts.csv", index=False)

    gpkg = DATA / "processed" / "ca_tract_charger_join_with_kde.gpkg"
    geo = gpd.read_file(gpkg)
    geo["GEOID"] = geo["GEOID"].astype(str)
    plot_benchmark_value_map(geo, statewide)
    plot_final_gap_map(geo, statewide)

    zero_current = nonbenchmark[nonbenchmark["current_total_evse"] == 0].nlargest(
        25, "planning_gap_evse_non_benchmark_only"
    )
    plt.figure(figsize=(10, 7))
    plt.barh(
        zero_current["GEOID"].astype(str),
        zero_current["planning_gap_evse_non_benchmark_only"],
        color="#c33a1a",
    )
    plt.gca().invert_yaxis()
    plt.xlabel("Planning gap EVSE count")
    plt.ylabel("Census tract")
    plt.title("Largest Planning Gaps Among Non-Benchmark Tracts With Current EVSE = 0")
    plt.tight_layout()
    plt.savefig(FIGURES / "top_zero_current_nonbenchmark_gap_tracts.png", dpi=220)
    plt.close()


if __name__ == "__main__":
    main()
