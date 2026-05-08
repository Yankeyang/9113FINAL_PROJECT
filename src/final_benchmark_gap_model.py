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
    "#f7f7f7",
    "#fff2b2",
    "#fed976",
    "#feb24c",
    "#fd8d3c",
    "#fc4e2a",
    "#e31a1c",
    "#bd0026",
    "#800026",
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


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    ratio_path = DATA / "processed" / "ca_tract_evse_vehicle_ratio_results.csv"
    ratio = pd.read_csv(ratio_path, dtype={"GEOID": str})
    ratio["is_benchmark_20to100"] = ratio[BENCHMARK_COL].between(20, 100, inclusive="both")

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
    statewide["application_group"] = np.where(
        statewide["is_benchmark_20to100"],
        "benchmark_training_standard",
        "non_benchmark_application",
    )
    statewide["planning_gap_evse_non_benchmark_only"] = np.where(
        statewide["is_benchmark_20to100"],
        np.nan,
        statewide["model_gap_evse_all_tracts"],
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

    nonbenchmark = statewide[~statewide["is_benchmark_20to100"]].copy()
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
    geo = geo.merge(
        statewide[
            [
                "GEOID",
                "planning_gap_evse_non_benchmark_only",
                "planning_gap_bin",
                "is_benchmark_20to100",
            ]
        ],
        on="GEOID",
        how="left",
    )
    geo_3857 = geo.to_crs(3857)
    fig, ax = plt.subplots(figsize=(8, 10))
    geo_3857.plot(ax=ax, color="#e6e6e6", linewidth=0)
    for label, color in zip(GAP_LABELS, GAP_COLORS):
        geo_3857[geo_3857["planning_gap_bin"] == label].plot(
            ax=ax,
            color=color,
            linewidth=0,
        )
    geo_3857.boundary.plot(ax=ax, linewidth=0.03, color="#b8b8b8")
    legend_handles = [Patch(facecolor="#e6e6e6", label="Benchmark tracts")]
    legend_handles += [
        Patch(facecolor=color, label=f"Gap {label} EVSE")
        for label, color in zip(GAP_LABELS, GAP_COLORS)
    ]
    ax.legend(
        handles=legend_handles,
        title="Planning gap bins",
        loc="lower left",
        fontsize=7,
        title_fontsize=8,
        frameon=True,
    )
    ax.set_axis_off()
    ax.set_title("Final Model Planning Gap for Non-Benchmark California Census Tracts")
    plt.tight_layout()
    plt.savefig(FIGURES / "final_scale_model_nonbenchmark_gap_map.png", dpi=220)
    plt.close()

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
