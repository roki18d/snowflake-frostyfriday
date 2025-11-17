"""Map display module for Italy ArcGIS application.

This module provides common functionality for displaying interactive maps
using pydeck with Places (cities, airports, etc.), Stations, and Railways data.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pydeck

from modules.settings import (
    DEFAULT_MAP_LATITUDE,
    DEFAULT_MAP_LONGITUDE,
    DEFAULT_MAP_ZOOM,
    PATH_COLOR_RGB,
    PLACES_ICON_URL,
    PLACES_TOOLTIP_BG,
    RAILWAYS_TOOLTIP_BG,
    SELECTED_PLACE_COLOR_RGB,
    STATIONS_ICON_URL,
    STATIONS_TOOLTIP_BG,
    TABLE_PLACES,
    TABLE_POINTS,
    TABLE_RAILWAYS,
)
from modules.utils import get_logger

logger = get_logger(__name__)

# SQL queries for data loading
SQL_PLACES = f"""
SELECT
    osm_id,
    name,
    type,
    ST_X(ST_CENTROID(geography)) AS longitude,
    ST_Y(ST_CENTROID(geography)) AS latitude,
FROM {TABLE_PLACES}
WHERE
    type IN ('city', 'island', 'country', 'airport')
    AND type NOT IN ('village', 'hamlet', 'town', 'locality', 'suburb')
"""

SQL_STATIONS = f"""
SELECT
    osm_id,
    name,
    type,
    ST_X(ST_CENTROID(geography)) AS longitude,
    ST_Y(ST_CENTROID(geography)) AS latitude,
FROM {TABLE_POINTS}
WHERE type IN ('station')
"""

SQL_RAILWAYS = f"""
SELECT
    osm_id,
    name,
    type,
    ST_ASGEOJSON(geography) AS geojson,
