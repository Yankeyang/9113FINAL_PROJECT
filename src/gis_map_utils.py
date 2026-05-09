from __future__ import annotations

from matplotlib.axes import Axes


def add_north_arrow(ax: Axes, x: float = 0.92, y: float = 0.14, size: float = 0.075) -> None:
    ax.annotate(
        "N",
        xy=(x, y + size),
        xytext=(x, y),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        bbox=dict(facecolor="white", edgecolor="black", linewidth=0.6, alpha=0.9, pad=2.2),
        arrowprops=dict(
            facecolor="black",
            edgecolor="black",
            width=4,
            headwidth=13,
            headlength=13,
            shrink=0,
        ),
        zorder=20,
    )


def add_scale_bar(
    ax: Axes,
    length_m: float,
    label: str | None = None,
    location: tuple[float, float] = (0.08, 0.07),
    linewidth: float = 4,
    anchor: str = "left",
) -> None:
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_anchor = xlim[0] + (xlim[1] - xlim[0]) * location[0]
    y0 = ylim[0] + (ylim[1] - ylim[0]) * location[1]
    if anchor == "center":
        x0 = x_anchor - length_m / 2
    else:
        x0 = x_anchor
    label = label or f"{int(length_m / 1000):,} km"

    ax.plot(
        [x0, x0 + length_m],
        [y0, y0],
        color="black",
        linewidth=linewidth,
        solid_capstyle="butt",
        zorder=20,
    )
    tick = (ylim[1] - ylim[0]) * 0.006
    ax.plot([x0, x0], [y0 - tick, y0 + tick], color="black", linewidth=linewidth * 0.6, zorder=20)
    ax.plot(
        [x0 + length_m, x0 + length_m],
        [y0 - tick, y0 + tick],
        color="black",
        linewidth=linewidth * 0.6,
        zorder=20,
    )
    ax.text(
        x0 + length_m / 2,
        y0 + tick * 2.2,
        label,
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color="black",
        zorder=20,
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.5),
    )


def add_map_credits(ax: Axes, text: str) -> None:
    ax.text(
        0.01,
        0.01,
        text,
        transform=ax.transAxes,
        fontsize=7,
        color="#4b5563",
        ha="left",
        va="bottom",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=2),
        zorder=20,
    )
