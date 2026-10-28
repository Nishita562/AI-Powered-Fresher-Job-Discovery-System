"""Registry of st.Page objects, filled in by app.py so views can link to each other."""

import streamlit as st

PAGES: dict = {}


def go(name: str) -> None:
    """Switch to another page if the navigation has been set up (it is not in unit tests)."""
    if name in PAGES:
        st.switch_page(PAGES[name])
