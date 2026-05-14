from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, Dict, Optional

import pandas as pd

from .common import (
    build_file_season_map,
    clean_player_name_strict,
    extract_team_runs_and_overs,
    overs_to_balls,
    positive_z_score_normalize,
)


def _build_player_data_for_match(
    df: pd.DataFrame,
    season: Optional[str],
    match_name: str,
) -> List[Dict[str, object]]:
    total_rows = df[df[0] == "TOTAL"]
    team_info = []
    for idx in total_rows.index:
        row = df.loc[idx]
        runs, overs = extract_team_runs_and_overs(row)
        if runs is not None and overs is not None:
            team_info.append((idx, runs, overs))

    total_match_runs = sum(info[1] for info in team_info) if team_info else 0
    total_match_balls = sum(overs_to_balls(info[2]) for info in team_info) if team_info else 0
    match_sr = (total_match_runs / total_match_balls) * 100 if total_match_balls > 0 else 0

    batting_indices = df[df[0] == "BATTING"].index.tolist()
    batting_block_counter = 0
    player_data: List[Dict[str, object]] = []

    for start in batting_indices:
        end_idx = df.loc[start:, 0][df.loc[start:, 0] == "Extras"]
        if end_idx.empty:
            continue
        end = end_idx.index[0]
        batting_block = df.loc[start + 1: end - 1]

        team_idx = min(batting_block_counter, len(team_info) - 1) if team_info else 0
        team_runs = team_info[team_idx][1] if team_info else 0
        team_overs = team_info[team_idx][2] if team_info else 0
        team_balls = overs_to_balls(team_overs) if team_overs else 0
        team_sr = (team_runs / team_balls) * 100 if team_balls > 0 else 0
        batting_block_counter += 1

        for _, row in batting_block.iterrows():
            name = row[0]
            if not isinstance(name, str) or name.strip() == "":
                continue
            try:
                runs = float(row[2])
                sr = float(row[6])
            except Exception:
                continue

            cleaned_name = clean_player_name_strict(name)
            if not cleaned_name:
                continue

            player_data.append({
                "Name": cleaned_name,
                "Runs": runs,
                "SR": sr,
                "SR_Team_SR": sr / team_sr if team_sr > 0 else 1.0,
                "Runs_Team_Runs": runs / team_runs if team_runs > 0 else 0.0,
                "SR_Match_SR": sr / match_sr if match_sr > 0 else 1.0,
                "Runs_Match_Runs": runs / total_match_runs if total_match_runs > 0 else 0.0,
                "Team_SR": team_sr,
                "Match": match_name,
                "Season": season,
            })

    return player_data


def _apply_impact_index(player_data: List[Dict[str, object]]) -> None:
    if not player_data:
        return

    sr_team_list = [p["SR_Team_SR"] for p in player_data]
    runs_team_list = [p["Runs_Team_Runs"] for p in player_data]
    sr_match_list = [p["SR_Match_SR"] for p in player_data]
    runs_match_list = [p["Runs_Match_Runs"] for p in player_data]

    norm_sr_team = positive_z_score_normalize(sr_team_list)
    norm_runs_team = positive_z_score_normalize(runs_team_list)
    norm_sr_match = positive_z_score_normalize(sr_match_list)
    norm_runs_match = positive_z_score_normalize(runs_match_list)

    for i, player in enumerate(player_data):
        metric1 = norm_sr_team[i] * norm_runs_team[i]
        metric2 = norm_sr_match[i] * norm_runs_match[i]
        impact = 0.40 * metric1 + 0.60 * metric2

        runs_ratio = player["Runs_Team_Runs"]
        sr_ratio = player["SR_Team_SR"]
        penalty = 0.0
        if runs_ratio > 0.15:
            base_penalty = 0.0
            if sr_ratio < 0.8:
                if sr_ratio <= 0.5:
                    base_penalty = 0.40
                else:
                    base_penalty = 0.10 + (0.8 - sr_ratio)

            if base_penalty > 0.0:
                runs_excess = min(runs_ratio, 0.40) - 0.15
                additional_penalty = min(runs_excess * 2.0, 0.50)
                base_reduction = 1.0 - base_penalty
                additional_reduction = 1.0 - additional_penalty
                penalty = 1.0 - (base_reduction * additional_reduction)

        adjusted_impact = impact * (1.0 - penalty)

        if player["Runs"] >= 50 and sr_ratio > 1.1:
            if player["Runs"] < 150:
                exponent = (player["Runs"] - 50) / 100
                multiplier = 2 ** exponent
            else:
                multiplier = 2.0
            adjusted_impact *= multiplier

        player["ImpactIndex"] = round(adjusted_impact, 4)


