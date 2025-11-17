"""H3 Index visualization module for Italy ArcGIS application.

This module provides H3 hexagon grid visualization, density analysis,
and coverage analysis using Snowflake's H3 functions and pydeck.
"""

from typing import Any, Dict, List

import pandas as pd
import pydeck

from modules.h3_settings import (
    H3_COVERAGE_COVERED,
    H3_COVERAGE_UNCOVERED,
    H3_DENSITY_COLORS,
    H3_GRID_COLOR,
)
from modules.settings import (
    DEFAULT_MAP_LATITUDE,
    DEFAULT_MAP_LONGITUDE,
    DEFAULT_MAP_ZOOM,
    PLACES_ICON_URL,
    STATIONS_ICON_URL,
    TABLE_PLACES,
    TABLE_POINTS,
)
from modules.utils import get_logger

logger = get_logger(__name__)


def load_h3_grid_data(session, resolution: int) -> pd.DataFrame:
    """Load H3 grid cells covering Italy.

    Args:
        session: Snowflake session object
        resolution: H3 resolution (0-15)

    Returns:
        DataFrame with H3 cell IDs and boundaries
    """
    sql = f"""
    SELECT DISTINCT
        H3_POINT_TO_CELL_STRING(geography, {resolution}) AS h3_cell
    FROM {TABLE_PLACES}
    WHERE geography IS NOT NULL
    """

    df = session.sql(sql).to_pandas()

    # Ensure column name is uppercase for consistency
    if 'h3_cell' in df.columns:
        df.rename(columns={'h3_cell': 'H3_CELL'}, inplace=True)

    # Log sample data for debugging
    if not df.empty:
        logger.info(f"Loaded {len(df)} H3 cells at resolution {resolution}")
        logger.info(f"Sample H3 cell IDs: {df['H3_CELL'].head(3).tolist()}")
        logger.info(f"H3_CELL dtype: {df['H3_CELL'].dtype}")
    else:
        logger.warning(f"No H3 cells loaded at resolution {resolution}")

    return df


def load_h3_density_data(session, resolution: int) -> pd.DataFrame:
    """Load H3 grid with city density counts.

    Args:
        session: Snowflake session object
        resolution: H3 resolution (0-15)

    Returns:
        DataFrame with H3 cells and city counts
    """
    sql = f"""
    SELECT
        H3_POINT_TO_CELL_STRING(geography, {resolution}) AS h3_cell,
        COUNT(*) AS city_count
    FROM {TABLE_PLACES}
    WHERE
        type IN ('city', 'town')
        AND geography IS NOT NULL
    GROUP BY h3_cell
    ORDER BY city_count DESC
    """

    df = session.sql(sql).to_pandas()

    # Ensure column names are uppercase
    df.columns = df.columns.str.upper()

    logger.info(f"Loaded {len(df)} H3 cells with density data at resolution {resolution}")
    return df


def load_city_locations(session) -> pd.DataFrame:
    """Load city locations for icon layer.

    Args:
        session: Snowflake session object

    Returns:
        DataFrame with city coordinates
    """
    sql = f"""
    SELECT
        osm_id,
        name,
        type,
        ST_X(ST_CENTROID(geography)) AS longitude,
        ST_Y(ST_CENTROID(geography)) AS latitude
    FROM {TABLE_PLACES}
    WHERE
        type IN ('city', 'town')
        AND geography IS NOT NULL
    """

    df = session.sql(sql).to_pandas()
    df.columns = df.columns.str.upper()

    logger.info(f"Loaded {len(df)} city locations for icon layer")
    return df


def load_station_locations(session) -> pd.DataFrame:
    """Load station location data for icon layer.

    Args:
        session: Snowflake session object

    Returns:
        DataFrame with station coordinates
    """
    sql = f"""
    SELECT
        osm_id,
        name,
        type,
        ST_X(ST_CENTROID(geography)) AS longitude,
        ST_Y(ST_CENTROID(geography)) AS latitude
    FROM {TABLE_POINTS}
    WHERE
        type = 'station'
        AND geography IS NOT NULL
    """

    df = session.sql(sql).to_pandas()
    df.columns = df.columns.str.upper()

    logger.info(f"Loaded {len(df)} station locations for icon layer")
    return df


