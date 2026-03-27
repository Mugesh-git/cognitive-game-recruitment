#!/usr/bin/env python3
"""
Pattern Matching / Symbol Search — 3 Rounds (4x4, 8x8, 12x12)
- Each round has multiple trials (configurable)
- Target preview -> grid -> measure RT -> record result
- Give Up: skips the rest of the current round (round score = 0)
- Not Present button allowed per trial
- Per-round scoring: Accuracy (40) + Speed (40) + Consistency (10) + Adaptability (10)
- Rounds weighted: [0.25, 0.35, 0.40]
- Results written to JSON at end
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random, time, json, statistics, math, os

# ----------------- CONFIG -----------------
ROUNDS_CONFIG = [
    {"grid": 4, "trials": 6, "presence_prob": 0.95, "preview": 0.8},   # Round 1: warm-up
    {"grid": 8, "trials": 6, "presence_prob": 0.8,  "preview": 0.6},   # Round 2: medium
    {"grid": 12,"trials": 6, "presence_prob": 0.6,  "preview": 0.5},   # Round 3: hard
]
ROUND_WEIGHTS = [0.25, 0.35, 0.40]

SYMBOL_POOL = ['@', '#', '$', '%', '&', '*', 'A', 'B', 'C', 'Δ', '◼', '◆', '■', '♠', '♣', '♦', '♥', '★', '☆']
MIN_PLAUSIBLE_RT = 0.05
BASE_MAX_TIME_4x4 = 12.0   # baseline human-friendly max time for 4x4 (seconds)
# ------------------------------------------

def compute_max_time_for_grid(grid):
    # scale max time roughly by grid area ratio
    scale = (grid*grid) / (4*4)
    return BASE_MAX_TIME_4x4 * scale

def clamp01(x): return max(0.0, min(1.0, x))

class PatternSearchRounds(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pattern Matching — 3-Round Grid Test")
        self.geometry("1000x700")
        self.configure(padx=10, pady=8)

        # runtime state
        self.round_index = -1
        self.trial_index = -1
        self.grid_buttons = []
        self.grid_data = []
        self.target = None
        self.present = False
        self.rt_start = None
        self.round_results = []   # per-round list of trial dicts
        self.all_rounds_results = []  # final
        self.gave_up_round = False

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Pattern Matching — 3 Rounds", font=("Helvetica", 18, "bold")).pack(side=tk.LEFT)
        self.start_btn = ttk.Button(top, text="Start Test", command=self.start_test)
        self.start_btn.pack(side=tk.RIGHT)

        center = ttk.Frame(self)
        center.pack(fill=tk.BOTH, expand=True, pady=8)

        # left: game area
        game_frame = ttk.LabelFrame(center, text="Game")
        game_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))

        self.header_label = ttk.Label(game_frame, text="Press Start to begin", font=("Helvetica", 14))
        self.header_label.pack(pady=6)

        self.target_label = ttk.Label(game_frame, text="TARGET: ", font=("Helvetica", 28))
        self.target_label.pack(pady=8)

        self.grid_frame = ttk.Frame(game_frame)
        self.grid_frame.pack(expand=True, pady=(0,8))

        controls = ttk.Frame(game_frame)
        controls.pack(fill=tk.X, pady=(0,8))

        self.not_present_btn = ttk.Button(controls, text="Target NOT present", command=self.declare_not_present, state=tk.DISABLED)
        self.not_present_btn.pack(side=tk.LEFT, padx=6)

        self.giveup_btn = ttk.Button(controls, text="Give Up Round", command=self.give_up_round, state=tk.DISABLED)
        self.giveup_btn.pack(side=tk.LEFT, padx=6)

        # right: summary
        summary_frame = ttk.LabelFrame(center, text="Session & Results")
        summary_frame.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(summary_frame, text="Progress").pack(pady=(8,2))
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(summary_frame, orient=tk.HORIZONTAL, length=220, mode='determinate', variable=self.progress_var)
        self.progress.pack(padx=8, pady=(0,8))

        ttk.Label(summary_frame, text="Feedback").pack()
        self.feedback = tk.Text(summary_frame, width=36, height=12, state=tk.DISABLED, wrap=tk.WORD)
        self.feedback.pack(padx=8, pady=(4,8))

        ttk.Label(summary_frame, text="Final Summary").pack()
        self.final_summary = tk.Text(summary_frame, width=36, height=18, state=tk.DISABLED, wrap=tk.WORD)
        self.final_summary.pack(padx=8, pady=(4,8))

        footer = ttk.Label(self, text="Tip: Memorize the target briefly, then search the grid. Use 'Not present' when appropriate.")
        footer.pack(side=tk.BOTTOM, pady=(6,0))

    # ------------ Test flow --------------
    def start_test(self):
        self.round_index = -1
        self.all_rounds_results.clear()
        self.start_btn.config(text="Quit Test", command=self.quit_test)
        self.next_round()

    def quit_test(self):
        if messagebox.askyesno("Quit Test", "End test early? Results so far will be summarized."):
            self.end_test()

    def next_round(self):
        self.round_index += 1
        total_rounds = len(ROUNDS_CONFIG)
        if self.round_index >= total_rounds:
            self.end_test()
            return
        cfg = ROUNDS_CONFIG[self.round_index]
        self.round_results = []
        self.gave_up_round = False
        self.trial_index = -1
        self.update_progress()
        self.set_feedback(f"Round {self.round_index+1} — Grid {cfg['grid']}×{cfg['grid']}: {cfg['trials']} trials. Get ready...")
        # short pause banner then start trials
        self.after(800, self.next_trial)

    def next_trial(self):
        if self.gave_up_round:
            # record round as skipped
            round_summary = self._compute_round_summary(skipped=True)
            self.all_rounds_results.append(round_summary)
            self.next_round()
            return

        cfg = ROUNDS_CONFIG[self.round_index]
        self.trial_index += 1
        if self.trial_index >= cfg["trials"]:
            # finish round: compute summary and store
            round_summary = self._compute_round_summary(skipped=False)
            self.all_rounds_results.append(round_summary)
            self.next_round()
            return

        # prepare trial
        self._prepare_trial(cfg)

    def _prepare_trial(self, cfg):
        # pick target and presence
        self.target = random.choice(SYMBOL_POOL)
        self.present = random.random() < cfg["presence_prob"]
        # generate grid
        self.grid_data = self._generate_grid(self.target, cfg["grid"], self.present)
        # UI update: show target preview
        self.target_label.config(text=f"TARGET:    {self.target}")
        self.clear_grid_ui()
        self.not_present_btn.config(state=tk.DISABLED)
        self.giveup_btn.config(state=tk.NORMAL)
        self.set_feedback(f"Preview target: {self.target} (preview {cfg['preview']}s)")
        # show target, then grid
        self.after(int(cfg["preview"]*1000), lambda: self._show_grid(cfg))

    def _generate_grid(self, target, grid, present):
        rows = grid
        cols = grid
        pool = [s for s in SYMBOL_POOL if s != target]
        grid_mat = [[random.choice(pool) for _ in range(cols)] for _ in range(rows)]
        if present:
            # place 1..min(4,rows) targets randomly
            count = random.randint(1, max(1, min(4, rows//2)))
            placed = 0
            while placed < count:
                r = random.randrange(rows)
                c = random.randrange(cols)
                if grid_mat[r][c] != target:
                    grid_mat[r][c] = target
                    placed += 1
        return grid_mat

    def _show_grid(self, cfg):
        # render grid into buttons
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.grid_buttons = []
        rows = cfg["grid"]
        cols = cfg["grid"]
        for r in range(rows):
            row_buttons = []
            for c in range(cols):
                text = self.grid_data[r][c]
                b = ttk.Button(self.grid_frame, text=text, width=3,
                               command=lambda rr=r, cc=c: self.handle_click(rr, cc))
                b.grid(row=r, column=c, padx=2, pady=2)
                row_buttons.append(b)
            self.grid_buttons.append(row_buttons)
        self.not_present_btn.config(state=tk.NORMAL)
        self.rt_start = time.perf_counter()
        self.set_feedback(f"Grid shown — find '{self.target}' (trial {self.trial_index+1}/{cfg['trials']})")

    def clear_grid_ui(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.grid_buttons = []

    def handle_click(self, r, c):
        rt = time.perf_counter() - (self.rt_start or time.perf_counter())
        clicked = self.grid_data[r][c]
        correct = (clicked == self.target)
        self._record_trial(correct=correct, rt=rt, present=self.present, clicked_pos=(r+1, c+1))
        # disable grid
        for row in self.grid_buttons:
            for b in row:
                b.config(state=tk.DISABLED)
        self.not_present_btn.config(state=tk.DISABLED)
        # immediate feedback
        if correct:
            self.set_feedback(f"Correct! Clicked {clicked} at ({r+1},{c+1}) — RT {rt:.3f}s")
        else:
            if self.present:
                locs = [(i+1,j+1) for i,row in enumerate(self.grid_data) for j,val in enumerate(row) if val==self.target]
                self.set_feedback(f"Incorrect. Clicked {clicked}. Targets at {locs}. RT {rt:.3f}s")
            else:
                self.set_feedback(f"Incorrect. Target wasn't present. RT {rt:.3f}s")
        # next trial after short pause
        self.after(700, self.next_trial)

    def declare_not_present(self):
        rt = time.perf_counter() - (self.rt_start or time.perf_counter())
        correct = (not self.present)
        self._record_trial(correct=correct, rt=rt, present=self.present, clicked_pos=None, declared_not_present=True)
        # disable grid
        for row in self.grid_buttons:
            for b in row:
                b.config(state=tk.DISABLED)
        self.not_present_btn.config(state=tk.DISABLED)
        if correct:
            self.set_feedback(f"Correct — target not present. RT {rt:.3f}s")
        else:
            locs = [(i+1,j+1) for i,row in enumerate(self.grid_data) for j,val in enumerate(row) if val==self.target]
            self.set_feedback(f"Incorrect — target present at {locs}. RT {rt:.3f}s")
        self.after(700, self.next_trial)

    def give_up_round(self):
        # mark flag and skip rest of current round
        if messagebox.askyesno("Give Up Round", "Skip the rest of this round? Round score will be 0."):
            self.gave_up_round = True
            # disable buttons
            self.not_present_btn.config(state=tk.DISABLED)
            self.giveup_btn.config(state=tk.DISABLED)
            self.clear_grid_ui()
            self.set_feedback("Round skipped by user.")
            # proceed to next_round on next_trial call
            self.after(400, self.next_trial)

    def _record_trial(self, correct, rt, present, clicked_pos, declared_not_present=False):
        record = {
            "round": self.round_index+1,
            "trial": self.trial_index+1,
            "target": self.target,
            "present": present,
            "declared_not_present": bool(declared_not_present),
            "correct": bool(correct),
            "rt": float(rt),
            "clicked_pos": clicked_pos
        }
        self.round_results.append(record)
        # update feedback log
        self.append_feedback(f"R{record['round']}T{record['trial']}: {'Correct' if correct else 'Incorrect'} | RT={rt:.3f}s\n")
        self.update_progress()

    def update_progress(self):
        # compute overall progress: rounds completed fraction
        completed = len(self.all_rounds_results)
        # plus current progress in current round
        cfg = None
        if 0 <= self.round_index < len(ROUNDS_CONFIG):
            cfg = ROUNDS_CONFIG[self.round_index]
        progress = (completed / len(ROUNDS_CONFIG)) * 100.0
        if cfg:
            # add fraction of trials done this round
            trials_done = max(0, self.trial_index+1)
            total_trials = cfg["trials"]
            progress += (trials_done / total_trials) * (100.0/len(ROUNDS_CONFIG))
        self.progress_var.set(min(100.0, progress))

    def append_feedback(self, txt):
        self.feedback.configure(state=tk.NORMAL)
        self.feedback.insert(tk.END, txt)
        self.feedback.see(tk.END)
        self.feedback.configure(state=tk.DISABLED)

    def set_feedback(self, txt):
        self.feedback.configure(state=tk.NORMAL)
        self.feedback.delete("1.0", tk.END)
        self.feedback.insert(tk.END, txt)
        self.feedback.configure(state=tk.DISABLED)

    # ------------ Scoring --------------
    def _compute_round_summary(self, skipped=False):
        """
        Compute scoring for the finished round.
        Returns a dict with trial records, per-round metrics and round_score_0_100.
        """
        cfg = ROUNDS_CONFIG[self.round_index]
        grid = cfg["grid"]
        max_time = compute_max_time_for_grid(grid)

        if skipped:
            # standardized skipped round result
            round_summary = {
                "round": self.round_index+1,
                "grid": grid,
                "skipped": True,
                "trials": [],
                "metrics": {
                    "accuracy_ratio": 0.0,
                    "avg_rt": None,
                    "speed_ratio": 0.0,
                    "consistency": 0.0,
                    "adaptability": 0.0,
                    "round_score_0_100": 0.0
                }
            }
            return round_summary

        trials = self.round_results
        total_trials = len(trials)
        if total_trials == 0:
            # no data -> zeroed metrics
            return self._compute_round_summary(skipped=True)

        # accuracy: correct_count / total_trials (counts correct Not-present as correct)
        correct_count = sum(1 for t in trials if t["correct"])
        accuracy_ratio = correct_count / total_trials

        # RT list for correct trials only (speed measured on correct responses)
        correct_rts = [t["rt"] for t in trials if t["correct"] and t["rt"] >= 0]
        avg_rt = statistics.mean(correct_rts) if correct_rts else None

        # speed_ratio: based on avg_rt normalized to max_time (higher is better)
        if avg_rt is None:
            speed_ratio = 0.0
        else:
            t = max(avg_rt, MIN_PLAUSIBLE_RT)
            if t >= max_time:
                speed_ratio = 0.0
            else:
                speed_ratio = clamp01((max_time - t) / (max_time - MIN_PLAUSIBLE_RT))

        # we multiply speed by accuracy so blind fast wrong answers don't get rewarded
        speed_component = speed_ratio * accuracy_ratio

        # consistency: reaction time stability (across correct trials). if only 1 correct trial -> consistent.
        if len(correct_rts) > 1 and avg_rt and avg_rt > 0:
            consistency_metric = clamp01(1.0 - (statistics.pstdev(correct_rts) / avg_rt))
        elif len(correct_rts) == 1:
            consistency_metric = 1.0
        else:
            consistency_metric = 0.0

        # adaptability: fraction of present-target trials that were correctly identified (ability to handle targets)
        present_trials = [t for t in trials if t["present"]]
        if present_trials:
            present_correct = sum(1 for t in present_trials if t["correct"])
            adaptability_metric = present_correct / len(present_trials)
        else:
            # if no present trials, fallback to overall accuracy
            adaptability_metric = accuracy_ratio

        # component scores
        accuracy_score = 40.0 * accuracy_ratio
        speed_score = 40.0 * speed_component
        consistency_score = 10.0 * consistency_metric
        adaptability_score = 10.0 * adaptability_metric

        round_score = accuracy_score + speed_score + consistency_score + adaptability_score
        round_score = max(0.0, min(100.0, round_score))

        metrics = {
            "accuracy_ratio": round(accuracy_ratio, 4),
            "avg_rt": round(avg_rt, 4) if avg_rt is not None else None,
            "speed_ratio": round(speed_ratio, 4),
            "speed_component": round(speed_component, 4),
            "consistency": round(consistency_metric, 4),
            "adaptability": round(adaptability_metric, 4),
            "accuracy_score_0_40": round(accuracy_score, 3),
            "speed_score_0_40": round(speed_score, 3),
            "consistency_score_0_10": round(consistency_score, 3),
            "adaptability_score_0_10": round(adaptability_score, 3),
            "round_score_0_100": round(round_score, 3),
            "max_time_for_grid_s": round(max_time, 2)
        }

        round_summary = {
            "round": self.round_index+1,
            "grid": grid,
            "skipped": False,
            "trials": trials.copy(),
            "metrics": metrics
        }
        # reset round_results for next round (kept earlier but we'll return a copy)
        self.round_results = []
        return round_summary

    def end_test(self):
        # compute final game-level aggregation
        weighted_total = 0.0
        aggregated_rounds = self.all_rounds_results.copy()
        
        for i, r in enumerate(aggregated_rounds):
            weight = ROUND_WEIGHTS[i] if i < len(ROUND_WEIGHTS) else (1.0/len(aggregated_rounds))
            round_score = r["metrics"]["round_score_0_100"] if not r.get("skipped", False) else 0.0
            weighted_total += (round_score / 100.0) * weight

        final_score = round(weighted_total * 100.0, 2)

        # skill-level contributions
        skill_weights = {
            "Processing Speed & Reaction Time": 0.50,
            "Visual Attention & Search": 0.35,
            "Working Memory (target hold)": 0.15
        }
        avg_round_score = sum(r["metrics"]["round_score_0_100"] for r in aggregated_rounds if not r.get("skipped", False)) / len(aggregated_rounds)
        skill_scores = {k: round(avg_round_score * w, 2) for k,w in skill_weights.items()}

        final_report = {
            "game": "Pattern Matching — 3 Round Grid Search",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "rounds": aggregated_rounds,
            "final_score_0_100": final_score,
            "skill_scores": skill_scores
        }

        # JSON output
        outpath = os.path.join(os.getcwd(), "pattern_search_results.json")
        try:
            with open(outpath, "w") as f:
                json.dump(final_report, f, indent=2)
        except Exception as e:
            print("Failed to save results:", e)

        # ---------------- Terminal Output ----------------
        print("\n===== Pattern Matching Test Results =====")
        print(f"Final Score: {final_score} / 100\n")
        for k,v in skill_scores.items():
            print(f"{k}: {v}")
        print("\n--- Per-Round Metrics ---")
        for r in aggregated_rounds:
            print(f"\nRound {r['round']} (Grid {r['grid']}×{r['grid']}) {'[SKIPPED]' if r.get('skipped', False) else ''}")
            m = r.get("metrics", {})
            if m:
                print(f" Accuracy: {m.get('accuracy_ratio',0)*100:.1f}%")
                if m.get('avg_rt') is not None:
                    print(f" Avg RT (correct trials): {m.get('avg_rt'):.3f}s")
                print(f" Speed Score: {m.get('speed_score_0_40',0):.1f}/40")
                print(f" Consistency Score: {m.get('consistency_score_0_10',0):.1f}/10")
                print(f" Adaptability Score: {m.get('adaptability_score_0_10',0):.1f}/10")
                print(f" Round Score: {m.get('round_score_0_100',0):.1f}/100")
        print(f"\nFull results JSON saved to: {outpath}")
        print("=========================================\n")
        # -------------------------------------------------

        # UI final summary
        self.final_summary.configure(state=tk.NORMAL)
        self.final_summary.delete("1.0", tk.END)
        self.final_summary.insert(tk.END, f"Final Score: {final_score} / 100\n\n")
        for k,v in skill_scores.items():
            self.final_summary.insert(tk.END, f"{k}: {v}\n")
        self.final_summary.insert(tk.END, f"\nFull results saved to: {outpath}\n")
        self.final_summary.configure(state=tk.DISABLED)

        # stop test mode
        self.set_feedback("Test completed. See final summary at right or terminal.")
        self.start_btn.config(text="Start Test", command=self.start_test)
        self.progress_var.set(100.0)


    # ----------------- end -----------------

if __name__ == "__main__":
    app = PatternSearchRounds()
    app.mainloop()
