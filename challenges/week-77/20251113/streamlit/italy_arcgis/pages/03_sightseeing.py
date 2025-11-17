"""Sightseeing Guide Page.

This page allows users to select a place (by OSM_ID or name) and
generates a tourism guide using Snowflake's COMPLETE function with AI.
"""

from typing import Any, Dict

import pandas as pd
import streamlit as st

from modules.map import build_map_deck, load_places, load_railways, load_stations
from modules.selection import extract_selected_feature
from modules.settings import (
    AVAILABLE_AI_MODELS,
    AVAILABLE_LANGUAGES,
    DEFAULT_CORTEX_LLM_MODEL,
    DEFAULT_TOURISM_GUIDE_LANGUAGE,
    LANGUAGE_LENGTH_CONSTRAINTS,
    TABLE_PLACES,
)
from modules.utils import (
    build_main_common_components,
    build_sidebar_common_components,
    create_session,
    get_logger,
)

logger = get_logger(__name__)

# Session state keys
SELECTED_PLACE_KEY = "sightseeing_selected_place"
TOURISM_GUIDE_KEY = "sightseeing_tourism_guide"
SEARCH_RESULTS_KEY = "sightseeing_search_results"
LANGUAGE_KEY = "sightseeing_guide_language"
AI_MODEL_KEY = "sightseeing_ai_model"

# Form field keys
FORM_FIELD_KEYS = {
    "name": "sightseeing_place_name",
    "osm_id": "sightseeing_place_osm_id",
    "type": "sightseeing_place_type",
    "longitude": "sightseeing_place_longitude",
    "latitude": "sightseeing_place_latitude",
}

_SELECTABLE_LAYER_ORDER = ("places_icon_layer",)


def build_sightseeing_page() -> None:
    """Build the sightseeing guide page with map and place selection."""
    session = st.session_state.session

    # Load data
    with st.spinner("Loading data..."):
        df_places = load_places(session)
        df_stations = load_stations(session)
        df_railways = load_railways(session)

    # Initialize session state
    _ensure_form_state()

    # Display map
    st.subheader("Select a Place")
    st.info("Click on a place on the map or search by name/OSM_ID below")

    deck = build_map_deck(df_places, df_stations, df_railways)
    selection_state = st.pydeck_chart(
        deck,
        selection_mode="single-object",
        on_select="rerun",
        key="sightseeing_map",
    )

    # Handle map selection
    _sync_selection_to_form(selection_state)

    # Display place selection form
    _render_place_selection_form(session, df_places)

    # Display tourism guide if available
    _render_tourism_guide()


def _ensure_form_state() -> None:
    """Ensure initial values for session state used in forms."""
    for key in FORM_FIELD_KEYS.values():
        st.session_state.setdefault(key, "")
    st.session_state.setdefault(SELECTED_PLACE_KEY, None)
    st.session_state.setdefault(TOURISM_GUIDE_KEY, None)
    st.session_state.setdefault(SEARCH_RESULTS_KEY, None)

    # Initialize language with migration support for old keys
    if LANGUAGE_KEY not in st.session_state:
        st.session_state[LANGUAGE_KEY] = DEFAULT_TOURISM_GUIDE_LANGUAGE
    elif st.session_state[LANGUAGE_KEY] not in AVAILABLE_LANGUAGES:
        # Migrate old language keys to new ones with flags
        language_mapping = {
            "日本語": "🇯🇵 日本語",
            "English": "🇺🇸 English",
            "Italiano": "🇮🇹 Italiano",
        }
        old_value = st.session_state[LANGUAGE_KEY]
        st.session_state[LANGUAGE_KEY] = language_mapping.get(old_value, DEFAULT_TOURISM_GUIDE_LANGUAGE)

    # Initialize AI model selection
    if AI_MODEL_KEY not in st.session_state:
        # Find the default model's display name
        default_display_name = None
        for display_name, model_id in AVAILABLE_AI_MODELS.items():
            if model_id == DEFAULT_CORTEX_LLM_MODEL:
                default_display_name = display_name
                break
        st.session_state[AI_MODEL_KEY] = default_display_name or "Claude 3.5 Sonnet"


