from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from .common import (
    BASE_DIR,
    RESULTS_DIR,
    ensure_dir,
    extract_team_runs_and_overs,
    overs_to_balls,
    positive_z_score_normalize,
)


def process_file(input_file: Path, output_file: Path) -> None:
    xls = pd.ExcelFile(input_file)
    writer = pd.ExcelWriter(output_file, engine="openpyxl")

    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)

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

            player_data = []
            for i, row in batting_block.iterrows():
                name = row[0]
                if not isinstance(name, str) or name.strip() == "":
                    continue
                try:
                    runs = float(row[2])
                    sr = float(row[6])
                except Exception:
                    continue

                player_data.append({
                    "index": i,
                    "Runs": runs,
                    "SR": sr,
                    "SR_Team_SR": sr / team_sr if team_sr > 0 else 1.0,
                    "Runs_Team_Runs": runs / team_runs if team_runs > 0 else 0.0,
                    "SR_Match_SR": sr / match_sr if match_sr > 0 else 1.0,
                    "Runs_Match_Runs": runs / total_match_runs if total_match_runs > 0 else 0.0,
                })

            if not player_data:
                continue

            norm_sr_team = positive_z_score_normalize([p["SR_Team_SR"] for p in player_data])
            norm_runs_team = positive_z_score_normalize([p["Runs_Team_Runs"] for p in player_data])
            norm_sr_match = positive_z_score_normalize([p["SR_Match_SR"] for p in player_data])
            norm_runs_match = positive_z_score_normalize([p["Runs_Match_Runs"] for p in player_data])

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
                        penalty = 1.0 - ((1.0 - base_penalty) * (1.0 - additional_penalty))

                impact *= (1.0 - penalty)

                if player["Runs"] >= 50 and sr_ratio > 1.1:
                    exponent = (player["Runs"] - 50) / 100 if player["Runs"] < 150 else 1
                    multiplier = 2 ** exponent if player["Runs"] < 150 else 2.0
                    impact *= multiplier

                df.at[player["index"], 8] = round(impact, 4)
                df.iat[start, 8] = "Batting Impact"

        df.to_excel(writer, sheet_name=sheet_name[:31], index=False, header=False)

    writer.close()


def add_batting_impact(
    input_files: Optional[Iterable[Path]] = None,
    input_dir: Path = BASE_DIR,
    output_dir: Path = RESULTS_DIR,
) -> List[Path]:
    output_dir = ensure_dir(output_dir)
    files = list(input_files) if input_files else sorted(input_dir.glob("IPL_Scorecards_*_to_*.xlsx"))
    output_files: List[Path] = []

    for file_path in files:
        output_path = output_dir / file_path.name.replace(".xlsx", "_with_impact.xlsx")
        process_file(file_path, output_path)
        output_files.append(output_path)
        print(f"✅ Done: {output_path}")

    return output_files


if __name__ == "__main__":
    add_batting_impact()
