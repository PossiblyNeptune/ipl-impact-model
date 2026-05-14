from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, List, Dict, Tuple, Optional, Union

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCORECARDS_DIR = REPO_ROOT / "scoreacrds"
BASE_DIR = SCORECARDS_DIR / "base"
RESULTS_DIR = SCORECARDS_DIR / "results"

DEFAULT_RANGES: List[Tuple[int, int]] = [
    (0, 59),
    (60, 118),
    (119, 178),
    (179, 252),
    (253, 328),
    (329, 404),
    (405, 464),
    (465, 524),
    (525, 584),
    (585, 644),
    (645, 704),
    (705, 764),
    (765, 824),
    (825, 884),
    (885, 958),
    (959, 1033),
    (1034, 1107),
    (1108, 1181),
]

SEASON_RANGES: List[Tuple[int, int, str]] = [
    (0, 59, "2008"),
    (60, 118, "2009"),
    (119, 178, "2010"),
    (179, 252, "2011"),
    (253, 328, "2012"),
    (329, 404, "2013"),
    (405, 464, "2014"),
    (465, 524, "2015"),
    (525, 584, "2016"),
    (585, 644, "2017"),
    (645, 704, "2018"),
    (705, 764, "2019"),
    (765, 824, "2020"),
    (825, 884, "2021"),
    (885, 958, "2022"),
    (959, 1033, "2023"),
    (1034, 1107, "2024"),
    (1108, 1181, "2025"),
]


def configure_pandas_display() -> None:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.expand_frame_repr", False)
    pd.set_option("display.max_colwidth", None)


def ensure_dir(path: Union[str, Path]) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def scorecard_filename(start: int, end: int) -> str:
    return f"IPL_Scorecards_{start:04d}_to_{end:04d}.xlsx"


def parse_scorecard_range(name: str) -> Tuple[Optional[int], Optional[int]]:
    match = re.search(r"IPL_Scorecards_(\d{4})_to_(\d{4})\.xlsx", name)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def season_for_range(start: Optional[int], end: Optional[int]) -> Optional[str]:
    if start is None or end is None:
        return None
    for range_start, range_end, season in SEASON_RANGES:
        if start == range_start and end == range_end:
            return season
    return None


def build_file_season_map(files: Iterable[Path]) -> Dict[Path, Optional[str]]:
    mapping: Dict[Path, Optional[str]] = {}
    for file_path in files:
        start, end = parse_scorecard_range(file_path.name)
        mapping[file_path] = season_for_range(start, end)
    return mapping


def find_scorecard_files(data_dir: Union[str, Path] = BASE_DIR) -> List[Path]:
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return []
    return sorted(data_dir.glob("IPL_Scorecards_*_to_*.xlsx"), key=lambda p: p.name)


def resolve_input_files(
    files: Optional[Iterable[str]],
    data_dir: Union[str, Path] = BASE_DIR,
) -> List[Path]:
    if not files:
        return find_scorecard_files(data_dir)

    resolved: List[Path] = []
    for entry in files:
        path = Path(entry)
        if not path.is_absolute():
            data_dir_path = Path(data_dir)
            candidate = data_dir_path / path
            path = candidate if candidate.exists() else (REPO_ROOT / path)
        resolved.append(path)
    return resolved


def write_csv(rows: Union[List[Dict[str, object]], pd.DataFrame], output_path: Union[str, Path]) -> None:
    output_path = Path(output_path)
    if isinstance(rows, pd.DataFrame):
        df = rows
    else:
        if not rows:
            return
        df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)


def overs_to_balls(overs: object) -> int:
    if overs is None:
        return 0
    try:
        overs_value = float(overs)
    except Exception:
        return 0

    whole = int(overs_value)
    decimal = overs_value - whole
    return whole * 6 + round(decimal * 10)


def extract_team_runs_and_overs(row: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    for i in range(len(row) - 1):
        col = row[i]
        if isinstance(col, str) and "wicket" in col.lower():
            match = re.search(r"\(([\d.]+) overs", col)
            if match:
                try:
                    overs = float(match.group(1))
                    runs = float(row[i + 1])
                    return runs, overs
                except Exception:
                    continue
    return None, None


def positive_z_score_normalize(values: Iterable[float]) -> List[float]:
    values_list = list(values)
    if not values_list:
        return []
    mean = np.mean(values_list)
    std = np.std(values_list)
    z_scores = [(v - mean) / std if std > 0 else 0 for v in values_list]
    min_z = min(z_scores)
    shift = -min_z + 0.01 if min_z <= 0 else 0
    return [z + shift for z in z_scores]


def clean_player_name_basic(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = re.sub(r"\([^()]*\)", "", name)
    name = re.sub(r"[*\u2020]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def clean_player_name_strict(name: str) -> str:
    name = clean_player_name_basic(name)
    name = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()
