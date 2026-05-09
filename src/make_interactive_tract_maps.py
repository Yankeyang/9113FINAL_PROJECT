from pathlib import Path
import json

import geopandas as gpd
import pandas as pd
import plotly.express as px


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
INTERACTIVE = OUTPUTS / "interactive"

CRS_CA_ALBERS = "EPSG:3310"
CRS_WGS84 = "EPSG:4326"
BENCHMARK_COL = "evse_per_1000_light_duty_vehicles_population_weighted"

GAP_CATEGORY_ORDER = [
    "Benchmark standard 20-100",
    "No vehicle-ratio data, excluded",
    "Above standard >100, excluded",
    "Gap 0 EVSE",
    "Gap 1-10 EVSE",
    "Gap 11-25 EVSE",
    "Gap 26-50 EVSE",
    "Gap 51-100 EVSE",
    "Gap 101-250 EVSE",
    "Gap 251-500 EVSE",
    "Gap 501-1000 EVSE",
    "Gap >1000 EVSE",
]
GAP_COLORS = {
    "Benchmark standard 20-100": "#d9d9d9",
    "No vehicle-ratio data, excluded": "#f3f4f6",
    "Above standard >100, excluded": "#238b45",
    "Gap 0 EVSE": "#f7f7f7",
    "Gap 1-10 EVSE": "#fff7bc",
    "Gap 11-25 EVSE": "#fee391",
    "Gap 26-50 EVSE": "#fec44f",
    "Gap 51-100 EVSE": "#fe9929",
    "Gap 101-250 EVSE": "#ec7014",
    "Gap 251-500 EVSE": "#cc4c02",
    "Gap 501-1000 EVSE": "#993404",
    "Gap >1000 EVSE": "#4d1600",
}

BENCHMARK_CATEGORY_ORDER = [
    "0 EVSE / 1,000 vehicles",
    "0-1 EVSE / 1,000 vehicles",
    "1-5 EVSE / 1,000 vehicles",
    "5-10 EVSE / 1,000 vehicles",
    "10-20 EVSE / 1,000 vehicles",
    "20-50 EVSE / 1,000 vehicles",
    "50-100 EVSE / 1,000 vehicles",
    ">100 EVSE / 1,000 vehicles",
]
BENCHMARK_COLORS = {
    "0 EVSE / 1,000 vehicles": "#ffffcc",
    "0-1 EVSE / 1,000 vehicles": "#c7e9b4",
    "1-5 EVSE / 1,000 vehicles": "#7fcdbb",
    "5-10 EVSE / 1,000 vehicles": "#41b6c4",
    "10-20 EVSE / 1,000 vehicles": "#1d91c0",
    "20-50 EVSE / 1,000 vehicles": "#225ea8",
    "50-100 EVSE / 1,000 vehicles": "#253494",
    ">100 EVSE / 1,000 vehicles": "#081d58",
}


def load_interactive_data() -> gpd.GeoDataFrame:
    geo = gpd.read_file(DATA / "processed" / "ca_tract_charger_join_with_kde.gpkg")
    geo["GEOID"] = geo["GEOID"].astype(str).str.zfill(11)

    statewide = pd.read_csv(
        DATA / "processed" / "final_scale_model_statewide_gap_results_nonbenchmark_flagged.csv",
        dtype={"GEOID": str},
    )
    statewide["GEOID"] = statewide["GEOID"].astype(str).str.zfill(11)

    keep_cols = [
        "GEOID",
        "NAMELSAD",
        "population",
        "tract_area_sq_mi",
        "light_duty_vehicles_population_weighted",
        "ev_vehicles_population_weighted",
        BENCHMARK_COL,
        "is_benchmark_20to100",
        "is_above_standard_gt100",
        "is_below_standard_lt20",
        "application_group",
        "predicted_target_evse_count",
        "current_total_evse",
        "planning_gap_evse_non_benchmark_only",
        "planning_gap_bin",
    ]
    gdf = geo[["GEOID", "geometry"]].merge(statewide[keep_cols], on="GEOID", how="left")

    gdf["gap_map_class"] = "Gap " + gdf["planning_gap_bin"].astype(str) + " EVSE"
    gdf.loc[gdf["is_benchmark_20to100"], "gap_map_class"] = "Benchmark standard 20-100"
    gdf.loc[gdf["is_above_standard_gt100"], "gap_map_class"] = "Above standard >100, excluded"
    gdf.loc[
        gdf["application_group"] == "excluded_no_vehicle_ratio",
        "gap_map_class",
    ] = "No vehicle-ratio data, excluded"
    gdf["gap_map_class"] = pd.Categorical(
        gdf["gap_map_class"],
        categories=GAP_CATEGORY_ORDER,
        ordered=True,
    )

    gdf["benchmark_map_class"] = pd.cut(
        gdf[BENCHMARK_COL],
        bins=[-0.1, 0, 1, 5, 10, 20, 50, 100, float("inf")],
        labels=BENCHMARK_CATEGORY_ORDER,
        include_lowest=True,
    )

    numeric_cols = [
        "population",
        "tract_area_sq_mi",
        "light_duty_vehicles_population_weighted",
        "ev_vehicles_population_weighted",
        BENCHMARK_COL,
        "predicted_target_evse_count",
        "current_total_evse",
        "planning_gap_evse_non_benchmark_only",
    ]
    for col in numeric_cols:
        gdf[col] = pd.to_numeric(gdf[col], errors="coerce").round(2)

    # Browser maps need tract boundaries as GeoJSON. A light geometric simplification
    # keeps the full tract-level data and hover fields while avoiding GB-scale HTML.
    return gdf.to_crs(CRS_CA_ALBERS).simplify(60).to_frame("geometry").join(
        gdf.drop(columns="geometry").set_index(gdf.index)
    ).set_geometry("geometry").to_crs(CRS_WGS84)


