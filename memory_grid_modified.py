# memory_grid_modified.py
import pygame
import random
import sys
import time
import json
import statistics

pygame.init()

WIDTH, HEIGHT = 600, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Memory Grid Game - Cognitive Skills Test")

WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (50, 150, 255)
BUTTON_COLOR = (255, 80, 80)
BUTTON_HOVER = (255, 120, 120)

font_large = pygame.font.SysFont("arial", 36)
font_small = pygame.font.SysFont("arial", 24)

def draw_text(text, font, color, center):
    text_surface = font.render(text, True, color)
    rect = text_surface.get_rect(center=center)
    screen.blit(text_surface, rect)

def draw_button(text, rect, hover):
    color = BUTTON_HOVER if hover else BUTTON_COLOR
    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, BLACK, rect, 2, border_radius=8)
    draw_text(text, font_small, WHITE, rect.center)

# Human-friendly speed normalization per grid size (seconds)
MAX_TIME_PER_GRID = {
    4: 60,   # 4x4
    6: 90,   # 6x6
    8: 120   # 8x8
}
MIN_PLAUSIBLE_TIME = 0.2  # fastest plausible overall time

def compute_speed_score(total_time, grid_size, accuracy_ratio):
    """
    Compute speed score (0..40).
    Uses a human-friendly normalization between MIN_PLAUSIBLE_TIME and MAX_TIME_PER_GRID.
    Multiplies by accuracy_ratio so speed only contributes when there's correct answers.
    """
    max_time = MAX_TIME_PER_GRID.get(grid_size, 120)
    min_time = MIN_PLAUSIBLE_TIME
    t = max(0.0, total_time)
    if t >= max_time or accuracy_ratio <= 0:
        speed_ratio = 0.0
    else:
        denom = (max_time - min_time)
        speed_ratio = (max_time - t) / denom if denom > 0 else 0.0
        speed_ratio = max(0.0, min(1.0, speed_ratio))
    speed_score = 40.0 * speed_ratio * accuracy_ratio
    return speed_score, round(speed_ratio, 4)

