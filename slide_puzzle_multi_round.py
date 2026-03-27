# slide_puzzle_multi_round.py
# Modified Slide Puzzle with 3 rounds (3x4, 4x4, 5x5), Give Up, and scoring/logging
import pygame, sys, random, time, json, math, statistics
from pygame.locals import *

# ---- Visual / timing constants ----
TILESIZE = 80
FPS = 30
BLANK = None

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BRIGHTBLUE = (0, 50, 255)
DARKTURQUOISE = (3, 54, 73)
GREEN = (0, 204, 0)

BGCOLOR = DARKTURQUOISE
TILECOLOR = GREEN
TEXTCOLOR = WHITE
BORDERCOLOR = BRIGHTBLUE
BASICFONTSIZE = 20

BUTTONCOLOR = (230, 230, 230)
BUTTONTEXT = (20, 20, 20)

# ---- Round definitions (Option A chosen) ----
ROUNDS = [
    {"width": 3, "height": 4},  # round 1: 3x4 => 11 tiles + 1 blank
    {"width": 4, "height": 4},  # round 2: 4x4 => 15 tiles + 1 blank
    {"width": 5, "height": 5},  # round 3: 5x5 => 24 tiles + 1 blank
]

# Window — will be recalculated per round to center board nicely
WINDOWWIDTH = 800
WINDOWHEIGHT = 600

# margins will be set after board size is set per round
XMARGIN = 0
YMARGIN = 0

UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

# JSON output file
RESULTS_FILE = "slide_puzzle_results.json"

