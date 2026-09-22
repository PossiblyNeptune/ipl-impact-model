from __future__ import annotations

import argparse
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .common import (
    BASE_DIR,
    REPO_ROOT,
    RESULTS_DIR,
    build_file_season_map,
    clean_player_name_strict,
    ensure_dir,
    extract_team_runs_and_overs,
    overs_to_balls,
)
from .scorecard import infer_team_name

CSV_DIR = REPO_ROOT / "scorecards_csv"
CSV_BASE_DIR = CSV_DIR / "base"
CSV_RESULTS_DIR = CSV_DIR / "results"


def convert_excel_to_stacked_csv(excel_path: Path, csv_path: Path) -> int:
    """
    Direct 1-to-1 conversion of an Excel workbook containing multiple match sheets
    into a single stacked CSV file, preserving all raw data and sheet names.
    """
    xls = pd.ExcelFile(excel_path)
    sheet_dfs: List[pd.DataFrame] = []

    for sheet_name in xls.sheet_names:
        try:
            df = xls.parse(sheet_name, header=None)
            if df.empty:
                continue
            df.dropna(how="all", axis=1, inplace=True)
            df.insert(0, "Sheet_Name", sheet_name)
            sheet_dfs.append(df)
        except Exception as exc:
            print(f"  [Warning] Failed reading sheet {sheet_name} in {excel_path.name}: {exc}")

    if not sheet_dfs:
        return 0

    combined = pd.concat(sheet_dfs, ignore_index=True)
    combined.to_csv(csv_path, index=False)
    return len(combined)