def memory_round(grid_size, round_number):
    """Runs a single round and returns metrics for that round."""
    cell_size = WIDTH // grid_size
    score = 0                     # number of fully-correct questions
    total_clicks = 0
    correct_clicks = 0
    reaction_times = []           # per-click reaction times
    question_correct_count = 0    # fully correct questions count
    give_up = False

    clock = pygame.time.Clock()
    pattern_display_time = 0.4
    time_between_patterns = 0.25

    round_start_time = time.time()
    last_click_time = time.time()

    QUESTIONS_PER_ROUND = 6
    for question in range(QUESTIONS_PER_ROUND):
        # pattern size grows modestly with question index
        pattern_count = min(3 + question, (grid_size ** 2) // 2)
        pattern = random.sample(range(grid_size ** 2), pattern_count)

        # --- SHOW PHASE ---
        # show empty grid, then flash cells one-by-one
        for idx in range(grid_size ** 2):
            row, col = divmod(idx, grid_size)
            rect = pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)
            pygame.draw.rect(screen, GRAY, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
        pygame.display.flip()
        time.sleep(0.35)

        for idx in pattern:
            row, col = divmod(idx, grid_size)
            rect = pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)
            pygame.draw.rect(screen, BLUE, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            pygame.display.flip()
            time.sleep(pattern_display_time)
            pygame.draw.rect(screen, GRAY, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            pygame.display.flip()
            time.sleep(time_between_patterns)

        # --- CLICK PHASE ---
        remaining = pattern_count
        clicked = set()
        question_correct = True

        give_up_rect = pygame.Rect(WIDTH//2 - 80, HEIGHT - 60, 160, 40)

        while remaining > 0:
            # draw grid and UI
            screen.fill(BLACK)
            for idx in range(grid_size ** 2):
                row, col = divmod(idx, grid_size)
                rect = pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)
                pygame.draw.rect(screen, GRAY, rect)
                pygame.draw.rect(screen, BLACK, rect, 2)

            mouse_pos = pygame.mouse.get_pos()
            draw_button("Give Up Round", give_up_rect, give_up_rect.collidepoint(mouse_pos))

            draw_text(f"Round {round_number}", font_small, YELLOW, (WIDTH//2, 20))
            draw_text(f"Round Score: {score}", font_small, WHITE, (520, 20))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if give_up_rect.collidepoint(event.pos):
                        give_up = True
                        # Return a standardized give-up result for this round
                        return {
                            "round": round_number,
                            "grid_size": grid_size,
                            "round_game_score_0_100": 0.0,
                            "score_questions_correct": 0,
                            "total_clicks": 0,
                            "correct_clicks": 0,
                            "accuracy_ratio": 0.0,
                            "avg_reaction_time_s": 0.0,
                            "consistency_metric": 0.0,
                            "adaptability_metric": 0.0,
                            "gave_up": True,
                            "skill_scores": {
                                "Memory": 0.0,
                                "Attention & Focus": 0.0,
                                "Processing Speed": 0.0,
                                "Visual-Spatial Awareness": 0.0,
                                "Cognitive Flexibility": 0.0
                            }
                        }

                    x, y = pygame.mouse.get_pos()
                    col = x // cell_size
                    row = y // cell_size
                    idx = row * grid_size + col
                    # ensure click inside grid
                    if 0 <= idx < grid_size ** 2 and idx not in clicked:
                        clicked.add(idx)
                        total_clicks += 1
                        rt = time.time() - last_click_time
                        reaction_times.append(rt)
                        last_click_time = time.time()

                        rect = pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)
                        if idx in pattern:
                            pygame.draw.rect(screen, GREEN, rect)
                            correct_clicks += 1
                            remaining -= 1
                        else:
                            pygame.draw.rect(screen, RED, rect)
                            question_correct = False
                            # break out: this question is failed
                            remaining = 0
                        pygame.draw.rect(screen, BLACK, rect, 2)
                        pygame.display.flip()
                        time.sleep(0.30)

            clock.tick(30)

        if question_correct:
            score += 1
            question_correct_count += 1

    # --- end of round questions ---
    round_completion_time = time.time() - round_start_time

    # If give up, we already returned above.
    # Compute core metrics, guarding divisions:
    accuracy_ratio = (correct_clicks / total_clicks) if total_clicks > 0 else 0.0
    avg_rt = (sum(reaction_times) / len(reaction_times)) if reaction_times else 0.0

    # Consistency: based on reaction-time stability (intervals)
    if len(reaction_times) >= 2 and avg_rt > 0:
        # Use stdev/avg pattern as consistency metric
        consistency_metric = max(0.0, 1.0 - (statistics.stdev(reaction_times) / avg_rt))
    else:
        # single click or no clicks -> default to 1 if some clicks exist, else 0
        consistency_metric = 1.0 if len(reaction_times) >= 1 else 0.0

    # Adaptability: fraction of questions fully correct
    adaptability_metric = question_correct_count / QUESTIONS_PER_ROUND if QUESTIONS_PER_ROUND > 0 else 0.0

    # Accuracy score (0..40)
    accuracy_score = 40.0 * accuracy_ratio

    # Speed score (0..40) - based on total round time and accuracy
    speed_score, speed_ratio = compute_speed_score(round_completion_time, grid_size, accuracy_ratio)

    # Consistency score (0..10)
    consistency_score = 10.0 * consistency_metric

    # Adaptability score (0..10)
    adaptability_score = 10.0 * adaptability_metric

    # Compose round game_score (0..100)
    round_game_score = accuracy_score + speed_score + consistency_score + adaptability_score
    round_game_score = max(0.0, min(100.0, round_game_score))

    # Map round -> global skill contributions (weights sum to 1)
    # Chosen weights for Memory Grid:
    # Memory (0.40), Attention (0.25), Processing Speed (0.15), Visual-Spatial (0.15), Cognitive Flexibility (0.05)
    skill_weights = {
        "Memory": 0.40,
        "Attention & Focus": 0.25,
        "Processing Speed": 0.15,
        "Visual-Spatial Awareness": 0.15,
        "Cognitive Flexibility": 0.05
    }

    skill_scores = {k: round(round_game_score * w, 2) for k, w in skill_weights.items()}

    results = {
        "round": round_number,
        "grid_size": grid_size,
        "round_game_score_0_100": round_game_score,
        "score_questions_correct": question_correct_count,
        "total_clicks": total_clicks,
        "correct_clicks": correct_clicks,
        "accuracy_ratio": round(accuracy_ratio, 4),
        "avg_reaction_time_s": round(avg_rt, 3),
        "consistency_metric": round(consistency_metric, 4),
        "adaptability_metric": round(adaptability_metric, 4),
        "completion_time_s": round(round_completion_time, 3),
        "speed_ratio": speed_ratio,
        "gave_up": give_up,
        "skill_scores": skill_scores
    }

    # small visual feedback before returning
    screen.fill(BLACK)
    draw_text(f"🎯 Round {round_number} Complete!", font_large, YELLOW, (WIDTH//2, HEIGHT//2 - 40))
    draw_text(f"Round Score: {int(round_game_score)}", font_small, WHITE, (WIDTH//2, HEIGHT//2 + 10))
    pygame.display.flip()
    time.sleep(1.2)
    return results

def memory_game():
    """
    Runs 3 rounds (4x4, 6x6, 8x8), aggregates round scores into a single
    weighted game score (0..100), and returns per-game results.
    """
    # rounds settings and weights (weights only for per-game aggregation)
    round_settings = [(4, 0.25), (6, 0.35), (8, 0.40)]
    all_results = []
    weighted_sum = 0.0
    total_weight = 0.0

    # aggregate skill summary (keep sums then divide by total weight)
    skill_accumulator = {
        "Memory": 0.0,
        "Attention & Focus": 0.0,
        "Processing Speed": 0.0,
        "Visual-Spatial Awareness": 0.0,
        "Cognitive Flexibility": 0.0
    }

    for idx, (grid, weight) in enumerate(round_settings, start=1):
        res = memory_round(grid, idx)
        all_results.append(res)
        # If player gave up, round_game_score_0_100 is expected 0.0 (we standardized above)
        round_score = res.get("round_game_score_0_100", 0.0)
        weighted_sum += round_score * weight
        total_weight += weight
        # accumulate skill contributions (each res["skill_scores"] are 0..100 per skill)
        for s in skill_accumulator:
            skill_accumulator[s] += res["skill_scores"].get(s, 0.0) * weight

    # Final weighted game score normalized
    final_weighted_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    final_weighted_score = round(final_weighted_score, 2)  # 0..100

    # Final skill scores averaged by weight
    final_skill_scores = {k: round(v / total_weight, 2) if total_weight > 0 else 0.0 for k, v in skill_accumulator.items()}

    summary = {
        "game_name": "Memory Grid",
        "total_rounds": len(round_settings),
        "weighted_game_score_0_100": final_weighted_score,
        "round_results": all_results,
        "final_skill_scores": final_skill_scores
    }

    # Display final screen briefly
    screen.fill(BLACK)
    draw_text("🏁 Memory Grid Completed!", font_large, (255, 215, 0), (WIDTH//2, HEIGHT//2 - 40))
    draw_text(f"Final Game Score: {int(final_weighted_score)} / 100", font_small, WHITE, (WIDTH//2, HEIGHT//2 + 10))
    pygame.display.flip()
    time.sleep(2.0)

    # Save per-game JSON (no cross-game CPS here)
    with open("memory_grid_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    pygame.quit()
    return summary

if __name__ == "__main__":
    memory_game()
