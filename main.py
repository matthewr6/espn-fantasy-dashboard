import streamlit as st
import pandas as pd
from espn_api.football import League

# =========================
# CONSTANTS (EDIT THESE)
# =========================
LEAGUE_ID = st.secrets["league_id"]
YEAR = st.secrets["year"]
ESPN_S2 = st.secrets["espn_s2"]
SWID = st.secrets["swid"]

# =========================
# Helper Functions
# =========================
def normalize_slot(slot: str) -> str:
    if slot == "RB/WR/TE":
        return "FLEX"
    if slot == "BENCH":
        return "BE"
    return slot

SLOT_ORDER = ["QB", "RB", "WR", "TE", "FLEX", "D/ST", "K", "BE"]
SLOT_ORDER_MAP = {slot: i for i, slot in enumerate(SLOT_ORDER)}

def get_team_name(team, team_lookup):
    if isinstance(team, int):
        if team == 0:
            return None
        return team_lookup.get(team)
    return team.team_name

def build_player_df(lineup):
    rows = []
    for p in lineup:
        slot = normalize_slot(p.slot_position)
        display_slot = f"BE ({p.position})" if slot == "BE" else slot
        rows.append({
            "Slot": display_slot,
            "Player": p.name,
            "Actual": p.points or 0,
            "Projected": p.projected_points or 0,
            "SlotOrder": SLOT_ORDER_MAP.get(slot, 999)
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(["SlotOrder"]).drop(columns="SlotOrder")

    # Totals
    total_row = pd.DataFrame({
        "Slot": ["TOTAL"],
        "Player": [""],
        "Actual": [df["Actual"].sum()],
        "Projected": [df["Projected"].sum()]
    })
    df = pd.concat([df, total_row], ignore_index=True)

    # Format numbers
    df["Actual"] = df["Actual"].map("{:.2f}".format)
    df["Projected"] = df["Projected"].map("{:.2f}".format)
    return df

# =========================
# Load League
# =========================
league = League(
    league_id=LEAGUE_ID,
    year=YEAR,
    espn_s2=ESPN_S2,
    swid=SWID,
)
team_lookup = {team.team_id: team.team_name for team in league.teams}
team_names = sorted(team_lookup.values())

# =========================
# Week Selector
# =========================
max_week = league.current_week
selected_week = st.selectbox(
    "Select Week",
    list(range(1, max_week + 1)),
    index=max_week-1
)
box_scores = league.box_scores(selected_week)

# =========================
# Mode Selector
# =========================
mode = st.radio("Choose matchup type:", ["Default Matchup", "Custom Teams"])

# =========================
# Helper functions
# =========================
def get_team_matchup(team_name):
    for matchup in box_scores:
        home = get_team_name(matchup.home_team, team_lookup)
        away = get_team_name(matchup.away_team, team_lookup)
        if home == team_name or away == team_name:
            return matchup
    return None

def get_lineup_for_team(team_name, matchup):
    if matchup is None:
        return []
    home = get_team_name(matchup.home_team, team_lookup)
    away = get_team_name(matchup.away_team, team_lookup)
    if home == team_name:
        return matchup.home_lineup
    if away == team_name:
        return matchup.away_lineup
    return []

# =========================
# Select Teams Based on Mode
# =========================
if mode == "Default Matchup":
    # Build list of default matchups
    matchup_labels = []
    matchup_map = {}
    for matchup in box_scores:
        home = get_team_name(matchup.home_team, team_lookup)
        away = get_team_name(matchup.away_team, team_lookup)
        if not home or not away:
            continue
        label = f"{home} vs {away}"
        matchup_labels.append(label)
        matchup_map[label] = matchup

    selected_matchup_label = st.selectbox("Select Matchup", matchup_labels)
    selected_matchup = matchup_map[selected_matchup_label]

    home_team_name = get_team_name(selected_matchup.home_team, team_lookup)
    away_team_name = get_team_name(selected_matchup.away_team, team_lookup)

    home_lineup = build_player_df(selected_matchup.home_lineup)
    away_lineup = build_player_df(selected_matchup.away_lineup)

else:  # Custom Teams
    col_home, col_away = st.columns(2)
    with col_home:
        home_team_name = st.selectbox("Select Home Team", team_names, index=0)
    with col_away:
        away_team_name = st.selectbox("Select Away Team", team_names, index=1)

    home_matchup = get_team_matchup(home_team_name)
    away_matchup = get_team_matchup(away_team_name)

    home_lineup = build_player_df(get_lineup_for_team(home_team_name, home_matchup))
    away_lineup = build_player_df(get_lineup_for_team(away_team_name, away_matchup))

# =========================
# Display Side by Side
# =========================
st.markdown(f"### {home_team_name} vs {away_team_name}")
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"#### {home_team_name}")
    st.table(home_lineup)

with col2:
    st.markdown(f"#### {away_team_name}")
    st.table(away_lineup)
