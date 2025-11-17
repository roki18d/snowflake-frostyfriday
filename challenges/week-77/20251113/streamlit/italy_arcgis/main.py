"""Italy ArcGIS Application - Home Page.

This page displays an overview map of Italy with places, stations, and railways,
along with statistics about the displayed data.
"""

import streamlit as st

from modules.map import (
    build_map_deck,
    load_places,
    load_railways,
    load_stations,
)
from modules.utils import (
    build_main_common_components,
    build_sidebar_common_components,
    create_session,
    get_logger,
)

logger = get_logger(__name__)

APPLICATION_NAME = "🇮🇹 Italy ArcGIS"


def build_home_page() -> None:
    """Build the home page with map display and statistics."""
    st.title(APPLICATION_NAME)
    st.write("Welcome to the Italy ArcGIS application. Explore places, stations, and railway networks across Italy.")

    session = st.session_state.session

    # Load data
    with st.spinner("Loading data..."):
        df_places = load_places(session)
        df_stations = load_stations(session)
        df_railways = load_railways(session)

    # Display statistics
    _render_statistics(df_places, df_stations, df_railways)

    # Display map
    st.subheader("Map Overview")
    deck = build_map_deck(df_places, df_stations, df_railways)
    st.pydeck_chart(deck, key="home_map")

    # Display data summaries
    _render_data_summaries(df_places, df_stations, df_railways)


def _render_statistics(df_places, df_stations, df_railways) -> None:
    """Render statistics cards for the loaded data."""
    st.subheader("Data Statistics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="📍 Places",
            value=f"{len(df_places):,}",
            help="Total number of cities, airports, and other places"
        )
        if not df_places.empty:
            place_types = df_places["TYPE"].value_counts()
            st.write("**Top Types:**")
            for place_type, count in place_types.head(3).items():
                st.write(f"- {place_type}: {count}")

    with col2:
        st.metric(
            label="🚉 Stations",
            value=f"{len(df_stations):,}",
            help="Total number of railway stations"
        )
        if not df_stations.empty:
            st.write("**Coverage:**")
            st.write(f"- Total: {len(df_stations)} stations")

    with col3:
        st.metric(
            label="🚄 Railway Lines",
            value=f"{len(df_railways):,}",
            help="Total number of railway lines"
        )
        if not df_railways.empty:
            railway_types = df_railways["TYPE"].value_counts()
            st.write("**Top Types:**")
            for railway_type, count in railway_types.head(3).items():
                st.write(f"- {railway_type}: {count}")


def _render_data_summaries(df_places, df_stations, df_railways) -> None:
    """Render expandable data summaries."""
    st.subheader("Data Summaries")

    with st.expander("Places Distribution by Type", expanded=False):
        if not df_places.empty:
            type_counts = df_places["TYPE"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            st.dataframe(type_counts, use_container_width=True, hide_index=True)
        else:
            st.info("No places data available.")

    with st.expander("Railway Lines by Type", expanded=False):
        if not df_railways.empty:
            railway_counts = df_railways["TYPE"].value_counts().reset_index()
            railway_counts.columns = ["Type", "Count"]
            st.dataframe(railway_counts, use_container_width=True, hide_index=True)
        else:
            st.info("No railway data available.")

    with st.expander("Geographic Coverage", expanded=False):
        st.write("**Data Coverage:**")
        col1, col2 = st.columns(2)

        with col1:
            if not df_places.empty:
                st.write("**Places:**")
                st.write(f"- Latitude range: {df_places['LATITUDE'].min():.2f} to {df_places['LATITUDE'].max():.2f}")
                st.write(f"- Longitude range: {df_places['LONGITUDE'].min():.2f} to {df_places['LONGITUDE'].max():.2f}")

        with col2:
            if not df_stations.empty:
                st.write("**Stations:**")
                st.write(f"- Latitude range: {df_stations['LATITUDE'].min():.2f} to {df_stations['LATITUDE'].max():.2f}")
                st.write(f"- Longitude range: {df_stations['LONGITUDE'].min():.2f} to {df_stations['LONGITUDE'].max():.2f}")


if __name__ == "__main__":
    session = create_session()
    st.session_state.session = session

    build_main_common_components("Home", show_title=False)
    build_sidebar_common_components()

    build_home_page()
