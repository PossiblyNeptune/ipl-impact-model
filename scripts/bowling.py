from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Dict, Optional

import pandas as pd

from .common import build_file_season_map


def convert_overs_to_balls(overs: object) -> int:
    if overs is None:
        return 0
    try:
        overs_value = float(overs)
    except Exception:
        return 0

    whole = int(overs_value)
    fraction = round((overs_value - whole) * 10)
    return whole * 6 + fraction


def convert_balls_to_overs(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def get_player_bowling_stats(player_name: str, files: Iterable[Path]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    name_lower = player_name.lower()

    for file_path in files:
        try:
            xls = pd.ExcelFile(file_path)
        except Exception as exc:
            print(f"Could not open {file_path}: {exc}")
            continue

        for sheet_name in xls.sheet_names:
            try:
                df = xls.parse(sheet_name, header=None)
                bowling_indices = df[df[0] == "BOWLING"].index.tolist()

                for start in bowling_indices:
                    end = start + 1
                    while end < len(df):
                        val = df.iloc[end, 0]
                        if pd.isna(val) or (isinstance(val, str) and val.isupper() and "BOWLING" not in val):
                            break
                        end += 1

                    bowling_df = df.iloc[start + 1: end]

                    for _, row in bowling_df.iterrows():
                        if isinstance(row[0], str) and name_lower in row[0].lower():
                            rows.append({
                                "File": file_path.name,
                                "Match": sheet_name,
                                "Player": row[0],
                                "Overs": row[1],
                                "Maidens": row[2],
                                "Runs Conceded": row[3],
                                "Wickets": row[4],
                                "Economy": row[5],
                                "% of Team Wickets": row[6] if len(row) > 6 else None,
                            })
            except Exception as exc:
                print(f"Error processing sheet {sheet_name} in {file_path}: {exc}")
                continue

    return pd.DataFrame(rows)


def summarize_bowling_df(bowling_df: pd.DataFrame) -> Dict[str, object]:
    df = bowling_df.copy()
    for col in ["Overs", "Maidens", "Runs Conceded", "Wickets", "Economy"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Balls Bowled"] = df["Overs"].apply(convert_overs_to_balls)

    total_balls = df["Balls Bowled"].sum()
    total_runs = df["Runs Conceded"].sum()
    total_wickets = df["Wickets"].sum()
    total_maidens = df["Maidens"].sum()
    matches_played = len(df)

    economy = round((total_runs / total_balls) * 6, 2) if total_balls > 0 else "N/A"
    avg = round(total_runs / total_wickets, 2) if total_wickets > 0 else "N/A"
    sr = round(total_balls / total_wickets, 2) if total_wickets > 0 else "N/A"

    return {
        "Matches": matches_played,
        "Overs": convert_balls_to_overs(total_balls),
        "Maidens": total_maidens,
        "Runs": total_runs,
        "Wickets": total_wickets,
        "Economy": economy,
        "Average": avg,
        "Strike Rate": sr,
    }


def summarize_bowling_by_season(
    player_name: str,
    files: Iterable[Path],
    file_season_map: Optional[Dict[Path, Optional[str]]] = None,
) -> Tuple[List[Dict[str, object]], Optional[Dict[str, object]], pd.DataFrame]:
    bowling_df = get_player_bowling_stats(player_name, files)
    if bowling_df.empty:
        return [], None, bowling_df

    if not file_season_map:
        file_season_map = build_file_season_map(files)

    bowling_df["Season"] = bowling_df["File"].map(
        {file_path.name: season for file_path, season in file_season_map.items()}
    )

    season_summaries: List[Dict[str, object]] = []
    for season, season_df in bowling_df.groupby("Season", dropna=False):
        summary = summarize_bowling_df(season_df)
        summary["Season"] = season or "Unknown"
        season_summaries.append(summary)

    career_summary = summarize_bowling_df(bowling_df)
    return season_summaries, career_summary, bowling_df


def print_bowling_summaries(
    player_name: str,
    season_summaries: List[Dict[str, object]],
    career_summary: Optional[Dict[str, object]],
) -> None:
    if not season_summaries:
        print(f"\nNo bowling data found for {player_name}.")
        return

    for summary in season_summaries:
        print(f"\n{summary['Season']} Stats:")
        print(f"Matches Played: {summary['Matches']}")
        print(f"Total Overs: {summary['Overs']}")
        print(f"Total Maidens: {summary['Maidens']}")
        print(f"Total Runs Conceded: {summary['Runs']}")
        print(f"Total Wickets: {summary['Wickets']}")
        print(f"Economy Rate: {summary['Economy']}")
        print(f"Bowling Average: {summary['Average']}")
        print(f"Bowling Strike Rate: {summary['Strike Rate']}")

    if career_summary:
        print("\nCombined Career Bowling Summary:")
        print(f"Matches Played: {career_summary['Matches']}")
        print(f"Total Overs: {career_summary['Overs']}")
        print(f"Total Maidens: {career_summary['Maidens']}")
        print(f"Total Runs Conceded: {career_summary['Runs']}")
        print(f"Total Wickets: {career_summary['Wickets']}")
        print(f"Overall Economy Rate: {career_summary['Economy']}")
        print(f"Bowling Average: {career_summary['Average']}")
        print(f"Bowling Strike Rate: {career_summary['Strike Rate']}")