def _sync_selection_to_form(selection_state: Any) -> None:
    """Sync selected place from map to session state and form fields."""
    feature = extract_selected_feature(selection_state, _SELECTABLE_LAYER_ORDER)
    if not feature:
        return

    st.session_state[SELECTED_PLACE_KEY] = feature
    for field, key in FORM_FIELD_KEYS.items():
        st.session_state[key] = feature.get(field, "")


def _render_place_selection_form(session, df_places: pd.DataFrame) -> None:
    """Render place selection form with search options."""
    st.subheader("Place Selection")

    # Search method selection
    search_method = st.radio(
        "Search Method",
        options=["map", "name", "osm_id"],
        format_func=lambda x: {
            "map": "Select from Map",
            "name": "Search by Name",
            "osm_id": "Search by OSM ID",
        }[x],
        index=0,
        horizontal=True,
    )

    # Search input based on method
    if search_method == "name":
        with st.form("search_by_name_form"):
            search_name = st.text_input(
                "Place Name",
                placeholder="Enter place name (e.g., Rome, Venice)",
                help="Search for a place by name",
            )
            search_submitted = st.form_submit_button("Search", use_container_width=True)

        if search_submitted and search_name:
            _search_place_by_name(session, search_name)

        # Display search results if available
        _render_search_results()

    elif search_method == "osm_id":
        with st.form("search_by_osm_id_form"):
            search_osm_id = st.text_input(
                "OSM ID",
                placeholder="Enter OSM ID (e.g., 12345)",
                help="Search for a place by OpenStreetMap ID",
            )
            search_submitted = st.form_submit_button("Search", use_container_width=True)

            if search_submitted and search_osm_id:
                _search_place_by_osm_id(session, search_osm_id)

    # Display selected place info
    st.write("---")
    st.write("**Selected Place:**")

    col1, col2 = st.columns(2)
    with col1:
        name = st.session_state.get(FORM_FIELD_KEYS["name"], "")
        st.text_input("Name", value=name, disabled=True, key="display_name")
    with col2:
        place_type = st.session_state.get(FORM_FIELD_KEYS["type"], "")
        st.text_input("Type", value=place_type, disabled=True, key="display_type")

    col1, col2 = st.columns(2)
    with col1:
        osm_id = st.session_state.get(FORM_FIELD_KEYS["osm_id"], "")
        st.text_input("OSM ID", value=osm_id, disabled=True, key="display_osm_id")
    with col2:
        longitude = st.session_state.get(FORM_FIELD_KEYS["longitude"], "")
        latitude = st.session_state.get(FORM_FIELD_KEYS["latitude"], "")
        coords = f"{latitude}, {longitude}" if latitude and longitude else ""
        st.text_input("Coordinates", value=coords, disabled=True, key="display_coords")

    # Generate tourism guide button
    st.write("---")
    selected_place = st.session_state.get(SELECTED_PLACE_KEY)
    if selected_place:
        # Language and Model selection
        col1, col2 = st.columns(2)
        with col1:
            # Get current language from session state, with fallback to default
            current_language = st.session_state.get(LANGUAGE_KEY, DEFAULT_TOURISM_GUIDE_LANGUAGE)

            # Handle migration from old language keys (without flags) to new ones (with flags)
            if current_language not in AVAILABLE_LANGUAGES:
                # Try to find matching language without flag
                language_mapping = {
                    "日本語": "🇯🇵 日本語",
                    "English": "🇺🇸 English",
                    "Italiano": "🇮🇹 Italiano",
                }
                current_language = language_mapping.get(current_language, DEFAULT_TOURISM_GUIDE_LANGUAGE)

            # Calculate the index for the selectbox
            try:
                default_index = list(AVAILABLE_LANGUAGES.keys()).index(current_language)
            except ValueError:
                default_index = 0  # Fallback to first option if not found

            language = st.selectbox(
                "Guide Language / ガイド言語",
                options=list(AVAILABLE_LANGUAGES.keys()),
                index=default_index,
                key=LANGUAGE_KEY,
            )

        with col2:
            # AI Model selection
            current_model_display = st.session_state.get(AI_MODEL_KEY, "Claude 3.5 Sonnet")

            # Calculate the index for the model selectbox
            try:
                model_index = list(AVAILABLE_AI_MODELS.keys()).index(current_model_display)
            except ValueError:
                model_index = 0  # Fallback to first option if not found

            ai_model_display = st.selectbox(
                "AI Model",
                options=list(AVAILABLE_AI_MODELS.keys()),
                index=model_index,
                key=AI_MODEL_KEY,
            )

        if st.button("🗺️ Generate Tourism Guide", use_container_width=True, type="primary"):
            # Get the actual model ID from the display name
            ai_model_id = AVAILABLE_AI_MODELS.get(ai_model_display, DEFAULT_CORTEX_LLM_MODEL)
            _generate_tourism_guide(session, selected_place, language, ai_model_id)
    else:
        st.info("Please select a place to generate a tourism guide")


