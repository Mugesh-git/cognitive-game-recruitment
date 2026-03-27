# app.py
"""
Streamlit dashboard that launches cognitive games (external scripts),
then discovers each game's result after the game finishes by:
 - checking likely output filenames, OR
 - scanning the game's stdout for JSON,
then normalizes skill names and displays per-game + aggregated visualizations.

Requires: streamlit, pandas, plotly, altair
Run: streamlit run app.py
"""

import streamlit as st
import subprocess, sys, json, time, os, re
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import altair as alt
from typing import Optional, Dict, Any, List

st.set_page_config(page_title="Cognitive Games Hub", layout="wide", page_icon="🧠")

ROOT = Path.cwd()

# ---------------------------
# Game configuration
# - script: file to run
# - candidate_result_files: list of filenames the script may write (checked after run)
# - match_game_names: list of substrings to match if reading JSON from lines/stdout
# ---------------------------
GAMES = {
    "Color Game (Stroop Test)": {
        "script": "Stroop1.py",
        "candidate_result_files": ["game_results.json", "stroop_results.json"],
        "match_game_names": ["Color Game", "Stroop"]
    },
    "Pattern Matching": {
        "script": "Pattern_Matching_1.py",
        "candidate_result_files": ["pattern_search_results.json", "pattern_matching_results.json"],
        "match_game_names": ["Pattern Matching", "pattern"]
    },
    "Tower of Hanoi": {
        "script": "Tower_of_Hanoi_2.py",
        "candidate_result_files": ["tower_of_hanoi_final.json", "tower_results.json"],
        "match_game_names": ["Tower of Hanoi", "Tower"]
    },
    "Slide Puzzle": {
        "script": "slide_puzzle_multi_round.py",
        "candidate_result_files": ["slide_puzzle_results.json", "slide_results.json"],
        "match_game_names": ["Slide Puzzle", "Slide"]
    },
    "Memory Grid": {
        "script": "memory_grid_modified.py",
        "candidate_result_files": ["memory_grid_results.json", "memory_results.json"],
        "match_game_names": ["Memory Grid", "Memory"]
    },
    "Shape–Color Switch": {
        "script": "shape_color_grid.py",  # update if different filename
        "candidate_result_files": ["shape_color_grid_results.json", "shape_color_results.json"],
        "match_game_names": ["Shape–Color Switch", "Shape Color", "Grid Shape"]
    }
}

# canonical domains (unified)
CANONICAL_SKILLS = [
    "Memory",
    "Attention & Focus",
    "Problem-Solving & Logical Thinking",
    "Spatial Awareness & Planning",
    "Processing Speed & Reaction Time",
    "Cognitive Flexibility",
    "Hand–Eye Coordination & Motor Skills",
]

# alias mapping for known variants -> canonical
SKILL_ALIAS = {
    "Visual Attention & Search": "Attention & Focus",
    "Working Memory (target hold)": "Memory",
    "Processing Speed": "Processing Speed & Reaction Time",
    "Processing Speed & Reaction Time": "Processing Speed & Reaction Time",
    "Spatial Reasoning": "Spatial Awareness & Planning",
    "Visual-Spatial Awareness": "Spatial Awareness & Planning",
    "Problem Solving": "Problem-Solving & Logical Thinking",
    "Problem-Solving": "Problem-Solving & Logical Thinking",
    "Attention": "Attention & Focus",
    "Attention & Focus": "Attention & Focus",
    "Memory": "Memory",
    "Cognitive Flexibility": "Cognitive Flexibility",
    "Hand–Eye Coordination & Motor Skills": "Hand–Eye Coordination & Motor Skills",
    # add more aliases if needed
}

