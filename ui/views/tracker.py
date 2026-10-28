"""Application Tracker: saved jobs and user-entered statuses, persisted in SQLite."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from config import settings
from src.export import to_csv_bytes
from ui import state
from ui.components import empty_state, metric_tile, notice, page_header
from ui.theme import CHART_COLORS


def render() -> None:
    state.show_flash()
    page_header("Application Tracker", "Keep track of jobs you saved and where each application stands.")
    notice("Statuses here are <b>entered by you</b> and stored only in the local SQLite database "
           "(database/jobs.db). They are not retrieved from employers.", "info")
    store = state.get_store()
    apps = store.load_applications()
    if apps.empty:
        empty_state("No saved jobs yet", "Use the Save button on any job card to start tracking it.")
        return

    counts = apps["status"].value_counts()
    cols = st.columns(len(settings.APPLICATION_STATUSES))
    for col, status in zip(cols, settings.APPLICATION_STATUSES):
        with col:
            metric_tile(status, int(counts.get(status, 0)))

    left, right = st.columns([2.2, 1], gap="large")
    with left:
        st.markdown("**Edit status and notes, then press Save changes**")
        editable = apps[["job_id", "title", "company", "data_mode", "status", "notes", "updated_at"]].copy()
        editable.insert(0, "remove", False)
        edited = st.data_editor(
            editable, hide_index=True, width="stretch", key="tracker_editor",
            disabled=["job_id", "title", "company", "data_mode", "updated_at"],
            column_order=["remove", "title", "company", "status", "notes", "data_mode", "updated_at"],
            column_config={
                "remove": st.column_config.CheckboxColumn("Remove", width="small"),
                "status": st.column_config.SelectboxColumn("Status", options=settings.APPLICATION_STATUSES, required=True),
                "notes": st.column_config.TextColumn("Notes", max_chars=500),
                "data_mode": st.column_config.TextColumn("Data", width="small"),
                "updated_at": st.column_config.TextColumn("Last updated"),
            },
        )
        b1, b2 = st.columns(2)
        if b1.button("Save changes", type="primary", icon=":material/save:", width="stretch"):
            changed = removed = 0
            original = apps.set_index("job_id")
            for _, row in edited.iterrows():
                if row["remove"]:
                    store.remove_application(row["job_id"])
                    removed += 1
                    continue
                before = original.loc[row["job_id"]]
                if row["status"] != before["status"] or (row["notes"] or "") != (before["notes"] or ""):
                    store.update_application(row["job_id"], status=row["status"], notes=row["notes"] or "")
                    changed += 1
            state.flash(f"Saved: {changed} updated, {removed} removed.")
            st.rerun()
        b2.download_button("Export tracker (CSV)", to_csv_bytes(apps), "application_tracker.csv", "text/csv",
                           icon=":material/download:", width="stretch")
    with right:
        chart_df = counts.reindex(settings.APPLICATION_STATUSES, fill_value=0).reset_index()
        chart_df.columns = ["status", "count"]
        fig = px.bar(chart_df, x="status", y="count", color="status", color_discrete_sequence=CHART_COLORS,
                     title="Applications by status", template="plotly_white")
        fig.update_layout(showlegend=False, height=340, margin=dict(l=10, r=10, t=50, b=10), yaxis_title="", xaxis_title="")
        fig.update_yaxes(dtick=1)
        st.plotly_chart(fig, width="stretch")
        st.caption(f"{len(apps)} tracked job(s). Saved sample jobs are fictional and marked as such in the Data column.")
