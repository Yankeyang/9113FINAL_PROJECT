from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"

COUNTY_DATA = {
    "001": ("Alameda", 1800),
    "003": ("Alpine", 10),
    "005": ("Amador", 100),
    "007": ("Butte", 500),
    "009": ("Calaveras", 120),
    "011": ("Colusa", 60),
    "013": ("Contra Costa", 1300),
    "015": ("Del Norte", 60),
    "017": ("El Dorado", 350),
    "019": ("Fresno", 1800),
    "021": ("Glenn", 70),
    "023": ("Humboldt", 300),
    "025": ("Imperial", 350),
    "027": ("Inyo", 50),
    "029": ("Kern", 1600),
    "031": ("Kings", 250),
    "033": ("Lake", 130),
    "035": ("Lassen", 70),
    "037": ("Los Angeles", 14000),
    "039": ("Madera", 300),
    "041": ("Marin", 300),
    "043": ("Mariposa", 50),
    "045": ("Mendocino", 180),
    "047": ("Merced", 450),
    "049": ("Modoc", 25),
    "051": ("Mono", 35),
    "053": ("Monterey", 750),
    "055": ("Napa", 180),
    "057": ("Nevada", 160),
    "059": ("Orange", 4500),
    "061": ("Placer", 550),
    "063": ("Plumas", 55),
    "065": ("Riverside", 3800),
    "067": ("Sacramento", 2800),
    "069": ("San Benito", 100),
    "071": ("San Bernardino", 3500),
    "073": ("San Diego", 4800),
    "075": ("San Francisco", 600),
    "077": ("San Joaquin", 1200),
    "079": ("San Luis Obispo", 500),
    "081": ("San Mateo", 800),
    "083": ("Santa Barbara", 650),
    "085": ("Santa Clara", 2200),
    "087": ("Santa Cruz", 400),
    "089": ("Shasta", 400),
    "091": ("Sierra", 12),
    "093": ("Siskiyou", 120),
    "095": ("Solano", 600),
    "097": ("Sonoma", 650),
    "099": ("Stanislaus", 950),
    "101": ("Sutter", 180),
    "103": ("Tehama", 130),
    "105": ("Trinity", 35),
    "107": ("Tulare", 750),
    "109": ("Tuolumne", 130),
    "111": ("Ventura", 1300),
    "113": ("Yolo", 300),
    "115": ("Yuba", 130),
}


def build_comparison() -> pd.DataFrame:
    final_df = pd.read_csv(
        DATA / "processed" / "final_scale_model_statewide_gap_results_nonbenchmark_flagged.csv",
        dtype={"GEOID": str},
    )
    final_df = final_df[final_df["application_group"] == "below_standard_gap_application"].copy()

    county_df = pd.DataFrame(
        [
            {"COUNTYFP": int(county), "county_name": name, "gas_nozzles": nozzles}
            for county, (name, nozzles) in COUNTY_DATA.items()
        ]
    )

    gas_pump_cars_per_hr = 12
    dcfc_cars_per_hr = 2.5
    l2_cars_per_hr = 0.33
    dcfc_share = 0.30
    l2_share = 0.70
    public_charge_pct = 0.20
    blended_ev_cars_per_hr = dcfc_share * dcfc_cars_per_hr + l2_share * l2_cars_per_hr
    throughput_ratio = gas_pump_cars_per_hr / blended_ev_cars_per_hr
    county_df["baseline_county_target_evse"] = (
        county_df["gas_nozzles"] * throughput_ratio * public_charge_pct
    )

    out = final_df.merge(county_df, on="COUNTYFP", how="left")
    out["baseline_weight"] = 1 / np.sqrt(out["tract_area_sq_mi"].clip(lower=0.001))
    out["baseline_weight_share"] = out["baseline_weight"] / out.groupby("COUNTYFP")[
        "baseline_weight"
    ].transform("sum")
    out["baseline_target_evse_count"] = np.rint(
        out["baseline_weight_share"] * out["baseline_county_target_evse"]
    )
    out["baseline_gap_evse"] = (
        out["baseline_target_evse_count"] - out["current_total_evse"]
    ).clip(lower=0)
    out["target_difference_final_minus_baseline"] = (
        out["predicted_target_evse_count"] - out["baseline_target_evse_count"]
    )
    out["gap_difference_final_minus_baseline"] = (
        out["planning_gap_evse_non_benchmark_only"] - out["baseline_gap_evse"]
    )

    cols = [
        "GEOID",
        "NAMELSAD",
        "COUNTYFP",
        "county_name",
        "current_total_evse",
        "predicted_target_evse_count",
        "baseline_target_evse_count",
        "planning_gap_evse_non_benchmark_only",
        "baseline_gap_evse",
        "target_difference_final_minus_baseline",
        "gap_difference_final_minus_baseline",
    ]
    out[cols].to_csv(TABLES / "baseline_vs_final_tract_comparison.csv", index=False)
    return out


