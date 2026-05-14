from __future__ import annotations

from typing import List, Dict, Optional
import re

import pandas as pd

from .common import extract_team_runs_and_overs, overs_to_balls


def infer_team_name(df: pd.DataFrame, start_idx: int, fallback: str) -> str:
    if start_idx > 0:
        candidate = df.iloc[start_idx - 1, 0]
        if isinstance(candidate, str) and candidate.strip():
            name = candidate.strip()
            name = re.sub(r"innings.*", "", name, flags=re.IGNORECASE).strip()
            return name or fallback
    return fallback


def extract_team_totals(df: pd.DataFrame) -> List[Dict[str, object]]:
    totals: List[Dict[str, object]] = []
    total_rows = df[df[0] == "TOTAL"]

    for idx in total_rows.index:
        row = df.loc[idx]
        runs, overs = extract_team_runs_and_overs(row)
        if runs is None or overs is None:
            continue
        balls = overs_to_balls(overs)
        run_rate = round((runs / balls) * 6, 2) if balls > 0 else 0.0
        totals.append({
            "Runs": runs,
            "Overs": overs,
            "Balls": balls,
            "RunRate": run_rate,
        })

    return totals


def extract_batting_blocks(df: pd.DataFrame) -> List[Dict[str, object]]:
    blocks: List[Dict[str, object]] = []
    batting_indices = df[df[0] == "BATTING"].index.tolist()
    totals = extract_team_totals(df)

    for idx, start in enumerate(batting_indices):
        end_idx = df.loc[start:, 0][df.loc[start:, 0] == "Extras"]
        if end_idx.empty:
            continue
        end = end_idx.index[0]
        batting_block = df.loc[start + 1: end - 1]

        rows = []
        for _, row in batting_block.iterrows():
            name = row[0]
            if not isinstance(name, str) or not name.strip():
                continue
            rows.append({
                "Player": row[0],
                "How Out": row[1] if len(row) > 1 else None,
                "Runs": row[2] if len(row) > 2 else None,
                "Balls": row[3] if len(row) > 3 else None,
                "4s": row[4] if len(row) > 4 else None,
                "6s": row[5] if len(row) > 5 else None,
                "Strike Rate": row[6] if len(row) > 6 else None,
            })

        team_name = infer_team_name(df, start, f"Innings {idx + 1}")
        team_total = totals[idx] if idx < len(totals) else None
        blocks.append({
            "team_name": team_name,
            "batting": pd.DataFrame(rows),
            "total": team_total,
        })

    return blocks


def extract_bowling_blocks(df: pd.DataFrame) -> List[Dict[str, object]]:
    blocks: List[Dict[str, object]] = []
    bowling_indices = df[df[0] == "BOWLING"].index.tolist()

    for idx, start in enumerate(bowling_indices):
        end = start + 1
        while end < len(df):
            val = df.iloc[end, 0]
            if pd.isna(val) or (isinstance(val, str) and val.isupper() and "BOWLING" not in val):
                break
            end += 1

        bowling_df = df.iloc[start + 1: end]
        rows = []
        for _, row in bowling_df.iterrows():
            name = row[0]
            if not isinstance(name, str) or not name.strip():
                continue
            rows.append({
                "Bowler": row[0],
                "Overs": row[1],
                "Maidens": row[2],
                "Runs": row[3],
                "Wickets": row[4],
                "Economy": row[5],
            })

        team_name = infer_team_name(df, start, f"Bowling {idx + 1}")
        blocks.append({
            "team_name": team_name,
            "bowling": pd.DataFrame(rows),
        })

    return blocks
