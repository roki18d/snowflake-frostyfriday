"""Application settings and constants for Italy ArcGIS.

This module centralizes all configuration values, constants, and
settings used across the application.
"""

# Application metadata
APPLICATION_NAME = "🇮🇹 Italy ArcGIS"
APPLICATION_VERSION = "1.0.0"

# Map display settings
DEFAULT_MAP_LATITUDE = 42.5
DEFAULT_MAP_LONGITUDE = 12.5
DEFAULT_MAP_ZOOM = 4.5

# Tooltip background colors
PLACES_TOOLTIP_BG = "rgba(255, 159, 54, 0.8)"
STATIONS_TOOLTIP_BG = "rgba(41, 181, 232, 0.8)"
RAILWAYS_TOOLTIP_BG = "rgba(212, 91, 144, 0.8)"

# Icon URLs
PLACES_ICON_URL = "https://cdn-icons-png.flaticon.com/512/149/149059.png"
STATIONS_ICON_URL = "https://cdn-icons-png.flaticon.com/256/149/149060.png"

# Path visualization colors (RGB)
PATH_COLOR_RGB = (41, 181, 232)  # #29B5E8
SELECTED_PLACE_COLOR_RGB = (41, 181, 232)  # #29B5E8

# Snowflake table names
TABLE_PLACES = "ITALY_ARCGIS_PLACES"
TABLE_POINTS = "ITALY_ARCGIS_POINTS"
TABLE_RAILWAYS = "ITALY_ARCGIS_RAILWAYS"

# Search settings
DEFAULT_NEAREST_STATIONS = 5
MAX_SELECTABLE_PLACES = 8  # Maximum 8 places for brute-force optimal path calculation

# Earth radius for distance calculations
EARTH_RADIUS_KM = 6371.0

# AI/ML settings
# Snowflake Cortex AI model for tourism guide generation
DEFAULT_CORTEX_LLM_MODEL = "claude-3-5-sonnet"

# Available Cortex AI models with display names
AVAILABLE_AI_MODELS = {
    "Claude 3.5 Sonnet": "claude-3-5-sonnet",
    "Claude 3 Opus": "claude-3-opus",
    "Claude 3 Haiku": "claude-3-haiku",
    "Mistral Large": "mistral-large",
    "Mistral 7B": "mistral-7b",
    "Llama 2 70B Chat": "llama2-70b-chat",
    "Snowflake Arctic": "snowflake-arctic",
}

# Legacy support - will be deprecated
CORTEX_LLM_MODEL = DEFAULT_CORTEX_LLM_MODEL

# Tourism guide language settings
DEFAULT_TOURISM_GUIDE_LANGUAGE = "🇯🇵 日本語"  # Default language for tourism guides
AVAILABLE_LANGUAGES = {
    "🇯🇵 日本語": "Japanese",
    "🇺🇸 English": "English",
    "🇮🇹 Italiano": "Italian",
}

# Language-specific length constraints for tourism guides
# Japanese uses character count, others use word count
LANGUAGE_LENGTH_CONSTRAINTS = {
    "Japanese": {
        "type": "characters",
        "limit": 2000,
        "prompt_text": "Limit the response to approximately 2000 characters (文字数制限: 約1500文字)",
    },
    "English": {
        "type": "words",
        "limit": 500,
        "prompt_text": "Limit the response to approximately 500 words",
    },
    "Italian": {
        "type": "words",
        "limit": 500,
        "prompt_text": "Limit the response to approximately 500 words",
    },
}