def plot_gap_difference_top50(df: pd.DataFrame) -> None:
    plot_df = df.nlargest(50, "gap_difference_final_minus_baseline").sort_values(
        "gap_difference_final_minus_baseline"
    )
    labels = plot_df.apply(lambda row: f"{row['county_name']} | {row['GEOID']}", axis=1)

    fig, ax = plt.subplots(figsize=(13, 11))
    colors = plt.cm.OrRd(np.linspace(0.35, 0.95, len(plot_df)))
    bars = ax.barh(
        labels,
        plot_df["gap_difference_final_minus_baseline"],
        color=colors,
        edgecolor="#8a2d18",
        linewidth=0.4,
    )

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + plot_df["gap_difference_final_minus_baseline"].max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"+{width:,.0f}",
            va="center",
            fontsize=8,
            color="#333333",
        )

    ax.set_title("Largest Gap Differences: Final Model minus Naive Baseline", fontsize=15, weight="bold")
    ax.set_xlabel("Additional EVSE gap in final model compared with baseline")
    ax.set_ylabel("Census tract")
    ax.grid(axis="x", alpha=0.25)
    ax.text(
        0.01,
        0.01,
        "Difference = final benchmark model value - naive gas-station baseline value.",
        transform=ax.transAxes,
        fontsize=8.5,
        color="#555555",
    )
    plt.tight_layout()
    plt.savefig(FIGURES / "baseline_vs_final_gap_difference_top50.png", dpi=220)
    plt.close()


def gap_bin_counts(df: pd.DataFrame) -> pd.DataFrame:
    bins = [-0.1, 0, 100, 250, 500, 1000, 1500, 2000, 3000, np.inf]
    labels = [
        "0",
        "1-100",
        "101-250",
        "251-500",
        "501-1000",
        "1001-1500",
        "1501-2000",
        "2001-3000",
        ">3000",
    ]
    final_counts = pd.cut(
        df["planning_gap_evse_non_benchmark_only"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    ).value_counts(sort=False)
    baseline_counts = pd.cut(
        df["baseline_gap_evse"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    ).value_counts(sort=False)
    return pd.DataFrame(
        {
            "gap_evse_bin": labels,
            "baseline_tract_count": baseline_counts.values,
            "final_model_tract_count": final_counts.values,
        }
    )


def plot_gap_bin_count_comparison(df: pd.DataFrame) -> None:
    counts = gap_bin_counts(df)
    counts.to_csv(TABLES / "baseline_vs_final_gap_bin_counts.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = np.arange(len(counts))
    width = 0.36
    baseline_bars = ax.bar(
        x - width / 2,
        counts["baseline_tract_count"],
        width,
        color="#d95f02",
        label="Naive baseline gap",
    )
    final_bars = ax.bar(
        x + width / 2,
        counts["final_model_tract_count"],
        width,
        color="#1769aa",
        label="Final model gap",
    )
    for bars in (baseline_bars, final_bars):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:,.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    ax.set_title("Census Tract Counts by EVSE Planning Gap Interval", fontsize=15, weight="bold")
    ax.set_xlabel("Planning gap interval: target EVSE - current EVSE")
    ax.set_ylabel("Number of census tracts")
    ax.set_xticks(x)
    ax.set_xticklabels(counts["gap_evse_bin"], rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    ax.text(
        0.5,
        -0.18,
        "Each bar counts how many non-benchmark census tracts fall into that gap interval.",
        ha="center",
        transform=ax.transAxes,
        fontsize=9,
        color="#555555",
    )
    plt.tight_layout()
    plt.savefig(FIGURES / "baseline_vs_final_gap_bin_counts.png", dpi=220)
    plt.close()


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    comparison = build_comparison()
    plot_gap_difference_top50(comparison)
    plot_gap_bin_count_comparison(comparison)


if __name__ == "__main__":
    main()
