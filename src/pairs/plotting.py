"""Plotly helpers; save_figure() writes every chart to reports/figures/ as HTML and PNG."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from pairs.config import FIGURES_DIR, TICKER_A, TICKER_B

logger = logging.getLogger(__name__)

#: Fixed colour per entity (validated categorical slots 1 and 2), never reassigned.
SERIES_COLORS: dict[str, str] = {TICKER_A: "#2a78d6", TICKER_B: "#eb6834"}
#: Colour for derived single series (ratio, difference, spread) that belong to neither leg.
DERIVED_COLOR: str = "#3d3d3a"
#: Fill for "weak relationship" periods (red pole of the diverging pair).
WEAK_SHADE_COLOR: str = "#e34948"

_SURFACE = "#fcfcfb"
_TEXT_PRIMARY = "#0b0b0b"
_TEXT_SECONDARY = "#52514e"
_GRID = "#e6e5e0"


def apply_style(fig: go.Figure, title: str) -> go.Figure:
    """Apply the project's shared layout (surface, fonts, recessive grid) to a figure.

    Parameters
    ----------
    fig : go.Figure
        Figure to style in place.
    title : str
        Chart title.

    Returns
    -------
    go.Figure
        The same figure, for chaining.
    """
    fig.update_layout(
        title={"text": title, "x": 0.0, "xanchor": "left", "font": {"size": 18}},
        paper_bgcolor=_SURFACE,
        plot_bgcolor=_SURFACE,
        font={"family": "Arial, Helvetica, sans-serif", "size": 13, "color": _TEXT_PRIMARY},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "left", "x": 0.0},
        hovermode="x unified",
        margin={"l": 70, "r": 30, "t": 80, "b": 50},
    )
    fig.update_xaxes(showgrid=False, linecolor=_TEXT_SECONDARY, tickcolor=_TEXT_SECONDARY)
    fig.update_yaxes(gridcolor=_GRID, zeroline=False, linecolor=_TEXT_SECONDARY)
    return fig


def shade_periods(
    fig: go.Figure,
    mask: pd.Series,
    label: str,
    color: str = WEAK_SHADE_COLOR,
    opacity: float = 0.18,
) -> go.Figure:
    """Shade the contiguous runs of days where ``mask`` is True, with one legend entry.

    Parameters
    ----------
    fig : go.Figure
        Figure with a date x-axis, modified in place.
    mask : pd.Series
        Boolean (or nullable boolean) series indexed by date; ``<NA>`` counts as False.
    label : str
        Legend text for the shaded area.
    color : str, optional
        Fill colour.
    opacity : float, optional
        Fill opacity.

    Returns
    -------
    go.Figure
        The same figure, for chaining.

    Notes
    -----
    Each run is shaded from its first day to the first day after it (or its last day at
    the end of the series), so consecutive daily runs touch without gaps.
    """
    flags = mask.fillna(False).astype(bool).to_numpy()
    dates = mask.index
    i, n = 0, len(flags)
    while i < n:
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and flags[j + 1]:
            j += 1
        x1 = dates[j + 1] if j + 1 < n else dates[j]
        fig.add_vrect(
            x0=dates[i], x1=x1, fillcolor=color, opacity=opacity, line_width=0, layer="below"
        )
        i = j + 1
    # Invisible trace so the shading has a legend entry. It carries a real date (with no y)
    # and the axis type is forced, otherwise Plotly may infer a numeric x-axis from it.
    fig.add_trace(
        go.Scatter(
            x=[dates[0]],
            y=[None],
            mode="markers",
            name=label,
            marker={"symbol": "square", "size": 12, "color": color, "opacity": 0.4},
        )
    )
    fig.update_xaxes(type="date")
    return fig


def save_figure(
    fig: go.Figure,
    name: str,
    figures_dir: Path = FIGURES_DIR,
    width: int = 1100,
    height: int = 550,
    scale: float = 2.0,
) -> tuple[Path, Path]:
    """Save a figure as interactive HTML and static PNG.

    Parameters
    ----------
    fig : go.Figure
        Figure to save.
    name : str
        File stem, e.g. ``"01_prices_is"``; ``.html`` and ``.png`` are appended.
    figures_dir : Path, optional
        Output directory, created if missing. Defaults to ``reports/figures/``.
    width, height : int, optional
        PNG size in CSS pixels.
    scale : float, optional
        PNG resolution multiplier.

    Returns
    -------
    tuple[Path, Path]
        Paths of the HTML and PNG files.

    Notes
    -----
    The PNG is the version reviewers see on GitHub, which renders neither
    Plotly output in notebooks nor HTML files. The HTML loads plotly.js from
    a CDN to keep the repository small. PNG export needs kaleido and a local
    Chrome/Chromium.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    html_path = figures_dir / f"{name}.html"
    png_path = figures_dir / f"{name}.png"
    fig.write_html(html_path, include_plotlyjs="cdn")
    fig.write_image(png_path, width=width, height=height, scale=scale)
    logger.info("Saved figure %s (.html, .png) in %s", name, figures_dir)
    return html_path, png_path
