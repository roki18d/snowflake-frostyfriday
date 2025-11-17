"""Shortest Path Exploration Page.

This page allows users to select up to 8 places on the map and
calculates the optimal shortest path visiting all selected locations.
Uses brute-force exhaustive search to guarantee the optimal solution.
"""

from itertools import permutations
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

from modules.map import build_map_deck, load_places, load_railways, load_stations
from modules.selection import extract_selected_feature
from modules.settings import EARTH_RADIUS_KM, MAX_SELECTABLE_PLACES
from modules.utils import (
    build_main_common_components,
    build_sidebar_common_components,
    create_session,
    get_logger,
)

logger = get_logger(__name__)

MAX_PLACES = MAX_SELECTABLE_PLACES
SELECTED_PLACES_KEY = "selected_places_list"
SHORTEST_PATH_KEY = "shortest_path_result"
LAST_SELECTION_KEY = "last_processed_selection"

_SELECTABLE_LAYER_ORDER = (
    "places_icon_layer",
)


def build_shortest_path_page() -> None:
    """Build the shortest path exploration page with map and UI."""
    session = st.session_state.session
    df_places = load_places(session)
    df_stations = load_stations(session)
    df_railways = load_railways(session)

    # Initialize session state
    if SELECTED_PLACES_KEY not in st.session_state:
        st.session_state[SELECTED_PLACES_KEY] = []
    if SHORTEST_PATH_KEY not in st.session_state:
        st.session_state[SHORTEST_PATH_KEY] = None
    if LAST_SELECTION_KEY not in st.session_state:
        st.session_state[LAST_SELECTION_KEY] = None

    # Get selected places from session state
    selected_places = st.session_state[SELECTED_PLACES_KEY]

    # Build selected places DataFrame
    df_selected = _build_selected_places_df(selected_places, df_places)

    # Build path lines if shortest path is calculated
    path_lines = None
    if st.session_state[SHORTEST_PATH_KEY] is not None:
        path_lines = _build_path_lines(st.session_state[SHORTEST_PATH_KEY])

    # Display map
    deck = build_map_deck(
        df_places,
        df_stations,
        df_railways,
        selected_places=df_selected,
        path_lines=path_lines,
    )

    st.subheader("Select Places on Map")
    st.info(
        f"Click on places to select them (max {MAX_PLACES} places). "
        "The optimal shortest path will be calculated using exhaustive search."
    )

    # Create 2:1 layout for map and selected places panel
    col_map, col_panel = st.columns([2, 1])

    with col_map:
        selection_state = st.pydeck_chart(
            deck,
            selection_mode="single-object",
            on_select="rerun",
            key="shortest_path_map",
        )

        # Handle selection
        _handle_place_selection(selection_state, df_places)

    with col_panel:
        # Display selected places and controls
        _render_selected_places_panel(session)

    # Display results in full width
    _render_shortest_path_results()

    # Show DataFrames
    st.subheader("DataFrames")
    with st.expander("DataFrame - Places", expanded=False):
        st.dataframe(df_places.head(100), height=360)


def _handle_place_selection(selection_state: Any, df_places: pd.DataFrame) -> None:
    """Handle place selection from map and update session state."""
    if not selection_state:
        return

    feature = extract_selected_feature(selection_state, _SELECTABLE_LAYER_ORDER)
    if not feature:
        return

    osm_id = feature.get("osm_id")

    # Check if this is the same selection we already processed
    last_selection = st.session_state.get(LAST_SELECTION_KEY)
    if last_selection == osm_id:
        return

    selected_places = st.session_state[SELECTED_PLACES_KEY]

    # Check if already selected
    if any(p.get("osm_id") == osm_id for p in selected_places):
        # Update last selection even if already in list
        st.session_state[LAST_SELECTION_KEY] = osm_id
        return

    # Check max limit
    if len(selected_places) >= MAX_PLACES:
        st.warning(f"Maximum {MAX_PLACES} places can be selected. Remove a place first.")
        st.session_state[LAST_SELECTION_KEY] = osm_id
        return

    # Add to selected places
    selected_places.append(feature)
    st.session_state[SELECTED_PLACES_KEY] = selected_places
    st.session_state[LAST_SELECTION_KEY] = osm_id

    # Clear shortest path result when selection changes
    st.session_state[SHORTEST_PATH_KEY] = None

    # Rerun to update the map and UI immediately
    st.rerun()