def _render_search_results() -> None:
    """Display search results for user to select from."""
    results = st.session_state.get(SEARCH_RESULTS_KEY)

    if results is None or len(results) == 0:
        return

    if len(results) == 1:
        # Single result was auto-selected, no need to display
        return

    st.info(f"Found {len(results)} places. Please select one:")

    # Display header
    col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
    with col1:
        st.write("**Name**")
    with col2:
        st.write("**Type**")
    with col3:
        st.write("**OSM ID**")
    with col4:
        st.write("")

    st.markdown("---")

    # Display search results for user to select
    for idx, row in results.iterrows():
        col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
        with col1:
            st.write(f"{row['NAME']}")
        with col2:
            st.write(f"_{row['TYPE']}_")
        with col3:
            st.write(f"`{row['OSM_ID']}`")
        with col4:
            if st.button("Select", key=f"select_result_{idx}"):
                place = {
                    "osm_id": str(row["OSM_ID"]),
                    "name": str(row["NAME"]),
                    "type": str(row["TYPE"]),
                    "longitude": f"{float(row['LONGITUDE']):.6f}",
                    "latitude": f"{float(row['LATITUDE']):.6f}",
                }
                st.session_state[SELECTED_PLACE_KEY] = place
                for field, key in FORM_FIELD_KEYS.items():
                    st.session_state[key] = place.get(field, "")
                st.session_state[SEARCH_RESULTS_KEY] = None
                st.rerun()


def _search_place_by_name(session, name: str) -> None:
    """Search for a place by name and update session state."""
    try:
        # Escape single quotes in the name for SQL safety
        safe_name = name.replace("'", "''")

        sql = f"""
        SELECT
            osm_id,
            name,
            type,
            ST_X(ST_CENTROID(geography)) AS longitude,
            ST_Y(ST_CENTROID(geography)) AS latitude,
            CASE
                WHEN LOWER(name) = LOWER('{safe_name}') THEN 1
                WHEN LOWER(name) LIKE LOWER('{safe_name}%') THEN 2
                WHEN LOWER(name) LIKE LOWER('%{safe_name}%') THEN 3
                ELSE 4
            END AS match_priority
        FROM {TABLE_PLACES}
        WHERE LOWER(name) LIKE LOWER('%{safe_name}%')
        ORDER BY match_priority, name
        LIMIT 10
        """

        result = session.sql(sql).to_pandas()

        if result.empty:
            st.session_state[SEARCH_RESULTS_KEY] = None
            st.warning(f"No place found with name containing '{name}'")
            return

        # Store search results in session state
        result.columns = [col.upper() for col in result.columns]
        st.session_state[SEARCH_RESULTS_KEY] = result

        # If single result, auto-select
        if len(result) == 1:
            place = {
                "osm_id": str(result["OSM_ID"].iloc[0]),
                "name": str(result["NAME"].iloc[0]),
                "type": str(result["TYPE"].iloc[0]),
                "longitude": f"{float(result['LONGITUDE'].iloc[0]):.6f}",
                "latitude": f"{float(result['LATITUDE'].iloc[0]):.6f}",
            }

            st.session_state[SELECTED_PLACE_KEY] = place
            for field, key in FORM_FIELD_KEYS.items():
                st.session_state[key] = place.get(field, "")

            st.success(f"Found: {place['name']} ({place['type']})")
            st.rerun()

    except Exception as e:
        logger.error(f"Error searching place by name: {e}")
        st.error(f"Error searching for place: {e}")


