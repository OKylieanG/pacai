"""
Renderer — Translates environment state into visual output.
Also handles keyboard input for manual play / testing.
"""

import pygame
import sys
from environment import Environment, Direction, CellType


# Colors
BLACK = (0, 0, 0)
DARK_BLUE = (0, 0, 40)
BLUE = (33, 33, 222)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
PELLET_COLOR = (255, 183, 174)
POWER_PELLET_COLOR = (255, 255, 255)
RED = (255, 0, 0)
PINK = (255, 184, 255)
CYAN = (0, 255, 255)
ORANGE = (255, 184, 82)
SCARED_BLUE = (33, 33, 255)
GREEN = (0, 255, 0)
DARK_RED = (100, 0, 0)

GHOST_COLORS = {
    'chaser': RED,
    'patroller': PINK,
    'wanderer': CYAN,
    'ambusher': ORANGE,
}

CELL_SIZE = 28
PANEL_WIDTH = 260


class Renderer:
    def __init__(self, env: Environment):
        self.env = env
        pygame.init()

        self.game_width = env.maze.width * CELL_SIZE
        self.game_height = env.maze.height * CELL_SIZE
        self.screen_width = self.game_width + PANEL_WIDTH
        self.screen_height = self.game_height

        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height)
        )
        pygame.display.set_caption("Pac-Man Consciousness Experiment")

        self.font = pygame.font.SysFont('monospace', 14)
        self.font_large = pygame.font.SysFont('monospace', 18, bold=True)
        self.clock = pygame.time.Clock()
        self.fps = 8  # Slow enough to watch

        # Pellet animation
        self.power_pellet_frame = 0

    def draw_maze(self):
        """Draw the grid and pellets."""
        for y in range(self.env.maze.height):
            for x in range(self.env.maze.width):
                cell = self.env.maze.grid[y][x]
                rect = pygame.Rect(
                    x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE
                )

                if cell == CellType.WALL:
                    pygame.draw.rect(self.screen, BLUE, rect)
                    # Inner shadow for depth
                    inner = rect.inflate(-4, -4)
                    pygame.draw.rect(self.screen, DARK_BLUE, inner)
                else:
                    if cell == CellType.PELLET:
                        cx = x * CELL_SIZE + CELL_SIZE // 2
                        cy = y * CELL_SIZE + CELL_SIZE // 2
                        pygame.draw.circle(
                            self.screen, PELLET_COLOR, (cx, cy), 2
                        )
                    elif cell == CellType.POWER_PELLET:
                        cx = x * CELL_SIZE + CELL_SIZE // 2
                        cy = y * CELL_SIZE + CELL_SIZE // 2
                        # Pulsing effect
                        radius = 5 + (self.power_pellet_frame % 4)
                        pygame.draw.circle(
                            self.screen, POWER_PELLET_COLOR, (cx, cy), radius
                        )

    def draw_pacman(self):
        """Draw the avatar. Appearance degrades with cognitive damage."""
        pm = self.env.pacman
        cx = pm.x * CELL_SIZE + CELL_SIZE // 2
        cy = pm.y * CELL_SIZE + CELL_SIZE // 2
        radius = CELL_SIZE // 2 - 2

        # Color shifts toward gray as health degrades
        health = pm.degradation.overall_health
        r = int(255 * health)
        g = int(255 * health)
        b = 0
        color = (max(80, r), max(80, g), b)

        # When in involuntary movement, flash red
        if pm.involuntary_timer > 0:
            if self.env.tick_count % 2 == 0:
                color = RED

        # Draw body
        pygame.draw.circle(self.screen, color, (cx, cy), radius)

        # Draw mouth based on direction
        mouth_angle_start = {
            Direction.RIGHT: 30,
            Direction.LEFT: 210,
            Direction.UP: 120,
            Direction.DOWN: 300,
            Direction.NONE: 30,
        }
        start = mouth_angle_start[pm.direction]
        # Animated mouth
        mouth_open = 45 if self.env.tick_count % 3 != 0 else 5
        import math
        points = [(cx, cy)]
        for angle in range(start + mouth_open, start + 360 - mouth_open, 5):
            rad = math.radians(angle)
            px = cx + int(radius * math.cos(rad))
            py = cy - int(radius * math.sin(rad))
            points.append((px, py))
        if len(points) > 2:
            pygame.draw.polygon(self.screen, color, points)

        # Powered up indicator
        if pm.powered_up:
            pygame.draw.circle(self.screen, WHITE, (cx, cy), radius + 3, 2)

    def draw_ghosts(self):
        """Draw ghosts with their behavioral colors."""
        for ghost in self.env.ghosts:
            cx = ghost.x * CELL_SIZE + CELL_SIZE // 2
            cy = ghost.y * CELL_SIZE + CELL_SIZE // 2
            radius = CELL_SIZE // 2 - 2

            if ghost.scared:
                color = SCARED_BLUE
                if ghost.scared_timer < 10 and self.env.tick_count % 2 == 0:
                    color = WHITE  # Flash when about to recover
            else:
                color = GHOST_COLORS.get(ghost.name, RED)

            # Ghost body — rounded top, wavy bottom
            body_rect = pygame.Rect(
                cx - radius, cy - radius,
                radius * 2, radius * 2
            )
            pygame.draw.circle(self.screen, color, (cx, cy - 2), radius)
            pygame.draw.rect(
                self.screen, color,
                (cx - radius, cy - 2, radius * 2, radius)
            )

            # Wavy bottom
            wave_y = cy + radius - 2
            for i in range(3):
                wx = cx - radius + i * (radius * 2 // 3) + radius // 3
                pygame.draw.circle(
                    self.screen, BLACK, (wx, wave_y), radius // 3
                )

            # Eyes
            eye_offset = 4
            eye_r = 3
            pupil_r = 1
            for side in [-1, 1]:
                ex = cx + side * eye_offset
                ey = cy - 3
                pygame.draw.circle(self.screen, WHITE, (ex, ey), eye_r)
                # Pupil looks toward pacman
                pdx = 1 if self.env.pacman.x > ghost.x else -1 if self.env.pacman.x < ghost.x else 0
                pdy = 1 if self.env.pacman.y > ghost.y else -1 if self.env.pacman.y < ghost.y else 0
                pygame.draw.circle(
                    self.screen, BLACK,
                    (ex + pdx, ey + pdy), pupil_r
                )

    def draw_status_panel(self):
        """Draw the sensor readout / health panel on the right side."""
        panel_x = self.game_width + 10
        y = 10

        # Title
        title = self.font_large.render("CONSCIOUSNESS", True, YELLOW)
        self.screen.blit(title, (panel_x, y))
        y += 30

        # Health bar
        deg = self.env.pacman.degradation
        health = deg.overall_health

        label = self.font.render("SYSTEM HEALTH", True, WHITE)
        self.screen.blit(label, (panel_x, y))
        y += 18

        bar_width = PANEL_WIDTH - 30
        bar_height = 14
        # Background
        pygame.draw.rect(self.screen, (40, 40, 40),
                         (panel_x, y, bar_width, bar_height))
        # Fill
        health_color = GREEN if health > 0.6 else YELLOW if health > 0.3 else RED
        pygame.draw.rect(self.screen, health_color,
                         (panel_x, y, int(bar_width * health), bar_height))
        pygame.draw.rect(self.screen, WHITE,
                         (panel_x, y, bar_width, bar_height), 1)
        y += 25

        # Individual systems
        systems = [
            ("Clarity", deg.clarity, GREEN),
            ("Sensor Noise", 1.0 - deg.sensor_noise, CYAN),
            ("Memory", 1.0 - deg.memory_loss, PINK),
            ("Motor Control", 1.0 - deg.motor_impairment, ORANGE),
        ]

        for name, value, color in systems:
            label = self.font.render(f"{name}", True, color)
            self.screen.blit(label, (panel_x, y))
            y += 16
            pygame.draw.rect(self.screen, (40, 40, 40),
                             (panel_x, y, bar_width, 8))
            pygame.draw.rect(self.screen, color,
                             (panel_x, y, int(bar_width * value), 8))
            y += 14

        y += 10

        # Control state
        if self.env.pacman.involuntary_timer > 0:
            ctrl_text = self.font.render("!! REFLEX OVERRIDE !!", True, RED)
            self.screen.blit(ctrl_text, (panel_x, y))
        elif self.env.pacman.powered_up:
            ctrl_text = self.font.render("POWERED UP", True, WHITE)
            self.screen.blit(ctrl_text, (panel_x, y))
        else:
            ctrl_text = self.font.render("In Control", True, GREEN)
            self.screen.blit(ctrl_text, (panel_x, y))
        y += 25

        # Stats
        stats = [
            f"Tick: {self.env.tick_count}",
            f"Pellets: {self.env.pellets_eaten}",
            f"Ghosts eaten: {self.env.ghosts_eaten}",
            f"Remaining: {self.env.maze.remaining_pellets()}",
        ]
        for stat in stats:
            text = self.font.render(stat, True, WHITE)
            self.screen.blit(text, (panel_x, y))
            y += 18

        y += 15

        # Pain log
        pain_label = self.font.render("PAIN LOG", True, RED)
        self.screen.blit(pain_label, (panel_x, y))
        y += 18

        if self.env.pain_events:
            for event in self.env.pain_events[-3:]:
                ptxt = self.font.render(
                    f"T{event['tick']}: {event['ghost']}",
                    True, (255, 100, 100)
                )
                self.screen.blit(ptxt, (panel_x, y))
                y += 16
        else:
            no_pain = self.font.render("-- none --", True, (80, 80, 80))
            self.screen.blit(no_pain, (panel_x, y))

        # Game over
        if self.game_over_state():
            y = self.screen_height // 2 - 20
            if not self.env.pacman.alive:
                go_text = self.font_large.render("SYSTEM FAILURE", True, RED)
            else:
                go_text = self.font_large.render("COMPLETE", True, GREEN)
            self.screen.blit(go_text, (panel_x, y))

    def draw_vision(self):
        """
        Draw the line-of-sight raycast as a translucent overlay.
        Shows what the agent can actually see ahead of it.
        """
        pm = self.env.pacman
        if pm.direction == Direction.NONE:
            return

        # Get the raycast data
        vision_data = self.env._raycast(pm.x, pm.y, pm.direction)

        # Create a transparent surface for the vision overlay
        overlay = pygame.Surface(
            (self.game_width, self.game_height), pygame.SRCALPHA
        )

        for entry in vision_data:
            vx, vy = entry['x'], entry['y']
            if not (0 <= vx < self.env.maze.width and
                    0 <= vy < self.env.maze.height):
                break

            rect = pygame.Rect(
                vx * CELL_SIZE + 2, vy * CELL_SIZE + 2,
                CELL_SIZE - 4, CELL_SIZE - 4
            )

            contents = entry['contents']

            if 'wall' in contents:
                # Vision terminates — dim highlight on the wall
                pygame.draw.rect(overlay, (100, 100, 255, 40), rect)
                break

            # Highlight visible cells
            has_threat = any(c.startswith('ghost:') and ':dangerous' in c
                            for c in contents)
            has_food = any(c in ('pellet', 'power_pellet') for c in contents)
            has_scared = any(c.startswith('ghost:') and ':scared' in c
                            for c in contents)

            if has_threat:
                color = (255, 0, 0, 60)  # Red tint for danger
            elif has_scared:
                color = (0, 100, 255, 60)  # Blue for vulnerable ghost
            elif has_food:
                color = (0, 255, 0, 40)  # Green tint for food
            else:
                color = (255, 255, 0, 25)  # Faint yellow for visible empty

            pygame.draw.rect(overlay, color, rect)

        self.screen.blit(overlay, (0, 0))

    def game_over_state(self) -> bool:
        return self.env.game_over

    def draw(self):
        """Render one frame."""
        self.screen.fill(BLACK)
        self.draw_maze()
        self.draw_vision()  # Vision overlay under entities
        self.draw_pacman()
        self.draw_ghosts()
        self.draw_status_panel()
        self.power_pellet_frame += 1
        pygame.display.flip()

    def get_input(self) -> Direction:
        """Get keyboard direction input."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            return Direction.UP
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            return Direction.DOWN
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            return Direction.LEFT
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            return Direction.RIGHT
        return Direction.NONE

    def handle_events(self) -> bool:
        """Process pygame events. Returns False if should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_r:
                    self.env.reset()
        return True

    def tick(self):
        """Wait for frame timing."""
        self.clock.tick(self.fps)


def main():
    """
    Manual play mode — lets you test the environment before
    wiring up the consciousness agent.
    """
    env = Environment()
    renderer = Renderer(env)

    print("=== PAC-MAN CONSCIOUSNESS ENVIRONMENT ===")
    print("Arrow keys / WASD to move")
    print("R to reset, ESC to quit")
    print("Watch the health panel — ghost contact degrades your systems.")
    print()

    running = True
    last_direction = Direction.NONE

    while running:
        running = renderer.handle_events()

        direction = renderer.get_input()
        if direction != Direction.NONE:
            last_direction = direction

        sensors = env.step(last_direction)

        renderer.draw()
        renderer.tick()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