def main():
    pygame.init()
    clock = pygame.time.Clock()
    font = pygame.font.Font('freesansbold.ttf', BASICFONTSIZE)

    all_round_results = []
    overall_start = time.time()

    for round_idx, rd in enumerate(ROUNDS, start=1):
        BOARDWIDTH = rd["width"]
        BOARDHEIGHT = rd["height"]
        cells = BOARDWIDTH * BOARDHEIGHT
        total_tiles = cells - 1  # one blank

        # center layout calculations
        global XMARGIN, YMARGIN, TILESIZE_LOCAL
        # scale tile size down if board too big for window
        max_tile_width = (WINDOWWIDTH - 80) // BOARDWIDTH
        max_tile_height = (WINDOWHEIGHT - 140) // BOARDHEIGHT
        TILESIZE_LOCAL = min(TILESIZE, max_tile_width, max_tile_height)
        XMARGIN = int((WINDOWWIDTH - (TILESIZE_LOCAL * BOARDWIDTH + (BOARDWIDTH - 1))) / 2)
        YMARGIN = int((WINDOWHEIGHT - (TILESIZE_LOCAL * BOARDHEIGHT + (BOARDHEIGHT - 1))) / 2)

        screen = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
        pygame.display.set_caption(f"Slide Puzzle — Round {round_idx} ({BOARDWIDTH}x{BOARDHEIGHT})")

        # Generate starting (solved) board for this shape
        solved = get_starting_board(BOARDWIDTH, BOARDHEIGHT)
        # We'll scramble by making random legal moves
        board = [ [solved[x][y] for y in range(BOARDHEIGHT)] for x in range(BOARDWIDTH) ]
        pygame.time.wait(300)
        scramble_moves = 60 + round_idx * 20  # increase scrambling a bit each round
        lastMove = None
        for _ in range(scramble_moves):
            move = get_random_move(board, lastMove)
            make_move(board, move)
            lastMove = move

        # Round variables and UI elements
        round_start_time = time.time()
        move_count = 0
        move_timestamps = []  # times at which valid moves occurred
        give_up = False
        round_done = False

        # Build Give Up button rect
        give_surf = font.render("GIVE UP", True, BUTTONTEXT, BUTTONCOLOR)
        give_rect = give_surf.get_rect()
        give_rect.topleft = (WINDOWWIDTH - give_rect.width - 20, 20)

        # Main loop for the round
        while not round_done:
            screen.fill(BGCOLOR)
            # show round info
            header = font.render(f"Round {round_idx} — {BOARDWIDTH} x {BOARDHEIGHT} (tiles 1..{total_tiles})", True, TEXTCOLOR)
            screen.blit(header, (20, 20))
            moves_surf = font.render(f"Moves: {move_count}", True, TEXTCOLOR)
            screen.blit(moves_surf, (20, 50))
            elapsed = time.time() - round_start_time
            time_surf = font.render(f"Time: {int(elapsed)}s", True, TEXTCOLOR)
            screen.blit(time_surf, (20, 80))

            # number of correct tiles live-update
            correct_now = count_correct_tiles(board, BOARDWIDTH, BOARDHEIGHT)
            correct_surf = font.render(
                f"Correct Tiles: {correct_now}/{BOARDWIDTH*BOARDHEIGHT - 1}", 
                True, TEXTCOLOR
            )
            screen.blit(correct_surf, (20, 110))



            # draw give up button
            screen.blit(give_surf, give_rect)

            # draw board
            draw_board(screen, board, BOARDWIDTH, BOARDHEIGHT, font)

            # check events
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONUP:
                    mousex, mousey = event.pos
                    # give up click?
                    if give_rect.collidepoint(event.pos):
                        give_up = True
                        round_done = True
                        round_end_time = time.time()
                        break
                    # tile click?
                    spotx, spoty = get_spot_clicked(board, mousex, mousey, BOARDWIDTH, BOARDHEIGHT)
                    if (spotx, spoty) != (None, None):
                        blankx, blanky = get_blank_position(board, BOARDWIDTH, BOARDHEIGHT)
                        direction = None
                        if spotx == blankx + 1 and spoty == blanky:
                            direction = LEFT
                        elif spotx == blankx - 1 and spoty == blanky:
                            direction = RIGHT
                        elif spotx == blankx and spoty == blanky + 1:
                            direction = UP
                        elif spotx == blankx and spoty == blanky - 1:
                            direction = DOWN
                        if direction:
                            slide_animation(screen, board, direction, BOARDWIDTH, BOARDHEIGHT, font, TILESIZE_LOCAL)
                            make_move(board, direction)
                            move_count += 1
                            move_timestamps.append(time.time())
                elif event.type == KEYUP:
                    # allow arrow keys to move
                    if event.key in (K_LEFT, K_a) and is_valid_move(board, LEFT, BOARDWIDTH, BOARDHEIGHT):
                        slide_animation(screen, board, LEFT, BOARDWIDTH, BOARDHEIGHT, font, TILESIZE_LOCAL)
                        make_move(board, LEFT)
                        move_count += 1
                        move_timestamps.append(time.time())
                    elif event.key in (K_RIGHT, K_d) and is_valid_move(board, RIGHT, BOARDWIDTH, BOARDHEIGHT):
                        slide_animation(screen, board, RIGHT, BOARDWIDTH, BOARDHEIGHT, font, TILESIZE_LOCAL)
                        make_move(board, RIGHT)
                        move_count += 1
                        move_timestamps.append(time.time())
                    elif event.key in (K_UP, K_w) and is_valid_move(board, UP, BOARDWIDTH, BOARDHEIGHT):
                        slide_animation(screen, board, UP, BOARDWIDTH, BOARDHEIGHT, font, TILESIZE_LOCAL)
                        make_move(board, UP)
                        move_count += 1
                        move_timestamps.append(time.time())
                    elif event.key in (K_DOWN, K_s) and is_valid_move(board, DOWN, BOARDWIDTH, BOARDHEIGHT):
                        slide_animation(screen, board, DOWN, BOARDWIDTH, BOARDHEIGHT, font, TILESIZE_LOCAL)
                        make_move(board, DOWN)
                        move_count += 1
                        move_timestamps.append(time.time())

            # check solved
            if board == solved:
                round_done = True
                round_end_time = time.time()

            pygame.display.update()
            clock.tick(FPS)

        # End of round: calc metrics
        total_time = round_end_time - round_start_time
        # count tiles in correct position
        correct_tiles = count_correct_tiles(board, BOARDWIDTH, BOARDHEIGHT)
        correctness_pct = (correct_tiles / (BOARDWIDTH * BOARDHEIGHT - 1)) * 100  # exclude blank from denominator

        # Speed: only relevant combined with correctness (we use correctness/time scaling)
        # Scale to 0..40. We choose a scaling constant so that reasonable times yield ~40.
        # speed_raw = (correctness_pct / max(0.1, total_time)) * scale_k
        # choose scale_k such that if correctness_pct==100 and total_time ~ 10s => about 40
        # scale_k = 10 * target => here use 4.0
        speed_raw = (correctness_pct / max(0.001, total_time)) * 2.5
        speed_score = min(40.0, speed_raw)

        # Accuracy score: correctness -> 0..40
        accuracy_score = (correctness_pct / 100.0) * 40.0

        # Consistency: use variability of move intervals (if <2 moves, consider perfect)
        consistency_score = 20.0
        if len(move_timestamps) >= 2:
            intervals = [t2 - t1 for t1, t2 in zip(move_timestamps[:-1], move_timestamps[1:])]
            avg_int = statistics.mean(intervals)
            std_int = statistics.pstdev(intervals) if len(intervals) > 1 else 0.0
            # normalized variability:
            var_ratio = std_int / (avg_int + 0.001)
            # damping factor: smaller var_ratio -> higher consistency
            # scale var_ratio so that var_ratio ~0.5 reduces some consistency, 1.0 reduces more
            consistency_score = max(0.0, 20.0 * (1.0 - 0.6 * var_ratio))
        else:
            # No or single move -> small deduction if user skipped quickly; keep full if solved quickly
            if move_count == 0:
                # no moves, user gave up immediately: give small neutral consistency (10)
                consistency_score = 10.0
            else:
                consistency_score = 18.0

        # Compose game_score
        game_score = accuracy_score + speed_score + consistency_score
        # clamp to 0..100
        game_score = max(0.0, min(100.0, game_score))

        # Domain-specific calculations (Slide Puzzle weights)
        # Primary: Spatial Reasoning (we agreed to round it)
        spatial = round(correctness_pct)
        # Problem solving: use correctness weighted by efficiency proxy (higher if fewer moves relative to board size)
        # Efficiency proxy = max(0.2, (1.0 - (move_count / (BOARDWIDTH*BOARDHEIGHT*3))))  # rough
        efficiency_proxy = max(0.1, 1.0 - (move_count / max(1.0, (BOARDWIDTH * BOARDHEIGHT * 3))))
        problem_solving = round((correctness_pct * 0.6 + efficiency_proxy * 100 * 0.4) / 1.0)
        # Processing speed domain use speed_score scaled to 0..100
        processing_speed = round((speed_score / 40.0) * 100)
        # Attention: tie to correctness as well (but include move accuracy)
        attention = round(correctness_pct)

        round_result = {
            "round": round_idx,
            "grid": f"{BOARDWIDTH}x{BOARDHEIGHT}",
            "total_tiles": total_tiles,
            "moves": move_count,
            "time_s": round(total_time, 2),
            "give_up": bool(give_up),
            "correct_tiles": correct_tiles,
            "correctness_pct": round(correctness_pct, 2),
            "accuracy_score_0_40": round(accuracy_score, 2),
            "speed_score_0_40": round(speed_score, 2),
            "consistency_score_0_20": round(consistency_score, 2),
            "game_score_0_100": round(game_score, 2),
            
            "spatial": spatial,
            "problem_solving": problem_solving,
            "processing_speed": processing_speed,
            "attention": attention
        }

        all_round_results.append(round_result)

        # brief inter-round display
        show_round_summary(screen, font, round_result)
        # small pause before next round
        pygame.time.wait(800)

    overall_end = time.time()
    total_duration = overall_end - overall_start

    # Aggregate final scores across rounds: simple average of game_score
    avg_game_score = sum(r["game_score_0_100"] for r in all_round_results) / len(all_round_results)
    # Aggregate domain scores: average per domain
    final_spatial = round(sum(r["spatial"] for r in all_round_results) / len(all_round_results))
    final_problem = round(sum(r["problem_solving"] for r in all_round_results) / len(all_round_results))
    final_processing = round(sum(r["processing_speed"] for r in all_round_results) / len(all_round_results))
    final_attention = round(sum(r["attention"] for r in all_round_results) / len(all_round_results))

    summary = {
        "game_name": "Slide Puzzle (3-round)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rounds": all_round_results,
        "total_duration_s": round(total_duration, 2),
        "avg_game_score_0_100": round(avg_game_score, 2),
        "final_domains": {
            "Spatial Reasoning": final_spatial,
            "Problem Solving": final_problem,
            "Processing Speed": final_processing,
            "Attention": final_attention
        }
    }

    # append to JSON results file
    with open(RESULTS_FILE, "a") as f:
        json.dump(summary, f)
        f.write("\n")

    print("\nSlide Puzzle Results:")
    print(json.dumps(summary, indent=4))

    # end screen showing final summary
    screen.fill(BGCOLOR)
    big = pygame.font.Font('freesansbold.ttf', 28)
    draw_text_center(screen, big, f"All rounds complete! Avg score: {round(avg_game_score,2)} / 100", (WINDOWWIDTH//2, WINDOWHEIGHT//2 - 20))
    draw_text_center(screen, font, "Press any key to exit.", (WINDOWWIDTH//2, WINDOWHEIGHT//2 + 20))
    pygame.display.update()
    # wait for key or quit
    waiting = True
    while waiting:
        for e in pygame.event.get():
            if e.type == QUIT:
                pygame.quit(); sys.exit()
            elif e.type == KEYDOWN or e.type == MOUSEBUTTONDOWN:
                waiting = False
    pygame.quit()
    return

# ---------- Helper functions ----------

def draw_text_center(surface, font, text, center):
    surf = font.render(text, True, TEXTCOLOR)
    rect = surf.get_rect(center=center)
    surface.blit(surf, rect)

def get_starting_board(boardwidth, boardheight):
    # create solved board for given dimensions
    counter = 1
    board = []
    for x in range(boardwidth):
        column = []
        for y in range(boardheight):
            column.append(counter)
            counter += boardwidth
        board.append(column)
        counter -= boardwidth * (boardheight - 1) + boardwidth - 1
    board[boardwidth-1][boardheight-1] = BLANK
    return board

def count_correct_tiles(board, boardwidth, boardheight):
    # count how many non-blank tiles are in their solved place (compared to starting board)
    solved = get_starting_board(boardwidth, boardheight)
    correct = 0
    for x in range(boardwidth):
        for y in range(boardheight):
            if solved[x][y] != BLANK and board[x][y] == solved[x][y]:
                correct += 1
    return correct

def get_blank_position(board, boardwidth, boardheight):
    for x in range(boardwidth):
        for y in range(boardheight):
            if board[x][y] == BLANK:
                return (x, y)

def make_move(board, move):
    blankx, blanky = get_blank_position(board, len(board), len(board[0]))
    if move == UP:
        board[blankx][blanky], board[blankx][blanky + 1] = board[blankx][blanky + 1], board[blankx][blanky]
    elif move == DOWN:
        board[blankx][blanky], board[blankx][blanky - 1] = board[blankx][blanky - 1], board[blankx][blanky]
    elif move == LEFT:
        board[blankx][blanky], board[blankx + 1][blanky] = board[blankx + 1][blanky], board[blankx][blanky]
    elif move == RIGHT:
        board[blankx][blanky], board[blankx - 1][blanky] = board[blankx - 1][blanky], board[blankx][blanky]

def is_valid_move(board, move, boardwidth, boardheight):
    blankx, blanky = get_blank_position(board, boardwidth, boardheight)
    return (move == UP and blanky != len(board[0]) - 1) or \
           (move == DOWN and blanky != 0) or \
           (move == LEFT and blankx != len(board) - 1) or \
           (move == RIGHT and blankx != 0)

def get_random_move(board, lastMove=None):
    validMoves = [UP, DOWN, LEFT, RIGHT]
    if lastMove == UP or not is_valid_move(board, DOWN, len(board), len(board[0])):
        if DOWN in validMoves: validMoves.remove(DOWN)
    if lastMove == DOWN or not is_valid_move(board, UP, len(board), len(board[0])):
        if UP in validMoves: validMoves.remove(UP)
    if lastMove == LEFT or not is_valid_move(board, RIGHT, len(board), len(board[0])):
        if RIGHT in validMoves: validMoves.remove(RIGHT)
    if lastMove == RIGHT or not is_valid_move(board, LEFT, len(board), len(board[0])):
        if LEFT in validMoves: validMoves.remove(LEFT)
    return random.choice(validMoves)

def get_left_top_of_tile(tileX, tileY):
    left = XMARGIN + (tileX * TILESIZE_LOCAL) + (tileX - 1)
    top = YMARGIN + (tileY * TILESIZE_LOCAL) + (tileY - 1)
    return (left, top)

def get_spot_clicked(board, x, y, boardwidth, boardheight):
    for tileX in range(boardwidth):
        for tileY in range(boardheight):
            left, top = get_left_top_of_tile(tileX, tileY)
            tileRect = pygame.Rect(left, top, TILESIZE_LOCAL, TILESIZE_LOCAL)
            if tileRect.collidepoint(x, y):
                return (tileX, tileY)
    return (None, None)

def draw_tile(surface, tilex, tiley, number):
    left, top = get_left_top_of_tile(tilex, tiley)
    if number != BLANK:
        pygame.draw.rect(surface, TILECOLOR, (left, top, TILESIZE_LOCAL, TILESIZE_LOCAL))
        textSurf = pygame.font.Font('freesansbold.ttf', BASICFONTSIZE).render(str(number), True, TEXTCOLOR)
        textRect = textSurf.get_rect()
        textRect.center = left + int(TILESIZE_LOCAL / 2), top + int(TILESIZE_LOCAL / 2)
        surface.blit(textSurf, textRect)
    else:
        # draw blank as background rect
        pygame.draw.rect(surface, BGCOLOR, (left, top, TILESIZE_LOCAL, TILESIZE_LOCAL))

def draw_board(surface, board, boardwidth, boardheight, font):
    left, top = get_left_top_of_tile(0, 0)
    width = boardwidth * TILESIZE_LOCAL
    height = boardheight * TILESIZE_LOCAL
    pygame.draw.rect(surface, BORDERCOLOR, (left - 5, top - 5, width + 11, height + 11), 4)
    for tilex in range(boardwidth):
        for tiley in range(boardheight):
            if board[tilex][tiley] is not None:
                draw_tile(surface, tilex, tiley, board[tilex][tiley])
            else:
                draw_tile(surface, tilex, tiley, BLANK)

def slide_animation(surface, board, direction, boardwidth, boardheight, font, tile_size):
    blankx, blanky = get_blank_position(board, boardwidth, boardheight)
    if direction == UP:
        movex, movey = blankx, blanky + 1
    elif direction == DOWN:
        movex, movey = blankx, blanky - 1
    elif direction == LEFT:
        movex, movey = blankx + 1, blanky
    elif direction == RIGHT:
        movex, movey = blankx - 1, blanky
    # prepare base
    draw_board(surface, board, boardwidth, boardheight, font)
    baseSurf = surface.copy()
    moveLeft, moveTop = get_left_top_of_tile(movex, movey)
    pygame.draw.rect(baseSurf, BGCOLOR, (moveLeft, moveTop, TILESIZE_LOCAL, TILESIZE_LOCAL))
    for i in range(0, TILESIZE_LOCAL, max(1, int(tile_size/4))):
        check_for_quit()
        surface.blit(baseSurf, (0,0))
        if direction == UP:
            draw_tile(surface, movex, movey, board[movex][movey])
            # visually offset
            rect = pygame.Rect(moveLeft, moveTop - i, TILESIZE_LOCAL, TILESIZE_LOCAL)
            pygame.draw.rect(surface, TILECOLOR, rect)
        elif direction == DOWN:
            rect = pygame.Rect(moveLeft, moveTop + i, TILESIZE_LOCAL, TILESIZE_LOCAL)
            pygame.draw.rect(surface, TILECOLOR, rect)
        elif direction == LEFT:
            rect = pygame.Rect(moveLeft - i, moveTop, TILESIZE_LOCAL, TILESIZE_LOCAL)
            pygame.draw.rect(surface, TILECOLOR, rect)
        elif direction == RIGHT:
            rect = pygame.Rect(moveLeft + i, moveTop, TILESIZE_LOCAL, TILESIZE_LOCAL)
            pygame.draw.rect(surface, TILECOLOR, rect)
        pygame.display.update()
        pygame.time.Clock().tick(FPS)

def check_for_quit():
    for event in pygame.event.get(QUIT):
        pygame.quit()
        sys.exit()
    for event in pygame.event.get(KEYUP):
        if event.key == K_ESCAPE:
            pygame.quit()
            sys.exit()
        pygame.event.post(event)

def show_round_summary(screen, font, round_result):
    screen.fill(BGCOLOR)
    draw_text_center(screen, font, f"Round {round_result['round']} Complete", (WINDOWWIDTH//2, WINDOWHEIGHT//2 - 60))
    draw_text_center(screen, font, f"Correctness: {round_result['correctness_pct']}%", (WINDOWWIDTH//2, WINDOWHEIGHT//2 - 20))
    draw_text_center(screen, font, f"Moves: {round_result['moves']}  Time: {round_result['time_s']}s", (WINDOWWIDTH//2, WINDOWHEIGHT//2 + 20))
    draw_text_center(screen, font, f"Round Score: {round_result['game_score_0_100']}", (WINDOWWIDTH//2, WINDOWHEIGHT//2 + 60))
    pygame.display.update()
    pygame.time.wait(1000)

if __name__ == '__main__':
    main()