def load_h3_coverage_data(session, resolution: int, radius_km: float) -> pd.DataFrame:
    """Load H3 coverage analysis for railway stations.

    Args:
        session: Snowflake session object
        resolution: H3 resolution (0-15)
        radius_km: Coverage radius in kilometers

    Returns:
        DataFrame with H3 cells marked as covered/uncovered
    """

    # Get covered cells (near stations)
    # Use ST_DWITHIN with CROSS JOIN approach
    # ST_DWITHIN expects distance in meters
    radius_m = int(radius_km * 1000)
    sql_covered = f"""
    WITH all_italy_cells AS (
        -- Generate H3 cells from both places (cities) and points (stations)
        -- to ensure complete coverage of Italy
        SELECT DISTINCT
            H3_POINT_TO_CELL(geography, {resolution}) AS h3_cell_int,
            H3_POINT_TO_CELL_STRING(geography, {resolution}) AS h3_cell
        FROM {TABLE_PLACES}
        WHERE geography IS NOT NULL

        UNION

        SELECT DISTINCT
            H3_POINT_TO_CELL(geography, {resolution}) AS h3_cell_int,
            H3_POINT_TO_CELL_STRING(geography, {resolution}) AS h3_cell
        FROM {TABLE_POINTS}
        WHERE geography IS NOT NULL AND type = 'station'
    ),
    stations AS (
        SELECT geography AS station_geo
        FROM {TABLE_POINTS}
        WHERE type = 'station'
    ),
    cell_station_pairs AS (
        SELECT DISTINCT
            c.h3_cell,
            c.h3_cell_int
        FROM all_italy_cells c
        CROSS JOIN stations s
        WHERE ST_DWITHIN(
            ST_CENTROID(H3_CELL_TO_BOUNDARY(c.h3_cell_int)),
            s.station_geo,
            {radius_m}
        )
    )
    SELECT
        a.h3_cell,
        CASE WHEN p.h3_cell IS NOT NULL THEN 1 ELSE 0 END AS is_covered
    FROM all_italy_cells a
    LEFT JOIN cell_station_pairs p ON a.h3_cell = p.h3_cell
    """

    df = session.sql(sql_covered).to_pandas()

    # Ensure column names are uppercase
    df.columns = df.columns.str.upper()

    covered_count = df[df["IS_COVERED"] == 1].shape[0]
    total_count = len(df)
    coverage_rate = (covered_count / total_count * 100) if total_count > 0 else 0

    logger.info(
        f"Coverage analysis: {covered_count}/{total_count} cells covered "
        f"({coverage_rate:.1f}%) at resolution {resolution}, radius {radius_km}km"
    )

    return df


def build_h3_grid_deck(df_h3: pd.DataFrame, resolution: int) -> pydeck.Deck:
    """Build pydeck.Deck for H3 grid visualization.

    Args:
        df_h3: DataFrame with H3 cell IDs
        resolution: H3 resolution for display info

    Returns:
        Configured pydeck.Deck instance
    """
    # Ensure H3_CELL column exists and is string type
    if 'H3_CELL' not in df_h3.columns:
        logger.warning(f"H3_CELL column not found. Available columns: {df_h3.columns.tolist()}")
        return pydeck.Deck()

    # Convert H3 cell IDs to string if they aren't already
    df_h3['H3_CELL'] = df_h3['H3_CELL'].astype(str)

    view_state = pydeck.ViewState(
        latitude=DEFAULT_MAP_LATITUDE,
        longitude=DEFAULT_MAP_LONGITUDE,
        zoom=DEFAULT_MAP_ZOOM,
        pitch=0,
        bearing=0,
    )

    layer = pydeck.Layer(
        "H3HexagonLayer",
        df_h3,
        get_hexagon="H3_CELL",
        get_fill_color=H3_GRID_COLOR,
        get_line_color=[80, 80, 80, 100],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
        extruded=False,
    )

    tooltip = {
        "html": "<b>H3 Cell:</b> {H3_CELL}",
        "style": {"backgroundColor": "steelblue", "color": "white"},
    }

    return pydeck.Deck(initial_view_state=view_state, layers=[layer], tooltip=tooltip)


