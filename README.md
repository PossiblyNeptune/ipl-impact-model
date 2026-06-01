# IPL Impact Analysis

A comprehensive data analysis project for Indian Premier League (IPL) cricket statistics, tracking batting performance and match data from 2008 to 2025.

Deployed at https://ipl-impact-model.streamlit.app/

## Project Overview

This project analyzes IPL match scorecards and cricket statistics to generate insights on player performance. It includes web scraping capabilities to collect match data, data processing tools to calculate performance metrics, and analysis scripts to generate career and seasonal statistics.

Note: The impact score model is batting-only. Bowling data is treated as raw scorecard information and is not part of the impact ratings.

## Data Structure

### Source Data
- **Match Scorecards**: Excel files containing raw IPL match data from seasons 2008-2025
- **Data Range**: 1,181+ match records organized in seasonal batches
- **File Organization**:
  - `scorecards/base/` - Raw match data
  - `scorecards/results/` - Processed data with impact metrics
  - `IPL_Scorecards_XXXX_to_XXXX.xlsx` - Raw match data
  - `IPL_Scorecards_XXXX_to_XXXX_with_impact.xlsx` - Processed data with impact metrics

### Seasons Covered
- 2008-2019: Batches of 59-60 matches per file
- 2020-2025: Batches of 59-75 matches per file
- **Total Matches**: 1,181+ recorded matches

## Project Files

### Consolidated Scripts
All analysis utilities now live in the `scripts/` folder.

- **`scripts/cli.py`** - Main entry point (CLI) for common workflows
- **`scripts/common.py`** - Shared utilities (file discovery, season mapping, parsing helpers)
- **`scripts/scrape_scorecards.py`** - Web scraper for scorecards
- **`scripts/add_impact.py`** - Adds batting impact scores to scorecards
- **`scripts/batting.py`** - Batting analysis (player summaries, top strike rates)
- **`scripts/bowling.py`** - Bowling analysis (player summaries)
- **`scripts/impact.py`** - Impact analysis (top innings, seasons, MOTM, etc.)
- **`scripts/scorecard.py`** - Scorecard parsing helpers for the UI

### Streamlit UI
- **`app.py`** - Interactive Streamlit app
- **`.streamlit/config.toml`** - UI theme configuration

## Key Features

### Data Extraction
- Scrapes live match scorecard data from howstat.com
- Automated batch processing for multiple seasons
- Handles network requests and HTML parsing with BeautifulSoup

### Data Processing
- Overs-to-balls conversion for standardized metrics
- Team runs and overs extraction from match data
- Positive z-score normalization for impact metrics

### Analysis Capabilities
- **Career Statistics**: Track player performance across multiple seasons
- **Seasonal Breakdown**: Analyze performance by IPL season
- **Player Rankings**: Identify top performers based on various metrics
- **Batting Impact**: Calculate batting impact contributions to match outcomes

## Technical Stack

- **Python 3.x**
- **Libraries**:
  - `pandas` - Data manipulation and analysis
  - `openpyxl` - Excel file operations
  - `requests` - Web scraping
  - `BeautifulSoup` - HTML parsing
  - `numpy` - Numerical calculations
  - `re` - Regular expressions for data extraction

## Usage Examples

Use the CLI to run common workflows:

### Scrape Scorecards
```bash
python -m scripts.cli scrape
python -m scripts.cli scrape --range 0000-0059 --range 0060-0118
```

### Add Batting Impact to Base Scorecards
```bash
python -m scripts.cli add-impact
```

### Player Batting Summary
```bash
python -m scripts.cli batting player "Jos Buttler"
```

### Top Strike Rate Rankings
```bash
python -m scripts.cli batting top-sr --min-runs 750 --limit 20
```

### Player Bowling Summary
```bash
python -m scripts.cli bowling player "Jasprit Bumrah"
```

Bowling summaries are raw aggregates only; the impact model remains batting-only.

### Impact Leaderboards
```bash
python -m scripts.cli impact top-innings --limit 50
python -m scripts.cli impact top-seasons --limit 50
python -m scripts.cli impact motm --limit 50
```

All commands accept `--csv` to export results (where supported).

## Streamlit App

Run the UI locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

The Streamlit UI focuses on batting impact scores and batting-related trends.

### Deploy to Streamlit Community Cloud
1. Push the repository to GitHub.
2. Go to https://share.streamlit.io and create a new app.
3. Select your repo, branch, and set the entry point to `app.py`.
4. Deploy and open the app URL.

## File-to-Season Mapping

| Excel File Range | Season |
|---|---|
| 0001 to 0059 | 2008 |
| 0060 to 0118 | 2009 |
| 0119 to 0178 | 2010 |
| 0179 to 0252 | 2011 |
| 0253 to 0328 | 2012 |
| 0329 to 0404 | 2013 |
| 0405 to 0464 | 2014 |
| 0465 to 0524 | 2015 |
| 0525 to 0584 | 2016 |
| 0585 to 0644 | 2017 |
| 0645 to 0704 | 2018 |
| 0705 to 0764 | 2019 |
| 0765 to 0824 | 2020 |
| 0825 to 0884 | 2021 |
| 0885 to 0958 | 2022 |
| 0959 to 1033 | 2023 |
| 1034 to 1107 | 2024 |
| 1108 to 1181 | 2025 |

## Data Format

### Excel Scorecard Structure
Each match sheet contains:
- **BATTING Section**: Player names, runs, balls, 4s, 6s, strike rate, percentage of team runs
- **BOWLING Section**: Bowler names, overs, runs, wickets, economy rate
- **TOTAL Row**: Team aggregate statistics with wickets and overs
- **Match Details**: Teams, date, venue information

## Performance Metrics

### Batting Metrics
- **Runs**: Total runs scored
- **Balls**: Balls faced
- **Strike Rate**: Runs per 100 balls
- **Average**: Runs per innings
- **% of Team Runs**: Contribution to team total

### Bowling Data (Raw Only)
- **Overs**: Bowling overs bowled
- **Runs**: Runs conceded
- **Wickets**: Wickets taken
- **Economy Rate**: Runs conceded per over

Bowling data is not scored by the impact model.

## Installation

1. Clone or download the repository
2. Install required dependencies:
   ```bash
   pip install pandas openpyxl requests beautifulsoup4 numpy
   ```
3. Place raw scorecards in `scorecards/base/`
4. Run analysis via `python -m scripts.cli ...`

## Notes

- The project uses positive z-score normalization to compare player performance
- Impact metrics are calculated to identify match-winning contributions
- Player names are cleaned to remove special characters and annotations for consistent grouping
- The project covers 18 IPL seasons with over 1,181 matches analyzed