# IPL Impact & VORP Studio (2008–2026)

A state-of-the-art sabermetric cricket analytics platform tracking batting performance, era-adjusted impact metrics, and position-specific **Value Over Replacement Player (I-VORP)** across 19 Indian Premier League seasons (1,255 matches, 19,113 innings).

🔗 **Live Interactive App**: [ipl-impact-model.streamlit.app](https://ipl-impact-model.streamlit.app/)

---

## Table of Contents

- [Overview](#overview)
- [Sabermetric Methodology](#sabermetric-methodology)
  - [Batting Impact Index](#1-batting-impact-index)
  - [Positional Value Over Replacement Player (I-VORP)](#2-positional-value-over-replacement-player-i-vorp)
  - [% Better Than Replacement (% vs Rep)](#3--better-than-replacement--vs-rep)
- [Interactive Streamlit Studio](#interactive-streamlit-studio)
  - [Tab 1: 🏟️ Match Scorecard & VORP](#tab-1-️-match-scorecard--vorp)
  - [Tab 2: 👤 Player Studio](#tab-2--player-studio)
  - [Tab 3: 👤 Player VORP Profiler](#tab-3--player-vorp-profiler)
  - [Tab 4: 🏆 The Pantheon: Iconic Knocks & Match-Winners](#tab-4--the-pantheon-iconic-knocks--match-winners)
- [CLI Reference](#cli-reference)
- [Dataset Architecture & Performance](#dataset-architecture--performance)
  - [File-to-Season Mapping](#file-to-season-mapping)
  - [Directory Structure](#directory-structure)
- [Installation & Quickstart](#installation--quickstart)
- [Tech Stack](#tech-stack)

---

## Overview

Traditional T20 cricket statistics (raw averages and cumulative runs) obscure situational context. Scoring a 35-ball 50 when chasing 210 carries a fundamentally different value than scoring 50 off 45 on a spinning pitch chasing 125. Furthermore, batting slots face starkly different structural demands: openers face the powerplay field restrictions with maximum deliveries available, whereas finishers face death overs under urgent run-rate demands.

This platform resolves those limitations through:
1. **Era & Match-Adjusted Batting Impact**: Quantifying each innings as a product of volume (share of team total) and tempo acceleration (positive z-score normalized strike rate relative to the match environment).
2. **Positional Replacement Baselines**: Establishing canonical replacement-level benchmarks (the 20th percentile of qualified regulars) for every batting slot (Openers through Number 8+) and tactical order (Top Order, Middle Order, Finisher, Lower Order).
3. **Surplus Value Metrics**: Measuring cumulative career/season **Total I-VORP** and rate-based **% Better Than Replacement (% vs Rep)**.
4. **Sub-40ms Performance**: Leveraging compressed Parquet binary caching for instant exploration across all 19,113 historical innings.

> **Note**: The impact model is strictly batting-focused. Bowling statistics are compiled as raw scorecard aggregates for context.

---

## Sabermetric Methodology

### 1. Batting Impact Index

The Batting Impact Index ($I_i$) models how decisively an individual batter moved the needle in a given match:

$$\text{Impact Index} = \text{Volume} \times \text{Acceleration}$$

- **Volume ($\text{Vol}$)**: Fraction of team runs scored by the batter:
  $$\text{Vol} = \frac{\text{Runs}_{\text{batter}}}{\text{Team Runs}}$$
- **Acceleration ($\text{Acc}$)**: Normalized relative strike rate compared to team scoring tempo, scaled via positive z-score transformation:
  $$\text{Acc} = z_{\text{pos}}\left(\frac{\text{SR}_{\text{batter}}}{\text{Team SR}}\right)$$

An impact of **1.00** represents a benchmark performance. Elite match-winning knocks frequently register impact scores between **2.00** and **4.00+**.

### 2. Positional Value Over Replacement Player (I-VORP)

Value Over Replacement Player determines how much value a cricketer generates beyond a readily available, "replacement-level" fringe player at the same batting position.

- **Positional Schemes**:
  - **Individual Positions**: `Opener`, `Number 3`, `Number 4`, `Number 5`, `Number 6`, `Number 7`, `Number 8+`.
  - **Tactical Orders**: `Top Order` (Slots 1–3), `Middle Order` (Slots 4–5), `Finisher` (Slots 6–7), `Lower Order` (Slots 8+).
- **Replacement Level ($B_{\text{pos}}$)**: Defined canonically as the **20th percentile ($P_{20}$)** of Batting Impact among qualified regulars at each slot.
- **Innings Surplus**:
  $$I_{\text{vorp}, i} = I_i - B_{\text{pos}}$$
- **Cumulative Surplus**:
  $$\text{Total I-VORP} = \sum_{i} I_{\text{vorp}, i}$$

### 3. % Better Than Replacement (% vs Rep)

While cumulative I-VORP scales with career length, **% Better Than Replacement** offers an intuitive, rate-based metric that normalizes across playing time:

$$\text{\% vs Rep} = \left(\frac{\text{Total I-VORP}}{\sum B_{\text{pos}}}\right) \times 100\% = \left(\frac{\overline{I}_{\text{actual}} - B_{\text{pos}}}{B_{\text{pos}}}\right) \times 100\%$$

- **$0\%$**: Exactly replacement level (par baseline).
- **$+50\%$ to $+100\%$**: High-quality regular.
- **$+150\%$ to $+250\%+$**: All-time elite batter.

---

## Interactive Streamlit Studio

Launch the dashboard locally with `streamlit run app.py`. The interface is split into four analytical workspaces:

### Tab 1: 🏟️ Match Scorecard & VORP
- **Match Inspector**: Browse all 1,255 matches across 19 seasons with automated team names, totals, and match summary cards.
- **Match Impact Leaders**: Ranked bar chart of every batter's impact in the selected match.
- **Annotated Batting Scorecards**: Innings-by-innings tables featuring batting positions, runs, balls, boundaries, strike rate, team share, Batting Impact index, positional replacement baseline, and single-match I-VORP surplus.
- **Bowling Summaries**: Bowling figures (overs, maidens, runs, wickets, economy).

### Tab 2: 👤 Player Studio
- **Multi-Position Filtering**: Analyze individual slots (`Opener`, `Number 3`, `Number 4`, ...) or tactical orders (`Top Order`, `Middle Order`, `Finisher`, `Lower Order`) with multi-select capabilities.
- **Aggregation Scope**: Toggle seamlessly between **All-Time Career** and **Individual Seasons**.
- **Ranking Controls**: Rank by `% Better Than Replacement`, `Total I-VORP`, `Total Impact`, or `Average I-VORP / Innings`.
- **Sort Toggle**: Switch between descending (top performers) and ascending (identifying replacement-level fringes).
- **Interactive Visualizations**:
  - Horizontal bar chart of leaders with color-scaled surplus value.
  - Scatter plot: *Innings vs Total I-VORP* (bubble size = runs, color = % vs Rep).
  - Scatter plot: *Innings vs Total Batting Impact* (bubble size = runs, color = average impact).
  - Centered leaderboard table with export-ready formatting.

### Tab 3: 👤 Player VORP Profiler
- **Searchable Player Dossier**: Deep dive into any batter across IPL history.
- **6-Metric Single-Line KPI Banner**:
  - Career Innings
  - Primary Slot
  - Total Batting Impact
  - Total I-VORP (Ind)
  - % vs Rep (Overall)
  - Average Impact / Inning
- **Impact vs Replacement Baseline Chart**: Grouped bar chart comparing the player's average impact at each position against the positional replacement threshold.
- **Positional Breakdown Tables**: Complete career splits across all individual positions and tactical orders.
- **Three Career Progression Trajectories**:
  1. *Season-by-Season Total I-VORP*: Longitudinal line graph tracing career value generation.
  2. *Season-by-Season % Better Than Replacement*: Dynamic bar graph color-coded by Above vs Below replacement, anchored by a $0\%$ par baseline.
  3. *Season-by-Season Total Batting Impact*: Line graph of absolute impact index trajectory.

### Tab 4: 🏆 The Pantheon: Iconic Knocks & Match-Winners
- **⚡ Greatest Single-Innings Knocks**: All-time highest Batting Impact innings in IPL history, with filters for batting slot, 1st innings (setting total), and 2nd innings (chasing).
- **⚔️ Lone Warrior Carry Jobs (% Team Runs)**: The most extreme single-handed efforts where one batter scored the highest proportion of their team's total runs (with single-line team names and configurable minimum runs cutoffs).
- **🧨 High-Velocity Blitzkriegs (≤ 25 Balls)**: The most destructive rapid-fire knocks capped at 25 balls, featuring a maximum balls slider (5 to 25 balls) and metric sorting by Impact, Strike Rate, or Runs.

---

## CLI Reference

All analytical utilities can be executed directly from the terminal via `scripts.cli`:

```bash
# Display top-level CLI help
python -m scripts.cli --help
```

### 1. Position-Specific VORP (`vorp`)
```bash
# Career position leaderboards
python -m scripts.cli vorp leaders "Opener" --sort-by pct_above_rep --limit 20
python -m scripts.cli vorp leaders "Finisher" --scheme tactical --sort-by total_ivorp --limit 20

# Best individual seasons in history
python -m scripts.cli vorp leaders "Opener" --by-season --sort-by pct_above_rep --min-innings 10 --limit 15
python -m scripts.cli vorp leaders "Number 4" --by-season --sort-by total_ivorp --min-innings 7 --limit 15

# Detailed player multi-position profile
python -m scripts.cli vorp player "Virat Kohli"
python -m scripts.cli vorp player "AB de Villiers"
python -m scripts.cli vorp player "Andre Russell"
```

### 2. Batting Impact Index (`impact`)
```bash
# Top single-innings knocks
python -m scripts.cli impact top-innings --limit 25

# Top single-season impact campaigns
python -m scripts.cli impact top-seasons --limit 25

# Man of the Match (highest impact) innings
python -m scripts.cli impact motm --limit 25
```

### 3. Traditional Aggregates (`batting` & `bowling`)
```bash
# Individual player career batting summary
python -m scripts.cli batting player "Jos Buttler"

# Highest strike rates (qualified by runs)
python -m scripts.cli batting top-sr --min-runs 750 --limit 20

# Player bowling aggregate summary
python -m scripts.cli bowling player "Jasprit Bumrah"
```

### 4. Data Processing Pipelines
```bash
# Calculate and append Batting Impact to raw base Excel scorecards
python -m scripts.cli add-impact

# Export Excel workbooks to standardized CSV and fast Parquet tables
python -m scripts.cli convert-csv
```

### 5. Web Scraping (`scrape`)
```bash
# Scrape live scorecards from Howstat into base Excel workbooks
python -m scripts.cli scrape
python -m scripts.cli scrape --range 0000-0059 --range 0060-0118
```

---

## Dataset Architecture & Performance

### File-to-Season Mapping

The project spans 19 IPL seasons (1,255 matches):

| Excel File Range | Season | Matches |
|:---:|:---:|:---:|
| `0001 to 0059` | **2008** | 59 |
| `0060 to 0118` | **2009** | 59 |
| `0119 to 0178` | **2010** | 60 |
| `0179 to 0252` | **2011** | 74 |
| `0253 to 0328` | **2012** | 76 |
| `0329 to 0404` | **2013** | 76 |
| `0405 to 0464` | **2014** | 60 |
| `0465 to 0524` | **2015** | 60 |
| `0525 to 0584` | **2016** | 60 |
| `0585 to 0644` | **2017** | 60 |
| `0645 to 0704` | **2018** | 60 |
| `0705 to 0764` | **2019** | 60 |
| `0765 to 0824` | **2020** | 60 |
| `0825 to 0884` | **2021** | 60 |
| `0885 to 0958` | **2022** | 74 |
| `0959 to 1033` | **2023** | 75 |
| `1034 to 1107` | **2024** | 74 |
| `1108 to 1181` | **2025** | 74 |
| `1182 to 1255` | **2026** | 74 |

### Directory Structure

```
ipl_impact/
├── .gitignore                      # Git ignore rules (bytecode, virtual environments, local caches)
├── .streamlit/                     # Local Streamlit config (git-ignored)
│   └── config.toml                 # Theme configuration
├── README.md                       # Comprehensive project documentation
├── app.py                          # 4-Tab interactive Streamlit application
├── requirements.txt                # Python dependencies
├── impact.md                       # Detailed mathematical documentation of Batting Impact
├── vorp.md                         # Detailed sabermetric documentation of I-VORP
├── scorecards/                     # Raw and impact-annotated Excel workbooks
│   ├── base/                       # Raw match scorecards (seasons 2008–2026)
│   └── results/                    # Scorecards enriched with Batting Impact
├── scorecards_csv/                 # Processed tabular datasets
│   └── results/
│       ├── all_batting_with_vorp.parquet  # Master dataset (<40ms read time, 19,113 rows)
│       ├── all_batting_with_vorp.csv      # Full CSV export
│       ├── all_matches.csv                # Match-level metadata & results
│       └── all_bowling.csv                # Bowling records across all matches
└── scripts/                        # Core analytics and utility modules
    ├── __init__.py                 # Package declaration
    ├── cli.py                      # Unified CLI entrypoint
    ├── common.py                   # Parsing utilities, z-score math, season mapping
    ├── vorp.py                     # Positional baseline & I-VORP calculation engine
    ├── impact.py                   # Batting Impact index rankings and aggregations
    ├── batting.py                  # Traditional batting summaries and strike rate rankings
    ├── bowling.py                  # Bowling summaries and leaderboards
    ├── add_impact.py               # In-place Excel scorecard enrichment
    ├── convert_to_csv.py           # Pipeline to generate structured CSV & Parquet
    ├── scorecard.py                # Scorecard parsing helpers for app views
    └── scrape_scorecards.py        # Web scraper for Howstat (git-ignored local utility)
```

---

## Installation & Quickstart

### Prerequisites
- Python `3.10` or higher
- `git`

### 1. Clone the Repository
```bash
git clone https://github.com/PossiblyNeptune/ipl-impact-model.git
cd ipl-impact-model
```

### 2. Set Up a Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
The studio will launch in your browser at `http://localhost:8501`.

---

## Tech Stack

- **Application Framework**: [Streamlit](https://streamlit.io/)
- **Data Manipulation**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Storage & Compression**: [PyArrow](https://arrow.apache.org/docs/python/) (Apache Parquet), [OpenPyXL](https://openpyxl.readthedocs.io/)
- **Interactive Visualizations**: [Plotly](https://plotly.com/python/)
- **Web Scraping**: [Requests](https://requests.readthedocs.io/), [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- **Typography & Aesthetics**: Custom CSS design system with Space Grotesk, Fraunces, and Inter fonts