def build_h3_density_deck(
    df_density: pd.DataFrame,
    df_cities: pd.DataFrame,
    resolution: int,
    low_threshold_pct: float = 33.0,
    high_threshold_pct: float = 66.0,
    show_city_icons: bool = True,
) -> pydeck.Deck:
    """Build pydeck.Deck for H3 density heatmap with optional city icons.

    Args:
        df_density: DataFrame with H3 cells and city counts
        df_cities: DataFrame with city locations
        resolution: H3 resolution for display info
        low_threshold_pct: Low density threshold as percentage of max (default: 33%)
        high_threshold_pct: High density threshold as percentage of max (default: 66%)
        show_city_icons: Whether to show city icon markers (default: True)

    Returns:
        Configured pydeck.Deck instance
    """
    if df_density.empty or 'H3_CELL' not in df_density.columns:
        logger.warning("Cannot build density deck: empty data or missing H3_CELL column")
        return pydeck.Deck()

    # Convert H3 cell IDs to string
    df_density['H3_CELL'] = df_density['H3_CELL'].astype(str)

    # Calculate density thresholds based on percentages
    max_count = df_density["CITY_COUNT"].max() if not df_density.empty else 1
    low_threshold = max_count * (low_threshold_pct / 100.0)
    high_threshold = max_count * (high_threshold_pct / 100.0)

    # Assign colors and density information
    def get_density_color(count: int) -> List[int]:
        if count >= high_threshold:
            return H3_DENSITY_COLORS["high"]
        elif count >= low_threshold:
            return H3_DENSITY_COLORS["medium"]
        else:
            return H3_DENSITY_COLORS["low"]

    def get_density_category(count: int) -> str:
        if count >= high_threshold:
            return "High"
        elif count >= low_threshold:
            return "Medium"
        else:
            return "Low"

    def get_density_percentage(count: int) -> float:
        return (count / max_count * 100.0) if max_count > 0 else 0.0

    df_density["COLOR"] = df_density["CITY_COUNT"].apply(get_density_color)
    df_density["DENSITY_CATEGORY"] = df_density["CITY_COUNT"].apply(get_density_category)
    df_density["DENSITY_PCT"] = df_density["CITY_COUNT"].apply(get_density_percentage)
    # Format percentage as string for tooltip display (PyDeck doesn't support format specifiers)
    df_density["DENSITY_PCT_STR"] = df_density["DENSITY_PCT"].apply(lambda x: f"{x:.1f}")

    view_state = pydeck.ViewState(
        latitude=DEFAULT_MAP_LATITUDE,
        longitude=DEFAULT_MAP_LONGITUDE,
        zoom=DEFAULT_MAP_ZOOM,
        pitch=0,
        bearing=0,
    )

    # H3 hexagon layer with tooltip
    h3_layer = pydeck.Layer(
        "H3HexagonLayer",
        df_density,
        get_hexagon="H3_CELL",
        get_fill_color="COLOR",
        get_line_color=[60, 60, 60, 120],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
        extruded=False,
        id="h3_density_layer",
    )

    layers = [h3_layer]

    # Add city icon layer if enabled and data is available
    # Note: pickable=False to disable tooltip on icons
    logger.info(f"show_city_icons={show_city_icons}, df_cities.empty={df_cities.empty}, df_cities.shape={df_cities.shape}")

    if show_city_icons and not df_cities.empty:
        logger.info(f"Adding city icon layer with {len(df_cities)} cities")
        # Prepare icon data for cities using the same icon as places
        icon_data = {
            "url": PLACES_ICON_URL,
            "width": 100,
            "height": 100,
            "anchorY": 100,
        }
        df_cities["ICON_DATA"] = [icon_data] * len(df_cities)

        city_icon_layer = pydeck.Layer(
            "IconLayer",
            df_cities,
            get_position=["LONGITUDE", "LATITUDE"],
            get_icon="ICON_DATA",
            get_size=4,
            size_scale=8,
            size_min_pixels=6,
            size_max_pixels=20,
            pickable=False,  # Disable tooltip for city icons
            auto_highlight=False,
            id="city_icon_layer",
        )
        layers.append(city_icon_layer)
        logger.info(f"City icon layer added. Total layers: {len(layers)}")
    else:
        logger.info(f"City icon layer NOT added. show_city_icons={show_city_icons}, df_cities.empty={df_cities.empty}")

    # Tooltip configuration - only shows for H3 hexagon layer
    tooltip = {
        "html": (
            "<div style='background-color: rgba(0,0,0,0.8); padding: 10px; "
            "border-radius: 4px; color: white;'>"
            "<b>H3 Cell:</b> {H3_CELL}<br/>"
            "<b>City Count:</b> {CITY_COUNT}<br/>"
            "<b>Density:</b> {DENSITY_PCT_STR}% of max<br/>"
            "<b>Category:</b> {DENSITY_CATEGORY}"
            "</div>"
        ),
        "style": {"backgroundColor": "rgba(0,0,0,0)", "color": "white"},
    }

    return pydeck.Deck(initial_view_state=view_state, layers=layers, tooltip=tooltip)


