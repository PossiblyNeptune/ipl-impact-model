from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Dict, Optional, Tuple

import pandas as pd

from .common import clean_player_name_basic


def get_all_players_batting_stats_in_file(xls: pd.ExcelFile) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)
        batting_indices = df[df[0] == "BATTING"].index.tolist()

        for start in batting_indices:
            trailing = df.loc[start:, 0][df.loc[start:, 0] == "Extras"]
            if trailing.empty:
                continue
            end = trailing.index[0]

            batting_block = df.loc[start + 1: end - 1]
            for _, row in batting_block.iterrows():
                cell0 = row[0]
                if isinstance(cell0, str):
                    player_name = clean_player_name_basic(cell0)
                    if player_name:
                        rows.append({
                            "Match": sheet_name,
                            "Player": player_name,
                            "How Out": row[1] if len(row) > 1 else None,
                            "Runs": row[2] if len(row) > 2 else None,
                            "Balls": row[3] if len(row) > 3 else None,
                            "4s": row[4] if len(row) > 4 else None,
                            "6s": row[5] if len(row) > 5 else None,
                            "Strike Rate": row[6] if len(row) > 6 else None,
                        })

    return pd.DataFrame(rows)


def get_player_batting_stats_in_file(player_name: str, xls: pd.ExcelFile) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    name_lower = player_name.lower()

    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)
        batting_indices = df[df[0] == "BATTING"].index.tolist()

        for start in batting_indices:
            trailing = df.loc[start:, 0][df.loc[start:, 0] == "Extras"]
            if trailing.empty:
                continue
            end = trailing.index[0]

            batting_block = df.loc[start + 1: end - 1]
            for _, row in batting_block.iterrows():
                cell0 = row[0]
                if isinstance(cell0, str) and name_lower in cell0.lower():
                    rows.append({
                        "Match": sheet_name,
                        "PlayerCell": row[0],
                        "How Out": row[1] if len(row) > 1 else None,
                        "Runs": row[2] if len(row) > 2 else None,
                        "Balls": row[3] if len(row) > 3 else None,
                        "4s": row[4] if len(row) > 4 else None,
                        "6s": row[5] if len(row) > 5 else None,
                        "Strike Rate": row[6] if len(row) > 6 else None,
                        "% of Team Runs": row[7] if len(row) > 7 else None,
                    })

    return pd.DataFrame(rows)


