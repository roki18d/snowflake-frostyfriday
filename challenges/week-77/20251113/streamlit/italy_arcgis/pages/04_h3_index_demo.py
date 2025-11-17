"""H3 Index Demo Page.

This page demonstrates Snowflake's H3 spatial indexing capabilities
through three interactive analysis types:
1. Grid Visualization - Understand hexagonal grid system
2. City Density Heatmap - Analyze city distribution patterns
3. Station Coverage - Calculate railway station coverage
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

from modules.h3_map import (
    build_h3_coverage_deck,
    build_h3_density_deck,
    build_h3_grid_deck,
    calculate_coverage_stats,
    calculate_density_stats,
    load_city_locations,
    load_h3_coverage_data,
    load_h3_density_data,
    load_h3_grid_data,
    load_station_locations,
)
from modules.h3_settings import (
    DEFAULT_COVERAGE_RADIUS_KM,
    DEFAULT_DENSITY_HIGH_THRESHOLD,
    DEFAULT_DENSITY_LOW_THRESHOLD,
    DEFAULT_H3_ANALYSIS_TYPE,
    DEFAULT_H3_RESOLUTION,
    DEFAULT_SHOW_CITY_ICONS,
    H3_ANALYSIS_TYPES,
    MAX_COVERAGE_RADIUS_KM,
    MAX_DENSITY_THRESHOLD,
    MAX_H3_RESOLUTION,
    MIN_COVERAGE_RADIUS_KM,
    MIN_DENSITY_THRESHOLD,
    MIN_H3_RESOLUTION,
)
from modules.utils import (
    build_main_common_components,
    build_sidebar_common_components,
    create_session,
    get_logger,
)

logger = get_logger(__name__)

# Session state keys
ANALYSIS_TYPE_KEY = "h3_analysis_type"
RESOLUTION_KEY = "h3_resolution"
COVERAGE_RADIUS_KEY = "h3_coverage_radius"
DENSITY_LOW_THRESHOLD_KEY = "h3_density_low_threshold"
DENSITY_HIGH_THRESHOLD_KEY = "h3_density_high_threshold"
SHOW_CITY_ICONS_KEY = "h3_show_city_icons"


def _ensure_session_state() -> None:
    """Initialize session state variables with defaults."""
    if ANALYSIS_TYPE_KEY not in st.session_state:
        st.session_state[ANALYSIS_TYPE_KEY] = DEFAULT_H3_ANALYSIS_TYPE

    if RESOLUTION_KEY not in st.session_state:
        st.session_state[RESOLUTION_KEY] = DEFAULT_H3_RESOLUTION

    if COVERAGE_RADIUS_KEY not in st.session_state:
        st.session_state[COVERAGE_RADIUS_KEY] = DEFAULT_COVERAGE_RADIUS_KM

    if DENSITY_LOW_THRESHOLD_KEY not in st.session_state:
        st.session_state[DENSITY_LOW_THRESHOLD_KEY] = DEFAULT_DENSITY_LOW_THRESHOLD

    if DENSITY_HIGH_THRESHOLD_KEY not in st.session_state:
        st.session_state[DENSITY_HIGH_THRESHOLD_KEY] = DEFAULT_DENSITY_HIGH_THRESHOLD

    if SHOW_CITY_ICONS_KEY not in st.session_state:
        st.session_state[SHOW_CITY_ICONS_KEY] = DEFAULT_SHOW_CITY_ICONS


def _render_header() -> None:
    """Render page header with title and description."""
    st.markdown(
        """
        **Snowflake H3 Spatial Indexing** を使ったイタリア地理データの分析デモです。
        六角形グリッドシステム（H3 Index）による密度分析・カバレッジ分析を実演します。
        """
    )
    st.divider()


def _render_demo_overview() -> None:
    """Render overview of each analysis stage."""
    st.subheader("📊 Demo Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📐 Stage 1")
        st.markdown("**Grid Visualization**")
        st.markdown(
            """
            H3 Index の基本概念を理解します。イタリア全土を六角形グリッドで覆い、
            解像度による六角形サイズの違いを視覚的に確認できます。

            **Key Points:**
            - 六角形グリッドシステムの仕組み
            - 解像度（3-8）とグリッドサイズの関係
            """
        )

    with col2:
        st.markdown("### 🔥 Stage 2")
        st.markdown("**City Density Heatmap**")
        st.markdown(
            """
            各六角形内の都市数を集計し、密度をヒートマップで可視化します。
            閾値を調整して、密度カテゴリーをカスタマイズできます。

            **Key Points:**
            - 都市分布の密度分析
            - カスタマイズ可能な閾値設定
            - 都市アイコンの表示切替
            """
        )

    with col3:
        st.markdown("### 🚉 Stage 3")
        st.markdown("**Station Coverage**")
        st.markdown(
            """
            **H3セルの中心点**が鉄道駅から指定半径内にある場合、
            そのセルを「カバー済」として可視化します。

            **Key Points:**
            - H3セル中心点ベースの判定
            - カバレッジ率の計算
            - 半径の調整（0.5-5.0km）
            """
        )

    st.divider()


def _render_controls() -> tuple[str, int, float, float, float, bool]:
    """Render control panel for analysis settings.

    Returns:
        Tuple of (analysis_type, resolution, coverage_radius, low_threshold, high_threshold, show_city_icons)
    """
    st.subheader("⚙️ Analysis Settings")

    # Analysis Type
    st.selectbox(
        "Analysis Type",
        options=list(H3_ANALYSIS_TYPES.keys()),
        help="Select the type of H3 analysis to perform",
        key=ANALYSIS_TYPE_KEY,
    )

    st.divider()

    # H3 Resolution
    st.number_input(
        "H3 Resolution",
        min_value=MIN_H3_RESOLUTION,
        max_value=MAX_H3_RESOLUTION,
        value=st.session_state[RESOLUTION_KEY],
        step=1,
        help="Higher resolution = smaller hexagons = more detail",
        key=RESOLUTION_KEY,
    )

    st.divider()

    # Get current values from session state
    analysis_type = st.session_state[ANALYSIS_TYPE_KEY]

    # Analysis-specific settings
    if H3_ANALYSIS_TYPES[analysis_type] == "coverage":
        # Coverage radius for Station Coverage
        st.slider(
            "Coverage Radius (km)",
            min_value=MIN_COVERAGE_RADIUS_KM,
            max_value=MAX_COVERAGE_RADIUS_KM,
            value=st.session_state[COVERAGE_RADIUS_KEY],
            step=0.5,
            help="Radius around each station considered as covered",
            key=COVERAGE_RADIUS_KEY,
        )

    elif H3_ANALYSIS_TYPES[analysis_type] == "density":
        # City icons checkbox for City Density Heatmap
        # Debug: Show state BEFORE checkbox
        st.caption(f"🔍 Before checkbox - Session state: {st.session_state.get(SHOW_CITY_ICONS_KEY, 'NOT SET')}, Default: {DEFAULT_SHOW_CITY_ICONS}")

        st.checkbox(
            "Show City Icons",
            help="Display city location markers on the map",
            key=SHOW_CITY_ICONS_KEY,
        )

        # Debug: Show the value immediately after checkbox
        current_value = st.session_state.get(SHOW_CITY_ICONS_KEY, DEFAULT_SHOW_CITY_ICONS)
        st.caption(f"⚙️ After checkbox - Current value: {current_value}")

        st.markdown("**Density Thresholds**")
        st.caption("Percentage of maximum city count")

        st.slider(
            "Low Threshold (%)",
            min_value=MIN_DENSITY_THRESHOLD,
            max_value=MAX_DENSITY_THRESHOLD,
            value=st.session_state[DENSITY_LOW_THRESHOLD_KEY],
            step=5,
            help="Cities below this percentage are colored green (low density)",
            key=DENSITY_LOW_THRESHOLD_KEY,
        )

        st.slider(
            "High Threshold (%)",
            min_value=MIN_DENSITY_THRESHOLD,
            max_value=MAX_DENSITY_THRESHOLD,
            value=st.session_state[DENSITY_HIGH_THRESHOLD_KEY],
            step=5,
            help="Cities above this percentage are colored red (high density)",
            key=DENSITY_HIGH_THRESHOLD_KEY,
        )

        # Get current threshold values for display
        low_threshold = st.session_state[DENSITY_LOW_THRESHOLD_KEY]
        high_threshold = st.session_state[DENSITY_HIGH_THRESHOLD_KEY]

        st.caption(f"🟢 Low: 0-{low_threshold}%")
        st.caption(f"🟡 Medium: {low_threshold}-{high_threshold}%")
        st.caption(f"🔴 High: {high_threshold}-100%")

    # Return all values from session state
    return (
        st.session_state[ANALYSIS_TYPE_KEY],
        st.session_state[RESOLUTION_KEY],
        st.session_state.get(COVERAGE_RADIUS_KEY, DEFAULT_COVERAGE_RADIUS_KM),
        st.session_state.get(DENSITY_LOW_THRESHOLD_KEY, DEFAULT_DENSITY_LOW_THRESHOLD),
        st.session_state.get(DENSITY_HIGH_THRESHOLD_KEY, DEFAULT_DENSITY_HIGH_THRESHOLD),
        st.session_state.get(SHOW_CITY_ICONS_KEY, DEFAULT_SHOW_CITY_ICONS),
    )


def _render_resolution_info(resolution: int) -> None:
    """Render information about H3 resolution.

    Args:
        resolution: Current H3 resolution value
    """
    # Resolution descriptions
    resolution_info = {
        3: "広域（州レベル）- 地域密度分析に適しています",
        4: "広域（州レベル）- 地域密度分析に適しています",
        5: "広域（州レベル）- 地域密度分析に適しています",
        6: "中域（市レベル）- 都市計画に適しています",
        7: "中域（市レベル）- 都市計画に適しています",
        8: "狭域（地区レベル）- 店舗カバレッジ分析に適しています",
    }

    info_text = resolution_info.get(
        resolution, "解像度が高いほど、詳細な分析が可能ですが計算量も増加します"
    )

    st.info(f"**Resolution {resolution}**: {info_text}")


def _render_grid_visualization(session, resolution: int) -> None:
    """Render H3 grid visualization.

    Args:
        session: Snowflake session object
        resolution: H3 resolution
    """
    st.subheader("📐 Stage 1: H3 Grid Visualization")
    st.markdown("イタリア全土を六角形グリッドで覆い、H3 Index の基本概念を理解します。")

    _render_resolution_info(resolution)

    with st.spinner("Loading H3 grid data..."):
        df_h3 = load_h3_grid_data(session, resolution)

    if df_h3.empty:
        st.warning("No H3 grid data available.")
        return

    # Display statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total H3 Cells", f"{len(df_h3):,}")
    with col2:
        st.metric("H3 Resolution", resolution)
    with col3:
        # Show sample H3 cell ID for debugging
        if not df_h3.empty and 'H3_CELL' in df_h3.columns:
            sample_cell = str(df_h3['H3_CELL'].iloc[0])
            st.metric("Sample Cell", f"{sample_cell[:8]}...")

    # Debug: Show data sample
    with st.expander("🔍 Debug: Data Sample"):
        st.write(f"DataFrame shape: {df_h3.shape}")
        st.write(f"Columns: {df_h3.columns.tolist()}")
        st.dataframe(df_h3.head(10))

    # Render map
    deck = build_h3_grid_deck(df_h3, resolution)
    st.pydeck_chart(deck, use_container_width=True)

    # Educational notes
    with st.expander("💡 H3 Index について"):
        st.markdown(
            """
            **H3 Index** は Uber が開発した六角形グリッドシステムです:
            - 地球全体を六角形で均等に分割
            - 解像度（0-15）により、グリッドサイズを調整可能
            - 六角形は正方形より隣接セルとの距離が均一で、地理分析に最適
            - Snowflake では H3 関数群により、高速な地理空間分析が可能
            """
        )


def _render_density_heatmap(
    session, resolution: int, low_threshold: float, high_threshold: float, show_city_icons: bool
) -> None:
    """Render H3 density heatmap.

    Args:
        session: Snowflake session object
        resolution: H3 resolution
        low_threshold: Low density threshold percentage
        high_threshold: High density threshold percentage
        show_city_icons: Whether to show city icon markers
    """
    st.subheader("🔥 Stage 2: City Density Heatmap")
    st.markdown(
        "各H3セル（六角形）内の**都市・町の数**をカウントし、密度として可視化します。"
    )
    st.info(
        "💡 **Densityの定義**: 各H3セル内に含まれる都市・町（city, town）の数を「密度」として扱います。"
        "密度の高さは、最大値に対する割合（%）で Low/Medium/High にカテゴリ分けされます。"
    )

    _render_resolution_info(resolution)

    with st.spinner("Loading city density data..."):
        df_density = load_h3_density_data(session, resolution)
        df_cities = load_city_locations(session)

    if df_density.empty:
        st.warning("No density data available.")
        return

    # Calculate and display statistics
    stats = calculate_density_stats(df_density)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total H3 Cells", f"{stats['total_cells']:,}")
    with col2:
        st.metric("Total Cities", f"{stats['total_cities']:,}")
    with col3:
        st.metric("Max Cities per Cell", f"{stats['max_cities_per_cell']}")
    with col4:
        st.metric("Avg Cities per Cell", f"{stats['avg_cities_per_cell']:.2f}")

    # Debug: Show current settings
    with st.expander("🔍 Debug: Current Settings"):
        st.write(f"Show City Icons (from parameter): {show_city_icons}")
        st.write(f"Show City Icons (from session state): {st.session_state.get(SHOW_CITY_ICONS_KEY, 'NOT SET')}")
        st.write(f"Low Threshold: {low_threshold}%")
        st.write(f"High Threshold: {high_threshold}%")
        st.write(f"Cities DataFrame shape: {df_cities.shape}")
        st.write(f"Density DataFrame shape: {df_density.shape}")
        st.write(f"Map key: density_map_{resolution}_{low_threshold}_{high_threshold}_{show_city_icons}")

    # Render map with custom thresholds and optional city icons
    deck = build_h3_density_deck(
        df_density, df_cities, resolution, low_threshold, high_threshold, show_city_icons
    )
    # Use a unique key based on settings to force re-render when settings change
    map_key = f"density_map_{resolution}_{low_threshold}_{high_threshold}_{show_city_icons}"
    st.pydeck_chart(deck, use_container_width=True, key=map_key)

    # Legend (dynamic based on thresholds)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"🟢 **Low Density** (0-{low_threshold}%)")
    with col2:
        st.markdown(f"🟡 **Medium Density** ({low_threshold}-{high_threshold}%)")
    with col3:
        st.markdown(f"🔴 **High Density** ({high_threshold}-100%)")

    # Educational notes
    with st.expander("💡 密度分析の活用例"):
        st.markdown(
            """
            **H3 Index を使った密度分析**:
            - 都市計画: 人口密集地域の特定
            - マーケティング: 店舗出店候補地の選定
            - 物流最適化: 配送拠点の最適配置
            - リスク分析: 災害時の影響範囲予測
            """
        )


def _render_coverage_analysis(session, resolution: int, radius_km: float) -> None:
    """Render H3 coverage analysis.

    Args:
        session: Snowflake session object
        resolution: H3 resolution
        radius_km: Coverage radius in kilometers
    """
    st.subheader("🚉 Stage 3: Station Coverage Analysis")
    st.markdown(
        f"**H3セルの中心点**が鉄道駅から {radius_km}km 圏内にある場合、そのセルを「カバー済」として可視化します。"
    )
    st.info(
        "💡 判定基準: H3セルの中心点と最寄り駅との距離で判定します。"
        "そのため、駅アイコンがセル内に表示されていても、セルの中心点が駅から遠い場合はカバーされていないと判定されます。"
    )

    _render_resolution_info(resolution)

    with st.spinner("Calculating station coverage..."):
        df_coverage = load_h3_coverage_data(session, resolution, radius_km)
        df_stations = load_station_locations(session)

    if df_coverage.empty:
        st.warning("No coverage data available.")
        return

    # Calculate and display statistics
    stats = calculate_coverage_stats(df_coverage)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total H3 Cells", f"{stats['total_cells']:,}")
    with col2:
        st.metric("Covered Cells", f"{stats['covered_cells']:,}")
    with col3:
        st.metric("Uncovered Cells", f"{stats['uncovered_cells']:,}")
    with col4:
        st.metric("Coverage Rate", f"{stats['coverage_rate']:.1f}%")

    # Render map
    deck = build_h3_coverage_deck(df_coverage, df_stations, resolution, radius_km)
    st.pydeck_chart(deck, use_container_width=True)

    # Legend
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"🔵 **Covered** (セルの中心点が駅から {radius_km}km 圏内)")
    with col2:
        st.markdown(f"⚪ **Uncovered** (セルの中心点が駅から {radius_km}km 圏外)")

    # Educational notes
    with st.expander("💡 カバレッジ分析の活用例"):
        st.markdown(
            """
            **H3 Index を使ったカバレッジ分析**:
            - インフラ計画: 公共交通機関のカバレッジ評価
            - 通信網: 基地局の配置最適化
            - 医療: 病院・診療所のアクセシビリティ評価
            - 小売: 店舗の商圏分析
            """
        )


def build_h3_index_demo_page() -> None:
    """Main application logic."""
    _ensure_session_state()
    _render_header()
    _render_demo_overview()

    # Get Snowflake session
    try:
        session = get_active_session()
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        logger.error(f"Snowflake connection error: {e}")
        return

    # Create two-column layout: 1/3 for settings, 2/3 for visualization
    settings_col, viz_col = st.columns([1, 2])

    # Left column: Analysis Settings
    with settings_col:
        analysis_type, resolution, coverage_radius, low_threshold, high_threshold, show_city_icons = _render_controls()
        analysis_code = H3_ANALYSIS_TYPES[analysis_type]

    # Right column: Visualization
    with viz_col:
        # Render selected analysis
        try:
            if analysis_code == "grid":
                _render_grid_visualization(session, resolution)
            elif analysis_code == "density":
                _render_density_heatmap(session, resolution, low_threshold, high_threshold, show_city_icons)
            elif analysis_code == "coverage":
                _render_coverage_analysis(session, resolution, coverage_radius)
            else:
                st.error(f"Unknown analysis type: {analysis_type}")

        except Exception as e:
            st.error(f"Error during analysis: {e}")
            logger.error(f"Analysis error ({analysis_type}): {e}", exc_info=True)

    # Footer
    st.divider()
    st.markdown(
        """
        ### 📚 Snowflake H3 Functions
        このデモでは以下の Snowflake H3 関数を使用しています:
        - `H3_POINT_TO_CELL(geography, resolution)` - 地点をH3セルに変換
        - `H3_CELL_TO_BOUNDARY(h3_cell)` - H3セルの境界ポリゴンを取得
        - `ST_BUFFER(geography, distance)` - 地点周辺のバッファゾーン作成
        - `ST_INTERSECTS(geo1, geo2)` - 地理オブジェクトの交差判定

        詳細は [Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/functions-geospatial) を参照してください。
        """
    )


if __name__ == "__main__":
    session = create_session()
    st.session_state.session = session

    build_main_common_components("H3 Index Demo")
    build_sidebar_common_components()

    build_h3_index_demo_page()