FROM {TABLE_RAILWAYS}
-- LIMIT 1000
"""


def load_places(session) -> pd.DataFrame:
    """Load places data and add visualization columns.

    Args:
        session: Snowflake session object

    Returns:
        DataFrame with places data and visualization columns
    """
    df_places = session.sql(SQL_PLACES).to_pandas()
    df_places["TOOLTIP_BG"] = PLACES_TOOLTIP_BG
    df_places["ICON_DATA"] = _build_icon_column(len(df_places), PLACES_ICON_URL)
    return df_places


def load_stations(session) -> pd.DataFrame:
    """Load stations data and add icon and tooltip styling.

    Args:
        session: Snowflake session object

    Returns:
        DataFrame with stations data and visualization columns
    """
    df_stations = session.sql(SQL_STATIONS).to_pandas()
    df_stations["TOOLTIP_BG"] = STATIONS_TOOLTIP_BG
    df_stations["ICON_DATA"] = _build_icon_column(len(df_stations), STATIONS_ICON_URL)
    return df_stations


def load_railways(session) -> pd.DataFrame:
    """Load railway GeoJSON data from Snowflake.

    Args:
        session: Snowflake session object

    Returns:
        DataFrame containing railway GeoJSON data
    """
    return session.sql(SQL_RAILWAYS).to_pandas()


def build_map_deck(
    df_places: pd.DataFrame,
    df_stations: pd.DataFrame,
    df_railways: pd.DataFrame,
    *,
    initial_latitude: float = DEFAULT_MAP_LATITUDE,
    initial_longitude: float = DEFAULT_MAP_LONGITUDE,
    initial_zoom: float = DEFAULT_MAP_ZOOM,
    selected_places: Optional[pd.DataFrame] = None,
    path_lines: Optional[List[Dict[str, Any]]] = None,
) -> pydeck.Deck:
    """Build a pydeck.Deck instance for map display.

    Args:
        df_places: Places DataFrame
        df_stations: Stations DataFrame
        df_railways: Railways DataFrame
        initial_latitude: Initial latitude for map view
        initial_longitude: Initial longitude for map view
        initial_zoom: Initial zoom level
        selected_places: DataFrame of selected places to highlight
        path_lines: List of line coordinates for path visualization

    Returns:
        Configured pydeck.Deck instance
    """
    railways_geojson, df_railway_points = _prepare_railway_layers(df_railways)

    view_state = pydeck.ViewState(
        latitude=initial_latitude,
        longitude=initial_longitude,
        zoom=initial_zoom,
        pitch=0,
        bearing=0,
    )

    layers = [
        _build_railways_layer(railways_geojson),
        _build_icon_layer(
            df_stations,
            layer_id="stations_icon_layer",
            size_min_pixels=12,
            size_max_pixels=64,
        ),
        _build_places_scatter_layer(df_places),
        _build_icon_layer(
            df_places,
            layer_id="places_icon_layer",
            size_min_pixels=24,
            size_max_pixels=128,
        ),
    ]

    if not df_railway_points.empty:
        layers.append(_build_railway_points_layer(df_railway_points))

    # Add selected places highlight layer
    if selected_places is not None and not selected_places.empty:
        layers.append(_build_selected_places_layer(selected_places))

    # Add path lines layer
    if path_lines is not None and len(path_lines) > 0:
        layers.append(_build_path_lines_layer(path_lines))

    tooltip = {
        "html": (
            "<div style=\"background-color: {TOOLTIP_BG}; padding: 6px; border-radius: 4px; "
            "color: white; min-width: 140px;\">"
            "<b>{NAME}</b><br/>Type: {TYPE}<br/>OSM ID: {OSM_ID}"
            "</div>"
        ),
        "style": {
            "backgroundColor": "rgba(0, 0, 0, 0)",
            "border": "none",
            "padding": "0",
            "fontSize": "12px",
        },
    }

    return pydeck.Deck(initial_view_state=view_state, layers=layers, tooltip=tooltip)


def _build_icon_column(length: int, url: str) -> List[Dict[str, object]]:
    """Generate icon configuration for IconLayer."""
    icon_spec = {
        "url": url,
        "width": 100,
        "height": 100,
        "anchorY": 100,
    }
    return [icon_spec] * length


def _prepare_railway_layers(
    df_railways: pd.DataFrame,
) -> Tuple[Dict[str, object], pd.DataFrame]:
    """Generate GeoJSON FeatureCollection and endpoint DataFrame for railways."""
    features: List[Dict[str, object]] = []
    endpoints: List[Dict[str, object]] = []

    for row in df_railways.itertuples(index=False):
        geometry = _parse_geometry(row.GEOJSON)
        if not geometry:
            continue

        _collect_endpoints(geometry, row, endpoints)

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "OSM_ID": row.OSM_ID,
                    "NAME": row.NAME,
                    "TYPE": row.TYPE,
                    "TOOLTIP_BG": RAILWAYS_TOOLTIP_BG,
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    points_df = _build_endpoint_dataframe(endpoints)
    return geojson, points_df


def _parse_geometry(raw_geojson: Optional[str]) -> Optional[Dict[str, object]]:
    """Parse GeoJSON string to dict, return None on failure."""
    if not raw_geojson:
        return None

    try:
        return json.loads(raw_geojson)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Invalid GeoJSON skipped")
        return None


def _collect_endpoints(
    geometry: Dict[str, object],
    row: Any,
    endpoints: List[Dict[str, object]],
) -> None:
    """Extract start and end points from railway geometry for scatter plot."""
    coordinates = geometry.get("coordinates")
    geom_type = geometry.get("type")

    def add_point(coord: Optional[List[float]]) -> None:
        if coord is None or len(coord) < 2:
            return
        endpoints.append(
            {
                "longitude": coord[0],
                "latitude": coord[1],
                "OSM_ID": row.OSM_ID,
                "NAME": row.NAME,
                "TYPE": row.TYPE,
                "TOOLTIP_BG": RAILWAYS_TOOLTIP_BG,
            }
        )

    if geom_type == "LineString" and coordinates:
        add_point(coordinates[0])
        add_point(coordinates[-1])
    elif geom_type == "MultiLineString" and coordinates:
        non_empty_lines = [line for line in coordinates if line]
        if not non_empty_lines:
            return
        add_point(non_empty_lines[0][0])
        add_point(non_empty_lines[-1][-1])


def _build_endpoint_dataframe(endpoints: List[Dict[str, object]]) -> pd.DataFrame:
    """Convert endpoint list to DataFrame, return empty DataFrame with columns if empty."""
    if not endpoints:
        columns = ["longitude", "latitude", "OSM_ID", "NAME", "TYPE", "TOOLTIP_BG"]
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(endpoints)


def _build_places_scatter_layer(df_places: pd.DataFrame) -> pydeck.Layer:
    """Build ScatterplotLayer for places."""
    return pydeck.Layer(
        "ScatterplotLayer",
        data=df_places,
        get_position=["LONGITUDE", "LATITUDE"],
        get_fill_color=[255, 159, 54, 100],
        get_radius=100,
        pickable=False,
        id="places_scatter_layer",
    )


def _build_icon_layer(
    df: pd.DataFrame,
    *,
    layer_id: str,
    size_min_pixels: int,
    size_max_pixels: int,
) -> pydeck.Layer:
    """Build IconLayer for displaying location data with icons."""
    return pydeck.Layer(
        "IconLayer",
        data=df,
        get_position=["LONGITUDE", "LATITUDE"],
        get_icon="ICON_DATA",
        get_size=60,
        size_units="meters",
        size_scale=0.5,
        size_min_pixels=size_min_pixels,
        size_max_pixels=size_max_pixels,
        pickable=True,
        auto_highlight=True,
        id=layer_id,
    )


def _build_railways_layer(railways_geojson: Dict[str, object]) -> pydeck.Layer:
    """Build GeoJsonLayer for railway lines."""
    return pydeck.Layer(
        "GeoJsonLayer",
        data=railways_geojson,
        pickable=True,
        stroked=True,
        filled=False,
        get_line_color=[212, 91, 144, 160],
        get_line_width=2,
        line_width_min_pixels=2,
        id="railways_geojson_layer",
    )


def _build_railway_points_layer(df_points: pd.DataFrame) -> pydeck.Layer:
    """Build ScatterplotLayer for railway endpoints."""
    return pydeck.Layer(
        "ScatterplotLayer",
        data=df_points,
        get_position=["longitude", "latitude"],
        get_fill_color=[212, 91, 144, 220],
        get_radius=120,
        pickable=True,
        auto_highlight=True,
        id="railway_points_layer",
    )


def _build_selected_places_layer(df_selected: pd.DataFrame) -> pydeck.Layer:
    """Build ScatterplotLayer to highlight selected places.

    Args:
        df_selected: DataFrame with selected places (must have LONGITUDE, LATITUDE columns)

    Returns:
        pydeck.Layer for selected places visualization
    """
    r, g, b = SELECTED_PLACE_COLOR_RGB
    return pydeck.Layer(
        "ScatterplotLayer",
        data=df_selected,
        get_position=["LONGITUDE", "LATITUDE"],
        get_fill_color=[r, g, b, 180],
        get_line_color=[r, g, b, 255],
        get_radius=2000,
        line_width_min_pixels=2,
        stroked=True,
        pickable=False,
        id="selected_places_layer",
    )


def _build_path_lines_layer(path_lines: List[Dict[str, Any]]) -> pydeck.Layer:
    """Build LineLayer to visualize the shortest path.

    Args:
        path_lines: List of dicts with 'start' and 'end' coordinates
                   e.g., [{"start": [lon1, lat1], "end": [lon2, lat2]}, ...]

    Returns:
        pydeck.Layer for path lines visualization
    """
    r, g, b = PATH_COLOR_RGB
    return pydeck.Layer(
        "LineLayer",
        data=path_lines,
        get_source_position="start",
        get_target_position="end",
        get_color=[r, g, b, 255],
        get_width=5,
        width_min_pixels=3,
        pickable=False,
        id="path_lines_layer",
    )
