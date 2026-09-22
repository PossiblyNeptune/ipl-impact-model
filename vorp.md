# Position-Specific Impact VORP (I-VORP) Model: Complete 0-to-100 Specification

This document provides a comprehensive, end-to-end specification of the **Position-Specific Impact Value Over Replacement Player (I-VORP)** model implemented in this repository. It covers the cricket philosophy, mathematical definitions, sabermetric replacement-level theory, empirical baselines across IPL history, step-by-step algorithms, and real-world leaderboards.

---

## Table of Contents

1. [Philosophy: Why Generic Metrics & Flat Comparisons Fail](#1-philosophy-why-generic-metrics--flat-comparisons-fail)
2. [The Two Positional Grouping Schemes](#2-the-two-positional-grouping-schemes)
3. [The Sabermetric Replacement Player Theory](#3-the-sabermetric-replacement-player-theory)
4. [Why the "Innings-Percentile" Flaw Undervalued Replacement Level](#4-why-the-innings-percentile-flaw-undervalued-replacement-level)
5. [The Standard Accepted Player-Season Baseline Formula](#5-the-standard-accepted-player-season-baseline-formula)
6. [The Core I-VORP Math (0 to 100)](#6-the-core-i-vorp-math-0-to-100)
7. [The "% Better Than Replacement" (% vs Rep) Metric](#7-the--better-than-replacement--vs-rep-metric)
8. [Concrete Numerical Walkthrough (Opener vs. Finisher)](#8-concrete-numerical-walkthrough-opener-vs-finisher)
9. [All-Time IPL Position Leaderboards](#9-all-time-ipl-position-leaderboards)
10. [Player Multi-Position Profiles (Case Studies)](#10-player-multi-position-profiles-case-studies)
11. [Codebase & Data Implementation Reference](#11-codebase--data-implementation-reference)

---

## 1. Philosophy: Why Generic Metrics & Flat Comparisons Fail

In Twenty20 cricket, comparing batsmen across different batting positions using flat metrics (such as total runs, raw strike rate, or traditional average) is fundamentally flawed.

Each position operates under radically different game constraints:

```
Positional Slot        Deliveries Available     Field Restrictions       Core Tactical Mandate
----------------------------------------------------------------------------------------------------------
Openers (1 & 2)        Up to 120 balls          Powerplay (2 outside)    Exploit restrictions & build volume
Number 3               Up to 110 balls          PP tail or spread field  Early collapse control / momentum
Middle Order (4 & 5)   15 to 35 balls           5 boundary fielders      Attack spin & rotate strike
Finishers (6 & 7)      6 to 18 balls            Death overs              Zero entry latency, maximum boundaries
Lower Order (8+)       1 to 8 balls             Final overs              Tail cameos & boundary attempts
```

### The Positional Distortion Trap
Consider two actual knocks:
* **Batter A (Opener)** scores `35 runs off 28 balls` (SR 125.0).
* **Batter B (Finisher at No. 7)** scores `28 runs off 11 balls` (SR 254.5).

Under traditional run tallies, Batter A appears superior (+35 runs vs +28 runs). In reality, Batter B's 28 off 11 in the death overs fundamentally shifted the winning probability of the match, whereas Batter A played an ordinary, replacement-level knock during the field restrictions.

**Position-Specific VORP eliminates this bias permanently by benchmarking every innings exclusively against players who bat in that exact same role.**

---

## 2. The Two Positional Grouping Schemes

Using the match-level `Batting_Order` column (1 to 11), the model provides two analytical lenses:

### Scheme 1: Individual Position Analysis
Granular role tracking where positions 1 and 2 are clubbed as opening partners:
* **`Opener`**: Batting Orders 1 & 2
* **`Number 3`**: Batting Order 3
* **`Number 4`**: Batting Order 4
* **`Number 5`**: Batting Order 5
* **`Number 6`**: Batting Order 6
* **`Number 7`**: Batting Order 7
* **`Number 8+`**: Batting Orders 8, 9, 10, 11 (combined tail)

### Scheme 2: Tactical Order Analysis
Broad tactical phases of a T20 innings:
* **`Top Order`**: Batting Orders 1, 2, 3 (Powerplay & foundation)
* **`Middle Order`**: Batting Orders 4, 5 (Middle overs 7–15 vs. spin)
* **`Finisher`**: Batting Orders 6, 7 (Death overs acceleration)
* **`Lower Order`**: Batting Orders 8, 9, 10, 11 (Tail)

---

## 3. The Sabermetric Replacement Player Theory

### Average Player vs. Replacement Player
A common misconception is that a replacement player is an "average" player.

```
Superstar (Top 10%)        -->  Jos Buttler, Virat Kohli, Andre Russell (~₹15-20+ Cr)
Average Starter (50%)      -->  Established mid-tier regular starter (~₹6-8 Cr)
Replacement Player (20%)   -->  Uncapped domestic backup, base-price squad member (~₹20-50 Lakh)
```

In sports analytics (Baseball / FanGraphs, Basketball / VORP, and modern Cricket analytics):
* An **Average Player** is a regular starter playing 14 matches a season.
* A **Replacement Player** is a freely available, substitute-level player: a bench backup, an emergency injury signing, or an uncapped domestic cricketer who plays 3 to 6 matches when a starter is unavailable.
* If a team fielded a roster entirely of replacement players, they would not win zero games; they would win roughly **25% to 30%** of their matches through baseline competency.

---

## 4. Why the "Innings-Percentile" Flaw Undervalued Replacement Level

In naive implementations, analysts take the 25th percentile across *all raw innings records*. 

### Why That Approach Fails:
In any cricket match, several batsmen get out for 0 (duck), 2, or 4 runs due to the high-variance nature of the sport. Their single-match `Batting_Impact` scores are nearly zero (`0.001` to `0.05`).
* If you take the 25th percentile of individual innings, your replacement baseline drops to a tiny **`0.18`**.
* You are no longer benchmarking against a replacement player; **you are benchmarking against getting out for a duck!**
* When an elite player averages `3.50` impact points and you divide by `0.18`, the numbers explode into unrealistic territory:
  `Player / Baseline = 3.50 / 0.18 = 19.4x (+1,840% above replacement)`

A real human replacement player does not get out for a duck in 75% of their matches. Over a body of work, an unheralded domestic backup still scores ~18–20 runs at ~120 SR.

---

## 5. The Standard Accepted Player-Season Baseline Formula

To establish the true, mathematically rigorous replacement baseline, the model follows standard sports sabermetrics:

### Step 1: Qualified Player-Season Aggregation
For each season $S$, position slot $P$, and player, we calculate their season-long average impact:
$$\text{Player\_Season\_Impact}(player, P, S) = \frac{\sum \text{Batting\_Impact}}{\text{Innings\_Played}}$$
*Qualification Filter*: Players who batted at least 3 times in that specific slot during that season (filtering out random one-ball cameos by non-specialists).

### Step 2: The 20th Percentile Bench Threshold
Within that pool of qualified player-seasons, the **Replacement Baseline** is defined as:
$$\text{Baseline\_Impact}(P, S) = \text{20th Percentile of Player\_Season\_Impact}(P, S)$$

This isolates the exact output of fringe starters and bench backups (e.g., Aaron Finch in 2022, Anuj Rawat, early-career domestic backups) who played occasionally.

### Empirical Baselines Across IPL History (19 Seasons Average)

```
Position Slot          Replacement Baseline (Impact / Match)     Typical Replacement Output
---------------------------------------------------------------------------------------------------------
Opener                 1.67                                      ~18-20 runs, faces 16-22 balls in PP
Number 3               1.54                                      ~20 runs, faces 14-18 balls
Number 4               1.54                                      ~18 runs, faces 12-16 balls
Number 5               1.17                                      ~14 runs, faces 10-14 balls
Finisher (No. 6 & 7)   0.90 – 1.12                               ~12-14 runs, faces 6-10 death balls
Lower Order (No. 8+)   0.21                                      Tailenders / brief cameos
```

> **Key Observation**: A replacement opener naturally accumulates more baseline volume (`1.67`) than a replacement finisher (`0.90 to 1.12`) because the opener faces more deliveries and has powerplay field restrictions. The model dynamically respects this positional hierarchy.

---

## 6. The Core I-VORP Math (0 to 100)

With the replacement baselines established, the model calculates value in four sequential stages:

```
[Match Scorecard]
       │
       ▼
1. Batting Impact (0 to 15+)       --> Measured relative to match par & team scoring pace
       │
       ▼
2. Position & Season Benchmark    --> Baseline_Impact(Position, Season)
       │
       ▼
3. Single-Innings I-VORP          --> Innings_I_VORP = Batting_Impact - Baseline_Impact
       │
       ▼
4. Career / Season Aggregation    --> Total_I_VORP  &  Avg_I_VORP  &  % vs Rep
```

---

### Formula 1: Single-Innings I-VORP
Every time a player walks out to bat in match $m$:
$$\text{Innings\_I\_VORP}_m = \text{Batting\_Impact}_m - \text{Baseline\_Impact}(P_m, S_m)$$

* If the player scores above replacement: $\text{Innings\_I\_VORP} > 0$ (value added).
* If the player plays sluggishly or fails: $\text{Innings\_I\_VORP} < 0$ (value lost).

---

### Formula 2: Total Cumulative I-VORP
The total volume of equity a player delivered to their franchise above replacement level:
$$\text{Total\_I\_VORP} = \sum_{m \in \text{Innings}} \text{Innings\_I\_VORP}_m$$

---

### Formula 3: Average I-VORP per Innings
The per-match quality index, independent of games played:
$$\text{Avg\_I\_VORP} = \frac{\text{Total\_I\_VORP}}{\text{Total\_Innings}}$$

---

## 7. The "% Better Than Replacement" (% vs Rep) Metric

While Total I-VORP provides raw point volume, the **`% vs Rep`** metric is the most intuitive metric for coaches, analysts, and fans:

$$\text{Pct\_Above\_Rep} = \left( \frac{\text{Total\_I\_VORP}}{\text{Total\_Replacement\_Baseline\_Sum}} \right) \times 100$$

Where $\text{Total\_Replacement\_Baseline\_Sum} = \sum \text{Baseline\_Impact}(P_m, S_m)$.

### How to Interpret `% vs Rep`:
* **`0.0%`**: The player performed exactly at replacement level.
* **`+50.0%`**: The player produced **1.5x** the match impact of a replacement player.
* **`+100.0%`**: The player produced **double (2.0x)** the match impact of a replacement player.
* **`+200.0%`**: The player produced **triple (3.0x)** the match impact of a replacement player.
* **Negative %**: The player was a net liability compared to a standard bench backup.

---

## 8. Concrete Numerical Walkthrough (Opener vs. Finisher)

### Scenario A: Elite Opener (David Warner)
* **Career Innings as Opener**: 163
* **Actual Total Impact**: `575.2` points (`Avg Impact = 3.53`)
* **Total Replacement Baseline**: `285.2` points (`Avg Baseline = 1.75`)

```
Calculation:
  Total I-VORP = 575.2 - 285.2 = +290.0 points above replacement
  Avg I-VORP   = +290.0 / 163  = +1.78 points per innings
  % vs Rep     = (+290.0 / 285.2) * 100 = +101.8%
```
*Verdict*: David Warner over his career delivered **+101.8% more impact** than a replacement opener—literally **double (2.02x)** the output of an unheralded backup opener.

---

### Scenario B: Elite Finisher (Kieron Pollard)
* **Career Innings as Finisher (No. 6 & 7)**: 81
* **Actual Total Impact**: `269.1` points (`Avg Impact = 3.32`)
* **Total Replacement Baseline**: `77.6` points (`Avg Baseline = 0.96`)

```
Calculation:
  Total I-VORP = 269.1 - 77.6  = +191.5 points above replacement
  Avg I-VORP   = +191.5 / 81   = +2.36 points per innings
  % vs Rep     = (+191.5 / 77.6) * 100 = +246.5%
```
*Verdict*: Kieron Pollard delivered **+246.5% more impact** than a replacement finisher—nearly **3.5x** the output of a backup finisher.

### Crucial Sabermetric Finding:
> **Why do elite Finishers have a higher `% vs Rep` (+246%) than elite Openers (+102%)?**  
> Because replacement-level openers still accumulate runs in the powerplay, whereas replacement-level finishers are almost entirely ineffective at striking at 170+ from ball one. **Elite death-overs hitting is the scarcest, highest-surplus skill in T20 cricket.**

---

## 9. All-Time IPL Position Leaderboards

Empirical results across 1,244 IPL matches (2008–2026):

### All-Time Opener Leaders (Scheme 1: Orders 1 & 2)
```
Rank  Player                 Innings  Runs    SR      Avg Impact   Total I-VORP   Avg I-VORP  % vs Rep   
---------------------------------------------------------------------------------------------------------
1     David Warner           163      5910    140.8   3.527        +290.03        +1.779      +101.8%    
2     Chris Gayle            122      4480    151.4   3.440        +228.70        +1.875      +119.8%    
3     KL Rahul               117      5011    141.6   3.695        +203.78        +1.742      +89.2%     
4     Virender Sehwag        98       2586    156.8   3.323        +202.39        +2.065      +164.2%    
5     Shikhar Dhawan         202      6362    128.1   2.567        +170.26        +0.843      +48.9%     
6     Virat Kohli            144      5684    141.9   3.012        +150.69        +1.046      +53.2%     
7     Adam Gilchrist         80       2069    138.4   2.966        +139.96        +1.750      +143.8%    
8     Jos Buttler            78       3003    149.6   3.686        +137.10        +1.758      +91.2%     
9     Shubman Gill           113      4335    143.2   3.192        +136.66        +1.209      +61.0%     
10    Faf du Plessis         119      4004    137.5   2.986        +134.52        +1.130      +60.9%     
```

---

### All-Time Number 3 Leaders (Scheme 1: Order 3)
```
Rank  Player                 Innings  Runs    SR      Avg Impact   Total I-VORP   Avg I-VORP  % vs Rep   
---------------------------------------------------------------------------------------------------------
1     Suresh Raina           171      4934    137.7   2.685        +201.92        +1.181      +78.5%     
2     Sanju Samson           94       3096    143.3   3.047        +147.21        +1.566      +105.7%    
3     AB de Villiers         58       2188    154.1   3.485        +119.92        +2.068      +145.8%    
4     Virat Kohli            93       2815    123.8   2.677        +115.07        +1.237      +85.9%     
5     Shaun Marsh            40       1417    134.3   4.146        +106.54        +2.664      +179.7%    
6     Shreyas Iyer           62       1863    135.8   2.876        +82.24         +1.326      +85.6%     
7     Manish Pandey          74       2012    125.3   2.463        +74.07         +1.001      +68.4%     
8     Suryakumar Yadav       65       1899    148.9   2.680        +72.86         +1.121      +71.9%     
```

---

### All-Time Finisher Leaders (Scheme 2: Tactical Orders 6 & 7)
```
Rank  Player                 Innings  Runs    SR      Avg Impact   Total I-VORP   Avg I-VORP  % vs Rep   
---------------------------------------------------------------------------------------------------------
1     Kieron Pollard         81       1730    152.6   3.323        +191.46        +2.364      +246.5%    
2     Andre Russell          68       1634    174.9   3.458        +163.60        +2.406      +228.6%    
3     Ravindra Jadeja        129      2101    129.4   2.063        +139.64        +1.082      +110.4%    
4     Dinesh Karthik         68       1334    161.5   2.822        +125.12        +1.840      +187.4%    
5     Axar Patel             89       1334    130.8   2.324        +113.37        +1.274      +121.3%    
6     Hardik Pandya          67       1177    154.5   2.564        +104.25        +1.556      +154.3%    
7     M S Dhoni              77       1434    124.9   2.334        +101.74        +1.321      +130.5%    
```

---

## 10. Player Multi-Position Profiles (Case Studies)

One of the most powerful applications of position-specific I-VORP is evaluating **where a batsman produces peak franchise value**.

### Case 1: Virat Kohli (Top Order Dominance)
```
=======================================================
  I-VORP Profile: Virat Kohli
=======================================================

[Scheme 1: Individual Position Breakdown]
Position        Innings  Runs    SR      Total I-VORP   Avg I-VORP  % vs Rep   
------------------------------------------------------------------------------
Opener          144      5684    141.9   +150.69        +1.046      +53.2%     
Number 3        93       2815    123.8   +115.07        +1.237      +85.9%     
Number 4        13       376     131.5   +20.25         +1.557      +107.3%    
Number 5        8        173     111.6   +12.59         +1.574      +119.5%    
Number 6        13       237     144.5   +20.63         +1.587      +196.2%    
Number 7        4        51      124.4   +11.61         +2.901      +407.7%    

[Scheme 2: Tactical Order Breakdown]
Tactical Slot   Innings  Runs    SR      Total I-VORP   Avg I-VORP  % vs Rep   
------------------------------------------------------------------------------
Top Order       237      8499    135.3   +289.93        +1.223      +73.8%     
Middle Order    21       549     124.5   +31.64         +1.507      +103.4%    
Finisher        17       288     140.5   +33.02         +1.942      +262.5%    
```

---

### Case 2: AB de Villiers (The Middle-Order Benchmark)
```
=======================================================
  I-VORP Profile: AB de Villiers
=======================================================

[Scheme 1: Individual Position Breakdown]
Position        Innings  Runs    SR      Total I-VORP   Avg I-VORP  % vs Rep   
------------------------------------------------------------------------------
Opener          2        10      142.9   +1.12          +0.560      +64.5%     
Number 3        58       2188    154.1   +119.92        +2.068      +145.8%    
Number 4        70       1956    146.0   +125.43        +1.792      +109.1%    
Number 5        35       938     158.4   +76.12         +2.175      +184.2%    
Number 6        5        70      159.1   +4.81          +0.962      +152.0%    

[Scheme 2: Tactical Order Breakdown]
Tactical Slot   Innings  Runs    SR      Total I-VORP   Avg I-VORP  % vs Rep   
------------------------------------------------------------------------------
Top Order       60       2198    154.0   +122.50        +2.042      +142.5%    
Middle Order    105      2894    149.8   +201.55        +1.920      +129.8%    
Finisher        5        70      159.1   +4.81          +0.962      +152.0%    
```

### Single-Season Positional Greats (Ranked by % Better Than Replacement)

By analyzing individual seasons (`--by-season`) ranked by `% vs Rep`, the model reveals the most dominant peak single-season campaigns relative to their positional replacement benchmark:

#### Top Opener Seasons by % vs Rep (min 10 innings):
```
Rank  Season   Player                 Innings  Runs    SR      Avg Impact   Total I-VORP   Avg I-VORP  % vs Rep   
-------------------------------------------------------------------------------------------------------------------
1     2009     Matthew Hayden         12       572     144.8   6.303        +62.19         +5.183      +462.5%    
2     2008     Sanath Jayasuriya      14       514     166.3   4.597        +52.68         +3.763      +451.2%    
3     2012     Chris Gayle            13       729     162.7   5.270        +55.83         +4.294      +440.4%    
4     2008     Shaun Marsh            11       616     139.7   4.326        +38.42         +3.492      +418.8%    
5     2008     Virender Sehwag        14       406     184.6   3.931        +43.36         +3.097      +371.4%    
```

#### Top Finisher Seasons by % vs Rep (min 7 innings):
```
Rank  Season   Player                 Innings  Runs    SR      Avg Impact   Total I-VORP   Avg I-VORP  % vs Rep   
-------------------------------------------------------------------------------------------------------------------
1     2019     Andre Russell          7        264     192.7   5.262        +32.64         +4.663      +779.4%    
2     2019     Hardik Pandya          11       310     198.7   4.981        +48.21         +4.383      +732.5%    
3     2012     Steve Smith            7        187     127.2   5.864        +35.41         +5.059      +628.0%    
4     2021     Andre Russell          7        178     154.8   3.712        +21.75         +3.107      +514.0%    
5     2008     Mark Boucher           7        153     131.9   3.955        +23.16         +3.309      +512.0%    
```

---

## 11. Codebase & Data Implementation Reference

| Component | File / Path | Responsibility |
|---|---|---|
| **Core Algorithm** | [`scripts/vorp.py`](file:///d:/projects/ipl_impact/scripts/vorp.py) | Position mapping, 20th percentile baseline derivation, I-VORP math, `% vs Rep`, career and single-season aggregations. |
| **CLI Dispatcher** | [`scripts/cli.py`](file:///d:/projects/ipl_impact/scripts/cli.py) | Exposes `vorp leaders` (with `--sort-by`, `--by-season`, `--min-pct`) and `vorp player`. |
| **Interactive Studio** | [`app.py`](file:///d:/projects/ipl_impact/app.py) | 5-tab Streamlit dashboard with position VORP studio, profiler, and % vs Rep filters. |
| **Master Dataset (CSV)** | [`scorecards_csv/results/all_batting_with_vorp.csv`](file:///d:/projects/ipl_impact/scorecards_csv/results/all_batting_with_vorp.csv) | 19,113 innings with `IVORP_Individual`, `IVORP_Tactical`, `Pct_Above_Rep_Ind`, and `Pct_Above_Rep_Tact`. |
| **Master Dataset (Parquet)** | [`scorecards_csv/results/all_batting_with_vorp.parquet`](file:///d:/projects/ipl_impact/scorecards_csv/results/all_batting_with_vorp.parquet) | Compressed binary format for instant sub-50ms Pandas loading. |

### CLI Usage Commands

```bash
# 1. Career Position Leaderboards by % vs Rep or Total I-VORP
python -m scripts.cli vorp leaders "Opener" --sort-by pct_above_rep --limit 20
python -m scripts.cli vorp leaders "Number 3" --sort-by total_ivorp --limit 20
python -m scripts.cli vorp leaders "Finisher" --scheme tactical --sort-by pct_above_rep --limit 20

# 2. Greatest Single-Season Positional Campaigns in History
python -m scripts.cli vorp leaders "Opener" --by-season --sort-by pct_above_rep --min-innings 10 --limit 15
python -m scripts.cli vorp leaders "Finisher" --scheme tactical --by-season --sort-by pct_above_rep --min-innings 7 --limit 15

# 3. Filter by Specific Season or Min % Threshold
python -m scripts.cli vorp leaders "Opener" --season 2016 --sort-by total_ivorp --limit 10
python -m scripts.cli vorp leaders "Middle Order" --scheme tactical --min-pct 100 --limit 15

# 4. Player Multi-Position Profile
python -m scripts.cli vorp player "Virat Kohli"
python -m scripts.cli vorp player "AB de Villiers"
python -m scripts.cli vorp player "Andre Russell"
```
