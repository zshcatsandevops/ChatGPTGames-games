
import pygame
import numpy as np
import sys

# Famicom vibes: low-res, chiptune soul
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
FPS = 60
PADDLE_WIDTH = 60
PADDLE_HEIGHT = 10
BALL_SIZE = 6
BRICK_WIDTH = 32
BRICK_HEIGHT = 12
BRICK_ROWS = 5
BRICK_COLS = 10
BRICK_GAP = 2

# Colors: Famicom palette punch (RGB approximations)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (248, 56, 0)
GREEN = (0, 232, 216)
BLUE = (120, 120, 248)
YELLOW = (248, 248, 56)
ORANGE = (248, 120, 88)
PINK = (248, 88, 136)
CYAN = (88, 216, 248)
PURPLE = (168, 104, 232)

BRICK_COLORS = [RED, ORANGE, YELLOW, GREEN, BLUE]


# --- Sound helpers -----------------------------------------------------------
def generate_beep(freq, duration, sample_rate=44100, volume=0.25):
    """
    Create a simple sine-wave beep (stereo) as a pygame Sound.
    Adds a short attack/release envelope to avoid clicks/"static".
    """
    n = int(sample_rate * duration)
    t = np.arange(n) / sample_rate
    wave = np.sin(2 * np.pi * freq * t)

    # Attack/Release envelope (5ms attack, 15ms release)
    attack = max(1, int(0.005 * sample_rate))
    release = max(1, int(0.015 * sample_rate))
    env = np.ones_like(wave)
    env[:attack] = np.linspace(0, 1, attack, endpoint=False)
    env[-release:] = np.linspace(1, 0, release, endpoint=True)

    wave = wave * env * volume
    stereo = np.column_stack((wave, wave))
    audio = np.clip(stereo * 32767, -32768, 32767).astype(np.int16)
    return pygame.sndarray.make_sound(audio)


class Sfx:
    """Holds sound effects. If mixer init fails, stays muted."""
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.bounce = None
        self.brick = None
        self.launch = None
        self.lose = None
        if enabled:
            try:
                self.bounce = generate_beep(440, 0.05)
                self.brick = generate_beep(660, 0.10)
                self.launch = generate_beep(880, 0.12)
                self.lose = generate_beep(220, 0.25)
            except pygame.error:
                self.enabled = False

    def toggle(self):
        self.enabled = not self.enabled

    def play(self, sound):
        if not self.enabled or sound is None:
            return
        sound.play()


sfx = None  # set in main()


class Paddle:
    def __init__(self):
        self.rect = pygame.Rect(
            SCREEN_WIDTH // 2 - PADDLE_WIDTH // 2,
            SCREEN_HEIGHT - 30,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        )
        self.speed = 8  # unused with mouse but kept for arrow fallback

    def update_mouse(self):
        mx, _ = pygame.mouse.get_pos()
        # If using SCALED, pygame returns scaled coords; clamp anyway.
        self.rect.centerx = int(mx)
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, self.rect)