# ---------------------------
# Helpers: run game + capture result
# ---------------------------
def run_game_and_collect(game_key: str, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Run the game's script, wait until it exits, then attempt to find its result.
    Returns standardized dict:
      {"game_name": str, "score_0_100": float, "skill_scores": {canon_skill: value}, "raw": raw_json}
    or None if nothing discoverable.
    """
    info = GAMES[game_key]
    script = info["script"]
    script_path = ROOT / script
    if not script_path.exists():
        st.error(f"Script not found: {script_path}")
        return None

    python = sys.executable
    st.info(f"Launching {script} ... the app will wait until the game window is closed.")
    # run and capture stdout/stderr to try fallback parsing
    try:
        proc = subprocess.run([python, str(script_path)], capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        st.error(f"Failed to run {script}: {e}")
        return None

    # 1) try known result files
    for fname in info.get("candidate_result_files", []):
        p = ROOT / fname
        if p.exists():
            # try parse
            try:
                raw = None
                # some files are line-based JSON (multiple objects per line)
                text = p.read_text()
                # attempt single json
                try:
                    raw = json.loads(text)
                except Exception:
                    # try last line JSON parse
                    last_obj = None
                    for line in text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            o = json.loads(line)
                            last_obj = o
                        except Exception:
                            continue
                    raw = last_obj
                if raw:
                    standardized = standardize_raw_game_result(raw, game_key)
                    if standardized:
                        return standardized
            except Exception:
                # continue fallback
                pass

    # 2) try to parse proc.stdout / proc.stderr for JSON fragments
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    # find JSON objects in the output using a simple regex search for { ... }
    json_objs = extract_json_objects_from_text(combined)
    if json_objs:
        # prefer ones whose game_name matches the game_key
        for obj in reversed(json_objs):
            if matches_game_name(obj, info.get("match_game_names", [])):
                standardized = standardize_raw_game_result(obj, game_key)
                if standardized:
                    return standardized
        # fallback: take last JSON object
        last = json_objs[-1]
        standardized = standardize_raw_game_result(last, game_key)
        if standardized:
            return standardized

    # 3) couldn't find result
    st.warning("No result file found and no JSON printed to console for this run. See console below.")
    with st.expander("Game console output (stdout/stderr)"):
        st.text(combined if combined.strip() else "<no stdout/stderr captured>")
    return None

def extract_json_objects_from_text(text: str) -> List[Dict[str, Any]]:
    """Attempt to extract JSON objects from text. Returns list of parsed objects."""
    objs = []
    # simple approach: find balanced braces and try parse
    brace_stack = []
    start_idx = None
    for i, ch in enumerate(text):
        if ch == "{":
            if start_idx is None:
                start_idx = i
            brace_stack.append("{")
        elif ch == "}":
            if brace_stack:
                brace_stack.pop()
                if not brace_stack and start_idx is not None:
                    candidate = text[start_idx:i+1]
                    try:
                        obj = json.loads(candidate)
                        objs.append(obj)
                    except Exception:
                        pass
                    start_idx = None
    return objs

def matches_game_name(obj: Dict[str, Any], match_names: List[str]) -> bool:
    g = obj.get("game_name") or obj.get("game") or ""
    for m in match_names:
        if m.lower() in g.lower():
            return True
    return False

# ---------------------------
# Standardize raw JSON -> canonical structure
# ---------------------------
def standardize_raw_game_result(raw: Dict[str, Any], game_key: str) -> Optional[Dict[str, Any]]:
    """
    Try to extract:
    - 0..100 game score (keys: game_score_0_100, avg_game_score_0_100, final_score_0_100, weighted_game_score_0_100)
    - skill_scores: mapping of skill names -> numeric values (per-game)
    Returns: {"game_name", "score_0_100", "skill_scores": {canonical:val}, "raw": raw}
    """
    if not isinstance(raw, dict):
        return None

    # Possible score keys
    score_keys = [
        "game_score_0_100", "avg_game_score_0_100", "avg_game_score", "final_score_0_100",
        "final_score", "weighted_game_score_0_100", "game_score", "avg_game_score_0_100",
        "avg_game_score_0_100"
    ]
    score = None
    for k in score_keys:
        if k in raw and isinstance(raw[k], (int, float)):
            score = float(raw[k]); break
    # fallback: some scripts put "game_score" 0..1
    if score is None:
        if "game_score" in raw and isinstance(raw["game_score"], (int, float)):
            val = float(raw["game_score"])
            # if between 0..1 assume fraction
            score = val * 100.0 if val <= 1.0 else val
    # other fallback keys
    if score is None:
        for k in ("avg_game_score_0_100", "game_score_0_100", "weighted_game_score_0_100"):
            if k in raw:
                try:
                    score = float(raw[k]); break
                except Exception:
                    pass
    # final fallback: look for any numeric named "*score*"
    if score is None:
        for k, v in raw.items():
            if "score" in k.lower() and isinstance(v, (int, float)):
                if 0 <= v <= 1:
                    score = float(v) * 100.0
                else:
                    score = float(v)
                break

    if score is None:
        # no numeric game score found; we can still try to build skill_scores and compute an aggregate later
        score = None

    # find skill_scores map under several possible keys
    skill_keys_candidates = ["skill_scores", "final_skill_scores", "average_skill_scores", "final_domains", "skill_contributions"]
    raw_skill_map = {}
    for k in skill_keys_candidates:
        if k in raw and isinstance(raw[k], dict):
            raw_skill_map = raw[k]
            break
    # also some games store per-domain under "final_domains" with different subkeys
    # normalize raw_skill_map to canonical
    canonical_skills = {s: 0.0 for s in CANONICAL_SKILLS}
    if raw_skill_map:
        for raw_k, raw_v in raw_skill_map.items():
            # map alias
            canon = SKILL_ALIAS.get(raw_k, None)
            if canon is None:
                # heuristic: find which canonical skill contains first word
                found = None
                for c in CANONICAL_SKILLS:
                    if raw_k.lower().split()[0] in c.lower():
                        found = c; break
                canon = found or raw_k
            if canon in canonical_skills:
                try:
                    canonical_skills[canon] = float(raw_v)
                except Exception:
                    canonical_skills[canon] = 0.0
            else:
                # ignore unknown keys
                pass
    else:
        # Some games embed domain numeric scores in other places (e.g., summary["final_domains"])
        # attempt to extract numbers from raw["final_domains"] if exists
        fd = raw.get("final_domains") or raw.get("final_domain") or {}
        if isinstance(fd, dict):
            for raw_k, raw_v in fd.items():
                canon = SKILL_ALIAS.get(raw_k, None) or raw_k
                if canon in canonical_skills:
                    try:
                        canonical_skills[canon] = float(raw_v)
                    except:
                        canonical_skills[canon] = 0.0

    # If still all zero but raw contains per-round skill lists, try per-round aggregation:
    if all(v == 0.0 for v in canonical_skills.values()):
        # try to search the raw for numbers in plausible keys (rounds, round_results, rounds)
        # for simplicity skip heavy heuristics here; accept that sometimes per-game mapping isn't present
        pass

    # If score missing, but we have skill scores we can compute an approximate score as average of skills
    if score is None:
        vals = [v for v in canonical_skills.values() if isinstance(v, (int, float))]
        if vals and any(v > 0 for v in vals):
            score = sum(vals) / len(vals)
        else:
            score = None

    return {
        "game_name": raw.get("game_name") or raw.get("game") or game_key,
        "score_0_100": round(score, 2) if score is not None else None,
        "skill_scores": {k: round(float(v), 2) for k, v in canonical_skills.items()},
        "raw": raw
    }

# ---------------------------
# Aggregation & visualization
# ---------------------------
def aggregate_played_games(play_results: Dict[str, Dict[str, Any]]):
    """
    Given per-play results (game_key -> standardized result),
    compute aggregated domain averages and unified CPS (average of available per-game scores).
    """
    played = [r for r in play_results.values() if r]
    domain_acc = {s: [] for s in CANONICAL_SKILLS}
    scores = []
    for r in played:
        if r["score_0_100"] is not None:
            scores.append(r["score_0_100"])
        for s in CANONICAL_SKILLS:
            domain_acc[s].append(r["skill_scores"].get(s, 0.0))
    avg_domains = {s: round(sum(v)/len(v), 2) if v else 0.0 for s, v in domain_acc.items()}
    unified_cps = round(sum(scores)/len(scores), 2) if scores else 0.0
    return avg_domains, unified_cps

def radar_chart(skill_scores: Dict[str, float], title: str = "Skill Radar"):
    labels = list(skill_scores.keys())
    values = [float(skill_scores[k]) for k in labels]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill='toself', name=title))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])), showlegend=False, title=title)
    return fig

# ---------------------------
# Streamlit pages
# ---------------------------
st.title("🧠 Cognitive Games Hub — Run & Analyze")
st.markdown("Launch each game from the app. After the candidate finishes a game, the app will automatically find the game's result (file or printed JSON), normalize domain names, and include it in the final unified CPS & visualizations.")

st.sidebar.header("Navigation")
pages = ["Home"] + list(GAMES.keys()) + ["Final Report"]
page = st.sidebar.radio("Go to", pages)

# store per-session last-run results in state
if "last_results" not in st.session_state:
    st.session_state.last_results = {g: None for g in GAMES.keys()}

if page == "Home":
    st.image("https://cdn-icons-png.flaticon.com/512/2353/2353480.png", width=140)
    st.markdown("""
    **How it works**
    1. Select a game page and click the Launch button. The game opens in a separate window.
    2. Play and close the game window when finished.
    3. The app will search for known result files for that game, or parse the game's stdout for JSON.
    4. The discovered result is normalized to the 7 canonical domains and included in the Final Report.

    **Games Rules**
    1. Stroop Test Game

        Objective: The candidate must identify the color of the word displayed on the screen, not the text itself.

        Rules:

        A word representing a color (e.g., "Red") will appear in a different color (e.g., the word "Red" might appear in blue).

        The candidate must select the color of the text correctly and as quickly as possible.

        Scoring can be based on speed and accuracy.
                
    2. Pattern Matching Game

        Objective: The candidate must identify the target symbol or character within a grid.

        Rules:

        A grid contains multiple symbols or characters. The target symbol may appear once, multiple times, or not at all.

        The candidate must select the target symbol quickly if it is present.

        If the target symbol is not present, the candidate must select the “Target Not Present” button.

        Scoring can be based on speed and accuracy.
                
    3. Tower of Hanoi Game

        Objective: The candidate must move all rings from the source tower to the target tower following the game’s rules.

        Rules:

        There are three towers and multiple rings of different sizes.

        The candidate must move one ring at a time from one tower to another.

        Rule: A larger ring cannot be placed on top of a smaller ring.

        The goal is to rearrange the rings so that the largest is at the bottom and the smallest is at the top on the target tower.

        Scoring can be based on the number of moves and correctness.
                
    4. Slide Puzzle Game

        Objective: The candidate must rearrange the tiles to complete the puzzle.

        Rules:

        The puzzle consists of sliding tiles within a grid, with one empty space to allow movement.

        The candidate must select and slide the correct tile to move it into the empty space.

        Optimal moves are important; the puzzle should be solved using the fewest possible moves.

        Scoring can be based on accuracy, speed, and efficiency of moves.
    5. Memory Grid Game

        Objective: The candidate must remember and select the boxes that light up in the correct order.

        Rules:

        A grid of boxes is displayed. Certain boxes light up briefly in a sequence.

        The candidate must select the boxes that lit up, remembering their positions.

        Timing is important; selections should be made quickly and accurately.

        Scoring can be based on accuracy and speed in recalling the sequence.
                
    6. Shape Color Switch Game

        Objective: The candidate must identify and select the correct shape in the grid based on the current rule.

        Rules:

        A grid contains multiple shapes of different colors.

        Each round has a specific rule indicating which shape (and possibly color) to select.

        The candidate must quickly choose the correct shape according to the rule.

        Scoring can be based on speed and accuracy.

        """)
    st.write("Available games:")
    for g in GAMES:
        st.write(f"- {g} (script: `{GAMES[g]['script']}`)")

elif page in GAMES:
    st.header(page)
    info = GAMES[page]
    st.write(f"Script: `{info['script']}`")
    if st.button(f"▶ Launch {page}"):
        res = run_game_and_collect(page)
        # cache into session
        st.session_state.last_results[page] = res
        if res:
            st.success(f"Result captured: score = {res['score_0_100']} / 100")
        else:
            st.warning("No result could be captured for this run.")
    # show last captured result for this game in session state (if any)
    last = st.session_state.last_results.get(page)
    if last:
        st.subheader("Last captured result (normalized)")
        st.metric("Score (0–100)", last["score_0_100"] or "N/A")
        st.dataframe(pd.DataFrame(list(last["skill_scores"].items()), columns=["Domain", "Score"]).set_index("Domain"))
        st.plotly_chart(radar_chart(last["skill_scores"], title=f"{page} — Skill Radar"), use_container_width=True)
        with st.expander("Show raw JSON from game"):
            st.json(last["raw"])
    else:
        st.info("No recent result for this game in this session. Launch and play to capture result.")

elif page == "Final Report":
    st.header("Final Aggregated Report (Unified CPS & Domains)")
    per_game_results = {g: st.session_state.last_results.get(g) for g in GAMES}
    avg_domains, unified_cps = aggregate_played_games({g: r for g, r in per_game_results.items() if r})
    if unified_cps == 0.0:
        st.warning("No captured results yet. Play at least one game to populate the report.")
    else:
        st.metric("Unified CPS (average of played game scores)", f"{unified_cps} / 100")
        st.subheader("Aggregated Domain Radar")
        st.plotly_chart(radar_chart(avg_domains, "Aggregated Skill Radar"), use_container_width=True)
        st.subheader("Aggregated Domain Scores (bar)")
        df = pd.DataFrame(list(avg_domains.items()), columns=["Domain", "Score"])
        st.altair_chart(alt.Chart(df).mark_bar().encode(x="Domain", y="Score", tooltip=["Domain", "Score"]).properties(height=300), use_container_width=True)

        st.subheader("Per-game contribution (stacked by domain)")
        # build dataframe for stacked chart
        rows = []
        for g, r in per_game_results.items():
            if r:
                for s, v in r["skill_scores"].items():
                    rows.append({"game": g, "domain": s, "score": v})
        if rows:
            df_stack = pd.DataFrame(rows)
            chart = alt.Chart(df_stack).mark_bar().encode(
                x=alt.X("domain:N", title="Domain"),
                y=alt.Y("score:Q", title="Score"),
                color=alt.Color("game:N", title="Game"),
                tooltip=["game", "domain", "score"]
            ).properties(height=420)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No per-game domain breakdown available yet.")

        st.markdown("### Per-game summary")
        for g, r in per_game_results.items():
            if r:
                st.write(f"**{g}** — Score: {r['score_0_100']} / 100")
                with st.expander(f"{g} — raw result"):
                    st.json(r["raw"])

        # recommendation
        top_domain = max(avg_domains, key=avg_domains.get)
        role_map = {
            "Memory": "Data Analyst",
            "Attention & Focus": "Quality Engineer",
            "Problem-Solving & Logical Thinking": "Software Developer",
            "Spatial Awareness & Planning": "UI/UX Designer",
            "Processing Speed & Reaction Time": "Tech Support Engineer",
            "Cognitive Flexibility": "Product Manager",
            "Hand–Eye Coordination & Motor Skills": "Game Tester",
        }
        st.success(f"💡 Strongest domain: **{top_domain}** → Suggested role: **{role_map.get(top_domain,'General IT Role')}**")

st.markdown("---")
st.caption("The dashboard tries multiple fallback ways to discover game results: known output files, JSON printed to stdout, or line-based JSON logs. If a game does not produce JSON, please update the script to either print a JSON object or write a result file.")
