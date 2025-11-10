"""
Simple Tetris in Python with Pygame
Single-file implementation — no assets required.

Controls:
Left/Right arrows : move
Up arrow / X      : rotate clockwise
Z                 : rotate counter-clockwise
Down arrow        : soft drop
Space             : hard drop
C                 : hold (optional toggle in this version? not implemented)
Esc               : quit
"""

import pygame
import random
import sys

# ---------- Configuration ----------
CELL_SIZE = 30
COLUMNS = 10
ROWS = 20
PLAY_WIDTH = CELL_SIZE * COLUMNS
PLAY_HEIGHT = CELL_SIZE * ROWS
SIDE_PANEL = 200
WINDOW_WIDTH = PLAY_WIDTH + SIDE_PANEL
WINDOW_HEIGHT = PLAY_HEIGHT
FPS = 60

# Colors (R,G,B)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
WHITE = (255, 255, 255)
COLORS = [
    (0, 240, 240),   # I - cyan
    (0, 0, 240),     # J - blue
    (240, 160, 0),   # L - orange
    (240, 240, 0),   # O - yellow
    (0, 240, 0),     # S - green
    (160, 0, 240),   # T - purple
    (240, 0, 0),     # Z - red
]

# Tetromino shapes (4x4 matrices using lists of rotation states)
TETROMINOES = {
    'I': [
        ["0000",
         "1111",
         "0000",
         "0000"],
        ["0010",
         "0010",
         "0010",
         "0010"]
    ],
    'J': [
        ["100",
         "111",
         "000"],
        ["011",
         "010",
         "010"],
        ["000",
         "111",
         "001"],
        ["010",
         "010",
         "110"]
    ],
    'L': [
        ["001",
         "111",
         "000"],
        ["010",
         "010",
         "011"],
        ["000",
         "111",
         "100"],
        ["110",
         "010",
         "010"]
    ],
    'O': [
        ["11",
         "11"]
    ],
    'S': [
        ["011",
         "110",
         "000"],
        ["010",
         "011",
         "001"]
    ],
    'T': [
        ["010",
         "111",
         "000"],
        ["010",
         "011",
         "010"],
        ["000",
         "111",
         "010"],
        ["010",
         "110",
         "010"]
    ],
    'Z': [
        ["110",
         "011",
         "000"],
        ["001",
         "011",
         "010"]
    ]
}

PIECE_KEYS = list(TETROMINOES.keys())

# ---------- Helper functions ----------
def rotate(shape):
    """Return rotated version (90 deg clockwise) of a shape (list of strings)."""
    grid = [list(row) for row in shape]
    h = len(grid)
    w = len(grid[0])
    new = []
    for x in range(w):
        new_row = []
        for y in range(h - 1, -1, -1):
            new_row.append(grid[y][x])
        new.append("".join(new_row))
    return new

def shape_cells(shape, offset_x, offset_y):
    for y, row in enumerate(shape):
        for x, ch in enumerate(row):
            if ch == '1':
                yield offset_x + x, offset_y + y

def make_grid(locked_positions={}):
    grid = [[None for _ in range(COLUMNS)] for _ in range(ROWS)]
    for (x, y), color in locked_positions.items():
        if 0 <= y < ROWS and 0 <= x < COLUMNS:
            grid[y][x] = color
    return grid

def valid_space(shape, offset_x, offset_y, locked):
    for x, y in shape_cells(shape, offset_x, offset_y):
        if x < 0 or x >= COLUMNS or y >= ROWS:
            return False
        if y >= 0 and (x, y) in locked:
            return False
    return True

def clear_lines(grid, locked):
    lines_to_clear = []
    for y in range(ROWS):
        if all(grid[y][x] is not None for x in range(COLUMNS)):
            lines_to_clear.append(y)
    if not lines_to_clear:
        return 0
    for row in reversed(lines_to_clear):
        for x in range(COLUMNS):
            if (x, row) in locked:
                del locked[(x, row)]
    for y in sorted([r for r in range(ROWS) if r < max(lines_to_clear)], reverse=True):
        shift = sum(1 for cleared in lines_to_clear if y < cleared)
        if shift > 0:
            for x in range(COLUMNS):
                if (x, y) in locked:
                    locked[(x, y + shift)] = locked.pop((x, y))
    return len(lines_to_clear)

# ---------- Piece class ----------
class Piece:
    def __init__(self, type_key):
        self.type = type_key
        self.rotations = TETROMINOES[type_key]
        self.rotation = 0
        self.shape = self.rotations[self.rotation]
        self.x = COLUMNS // 2 - len(self.shape[0]) // 2
        self.y = -len(self.shape)
        self.color = COLORS[PIECE_KEYS.index(type_key)]
    def rotate(self, locked):
        old = self.rotation
        self.rotation = (self.rotation + 1) % len(self.rotations)
        self.shape = self.rotations[self.rotation]
        if not valid_space(self.shape, self.x, self.y, locked):
            for dx in (-1, 1, -2, 2):
                if valid_space(self.shape, self.x + dx, self.y, locked):
                    self.x += dx
                    return True
            self.rotation = old
            self.shape = self.rotations[self.rotation]
            return False
        return True
    def rotate_ccw(self, locked):
        old = self.rotation
        self.rotation = (self.rotation - 1) % len(self.rotations)
        self.shape = self.rotations[self.rotation]
        if not valid_space(self.shape, self.x, self.y, locked):
            for dx in (-1, 1, -2, 2):
                if valid_space(self.shape, self.x + dx, self.y, locked):
                    self.x += dx
                    return True
            self.rotation = old
            self.shape = self.rotations[self.rotation]
            return False
        return True

