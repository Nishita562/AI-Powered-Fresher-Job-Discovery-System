"""Custom CSS layered on top of the Streamlit theme in .streamlit/config.toml."""

import streamlit as st

PALETTE = {
    "primary": "#4F46E5",
    "primary_dark": "#3730A3",
    "accent": "#0D9488",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "card": "#FFFFFF",
    "good": "#15803D",
    "warn": "#B45309",
    "bad": "#B91C1C",
}

# Categorical colours for charts (colour-blind-friendly, fixed order).
CHART_COLORS = ["#4F46E5", "#0D9488", "#F59E0B", "#DB2777", "#0284C7", "#65A30D", "#9333EA", "#EA580C", "#475569", "#14B8A6"]

CSS = f"""
<style>
:root {{ --primary: {PALETTE['primary']}; --accent: {PALETTE['accent']}; --muted: {PALETTE['muted']}; --border: {PALETTE['border']}; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1250px; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #EEF2FF 0%, #F8FAFC 60%); border-right: 1px solid var(--border); }}

/* hero banner */
.hero {{ background: linear-gradient(120deg, {PALETTE['primary']} 0%, {PALETTE['primary_dark']} 55%, {PALETTE['accent']} 130%);
        color: #fff; border-radius: 18px; padding: 26px 30px; margin-bottom: 18px; }}
.hero h1 {{ color: #fff; font-size: 1.9rem; margin: 0 0 6px 0; }}
.hero p {{ color: #E0E7FF; margin: 0; font-size: 1.02rem; }}

/* page header */
.page-title {{ font-size: 1.65rem; font-weight: 700; margin: 0 0 2px 0; color: {PALETTE['text']}; }}
.page-sub {{ color: var(--muted); margin: 0 0 14px 0; }}

/* metric tiles */
.metric-tile {{ background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 14px 16px; height: 100%; }}
.metric-tile .label {{ color: var(--muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: .04em; }}
.metric-tile .value {{ font-size: 1.75rem; font-weight: 700; color: {PALETTE['text']}; line-height: 1.2; }}
.metric-tile .hint {{ color: var(--muted); font-size: 0.8rem; }}

/* bordered containers used as cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: #fff; border-radius: 14px !important; }}
.job-title {{ font-size: 1.08rem; font-weight: 650; color: {PALETTE['text']}; margin-bottom: 2px; }}
.job-meta {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 6px; }}
.job-snippet {{ color: #334155; font-size: 0.9rem; margin: 6px 0 2px 0; }}

/* badges and chips */
.badge {{ display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.74rem; font-weight: 600;
          margin: 0 4px 4px 0; border: 1px solid transparent; white-space: nowrap; }}
.b-live {{ background: #DCFCE7; color: #166534; border-color: #BBF7D0; }}
.b-sample {{ background: #FEF3C7; color: #92400E; border-color: #FDE68A; }}
.b-demo {{ background: #DBEAFE; color: #1E40AF; border-color: #BFDBFE; }}
.b-neutral {{ background: #F1F5F9; color: #334155; border-color: #E2E8F0; }}
.b-good {{ background: #DCFCE7; color: #166534; }}
.b-warn {{ background: #FEF3C7; color: #92400E; }}
.b-bad {{ background: #FEE2E2; color: #991B1B; }}
.chip {{ display: inline-block; padding: 1px 8px; border-radius: 6px; font-size: 0.76rem; margin: 0 4px 4px 0;
         background: #EEF2FF; color: #3730A3; }}
.chip-match {{ background: #DCFCE7; color: #166534; }}
.chip-miss {{ background: #FFF7ED; color: #9A3412; }}

/* score display */
.score-box {{ text-align: center; border-radius: 12px; padding: 8px 4px; background: #EEF2FF; }}
.score-box .num {{ font-size: 1.6rem; font-weight: 750; color: {PALETTE['primary_dark']}; line-height: 1.1; }}
.score-box .cap {{ font-size: 0.72rem; color: var(--muted); }}
.bar {{ height: 8px; background: #E2E8F0; border-radius: 4px; overflow: hidden; margin: 2px 0 6px 0; }}
.bar > span {{ display: block; height: 100%; background: {PALETTE['accent']}; }}
.bar-label {{ font-size: 0.78rem; color: #334155; display: flex; justify-content: space-between; }}

.notice {{ border-left: 4px solid {PALETTE['warn']}; background: #FFFBEB; padding: 10px 14px; border-radius: 8px;
           color: #78350F; font-size: 0.9rem; margin: 6px 0 12px 0; }}
.notice.info {{ border-color: {PALETTE['primary']}; background: #EEF2FF; color: #312E81; }}
.empty-state {{ text-align: center; padding: 34px 10px; color: var(--muted); border: 1px dashed #CBD5E1; border-radius: 14px; background: #fff; }}
.empty-state .big {{ font-size: 1.15rem; font-weight: 600; color: #334155; }}
.small-muted {{ color: var(--muted); font-size: 0.82rem; }}
@media (max-width: 760px) {{ .hero {{ padding: 18px; }} .hero h1 {{ font-size: 1.4rem; }} .metric-tile .value {{ font-size: 1.35rem; }} }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
