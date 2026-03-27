import pygame
import random
import sys
import time
import math
import statistics
import json

# Grid-based Shape–Color Switch (3 rounds: 4x4, 8x8, 12x12)
# Scoring per round: Accuracy(40) + Speed(40) + Consistency(10) + Adaptability(10)
# Give-Up button skips only that round (round score = 0) and moves to next round.

pygame.init()
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Grid Shape–Color Switch — Cognitive Flexibility Test")

# Colors, shapes, fonts
BG_TOP = (30, 30, 60)
BG_BOTTOM = (10, 10, 30)
TEXT_COLOR = (255, 255, 255)
COLORS = {"red": (230, 80, 80), "blue": (80, 150, 255), "green": (60, 200, 100), "yellow": (250, 220, 70)}
SHAPES = ["circle", "square", "triangle", "diamond"]
font_large = pygame.font.SysFont("arial", 32)
font_small = pygame.font.SysFont("arial", 20)

# Scoring constants
ACCURACY_WEIGHT = 40.0
SPEED_WEIGHT = 40.0
CONSISTENCY_WEIGHT = 10.0
ADAPTABILITY_WEIGHT = 10.0
MIN_PLAUSIBLE_RT = 0.05
BASE_MAX_TIME_4x4 = 25.0  # baseline for 4x4; scaled by grid area

# Rounds configuration (grid sizes)
ROUNDS = [4, 8, 12]

# UI layout
TOP_MARGIN = 110
SIDE_PADDING = 40
BOTTOM_MARGIN = 80
GIVEUP_BTN_RECT = pygame.Rect(WIDTH - 170, HEIGHT - 60, 140, 40)

clock = pygame.time.Clock()


def draw_background():
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio
        g = BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio
        b = BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio
        pygame.draw.line(screen, (int(r), int(g), int(b)), (0, y), (WIDTH, y))


def draw_text(text, font, color, center):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center)
    screen.blit(surf, rect)


def draw_button(text, rect, hover=False):
    color = (200, 40, 40) if not hover else (230, 70, 70)
    pygame.draw.rect(screen, color, rect, border_radius=6)
    pygame.draw.rect(screen, (0, 0, 0), rect, 2, border_radius=6)
    draw_text(text, font_small, (255, 255, 255), rect.center)