# ---------- Game class ----------
class Tetris:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tetris - Python")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 20)
        self.large_font = pygame.font.SysFont("monospace", 36, bold=True)
        self.reset()

    def reset(self):
        self.locked = {}
        self.grid = make_grid(self.locked)
        self.current = self.get_new_piece()
        self.next_piece = self.get_new_piece()
        self.fall_time = 0.0
        self.fall_speed = 0.6
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False

    def get_new_piece(self):
        key = random.choice(PIECE_KEYS)
        return Piece(key)

    def draw_grid(self):
        self.screen.fill(BLACK)
        pygame.draw.rect(self.screen, GRAY, (0, 0, PLAY_WIDTH, PLAY_HEIGHT), 4)
        for x in range(COLUMNS):
            for y in range(ROWS):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, (20, 20, 20), rect, 1)
        for (x, y), color in self.locked.items():
            if y >= 0:
                pygame.draw.rect(self.screen, color,
                                 (x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2))
        for x, y in shape_cells(self.current.shape, self.current.x, self.current.y):
            if y >= 0:
                pygame.draw.rect(self.screen, self.current.color,
                                (x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2))
        nx = PLAY_WIDTH + 20
        ny = 20
        label = self.font.render("Next:", True, WHITE)
        self.screen.blit(label, (nx, ny))
        for x, y in shape_cells(self.next_piece.shape, 0, 0):
            px = nx + (x) * CELL_SIZE
            py = ny + 30 + (y) * CELL_SIZE
            pygame.draw.rect(self.screen, self.next_piece.color,
                             (px + 1, py + 1, CELL_SIZE - 2, CELL_SIZE - 2))
        score_label = self.font.render(f"Score: {self.score}", True, WHITE)
        lines_label = self.font.render(f"Lines: {self.lines}", True, WHITE)
        level_label = self.font.render(f"Level: {self.level}", True, WHITE)
        self.screen.blit(score_label, (nx, 200))
        self.screen.blit(lines_label, (nx, 230))
        self.screen.blit(level_label, (nx, 260))

    def lock_piece(self):
        for x, y in shape_cells(self.current.shape, self.current.x, self.current.y):
            if y < 0:
                self.game_over = True
            else:
                self.locked[(x, y)] = self.current.color
        self.grid = make_grid(self.locked)
        cleared = clear_lines(self.grid, self.locked)
        if cleared:
            score_table = {1: 40, 2: 100, 3: 300, 4: 1200}
            self.score += score_table.get(cleared, 0) * self.level
            self.lines += cleared
            self.level = self.lines // 10 + 1
            self.fall_speed = max(0.05, 0.6 - (self.level - 1) * 0.05)
        self.current = self.next_piece
        self.next_piece = self.get_new_piece()

    def hard_drop(self):
        while valid_space(self.current.shape, self.current.x, self.current.y + 1, self.locked):
            self.current.y += 1
        self.lock_piece()

    def run(self):
        pygame.time.set_timer(pygame.USEREVENT + 1, int(self.fall_speed * 1000))
        last_time = pygame.time.get_ticks()
        while True:
            if self.game_over:
                self.show_game_over()
                return
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_LEFT:
                        if valid_space(self.current.shape, self.current.x - 1, self.current.y, self.locked):
                            self.current.x -= 1
                    if event.key == pygame.K_RIGHT:
                        if valid_space(self.current.shape, self.current.x + 1, self.current.y, self.locked):
                            self.current.x += 1
                    if event.key in (pygame.K_UP, pygame.K_x):
                        self.current.rotate(self.locked)
                    if event.key == pygame.K_z:
                        self.current.rotate_ccw(self.locked)
                    if event.key == pygame.K_DOWN:
                        if valid_space(self.current.shape, self.current.x, self.current.y + 1, self.locked):
                            self.current.y += 1
                    if event.key == pygame.K_SPACE:
                        self.hard_drop()

            current_time = pygame.time.get_ticks()
            if current_time - last_time > int(self.fall_speed * 1000):
                last_time = current_time
                if valid_space(self.current.shape, self.current.x, self.current.y + 1, self.locked):
                    self.current.y += 1
                else:
                    self.lock_piece()
                    if self.game_over:
                        self.show_game_over()
                        return

            self.draw_grid()
            pygame.display.update()

    def show_game_over(self):
        self.screen.fill(BLACK)
        over = self.large_font.render("GAME OVER", True, WHITE)
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        inst = self.font.render("Press R to restart or Esc to quit", True, WHITE)
        self.screen.blit(over, (PLAY_WIDTH // 2 - over.get_width() // 2, PLAY_HEIGHT // 2 - 60))
        self.screen.blit(score_text, (PLAY_WIDTH // 2 - score_text.get_width() // 2, PLAY_HEIGHT // 2 - 10))
        self.screen.blit(inst, (PLAY_WIDTH // 2 - inst.get_width() // 2, PLAY_HEIGHT // 2 + 30))
        pygame.display.update()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_r:
                        self.reset()
                        self.run()
                        return

# ---------- Run the game ----------
if __name__ == "__main__":
    game = Tetris()
    game.run()