def extract_structured_data_from_workbook(
    excel_path: Path,
    season_label: Optional[str] = None,
    is_results: bool = False,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]]]:
    """
    Extracts clean, normalized relational records for:
      1. Matches
      2. Batting innings
      3. Bowling innings
    """
    xls = pd.ExcelFile(excel_path)
    match_records: List[Dict[str, object]] = []
    batting_records: List[Dict[str, object]] = []
    bowling_records: List[Dict[str, object]] = []

    for sheet_name in xls.sheet_names:
        try:
            df = xls.parse(sheet_name, header=None)
        except Exception:
            continue

        if df.empty or len(df) < 5:
            continue

        # --- 1. Extract Team Totals & Overs ---
        total_rows = df[df[0] == "TOTAL"]
        team_totals: List[Dict[str, object]] = []
        for idx in total_rows.index:
            row = df.loc[idx]
            runs, overs = extract_team_runs_and_overs(row)
            if runs is not None and overs is not None:
                balls = overs_to_balls(overs)
                rr = round((runs / balls) * 6, 2) if balls > 0 else 0.0
                team_totals.append({
                    "runs": runs,
                    "overs": overs,
                    "balls": balls,
                    "run_rate": rr,
                })

        total_match_runs = sum(t["runs"] for t in team_totals) if team_totals else 0.0
        total_match_balls = sum(t["balls"] for t in team_totals) if team_totals else 0
        match_sr = round((total_match_runs / total_match_balls) * 100, 2) if total_match_balls > 0 else 0.0

        # --- 2. Extract Batting Blocks ---
        batting_indices = df[df[0] == "BATTING"].index.tolist()
        team_names: List[str] = []

        for b_idx, start in enumerate(batting_indices):
            trailing = df.loc[start:, 0][df.loc[start:, 0] == "Extras"]
            if trailing.empty:
                continue
            end = trailing.index[0]
            batting_block = df.loc[start + 1: end - 1]

            team_name = infer_team_name(df, start, f"Team {b_idx + 1}")
            # Clean "target" annotations
            team_name = re.sub(r"\(.*?target.*?\)", "", team_name, flags=re.IGNORECASE).strip()
            team_names.append(team_name)

            team_idx = min(b_idx, len(team_totals) - 1) if team_totals else 0
            team_runs = team_totals[team_idx]["runs"] if team_totals else 0.0
            team_balls = team_totals[team_idx]["balls"] if team_totals else 0
            team_sr = round((team_runs / team_balls) * 100, 2) if team_balls > 0 else 0.0

            for pos, (_, row) in enumerate(batting_block.iterrows(), start=1):
                raw_player = row[0]
                if not isinstance(raw_player, str) or not raw_player.strip():
                    continue

                cleaned_player = clean_player_name_strict(raw_player)
                how_out = row[1] if len(row) > 1 and pd.notna(row[1]) else None
                runs = pd.to_numeric(row[2], errors="coerce") if len(row) > 2 else None
                balls = pd.to_numeric(row[3], errors="coerce") if len(row) > 3 else None
                fours = pd.to_numeric(row[4], errors="coerce") if len(row) > 4 else None
                sixes = pd.to_numeric(row[5], errors="coerce") if len(row) > 5 else None
                sr = pd.to_numeric(row[6], errors="coerce") if len(row) > 6 else None
                pct_runs = row[7] if len(row) > 7 and pd.notna(row[7]) else None

                impact = None
                if is_results and len(row) > 8:
                    impact = pd.to_numeric(row[8], errors="coerce")

                record = {
                    "Season": season_label,
                    "Match": sheet_name,
                    "Innings": b_idx + 1,
                    "Team": team_name,
                    "Batting_Order": pos,
                    "Player": raw_player.strip(),
                    "Player_Clean": cleaned_player,
                    "How_Out": how_out,
                    "Runs": runs,
                    "Balls": balls,
                    "4s": fours,
                    "6s": sixes,
                    "Strike_Rate": sr,
                    "Pct_Team_Runs": pct_runs,
                    "Team_Runs": team_runs,
                    "Team_SR": team_sr,
                    "Match_Runs": total_match_runs,
                    "Match_SR": match_sr,
                }
                if is_results:
                    record["Batting_Impact"] = impact

                batting_records.append(record)

        # --- 3. Extract Bowling Blocks ---
        bowling_indices = df[df[0] == "BOWLING"].index.tolist()
        for bowl_idx, start in enumerate(bowling_indices):
            end = start + 1
            while end < len(df):
                val = df.iloc[end, 0]
                if pd.isna(val) or (isinstance(val, str) and val.isupper() and "BOWLING" not in val):
                    break
                end += 1

            bowling_block = df.iloc[start + 1: end]
            # In a 2-innings match, bowling team in Innings 1 is Team 2; bowling team in Innings 2 is Team 1
            bowling_team = team_names[1] if bowl_idx == 0 and len(team_names) > 1 else (
                team_names[0] if bowl_idx == 1 and len(team_names) > 0 else f"Bowling Team {bowl_idx + 1}"
            )
            batting_opponent = team_names[bowl_idx] if bowl_idx < len(team_names) else f"Batting Team {bowl_idx + 1}"

            for _, row in bowling_block.iterrows():
                raw_bowler = row[0]
                if not isinstance(raw_bowler, str) or not raw_bowler.strip():
                    continue

                cleaned_bowler = clean_player_name_strict(raw_bowler)
                overs = pd.to_numeric(row[1], errors="coerce") if len(row) > 1 else None
                maidens = pd.to_numeric(row[2], errors="coerce") if len(row) > 2 else None
                runs_conceded = pd.to_numeric(row[3], errors="coerce") if len(row) > 3 else None
                wickets = pd.to_numeric(row[4], errors="coerce") if len(row) > 4 else None
                econ = pd.to_numeric(row[5], errors="coerce") if len(row) > 5 else None
                pct_wickets = row[6] if len(row) > 6 and pd.notna(row[6]) else None
                balls_bowled = overs_to_balls(overs) if pd.notna(overs) else 0

                bowling_records.append({
                    "Season": season_label,
                    "Match": sheet_name,
                    "Innings": bowl_idx + 1,
                    "Bowling_Team": bowling_team,
                    "Against_Team": batting_opponent,
                    "Bowler": raw_bowler.strip(),
                    "Bowler_Clean": cleaned_bowler,
                    "Overs": overs,
                    "Balls_Bowled": balls_bowled,
                    "Maidens": maidens,
                    "Runs_Conceded": runs_conceded,
                    "Wickets": wickets,
                    "Economy": econ,
                    "Pct_Team_Wickets": pct_wickets,
                })

        # --- 4. Match Level Summary ---
        t1_name = team_names[0] if len(team_names) > 0 else "Team 1"
        t2_name = team_names[1] if len(team_names) > 1 else "Team 2"
        t1 = team_totals[0] if len(team_totals) > 0 else {}
        t2 = team_totals[1] if len(team_totals) > 1 else {}

        match_records.append({
            "Season": season_label,
            "Match": sheet_name,
            "Team_1": t1_name,
            "Team_2": t2_name,
            "Team_1_Runs": t1.get("runs"),
            "Team_1_Overs": t1.get("overs"),
            "Team_1_Balls": t1.get("balls"),
            "Team_1_RR": t1.get("run_rate"),
            "Team_2_Runs": t2.get("runs"),
            "Team_2_Overs": t2.get("overs"),
            "Team_2_Balls": t2.get("balls"),
            "Team_2_RR": t2.get("run_rate"),
            "Total_Match_Runs": total_match_runs,
            "Total_Match_Balls": total_match_balls,
            "Match_SR": match_sr,
        })

    return match_records, batting_records, bowling_records