def build_h3_coverage_deck(
    df_coverage: pd.DataFrame, df_stations: pd.DataFrame, resolution: int, radius_km: float
) -> pydeck.Deck:
    """Build pydeck.Deck for H3 coverage analysis with station icons.

    Args:
        df_coverage: DataFrame with H3 cells and coverage status
        df_stations: DataFrame with station coordinates
        resolution: H3 resolution for display info
        radius_km: Coverage radius in kilometers

    Returns:
        Configured pydeck.Deck instance
    """
    if df_coverage.empty or 'H3_CELL' not in df_coverage.columns:
        logger.warning("Cannot build coverage deck: empty data or missing H3_CELL column")
        return pydeck.Deck()

    # Convert H3 cell IDs to string
    df_coverage['H3_CELL'] = df_coverage['H3_CELL'].astype(str)

    # Assign colors based on coverage status
    def get_coverage_color(is_covered: int) -> List[int]:
        return H3_COVERAGE_COVERED if is_covered == 1 else H3_COVERAGE_UNCOVERED

    df_coverage["COLOR"] = df_coverage["IS_COVERED"].apply(
        lambda x: get_coverage_color(x)
    )

    view_state = pydeck.ViewState(
        latitude=DEFAULT_MAP_LATITUDE,
        longitude=DEFAULT_MAP_LONGITUDE,
        zoom=DEFAULT_MAP_ZOOM,
        pitch=0,
        bearing=0,
    )

    # H3 coverage layer
    h3_layer = pydeck.Layer(
        "H3HexagonLayer",
        df_coverage,
        get_hexagon="H3_CELL",
        get_fill_color="COLOR",
        get_line_color=[40, 40, 40, 80],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
        extruded=False,
        id="h3_coverage_layer",
    )

    layers = [h3_layer]

    # Add station icon layer if data is available
    if not df_stations.empty:
        icon_data = {
            "url": STATIONS_ICON_URL,
            "width": 256,
            "height": 256,
            "anchorY": 256,
        }
        df_stations["ICON_DATA"] = [icon_data] * len(df_stations)

        station_icon_layer = pydeck.Layer(
            "IconLayer",
            df_stations,
            get_position=["LONGITUDE", "LATITUDE"],
            get_icon="ICON_DATA",
            get_size=2,
            size_scale=4,
            size_min_pixels=4,
            size_max_pixels=12,
            pickable=False,  # Disable tooltip for station icons
            auto_highlight=False,
            id="station_icon_layer",
        )
        layers.append(station_icon_layer)

    # Tooltip - only shows for H3 hexagon layer
    tooltip = {
        "html": (
            "<div style='background-color: rgba(0,0,0,0.8); padding: 8px; "
            "border-radius: 4px; color: white;'>"
            "<b>H3 Cell:</b> {H3_CELL}<br/>"
            "<b>Coverage:</b> {IS_COVERED}"
            "</div>"
        ),
        "style": {"backgroundColor": "rgba(0,0,0,0)", "color": "white"},
    }

    return pydeck.Deck(initial_view_state=view_state, layers=layers, tooltip=tooltip)


def calculate_coverage_stats(df_coverage: pd.DataFrame) -> Dict[str, Any]:
    """Calculate coverage statistics from coverage data.

    Args:
        df_coverage: DataFrame with IS_COVERED column

    Returns:
        Dictionary with coverage statistics
    """
    total_cells = len(df_coverage)
    covered_cells = df_coverage[df_coverage["IS_COVERED"] == 1].shape[0]
    uncovered_cells = total_cells - covered_cells
    coverage_rate = (covered_cells / total_cells * 100) if total_cells > 0 else 0

    return {
        "total_cells": total_cells,
        "covered_cells": covered_cells,
        "uncovered_cells": uncovered_cells,
        "coverage_rate": coverage_rate,
    }


def calculate_density_stats(df_density: pd.DataFrame) -> Dict[str, Any]:
    """Calculate density statistics from density data.

    Args:
        df_density: DataFrame with CITY_COUNT column

    Returns:
        Dictionary with density statistics
    """
    total_cells = len(df_density)
    total_cities = df_density["CITY_COUNT"].sum() if not df_density.empty else 0
    max_cities = df_density["CITY_COUNT"].max() if not df_density.empty else 0
    avg_cities = df_density["CITY_COUNT"].mean() if not df_density.empty else 0

    return {
        "total_cells": total_cells,
        "total_cities": int(total_cities),
        "max_cities_per_cell": int(max_cities),
        "avg_cities_per_cell": float(avg_cities),
    }
