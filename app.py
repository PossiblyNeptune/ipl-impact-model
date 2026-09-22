from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scripts.common import (
    BASE_DIR,
    REPO_ROOT,
    clean_player_name_strict,
    configure_pandas_display,
)
from scripts import vorp

configure_pandas_display()

st.set_page_config(
    page_title="IPL Impact & VORP Studio",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Fraunces:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg: #f6f1e9;
  --panel: #ffffff;
  --ink: #1d1a16;
  --muted: #5c5c5c;
  --accent: #1d7a6d;
  --accent-2: #e4572e;
  --border-light: rgba(29, 122, 109, 0.15);
}

.stApp {
  background: linear-gradient(160deg, #f6f1e9 0%, #eff6f3 45%, #f8efe7 100%);
  color: var(--ink);
  font-family: 'Inter', sans-serif;
}

/* Completely remove sidebar and toggle buttons */
[data-testid="stSidebar"],
section[data-testid="stSidebar"],
button[data-testid="stExpandSidebarButton"],
button[data-testid="stBaseButton-headerNoPadding"],
div[data-testid="collapsedControl"] {
  display: none !important;
  width: 0 !important;
  visibility: hidden !important;
}

h1, h2, h3, h4 {
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: -0.02em;
}

.hero {
  background: radial-gradient(circle at top left, rgba(29, 122, 109, 0.20), transparent 55%),
              radial-gradient(circle at bottom right, rgba(228, 87, 46, 0.20), transparent 50%),
              #ffffff;
  padding: 1.6rem 2rem;
  border-radius: 18px;
  border: 1px solid rgba(29, 122, 109, 0.22);
  margin-bottom: 1.2rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
}

.hero h1 {
  font-size: 2.2rem;
  margin-bottom: 0.3rem;
  color: #143f37;
}

.hero p {
  font-size: 1.05rem;
  color: #3d4a46;
  margin-bottom: 0.8rem;
  font-family: 'Fraunces', serif;
}


.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.2rem;
}

.metric-card {
  background: var(--panel);
  border-radius: 14px;
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.07);
}

.metric-card-compact {
  padding: 0.7rem 0.75rem;
  border-radius: 12px;
  min-width: 0;
}

.metric-card-compact .metric-title {
  font-size: 0.70rem;
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 0.25rem;
}

.metric-card-compact .metric-value {
  font-size: 1.4rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.metric-card-compact .metric-sub {
  font-size: 0.72rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 0.25rem;
}

@media (min-width: 768px) {
  div[data-testid="stHorizontalBlock"]:has(.metric-card-compact) {
    flex-wrap: nowrap !important;
    gap: 0.6rem !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.metric-card-compact) > div[data-testid="column"] {
    min-width: 0 !important;
    flex: 1 1 0 !important;
  }
}

.metric-title {
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 600;
  font-family: 'Space Grotesk', sans-serif;
  margin-bottom: 0.3rem;
}

.metric-value {
  font-size: 1.7rem;
  font-weight: 700;
  color: var(--ink);
  font-family: 'Space Grotesk', sans-serif;
  line-height: 1.2;
}

.metric-sub {
  font-size: 0.85rem;
  color: var(--muted);
  margin-top: 0.3rem;
  font-family: 'Inter', sans-serif;
}

.table-wrap {
  background: #ffffff;
  border-radius: 14px;
  padding: 0.5rem;
  border: 1px solid var(--border-light);
  box-shadow: 0 8px 20px rgba(0,0,0,0.03);
  overflow-x: auto;
  margin-bottom: 1.5rem;
}

.table-wrap table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}

.table-wrap th {
  background: #f7faf9;
  color: #143f37;
  font-weight: 700;
  padding: 10px 12px;
  border-bottom: 2px solid #d5ded9;
  text-align: center !important;
  font-family: 'Space Grotesk', sans-serif;
  white-space: nowrap;
}

.table-wrap td {
  padding: 9px 12px;
  border-bottom: 1px solid #eef2f0;
  text-align: center !important;
  color: #24292e;
  white-space: nowrap;
}

.table-wrap tr:hover td {
  background: #f4f9f7;
}

div[data-testid="stDataFrame"] table th,
div[data-testid="stDataFrame"] table td,
div[data-testid="stTable"] table th,
div[data-testid="stTable"] table td {
  text-align: center !important;
}
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)

# ---------------------------------------------------------
# HERO BANNER
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <h1>🏏 IPL Impact & VORP Studio</h1>
      <p>Quantifying Era-Adjusted Batting Impact, Position-Specific Value Over Replacement Player (I-VORP), and % Superiority across 19 Seasons (2008–2026).</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# DATA LOADING (BLAZING FAST WITH PARQUET CACHING)
# ---------------------------------------------------------
PARQUET_PATH = REPO_ROOT / "scorecards_csv" / "results" / "all_batting_with_vorp.parquet"
CSV_PATH = REPO_ROOT / "scorecards_csv" / "results" / "all_batting_with_vorp.csv"
MATCHES_PARQUET_PATH = REPO_ROOT / "scorecards_csv" / "results" / "all_matches.parquet"
MATCHES_CSV_PATH = REPO_ROOT / "scorecards_csv" / "results" / "all_matches.csv"


@st.cache_data(show_spinner=False)
def load_vorp_dataset() -> pd.DataFrame:
    """
    Loads full enriched batting dataset with Impact and I-VORP.
    Fast path: Parquet (<40ms). Fallbacks: CSV or live calculation.
    """
    if PARQUET_PATH.exists():
        df = pd.read_parquet(PARQUET_PATH)
    elif CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
    else:
        try:
            df = vorp.load_and_enrich_vorp_data()
        except Exception:
            return pd.DataFrame()

    # Backwards compatibility and helper aliases
    df["Name"] = df["Player_Clean"]
    df["ImpactIndex"] = df["Batting_Impact"]
    df["SR"] = df["Strike_Rate"]
    df["Season"] = df["Season"].astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_matches_metadata() -> pd.DataFrame:
    """
    Loads match summary data with team names, scores, and match results.
    """
    if MATCHES_PARQUET_PATH.exists():
        return pd.read_parquet(MATCHES_PARQUET_PATH)
    elif MATCHES_CSV_PATH.exists():
        return pd.read_csv(MATCHES_CSV_PATH)
    return pd.DataFrame()


