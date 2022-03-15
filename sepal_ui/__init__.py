from types import SimpleNamespace
from pathlib import Path
from configparser import ConfigParser

import ipyvuetify as v

from sepal_ui.frontend import styles

__author__ = """Pierrick Rambaud"""
__email__ = "pierrick.rambaud49@gmail.com"
__version__ = "2.6.2"


def get_theme(config_file):
    """
    get the theme from the config file (default to dark)

    Return:
        (str): the theme to use
    """

    # init theme
    theme = "dark"

    # read the config file if existing
    if config_file.is_file():
        config = ConfigParser()
        config.read(config_file)
        theme = config.get("sepal-ui", "theme", fallback="dark")

    # set vuetify theme
    v.theme.dark = True if theme == "dark" else False

    return theme


config_file = Path.home() / ".sepal-ui-config"
"Pathlib.Path: the configuration file generated by sepal-ui based application to save parameters as language or theme"

theme = getattr(v.theme.themes, get_theme(config_file))
"traitlets: the theme used in sepal"

color = SimpleNamespace(
    main=theme.main,
    darker=theme.darker,
    bg=theme.bg_color,
    primary=theme.primary,
    accent=theme.accent,
    secondary=theme.secondary,
    success=theme.success,
    info=theme.info,
    warning=theme.warning,
    error=theme.error,
    menu=theme.menu,
)
'SimpleNamespace: the colors of sepal. members are in the following list: "main, darker, bg, primary, accent, secondary, success, info, warning, error, menu". They will render according to the selected theme.'
