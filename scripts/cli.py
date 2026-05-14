from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import List, Tuple

from scripts import add_impact, batting, bowling, impact, scrape_scorecards
from scripts.common import (
    BASE_DIR,
    RESULTS_DIR,
    build_file_season_map,
    configure_pandas_display,
    resolve_input_files,
    write_csv,
)


def _parse_ranges(range_args: List[str]) -> List[Tuple[int, int]]:
    ranges: List[Tuple[int, int]] = []
    for item in range_args:
        match = re.match(r"(\d+)-(\d+)", item)
        if not match:
            raise ValueError(f"Invalid range format: {item}")
        ranges.append((int(match.group(1)), int(match.group(2))))
    return ranges


def _add_common_file_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-dir", default=str(BASE_DIR), help="Directory with base scorecards")
    parser.add_argument("--files", nargs="*", help="Specific scorecard files to include")


def main() -> None:
    configure_pandas_display()

    parser = argparse.ArgumentParser(description="IPL impact analysis toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser("scrape", help="Scrape scorecards from howstat")
    scrape_parser.add_argument(
        "--range",
        action="append",
        dest="ranges",
        help="Match code range like 0000-0059 (repeatable)",
    )
    scrape_parser.add_argument("--output-dir", default=str(BASE_DIR))

    impact_add_parser = subparsers.add_parser("add-impact", help="Add batting impact column")
    impact_add_parser.add_argument("--input-dir", default=str(BASE_DIR))
    impact_add_parser.add_argument("--output-dir", default=str(RESULTS_DIR))
    impact_add_parser.add_argument("--files", nargs="*", help="Specific files to process")

    batting_parser = subparsers.add_parser("batting", help="Batting analysis")
    batting_sub = batting_parser.add_subparsers(dest="batting_cmd", required=True)

    batting_player = batting_sub.add_parser("player", help="Player batting summary")
    batting_player.add_argument("player", help="Player name to search for")
    _add_common_file_args(batting_player)
    batting_player.add_argument("--csv", help="Write raw innings to CSV")

    batting_top_sr = batting_sub.add_parser("top-sr", help="Top strike rate rankings")
    _add_common_file_args(batting_top_sr)
    batting_top_sr.add_argument("--min-runs", type=int, default=1000)
    batting_top_sr.add_argument("--limit", type=int, default=20)
    batting_top_sr.add_argument("--csv", help="Write results to CSV")

    bowling_parser = subparsers.add_parser("bowling", help="Bowling analysis")
    bowling_sub = bowling_parser.add_subparsers(dest="bowling_cmd", required=True)

    bowling_player = bowling_sub.add_parser("player", help="Player bowling summary")
    bowling_player.add_argument("player", help="Player name to search for")
    _add_common_file_args(bowling_player)
    bowling_player.add_argument("--csv", help="Write raw innings to CSV")

    impact_parser = subparsers.add_parser("impact", help="Impact index analysis")
    impact_sub = impact_parser.add_subparsers(dest="impact_cmd", required=True)

    impact_top_innings = impact_sub.add_parser("top-innings", help="Top impact innings")
    _add_common_file_args(impact_top_innings)
    impact_top_innings.add_argument("--limit", type=int, default=50)
    impact_top_innings.add_argument("--csv", help="Write results to CSV")

    impact_top_seasons = impact_sub.add_parser("top-seasons", help="Top seasons by impact")
    _add_common_file_args(impact_top_seasons)
    impact_top_seasons.add_argument("--limit", type=int, default=50)
    impact_top_seasons.add_argument("--csv", help="Write results to CSV")

    impact_top_batsmen = impact_sub.add_parser("top-batsmen", help="Top cumulative impact")
    _add_common_file_args(impact_top_batsmen)
    impact_top_batsmen.add_argument("--limit", type=int, default=50)
    impact_top_batsmen.add_argument("--csv", help="Write results to CSV")

    impact_avg_batsmen = impact_sub.add_parser("avg-batsmen", help="Top average impact")
    _add_common_file_args(impact_avg_batsmen)
    impact_avg_batsmen.add_argument("--limit", type=int, default=50)
    impact_avg_batsmen.add_argument("--min-runs", type=int, default=500)
    impact_avg_batsmen.add_argument("--csv", help="Write results to CSV")

    impact_motm = impact_sub.add_parser("motm", help="Batsman of the match counts")
    _add_common_file_args(impact_motm)
    impact_motm.add_argument("--limit", type=int, default=50)
    impact_motm.add_argument("--csv", help="Write results to CSV")

    impact_top_per_match = impact_sub.add_parser("top-per-match", help="Top players per match")
    impact_top_per_match.add_argument("--file", required=True, help="Scorecard file to analyze")
    impact_top_per_match.add_argument("--data-dir", default=str(BASE_DIR))
    impact_top_per_match.add_argument("--limit", type=int, default=5)
    impact_top_per_match.add_argument("--csv", help="Write results to CSV")

    args = parser.parse_args()

    if args.command == "scrape":
        ranges = _parse_ranges(args.ranges) if args.ranges else None
        scrape_scorecards.scrape_scorecards(ranges=ranges, output_dir=Path(args.output_dir))
        return

    if args.command == "add-impact":
        files = resolve_input_files(args.files, Path(args.input_dir)) if args.files else None
        add_impact.add_batting_impact(files, Path(args.input_dir), Path(args.output_dir))
        return

    if args.command == "batting":
        files = resolve_input_files(args.files, Path(args.data_dir))
        file_map = build_file_season_map(files)

        if args.batting_cmd == "player":
            season_summaries, career_summary, career_df = batting.summarize_player_across_files(
                args.player, files, file_map
            )
            batting.print_player_summaries(args.player, season_summaries, career_summary)
            if args.csv:
                write_csv(career_df, args.csv)
            return

        if args.batting_cmd == "top-sr":
            top_df = batting.get_top_strike_rate(files, args.min_runs, args.limit)
            batting.print_top_strike_rate(top_df, args.min_runs)
            if args.csv:
                write_csv(top_df, args.csv)
            return

    if args.command == "bowling":
        files = resolve_input_files(args.files, Path(args.data_dir))
        file_map = build_file_season_map(files)

        if args.bowling_cmd == "player":
            season_summaries, career_summary, bowling_df = bowling.summarize_bowling_by_season(
                args.player, files, file_map
            )
            bowling.print_bowling_summaries(args.player, season_summaries, career_summary)
            if args.csv:
                write_csv(bowling_df, args.csv)
            return

    if args.command == "impact":
        if args.impact_cmd == "top-per-match":
            file_path = resolve_input_files([args.file], Path(args.data_dir))[0]
            season_label = build_file_season_map([file_path]).get(file_path)
            rows = impact.top_players_per_match(file_path, args.limit, season_label)
            impact.print_top_players_per_match(rows)
            if args.csv:
                write_csv(rows, args.csv)
            return

        files = resolve_input_files(args.files, Path(args.data_dir))
        file_map = build_file_season_map(files)
        all_innings = impact.load_innings_data(files, file_map)

        if args.impact_cmd == "top-innings":
            rows = impact.top_innings(all_innings, args.limit)
            impact.print_top_innings(rows)
            if args.csv:
                write_csv(rows, args.csv)
            return

        if args.impact_cmd == "top-seasons":
            rows = impact.top_player_seasons(all_innings, args.limit)
            impact.print_top_seasons(rows)
            if args.csv:
                write_csv(rows, args.csv)
            return

        if args.impact_cmd == "top-batsmen":
            rows = impact.top_batsmen_cumulative(all_innings, args.limit)
            impact.print_top_batsmen(rows)
            if args.csv:
                write_csv(rows, args.csv)
            return

        if args.impact_cmd == "avg-batsmen":
            rows = impact.top_batsmen_avg_impact(all_innings, args.limit, args.min_runs)
            impact.print_top_avg_batsmen(rows, args.min_runs)
            if args.csv:
                write_csv(rows, args.csv)
            return

        if args.impact_cmd == "motm":
            counts = impact.batsman_of_match_counts(files, file_map)
            rows = [{"Name": name, "Count": count} for name, count in counts.items()]
            rows.sort(key=lambda x: x["Count"], reverse=True)
            impact.print_batsman_of_match(rows, args.limit)
            if args.csv:
                write_csv(rows, args.csv)
            return


if __name__ == "__main__":
    main()