def _search_place_by_osm_id(session, osm_id: str) -> None:
    """Search for a place by OSM ID and update session state."""
    try:
        sql = f"""
        SELECT
            osm_id,
            name,
            type,
            ST_X(ST_CENTROID(geography)) AS longitude,
            ST_Y(ST_CENTROID(geography)) AS latitude
        FROM {TABLE_PLACES}
        WHERE osm_id = '{osm_id}'
        LIMIT 1
        """

        result = session.sql(sql).to_pandas()

        if result.empty:
            st.warning(f"No place found with OSM ID '{osm_id}'")
            return

        # Update session state with found place
        result.columns = [col.upper() for col in result.columns]
        place = {
            "osm_id": str(result["OSM_ID"].iloc[0]),
            "name": str(result["NAME"].iloc[0]),
            "type": str(result["TYPE"].iloc[0]),
            "longitude": f"{float(result['LONGITUDE'].iloc[0]):.6f}",
            "latitude": f"{float(result['LATITUDE'].iloc[0]):.6f}",
        }

        st.session_state[SELECTED_PLACE_KEY] = place
        for field, key in FORM_FIELD_KEYS.items():
            st.session_state[key] = place.get(field, "")

        st.success(f"Found: {place['name']} ({place['type']})")
        st.rerun()

    except Exception as e:
        logger.error(f"Error searching place by OSM ID: {e}")
        st.error(f"Error searching for place: {e}")


