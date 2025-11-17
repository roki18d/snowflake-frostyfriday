from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import streamlit as st

from modules.map import build_map_deck, load_places, load_railways, load_stations
from modules.selection import extract_selected_feature
from modules.settings import DEFAULT_NEAREST_STATIONS, EARTH_RADIUS_KM, TABLE_POINTS
from modules.utils import (
    build_main_common_components,
    build_sidebar_common_components,
    create_session,
    get_logger,
)

logger = get_logger(__name__)

FORM_FIELD_KEYS = {
    "name": "selected_feature_name",
    "type": "selected_feature_type",
    "osm_id": "selected_feature_osm_id",
    "longitude": "selected_feature_longitude",
    "latitude": "selected_feature_latitude",
}

_SELECTABLE_LAYER_ORDER = (
    "railway_points_layer",
    "stations_icon_layer",
    "places_icon_layer",
)

NEAREST_STATIONS_STATE_KEY = "nearest_station_results"
SELECTED_FEATURE_STATE_KEY = "selected_feature"

FeatureDict = Dict[str, str]
NEAREST_STATION_COLUMNS = [
    "NAME",
    "TYPE",
    "OSM_ID",
    "LONGITUDE",
    "LATITUDE",
    "ST_DISTANCE_KM",
    "HAVERSINE_KM",
    "DIFF_KM",
]


def build_map_page() -> None:
    """Build the entire map display page and render data and UI."""
    session = st.session_state.session
    df_places = load_places(session)
    df_stations = load_stations(session)
    df_railways = load_railways(session)

    deck = build_map_deck(df_places, df_stations, df_railways)
    _ensure_form_state()

    # Create 2:1 layout for map and form
    col_map, col_form = st.columns([2, 1])

    with col_map:
        selection_state = st.pydeck_chart(
            deck,
            selection_mode="single-object",
            on_select="rerun",
            key="italy_arcgis_map",
        )
        _sync_selection_to_form(selection_state)

    with col_form:
        _render_selected_feature_form()

    # Display search results in full width
    _render_nearest_station_results()

    st.subheader("DataFrames")

    with st.expander("DataFrame - Places", expanded=False):
        st.dataframe(df_places.head(100), height=360)

    with st.expander("DataFrame - Stations", expanded=False):
        st.dataframe(df_stations.head(100), height=360)

    with st.expander("DataFrame - Railways", expanded=False):
        st.dataframe(df_railways.head(100), height=360)


def _ensure_form_state() -> None:
    """Ensure initial values for session state used in forms."""
    for key in FORM_FIELD_KEYS.values():
        st.session_state.setdefault(key, "")


def _sync_selection_to_form(selection_state: Any) -> None:
    """Sync selected feature to session state and form fields."""
    feature = extract_selected_feature(selection_state, _SELECTABLE_LAYER_ORDER)
    if not feature:
        return

    st.session_state[SELECTED_FEATURE_STATE_KEY] = feature
    for field, key in FORM_FIELD_KEYS.items():
        st.session_state[key] = feature.get(field, "")


def _render_selected_feature_form() -> None:
    """Render selected location information and nearest station search UI."""
    submitted = _render_selected_feature_inputs()

    st.session_state.setdefault(NEAREST_STATIONS_STATE_KEY, None)

    if submitted:
        _handle_nearest_station_search()


def _render_selected_feature_inputs() -> bool:
    """Display form input fields and return submission status."""
    with st.form("selected_feature_form"):
        st.text_input("Name", key=FORM_FIELD_KEYS["name"])
        st.text_input("Type", key=FORM_FIELD_KEYS["type"])
        st.text_input("OSM ID", key=FORM_FIELD_KEYS["osm_id"])
        st.text_input("Latitude", key=FORM_FIELD_KEYS["latitude"])
        st.text_input("Longitude", key=FORM_FIELD_KEYS["longitude"])
        return st.form_submit_button("Search", use_container_width=True)