def compact_geojson(gdf: gpd.GeoDataFrame) -> dict:
    return json.loads(gdf[["GEOID", "geometry"]].to_json(drop_id=True))


def make_hover_data() -> dict[str, bool | str]:
    return {
        "GEOID": True,
        "NAMELSAD": True,
        "population": ":,.0f",
        "tract_area_sq_mi": ":,.2f",
        "light_duty_vehicles_population_weighted": ":,.0f",
        "ev_vehicles_population_weighted": ":,.0f",
        BENCHMARK_COL: ":,.2f",
        "current_total_evse": ":,.0f",
        "predicted_target_evse_count": ":,.0f",
        "planning_gap_evse_non_benchmark_only": ":,.0f",
        "gap_map_class": False,
        "benchmark_map_class": False,
    }


def style_layout(fig, title: str) -> None:
    fig.update_traces(marker_line_width=0.15, marker_line_color="rgba(255,255,255,0.45)")
    fig.update_layout(
        title={"text": title, "x": 0.42, "xanchor": "center"},
        height=900,
        margin={"l": 10, "r": 300, "t": 70, "b": 10},
        legend={
            "title": {"text": "Map legend"},
            "x": 1.02,
            "y": 0.98,
            "xanchor": "left",
            "yanchor": "top",
            "bgcolor": "rgba(255,255,255,0.96)",
            "bordercolor": "#c7c7c7",
            "borderwidth": 1,
        },
        map={
            "style": "carto-positron",
            "center": {"lat": 37.2, "lon": -119.5},
            "zoom": 5.05,
        },
    )


def write_gap_map(gdf: gpd.GeoDataFrame) -> None:
    geojson = compact_geojson(gdf)
    table = pd.DataFrame(gdf.drop(columns="geometry"))
    fig = px.choropleth_map(
        table,
        geojson=geojson,
        locations="GEOID",
        featureidkey="properties.GEOID",
        color="gap_map_class",
        category_orders={"gap_map_class": GAP_CATEGORY_ORDER},
        color_discrete_map=GAP_COLORS,
        hover_name="NAMELSAD",
        hover_data=make_hover_data(),
    )
    style_layout(
        fig,
        "Interactive Final Model EVSE Planning Gap by California Census Tract",
    )
    fig.write_html(
        INTERACTIVE / "interactive_final_model_gap_by_tract.html",
        include_plotlyjs="cdn",
        full_html=True,
    )


def write_benchmark_map(gdf: gpd.GeoDataFrame) -> None:
    geojson = compact_geojson(gdf)
    table = pd.DataFrame(gdf.drop(columns="geometry"))
    fig = px.choropleth_map(
        table,
        geojson=geojson,
        locations="GEOID",
        featureidkey="properties.GEOID",
        color="benchmark_map_class",
        category_orders={"benchmark_map_class": BENCHMARK_CATEGORY_ORDER},
        color_discrete_map=BENCHMARK_COLORS,
        hover_name="NAMELSAD",
        hover_data=make_hover_data(),
    )
    style_layout(
        fig,
        "Interactive EV Charger Benchmark Value by California Census Tract",
    )
    fig.write_html(
        INTERACTIVE / "interactive_ev_charger_benchmark_value_by_tract.html",
        include_plotlyjs="cdn",
        full_html=True,
    )


def main() -> None:
    INTERACTIVE.mkdir(parents=True, exist_ok=True)
    gdf = load_interactive_data()
    gdf.drop(columns="geometry").to_csv(
        INTERACTIVE / "interactive_tract_hover_data_complete.csv",
        index=False,
    )
    write_gap_map(gdf)
    write_benchmark_map(gdf)
    print(f"Wrote interactive maps to {INTERACTIVE}")


if __name__ == "__main__":
    main()
