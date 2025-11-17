"""H3 Index demo settings and constants.

This module contains all configuration values specific to the H3 Index
demonstration features, including resolution settings, analysis types,
and color schemes.
"""

# H3 resolution settings
DEFAULT_H3_RESOLUTION = 5
MIN_H3_RESOLUTION = 3
MAX_H3_RESOLUTION = 8

# H3 analysis types
H3_ANALYSIS_TYPES = {
    "Grid Visualization": "grid",
    "City Density Heatmap": "density",
    "Station Coverage": "coverage",
}

DEFAULT_H3_ANALYSIS_TYPE = "Grid Visualization"

# H3 coverage settings
DEFAULT_COVERAGE_RADIUS_KM = 1.0
MIN_COVERAGE_RADIUS_KM = 0.5
MAX_COVERAGE_RADIUS_KM = 5.0

# H3 density threshold settings (as percentages of max density)
# These define the boundaries between low/medium/high density categories
DEFAULT_DENSITY_LOW_THRESHOLD = 20  # 0-20% = Low density
DEFAULT_DENSITY_HIGH_THRESHOLD = 50  # 50-100% = High density, 20-50% = Medium density
MIN_DENSITY_THRESHOLD = 0
MAX_DENSITY_THRESHOLD = 100

# H3 density display settings
DEFAULT_SHOW_CITY_ICONS = False  # Show city pin icons on density heatmap by default

# H3 color schemes
H3_GRID_COLOR = [100, 149, 237, 80]  # Cornflower blue with transparency

H3_DENSITY_COLORS = {
    "low": [76, 175, 80, 120],      # Green
    "medium": [255, 235, 59, 140],  # Yellow
    "high": [244, 67, 54, 160],     # Red
}

H3_COVERAGE_COVERED = [33, 150, 243, 140]  # Blue - covered areas
H3_COVERAGE_UNCOVERED = [158, 158, 158, 60]  # Gray - uncovered areas