def _handle_nearest_station_search() -> None:
    """Calculate nearest stations based on form coordinates and store in state."""
    selected_coords = _get_selected_coordinates()
    if selected_coords is None:
        st.warning("Please select a point and ensure coordinates are entered.")
        st.session_state[NEAREST_STATIONS_STATE_KEY] = None
        return

    lat, lon = selected_coords
    session = st.session_state.session
    st.session_state[NEAREST_STATIONS_STATE_KEY] = _compute_nearest_stations_with_snowflake(
        session, lat, lon
    )


def _render_nearest_station_results() -> None:
    """Render the calculated nearest station results table."""
    results_df = st.session_state.get(NEAREST_STATIONS_STATE_KEY)
    if results_df is None:
        return

    if results_df.empty:
        st.info("No station data found.")
        return

    st.dataframe(results_df, height=220, use_container_width=True)


def _get_selected_coordinates() -> Optional[Tuple[float, float]]:
    """Convert form input latitude/longitude to float and retrieve."""
    lat = _parse_float(st.session_state.get(FORM_FIELD_KEYS["latitude"], ""))
    lon = _parse_float(st.session_state.get(FORM_FIELD_KEYS["longitude"], ""))
    if lat is None or lon is None:
        return None
    return lat, lon


def _parse_float(raw_value: Any) -> Optional[float]:
    """Convert any value to float, return None on failure."""
    try:
        return float(str(raw_value).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _compute_nearest_stations_with_snowflake(
    session,
    lat: float,
    lon: float,
    top_n: int = DEFAULT_NEAREST_STATIONS,
) -> pd.DataFrame:
    """Use Snowflake geospatial functions to find nearest stations.

    This function calculates distances using both ST_DISTANCE (Snowflake)
    and Haversine formula for comparison.

    Args:
        session: Snowflake session object
        lat: Latitude of the search point
        lon: Longitude of the search point
        top_n: Number of nearest stations to return

    Returns:
        DataFrame with nearest stations and their distances in kilometers
        (both ST_DISTANCE and Haversine calculations)
    """
    sql = f"""
    SELECT
        name,
        type,
        osm_id,
        ST_X(ST_CENTROID(geography)) AS longitude,
        ST_Y(ST_CENTROID(geography)) AS latitude,
        ROUND(ST_DISTANCE(
            geography,
            ST_POINT({lon}, {lat})
        ) / 1000, 3) AS st_distance_km
    FROM {TABLE_POINTS}
    WHERE type IN ('station')
    ORDER BY st_distance_km ASC
    LIMIT {top_n}
    """

    try:
        df_result = session.sql(sql).to_pandas()

        if df_result.empty:
            return pd.DataFrame(columns=NEAREST_STATION_COLUMNS)

        # Rename columns to match expected format
        df_result.columns = [col.upper() for col in df_result.columns]

        # Calculate Haversine distance for each station
        df_result["HAVERSINE_KM"] = df_result.apply(
            lambda row: _haversine_distance_km(
                lat, lon, row["LATITUDE"], row["LONGITUDE"]
            ),
            axis=1,
        )

        # Round Haversine distance
        df_result["HAVERSINE_KM"] = df_result["HAVERSINE_KM"].round(3)

        # Calculate difference between the two methods
        df_result["DIFF_KM"] = (
            df_result["ST_DISTANCE_KM"] - df_result["HAVERSINE_KM"]
        ).round(3)

        return df_result
    except Exception as e:
        logger.error(f"Error computing nearest stations: {e}")
        return pd.DataFrame(columns=NEAREST_STATION_COLUMNS)


def _haversine_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate distance between two points using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in kilometers
    """
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_KM * c


if __name__ == "__main__":
    session = create_session()
    st.session_state.session = session

    build_main_common_components("Search Nearest Stations")
    build_sidebar_common_components()

    build_map_page()
