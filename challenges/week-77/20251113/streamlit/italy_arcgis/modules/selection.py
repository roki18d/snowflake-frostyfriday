"""Common selection handling utilities for pydeck map interactions.

This module provides reusable functions for handling feature selection
from pydeck maps across different pages.
"""

from typing import Any, Dict, Optional


def extract_selected_feature(
    selection_state: Any,
    layer_order: tuple = ("places_icon_layer",)
) -> Optional[Dict[str, str]]:
    """Extract selected feature from pydeck selection state.

    Args:
        selection_state: Selection state from pydeck chart
        layer_order: Tuple of layer IDs to check in order of priority

    Returns:
        Dictionary with normalized feature data or None
    """
    if not selection_state:
        return None

    selection = None
    if isinstance(selection_state, dict):
        selection = selection_state.get("selection", selection_state)
    else:
        selection = getattr(selection_state, "selection", None)

    if not selection:
        return None

    objects_by_layer = selection.get("objects")
    if not isinstance(objects_by_layer, dict):
        return None

    for layer_id in layer_order:
        layer_objects = objects_by_layer.get(layer_id)
        if not layer_objects:
            continue
        first_entry = layer_objects[0]
        raw_object = first_entry.get("object", first_entry)
        normalized = normalize_feature(raw_object)
        if normalized:
            return normalized

    return None


def normalize_feature(raw_object: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Convert pydeck raw data to standardized format.

    Args:
        raw_object: Raw feature object from pydeck

    Returns:
        Dictionary with normalized keys or None
    """
    if not raw_object:
        return None

    return {
        "osm_id": to_string(get_field(raw_object, "OSM_ID", "osm_id")),
        "name": to_string(get_field(raw_object, "NAME", "name")),
        "type": to_string(get_field(raw_object, "TYPE", "type")),
        "longitude": to_string(get_field(raw_object, "LONGITUDE", "longitude", "lon")),
        "latitude": to_string(get_field(raw_object, "LATITUDE", "latitude", "lat")),
    }


def get_field(data: Dict[str, Any], *keys: str) -> Any:
    """Return the first value found from multiple candidate keys.

    Args:
        data: Dictionary to search
        *keys: Keys to try in order

    Returns:
        Value of first matching key or None
    """
    for key in keys:
        if key in data:
            return data[key]
    return None


def to_string(value: Any) -> str:
    """Convert value to empty string or string representation.

    Args:
        value: Value to convert

    Returns:
        String representation or empty string
    """
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
