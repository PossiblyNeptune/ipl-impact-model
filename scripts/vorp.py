from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .common import REPO_ROOT

CSV_DIR = REPO_ROOT / "scorecards_csv" / "results"
BATTING_WITH_IMPACT_CSV = CSV_DIR / "all_batting_with_impact.csv"
BATTING_WITH_VORP_CSV = CSV_DIR / "all_batting_with_vorp.csv"


def map_individual_position(order: int) -> str:
    """
    Scheme 1: Individual positions with 1 & 2 clubbed as Opener.
    """
    if order in (1, 2):
        return "Opener"
    elif order == 3:
        return "Number 3"
    elif order == 4:
        return "Number 4"
    elif order == 5:
        return "Number 5"
    elif order == 6:
        return "Number 6"
    elif order == 7:
        return "Number 7"
    else:
        return "Number 8+"


def map_tactical_position(order: int) -> str:
    """
    Scheme 2: Broad tactical orders:
      - Top Order: 1, 2, 3
      - Middle Order: 4, 5
      - Finisher: 6, 7
      - Lower Order: 8+
    """
    if order in (1, 2, 3):
        return "Top Order"
    elif order in (4, 5):
        return "Middle Order"
    elif order in (6, 7):
        return "Finisher"
    else:
        return "Lower Order"


def load_and_enrich_vorp_data(
    input_csv: Path = BATTING_WITH_IMPACT_CSV,
    replacement_quantile: float = 0.25,
) -> pd.DataFrame:
    """
    Loads batting data with impact, assigns both position schemes,
    computes era- and position-specific replacement baselines,
    and derives I-VORP for both schemes.
    """
    if not input_csv.exists():
        raise FileNotFoundError(f"Source file {input_csv} not found. Run 'python -m scripts.cli convert-csv' first.")

    df = pd.read_csv(input_csv)

    # 1. Map Position Schemes
    df["Pos_Individual"] = df["Batting_Order"].apply(map_individual_position)
    df["Pos_Tactical"] = df["Batting_Order"].apply(map_tactical_position)

    # 2. Compute Scheme 1: Individual Position Baselines
    # Standard sabermetric replacement definition:
    # Evaluate players with reasonable playing time (>= 3 innings at slot in season)
    # The replacement baseline is the 20th percentile of those player-season averages (~bench/fringe player)
    ps_ind = (
        df.groupby(["Season", "Player_Clean", "Pos_Individual"])
        .agg(Innings=("Batting_Impact", "count"), Avg_Impact=("Batting_Impact", "mean"))
        .reset_index()
    )
    qual_ind = ps_ind[ps_ind["Innings"] >= 3]
    base_ind = (
        qual_ind.groupby(["Season", "Pos_Individual"])["Avg_Impact"]
        .quantile(0.20)
        .reset_index()
        .rename(columns={"Avg_Impact": "Baseline_Impact_Ind"})
    )
    global_fallbacks_ind = qual_ind.groupby("Pos_Individual")["Avg_Impact"].quantile(0.20)

    df = df.merge(base_ind, on=["Season", "Pos_Individual"], how="left")
    df["Baseline_Impact_Ind"] = df["Baseline_Impact_Ind"].fillna(df["Pos_Individual"].map(global_fallbacks_ind)).round(4)
    df["IVORP_Individual"] = (df["Batting_Impact"] - df["Baseline_Impact_Ind"]).round(4)
    df["Pct_Above_Rep_Ind"] = (
        (df["IVORP_Individual"] / df["Baseline_Impact_Ind"].replace(0, np.nan)) * 100
    ).round(1)

    # 3. Compute Scheme 2: Tactical Position Baselines
    ps_tact = (
        df.groupby(["Season", "Player_Clean", "Pos_Tactical"])
        .agg(Innings=("Batting_Impact", "count"), Avg_Impact=("Batting_Impact", "mean"))
        .reset_index()
    )
    qual_tact = ps_tact[ps_tact["Innings"] >= 3]
    base_tact = (
        qual_tact.groupby(["Season", "Pos_Tactical"])["Avg_Impact"]
        .quantile(0.20)
        .reset_index()
        .rename(columns={"Avg_Impact": "Baseline_Impact_Tact"})
    )
    global_fallbacks_tact = qual_tact.groupby("Pos_Tactical")["Avg_Impact"].quantile(0.20)

    df = df.merge(base_tact, on=["Season", "Pos_Tactical"], how="left")
    df["Baseline_Impact_Tact"] = df["Baseline_Impact_Tact"].fillna(df["Pos_Tactical"].map(global_fallbacks_tact)).round(4)
    df["IVORP_Tactical"] = (df["Batting_Impact"] - df["Baseline_Impact_Tact"]).round(4)
    df["Pct_Above_Rep_Tact"] = (
        (df["IVORP_Tactical"] / df["Baseline_Impact_Tact"].replace(0, np.nan)) * 100
    ).round(1)

    return df


