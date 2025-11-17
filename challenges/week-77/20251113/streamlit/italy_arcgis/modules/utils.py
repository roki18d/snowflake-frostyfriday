import logging
import sys

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from colorama import Fore, Style, init as colorama_init
from modules.settings import APPLICATION_NAME


colorama_init(autoreset=True)

LOG_LEVEL_COLORS = {
    "DEBUG": Fore.CYAN,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA + Style.BRIGHT,
}

class ColorFormatter(logging.Formatter):
    def __init__(self, use_color=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in LOG_LEVEL_COLORS:
            color = LOG_LEVEL_COLORS[levelname]
            record.levelname = f"{color}{levelname}{Style.RESET_ALL}"
        return super().format(record)


def get_logger(name: str = __name__, log_level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    use_color = sys.stdout.isatty()
    formatter = ColorFormatter(
        use_color=use_color,
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = get_logger(__name__)


@st.cache_resource(show_spinner=False)
def create_session():
    try:
        from snowflake.snowpark.context import get_active_session
        return get_active_session()

    except Exception:
        from snowflake.snowpark import Session
        cfg = st.secrets["snowflake"]
        session = Session.builder.configs(
            {
                "account": cfg["account"],
                "user": cfg["user"],
                "role": cfg["role"],
                "warehouse": cfg["warehouse"],
                "database": cfg["database"],
                "schema": cfg["schema"],
                "authenticator": "externalbrowser",
            }
        ).create()
        return session


def get_current_datetime():
    return datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")


def build_main_common_components(page_name: str, show_title: bool = True):
    if show_title:
        st.title(page_name)
    try:
        st.set_page_config(
            page_title=f"{page_name} - {APPLICATION_NAME}",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except Exception as e:
        logger.warning(e)

    hide_decoration_bar_style = '''
        <style>[data-testid="stDecoration"] {display:none;}</style>
    '''
    st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)
    return


def build_sidebar_common_components():
    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    st.sidebar.page_link("main.py", label="Home", icon=":material/home:")
    st.sidebar.page_link("pages/01_nearest_stations.py", label="Nearest Stations", icon=":material/train:")
    st.sidebar.page_link("pages/02_shortest_path.py", label="Shortest Path", icon=":material/route:")
    st.sidebar.page_link("pages/03_sightseeing.py", label="Sightseeing Guide", icon=":material/tour:")
    st.sidebar.page_link("pages/04_h3_index_demo.py", label="H3 Index Demo", icon=":material/hive:")
