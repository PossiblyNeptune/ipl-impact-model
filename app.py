from __future__ import annotations

from pathlib import Path
from typing import List, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from scripts import impact
from scripts.common import (
    BASE_DIR,
    build_file_season_map,
    clean_player_name_strict,
    configure_pandas_display,
    find_scorecard_files,
)
from scripts.scorecard import extract_batting_blocks


configure_pandas_display()

st.set_page_config(
    page_title="IPL Impact Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Fraunces:wght@400;600&display=swap');

:root {
  --bg: #f6f1e9;
  --panel: #ffffff;
  --ink: #1d1a16;
  --muted: #5c5c5c;
  --accent: #1d7a6d;
  --accent-2: #e4572e;
}

.stApp {
  background: linear-gradient(160deg, #f6f1e9 0%, #eff6f3 45%, #f8efe7 100%);
  color: var(--ink);
}

section[data-testid="stSidebar"] {
  background: #143f37;
  color: #f6f1e9;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p {
  color: #f6f1e9;
}

h1, h2, h3, h4 {
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: -0.02em;
}

p, label, div {
  font-family: 'Fraunces', serif;
}

.hero {
  background: radial-gradient(circle at top left, rgba(29, 122, 109, 0.18), transparent 55%),
              radial-gradient(circle at bottom right, rgba(228, 87, 46, 0.18), transparent 50%);
  padding: 1.4rem 1.6rem;
  border-radius: 16px;
  border: 1px solid rgba(29, 122, 109, 0.2);
}

.metric-card {
  background: var(--panel);
  border-radius: 14px;
  padding: 1rem 1.1rem;
  border: 1px solid rgba(29, 122, 109, 0.15);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.05);
}

.metric-title {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}

.metric-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--ink);
}

.metric-sub {
  font-size: 0.9rem;
  color: var(--muted);
}
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <h1>IPL Impact Studio</h1>
            <p>Explore match scorecards, batting impact ratings, and season trends.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info("Impact scores are batting-only. Bowling metrics are not modeled in this UI.")

files = find_scorecard_files(BASE_DIR)
if not files:
    st.warning("No scorecard files found in scoreacrds/base. Add scorecards and refresh.")
    st.stop()

file_season_map = build_file_season_map(files)
seasons = sorted({season for season in file_season_map.values() if season})

st.sidebar.header("Filters")
selected_seasons = st.sidebar.multiselect("Seasons", seasons, default=seasons)

filtered_files = [
    file_path for file_path in files
    if not selected_seasons or file_season_map.get(file_path) in selected_seasons
]

if not filtered_files:
    st.warning("No files match the selected seasons.")
    st.stop()


def format_file_label(file_path: Path) -> str:
    season_label = file_season_map.get(file_path) or "Unknown"
    return f"{season_label} | {file_path.name}"


selected_file = st.sidebar.selectbox(
    "Scorecard file",
    filtered_files,
    format_func=format_file_label,
)

@st.cache_data(show_spinner=False)
def load_sheet_names(file_path: str) -> List[str]:
    return pd.ExcelFile(file_path).sheet_names