df_master = load_vorp_dataset()
df_matches = load_matches_metadata()

if df_master.empty:
    st.error(
        "⚠️ **Dataset not found.** The master VORP dataset could not be loaded. "
        "Please ensure `scorecards_csv/results/all_batting_with_vorp.parquet` is present in the repository."
    )
    st.stop()


# ---------------------------------------------------------
# TABLE FORMATTING HELPERS
# ---------------------------------------------------------
def center_table(
    df: pd.DataFrame,
    format_map: Optional[Dict[str, str]] = None,
    hide_index: bool = True,
    small_cols: Optional[List[int]] = None,
    wide_cols: Optional[List[int]] = None,
) -> pd.io.formats.style.Styler:
    styler = df.style
    if format_map:
        styler = styler.format(format_map, na_rep="-")
    if hide_index:
        styler = styler.hide(axis="index")
    styler = styler.set_properties(**{"text-align": "center"})

    styles = [
        {"selector": "th", "props": [("text-align", "center"), ("background-color", "#f7faf9"), ("color", "#143f37"), ("white-space", "nowrap")]},
        {"selector": "th.row_heading", "props": [("text-align", "center")]},
    ]
    if small_cols:
        for col_idx in small_cols:
            styles.append({
                "selector": f"th.col{col_idx}, td.col{col_idx}",
                "props": [("width", "75px"), ("min-width", "75px"), ("max-width", "75px"), ("white-space", "nowrap")],
            })
    if wide_cols:
        for col_idx in wide_cols:
            styles.append({
                "selector": f"th.col{col_idx}, td.col{col_idx}",
                "props": [("min-width", "210px"), ("white-space", "nowrap !important"), ("text-align", "center")],
            })
    if "Team" in df.columns:
        team_idx = list(df.columns).index("Team")
        styles.append({
            "selector": f"th.col{team_idx}, td.col{team_idx}",
            "props": [("min-width", "210px"), ("white-space", "nowrap !important"), ("text-align", "center")],
        })
    return styler.set_table_styles(styles)