def match_impact_dataframe(
    df: pd.DataFrame,
    season_label: Optional[str],
    match_name: str,
) -> pd.DataFrame:
    player_data = _build_player_data_for_match(df, season_label, match_name)
    if not player_data:
        return pd.DataFrame()
    _apply_impact_index(player_data)
    return pd.DataFrame(player_data)


def load_innings_data(
    files: Iterable[Path],
    file_season_map: Optional[Dict[Path, Optional[str]]] = None,
) -> List[Dict[str, object]]:
    files_list = list(files)
    if not file_season_map:
        file_season_map = build_file_season_map(files_list)

    all_innings: List[Dict[str, object]] = []
    for file_path in files_list:
        season_label = file_season_map.get(file_path)
        try:
            xls = pd.ExcelFile(file_path)
        except Exception as exc:
            print(f"Could not open {file_path}: {exc}")
            continue

        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name, header=None)
            player_data = _build_player_data_for_match(df, season_label, sheet_name)
            if not player_data:
                continue
            _apply_impact_index(player_data)
            all_innings.extend(player_data)

    return all_innings


def top_innings(all_innings: List[Dict[str, object]], limit: int = 50) -> List[Dict[str, object]]:
    return sorted(all_innings, key=lambda x: x["ImpactIndex"], reverse=True)[:limit]


def top_player_seasons(all_innings: List[Dict[str, object]], limit: int = 50) -> List[Dict[str, object]]:
    if not all_innings:
        return []

    df_innings = pd.DataFrame(all_innings)
    seasonal_impact = df_innings.groupby(["Name", "Season"])['ImpactIndex'].sum().reset_index()
    top_seasons = seasonal_impact.sort_values(by="ImpactIndex", ascending=False)[:limit]
    return top_seasons.to_dict(orient="records")


def top_batsmen_cumulative(all_innings: List[Dict[str, object]], limit: int = 50) -> List[Dict[str, object]]:
    if not all_innings:
        return []

    df_innings = pd.DataFrame(all_innings)
    cumulative = df_innings.groupby("Name")["ImpactIndex"].sum().reset_index()
    top_batsmen = cumulative.sort_values(by="ImpactIndex", ascending=False)[:limit]
    return top_batsmen.to_dict(orient="records")


def top_batsmen_avg_impact(
    all_innings: List[Dict[str, object]],
    limit: int = 50,
    min_runs: int = 500,
) -> List[Dict[str, object]]:
    if not all_innings:
        return []

    df_innings = pd.DataFrame(all_innings)
    aggregated = df_innings.groupby("Name").agg({
        "ImpactIndex": "sum",
        "Runs": "sum",
        "Match": "count",
    }).reset_index()
    aggregated.columns = ["Name", "TotalImpactIndex", "TotalRuns", "InningsCount"]

    filtered = aggregated[aggregated["TotalRuns"] >= min_runs]
    if filtered.empty:
        return []

    filtered["AvgImpactPerMatch"] = filtered["TotalImpactIndex"] / filtered["InningsCount"]
    top_avg = filtered.sort_values(by="AvgImpactPerMatch", ascending=False)[:limit]
    return top_avg.to_dict(orient="records")


