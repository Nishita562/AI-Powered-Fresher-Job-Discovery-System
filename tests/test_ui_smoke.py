"""Headless UI tests with Streamlit's AppTest: every page renders and key buttons work."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
VIEWS = ["dashboard", "job_search", "recommendations", "companies", "tracker", "analytics", "discover", "settings_about"]


def _view_script(module: str, prelude: str = "") -> str:
    return f"""
import sys; sys.path.insert(0, {str(ROOT)!r})
import importlib
from ui import state, theme
theme.inject_css(); state.init_state()
{prelude}
importlib.import_module("ui.views.{module}").render()
"""


@pytest.mark.parametrize("module", VIEWS)
def test_page_renders_without_exceptions(module):
    at = AppTest.from_string(_view_script(module), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]


def test_full_app_with_navigation_renders():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()
    assert not at.exception
    assert any("Fresher Job Discovery" in m.value for m in at.markdown)


def test_demo_profile_button_produces_scores():
    at = AppTest.from_string(_view_script("dashboard"), default_timeout=90).run()
    demo = [b for b in at.button if b.label == "Try a demo profile"]
    assert demo, "demo profile button missing"
    demo[0].click().run()
    assert at.session_state.profile is not None
    assert not at.exception


def test_recommendations_page_with_demo_profile_lists_results():
    prelude = "st_profile = state.DEMO_PROFILE\nimport streamlit as st\nst.session_state.profile = st_profile"
    at = AppTest.from_string(_view_script("recommendations", prelude), default_timeout=90).run()
    assert not at.exception
    assert any("Top" in m.value and "matches" in m.value for m in at.markdown)


def test_job_search_keyword_filters_results():
    at = AppTest.from_string(_view_script("job_search"), default_timeout=90).run()
    at.text_input(key="f_keyword").input("nlp").run()
    assert not at.exception
    counts = [m.value for m in at.markdown if "jobs match" in m.value]
    assert counts and not counts[0].startswith("**0**")


def test_company_preselection_survives_other_interactions():
    # Regression: companies sent from the Company Explorer used to reset after any other click.
    prelude = ("import streamlit as st\n"
               "if 'seeded' not in st.session_state:\n"
               "    st.session_state.seeded = True\n"
               "    st.session_state.crawl_preselect = ['Paytm', 'Groww']")
    at = AppTest.from_string(_view_script("discover", prelude), default_timeout=90).run()
    assert at.multiselect(key="live_companies").value == ["Paytm", "Groww"]
    at.checkbox(key="live_headed").check().run()
    assert at.multiselect(key="live_companies").value == ["Paytm", "Groww"]
    assert not at.exception