def summarize_batting_df(df_innings: pd.DataFrame) -> Dict[str, object]:
    df = df_innings.copy()
    for col in ["Runs", "Balls", "4s", "6s", "Strike Rate"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    total_runs = df["Runs"].sum()
    total_balls = df["Balls"].sum()
    total_4s = df["4s"].sum()
    total_6s = df["6s"].sum()
    innings_played = len(df)

    not_outs = df["How Out"].astype(str).str.lower().str.contains("not out").sum()
    outs = innings_played - not_outs

    season_sr = round((total_runs / total_balls) * 100, 2) if total_balls > 0 else 0.0
    season_avg = round(total_runs / outs, 2) if outs > 0 else "N/A"

    return {
        "Innings": innings_played,
        "Not Outs": not_outs,
        "Runs": total_runs,
        "Balls": total_balls,
        "4s": total_4s,
        "6s": total_6s,
        "Strike Rate": season_sr,
        "Average": season_avg,
    }


def summarize_player_across_files(
    player_name: str,
    files: Iterable[Path],
    file_season_map: Optional[Dict[Path, Optional[str]]] = None,
) -> Tuple[List[Dict[str, object]], Optional[Dict[str, object]], pd.DataFrame]:
    season_summaries: List[Dict[str, object]] = []
    career_df = pd.DataFrame()

    for file_path in files:
        season_label = file_season_map.get(file_path) if file_season_map else None
        season_label = season_label or file_path.name

        try:
            xls = pd.ExcelFile(file_path)
        except Exception as exc:
            print(f"Could not open {file_path}: {exc}")
            continue

        df_season = get_player_batting_stats_in_file(player_name, xls)
        if df_season.empty:
            season_summaries.append({"Season": season_label, "HasData": False})
            continue

        summary = summarize_batting_df(df_season)
        summary["Season"] = season_label
        summary["HasData"] = True
        season_summaries.append(summary)
        career_df = pd.concat([career_df, df_season], ignore_index=True)

    career_summary = summarize_batting_df(career_df) if not career_df.empty else None
    return season_summaries, career_summary, career_df


def get_top_strike_rate(
    files: Iterable[Path],
    min_runs: int = 1000,
    limit: int = 20,
) -> pd.DataFrame:
    all_players_df = pd.DataFrame()

    for file_path in files:
        try:
            xls = pd.ExcelFile(file_path)
        except Exception as exc:
            print(f"Could not open {file_path}: {exc}")
            continue

        df_season_innings = get_all_players_batting_stats_in_file(xls)
        if df_season_innings.empty:
            continue

        all_players_df = pd.concat([all_players_df, df_season_innings], ignore_index=True)

    if all_players_df.empty:
        return pd.DataFrame()

    top_players_summary = []
    for player_name, player_df in all_players_df.groupby("Player"):
        summary = summarize_batting_df(player_df)
        summary["Player"] = player_name
        top_players_summary.append(summary)

    summary_df = pd.DataFrame(top_players_summary)
    qualified_df = summary_df[summary_df["Runs"] >= min_runs]
    if qualified_df.empty:
        return pd.DataFrame()

    return qualified_df.sort_values(by="Strike Rate", ascending=False).head(limit)


def print_player_summaries(
    player_name: str,
    season_summaries: List[Dict[str, object]],
    career_summary: Optional[Dict[str, object]],
) -> None:
    for summary in season_summaries:
        print(f"\n{summary['Season']} Stats:")
        if not summary.get("HasData"):
            print("  (No batting data found.)")
            continue

        print(f"  Innings Played: {summary['Innings']}")
        print(f"  Not Outs: {summary['Not Outs']}")
        print(f"  Total Runs: {summary['Runs']}")
        print(f"  Total Balls: {summary['Balls']}")
        print(f"  Total 4s: {summary['4s']}")
        print(f"  Total 6s: {summary['6s']}")
        print(f"  Strike Rate: {summary['Strike Rate']}")
        print(f"  Batting Average: {summary['Average']}")

    if career_summary:
        print("\nCombined Career Batting Summary:")
        print(f"  Innings Played: {career_summary['Innings']}")
        print(f"  Not Outs: {career_summary['Not Outs']}")
        print(f"  Total Runs: {career_summary['Runs']}")
        print(f"  Total Balls: {career_summary['Balls']}")
        print(f"  Total 4s: {career_summary['4s']}")
        print(f"  Total 6s: {career_summary['6s']}")
        print(f"  Strike Rate: {career_summary['Strike Rate']}")
        print(f"  Batting Average: {career_summary['Average']}")
    else:
        print(f"\nNo batting data found at all for {player_name}.")


def print_top_strike_rate(top_df: pd.DataFrame, min_runs: int) -> None:
    if top_df.empty:
        print(f"\nNo players found with at least {min_runs} runs.")
        return

    print(f"\nTop Players by Strike Rate (Minimum {min_runs} Runs):")
    print("=" * 60)
    for _, row in top_df.iterrows():
        print(f"Player: {row['Player']}")
        print(f"  Innings Played: {row['Innings']}")
        print(f"  Total Runs: {row['Runs']}")
        print(f"  Batting Average: {row['Average']}")
        print(f"  Strike Rate: {row['Strike Rate']}")
        print(f"  Total 4s: {row['4s']}")
        print(f"  Total 6s: {row['6s']}")
        print("-" * 60)
