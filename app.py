"""AI-Powered Fresher Job Discovery System — Streamlit entry point.

Run with:  streamlit run app.py   (or ./run.sh)
"""

import streamlit as st

st.set_page_config(page_title="Fresher Job Discovery", page_icon=":material/travel_explore:", layout="wide",
                   initial_sidebar_state="expanded")

from src.data_loader import DATASET_CHOICES  # noqa: E402
from ui import nav, state, theme  # noqa: E402
from ui.components import data_mode_summary  # noqa: E402
from ui.views import (analytics, companies, dashboard, discover, job_search, recommendations,  # noqa: E402
                      settings_about, tracker)

theme.inject_css()
state.init_state()

nav.PAGES.update({
    "dashboard": st.Page(dashboard.render, title="Dashboard", icon=":material/space_dashboard:", url_path="dashboard", default=True),
    "search": st.Page(job_search.render, title="Job Search", icon=":material/search:", url_path="search"),
    "recommend": st.Page(recommendations.render, title="AI Recommendations", icon=":material/auto_awesome:", url_path="recommendations"),
    "companies": st.Page(companies.render, title="Company Explorer", icon=":material/apartment:", url_path="companies"),
    "tracker": st.Page(tracker.render, title="Application Tracker", icon=":material/checklist:", url_path="tracker"),
    "analytics": st.Page(analytics.render, title="Analytics", icon=":material/insights:", url_path="analytics"),
    "discover": st.Page(discover.render, title="Collect Jobs (Playwright)", icon=":material/robot_2:", url_path="collect"),
    "settings": st.Page(settings_about.render, title="Settings & About", icon=":material/settings:", url_path="about"),
})
P = nav.PAGES
page = st.navigation({
    "Find jobs": [P["dashboard"], P["search"], P["recommend"]],
    "Explore & track": [P["companies"], P["tracker"], P["analytics"]],
    "System": [P["discover"], P["settings"]],
})

with st.sidebar:
    st.markdown("### :material/travel_explore: Fresher Job Discovery")
    st.caption("Playwright · TF-IDF recommendations · SQLite")
    choice = st.selectbox("Dataset", list(DATASET_CHOICES), format_func=DATASET_CHOICES.get,
                          index=list(DATASET_CHOICES).index(st.session_state.dataset_choice),
                          help="Choose which records every page uses. Sample data is fictional.")
    if choice != st.session_state.dataset_choice:
        st.session_state.dataset_choice = choice
        st.session_state.search_page = 1
        st.session_state.pop("score_cache", None)
        st.rerun()
    st.markdown(data_mode_summary(state.get_jobs()), unsafe_allow_html=True)

page.run()

with st.sidebar:  # rendered after the page so it reflects a profile submitted on this run
    profile = st.session_state.profile
    if profile:
        st.caption(f"Profile: {len(profile.skills)} skills · {', '.join(profile.preferred_roles[:2]) or 'no role set'}"
                   + (" (demo profile)" if st.session_state.profile_is_demo else ""))
    else:
        st.caption("No candidate profile yet — set one on **AI Recommendations** to see match scores.")