def draw_shape_at(cell_rect, shape_name, color):
    cx = cell_rect.centerx
    cy = cell_rect.centery
    w = int(cell_rect.width * 0.5)
    h = int(cell_rect.height * 0.5)
    if shape_name == "circle":
        pygame.draw.circle(screen, color, (cx, cy), min(w, h) // 2)
    elif shape_name == "square":
        side = min(w, h)
        r = pygame.Rect(cx - side // 2, cy - side // 2, side, side)
        pygame.draw.rect(screen, color, r, border_radius=6)
    elif shape_name == "triangle":
        pts = [(cx, cy - h // 2), (cx - w // 2, cy + h // 2), (cx + w // 2, cy + h // 2)]
        pygame.draw.polygon(screen, color, pts)
    elif shape_name == "diamond":
        pts = [(cx, cy - h // 2), (cx - w // 2, cy), (cx, cy + h // 2), (cx + w // 2, cy)]
        pygame.draw.polygon(screen, color, pts)
    else:
        pygame.draw.circle(screen, color, (cx, cy), min(w, h) // 2)


def compute_max_time_for_grid(grid):
    area = grid * grid
    scale = area / 16.0  # 4x4 baseline
    return BASE_MAX_TIME_4x4 * scale


def compute_round_scores(total_clicks, correct_clicks, reaction_times, completion_time, targets_cleared, targets_total, grid):
    # Accuracy
    accuracy_ratio = (correct_clicks / total_clicks) if total_clicks > 0 else 0.0

    # Average RT
    avg_rt = (sum(reaction_times) / len(reaction_times)) if reaction_times else 0.0

    # Speed normalization (grid-aware)
    max_time = compute_max_time_for_grid(grid)
    if completion_time <= 0 or accuracy_ratio <= 0:
        speed_ratio = 0.0
    else:
        t = max(completion_time, MIN_PLAUSIBLE_RT)
        if t >= max_time:
            speed_ratio = 0.0
        else:
            speed_ratio = (max_time - t) / (max_time - MIN_PLAUSIBLE_RT)
            speed_ratio = max(0.0, min(1.0, speed_ratio))
    speed_component = speed_ratio * accuracy_ratio

    # Consistency
    if len(reaction_times) > 1 and avg_rt > 0:
        consistency_metric = max(0.0, 1.0 - (statistics.stdev(reaction_times) / avg_rt))
    else:
        consistency_metric = 1.0 if len(reaction_times) >= 1 else 0.0

    # Adaptability
    adaptability_metric = (targets_cleared / targets_total) if targets_total > 0 else 0.0

    # Component scores
    accuracy_score = ACCURACY_WEIGHT * accuracy_ratio
    speed_score = SPEED_WEIGHT * speed_component
    consistency_score = CONSISTENCY_WEIGHT * consistency_metric
    adaptability_score = ADAPTABILITY_WEIGHT * adaptability_metric

    round_score = accuracy_score + speed_score + consistency_score + adaptability_score
    round_score = max(0.0, min(100.0, round_score))

    breakdown = {
        "accuracy_ratio": round(accuracy_ratio, 4),
        "avg_reaction_time_s": round(avg_rt, 4),
        "speed_ratio": round(speed_ratio, 4),
        "speed_component": round(speed_component, 4),
        "consistency_metric": round(consistency_metric, 4),
        "adaptability_metric": round(adaptability_metric, 4),
        "accuracy_score_0_40": round(accuracy_score, 3),
        "speed_score_0_40": round(speed_score, 3),
        "consistency_score_0_10": round(consistency_score, 3),
        "adaptability_score_0_10": round(adaptability_score, 3),
        "round_score_0_100": round(round_score, 3),
    }
    return round_score, breakdown


def run_round(grid_size, round_index):
    # prepare grid layout
    grid_area_w = WIDTH - SIDE_PADDING * 2
    grid_area_h = HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
    grid_area = min(grid_area_w, grid_area_h)
    cell_size = grid_area // grid_size
    # center grid
    grid_w = cell_size * grid_size
    grid_h = cell_size * grid_size
    left = (WIDTH - grid_w) // 2
    top = TOP_MARGIN + (grid_area_h - grid_h) // 2

    # choose rule: color + shape
    target_color = random.choice(list(COLORS.keys()))
    target_shape = random.choice(SHAPES)

    # determine target count: 1 to 4 scaled with grid
    targets_total = max(1, min(6, grid_size // 2))

    # fill grid with items
    cells = []
    indices = list(range(grid_size * grid_size))
    random.shuffle(indices)
    target_indices = set(indices[:targets_total])

    for idx in range(grid_size * grid_size):
        row, col = divmod(idx, grid_size)
        cell_rect = pygame.Rect(left + col * cell_size, top + row * cell_size, cell_size, cell_size)
        if idx in target_indices:
            cells.append({"color": target_color, "shape": target_shape, "rect": cell_rect, "is_target": True})
        else:
            # choose decoy: sometimes share color or shape to increase difficulty
            if random.random() < 0.5:
                # share one attribute
                if random.random() < 0.5:
                    c = target_color
                    s = random.choice([sh for sh in SHAPES if sh != target_shape])
                else:
                    s = target_shape
                    c = random.choice([co for co in COLORS.keys() if co != target_color])
            else:
                c = random.choice([co for co in COLORS.keys() if co != target_color])
                s = random.choice([sh for sh in SHAPES if sh != target_shape])
            cells.append({"color": c, "shape": s, "rect": cell_rect, "is_target": False})

    # round metrics
    total_clicks = 0
    correct_clicks = 0
    reaction_times = []
    targets_cleared = 0
    round_start = time.time()
    last_interaction = round_start
    gave_up = False

    running = True
    while running:
        draw_background()
        # header
        draw_text(f"Round {round_index + 1} — Grid {grid_size}×{grid_size}", font_large, TEXT_COLOR, (WIDTH // 2, 40))
        draw_text(f"Find: {target_color.upper()} {target_shape.upper()}", font_small, TEXT_COLOR, (WIDTH // 2, 76))
        # draw Give-Up button
        mx, my = pygame.mouse.get_pos()
        hover = GIVEUP_BTN_RECT.collidepoint((mx, my))
        draw_button("Give Up", GIVEUP_BTN_RECT, hover)

        # draw grid
        for i, c in enumerate(cells):
            rect = c["rect"]
            pygame.draw.rect(screen, (220, 220, 220), rect, 1)
            draw_shape_at(rect, c["shape"], COLORS[c["color"]])

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if GIVEUP_BTN_RECT.collidepoint(pos):
                    gave_up = True
                    running = False
                    break
                # detect clicked cell
                for idx, c in enumerate(cells):
                    if c["rect"].collidepoint(pos):
                        total_clicks += 1
                        rt = time.time() - last_interaction
                        last_interaction = time.time()
                        if c["is_target"]:
                            correct_clicks += 1
                            reaction_times.append(rt)
                            targets_cleared += 1
                            # mark cleared so it is no longer a target
                            cells[idx]["is_target"] = False
                            # optional visual feedback handled next frame
                        else:
                            # wrong click: record slightly penalized rt
                            reaction_times.append(rt + 0.2)
                        break

        # check end condition: all targets cleared
        remaining_targets = [c for c in cells if c.get("is_target")]
        if not remaining_targets or gave_up:
            running = False

        clock.tick(60)

    completion_time = time.time() - round_start

    if gave_up:
        # standardized give-up result for this round
        round_score = 0.0
        breakdown = {
            "accuracy_ratio": 0.0,
            "avg_reaction_time_s": 0.0,
            "speed_ratio": 0.0,
            "speed_component": 0.0,
            "consistency_metric": 0.0,
            "adaptability_metric": 0.0,
            "accuracy_score_0_40": 0.0,
            "speed_score_0_40": 0.0,
            "consistency_score_0_10": 0.0,
            "adaptability_score_0_10": 0.0,
            "round_score_0_100": 0.0,
        }
    else:
        round_score, breakdown = compute_round_scores(
            total_clicks=total_clicks,
            correct_clicks=correct_clicks,
            reaction_times=reaction_times,
            completion_time=completion_time,
            targets_cleared=targets_cleared,
            targets_total=targets_total,
            grid=grid_size
        )

    # round record
    record = {
        "round_index": round_index + 1,
        "grid_size": grid_size,
        "target_rule": f"{target_color} {target_shape}",
        "total_clicks": total_clicks,
        "correct_clicks": correct_clicks,
        "targets_total": targets_total,
        "targets_cleared": targets_cleared,
        "completion_time_s": round(completion_time, 3),
        "gave_up": bool(gave_up),
        "breakdown": breakdown
    }
    return record


def shape_color_grid_game():
    rounds_results = []
    for i, grid in enumerate(ROUNDS):
        # inter-round banner
        t0 = time.time()
        while time.time() - t0 < 0.7:
            draw_background()
            draw_text(f"Get ready — Round {i+1}", font_large, (255, 215, 0), (WIDTH // 2, HEIGHT // 2))
            pygame.display.flip()
            clock.tick(30)

        res = run_round(grid, i)
        rounds_results.append(res)

    # aggregate
    avg_score = sum(r["breakdown"]["round_score_0_100"] for r in rounds_results) / len(rounds_results)

    skill_weights = {
        "Attention & Focus": 0.40,
        "Processing Speed & Reaction Time": 0.35,
        "Cognitive Flexibility": 0.25
    }
    skill_scores = {k: round(avg_score * w, 2) for k, w in skill_weights.items()}

    game_result = {
        "game_name": "Grid Shape–Color Switch",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rounds": rounds_results,
        "game_score_0_100": round(avg_score, 3),
        "skill_scores": skill_scores
    }

    with open("shape_color_grid_results.json", "w") as f:
        json.dump(game_result, f, indent=2)

    # final screen
    draw_background()
    draw_text("🎯 Test Complete!", font_large, (255, 215, 0), (WIDTH // 2, HEIGHT // 2 - 40))
    draw_text(f"Game Score: {game_result['game_score_0_100']} / 100", font_small, TEXT_COLOR, (WIDTH // 2, HEIGHT // 2 + 10))
    pygame.display.flip()

    print(json.dumps(game_result, indent=2))

    # wait for exit
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit(); sys.exit()


if __name__ == '__main__':
    shape_color_grid_game()
