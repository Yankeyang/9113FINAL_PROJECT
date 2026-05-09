"""Create KDE maps with real-world color basemaps.

These maps are presentation-oriented alternatives to the dark KDE maps.
They use OpenStreetMap-style basemaps and transparent KDE overlays.
"""

from __future__ import annotations

from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde
from shapely.geometry import box

from gis_map_utils import add_map_credits, add_north_arrow, add_scale_bar


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"

CRS_WEB_MERCATOR = "EPSG:3857"
CRS_WGS84 = "EPSG:4326"


def kde_surface(
    points_gdf: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float],
    nx: int,
    ny: int,
) -> np.ndarray:
    minx, miny, maxx, maxy = bounds
    subset = points_gdf.cx[minx:maxx, miny:maxy].copy()
    if len(subset) < 5:
        return np.array([])

    weights = subset["total_evse"].replace(0, 1).to_numpy()
    xy = np.vstack([subset.geometry.x.to_numpy(), subset.geometry.y.to_numpy()])
    kde = gaussian_kde(xy, weights=weights)

    x_grid = np.linspace(minx, maxx, nx)
    y_grid = np.linspace(miny, maxy, ny)
    xx, yy = np.meshgrid(x_grid, y_grid)
    return kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)


def plot_statewide_osm_kde(chargers: gpd.GeoDataFrame, tracts: gpd.GeoDataFrame) -> None:
    minx, miny, maxx, maxy = tracts.total_bounds
    z = kde_surface(chargers, (minx, miny, maxx, maxy), nx=430, ny=520)
    z = np.where(z >= np.nanpercentile(z, 74), z, np.nan)

    fig, ax = plt.subplots(figsize=(11, 13), facecolor="white")
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    cx.add_basemap(
        ax,
        source=cx.providers.OpenStreetMap.Mapnik,
        zoom=6,
        attribution_size=6,
    )
    tracts.dissolve().boundary.plot(ax=ax, linewidth=1.0, color="#4b5563", alpha=0.75)
    image = ax.imshow(
        z,
        extent=[minx, maxx, miny, maxy],
        origin="lower",
        cmap="YlOrRd",
        alpha=0.62,
        vmax=np.nanpercentile(z, 99.6),
    )
    fig.colorbar(image, ax=ax, fraction=0.032, pad=0.01, label="EVSE-weighted KDE intensity")
    ax.set_title(
        "California Public EV Charger KDE Hotspots\nOpenStreetMap basemap, high-density areas",
        fontsize=16,
        pad=12,
    )
    add_scale_bar(ax, 200_000, "200 km", location=(0.50, 0.055), anchor="center")
    add_north_arrow(ax, x=0.075, y=0.86)
    add_map_credits(ax, "Basemap: OpenStreetMap | KDE weighted by EVSE ports")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "ca_ev_charger_kde_osm_basemap.png", dpi=240)
    plt.close(fig)


def plot_regional_osm_kde(chargers: gpd.GeoDataFrame) -> None:
    regions = {
        "Los Angeles Region": (-119.1, 33.45, -117.55, 34.45),
        "San Francisco Bay Area": (-122.65, 37.15, -121.65, 38.05),
        "San Diego Region": (-117.45, 32.45, -116.75, 33.15),
    }

    fig, axes = plt.subplots(1, 3, figsize=(17, 6), facecolor="white")
    for ax, (title, lonlat_bounds) in zip(axes, regions.items()):
        region_poly = gpd.GeoSeries([box(*lonlat_bounds)], crs=CRS_WGS84).to_crs(
            CRS_WEB_MERCATOR
        )
        minx, miny, maxx, maxy = tuple(region_poly.total_bounds)
        z = kde_surface(chargers, (minx, miny, maxx, maxy), nx=300, ny=300)

        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        cx.add_basemap(
            ax,
            source=cx.providers.OpenStreetMap.Mapnik,
            zoom=10,
            attribution_size=5,
        )
        if z.size:
            z = np.where(z >= np.nanpercentile(z, 60), z, np.nan)
            ax.imshow(
                z,
                extent=[minx, maxx, miny, maxy],
                origin="lower",
                cmap="YlOrRd",
                alpha=0.62,
                vmax=np.nanpercentile(z, 99.5),
            )
        chargers.cx[minx:maxx, miny:maxy].plot(
            ax=ax,
            markersize=1.2,
            color="#111827",
            alpha=0.35,
        )
        add_scale_bar(ax, 20_000, "20 km", location=(0.50, 0.07), linewidth=3, anchor="center")
        add_north_arrow(ax, x=0.10, y=0.80, size=0.065)
        ax.set_title(title, fontsize=13, pad=8)
        ax.set_axis_off()

    fig.suptitle(
        "EV Charging Infrastructure Benchmark Regions\nKDE over real-world basemap",
        fontsize=17,
        y=0.98,
    )
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "benchmark_regions_kde_osm_basemap.png", dpi=240)
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    chargers = gpd.read_file(PROCESSED_DIR / "cec_existing_public_chargers_clean.gpkg").to_crs(
        CRS_WEB_MERCATOR
    )
    tracts = gpd.read_file(PROCESSED_DIR / "ca_census_tracts_2024_clean.gpkg").to_crs(
        CRS_WEB_MERCATOR
    )
    plot_statewide_osm_kde(chargers, tracts)
    plot_regional_osm_kde(chargers)


if __name__ == "__main__":
    main()