def _build_selected_places_df(
    selected_places: List[Dict[str, str]], df_places: pd.DataFrame
) -> pd.DataFrame:
    """Build DataFrame of selected places with proper column names."""
    if not selected_places:
        return pd.DataFrame(columns=["LONGITUDE", "LATITUDE", "NAME", "OSM_ID"])

    data = []
    for place in selected_places:
        try:
            data.append(
                {
                    "LONGITUDE": float(place["longitude"]),
                    "LATITUDE": float(place["latitude"]),
                    "NAME": place["name"],
                    "OSM_ID": place["osm_id"],
                    "TYPE": place["type"],
                }
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid place data: {e}")
            continue

    if not data:
        return pd.DataFrame(columns=["LONGITUDE", "LATITUDE", "NAME", "OSM_ID"])

    return pd.DataFrame(data)


def _render_selected_places_panel(session) -> None:
    """Display selected places list and control buttons."""
    st.subheader("Selected Places")

    selected_places = st.session_state[SELECTED_PLACES_KEY]

    if not selected_places:
        st.info("No places selected. Click on places on the map to select them.")
        return

    # Display selected places
    for idx, place in enumerate(selected_places):
        col1, col2, col3 = st.columns([0.5, 3, 1])
        with col1:
            st.write(f"{idx + 1}.")
        with col2:
            st.write(f"**{place['name']}** ({place['type']})")
        with col3:
            if st.button("Remove", key=f"remove_{idx}"):
                selected_places.pop(idx)
                st.session_state[SELECTED_PLACES_KEY] = selected_places
                st.session_state[SHORTEST_PATH_KEY] = None
                st.rerun()

    st.write("---")

    # Control buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Clear All", use_container_width=True):
            st.session_state[SELECTED_PLACES_KEY] = []
            st.session_state[SHORTEST_PATH_KEY] = None
            st.rerun()

    with col2:
        if st.button(
            "Calculate Shortest Path",
            disabled=len(selected_places) < 2,
            use_container_width=True,
        ):
            _calculate_shortest_path(session, selected_places)

    with col3:
        st.write(f"{len(selected_places)}/{MAX_PLACES} selected")


def _calculate_shortest_path(session, selected_places: List[Dict[str, str]]) -> None:
    """Calculate the shortest path using brute force optimal algorithm.

    Maximum 8 places are supported to ensure optimal solution is found
    within reasonable time (7! = 5,040 permutations).
    """
    if len(selected_places) < 2:
        st.warning("Please select at least 2 places.")
        return

    # Convert to list of coordinates
    coords = []
    for place in selected_places:
        try:
            coords.append(
                (
                    float(place["latitude"]),
                    float(place["longitude"]),
                    place["name"],
                )
            )
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid coordinate data: {e}")
            st.error("Invalid place data. Please try again.")
            return

    # Calculate distances using Snowflake
    distances = _calculate_distance_matrix(session, coords)

    # Always use brute force to guarantee optimal solution (max 8 places)
    best_path, total_distance = _solve_tsp_brute_force(distances)

    # Store result
    result = {
        "path": best_path,
        "total_distance": total_distance,
        "places": selected_places,
    }
    st.session_state[SHORTEST_PATH_KEY] = result

    # Rerun to update the map with the path visualization
    st.rerun()


def _calculate_distance_matrix(
    session, coords: List[Tuple[float, float, str]]
) -> List[List[float]]:
    """Calculate distance matrix using Snowflake ST_DISTANCE."""
    n = len(coords)
    distances = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            lat1, lon1, _ = coords[i]
            lat2, lon2, _ = coords[j]

            sql = f"""
            SELECT ST_DISTANCE(
                ST_POINT({lon1}, {lat1}),
                ST_POINT({lon2}, {lat2})
            ) / 1000 AS distance_km
            """

            try:
                result = session.sql(sql).collect()
                dist = float(result[0]["DISTANCE_KM"])
                distances[i][j] = dist
                distances[j][i] = dist
            except Exception as e:
                logger.error(f"Error calculating distance: {e}")
                # Use fallback Haversine formula
                dist = _haversine_distance(lat1, lon1, lat2, lon2)
                distances[i][j] = dist
                distances[j][i] = dist

    return distances


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance as fallback (in km)."""
    from math import asin, cos, radians, sin, sqrt
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_KM * c


def _solve_tsp_brute_force(
    distances: List[List[float]],
) -> Tuple[List[int], float]:
    """Solve shortest path problem using brute force exhaustive search.

    This guarantees finding the optimal solution by evaluating all possible
    paths through all cities. For n places, this evaluates n! permutations.

    Args:
        distances: n x n distance matrix

    Returns:
        Tuple of (optimal_path, total_distance)
    """
    n = len(distances)
    if n <= 1:
        return [0], 0.0
    if n == 2:
        return [0, 1], distances[0][1]

    all_cities = list(range(n))
    best_path = None
    best_distance = float("inf")

    # Try all permutations of all cities to find truly optimal path
    for perm in permutations(all_cities):
        path = list(perm)
        # Calculate total distance for this path (no return to start)
        dist = sum(distances[path[i]][path[i + 1]] for i in range(len(path) - 1))

        if dist < best_distance:
            best_distance = dist
            best_path = path

    return best_path, best_distance


def _build_path_lines(result: Dict[str, Any]) -> List[Dict[str, List[float]]]:
    """Build path lines data for visualization."""
    path = result["path"]
    places = result["places"]

    lines = []
    for i in range(len(path) - 1):
        start_idx = path[i]
        end_idx = path[i + 1]

        start_place = places[start_idx]
        end_place = places[end_idx]

        lines.append(
            {
                "start": [float(start_place["longitude"]), float(start_place["latitude"])],
                "end": [float(end_place["longitude"]), float(end_place["latitude"])],
            }
        )

    return lines


def _render_shortest_path_results() -> None:
    """Display the calculated shortest path results."""
    result = st.session_state.get(SHORTEST_PATH_KEY)
    if result is None:
        return

    st.subheader("Shortest Path Result")

    total_distance = result["total_distance"]
    path = result["path"]
    places = result["places"]

    st.metric("Total Distance", f"{total_distance:.2f} km")

    st.write("**Path Order:**")
    for i, idx in enumerate(path):
        place = places[idx]
        st.write(f"{i + 1}. {place['name']} ({place['type']})")


if __name__ == "__main__":
    session = create_session()
    st.session_state.session = session

    build_main_common_components("Shortest Path Exploration")
    build_sidebar_common_components()

    build_shortest_path_page()
