from __future__ import annotations

from pathlib import Path
import re
from typing import List, Dict, Optional

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
    min-width: 320px;
    max-width: 520px;
    resize: horizontal;
    overflow: auto;
}

section[data-testid="stSidebar"][aria-expanded="false"] {
    width: 0;
    min-width: 0;
    max-width: 0;
    margin-left: 0;
}

section[data-testid="stSidebar"][aria-expanded="false"] ~ div[data-testid="stMain"] {
    margin-left: 0;
    padding-left: 0;
}

button[data-testid="stExpandSidebarButton"],
button[data-testid="stBaseButton-headerNoPadding"] {
    background: #143f37;
    color: #f6f1e9;
    padding: 6px 12px;
    border-radius: 999px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
    position: relative;
}

button[data-testid="stExpandSidebarButton"] *,
button[data-testid="stBaseButton-headerNoPadding"] * {
    display: none !important;
}

button[data-testid="stExpandSidebarButton"]::before {
    content: "Filters";
    color: #f6f1e9;
}

button[data-testid="stBaseButton-headerNoPadding"]::before {
    content: "Close";
    color: #f6f1e9;
}

.table-wrap table {
    width: 100%;
    border-collapse: collapse;
}

.table-wrap th,
.table-wrap td {
    text-align: center !important;
}

.table-wrap th {
    white-space: nowrap;
}

div[data-testid="stDataFrame"] div[role="gridcell"],
div[data-testid="stDataFrame"] div[role="columnheader"],
div[data-testid="stDataFrame"] div[role="rowheader"] {
    justify-content: center;
    text-align: center;
}