def get_position_leaderboard(
    df: pd.DataFrame,
    position: str,
    scheme: str = "individual",
    season: Optional[int] = None,
    min_innings: int = 15,
    min_pct_above_rep: Optional[float] = None,
    sort_by: str = "total_ivorp",
    group_by_season: bool = False,
    limit: int = 20,
) -> pd.DataFrame:
    """
    Ranks players by Total I-VORP or % vs Rep at a specific position.
    Can aggregate by career (group_by_season=False) or individual player-seasons (group_by_season=True).
    """
    is_ind = scheme.lower().startswith("ind")
    col_pos = "Pos_Individual" if is_ind else "Pos_Tactical"
    col_vorp = "IVORP_Individual" if is_ind else "IVORP_Tactical"
    col_base = "Baseline_Impact_Ind" if is_ind else "Baseline_Impact_Tact"

    filtered = df.copy()
    if season is not None:
        filtered = filtered[filtered["Season"] == season]

    # Normalize search match for position
    pos_lower = position.strip().lower()
    valid_positions = filtered[col_pos].unique()
    target_pos = None
    for p in valid_positions:
        if p.lower() == pos_lower or pos_lower in p.lower():
            target_pos = p
            break

    if not target_pos:
        available = ", ".join(sorted(valid_positions))
        raise ValueError(f"Position '{position}' not recognized. Available: {available}")

    pos_df = filtered[filtered[col_pos] == target_pos]

    group_cols = ["Season", "Player_Clean"] if group_by_season else ["Player_Clean"]

    agg_df = (
        pos_df.groupby(group_cols)
        .agg(
            Innings=(col_vorp, "count"),
            Runs=("Runs", "sum"),
            Balls=("Balls", "sum"),
            Avg_Impact=("Batting_Impact", "mean"),
            Total_IVORP=(col_vorp, "sum"),
            Avg_IVORP=(col_vorp, "mean"),
            Total_Baseline=(col_base, "sum"),
        )
        .reset_index()
    )

    agg_df["SR"] = (agg_df["Runs"] * 100 / agg_df["Balls"]).round(2)
    agg_df["Total_IVORP"] = agg_df["Total_IVORP"].round(2)
    agg_df["Avg_IVORP"] = agg_df["Avg_IVORP"].round(3)
    agg_df["Avg_Impact"] = agg_df["Avg_Impact"].round(3)
    agg_df["Pct_Above_Rep"] = (
        (agg_df["Total_IVORP"] / agg_df["Total_Baseline"].replace(0, np.nan)) * 100
    ).round(1)

    qualified = agg_df[agg_df["Innings"] >= min_innings]

    if min_pct_above_rep is not None:
        qualified = qualified[qualified["Pct_Above_Rep"] >= min_pct_above_rep]

    sort_col = "Total_IVORP"
    sort_key = sort_by.strip().lower()
    if "pct" in sort_key or "rep" in sort_key:
        sort_col = "Pct_Above_Rep"
    elif "avg" in sort_key:
        sort_col = "Avg_IVORP"

    return (
        qualified.sort_values(by=sort_col, ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def get_player_vorp_profile(
    df: pd.DataFrame,
    player_name: str,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns a player's I-VORP breakdown across:
      1. Individual Positions (Opener, No 3, No 4, etc.)
      2. Tactical Positions (Top Order, Middle Order, Finisher, Lower Order)
    """
    name_clean = player_name.strip().lower()
    matches = df[df["Player_Clean"].str.lower().str.contains(name_clean, na=False)]
    if matches.empty:
        # Fallback search on raw player column
        matches = df[df["Player"].str.lower().str.contains(name_clean, na=False)]

    if matches.empty:
        return pd.DataFrame(), pd.DataFrame()

    canonical_name = matches["Player_Clean"].mode().iloc[0]
    player_df = df[df["Player_Clean"] == canonical_name]

    # Scheme 1: Individual Positions
    ind_profile = (
        player_df.groupby("Pos_Individual")
        .agg(
            Innings=("IVORP_Individual", "count"),
            Runs=("Runs", "sum"),
            Balls=("Balls", "sum"),
            Total_Impact=("Batting_Impact", "sum"),
            Avg_Impact=("Batting_Impact", "mean"),
            Total_IVORP=("IVORP_Individual", "sum"),
            Avg_IVORP=("IVORP_Individual", "mean"),
            Total_Baseline=("Baseline_Impact_Ind", "sum"),
        )
        .reset_index()
    )
    ind_profile["SR"] = (ind_profile["Runs"] * 100 / ind_profile["Balls"].replace(0, np.nan)).round(2)
    ind_profile["Total_Impact"] = ind_profile["Total_Impact"].round(2)
    ind_profile["Avg_Impact"] = ind_profile["Avg_Impact"].round(3)
    ind_profile["Total_IVORP"] = ind_profile["Total_IVORP"].round(2)
    ind_profile["Avg_IVORP"] = ind_profile["Avg_IVORP"].round(3)
    ind_profile["Pct_Above_Rep"] = (
        (ind_profile["Total_IVORP"] / ind_profile["Total_Baseline"].replace(0, np.nan)) * 100
    ).round(1)

    # Order positions logically
    order_map = {"Opener": 1, "Number 3": 2, "Number 4": 3, "Number 5": 4, "Number 6": 5, "Number 7": 6, "Number 8+": 7}
    ind_profile["SortKey"] = ind_profile["Pos_Individual"].map(order_map)
    ind_profile = ind_profile.sort_values(by="SortKey").drop(columns=["SortKey"]).reset_index(drop=True)

    # Scheme 2: Tactical Positions
    tact_profile = (
        player_df.groupby("Pos_Tactical")
        .agg(
            Innings=("IVORP_Tactical", "count"),
            Runs=("Runs", "sum"),
            Balls=("Balls", "sum"),
            Total_Impact=("Batting_Impact", "sum"),
            Avg_Impact=("Batting_Impact", "mean"),
            Total_IVORP=("IVORP_Tactical", "sum"),
            Avg_IVORP=("IVORP_Tactical", "mean"),
            Total_Baseline=("Baseline_Impact_Tact", "sum"),
        )
        .reset_index()
    )
    tact_profile["SR"] = (tact_profile["Runs"] * 100 / tact_profile["Balls"].replace(0, np.nan)).round(2)
    tact_profile["Total_Impact"] = tact_profile["Total_Impact"].round(2)
    tact_profile["Avg_Impact"] = tact_profile["Avg_Impact"].round(3)
    tact_profile["Total_IVORP"] = tact_profile["Total_IVORP"].round(2)
    tact_profile["Avg_IVORP"] = tact_profile["Avg_IVORP"].round(3)
    tact_profile["Pct_Above_Rep"] = (
        (tact_profile["Total_IVORP"] / tact_profile["Total_Baseline"].replace(0, np.nan)) * 100
    ).round(1)

    tact_order_map = {"Top Order": 1, "Middle Order": 2, "Finisher": 3, "Lower Order": 4}
    tact_profile["SortKey"] = tact_profile["Pos_Tactical"].map(tact_order_map)
    tact_profile = tact_profile.sort_values(by="SortKey").drop(columns=["SortKey"]).reset_index(drop=True)

    return ind_profile, tact_profile


def print_leaderboard(leader_df: pd.DataFrame, title: str) -> None:
    if leader_df.empty:
        print(f"No players found for: {title}")
        return

    has_season = "Season" in leader_df.columns
    print(f"\n=== {title} ===")
    if has_season:
        print(f"{'Rank':<5} {'Season':<8} {'Player':<22} {'Innings':<8} {'Runs':<7} {'SR':<7} {'Avg Impact':<12} {'Total I-VORP':<14} {'Avg I-VORP':<11} {'% vs Rep':<11}")
        print("-" * 115)
        for rank, row in enumerate(leader_df.itertuples(), start=1):
            pct_str = f"{row.Pct_Above_Rep:+,.1f}%" if pd.notna(row.Pct_Above_Rep) else "N/A"
            print(
                f"{rank:<5} {row.Season:<8} {row.Player_Clean:<22} {int(row.Innings):<8} {int(row.Runs):<7} "
                f"{row.SR:<7.1f} {row.Avg_Impact:<12.3f} {row.Total_IVORP:<+14.2f} {row.Avg_IVORP:<+11.3f} {pct_str:<11}"
            )
    else:
        print(f"{'Rank':<5} {'Player':<22} {'Innings':<8} {'Runs':<7} {'SR':<7} {'Avg Impact':<12} {'Total I-VORP':<14} {'Avg I-VORP':<11} {'% vs Rep':<11}")
        print("-" * 105)
        for rank, row in enumerate(leader_df.itertuples(), start=1):
            pct_str = f"{row.Pct_Above_Rep:+,.1f}%" if pd.notna(row.Pct_Above_Rep) else "N/A"
            print(
                f"{rank:<5} {row.Player_Clean:<22} {int(row.Innings):<8} {int(row.Runs):<7} "
                f"{row.SR:<7.1f} {row.Avg_Impact:<12.3f} {row.Total_IVORP:<+14.2f} {row.Avg_IVORP:<+11.3f} {pct_str:<11}"
            )


def print_player_profile(player_name: str, ind_df: pd.DataFrame, tact_df: pd.DataFrame) -> None:
    if ind_df.empty and tact_df.empty:
        print(f"\nNo batting records found for: {player_name}")
        return

    print(f"\n=======================================================")
    print(f"  I-VORP Profile: {player_name}")
    print(f"=======================================================")

    print("\n[Scheme 1: Individual Position Breakdown]")
    print(f"{'Position':<15} {'Innings':<8} {'Runs':<7} {'SR':<7} {'Total I-VORP':<14} {'Avg I-VORP':<11} {'% vs Rep':<11}")
    print("-" * 78)
    for row in ind_df.itertuples():
        pct_str = f"{row.Pct_Above_Rep:+,.1f}%" if pd.notna(row.Pct_Above_Rep) else "N/A"
        print(
            f"{row.Pos_Individual:<15} {int(row.Innings):<8} {int(row.Runs):<7} {row.SR:<7.1f} "
            f"{row.Total_IVORP:<+14.2f} {row.Avg_IVORP:<+11.3f} {pct_str:<11}"
        )

    print("\n[Scheme 2: Tactical Order Breakdown (Top / Middle / Finisher)]")
    print(f"{'Tactical Slot':<15} {'Innings':<8} {'Runs':<7} {'SR':<7} {'Total I-VORP':<14} {'Avg I-VORP':<11} {'% vs Rep':<11}")
    print("-" * 78)
    for row in tact_df.itertuples():
        pct_str = f"{row.Pct_Above_Rep:+,.1f}%" if pd.notna(row.Pct_Above_Rep) else "N/A"
        print(
            f"{row.Pos_Tactical:<15} {int(row.Innings):<8} {int(row.Runs):<7} {row.SR:<7.1f} "
            f"{row.Total_IVORP:<+14.2f} {row.Avg_IVORP:<+11.3f} {pct_str:<11}"
        )


def export_vorp_csv(output_path: Path = BATTING_WITH_VORP_CSV) -> Path:
    """
    Generates and saves the master dataset with I-VORP columns.
    """
    df = load_and_enrich_vorp_data()
    df.to_csv(output_path, index=False)
    print(f"[SUCCESS] Exported enriched I-VORP dataset ({len(df)} rows) to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Position-Specific Impact VORP (I-VORP) Calculator")
    subparsers = parser.add_subparsers(dest="vorp_cmd", required=True)

    # Leaderboard subparser
    sub_lead = subparsers.add_parser("leaders", help="Position I-VORP leaderboard")
    sub_lead.add_argument("position", help="Position (e.g., Opener, 'Number 3', 'Middle Order', Finisher)")
    sub_lead.add_argument("--scheme", choices=["individual", "tactical"], default="individual", help="Position grouping scheme")
    sub_lead.add_argument("--season", type=int, default=None, help="Filter by season (e.g., 2022)")
    sub_lead.add_argument("--min-innings", type=int, default=15, help="Minimum innings cutoff")
    sub_lead.add_argument("--min-pct", type=float, default=None, help="Minimum %% vs Rep cutoff")
    sub_lead.add_argument("--sort-by", choices=["total_ivorp", "pct_above_rep", "avg_ivorp"], default="total_ivorp", help="Ranking metric")
    sub_lead.add_argument("--by-season", action="store_true", help="Rank individual player-seasons instead of career totals")
    sub_lead.add_argument("--limit", type=int, default=20, help="Number of players to show")

    # Player profile subparser
    sub_player = subparsers.add_parser("player", help="Player I-VORP multi-position profile")
    sub_player.add_argument("name", help="Player name (e.g., 'Virat Kohli', 'AB de Villiers')")

    # Export subparser
    sub_export = subparsers.add_parser("export", help="Export full CSV with I-VORP columns")
    sub_export.add_argument("--output", default=str(BATTING_WITH_VORP_CSV), help="Output CSV path")

    args = parser.parse_args()

    df_vorp = load_and_enrich_vorp_data()

    if args.vorp_cmd == "leaders":
        season_str = f"Season {args.season}" if args.season else ("Single Season" if args.by_season else "All-Time")
        metric_str = "% vs Rep" if "pct" in args.sort_by else "Total I-VORP"
        title = f"{season_str} Leaders by {metric_str}: {args.position} ({args.scheme.capitalize()} Scheme)"
        lb = get_position_leaderboard(
            df_vorp,
            position=args.position,
            scheme=args.scheme,
            season=args.season,
            min_innings=args.min_innings,
            min_pct_above_rep=args.min_pct,
            sort_by=args.sort_by,
            group_by_season=args.by_season,
            limit=args.limit,
        )
        print_leaderboard(lb, title)

    elif args.vorp_cmd == "player":
        ind_df, tact_df = get_player_vorp_profile(df_vorp, args.name)
        print_player_profile(args.name, ind_df, tact_df)

    elif args.vorp_cmd == "export":
        export_vorp_csv(Path(args.output))