def batsman_of_match_counts(
    files: Iterable[Path],
    file_season_map: Optional[Dict[Path, Optional[str]]] = None,
) -> Dict[str, int]:
    files_list = list(files)
    if not file_season_map:
        file_season_map = build_file_season_map(files_list)

    counts: Dict[str, int] = defaultdict(int)
    for file_path in files_list:
        season_label = file_season_map.get(file_path)
        try:
            xls = pd.ExcelFile(file_path)
        except Exception as exc:
            print(f"Could not open {file_path}: {exc}")
            continue

        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name, header=None)
            player_data = _build_player_data_for_match(df, season_label, sheet_name)
            if not player_data:
                continue
            _apply_impact_index(player_data)
            best_batsman = max(player_data, key=lambda p: p["ImpactIndex"])
            counts[best_batsman["Name"]] += 1

    return counts


def top_players_per_match(
    file_path: Path,
    limit: int = 5,
    season_label: Optional[str] = None,
) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as exc:
        print(f"Could not open {file_path}: {exc}")
        return results

    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)
        player_data = _build_player_data_for_match(df, season_label, sheet_name)
        if not player_data:
            continue
        _apply_impact_index(player_data)
        top_players = sorted(player_data, key=lambda x: x["ImpactIndex"], reverse=True)[:limit]

        for rank, player in enumerate(top_players, start=1):
            results.append({
                "Match": sheet_name,
                "Season": season_label,
                "Rank": rank,
                "Name": player["Name"],
                "Runs": player["Runs"],
                "SR": player["SR"],
                "ImpactIndex": player["ImpactIndex"],
            })

    return results


def print_top_innings(rows: List[Dict[str, object]]) -> None:
    if not rows:
        print("No innings data found to display top performances.")
        return

    print("\n=== Top Impact Score Innings ===")
    for rank, inning in enumerate(rows, start=1):
        print(
            f"#{rank}: {inning['Name']} | Runs: {inning['Runs']} | SR: {inning['SR']} | "
            f"Impact Index: {inning['ImpactIndex']} | Match: {inning['Match']} | Season: {inning['Season']}"
        )


def print_top_seasons(rows: List[Dict[str, object]]) -> None:
    if not rows:
        print("No innings data found to display top individual seasons.")
        return

    print("\n=== Top Individual Seasons by Batsmen ===")
    for rank, row in enumerate(rows, start=1):
        print(
            f"#{rank}: {row['Name']} | Season: {row['Season']} | "
            f"Cumulative Impact Index: {round(row['ImpactIndex'], 4)}"
        )


def print_top_batsmen(rows: List[Dict[str, object]]) -> None:
    if not rows:
        print("No innings data found to display top batsmen by cumulative impact.")
        return

    print("\n=== Top Batsmen by Cumulative Impact Points ===")
    for rank, row in enumerate(rows, start=1):
        print(f"#{rank}: {row['Name']} | Cumulative Impact Index: {round(row['ImpactIndex'], 4)}")


def print_top_avg_batsmen(rows: List[Dict[str, object]], min_runs: int) -> None:
    if not rows:
        print(f"No batsmen found with at least {min_runs} runs.")
        return

    print("\n=== Top Batsmen by Average Impact Per Match ===")
    for rank, row in enumerate(rows, start=1):
        print(
            f"#{rank}: {row['Name']} | Innings: {row['InningsCount']} | "
            f"Average Impact Index Per Match: {round(row['AvgImpactPerMatch'], 4)}"
        )


def print_batsman_of_match(rows: List[Dict[str, object]], limit: int) -> None:
    if not rows:
        print("No batsman of match data found.")
        return

    print("\n=== Top Batsmen of the Match (by count) ===")
    for rank, row in enumerate(rows[:limit], start=1):
        print(f"{rank}. {row['Name']} - {row['Count']} awards")


def print_top_players_per_match(rows: List[Dict[str, object]]) -> None:
    if not rows:
        print("No match data found to display top players per match.")
        return

    current_match = None
    for row in rows:
        if row["Match"] != current_match:
            current_match = row["Match"]
            print(f"\n=== Match: {current_match} ===")
        print(
            f"#{row['Rank']}: {row['Name']} | Runs: {row['Runs']} | SR: {row['SR']} | "
            f"Impact Index: {row['ImpactIndex']}"
        )