div[data-testid="stDataFrame"] table th,
div[data-testid="stDataFrame"] table td,
div[data-testid="stTable"] table th,
div[data-testid="stTable"] table td {
    text-align: center !important;
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
      <h1>IPL Impact Model</h1>
            <p>Explore match scorecards, batting impact ratings, and season trends.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.info("Impact scores are batting-only. Bowling metrics are not modeled in this UI.")


def center_table(
    df: pd.DataFrame,
    format_map: Optional[Dict[str, str]] = None,
    hide_index: bool = False,
    small_cols: Optional[List[int]] = None,
) -> pd.io.formats.style.Styler:
    styler = df.style
    if format_map:
        styler = styler.format(format_map)
    if hide_index:
        styler = styler.hide(axis="index")
    styler = styler.set_properties(**{"text-align": "center"})

    styles = [
        {"selector": "th", "props": [("text-align", "center")]},
        {"selector": "th.row_heading", "props": [("text-align", "center")]},
    ]
    if small_cols:
        for col_idx in small_cols:
            styles.append({
                "selector": f"th.col{col_idx}, td.col{col_idx}",
                "props": [("width", "90px"), ("min-width", "90px"), ("max-width", "90px")],
            })

    return styler.set_table_styles(styles).set_table_attributes('class="center-table"')


def render_table(styler: pd.io.formats.style.Styler) -> None:
    st.markdown(f"<div class='table-wrap'>{styler.to_html()}</div>", unsafe_allow_html=True)

files = find_scorecard_files(BASE_DIR)
if not files:
    st.warning("No scorecard files found in scorecards/base. Add scorecards and refresh.")
    st.stop()

file_season_map = build_file_season_map(files)
seasons = sorted({season for season in file_season_map.values() if season})

st.sidebar.header("Filters")
st.sidebar.subheader("Seasons")
selected_seasons: List[str] = []
for season in seasons:
    if st.sidebar.checkbox(season, value=True, key=f"season_{season}"):
        selected_seasons.append(season)

filtered_files = [
    file_path for file_path in files
    if not selected_seasons or file_season_map.get(file_path) in selected_seasons
]

if not filtered_files:
    st.warning("No files match the selected seasons.")
    st.stop()


def format_file_label(file_path: Path) -> str:
    season_label = file_season_map.get(file_path) or "Unknown"
    return season_label


selected_file = st.sidebar.selectbox(
    "Scorecard file",
    filtered_files,
    format_func=format_file_label,
)

@st.cache_data(show_spinner=False)
def load_sheet(file_path: str, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(file_path, sheet_name=sheet_name, header=None)

@st.cache_data(show_spinner=False)
def load_match_labels(file_path: str) -> Dict[str, str]:
    xls = pd.ExcelFile(file_path)
    labels: Dict[str, str] = {}

    def normalize_team_label(name: str) -> str:
        label = re.sub(r"\(.*?target.*?\)", "", name, flags=re.IGNORECASE)
        label = re.sub(r"\btarget\b.*", "", label, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", label).strip()

    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)
        blocks = extract_batting_blocks(df)
        team_names = [block.get("team_name") for block in blocks if block.get("team_name")]
        team_names = [
            normalize_team_label(name)
            for name in team_names
            if isinstance(name, str) and name.strip()
        ]
        if len(team_names) >= 2:
            label = f"{sheet_name} {team_names[0]} vs {team_names[1]}"
        elif len(team_names) == 1:
            label = f"{sheet_name} {team_names[0]}"
        else:
            label = sheet_name
        labels[sheet_name] = label
    return labels

match_labels = load_match_labels(str(selected_file))
sheet_names = list(match_labels.keys())
selected_match = st.sidebar.selectbox(
    "Match",
    sheet_names,
    format_func=lambda name: match_labels.get(name, name),
)
season_label = file_season_map.get(selected_file)

match_df = load_sheet(str(selected_file), selected_match)
impact_df = impact.match_impact_dataframe(match_df, season_label, selected_match)

batting_blocks = extract_batting_blocks(match_df)

@st.cache_data(show_spinner=True)
def load_all_innings(file_list: List[str]) -> pd.DataFrame:
    files = [Path(path) for path in file_list]
    all_innings = impact.load_innings_data(files, build_file_season_map(files))
    return pd.DataFrame(all_innings)

df_all = load_all_innings([str(path) for path in filtered_files])

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

tab_scorecard, tab_impact, tab_trends = st.tabs([
    "Batting Scorecard",
    "Batting Impact Leaders",
    "Batting Trends",
])

with tab_scorecard:
    st.subheader("Batting Scorecard")

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

    if impact_df.empty:
        st.info("No impact data found for this match.")
    else:
        match_top = impact_df.sort_values(by="ImpactIndex", ascending=False).head(10)
        impact_fig = px.bar(
            match_top,
            x="ImpactIndex",
            y="Name",
            orientation="h",
            color="ImpactIndex",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            title="Match Impact Leaders",
        )
        impact_fig.update_layout(height=320, yaxis=dict(autorange="reversed"))
        st.plotly_chart(impact_fig, use_container_width=True)

    for idx, block in enumerate(batting_blocks):
        team_name = block.get("team_name", f"Innings {idx + 1}")
        batting_df = block["batting"].copy()

        st.markdown(f"### {team_name}")
        if not batting_df.empty:
            batting_df = batting_df[[
                "Player", "How Out", "Runs", "Balls", "4s", "6s", "Strike Rate", "ImpactIndex"
            ]]
            batting_df["Strike Rate"] = pd.to_numeric(batting_df["Strike Rate"], errors="coerce")
            for col in ["Runs", "Balls", "4s", "6s"]:
                batting_df[col] = pd.to_numeric(batting_df[col], errors="coerce").round(0).astype("Int64")
            batting_df = batting_df.reset_index(drop=True)
            batting_df.insert(0, "No.", range(1, len(batting_df) + 1))
            st.table(
                center_table(
                    batting_df,
                    format_map={
                        "Runs": "{:.0f}",
                        "Balls": "{:.0f}",
                        "4s": "{:.0f}",
                        "6s": "{:.0f}",
                        "Strike Rate": "{:.2f}",
                        "ImpactIndex": "{:.3f}",
                    },
                    hide_index=True,
                    small_cols=[0],
                )
            )
        else:
            st.info("No batting data found for this innings.")

with tab_impact:
    st.subheader("Batting Impact Leaders")

    if df_all.empty:
        st.info("No impact data found for the selected seasons.")
    else:
        player_summary = df_all.groupby("Name").agg({
            "ImpactIndex": "sum",
            "Runs": "sum",
            "SR": "mean",
            "Match": "count",
        }).reset_index()
        player_summary.rename(columns={
            "ImpactIndex": "TotalImpact",
            "Runs": "TotalRuns",
            "SR": "AvgSR",
            "Match": "Innings",
        }, inplace=True)
        player_summary["ImpactPerInnings"] = player_summary["TotalImpact"] / player_summary["Innings"]

        top_count = st.slider("Top players", min_value=5, max_value=30, value=12)
        impact_top = player_summary.sort_values(by="TotalImpact", ascending=False).head(top_count)

        fig = px.bar(
            impact_top,
            x="TotalImpact",
            y="Name",
            orientation="h",
            color="TotalImpact",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            title="Total Cumulative Impact by Player",
        )
        fig.update_layout(height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

        scatter_fig = px.scatter(
            player_summary,
            x="AvgSR",
            y="TotalRuns",
            color="TotalImpact",
            size="TotalImpact",
            hover_name="Name",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            title="Season Cumulative Runs vs Average Strike Rate",
            labels={"AvgSR": "Avg SR (innings)", "TotalRuns": "Total Runs"},
        )
        scatter_fig.update_layout(height=450)
        st.plotly_chart(scatter_fig, use_container_width=True)

        st.markdown("#### Impact vs Innings Count")
        innings_fig = px.scatter(
            player_summary,
            x="Innings",
            y="TotalImpact",
            size="TotalRuns",
            color="ImpactPerInnings",
            hover_name="Name",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            title="Total Impact vs Innings",
            labels={
                "TotalImpact": "Total Impact",
                "Innings": "Innings",
                "ImpactPerInnings": "Impact per Innings",
            },
        )
        innings_fig.update_layout(height=360)
        st.plotly_chart(innings_fig, use_container_width=True)

        st.markdown("#### Total Impact vs % Match Impact Share")
        match_totals = df_all.groupby(["Season", "Match"]).agg({"ImpactIndex": "sum"}).rename(
            columns={"ImpactIndex": "MatchImpact"}
        )
        share_df = df_all.merge(match_totals, on=["Season", "Match"], how="left")
        share_df["MatchImpactPct"] = (share_df["ImpactIndex"] / share_df["MatchImpact"]) * 100

        player_team_share = share_df.groupby("Name").agg({
            "ImpactIndex": "sum",
            "MatchImpactPct": "mean",
        }).reset_index()
        player_team_share = player_team_share.merge(
            player_summary[["Name", "Innings"]],
            on="Name",
            how="left",
        )

        share_fig = px.scatter(
            player_team_share,
            x="ImpactIndex",
            y="MatchImpactPct",
            size="ImpactIndex",
            color="Innings",
            hover_name="Name",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            title="Total Impact vs Avg % Match Impact Share",
            labels={"ImpactIndex": "Total Impact", "MatchImpactPct": "% of Match Impact"},
        )
        share_fig.update_layout(height=360)
        st.plotly_chart(share_fig, use_container_width=True)

with tab_trends:
    st.subheader("Batting Trends")
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

        st.markdown("#### Best Knocks")
        top_knocks = df_all.sort_values(by="ImpactIndex", ascending=False).head(20).reset_index(drop=True)
        top_knocks.insert(0, "Rank", range(1, len(top_knocks) + 1))
        top_knocks_view = top_knocks[["Rank", "Name", "Season", "Match", "Runs", "SR", "ImpactIndex"]]
        top_knocks_view["Runs"] = pd.to_numeric(top_knocks_view["Runs"], errors="coerce").round(0).astype("Int64")
        render_table(
            center_table(
                top_knocks_view,
                format_map={"Runs": "{:.0f}", "SR": "{:.2f}", "ImpactIndex": "{:.3f}"},
                hide_index=True,
                small_cols=[0, 2],
            )
        )

        st.markdown("#### Best Players by Season")
        seasonal_totals = df_all.groupby(["Season", "Name"]).agg({
            "ImpactIndex": "sum",
            "Runs": "sum",
            "SR": "mean",
            "Match": "count",
        }).reset_index()
        seasonal_totals.rename(columns={"Match": "Innings"}, inplace=True)
        seasonal_top = seasonal_totals.sort_values(by="ImpactIndex", ascending=False).head(20).reset_index(drop=True)
        seasonal_top.insert(0, "Rank", range(1, len(seasonal_top) + 1))
        seasonal_top = seasonal_top[["Rank", "Season", "Name", "ImpactIndex", "Innings", "Runs", "SR"]]
        seasonal_top["Innings"] = pd.to_numeric(seasonal_top["Innings"], errors="coerce").round(0).astype("Int64")
        seasonal_top["Runs"] = pd.to_numeric(seasonal_top["Runs"], errors="coerce").round(0).astype("Int64")
        render_table(
            center_table(
                seasonal_top,
                format_map={
                    "ImpactIndex": "{:.3f}",
                    "Innings": "{:.0f}",
                    "Runs": "{:.0f}",
                    "SR": "{:.2f}",
                },
                hide_index=True,
                small_cols=[0, 1],
            )
        )
