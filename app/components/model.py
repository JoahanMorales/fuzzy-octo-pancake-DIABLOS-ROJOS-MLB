"""Streamlit cache for the model bundle. Pages call this instead of loading LightGBM on every rerun."""
from __future__ import annotations

import streamlit as st

from stuffplus.serving import available, load_bundle


@st.cache_resource(show_spinner="Cargando modelos…")
def cached_bundle():
    """``st.cache_resource`` around ``serving.load_bundle``. None when there is no manifest."""
    if not available():
        return None
    return load_bundle()
