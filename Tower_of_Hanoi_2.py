# tower_of_hanoi_modified.py (consistency + adaptability integrated, Option A)
import pygame
import sys
import time
import json
import statistics

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tower of Hanoi - Cognitive Skills Test")

# Colors and fonts
BG_TOP = (30, 30, 60)
BG_BOTTOM = (10, 10, 30)
POLE_COLOR = (220, 220, 220)
DISK_COLORS = [(255, 99, 71), (255, 165, 0), (50, 205, 50), (100, 149, 237), (186, 85, 211)]
TEXT_COLOR = (255, 255, 255)
font_large = pygame.font.SysFont("arial", 36)
font_small = pygame.font.SysFont("arial", 24)

POLE_Y = HEIGHT - 150
POLE_WIDTH = 10
POLE_HEIGHT = 220
POLE_X = [200, 400, 600]

# ---- Final Cognitive Skill Weights (Tower of Hanoi) ----
target_skills = {
    "Problem-Solving & Logical Thinking": 0.30,
    "Spatial Awareness & Planning": 0.30,
    "Attention & Focus": 0.20,
    "Processing Speed & Reaction Time": 0.10,
    "Memory": 0.05,
    "Cognitive Flexibility": 0.05,
    "Hand–Eye Coordination & Motor Skills": 0.00
}

# Round weights (importance of each round towards game)
ROUND_WEIGHTS = [0.25, 0.35, 0.40]

# Max allowed times per round (seconds) for speed normalization (human-friendly)
MAX_TIME_PER_ROUND = {
    1: 60,   # round 1 (3 disks)
    2: 120,  # round 2 (4 disks)
    3: 180   # round 3 (5 disks)
}
# Minimum plausible human completion time (seconds) used to bound speed normalization
MIN_PLAUSIBLE_TIME = 3.0

def draw_background():
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio
        g = BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio
        b = BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio
        pygame.draw.line(screen, (int(r), int(g), int(b)), (0, y), (WIDTH, y))