def _generate_tourism_guide(session, place: Dict[str, str], language: str, model_id: str) -> None:
    """Generate tourism guide using Snowflake COMPLETE function.

    Args:
        session: Snowflake session
        place: Dictionary containing place information
        language: Target language for the guide (e.g., "🇯🇵 日本語", "🇺🇸 English")
        model_id: Snowflake Cortex model ID (e.g., "claude-3-5-sonnet")
    """
    place_name = place.get("name", "Unknown")
    place_type = place.get("type", "place")

    # Get the English name of the language for the prompt
    language_name = AVAILABLE_LANGUAGES.get(language, "English")

    # Get length constraint from settings based on language
    length_config = LANGUAGE_LENGTH_CONSTRAINTS.get(
        language_name,
        {
            "type": "words",
            "limit": 500,
            "prompt_text": "Limit the response to approximately 500 words",
        }
    )
    length_constraint = length_config["prompt_text"]

    with st.spinner(f"Generating tourism guide for {place_name}..."):
        try:
            # Create a prompt for the AI with language specification
            prompt = f"""Write a comprehensive tourism guide for {place_name}, a {place_type} in Italy.

IMPORTANT:
- Write the entire guide in {language_name}
- Format the output in Markdown for better readability
- Use proper Markdown formatting: headers (##, ###), bold (**text**), lists (- item), etc.

Include the following sections with Markdown headers:

### Overview
Brief introduction and historical significance

### Main Attractions
Top sights and landmarks to visit (use bullet points with - )

### Cultural Highlights
Museums, galleries, and cultural venues (use bullet points with - )

### Local Cuisine
Famous dishes and recommended restaurants (use bullet points with - )

### Best Time to Visit
Seasonal recommendations

### Travel Tips
Practical advice for tourists (use bullet points with - )

Keep the tone informative and engaging. {length_constraint}
Remember: The entire response must be written in {language_name} and properly formatted in Markdown."""

            # Use Snowflake COMPLETE function
            # Note: COMPLETE is typically available in Snowflake Cortex
            # Model is selected by user via UI
            sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{model_id}',
                '{prompt.replace("'", "''")}'
            ) AS tourism_guide
            """

            result = session.sql(sql).to_pandas()

            if not result.empty and result["TOURISM_GUIDE"].iloc[0]:
                guide = result["TOURISM_GUIDE"].iloc[0]
                # Get model display name for showing to user
                model_display_name = None
                for display_name, model in AVAILABLE_AI_MODELS.items():
                    if model == model_id:
                        model_display_name = display_name
                        break

                st.session_state[TOURISM_GUIDE_KEY] = {
                    "place": place,
                    "guide": guide,
                    "language": language,
                    "model": model_id,
                    "model_display": model_display_name or model_id,
                }
                st.success(f"Tourism guide generated for {place_name}!")
                st.rerun()
            else:
                st.error("Failed to generate tourism guide. Please try again.")

        except Exception as e:
            logger.error(f"Error generating tourism guide: {e}")
            st.error(f"Error generating tourism guide: {e}")

            # Fallback: provide a simple message
            if "COMPLETE" in str(e).upper() or "CORTEX" in str(e).upper():
                st.warning(
                    "Snowflake Cortex AI functions may not be available in your account. "
                    "Please check that CORTEX is enabled."
                )


def _render_tourism_guide() -> None:
    """Display the generated tourism guide."""
    guide_data = st.session_state.get(TOURISM_GUIDE_KEY)

    if not guide_data:
        return

    place = guide_data.get("place", {})
    guide = guide_data.get("guide", "")
    language = guide_data.get("language", DEFAULT_TOURISM_GUIDE_LANGUAGE)
    model_id = guide_data.get("model", DEFAULT_CORTEX_LLM_MODEL)
    model_display = guide_data.get("model_display", model_id)

    st.write("---")
    st.subheader(f"🗺️ Tourism Guide: {place.get('name', 'Unknown')}")

    # Display place info in an info box
    st.info(
        f"**Location:** {place.get('name')} ({place.get('type')})\n\n"
        f"**OSM ID:** {place.get('osm_id')}\n\n"
        f"**Coordinates:** {place.get('latitude')}, {place.get('longitude')}"
    )

    # Display the guide content with Markdown formatting
    st.caption(f"Language: {language} | Model: {model_display}")

    # Render the guide with proper Markdown formatting
    # The guide is already in Markdown format from the AI
    st.markdown(guide, unsafe_allow_html=False)

    # Add action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Regenerate Guide", use_container_width=True):
            session = st.session_state.session
            current_language = st.session_state.get(LANGUAGE_KEY, DEFAULT_TOURISM_GUIDE_LANGUAGE)
            current_model_display = st.session_state.get(AI_MODEL_KEY, "Claude 3.5 Sonnet")
            current_model_id = AVAILABLE_AI_MODELS.get(current_model_display, DEFAULT_CORTEX_LLM_MODEL)
            _generate_tourism_guide(session, place, current_language, current_model_id)

    with col2:
        if st.button("🗑️ Clear Guide", use_container_width=True):
            st.session_state[TOURISM_GUIDE_KEY] = None
            st.rerun()


if __name__ == "__main__":
    session = create_session()
    st.session_state.session = session

    build_main_common_components("Sightseeing Guide")
    build_sidebar_common_components()

    build_sightseeing_page()