def render_table(styler: pd.io.formats.style.Styler) -> None:
    st.markdown(f"<div class='table-wrap'>{styler.to_html()}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# GLOBAL SEASON FILTER & CONTROLS (MAIN PAGE ABOVE TABS)
# ---------------------------------------------------------
all_seasons = sorted(df_master["Season"].unique().tolist())

with st.container():
    f_c1, f_c2 = st.columns([1.1, 2.9])
    with f_c1:
        select_all = st.checkbox("📅 Select All 19 Seasons (2008–2026)", value=True, key="global_select_all_seasons")
    
    if select_all:
        selected_seasons = all_seasons
        with f_c2:
            st.info(f"Viewing all 19 seasons (2008–2026) across {len(df_master):,} historical innings. Uncheck box to filter specific seasons.")
    else:
        with f_c2:
            selected_seasons = st.multiselect(
                "Select Seasons to Analyze",
                options=all_seasons,
                default=[2024, 2025, 2026] if 2024 in all_seasons else all_seasons[-3:],
                key="global_seasons_multiselect",
            )

if not selected_seasons:
    st.warning("Please select at least one season above to view data.")
    st.stop()

# Filter global dataframe
df_filtered = df_master[df_master["Season"].isin(selected_seasons)].copy()



# ---------------------------------------------------------
# 4 COMPREHENSIVE TABS
# ---------------------------------------------------------
tab_scorecard, tab_vorp, tab_profiler, tab_pantheon = st.tabs([
    "🏟️ Match Scorecard & VORP",
    "👤 Player Studio",
    "👤 Player VORP Profiler",
    "🏆 The Pantheon: Iconic Knocks",
])


# =========================================================
# TAB 1: MATCH SCORECARD & VORP
# =========================================================
with tab_scorecard:
    st.subheader("🏟️ Match Scorecard with Impact & Positional VORP")

    # Match picker
    season_for_match = st.selectbox(
        "Select Season",
        options=sorted(selected_seasons, reverse=True),
        key="match_season_select",
    )
    season_matches = df_filtered[df_filtered["Season"] == season_for_match]
    unique_matches = season_matches["Match"].unique().tolist()

    # Build descriptive label map using df_matches if available
    match_labels: Dict[str, str] = {}
    if not df_matches.empty:
        season_meta = df_matches[df_matches["Season"] == season_for_match]
        for _, row in season_meta.iterrows():
            m_id = str(row["Match"])
            t1 = row.get("Team_1", "")
            t2 = row.get("Team_2", "")
            if pd.notna(t1) and pd.notna(t2):
                match_labels[m_id] = f"{m_id}: {t1} vs {t2}"

    selected_match_id = st.selectbox(
        "Select Match",
        options=unique_matches,
        format_func=lambda m: match_labels.get(m, m),
        key="match_picker_select",
    )

    match_df = season_matches[season_matches["Match"] == selected_match_id]

    if match_df.empty:
        st.info("No scorecard data found for this match.")
    else:
        # Match Overview Cards
        inn_numbers = sorted(match_df["Innings"].unique().tolist())
        card_cols = st.columns(max(len(inn_numbers), 2))

        for idx, inn_num in enumerate(inn_numbers):
            inn_data = match_df[match_df["Innings"] == inn_num]
            team_name = inn_data["Team"].iloc[0] if not inn_data.empty else f"Innings {inn_num}"
            team_runs = inn_data["Team_Runs"].iloc[0] if not inn_data.empty else inn_data["Runs"].sum()
            team_sr = inn_data["Team_SR"].iloc[0] if not inn_data.empty else 0.0

            top_impact_row = inn_data.sort_values(by="Batting_Impact", ascending=False).head(1)
            top_vorp_row = inn_data.sort_values(by="IVORP_Individual", ascending=False).head(1)

            top_impact_text = (
                f"{top_impact_row.iloc[0]['Player_Clean']} ({top_impact_row.iloc[0]['Batting_Impact']:.2f})"
                if not top_impact_row.empty else "-"
            )
            top_vorp_text = (
                f"{top_vorp_row.iloc[0]['Player_Clean']} (+{top_vorp_row.iloc[0]['IVORP_Individual']:.2f})"
                if not top_vorp_row.empty else "-"
            )

            card_html = (
                f"<div class='metric-card'>"
                f"<div class='metric-title'>Innings {inn_num} • {team_name}</div>"
                f"<div class='metric-value'>{int(team_runs) if pd.notna(team_runs) else '-'}</div>"
                f"<div class='metric-sub'>Team Strike Rate: {team_sr:.1f}</div>"
                f"<div class='metric-sub'>💥 <b>Impact Leader</b>: {top_impact_text}</div>"
                f"<div class='metric-sub'>🛡️ <b>I-VORP Leader</b>: {top_vorp_text}</div>"
                f"</div>"
            )
            card_cols[idx].markdown(card_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 1. Match Impact Leaders Bar Chart
        top_match_impact = (
            match_df.sort_values(by="Batting_Impact", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

        fig_match_impact = px.bar(
            top_match_impact,
            x="Batting_Impact",
            y="Player_Clean",
            orientation="h",
            color="Batting_Impact",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            hover_data=["Team", "Pos_Individual", "Runs", "Balls", "Strike_Rate"],
            labels={"Batting_Impact": "Batting Impact", "Player_Clean": "Batter"},
            title="Match Batting Impact Leaders",
        )
        fig_match_impact.update_layout(
            height=320,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_match_impact, use_container_width=True)

        # 2. Match Individual Position I-VORP Bar Chart (directly under impact bar)
        top_match_vorp = (
            match_df.sort_values(by="IVORP_Individual", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

        fig_match_vorp = px.bar(
            top_match_vorp,
            x="IVORP_Individual",
            y="Player_Clean",
            orientation="h",
            color="IVORP_Individual",
            color_continuous_scale=["#1d7a6d", "#e4572e"],
            hover_data=["Team", "Pos_Individual", "Runs", "Balls", "Strike_Rate", "Baseline_Impact_Ind"],
            labels={"IVORP_Individual": "Individual I-VORP", "Player_Clean": "Batter"},
            title="Match Individual Position I-VORP Leaders",
        )
        fig_match_vorp.update_layout(
            height=320,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_match_vorp, use_container_width=True)

        # Detailed Innings Batting Scorecards
        for inn_num in inn_numbers:
            inn_data = match_df[match_df["Innings"] == inn_num].copy()
            team_name = inn_data["Team"].iloc[0] if not inn_data.empty else f"Innings {inn_num}"
            st.markdown(f"#### 🏏 Innings {inn_num}: {team_name}")

            view_df = inn_data[[
                "Batting_Order",
                "Player",
                "How_Out",
                "Runs",
                "Balls",
                "4s",
                "6s",
                "Strike_Rate",
                "Batting_Impact",
                "IVORP_Individual",
            ]].copy()

            view_df.columns = [
                "Order",
                "Player",
                "Dismissal",
                "Runs",
                "Balls",
                "4s",
                "6s",
                "SR",
                "Impact",
                "I-VORP",
            ]

            view_df["Order"] = pd.to_numeric(view_df["Order"], errors="coerce").fillna(0).astype(int)
            for c in ["Runs", "Balls", "4s", "6s"]:
                view_df[c] = pd.to_numeric(view_df[c], errors="coerce").fillna(0).astype(int)

            render_table(
                center_table(
                    view_df,
                    format_map={
                        "SR": "{:.1f}",
                        "Impact": "{:.3f}",
                        "I-VORP": "{:+.3f}",
                    },
                    hide_index=True,
                    small_cols=[0, 3, 4, 5, 6],
                )
            )


# =========================================================
# TAB 2: PLAYER STUDIO (POSITION VORP & IMPACT)
# =========================================================
with tab_vorp:
    st.subheader("👤 Player Studio")
    st.caption(
        "Evaluate batter value relative to the canonical sabermetric replacement baseline (20th percentile of qualified regulars at that position)."
    )

    # Filter row 1: Schemes and Positions
    f_col1, f_col2, f_col3, f_col4 = st.columns([1, 1.6, 1, 1.2])

    with f_col1:
        scheme_choice = st.radio(
            "Positional Scheme",
            options=["Individual Positions", "Tactical Orders"],
            index=0,
            key="vorp_scheme_choice",
        )

    is_ind = scheme_choice == "Individual Positions"
    pos_column = "Pos_Individual" if is_ind else "Pos_Tactical"
    vorp_column = "IVORP_Individual" if is_ind else "IVORP_Tactical"
    base_column = "Baseline_Impact_Ind" if is_ind else "Baseline_Impact_Tact"

    available_positions = sorted(df_filtered[pos_column].unique().tolist())
    if is_ind:
        # Sort canonically
        canonical_order = ["Opener", "Number 3", "Number 4", "Number 5", "Number 6", "Number 7", "Number 8+"]
        available_positions = [p for p in canonical_order if p in available_positions]
    else:
        canonical_tact = ["Top Order", "Middle Order", "Finisher", "Lower Order"]
        available_positions = [p for p in canonical_tact if p in available_positions]

    with f_col2:
        selected_positions = st.multiselect(
            "Select Batting Position(s)",
            options=available_positions,
            default=available_positions,
            key=f"vorp_pos_multiselect_{'ind' if is_ind else 'tact'}",
            help="Select one or multiple positions to analyze. Default includes all positions.",
        )

    target_positions = selected_positions if selected_positions else available_positions
    if len(target_positions) == len(available_positions):
        pos_label_display = "All Positions"
    elif len(target_positions) <= 2:
        pos_label_display = " & ".join(target_positions)
    else:
        pos_label_display = f"{len(target_positions)} Positions"

    with f_col3:
        view_mode = st.radio(
            "Aggregation Scope",
            options=["All-Time Career", "Individual Seasons"],
            index=0,
            key="vorp_view_mode",
        )

    is_by_season = view_mode == "Individual Seasons"

    with f_col4:
        rank_metric = st.selectbox(
            "Rank By Metric",
            options=[
                "% Better Than Replacement (% vs Rep)",
                "Total I-VORP (Cumulative)",
                "Total Impact",
                "Average I-VORP / Innings",
            ],
            index=0,
            key="vorp_rank_metric",
        )

    # Filter row 2: Sliders for cuts
    s_col1, s_col2, s_col3 = st.columns(3)

    with s_col1:
        default_min_inn = 7 if is_by_season else 15
        min_inn = st.slider(
            f"Minimum Innings ({pos_label_display})",
            min_value=1,
            max_value=60 if not is_by_season else 20,
            value=default_min_inn,
            key="vorp_min_inn_slider",
        )

    with s_col2:
        st.markdown("**Sort Order**")
        vorp_sort_asc = st.toggle(
            "Sort Ascending (Lowest First)",
            value=False,
            key="vorp_sort_asc",
            help="Toggle between descending (highest ranked first) and ascending (lowest ranked first) order.",
        )

    with s_col3:
        top_n_vorp = st.slider(
            "Number of Players/Seasons to Display",
            min_value=5,
            max_value=50,
            value=15,
            key="vorp_top_n_slider",
        )

    # Perform aggregation
    pos_data = df_filtered[df_filtered[pos_column].isin(target_positions)].copy()

    if pos_data.empty:
        st.warning(f"No records found for positions: {pos_label_display}")
    else:
        group_fields = ["Season", "Player_Clean"] if is_by_season else ["Player_Clean"]

        agg_pos = pos_data.groupby(group_fields).agg(
            Innings=(vorp_column, "count"),
            Runs=("Runs", "sum"),
            Balls=("Balls", "sum"),
            Total_Impact=("Batting_Impact", "sum"),
            Avg_Impact=("Batting_Impact", "mean"),
            Total_IVORP=(vorp_column, "sum"),
            Avg_IVORP=(vorp_column, "mean"),
            Total_Baseline=(base_column, "sum"),
        ).reset_index()

        agg_pos["SR"] = (agg_pos["Runs"] * 100 / agg_pos["Balls"].replace(0, np.nan)).round(2)
        agg_pos["Total_Impact"] = agg_pos["Total_Impact"].round(2)
        agg_pos["Total_IVORP"] = agg_pos["Total_IVORP"].round(2)
        agg_pos["Avg_IVORP"] = agg_pos["Avg_IVORP"].round(3)
        agg_pos["Avg_Impact"] = agg_pos["Avg_Impact"].round(3)
        agg_pos["Baseline_Avg"] = (agg_pos["Total_Baseline"] / agg_pos["Innings"]).round(3)
        agg_pos["Pct_Above_Rep"] = (
            (agg_pos["Total_IVORP"] / agg_pos["Total_Baseline"].replace(0, np.nan)) * 100
        ).round(1)

        # Apply filtering
        qualified_pos = agg_pos[agg_pos["Innings"] >= min_inn].copy()

        # Sort
        if "Total Impact" in rank_metric or "Batting Impact" in rank_metric:
            sort_target = "Total_Impact"
        elif "Cumulative" in rank_metric or "Total I-VORP" in rank_metric:
            sort_target = "Total_IVORP"
        elif "Average" in rank_metric:
            sort_target = "Avg_IVORP"
        else:
            sort_target = "Pct_Above_Rep"

        leaderboard_pos = qualified_pos.sort_values(by=sort_target, ascending=vorp_sort_asc).head(top_n_vorp).reset_index(drop=True)

        # Position KPI summary
        pos_rep_baseline = pos_data[base_column].median() if not pos_data.empty else 0.0
        top_name = leaderboard_pos.iloc[0]["Player_Clean"] if not leaderboard_pos.empty else "None"
        if is_by_season and not leaderboard_pos.empty:
            top_name = f"{top_name} ({leaderboard_pos.iloc[0]['Season']})"

        median_pct = qualified_pos["Pct_Above_Rep"].median() if not qualified_pos.empty else 0.0

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        kpi_col1.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Replacement Baseline</div>"
            f"<div class='metric-value'>{pos_rep_baseline:.3f}</div>"
            f"<div class='metric-sub'>Median Par across {pos_label_display}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        rank_badge_title = f"#1 ({'Lowest' if vorp_sort_asc else 'Highest'})"
        kpi_col2.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>{rank_badge_title}</div>"
            f"<div class='metric-value' style='font-size:1.35rem;'>{top_name}</div>"
            f"<div class='metric-sub'>Ranked by {rank_metric.split(' ')[0]}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        kpi_col3.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Median % vs Rep</div>"
            f"<div class='metric-value'>{median_pct:+.1f}%</div>"
            f"<div class='metric-sub'>Across {len(qualified_pos)} qualified batters</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        kpi_col4.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Qualified Batters</div>"
            f"<div class='metric-value'>{len(qualified_pos)}</div>"
            f"<div class='metric-sub'>Min {min_inn} innings threshold</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if leaderboard_pos.empty:
            st.info(f"No batters met the criteria (Min {min_inn} Innings). Try relaxing the cutoff.")
        else:
            # Bar Chart of Top Performers
            plot_df = leaderboard_pos.copy()
            if is_by_season:
                plot_df["Label"] = plot_df["Player_Clean"] + " (" + plot_df["Season"].astype(str) + ")"
            else:
                plot_df["Label"] = plot_df["Player_Clean"]

            chart_prefix = "Lowest" if vorp_sort_asc else "Top"
            chart_order_tag = " [Ascending]" if vorp_sort_asc else ""
            fig_pos = px.bar(
                plot_df,
                x=sort_target,
                y="Label",
                orientation="h",
                color="Pct_Above_Rep" if sort_target != "Pct_Above_Rep" else "Total_IVORP",
                color_continuous_scale=["#1d7a6d", "#e4572e"],
                hover_data=["Innings", "Runs", "SR", "Total_Impact", "Avg_Impact", "Total_IVORP", "Pct_Above_Rep"],
                labels={
                    sort_target: rank_metric,
                    "Label": "Batter",
                    "Total_Impact": "Total Impact",
                    "Pct_Above_Rep": "% vs Rep",
                    "Total_IVORP": "Total I-VORP",
                },
                title=f"{chart_prefix} {len(plot_df)} ({pos_label_display}, {view_mode}) Ranked by {rank_metric}{chart_order_tag}",
            )
            fig_pos.update_layout(
                height=max(400, len(plot_df) * 26),
                yaxis=dict(autorange="reversed"),
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_pos, use_container_width=True)

            # Scatter Plot 1: Innings vs Total I-VORP
            scatter_vorp = px.scatter(
                qualified_pos,
                x="Innings",
                y="Total_IVORP",
                size="Runs",
                color="Pct_Above_Rep",
                hover_name="Player_Clean",
                hover_data=["Season", "Runs", "SR", "Total_Impact", "Avg_Impact", "Pct_Above_Rep"] if is_by_season else ["Runs", "SR", "Total_Impact", "Avg_Impact", "Pct_Above_Rep"],
                color_continuous_scale=["#1d7a6d", "#e4572e"],
                title=f"Innings vs Total I-VORP ({pos_label_display}) (Bubble Size = Runs, Color = % vs Rep)",
                labels={
                    "Total_IVORP": "Total I-VORP",
                    "Innings": "Innings Batted",
                    "Pct_Above_Rep": "% vs Rep",
                    "Total_Impact": "Total Impact",
                    "Avg_Impact": "Avg Impact",
                    "Runs": "Runs",
                },
            )
            scatter_vorp.update_layout(height=420)
            st.plotly_chart(scatter_vorp, use_container_width=True)

            # Scatter Plot 2: Innings vs Total Batting Impact (under innings vs ivorp)
            scatter_impact = px.scatter(
                qualified_pos,
                x="Innings",
                y="Total_Impact",
                size="Runs",
                color="Avg_Impact",
                hover_name="Player_Clean",
                hover_data=["Season", "Runs", "SR", "Total_IVORP", "Avg_Impact", "Pct_Above_Rep"] if is_by_season else ["Runs", "SR", "Total_IVORP", "Avg_Impact", "Pct_Above_Rep"],
                color_continuous_scale=["#1d7a6d", "#e4572e"],
                title=f"Innings vs Total Batting Impact ({pos_label_display}) (Bubble Size = Runs, Color = Avg Impact)",
                labels={
                    "Total_Impact": "Total Batting Impact",
                    "Innings": "Innings Batted",
                    "Avg_Impact": "Avg Impact / Inning",
                    "Total_IVORP": "Total I-VORP",
                    "Pct_Above_Rep": "% vs Rep",
                    "Runs": "Runs",
                },
            )
            scatter_impact.update_layout(height=420)
            st.plotly_chart(scatter_impact, use_container_width=True)

            # Clean Centered Table
            st.markdown(f"#### 📋 Leaderboard Table: {pos_label_display} ({view_mode})")
            table_view = leaderboard_pos.copy()
            table_view.insert(0, "Rank", range(1, len(table_view) + 1))

            col_order = ["Rank"]
            if is_by_season:
                col_order.append("Season")
            col_order.extend([
                "Player_Clean",
                "Innings",
                "Runs",
                "Balls",
                "SR",
                "Total_Impact",
                "Avg_Impact",
                "Baseline_Avg",
                "Total_IVORP",
                "Avg_IVORP",
                "Pct_Above_Rep",
            ])

            table_view = table_view[col_order].rename(columns={
                "Player_Clean": "Player",
                "Total_Impact": "Total Impact",
                "Avg_Impact": "Avg Impact",
                "Baseline_Avg": "Rep Base",
                "Total_IVORP": "Total I-VORP",
                "Avg_IVORP": "Avg I-VORP",
                "Pct_Above_Rep": "% vs Rep",
            })

            table_view["Innings"] = table_view["Innings"].astype(int)
            table_view["Runs"] = table_view["Runs"].fillna(0).astype(int)
            table_view["Balls"] = table_view["Balls"].fillna(0).astype(int)

            render_table(
                center_table(
                    table_view,
                    format_map={
                        "SR": "{:.1f}",
                        "Total Impact": "{:.2f}",
                        "Avg Impact": "{:.3f}",
                        "Rep Base": "{:.3f}",
                        "Total I-VORP": "{:+.2f}",
                        "Avg I-VORP": "{:+.3f}",
                        "% vs Rep": "{:+.1f}%",
                    },
                    hide_index=True,
                    small_cols=[0, 1] if is_by_season else [0],
                )
            )


# =========================================================
# TAB 3: PLAYER VORP PROFILER (MULTI-POSITION BREAKDOWN)
# =========================================================
with tab_profiler:
    st.subheader("👤 Player VORP Multi-Position Profiler")
    st.caption("Deep dive into any player's career versatility, positional impact, and surplus value over replacement.")

    all_players = sorted(df_filtered["Player_Clean"].unique().tolist())
    default_player_idx = all_players.index("Virat Kohli") if "Virat Kohli" in all_players else 0

    selected_player = st.selectbox(
        "Search or Select Player",
        options=all_players,
        index=default_player_idx,
        key="profiler_player_select",
    )

    player_records = df_filtered[df_filtered["Player_Clean"] == selected_player].copy()

    if player_records.empty:
        st.info("No records found for this player in selected seasons.")
    else:
        # Career Summary Cards
        p_inn = len(player_records)
        p_runs = int(player_records["Runs"].sum())
        p_balls = int(player_records["Balls"].sum())
        p_sr = (p_runs * 100 / p_balls) if p_balls > 0 else 0.0
        p_impact_total = player_records["Batting_Impact"].sum()
        p_impact_avg = player_records["Batting_Impact"].mean()
        p_vorp_ind = player_records["IVORP_Individual"].sum()
        p_base_ind = player_records["Baseline_Impact_Ind"].sum()
        p_pct_ind = (p_vorp_ind / p_base_ind * 100) if p_base_ind > 0 else 0.0
        primary_pos = player_records["Pos_Individual"].mode().iloc[0] if not player_records.empty else "N/A"

        pc1, pc2, pc3, pc4, pc5, pc6 = st.columns(6, gap="small")
        pc1.markdown(
            f"<div class='metric-card metric-card-compact' title='Career Innings: {p_inn}'>"
            f"<div class='metric-title'>Career Innings</div>"
            f"<div class='metric-value'>{p_inn}</div>"
            f"<div class='metric-sub'>{p_runs:,} runs ({p_sr:.1f} SR)</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        pc2.markdown(
            f"<div class='metric-card metric-card-compact' title='Primary Slot: {primary_pos}'>"
            f"<div class='metric-title'>Primary Slot</div>"
            f"<div class='metric-value' style='font-size:1.35rem;'>{primary_pos}</div>"
            f"<div class='metric-sub'>Most frequent batting slot</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        pc3.markdown(
            f"<div class='metric-card metric-card-compact' title='Total Batting Impact: {p_impact_total:.2f}'>"
            f"<div class='metric-title'>Total Impact</div>"
            f"<div class='metric-value'>{p_impact_total:.2f}</div>"
            f"<div class='metric-sub'>Cumulative batting impact</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        pc4.markdown(
            f"<div class='metric-card metric-card-compact' title='Total I-VORP (Ind): {p_vorp_ind:+.2f}'>"
            f"<div class='metric-title'>Total I-VORP (Ind)</div>"
            f"<div class='metric-value'>{p_vorp_ind:+.2f}</div>"
            f"<div class='metric-sub'>Cumulative value vs rep</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        pc5.markdown(
            f"<div class='metric-card metric-card-compact' title='% vs Rep (Overall): {p_pct_ind:+.1f}%'>"
            f"<div class='metric-title'>% vs Rep (Overall)</div>"
            f"<div class='metric-value'>{p_pct_ind:+.1f}%</div>"
            f"<div class='metric-sub'>Relative surplus value</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        pc6.markdown(
            f"<div class='metric-card metric-card-compact' title='Avg Impact: {p_impact_avg:.3f}'>"
            f"<div class='metric-title'>Avg Impact</div>"
            f"<div class='metric-value'>{p_impact_avg:.3f}</div>"
            f"<div class='metric-sub'>Per inning (1.0 = match par)</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Multi-Position Breakdown tables via vorp.py
        ind_profile, tact_profile = vorp.get_player_vorp_profile(df_filtered, selected_player)

        # Side-by-side grouped bar chart: Player Impact vs Replacement Baseline across positions
        if not ind_profile.empty:
            st.markdown("#### 📊 Player Impact vs Replacement Baseline by Position")
            ind_profile_chart = ind_profile.copy()
            ind_profile_chart["Baseline_Avg"] = (ind_profile_chart["Total_Baseline"] / ind_profile_chart["Innings"]).round(3)

            comp_df = pd.melt(
                ind_profile_chart,
                id_vars=["Pos_Individual"],
                value_vars=["Avg_Impact", "Baseline_Avg"],
                var_name="Metric",
                value_name="Impact Rating",
            )
            comp_df["Metric"] = comp_df["Metric"].map({
                "Avg_Impact": f"{selected_player}'s Avg Impact",
                "Baseline_Avg": "Replacement Baseline",
            })

            fig_comp = px.bar(
                comp_df,
                x="Pos_Individual",
                y="Impact Rating",
                color="Metric",
                barmode="group",
                color_discrete_map={
                    f"{selected_player}'s Avg Impact": "#1d7a6d",
                    "Replacement Baseline": "#e4572e",
                },
                title=f"{selected_player}: Batting Impact vs Replacement Level Across Positions",
            )
            fig_comp.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_comp, use_container_width=True)

        # Display Positional Tables
        pt1, pt2 = st.columns(2)

        with pt1:
            st.markdown("##### 📌 Individual Positions Breakdown")
            if not ind_profile.empty:
                ind_view = ind_profile[[
                    "Pos_Individual", "Innings", "Runs", "SR", "Total_Impact", "Avg_Impact", "Total_IVORP", "Pct_Above_Rep"
                ]].rename(columns={
                    "Pos_Individual": "Position",
                    "Total_Impact": "Total Impact",
                    "Avg_Impact": "Avg Impact",
                    "Total_IVORP": "Total I-VORP",
                    "Pct_Above_Rep": "% vs Rep",
                })
                ind_view["Innings"] = ind_view["Innings"].astype(int)
                ind_view["Runs"] = ind_view["Runs"].fillna(0).astype(int)
                render_table(
                    center_table(
                        ind_view,
                        format_map={
                            "SR": "{:.1f}",
                            "Total Impact": "{:.2f}",
                            "Avg Impact": "{:.3f}",
                            "Total I-VORP": "{:+.2f}",
                            "% vs Rep": "{:+.1f}%",
                        },
                        hide_index=True,
                    )
                )

        with pt2:
            st.markdown("##### 🛡️ Tactical Orders Breakdown")
            if not tact_profile.empty:
                tact_view = tact_profile[[
                    "Pos_Tactical", "Innings", "Runs", "SR", "Total_Impact", "Avg_Impact", "Total_IVORP", "Pct_Above_Rep"
                ]].rename(columns={
                    "Pos_Tactical": "Tactical Slot",
                    "Total_Impact": "Total Impact",
                    "Avg_Impact": "Avg Impact",
                    "Total_IVORP": "Total I-VORP",
                    "Pct_Above_Rep": "% vs Rep",
                })
                tact_view["Innings"] = tact_view["Innings"].astype(int)
                tact_view["Runs"] = tact_view["Runs"].fillna(0).astype(int)
                render_table(
                    center_table(
                        tact_view,
                        format_map={
                            "SR": "{:.1f}",
                            "Total Impact": "{:.2f}",
                            "Avg Impact": "{:.3f}",
                            "Total I-VORP": "{:+.2f}",
                            "% vs Rep": "{:+.1f}%",
                        },
                        hide_index=True,
                    )
                )

        # Career Year-by-Year Progression
        st.markdown("#### 📈 Season-by-Season I-VORP Trajectory")
        season_prog = player_records.groupby("Season").agg(
            Innings=("IVORP_Individual", "count"),
            Runs=("Runs", "sum"),
            Balls=("Balls", "sum"),
            Total_Impact=("Batting_Impact", "sum"),
            Avg_Impact=("Batting_Impact", "mean"),
            Total_IVORP=("IVORP_Individual", "sum"),
            Total_Base=("Baseline_Impact_Ind", "sum"),
        ).reset_index()

        season_prog["SR"] = (season_prog["Runs"] * 100 / season_prog["Balls"].replace(0, np.nan)).round(2)
        season_prog["Total_Impact"] = season_prog["Total_Impact"].round(2)
        season_prog["Avg_Impact"] = season_prog["Avg_Impact"].round(3)
        season_prog["Total_IVORP"] = season_prog["Total_IVORP"].round(2)
        season_prog["Pct_Above_Rep"] = (
            (season_prog["Total_IVORP"] / season_prog["Total_Base"].replace(0, np.nan)) * 100
        ).round(1)

        fig_prog = px.line(
            season_prog,
            x="Season",
            y="Total_IVORP",
            markers=True,
            hover_data=["Innings", "Runs", "SR", "Total_Impact", "Avg_Impact", "Pct_Above_Rep"],
            title=f"{selected_player}: Total I-VORP by Season",
            labels={"Total_IVORP": "Total I-VORP", "Season": "IPL Season"},
        )
        fig_prog.update_traces(line_color="#1d7a6d", line_width=3, marker=dict(size=8, color="#e4572e"))
        fig_prog.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
        fig_prog.update_xaxes(dtick=1)
        st.plotly_chart(fig_prog, use_container_width=True)

        # Season vs % Better Than Replacement Bar Graph
        st.markdown("#### 📊 Season-by-Season % Better Than Replacement (% vs Rep)")
        st.caption("Relative surplus value generated over positional replacement baselines by season ($0\\% = \\text{Replacement Par}$).")

        season_prog["Status"] = np.where(season_prog["Pct_Above_Rep"] >= 0, "Above Replacement", "Below Replacement")
        season_prog["Pct_Text"] = season_prog["Pct_Above_Rep"].apply(lambda v: f"{v:+.1f}%" if pd.notnull(v) else "")
        season_prog["Season_Str"] = season_prog["Season"].astype(str)

        fig_pct_prog = px.bar(
            season_prog,
            x="Season_Str",
            y="Pct_Above_Rep",
            color="Status",
            color_discrete_map={
                "Above Replacement": "#1d7a6d",
                "Below Replacement": "#e4572e",
            },
            text="Pct_Text",
            custom_data=["Innings", "Runs", "SR", "Total_IVORP", "Total_Impact"],
            title=f"{selected_player}: % Better Than Replacement by Season",
            labels={
                "Season_Str": "IPL Season",
                "Pct_Above_Rep": "% vs Rep",
                "Status": "Status",
            },
        )
        fig_pct_prog.update_traces(
            textposition="outside",
            hovertemplate=(
                "<b>Season %{x}</b><br>"
                "% vs Rep: <b>%{y:+.1f}%</b><br>"
                "Innings: %{customdata[0]}<br>"
                "Runs: %{customdata[1]:,}<br>"
                "SR: %{customdata[2]:.1f}<br>"
                "Total I-VORP: %{customdata[3]:+.2f}<br>"
                "Total Impact: %{customdata[4]:.2f}<extra></extra>"
            ),
        )
        fig_pct_prog.add_hline(
            y=0,
            line_dash="dash",
            line_color="#718096",
            line_width=1.5,
            annotation_text="Replacement Par (0%)",
            annotation_position="bottom right",
            annotation_font_size=11,
            annotation_font_color="#718096",
        )
        fig_pct_prog.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="IPL Season",
            yaxis_title="% vs Replacement Baseline",
            legend_title_text="",
            uniformtext_minsize=8,
            uniformtext_mode="hide",
        )
        st.plotly_chart(fig_pct_prog, use_container_width=True)

        # Season vs Total Impact Graph at bottom
        st.markdown("#### 💥 Season-by-Season Total Batting Impact Trajectory")
        fig_impact_prog = px.line(
            season_prog,
            x="Season",
            y="Total_Impact",
            markers=True,
            hover_data=["Innings", "Runs", "SR", "Avg_Impact", "Total_IVORP", "Pct_Above_Rep"],
            title=f"{selected_player}: Total Batting Impact by Season",
            labels={"Total_Impact": "Total Batting Impact", "Season": "IPL Season"},
        )
        fig_impact_prog.update_traces(line_color="#e4572e", line_width=3, marker=dict(size=8, color="#1d7a6d"))
        fig_impact_prog.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
        fig_impact_prog.update_xaxes(dtick=1)
        st.plotly_chart(fig_impact_prog, use_container_width=True)


# =========================================================
# TAB 4: THE PANTHEON (ICONIC KNOCKS & MATCH-WINNERS)
# =========================================================
with tab_pantheon:
    st.subheader("🏆 The Pantheon: Iconic Knocks & Match-Winners")
    st.caption("Celebrating legendary masterclasses, solitary carry jobs, and high-velocity blitzkriegs across 19 IPL seasons.")

    sec_choice = st.radio(
        "Select Pantheon Hall",
        options=[
            "⚡ Greatest Single-Innings Knocks",
            "⚔️ Lone Warrior Carry Jobs (% Team Runs)",
            "🧨 High-Velocity Blitzkriegs (≤ 25 Balls)",
        ],
        horizontal=True,
        key="pantheon_category_radio",
    )

    if sec_choice == "⚡ Greatest Single-Innings Knocks":
        st.markdown("#### ⚡ The Greatest Single-Innings Knocks of All Time")
        st.caption("Pure era-adjusted batting impact index ($I = \\text{Vol} \\times \\text{Acc}$), normalized against match tempo and team scoring environments.")

        f_k1, f_k2, f_k3 = st.columns([1.5, 1.5, 1.2])
        with f_k1:
            pos_choice_k = st.selectbox(
                "Filter by Batting Slot",
                options=["All Positions", "Opener", "Number 3", "Number 4", "Number 5", "Number 6", "Number 7", "Number 8+"],
                key="knocks_pos_filter",
            )
        with f_k2:
            inn_context_k = st.selectbox(
                "Innings Context",
                options=["All Innings", "1st Innings (Setting Total)", "2nd Innings (Chasing)"],
                key="knocks_inn_context",
            )
        with f_k3:
            knocks_count = st.slider("Knocks to Display", min_value=10, max_value=100, value=25, key="knocks_count_slider")

        target_knocks = df_filtered.copy()
        if pos_choice_k != "All Positions":
            target_knocks = target_knocks[target_knocks["Pos_Individual"] == pos_choice_k]
        if inn_context_k == "1st Innings (Setting Total)":
            target_knocks = target_knocks[target_knocks["Innings"] == 1]
        elif inn_context_k == "2nd Innings (Chasing)":
            target_knocks = target_knocks[target_knocks["Innings"] == 2]

        top_knocks = target_knocks.sort_values(by="Batting_Impact", ascending=False).head(knocks_count).reset_index(drop=True)
        top_knocks.insert(0, "Rank", range(1, len(top_knocks) + 1))

        top_knocks_view = top_knocks[[
            "Rank", "Player_Clean", "Season", "Match", "Team", "Pos_Individual", "Runs", "Balls", "4s", "6s", "Strike_Rate", "Batting_Impact", "IVORP_Individual"
        ]].rename(columns={
            "Player_Clean": "Batter",
            "Pos_Individual": "Slot",
            "Strike_Rate": "SR",
            "Batting_Impact": "Impact Index",
            "IVORP_Individual": "I-VORP Surplus",
        })
        for col in ["Runs", "Balls", "4s", "6s"]:
            top_knocks_view[col] = pd.to_numeric(top_knocks_view[col], errors="coerce").fillna(0).astype(int)

        render_table(
            center_table(
                top_knocks_view,
                format_map={
                    "Runs": "{:.0f}",
                    "Balls": "{:.0f}",
                    "4s": "{:.0f}",
                    "6s": "{:.0f}",
                    "SR": "{:.1f}",
                    "Impact Index": "{:.3f}",
                    "I-VORP Surplus": "{:+.2f}",
                },
                hide_index=True,
                small_cols=[0, 2],
                wide_cols=[4],
            )
        )

    elif sec_choice == "⚔️ Lone Warrior Carry Jobs (% Team Runs)":
        st.markdown("#### ⚔️ Lone Warrior Carry Jobs (% of Team Total)")
        st.caption("The most dominant one-man army performances in IPL history where a single batter shouldered an extreme fraction of their team's runs.")

        f_l1, f_l2, f_l3 = st.columns([1.2, 1.4, 1.2])
        with f_l1:
            min_runs_lone = st.slider("Minimum Runs Scored", min_value=30, max_value=100, value=50, step=5, key="lone_min_runs")
        with f_l2:
            inn_context_l = st.selectbox(
                "Innings Context",
                options=["All Innings", "1st Innings (Setting Total)", "2nd Innings (Chasing)"],
                key="lone_inn_context",
            )
        with f_l3:
            lone_count = st.slider("Knocks to Display", min_value=10, max_value=50, value=25, key="lone_display_count")

        df_lone = df_filtered[df_filtered["Runs"] >= min_runs_lone].copy()
        df_lone["Calc_Pct_Team"] = (df_lone["Runs"] * 100 / df_lone["Team_Runs"].replace(0, np.nan)).round(1)

        if inn_context_l == "1st Innings (Setting Total)":
            df_lone = df_lone[df_lone["Innings"] == 1]
        elif inn_context_l == "2nd Innings (Chasing)":
            df_lone = df_lone[df_lone["Innings"] == 2]

        top_lone = df_lone.sort_values(by=["Calc_Pct_Team", "Batting_Impact"], ascending=[False, False]).head(lone_count).reset_index(drop=True)
        top_lone.insert(0, "Rank", range(1, len(top_lone) + 1))

        lone_view = top_lone[[
            "Rank", "Player_Clean", "Season", "Match", "Team", "Runs", "Balls", "Strike_Rate", "Team_Runs", "Calc_Pct_Team", "Batting_Impact"
        ]].rename(columns={
            "Player_Clean": "Batter",
            "Strike_Rate": "SR",
            "Team_Runs": "Team Total",
            "Calc_Pct_Team": "% Team Runs",
            "Batting_Impact": "Impact Index",
        })
        for col in ["Runs", "Balls", "Team Total"]:
            lone_view[col] = pd.to_numeric(lone_view[col], errors="coerce").fillna(0).astype(int)

        render_table(
            center_table(
                lone_view,
                format_map={
                    "Runs": "{:.0f}",
                    "Balls": "{:.0f}",
                    "SR": "{:.1f}",
                    "Team Total": "{:.0f}",
                    "% Team Runs": "{:.1f}%",
                    "Impact Index": "{:.3f}",
                },
                hide_index=True,
                small_cols=[0, 2],
                wide_cols=[4],
            )
        )

    elif sec_choice == "🧨 High-Velocity Blitzkriegs (≤ 25 Balls)":
        st.markdown("#### 🧨 High-Velocity Blitzkriegs (≤ 25 Deliveries Faced)")
        st.caption("Maximum impact in limited deliveries: celebrating the most devastating cameos in IPL history capped at 25 balls.")

        f_b1, f_b2, f_b3 = st.columns([1.2, 1.4, 1.2])
        with f_b1:
            max_balls_blitz = st.slider("Maximum Balls Faced", min_value=5, max_value=25, value=25, key="blitz_max_balls")
        with f_b2:
            rank_blitz_metric = st.selectbox(
                "Rank By",
                options=["Batting Impact", "Strike Rate", "Runs Scored"],
                key="blitz_rank_metric",
            )
        with f_b3:
            blitz_count = st.slider("Knocks to Display", min_value=10, max_value=50, value=25, key="blitz_count_slider")

        df_blitz = df_filtered[(df_filtered["Balls"] <= max_balls_blitz) & (df_filtered["Balls"] > 0)].copy()

        if rank_blitz_metric == "Batting Impact":
            sort_b = "Batting_Impact"
        elif rank_blitz_metric == "Strike Rate":
            sort_b = "Strike_Rate"
        else:
            sort_b = "Runs"

        top_blitz = df_blitz.sort_values(by=[sort_b, "Batting_Impact"], ascending=[False, False]).head(blitz_count).reset_index(drop=True)
        top_blitz.insert(0, "Rank", range(1, len(top_blitz) + 1))

        blitz_view = top_blitz[[
            "Rank", "Player_Clean", "Season", "Match", "Team", "Pos_Individual", "Runs", "Balls", "4s", "6s", "Strike_Rate", "Batting_Impact"
        ]].rename(columns={
            "Player_Clean": "Batter",
            "Pos_Individual": "Slot",
            "Strike_Rate": "SR",
            "Batting_Impact": "Impact Index",
        })
        for col in ["Runs", "Balls", "4s", "6s"]:
            blitz_view[col] = pd.to_numeric(blitz_view[col], errors="coerce").fillna(0).astype(int)

        render_table(
            center_table(
                blitz_view,
                format_map={
                    "Runs": "{:.0f}",
                    "Balls": "{:.0f}",
                    "4s": "{:.0f}",
                    "6s": "{:.0f}",
                    "SR": "{:.1f}",
                    "Impact Index": "{:.3f}",
                },
                hide_index=True,
                small_cols=[0, 2],
                wide_cols=[4],
            )
        )