def draw_poles():
    for x in POLE_X:
        pygame.draw.rect(screen, POLE_COLOR, (x - POLE_WIDTH//2, POLE_Y - POLE_HEIGHT, POLE_WIDTH, POLE_HEIGHT))
    pygame.draw.rect(screen, (230, 230, 230), (100, POLE_Y, 600, 10))

def draw_text(text, font, color, center):
    text_surface = font.render(text, True, color)
    rect = text_surface.get_rect(center=center)
    screen.blit(text_surface, rect)

def draw_disks(poles):
    for i, pole in enumerate(poles):
        for j, disk in enumerate(pole):
            disk_width = 40 + disk * 30
            disk_height = 20
            x = POLE_X[i] - disk_width // 2
            y = POLE_Y - (j + 1) * disk_height
            color = DISK_COLORS[disk % len(DISK_COLORS)]
            pygame.draw.rect(screen, color, (x, y, disk_width, disk_height), border_radius=8)
            pygame.draw.rect(screen, (0, 0, 0), (x, y, disk_width, disk_height), 2, border_radius=8)

def count_correct_on_target(poles, num_disks):
    """Count how many disks are correctly stacked on target pole (pole index 2),
       in correct order from largest (bottom) to smallest (top)."""
    target = poles[2]
    correct = 0
    expected_stack = list(range(num_disks - 1, -1, -1))
    # compare from bottom up (our representation's bottom is index 0)
    for i in range(min(len(target), len(expected_stack))):
        if target[i] == expected_stack[i]:
            correct += 1
        else:
            break
    return correct

def compute_speed_score(completion_time, round_num, accuracy_ratio):
    """
    Compute speed score on a 0..40 scale using a human-friendly normalization:
    - Uses min plausible time and max allowed time per round to compute a ratio in [0,1]
    - Multiplies by accuracy_ratio so speed contributes only when accuracy exists
    """
    max_time = MAX_TIME_PER_ROUND.get(round_num, 180)
    min_time = MIN_PLAUSIBLE_TIME
    t = max(completion_time, 0.0)
    if t >= max_time:
        speed_ratio = 0.0
    else:
        denom = (max_time - min_time)
        if denom <= 0:
            speed_ratio = 0.0
        else:
            speed_ratio = (max_time - t) / denom
            speed_ratio = max(0.0, min(1.0, speed_ratio))
    return 40.0 * speed_ratio * accuracy_ratio, round(speed_ratio, 4)

def tower_of_hanoi(num_disks, round_num):
    # initialize poles; disks coded num_disks-1..0 (largest to smallest)
    poles = [list(range(num_disks - 1, -1, -1)), [], []]
    selected_disk = None
    selected_pole = None
    move_count = 0
    invalid_moves = 0
    gave_up = False
    move_timestamps = []

    optimal_moves = (2 ** num_disks) - 1
    start_time = time.time()
    clock = pygame.time.Clock()

    while True:
        draw_background()
        draw_poles()
        draw_disks(poles)
        elapsed = time.time() - start_time
        draw_text(f"Round {round_num} | Moves: {move_count}", font_small, TEXT_COLOR, (140, 40))
        draw_text(f"Time: {int(elapsed)}s", font_small, TEXT_COLOR, (700, 40))
        # show only Give Up instruction
        draw_text("Press [G] to Give Up", font_small, (200, 200, 255), (WIDTH//2, HEIGHT - 40))

        # Check win or give up
        if len(poles[2]) == num_disks or gave_up:
            completion_time = time.time() - start_time

            # Determine accuracy ratio:
            if move_count > 0:
                accuracy_ratio = min(1.0, optimal_moves / move_count)
            else:
                # no moves (maybe gave up immediately) -> use disks correctly placed on target as partial accuracy
                correct_disks = count_correct_on_target(poles, num_disks)
                accuracy_ratio = (correct_disks / num_disks) if num_disks > 0 else 0.0

            # Accuracy (0..40)
            accuracy_score = 40.0 * accuracy_ratio

            # Speed: human-friendly calculation (not compared to optimal solver time)
            speed_score, speed_ratio = compute_speed_score(completion_time, round_num, accuracy_ratio)

            # --- Consistency (now based on move timing stability) ---
            # build list of move intervals (seconds between consecutive valid moves)
            if len(move_timestamps) >= 2:
                intervals = [t2 - t1 for t1, t2 in zip(move_timestamps[:-1], move_timestamps[1:])]
                avg_interval = sum(intervals) / len(intervals)
                if len(intervals) > 1 and avg_interval > 0:
                    consistency_metric = max(0.0, 1.0 - (statistics.stdev(intervals) / avg_interval))
                else:
                    # only one interval -> treat as consistent
                    consistency_metric = 1.0
            else:
                # no moves or single move -> default to 0 if no moves, else 1
                consistency_metric = 1.0 if move_count > 0 else 0.0

            # Consistency score scaled to 0..10
            consistency_score = 10.0 * consistency_metric

            # --- Adaptability (based on invalid moves rate) ---
            adaptability_metric = max(0.0, 1.0 - (invalid_moves / max(1, move_count)))
            adaptability_score = 10.0 * adaptability_metric

            # Compose game score (0..100) using Option A weights:
            # Accuracy 40, Speed 40, Consistency 10, Adaptability 10
            game_score = accuracy_score + speed_score + consistency_score + adaptability_score
            game_score = max(0.0, min(100.0, game_score))

            # Apply round weight (weighted fraction used to sum across rounds)
            round_weight = ROUND_WEIGHTS[round_num - 1]
            weighted_fraction = (game_score / 100.0) * round_weight

            # Skill distribution (base: game_score * weight)
            skill_scores = {}
            for skill, w in target_skills.items():
                skill_scores[skill] = round(game_score * w, 2)

            # --- Override Spatial Awareness with a component-based formula ---
            invalid_rate = invalid_moves / max(1, move_count)
            validity = max(0.0, min(1.0, 1.0 - invalid_rate))

            w_acc = 0.50
            w_speed = 0.30
            w_valid = 0.20

            try:
                spd_ratio = speed_ratio
            except NameError:
                spd_ratio = 0.0

            spatial_component = (w_acc * accuracy_ratio) + (w_speed * spd_ratio) + (w_valid * validity)
            spatial_component = max(0.0, min(1.0, spatial_component))
            spatial_component_0_100 = spatial_component * 100.0

            spatial_key = "Spatial Awareness & Planning"
            if spatial_key in target_skills:
                spatial_weight = target_skills[spatial_key]
                skill_scores[spatial_key] = round(spatial_component_0_100 * spatial_weight, 2)
            else:
                skill_scores[spatial_key] = round(spatial_component_0_100, 2)

            # Count correct disks on target (for reporting)
            correct_disks = count_correct_on_target(poles, num_disks)

            # Prepare some additional reporting values
            avg_move_interval = None
            if len(move_timestamps) >= 2:
                intervals = [t2 - t1 for t1, t2 in zip(move_timestamps[:-1], move_timestamps[1:])]
                avg_move_interval = round(sum(intervals) / len(intervals), 3)

            results = {
                "game_name": "Tower of Hanoi",
                "round": round_num,
                "disks": num_disks,
                "total_moves": move_count,
                "invalid_moves": invalid_moves,
                "optimal_moves": optimal_moves,
                "accuracy_ratio": round(accuracy_ratio, 4),
                "accuracy_score_0_40": round(accuracy_score, 3),
                "completion_time_s": round(completion_time, 3),
                "speed_ratio": speed_ratio,
                "speed_score_0_40": round(speed_score, 3),
                "consistency_metric": round(consistency_metric, 4),
                "consistency_score_0_10": round(consistency_score, 3),
                "adaptability_metric": round(adaptability_metric, 4),
                "adaptability_score_0_10": round(adaptability_score, 3),
                "game_score_0_100": round(game_score, 3),
                "weighted_fraction": round(weighted_fraction, 4),
                "gave_up": bool(gave_up),
                "correct_disks_on_target": correct_disks,
                "avg_move_interval_s": avg_move_interval,
                "skill_scores": skill_scores
            }

            pygame.display.flip()
            time.sleep(0.8)
            return weighted_fraction, results

        pygame.display.flip()

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    gave_up = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                for i, pole_x in enumerate(POLE_X):
                    if abs(x - pole_x) < 80 and POLE_Y - POLE_HEIGHT < y < POLE_Y:
                        if selected_disk is None:
                            if poles[i]:
                                selected_disk = poles[i][-1]
                                selected_pole = i
                        else:
                            if i != selected_pole:
                                # valid move if destination empty or top disk larger than selected
                                if not poles[i] or poles[i][-1] > selected_disk:
                                    poles[i].append(selected_disk)
                                    poles[selected_pole].pop()
                                    move_count += 1
                                    move_timestamps.append(time.time())
                                else:
                                    invalid_moves += 1
                            selected_disk = None
                            selected_pole = None
                        break
        clock.tick(30)

def wait_for_enter(text):
    waiting = True
    while waiting:
        draw_background()
        draw_text(text, font_large, TEXT_COLOR, (WIDTH//2, HEIGHT//2))
        draw_text("Press ENTER to start", font_small, TEXT_COLOR, (WIDTH//2, HEIGHT//2 + 50))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                waiting = False

# ---- Game Flow ----
if __name__ == "__main__":
    rounds = [(3, 1), (4, 2), (5, 3)]
    total_weighted = 0.0
    all_results = []

    for num_disks, round_num in rounds:
        wait_for_enter(f"Round {round_num} - {num_disks} Disks")
        weighted_frac, result = tower_of_hanoi(num_disks, round_num)
        total_weighted += weighted_frac
        all_results.append(result)

    # final_score (0..100)
    final_score = round(total_weighted * 100.0, 2)

    # ---- Aggregate Skill Breakdown ----
    aggregated_skills = {skill: 0.0 for skill in target_skills}
    for r in all_results:
        for skill, val in r["skill_scores"].items():
            aggregated_skills[skill] += val
    for skill in aggregated_skills:
        aggregated_skills[skill] = round(aggregated_skills[skill] / len(all_results), 2)

    final_output = {
        "game": "Tower of Hanoi",
        "final_score_0_100": final_score,
        "average_skill_scores": aggregated_skills,
        "round_details": all_results
    }

    with open("tower_of_hanoi_final.json", "w") as f:
        json.dump(final_output, f, indent=4)

    print("\n🏁 Tower of Hanoi Completed!")
    print(json.dumps(final_output, indent=4))
    pygame.quit()
