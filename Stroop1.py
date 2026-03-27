# Stroop_test.py 
import tkinter as tk
import random, time, json, statistics
from tkinter import messagebox

# -------------------------------
# Cognitive Skill Weights (Balanced)
# -------------------------------
target_skills = {
    "Memory": 0.05,
    "Attention & Focus": 0.30,
    "Problem-Solving & Logical Thinking": 0.00,
    "Spatial Awareness & Planning": 0.00,
    "Processing Speed & Reaction Time": 0.45,
    "Cognitive Flexibility": 0.20,
    "Hand–Eye Coordination & Motor Skills": 0.00
}

colours = ['Red', 'Blue', 'Green', 'Pink', 'Black',
           'Yellow', 'Orange', 'White', 'Purple', 'Brown']

round_number = 1
score = 0
timeleft = 30
attempts = 0
correct_attempts = 0
reaction_times = []
start_time = 0
current_color = ""
game_start_time = 0
rapid_timer = None


def startGame(event=None):
    global round_number, timeleft, score, attempts, correct_attempts, reaction_times, game_start_time
    round_number = 1
    score = 0
    attempts = 0
    correct_attempts = 0
    reaction_times = []
    game_start_time = time.time()
    startRound()


def startRound():
    global timeleft
    if round_number == 1:
        messagebox.showinfo("Round 1", "Round 1: Normal mode\nFocus and identify the color of the word!")
    elif round_number == 2:
        messagebox.showinfo("Round 2", "Round 2: Slightly faster, stay focused!")
    elif round_number == 3:
        messagebox.showinfo("Round 3", "Round 3: Rapid Response Mode!\nEach question lasts only 2 seconds!")

    timeleft = 30
    countdown()
    nextColour()


def nextColour():
    global start_time, current_color, rapid_timer

    if timeleft > 0:
        if rapid_timer:
            root.after_cancel(rapid_timer)

        word_text = random.choice(colours)

        # 30% same, 70% different
        if random.random() < 0.3:
            font_color = word_text
        else:
            font_color = random.choice([c for c in colours if c != word_text])

        label.config(fg=font_color, text=word_text)
        current_color = font_color
        scoreLabel.config(text=f"Score: {score}")

        # Generate dot options safely
        n = len(dot_canvases)
        distractors = [c for c in colours if c != font_color]

        if not distractors:
            distractors = colours[:]  # fallback

        chosen = random.sample(distractors, n - 1) if len(distractors) >= (n - 1) else distractors[:]
        while len(chosen) < (n - 1):
            chosen.append(random.choice(distractors))

        options = chosen + [font_color]
        random.shuffle(options)
        updateDots(options)

        start_time = time.time()

        if round_number == 3:
            rapid_timer = root.after(2000, timeout_question)


def timeout_question():
    global attempts
    if timeleft > 0:
        attempts += 1
        nextColour()


def checkColor(selected_color):
    global score, attempts, correct_attempts, reaction_times, start_time

    if timeleft > 0:
        if round_number == 3 and rapid_timer:
            root.after_cancel(rapid_timer)

        attempts += 1

        reaction_time = time.time() - start_time if start_time else 0
        reaction_times.append(reaction_time)

        if selected_color.lower() == label.cget('fg').lower():
            score += 1
            correct_attempts += 1

        nextColour()


def countdown():
    global timeleft, round_number
    if timeleft > 0:
        timeleft -= 1
        timeLabel.config(text=f"Time left: {timeleft}")
        timeLabel.after(1000, countdown)
    else:
        for canvas in dot_canvases:
            canvas.unbind("<Button-1>")

        if round_number < 3:
            nextRound()
        else:
            show_results()


def nextRound():
    global round_number
    round_number += 1

    if round_number == 2:
        for c in dot_canvases:
            c.destroy()
        dot_canvases.clear()
        for _ in range(6):
            c = tk.Canvas(dotFrame, width=50, height=50, bg="white", highlightthickness=0)
            c.pack(side="left", padx=8)
            dot_canvases.append(c)

    startRound()


def updateDots(options):
    for canvas, color in zip(dot_canvases, options):
        canvas.delete("all")
        try:
            canvas.create_oval(10, 10, 40, 40, fill=color, outline="")
        except tk.TclError:
            canvas.create_oval(10, 10, 40, 40, fill=color.lower(), outline="")
        canvas.bind("<Button-1>", lambda e, c=color: checkColor(c))



def show_results():
    global game_start_time

    total_time = round(time.time() - game_start_time, 2)

    accuracy = correct_attempts / attempts if attempts > 0 else 0.0
    avg_reaction = sum(reaction_times) / len(reaction_times) if reaction_times else 0.0

    # --- Consistency ---
    if len(reaction_times) > 1 and avg_reaction > 0:
        consistency = max(0.0, 1 - (statistics.stdev(reaction_times) / avg_reaction))
    else:
        consistency = 1.0

    # Adaptability = accuracy
    adaptability = accuracy

    # Speed ratio (ideal reaction = 0.6s)
    if avg_reaction > 0:
        speed_ratio = min(1.0, 0.6 / avg_reaction)
    else:
        speed_ratio = 0.0

    # Game score 0–100
    game_score = round(
        ((0.4 * accuracy) +
         (0.2 * consistency) +
         (0.2 * adaptability) +
         (0.2 * speed_ratio)) * 100,
        2
    )

    # Skill contribution (no CPS here)
    skill_scores = {s: round(game_score * w, 2) for s, w in target_skills.items()}

    results = {
        "game_name": "Color Game (Stroop Test)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rounds_completed": round_number,
        "total_attempts": attempts,
        "correct_attempts": correct_attempts,
        "accuracy_%": round(accuracy * 100, 2),
        "avg_reaction_time_s": round(avg_reaction, 3),
        "consistency": round(consistency, 3),
        "adaptability": round(adaptability, 3),
        "speed_ratio": round(speed_ratio, 3),
        "completion_time_s": total_time,
        "game_score_0_100": game_score,
        "skill_scores": skill_scores
    }

    with open("game_results.json", "a") as f:
        json.dump(results, f)
        f.write("\n")

    print("\nColor Game results:")
    print(json.dumps(results, indent=4))

    messagebox.showinfo("Game Over", "Stroop Test completed! Scores saved.")
    root.destroy()




if __name__ == "__main__":
    root = tk.Tk()
    root.title("Color Game - Stroop Cognitive Test")
    root.geometry("420x480")
    root.config(bg="white")

    instructions = tk.Label(root, text="Click the dot matching the COLOR of the word!", font=('Helvetica', 12), bg="white")
    instructions.pack(pady=5)

    scoreLabel = tk.Label(root, text="Press Enter or Click Start", font=('Helvetica', 12), bg="white")
    scoreLabel.pack()
    timeLabel = tk.Label(root, text=f"Time left: {timeleft}", font=('Helvetica', 12), bg="white")
    timeLabel.pack()

    label = tk.Label(root, font=('Helvetica', 60), bg="white")
    label.pack(pady=10)

    dotFrame = tk.Frame(root, bg="white")
    dotFrame.pack(pady=10)

    dot_canvases = [tk.Canvas(dotFrame, width=50, height=50, bg="white", highlightthickness=0) for _ in range(5)]
    for c in dot_canvases:
        c.pack(side="left", padx=10)

    tk.Button(root, text="Start", command=startGame, font=('Helvetica', 12)).pack(pady=10)
    root.bind('<Return>', startGame)
    root.mainloop()
