# 🇮🇹 Italy ArcGIS Application

An interactive Streamlit application for exploring geographical data of Italy, including places, railway stations, and railway networks.

## Features

### 🏠 Home Page
- Interactive map overview of Italy
- Statistics dashboard showing:
  - Total number of places, stations, and railway lines
  - Distribution by type
  - Geographic coverage information
- Real-time data visualization using pydeck

### 🚉 Nearest Stations Search
- Search for nearest railway stations from any point on the map
- Click on places to select coordinates
- Distance calculation using:
  - **ST_DISTANCE**: Snowflake's geospatial function (geodetic distance)
  - **Haversine Formula**: Mathematical approximation
  - **Comparison**: Shows difference between the two methods
- Display top N nearest stations (default: 5)

### 🛤️ Shortest Path Exploration
- Select up to 10 places on the map
- Calculate optimal path using Traveling Salesman Problem (TSP) algorithms:
  - **Brute Force**: For ≤8 places (optimal solution)
  - **Nearest Neighbor**: For >8 places (heuristic)
- Distance matrix calculated using Snowflake ST_DISTANCE
- Visual path display on map with blue lines (#29B5E8)
- Total distance and visit order summary

### 🗺️ Sightseeing Guide
- Search places by:
  - **Map Selection**: Click on places directly on the map
  - **Name Search**: Search by place name (e.g., "Rome", "Venice")
  - **OSM ID**: Direct lookup by OpenStreetMap ID
- AI-powered tourism guide using Snowflake Cortex COMPLETE function
- **Multi-language support**: Generate guides in Japanese 🇯🇵 (default, ~1500 chars), English 🇺🇸 (~500 words), or Italian 🇮🇹 (~500 words)
- **Multi-model support**: Choose from 7 AI models including Claude 3.5 Sonnet (default), Claude 3 Opus, Mistral Large, and more
- **Markdown formatting**: Guides are generated with proper Markdown structure for better readability
- Comprehensive guide includes:
  - Historical overview and significance
  - Main attractions and landmarks
  - Cultural highlights and museums
  - Local cuisine recommendations
  - Best time to visit
  - Practical travel tips

## Project Structure

```
italy_arcgis/
├── main.py                    # Home page
├── pages/
│   ├── 01_nearest_stations.py # Nearest stations search
│   ├── 02_shortest_path.py    # Shortest path exploration
│   └── 03_sightseeing.py      # AI-powered tourism guide
├── modules/
│   ├── map.py                 # Map display utilities
│   ├── selection.py           # Feature selection handlers
│   ├── settings.py            # Configuration and constants
│   └── utils.py               # Common utilities
└── README.md                  # This file
```

## Data Sources

The application uses the following Snowflake tables:

- `ITALY_ARCGIS_PLACES`: Cities, airports, and other significant locations
- `ITALY_ARCGIS_POINTS`: Railway stations
- `ITALY_ARCGIS_RAILWAYS`: Railway lines and networks

## Technical Details

### Map Visualization
- **Library**: Pydeck (deck.gl for Python)
- **Layers**:
  - GeoJsonLayer for railway lines
  - IconLayer for places and stations
  - ScatterplotLayer for highlights and endpoints
  - LineLayer for path visualization

### Distance Calculations

#### ST_DISTANCE (Snowflake)
- Uses WGS84 ellipsoid model
- Geodetic distance calculation
- High accuracy
- Server-side computation

#### Haversine Formula
- Spherical Earth approximation
- Client-side calculation
- Fast computation
- Typical difference: <0.5% from ST_DISTANCE

### Algorithms

#### TSP Solver
- **Brute Force** O(n!): Optimal for small n (≤8)
- **Nearest Neighbor** O(n²): Fast heuristic for larger n

### AI-Powered Features

#### Snowflake Cortex COMPLETE
- **Function**: `SNOWFLAKE.CORTEX.COMPLETE(model, prompt)`
- **Model**: mistral-large (Large Language Model)
- **Use Case**: Generate comprehensive tourism guides
- **Features**:
  - Natural language generation
  - Contextual understanding
  - Structured content generation
  - Multi-section tourism guides
- **Requirements**: Snowflake Cortex must be enabled in your account

**⚠️ Setup Required**: Grant Cortex privileges to your Snowflake role:

```sql
-- Grant Cortex AI function execution privilege
GRANT EXECUTE ON FUNCTION SNOWFLAKE.CORTEX.COMPLETE(VARCHAR, VARCHAR) TO ROLE <YOUR_ROLE>;
```

**Model Configuration**: The default AI model can be changed in `modules/settings.py`:
```python
DEFAULT_CORTEX_LLM_MODEL = "claude-3-5-sonnet"  # Default model

AVAILABLE_AI_MODELS = {
    "Claude 3.5 Sonnet": "claude-3-5-sonnet",    # Default - Best balance
    "Claude 3 Opus": "claude-3-opus",            # Most capable
    "Claude 3 Haiku": "claude-3-haiku",          # Fastest
    "Mistral Large": "mistral-large",
    "Mistral 7B": "mistral-7b",
    "Llama 2 70B Chat": "llama2-70b-chat",
    "Snowflake Arctic": "snowflake-arctic",
}
```

Users can select different models via the UI dropdown. The model selection is saved per session.

**Language Configuration**: Default language and available options:
```python
DEFAULT_TOURISM_GUIDE_LANGUAGE = "🇯🇵 日本語"  # Default language
AVAILABLE_LANGUAGES = {
    "🇯🇵 日本語": "Japanese",
    "🇺🇸 English": "English",
    "🇮🇹 Italiano": "Italian",
}

# Language-specific length constraints
LANGUAGE_LENGTH_CONSTRAINTS = {
    "Japanese": {
        "type": "characters",
        "limit": 1500,
        "prompt_text": "Limit the response to approximately 1500 characters (文字数制限: 約1500文字)",
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
```

You can adjust the `limit` values for each language to control the length of generated tourism guides.

## Configuration

All configuration values are centralized in `modules/settings.py`:

```python
# Map settings
DEFAULT_MAP_LATITUDE = 42.5
DEFAULT_MAP_LONGITUDE = 12.5
DEFAULT_MAP_ZOOM = 4.5

# Search settings
DEFAULT_NEAREST_STATIONS = 5
MAX_SELECTABLE_PLACES = 10

# Colors
PATH_COLOR_RGB = (41, 181, 232)  # #29B5E8

# AI/ML settings
DEFAULT_CORTEX_LLM_MODEL = "claude-3-5-sonnet"  # Default AI model
DEFAULT_TOURISM_GUIDE_LANGUAGE = "🇯🇵 日本語"  # Default guide language
```

## Usage

1. **Start the application**:
   ```bash
   streamlit run main.py
   ```

2. **Navigate** using the sidebar menu

3. **Interact** with the map:
   - Click on places/stations to select
   - View information in data tables
   - Calculate distances and paths

## Development

### Adding New Pages

1. Create new file in `pages/` with numeric prefix (e.g., `03_new_feature.py`)
2. Add page link in `modules/utils.py` → `build_sidebar_common_components()`
3. Import common utilities from `modules/`

### Modifying Map Behavior

- Update `modules/map.py` for map display changes
- Update `modules/selection.py` for selection handling
- Update `modules/settings.py` for configuration changes

## Dependencies

- `streamlit`: Web application framework
- `pydeck`: Map visualization
- `pandas`: Data manipulation
- `snowflake-snowpark-python`: Snowflake connectivity
- `colorama`: Colored logging

## License

Internal project for Italy ArcGIS data exploration.
