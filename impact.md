# IPL Batting Impact Model: Complete 0-to-100 Mathematical & Architectural Specification

This document provides an exhaustive, end-to-end explanation of the **IPL Batting Impact Model** implemented in this repository. It covers the cricket philosophy, mathematical formulation, step-by-step algorithms, edge-case handlings, and macro-level aggregations.

---

## Table of Contents

1. [Philosophy & Motivation: Why Traditional Metrics Fail T20](#1-philosophy--motivation-why-traditional-metrics-fail-t20)
2. [Data Ingestion & Extraction Engine](#2-data-ingestion--extraction-engine)
3. [The Contextual Baseline Ratios](#3-the-contextual-baseline-ratios)
4. [Positive Z-Score Normalization Algorithm](#4-positive-z-score-normalization-algorithm)
5. [The Interaction Metric & Weighting Scheme](#5-the-interaction-metric--weighting-scheme)
6. [The "Anchor Trap" Negative Impact Penalty](#6-the-anchor-trap-negative-impact-penalty)
7. [The High-Volume Accelerator Multiplier](#7-the-high-volume-accelerator-multiplier)
8. [Comprehensive Numerical Walkthrough (Step-by-Step)](#8-comprehensive-numerical-walkthrough-step-by-step)
9. [Macro-Level Impact Aggregations & Leaderboards](#9-macro-level-impact-aggregations--leaderboards)
10. [Why Bowling is Kept Separate (Model Boundary)](#10-why-bowling-is-kept-separate-model-boundary)
11. [Codebase Reference Map](#11-codebase-reference-map)

---

## 1. Philosophy & Motivation: Why Traditional Metrics Fail T20

In Test cricket and One Day Internationals (ODIs), wickets are the primary scarce resource. In Twenty20 (T20) cricket, **balls (120 deliveries per team) are the rarest commodity**.

Traditional cricket statistics break down in T20:
- **Raw Runs**: Scoring 50 runs off 48 balls in a chase of 210 hurts the team more than scoring 25 off 10 balls.
- **Traditional Batting Average ($\frac{\text{Runs}}{\text{Outs}}$)**: Heavily biases towards red-ink "not-outs" accumulated in the lower order or anchors who preserve their wicket at the cost of team run rate.
- **Raw Strike Rate**: Ignores pitch conditions. A strike rate of 145 on an Ahmedabad highway where par score is 230 is below average; a strike rate of 145 on a turning Chepauk pitch where par is 135 is match-winning.

### The Objective of the Batting Impact Model
The model quantifies:
> *"Given the pitch and match conditions, how much did this batsman accelerate or hinder their team's scoring pace relative to all players in that match, and how much volume did they contribute?"*

---

## 2. Data Ingestion & Extraction Engine

The raw data originates as HTML match scorecards scraped from Howstat and saved into Excel workbooks (`scorecards/base/IPL_Scorecards_XXXX_to_XXXX.xlsx`).

```
Scorecard (Excel Sheet)
│
├── Match Header / Meta
├── BATTING Team 1 ──> [Player, How Out, Runs, Balls, 4s, 6s, SR, % Runs]
├── Extras & TOTAL ──> "TOTAL (20.0 overs) 198"
├── BOWLING Team 2 ──> [Bowler, Overs, Maidens, Runs, Wickets, Economy]
├── BATTING Team 2 ──> [Player, How Out, Runs, Balls, 4s, 6s, SR, % Runs]
└── Extras & TOTAL ──> "TOTAL (19.2 overs) 201"
```

### Parsing Match & Team Aggregates
Implemented in [`scripts/common.py`](file:///d:/projects/ipl_impact/scripts/common.py) and [`scripts/scorecard.py`](file:///d:/projects/ipl_impact/scripts/scorecard.py):

1. **Overs to Balls Conversion**:
   Cricket overs use base-6 fractional notation (e.g., $19.3$ overs means $19$ overs and $3$ balls):
   $$\text{Balls} = \lfloor \text{Overs} \rfloor \times 6 + \text{round}\left( (\text{Overs} - \lfloor \text{Overs} \rfloor) \times 10 \right)$$
   *Example*: $19.3 \rightarrow 19 \times 6 + 3 = 117 \text{ balls}$.

2. **Extracting Team Runs and Balls**:
   The parser inspects the `TOTAL` row using regex `\(([\d.]+) overs` to capture total team runs and balls.
   $$\text{Team SR} = \left(\frac{\text{Team Runs}}{\text{Team Balls}}\right) \times 100$$

3. **Match Aggregate Baseline**:
   $$\text{Total Match Runs} = \text{Runs}_{\text{Team 1}} + \text{Runs}_{\text{Team 2}}$$
   $$\text{Total Match Balls} = \text{Balls}_{\text{Team 1}} + \text{Balls}_{\text{Team 2}}$$
   $$\text{Match SR} = \left(\frac{\text{Total Match Runs}}{\text{Total Match Balls}}\right) \times 100$$

4. **Player Name Sanitization**:
   Player names often contain symbols (`*` for not-out, `†` for wicketkeeper, `(c)` for captain). The system cleans these strings into canonical forms using [`clean_player_name_strict()`](file:///d:/projects/ipl_impact/scripts/common.py#L185-L190).

---

## 3. The Contextual Baseline Ratios

For each batsman $i$ in a match, the model constructs four relative performance ratios:

| Ratio Name | Formula | Meaning |
|---|---|---|
| **`SR_Team_SR`** | $\frac{\text{SR}_i}{\text{Team SR}}$ | Did the batsman score faster or slower than their own teammates? |
| **`Runs_Team_Runs`** | $\frac{\text{Runs}_i}{\text{Team Runs}}$ | What proportion of the team's total runs came from this batsman? |
| **`SR_Match_SR`** | $\frac{\text{SR}_i}{\text{Match SR}}$ | Did the batsman score faster or slower than the pitch/match standard? |
| **`Runs_Match_Runs`** | $\frac{\text{Runs}_i}{\text{Total Match Runs}}$ | What proportion of the entire match's runs did this batsman produce? |

If $\text{Team SR} = 0$ or $\text{Match SR} = 0$, the ratio safely defaults to $1.0$. If runs equal $0$, the ratio defaults to $0.0$.

---

## 4. Positive Z-Score Normalization Algorithm

### Why Raw Ratios Cannot Be Directly Multiplied
1. **Scale Disparity**: In low-scoring games vs high-scoring shootouts, run percentages and strike-rate ratios fluctuate differently.
2. **The Negative Product Fallacy**: If standard z-scores were negative, multiplying a negative SR z-score by a negative Runs z-score would yield a **positive** impact product ($(-2) \times (-2) = +4$). That would disastrously award high impact to a batsman who scored few runs at a terrible strike rate!

### The Algorithm: `positive_z_score_normalize`
Implemented in [`scripts/common.py`](file:///d:/projects/ipl_impact/scripts/common.py#L164-L174):

For a feature vector $X = [x_1, x_2, \dots, x_N]$ containing values for all batters in the match:

1. **Calculate Sample Mean and Standard Deviation**:
   $$\mu = \frac{1}{N} \sum_{k=1}^N x_k$$
   $$\sigma = \sqrt{\frac{1}{N} \sum_{k=1}^N (x_k - \mu)^2}$$

2. **Compute Standard Z-Scores**:
   $$z_i = \begin{cases} \frac{x_i - \mu}{\sigma}, & \text{if } \sigma > 0 \\ 0, & \text{otherwise} \end{cases}$$

3. **Determine Minimum Z-Score and Positive Shift**:
   Let $z_{\min} = \min(z_1, z_2, \dots, z_N)$.
   $$\text{shift} = \begin{cases} -z_{\min} + 0.01, & \text{if } z_{\min} \le 0 \\ 0, & \text{if } z_{\min} > 0 \end{cases}$$

4. **Compute Strictly Positive Normalized Value**:
   $$Z^+_i = z_i + \text{shift}$$

This guarantees:
- Every normalized score $Z^+_i \ge 0.01$.
- The relative variance, distances, and distributions of the innings in that specific match are strictly preserved.

This normalization is executed independently for each match across four dimensions:
- $\text{Norm\_SR\_Team}$
- $\text{Norm\_Runs\_Team}$
- $\text{Norm\_SR\_Match}$
- $\text{Norm\_Runs\_Match}$

---

## 5. The Interaction Metric & Weighting Scheme

A great T20 innings requires **both** volume and strike-rate efficiency. Scoring 15 runs off 6 balls is high SR but low volume; scoring 60 runs off 55 balls is high volume but low SR. Multiplying the normalized terms captures this joint interaction.

### Metric 1: Team Context Interaction
$$\text{Metric}_1 = \text{Norm\_SR\_Team}_i \times \text{Norm\_Runs\_Team}_i$$

### Metric 2: Match Context Interaction
$$\text{Metric}_2 = \text{Norm\_SR\_Match}_i \times \text{Norm\_Runs\_Match}_i$$

### Base Impact Formula
The composite base impact score balances team-level role execution with pitch-level par conditions:

$$\text{BaseImpact} = 0.40 \times \text{Metric}_1 + 0.60 \times \text{Metric}_2$$

```
                         ┌─── [Norm_SR_Team]   x [Norm_Runs_Team]  ───> Metric 1 (40%)
[All Batters in Match] ──┤                                                              ───> Base Impact
                         └─── [Norm_SR_Match]  x [Norm_Runs_Match] ───> Metric 2 (60%)
```

- **60% Weight on Match Context**: Grounds the player against the actual difficulty of the pitch experienced by both sides.
- **40% Weight on Team Context**: Evaluates the batsman's specific contribution to their own team's operational strategy.

---

## 6. The "Anchor Trap" Negative Impact Penalty

One of the most innovative features of this model is penalizing **innings that actively harm the team by wasting deliveries**. If a batsman consumes a significant share of team runs but scores significantly slower than their teammates, they suffocate the innings.

### Trigger Criteria
The penalty triggers if and only if:
1. **Significant Volume**: $\text{Runs\_Team\_Runs} > 0.15$ (scored more than 15% of team runs)
2. **Sub-par Strike Rate**: $\text{SR\_Team\_SR} < 0.80$ (scored at less than 80% of team strike rate)

### Penalty Computation Steps
Implemented in [`scripts/impact.py`](file:///d:/projects/ipl_impact/scripts/impact.py#L106-L123):

#### Step A: Base Rate Penalty
- If $\text{SR\_Team\_SR} \le 0.50$ (extreme drag):
  $$\text{base\_penalty} = 0.40 \quad (40\%)$$
- If $0.50 < \text{SR\_Team\_SR} < 0.80$:
  $$\text{base\_penalty} = 0.10 + (0.80 - \text{SR\_Team\_SR})$$
  *(e.g., if SR ratio is $0.70$, penalty is $0.10 + 0.10 = 0.20$ or 20%)*

#### Step B: Volume Excess Penalty
A batter who scores slowly while making 20% of team runs is damaging; a batter who scores slowly while eating up 40% of team runs is crippling.
$$\text{runs\_excess} = \min(\text{Runs\_Team\_Runs}, 0.40) - 0.15$$
$$\text{additional\_penalty} = \min(\text{runs\_excess} \times 2.0, 0.50)$$

#### Step C: Combined Compounded Penalty
$$\text{penalty} = 1.0 - \left[ (1.0 - \text{base\_penalty}) \times (1.0 - \text{additional\_penalty}) \right]$$

#### Step D: Apply Penalty
$$\text{AdjustedImpact} = \text{BaseImpact} \times (1.0 - \text{penalty})$$

*Result*: Up to a 70% reduction in impact score for harmful, sluggish innings.

---

## 7. The High-Volume Accelerator Multiplier

Conversely, when a batsman scores heavily ($\ge 50$ runs) while significantly outscoring their team's strike rate ($> 110\%$), they have played an elite, match-defining knock. The model awards an exponential booster.

### Trigger Criteria
1. $\text{Runs} \ge 50$
2. $\text{SR\_Team\_SR} > 1.10$

### Multiplier Formulation
$$\text{multiplier} = \begin{cases} 2^{\frac{\text{Runs} - 50}{100}}, & \text{if } 50 \le \text{Runs} < 150 \\ 2.0, & \text{if } \text{Runs} \ge 150 \end{cases}$$

### Milestone Multiplier Progression

| Runs Scored | Exponent $\frac{\text{Runs}-50}{100}$ | Multiplier $2^{\text{exponent}}$ | Effect on Impact |
|:---:|:---:|:---:|:---|
| **50** | $0.00$ | $2^0 = \mathbf{1.000\times}$ | Entry threshold (no boost yet) |
| **75** | $0.25$ | $2^{0.25} \approx \mathbf{1.189\times}$ | $+18.9\%$ bonus |
| **100** | $0.50$ | $2^{0.50} \approx \mathbf{1.414\times}$ | $+41.4\%$ bonus |
| **125** | $0.75$ | $2^{0.75} \approx \mathbf{1.682\times}$ | $+68.2\%$ bonus |
| **150+** | $1.00$ | $2^{1.00} = \mathbf{2.000\times}$ | Maximum capped doubling ($+100\%$) |

### Final Match Impact Index
$$\text{ImpactIndex} = \text{round}(\text{AdjustedImpact} \times \text{multiplier}, 4)$$

---

## 8. Comprehensive Numerical Walkthrough (Step-by-Step)

To see the math in action, consider a real match scenario:

### Match Summary
- **Team A**: 200 runs off 120 balls ($\text{Team A SR} = 166.67$)
- **Team B**: 180 runs off 120 balls ($\text{Team B SR} = 150.00$)
- **Match Aggregates**:
  - $\text{Total Match Runs} = 380$
  - $\text{Total Match Balls} = 240$
  - $\text{Match SR} = \frac{380}{240} \times 100 = 158.33$

### Three Batters Under Evaluation
1. **Batter 1 (Match-Winning Centurion)**: 100 runs off 50 balls ($\text{SR} = 200.00$) for Team A.
2. **Batter 2 (Anchor Trap)**: 45 runs off 40 balls ($\text{SR} = 112.50$) for Team A.
3. **Batter 3 (Death-Overs Finisher)**: 30 runs off 10 balls ($\text{SR} = 300.00$) for Team B.

---

### Step 1: Compute Context Ratios

#### Batter 1 (100 off 50, Team A)
- $\text{SR\_Team\_SR} = \frac{200.00}{166.67} = 1.200$
- $\text{Runs\_Team\_Runs} = \frac{100}{200} = 0.500$
- $\text{SR\_Match\_SR} = \frac{200.00}{158.33} = 1.263$
- $\text{Runs\_Match\_Runs} = \frac{100}{380} = 0.263$

#### Batter 2 (45 off 40, Team A)
- $\text{SR\_Team\_SR} = \frac{112.50}{166.67} = 0.675$ *(< 0.80: Potential penalty!)*
- $\text{Runs\_Team\_Runs} = \frac{45}{200} = 0.225$ *(> 0.15: Meets volume threshold!)*
- $\text{SR\_Match\_SR} = \frac{112.50}{158.33} = 0.711$
- $\text{Runs\_Match\_Runs} = \frac{45}{380} = 0.118$

#### Batter 3 (30 off 10, Team B)
- $\text{SR\_Team\_SR} = \frac{300.00}{150.00} = 2.000$
- $\text{Runs\_Team\_Runs} = \frac{30}{180} = 0.167$
- $\text{SR\_Match\_SR} = \frac{300.00}{158.33} = 1.895$
- $\text{Runs\_Match\_Runs} = \frac{30}{380} = 0.079$

---

### Step 2: Positive Z-Score Normalization (Simulated)
Suppose across all 14 batters in the match, the normalization produces:

| Batter | Norm_SR_Team | Norm_Runs_Team | Norm_SR_Match | Norm_Runs_Match |
|---|:---:|:---:|:---:|:---:|
| **Batter 1 (Centurion)** | $1.85$ | $2.40$ | $1.90$ | $2.35$ |
| **Batter 2 (Anchor Trap)** | $0.55$ | $1.20$ | $0.60$ | $1.15$ |
| **Batter 3 (Finisher)** | $2.95$ | $0.85$ | $2.80$ | $0.80$ |

---

### Step 3: Interaction Metrics & Base Impact

#### Batter 1:
- $\text{Metric}_1 = 1.85 \times 2.40 = 4.440$
- $\text{Metric}_2 = 1.90 \times 2.35 = 4.465$
- $\text{BaseImpact} = 0.40(4.440) + 0.60(4.465) = 1.776 + 2.679 = \mathbf{4.455}$

#### Batter 2:
- $\text{Metric}_1 = 0.55 \times 1.20 = 0.660$
- $\text{Metric}_2 = 0.60 \times 1.15 = 0.690$
- $\text{BaseImpact} = 0.40(0.660) + 0.60(0.690) = 0.264 + 0.414 = \mathbf{0.678}$

#### Batter 3:
- $\text{Metric}_1 = 2.95 \times 0.85 = 2.5075$
- $\text{Metric}_2 = 2.80 \times 0.80 = 2.2400$
- $\text{BaseImpact} = 0.40(2.5075) + 0.60(2.2400) = 1.003 + 1.344 = \mathbf{2.347}$

---

### Step 4: Penalty & Multiplier Modifications

#### Evaluating Batter 2 for Penalty:
- $\text{Runs\_Team\_Runs} = 0.225 > 0.15$ (True)
- $\text{SR\_Team\_SR} = 0.675 < 0.80$ (True $\rightarrow$ **Penalty Triggered!**)
- $\text{base\_penalty} = 0.10 + (0.80 - 0.675) = 0.10 + 0.125 = \mathbf{0.225}$
- $\text{runs\_excess} = \min(0.225, 0.40) - 0.15 = 0.075$
- $\text{additional\_penalty} = \min(0.075 \times 2.0, 0.50) = \mathbf{0.150}$
- $\text{penalty} = 1.0 - [(1.0 - 0.225) \times (1.0 - 0.150)] = 1.0 - [0.775 \times 0.850] = 1.0 - 0.65875 = \mathbf{0.34125}$ (34.1% reduction)
- $\text{AdjustedImpact} = 0.678 \times (1.0 - 0.34125) = \mathbf{0.4466}$

#### Evaluating Batter 1 for Multiplier:
- $\text{Runs} = 100 \ge 50$ (True)
- $\text{SR\_Team\_SR} = 1.20 > 1.10$ (True $\rightarrow$ **Multiplier Triggered!**)
- $\text{exponent} = \frac{100 - 50}{100} = 0.50$
- $\text{multiplier} = 2^{0.50} \approx \mathbf{1.4142}$
- $\text{ImpactIndex} = 4.455 \times 1.4142 = \mathbf{6.3003}$

#### Evaluating Batter 3:
- Runs $< 50$ (No multiplier)
- Penalty conditions not met.
- $\text{ImpactIndex} = \mathbf{2.3470}$

---

### Comparison of Final Scores

```
┌────────────────────────────────────────┬─────────────┬──────────────┬──────────────┐
│ Player                                 │ Traditional │ Impact Index │ Evaluation   │
├────────────────────────────────────────┼─────────────┼──────────────┼──────────────┤
│ Batter 1 (100 off 50 balls, SR 200)    │ 100 runs    │    6.3003    │ Legendary    │
│ Batter 3 (30 off 10 balls, SR 300)     │  30 runs    │    2.3470    │ High Impact  │
│ Batter 2 (45 off 40 balls, SR 112.5)   │  45 runs    │    0.4466    │ Sub-par Drag │
└────────────────────────────────────────┴─────────────┴──────────────┴──────────────┘
```

*Crucial insight*: Traditional scorecards make Batter 2 look like the second-best batsman with 45 runs. The Batting Impact Model correctly demonstrates that Batter 3's quick-fire 30 off 10 had **over 5x the positive match impact** of Batter 2's sluggish 45 off 40.

---

## 9. Macro-Level Impact Aggregations & Leaderboards

Implemented in [`scripts/impact.py`](file:///d:/projects/ipl_impact/scripts/impact.py):

### 1. Cumulative Player Impact
$$\text{TotalImpact}(p) = \sum_{m \in \text{Matches}} \text{ImpactIndex}(p, m)$$
Measures career-long volume of match impact. High-volume, high-SR all-time greats (e.g., AB de Villiers, Suresh Raina, David Warner, Chris Gayle, Virat Kohli, Jos Buttler) dominate this ranking.

### 2. Average Impact per Innings
$$\text{AvgImpactPerMatch}(p) = \frac{\sum \text{ImpactIndex}(p, m)}{\text{InningsCount}(p)}$$
Typically filtered with a minimum run threshold (e.g., $\ge 500$ runs) to identify players who consistently outperform match par whenever they walk out to bat.

### 3. Individual Season Impact
$$\text{SeasonalImpact}(p, s) = \sum_{m \in \text{Season } s} \text{ImpactIndex}(p, m)$$
Identifies the most dominant individual seasons in IPL history (e.g., Virat Kohli 2016, Jos Buttler 2022, Chris Gayle 2011/2012).

### 4. Impact Batsman of the Match (BOTM)
For every match $m$, the model finds the single highest impact batsman:
$$\text{BOTM}(m) = \arg\max_{p \in \text{Match } m} \left( \text{ImpactIndex}(p, m) \right)$$
The player with the most BOTM designations across their career represents the most frequent match-winner.

### 5. Percentage Match Impact Share
In [`app.py`](file:///d:/projects/ipl_impact/app.py#L497-L503):
$$\text{MatchImpactPct}(p, m) = \left( \frac{\text{ImpactIndex}(p, m)}{\sum_{k \in \text{Match } m} \text{ImpactIndex}(k, m)} \right) \times 100$$
Reveals what share of the total batting performance in the match belonged to that individual.

---

## 10. Why Bowling is Kept Separate (Model Boundary)

A deliberate architecture decision was made in this codebase: **The Impact Model is strictly batting-only.**

### Rationale
1. **Asymmetry in Wicket Value**: In T20 cricket, taking the wicket of an opener or top-order powerhouse is fundamentally different from cleaning up numbers 9, 10, or 11 in the 20th over. Without ball-by-ball dismissal context, equal wicket weighting distorts reality.
2. **Phase of the Match Distortion**: Overs 1-6 (Powerplay) and Overs 16-20 (Death) inherently yield higher economy rates than middle overs (7-15). Rewarding or punishing raw economy rates without phase segmentation would penalize elite death-over bowlers who bowl the hardest overs.
3. **Data Integrity**: Raw scorecard data lacks ball-by-ball phase timestamps. Consequently, bowling analysis in [`scripts/bowling.py`](file:///d:/projects/ipl_impact/scripts/bowling.py) is kept as transparent, unadulterated descriptive statistics (Overs, Maidens, Runs, Wickets, Economy Rate, Bowling Average).

---

## 11. Codebase Reference Map

| Functionality | Primary File | Key Functions / Classes |
|---|---|---|
| **Impact Algorithm** | [`scripts/impact.py`](file:///d:/projects/ipl_impact/scripts/impact.py) | `_build_player_data_for_match()`, `_apply_impact_index()`, `load_innings_data()` |
| **Excel Batch Writer** | [`scripts/add_impact.py`](file:///d:/projects/ipl_impact/scripts/add_impact.py) | `process_file()`, `add_batting_impact()` |
| **Normalization & Math** | [`scripts/common.py`](file:///d:/projects/ipl_impact/scripts/common.py) | `positive_z_score_normalize()`, `overs_to_balls()`, `extract_team_runs_and_overs()` |
| **Scorecard Parsing** | [`scripts/scorecard.py`](file:///d:/projects/ipl_impact/scripts/scorecard.py) | `extract_batting_blocks()`, `extract_bowling_blocks()`, `extract_team_totals()` |
| **Traditional Batting** | [`scripts/batting.py`](file:///d:/projects/ipl_impact/scripts/batting.py) | `summarize_batting_df()`, `get_top_strike_rate()` |
| **Traditional Bowling** | [`scripts/bowling.py`](file:///d:/projects/ipl_impact/scripts/bowling.py) | `summarize_bowling_df()`, `bowling_leaderboard()` |
| **Interactive Dashboard** | [`app.py`](file:///d:/projects/ipl_impact/app.py) | Streamlit UI tabs: Batting Scorecard, Impact Leaders, Batting Trends |
| **CLI Dispatcher** | [`scripts/cli.py`](file:///d:/projects/ipl_impact/scripts/cli.py) | Subcommands: `add-impact`, `convert-csv`, `batting`, `bowling`, `impact`, `vorp` |