class Ball:
    def __init__(self):
        self.size = BALL_SIZE
        self.x = SCREEN_WIDTH / 2
        self.y = SCREEN_HEIGHT / 2
        self.dx = 4.0
        self.dy = -4.0
        self.launched = False
        self.rect = pygame.Rect(int(self.x - self.size / 2), int(self.y - self.size / 2), self.size, self.size)

    def stick_to_paddle(self, paddle):
        self.x = paddle.rect.centerx
        self.y = paddle.rect.top - self.size // 2 - 1
        self.rect.center = (int(self.x), int(self.y))

    def update(self, paddle, bricks):
        if not self.launched:
            self.stick_to_paddle(paddle)
            return False

        # Move
        self.x += self.dx
        self.y += self.dy
        self.rect.center = (int(self.x), int(self.y))

        # Walls
        if self.rect.left <= 0:
            self.rect.left = 0
            self.x = self.rect.centerx
            self.dx = -self.dx
            sfx.play(sfx.bounce)
        elif self.rect.right >= SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.x = self.rect.centerx
            self.dx = -self.dx
            sfx.play(sfx.bounce)
        if self.rect.top <= 0:
            self.rect.top = 0
            self.y = self.rect.centery
            self.dy = -self.dy
            sfx.play(sfx.bounce)

        # Paddle
        if self.rect.colliderect(paddle.rect) and self.dy > 0:
            self.rect.bottom = paddle.rect.top - 1
            self.y = self.rect.centery
            self.dy = -abs(self.dy)
            # Mix in angle based on hit position
            hit_pos = (self.rect.centerx - paddle.rect.centerx) / (PADDLE_WIDTH / 2)
            self.dx = hit_pos * 5.0
            sfx.play(sfx.bounce)

        # Bricks (flip the axis of greater penetration)
        hit_index = self.rect.collidelist([b.rect for b in bricks])
        if hit_index != -1:
            brick = bricks.pop(hit_index)
            dx_overlap = (brick.rect.width / 2) - abs(self.rect.centerx - brick.rect.centerx)
            dy_overlap = (brick.rect.height / 2) - abs(self.rect.centery - brick.rect.centery)
            if dx_overlap < dy_overlap:
                self.dx = -self.dx
            else:
                self.dy = -self.dy
            sfx.play(sfx.brick)

        # Fall below
        if self.rect.top >= SCREEN_HEIGHT:
            sfx.play(sfx.lose)
            self.reset()
            return False

        return len(bricks) == 0

    def launch(self):
        if not self.launched:
            self.launched = True
            if self.dy == 0:
                self.dy = -4.0
            sfx.play(sfx.launch)

    def reset(self):
        self.x = SCREEN_WIDTH / 2
        self.y = SCREEN_HEIGHT / 2
        self.dx = 4.0
        self.dy = 0.0
        self.launched = False
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, screen):
        pygame.draw.ellipse(screen, WHITE, self.rect)


class Brick:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, BRICK_WIDTH, BRICK_HEIGHT)
        self.color = color

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 1)


def build_bricks(cols, rows):
    bricks = []
    cols = max(1, cols)
    grid_w = cols * BRICK_WIDTH + (cols - 1) * BRICK_GAP
    left = max(0, (SCREEN_WIDTH - grid_w) // 2)
    top = 50
    for row in range(rows):
        color = BRICK_COLORS[row % len(BRICK_COLORS)]
        for col in range(cols):
            x = left + col * (BRICK_WIDTH + BRICK_GAP)
            y = top + row * (BRICK_HEIGHT + BRICK_GAP)
            bricks.append(Brick(x, y, color))
    return bricks


def main():
    # Initialize audio first for clean sndarray behavior
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.init()

    # Pixel-perfect scaling window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Breakout: Famicom Fury — Mouse Edition")
    clock = pygame.time.Clock()

    # Try to init audio; if it fails, we stay muted
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        enable_audio = True
    except pygame.error:
        enable_audio = False

    global sfx
    sfx = Sfx(enabled=enable_audio)

    font = pygame.font.Font(None, 18)

    paddle = Paddle()
    ball = Ball()

    # Fit columns to width, center the wall
    max_cols = max(1, (SCREEN_WIDTH + BRICK_GAP) // (BRICK_WIDTH + BRICK_GAP))
    cols = min(BRICK_COLS, max_cols)
    bricks = build_bricks(cols, BRICK_ROWS)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    ball.launch()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    sfx.toggle()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click
                    ball.launch()

        # Mouse controls the paddle
        paddle.update_mouse()

        # Update ball + collisions
        win = ball.update(paddle, bricks)

        if win:
            bricks = build_bricks(cols, BRICK_ROWS)
            ball.reset()

        # Draw
        screen.fill(BLACK)
        paddle.draw(screen)
        ball.draw(screen)
        for brick in bricks:
            brick.draw(screen)

        # HUD
        hud = "Mouse to move • Click/SPACE to launch • M: mute • ESC: quit"
        text = font.render(hud, True, WHITE)
        screen.blit(text, (6, 6))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