def convert_all(
    base_src_dir: Path = BASE_DIR,
    results_src_dir: Path = RESULTS_DIR,
    target_csv_root: Path = CSV_DIR,
    create_parquet: bool = True,
) -> None:
    """
    Main conversion routine:
    1. Converts all Excel workbooks in base/ and results/ to 1:1 CSV counterparts in scorecards_csv/.
    2. Builds consolidated, clean relational datasets (all_matches, all_batting, all_bowling).
    """
    t_start = time.time()
    csv_base_dir = ensure_dir(target_csv_root / "base")
    csv_results_dir = ensure_dir(target_csv_root / "results")

    base_files = sorted(base_src_dir.glob("IPL_Scorecards_*_to_*.xlsx"), key=lambda p: p.name)
    results_files = sorted(results_src_dir.glob("IPL_Scorecards_*_to_*_with_impact.xlsx"), key=lambda p: p.name)

    print("[START] Starting Excel to CSV Conversion")
    print(f"   Source Base files   : {len(base_files)} files in {base_src_dir}")
    print(f"   Source Results files: {len(results_files)} files in {results_src_dir}")
    print(f"   Target Directory    : {target_csv_root}\n")

    # -------------------------------------------------------------
    # Step 1: Convert Base Files
    # -------------------------------------------------------------
    print("[1/2] Processing Base Scorecards...")
    base_season_map = build_file_season_map(base_files)
    all_base_matches: List[Dict[str, object]] = []
    all_base_batting: List[Dict[str, object]] = []
    all_base_bowling: List[Dict[str, object]] = []

    for idx, f in enumerate(base_files, start=1):
        out_csv_name = f.stem + ".csv"
        out_csv_path = csv_base_dir / out_csv_name
        rows_stacked = convert_excel_to_stacked_csv(f, out_csv_path)

        season = base_season_map.get(f)
        matches, batting, bowling = extract_structured_data_from_workbook(f, season_label=season, is_results=False)
        all_base_matches.extend(matches)
        all_base_batting.extend(batting)
        all_base_bowling.extend(bowling)

        print(f"   [{idx}/{len(base_files)}] Converted {f.name} -> {out_csv_name} ({rows_stacked} rows, {len(matches)} matches)")

    # Save consolidated Base tables
    df_base_matches = pd.DataFrame(all_base_matches)
    df_base_batting = pd.DataFrame(all_base_batting)
    df_base_bowling = pd.DataFrame(all_base_bowling)

    df_base_matches.to_csv(csv_base_dir / "all_matches.csv", index=False)
    df_base_batting.to_csv(csv_base_dir / "all_batting.csv", index=False)
    df_base_bowling.to_csv(csv_base_dir / "all_bowling.csv", index=False)

    if create_parquet:
        try:
            df_base_matches.to_parquet(csv_base_dir / "all_matches.parquet", index=False)
            df_base_batting.to_parquet(csv_base_dir / "all_batting.parquet", index=False)
            df_base_bowling.to_parquet(csv_base_dir / "all_bowling.parquet", index=False)
        except Exception as exc:
            print(f"   [Notice] Parquet export skipped: {exc}")

    print(f"   [DONE] Base Consolidated: {len(df_base_matches)} matches, {len(df_base_batting)} batting rows, {len(df_base_bowling)} bowling rows.\n")

    # -------------------------------------------------------------
    # Step 2: Convert Results Files
    # -------------------------------------------------------------
    print("[2/2] Processing Results Scorecards (with Impact Index)...")
    res_season_map = build_file_season_map(results_files)
    all_res_matches: List[Dict[str, object]] = []
    all_res_batting: List[Dict[str, object]] = []
    all_res_bowling: List[Dict[str, object]] = []

    for idx, f in enumerate(results_files, start=1):
        out_csv_name = f.stem + ".csv"
        out_csv_path = csv_results_dir / out_csv_name
        rows_stacked = convert_excel_to_stacked_csv(f, out_csv_path)

        season = res_season_map.get(f)
        matches, batting, bowling = extract_structured_data_from_workbook(f, season_label=season, is_results=True)
        all_res_matches.extend(matches)
        all_res_batting.extend(batting)
        all_res_bowling.extend(bowling)

        print(f"   [{idx}/{len(results_files)}] Converted {f.name} -> {out_csv_name} ({rows_stacked} rows, {len(matches)} matches)")

    # Save consolidated Results tables
    df_res_matches = pd.DataFrame(all_res_matches)
    df_res_batting = pd.DataFrame(all_res_batting)
    df_res_bowling = pd.DataFrame(all_res_bowling)

    df_res_matches.to_csv(csv_results_dir / "all_matches.csv", index=False)
    df_res_batting.to_csv(csv_results_dir / "all_batting_with_impact.csv", index=False)
    df_res_bowling.to_csv(csv_results_dir / "all_bowling.csv", index=False)

    if create_parquet:
        try:
            df_res_matches.to_parquet(csv_results_dir / "all_matches.parquet", index=False)
            df_res_batting.to_parquet(csv_results_dir / "all_batting_with_impact.parquet", index=False)
            df_res_bowling.to_parquet(csv_results_dir / "all_bowling.parquet", index=False)
        except Exception as exc:
            print(f"   [Notice] Parquet export skipped: {exc}")

    print(f"   [DONE] Results Consolidated: {len(df_res_matches)} matches, {len(df_res_batting)} batting rows (with impact), {len(df_res_bowling)} bowling rows.\n")

    elapsed = time.time() - t_start
    print(f"[SUCCESS] All conversions finished in {elapsed:.2f} seconds!")
    print(f"[INFO] CSV files are saved in: {target_csv_root}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Excel scorecards to CSV and structured tables")
    parser.add_argument("--base-dir", default=str(BASE_DIR), help="Directory containing raw base Excel scorecards")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR), help="Directory containing results Excel scorecards")
    parser.add_argument("--output-dir", default=str(CSV_DIR), help="Destination folder for CSV files")
    args = parser.parse_args()

    convert_all(
        base_src_dir=Path(args.base_dir),
        results_src_dir=Path(args.results_dir),
        target_csv_root=Path(args.output_dir),
    )