@st.cache_data(show_spinner=False)
def load_sheet(file_path: str, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(file_path, sheet_name=sheet_name, header=None)

sheet_names = load_sheet_names(str(selected_file))
selected_match = st.sidebar.selectbox("Match", sheet_names)
season_label = file_season_map.get(selected_file)

match_df = load_sheet(str(selected_file), selected_match)
impact_df = impact.match_impact_dataframe(match_df, season_label, selected_match)

batting_blocks = extract_batting_blocks(match_df)

impact_map = {}
if not impact_df.empty:
    impact_map = dict(zip(impact_df["Name"], impact_df["ImpactIndex"]))

for block in batting_blocks:
    batting_df = block["batting"]
    if batting_df.empty:
        block["batting"] = batting_df
        continue
    batting_df["ImpactIndex"] = batting_df["Player"].apply(
        lambda name: impact_map.get(clean_player_name_strict(str(name)))
    )
    block["batting"] = batting_df

summary_cols = st.columns(3)
for idx, block in enumerate(batting_blocks[:2]):
    total = block.get("total")
    team_name = block.get("team_name", f"Innings {idx + 1}")
    if total:
        runs = total["Runs"]
        overs = total["Overs"]
        run_rate = total["RunRate"]
    else:
        runs = "-"
        overs = "-"
        run_rate = "-"

    top_impact = None
    if not block["batting"].empty and "ImpactIndex" in block["batting"].columns:
        impact_series = pd.to_numeric(block["batting"]["ImpactIndex"], errors="coerce")
        if impact_series.notna().any():
            top_idx = impact_series.idxmax()
            top_row = block["batting"].loc[[top_idx]]
        else:
            top_row = pd.DataFrame()
        if not top_row.empty:
            top_impact = f"{top_row.iloc[0]['Player']} ({top_row.iloc[0]['ImpactIndex']})"

    card_html = (
        f"<div class='metric-card'>"
        f"<div class='metric-title'>{team_name}</div>"
        f"<div class='metric-value'>{runs}</div>"
        f"<div class='metric-sub'>Overs: {overs} | Run rate: {run_rate}</div>"
    )
    if top_impact:
        card_html += f"<div class='metric-sub'>Impact leader: {top_impact}</div>"
    card_html += "</div>"

    summary_cols[idx % 3].markdown(card_html, unsafe_allow_html=True)

st.markdown("\n")

team_summary_rows: List[Dict[str, object]] = []
for idx, block in enumerate(batting_blocks):
    total = block.get("total")
    if not total:
        continue
    team_summary_rows.append({
        "Team": block.get("team_name", f"Innings {idx + 1}"),
        "Runs": total["Runs"],
        "Overs": total["Overs"],
        "RunRate": total["RunRate"],
    })

if team_summary_rows:
    team_summary_df = pd.DataFrame(team_summary_rows)
    team_fig = px.bar(
        team_summary_df,
        x="Team",
        y="Runs",
        color="RunRate",
        color_continuous_scale=["#1d7a6d", "#e4572e"],
        title="Team Runs and Run Rate",
    )
    team_fig.update_layout(height=320)
    st.plotly_chart(team_fig, use_container_width=True)

tab_scorecard, tab_impact, tab_trends = st.tabs([
    "Batting Scorecard",
    "Batting Impact Leaders",
    "Batting Trends",
])

with tab_scorecard:
    st.subheader("Batting Scorecard")

    for idx, block in enumerate(batting_blocks):
        team_name = block.get("team_name", f"Innings {idx + 1}")
        batting_df = block["batting"].copy()

        st.markdown(f"### {team_name}")
        if not batting_df.empty:
            batting_df = batting_df[[
                "Player", "How Out", "Runs", "Balls", "4s", "6s", "Strike Rate", "ImpactIndex"
            ]]
            batting_df["Strike Rate"] = pd.to_numeric(batting_df["Strike Rate"], errors="coerce")
            batting_df["Runs"] = pd.to_numeric(batting_df["Runs"], errors="coerce")
            st.dataframe(
                batting_df.style.format({"Strike Rate": "{:.2f}", "ImpactIndex": "{:.3f}"}),
                use_container_width=True,
            )
        else:
            st.info("No batting data found for this innings.")

with tab_impact:
    st.subheader("Batting Impact Leaders")

    if impact_df.empty:
        st.info("No impact data found for this match.")
    else:
        top_count = st.slider("Top players", min_value=5, max_value=20, value=10)
        impact_top = impact_df.sort_values(by="ImpactIndex", ascending=False).head(top_count)

        fig = px.bar(
            impact_top,
            x="ImpactIndex",
            y="Name",
            orientation="h",
            color="ImpactIndex",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            title="Impact Index by Player",
        )
        fig.update_layout(height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

        scatter_fig = px.scatter(
            impact_df,
            x="SR",
            y="Runs",
            color="ImpactIndex",
            size="ImpactIndex",
            hover_name="Name",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            title="Runs vs Strike Rate (Impact Sized)",
        )
        scatter_fig.update_layout(height=450)
        st.plotly_chart(scatter_fig, use_container_width=True)

with tab_trends:
    st.subheader("Batting Trends")
    trends_enabled = st.checkbox("Load season trend data", value=False)

    if not trends_enabled:
        st.info("Enable season trend data to explore player and season level summaries.")
    else:
        @st.cache_data(show_spinner=True)
        def load_all_innings(file_list: List[str]) -> pd.DataFrame:
            files = [Path(path) for path in file_list]
            all_innings = impact.load_innings_data(files, build_file_season_map(files))
            return pd.DataFrame(all_innings)

        df_all = load_all_innings([str(path) for path in filtered_files])
        if df_all.empty:
            st.info("No innings data available for the selected seasons.")
        else:
            player_name = st.selectbox("Player", sorted(df_all["Name"].unique()))
            player_df = df_all[df_all["Name"] == player_name]
            season_summary = player_df.groupby("Season", dropna=False).agg({
                "ImpactIndex": "sum",
                "Runs": "sum",
                "Match": "count",
            }).reset_index()

            trend_fig = px.line(
                season_summary,
                x="Season",
                y="ImpactIndex",
                markers=True,
                title="Impact by Season",
            )
            st.plotly_chart(trend_fig, use_container_width=True)

            st.markdown("#### Best Knocks (Selected Seasons)")
            top_knocks = df_all.sort_values(by="ImpactIndex", ascending=False).head(20)
            st.dataframe(top_knocks[["Name", "Season", "Match", "Runs", "SR", "ImpactIndex"]])

            st.markdown("#### Best Players by Season")
            seasonal_totals = df_all.groupby(["Season", "Name"])['ImpactIndex'].sum().reset_index()
            seasonal_top = seasonal_totals.sort_values(by="ImpactIndex", ascending=False).head(20)
            st.dataframe(seasonal_top, use_container_width=True)
