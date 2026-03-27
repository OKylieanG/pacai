"""
Pac-Man Consciousness Environment

A minimal Pac-Man world designed as a substrate for consciousness experiments.
The environment produces signals for an agent's sensors and applies structural
consequences (not just scores) for interactions.
"""

import random
import math
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    NONE = auto()

    def to_delta(self):
        return {
            Direction.UP: (0, -1),
            Direction.DOWN: (0, 1),
            Direction.LEFT: (-1, 0),
            Direction.RIGHT: (1, 0),
            Direction.NONE: (0, 0),
        }[self]

    def opposite(self):
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
            Direction.NONE: Direction.NONE,
        }[self]

    def turn_left(self):
        return {
            Direction.UP: Direction.LEFT,
            Direction.LEFT: Direction.DOWN,
            Direction.DOWN: Direction.RIGHT,
            Direction.RIGHT: Direction.UP,
            Direction.NONE: Direction.NONE,
        }[self]

    def turn_right(self):
        return {
            Direction.UP: Direction.RIGHT,
            Direction.RIGHT: Direction.DOWN,
            Direction.DOWN: Direction.LEFT,
            Direction.LEFT: Direction.UP,
            Direction.NONE: Direction.NONE,
        }[self]


class Action(Enum):
    """
    The agent's action space. It can only move forward or turn.
    No backward movement — that only happens involuntarily via pain reflex.
    """
    FORWARD = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()
    NONE = auto()


class CellType(Enum):
    EMPTY = 0
    WALL = 1
    PELLET = 2
    POWER_PELLET = 3


@dataclass
class DegradationState:
    """
    Tracks the structural damage to the agent's cognitive systems.
    This isn't a score — it represents real impairment.
    """
    sensor_noise: float = 0.0       # 0.0 = clear, 1.0 = total noise
    memory_loss: float = 0.0        # 0.0 = full memory, 1.0 = no memory
    motor_impairment: float = 0.0   # 0.0 = full control, 1.0 = no control
    clarity: float = 1.0            # 1.0 = full clarity, 0.0 = none

    def apply_damage(self, amount: float = 0.15):
        """Ghost contact: degrade all systems."""
        self.sensor_noise = min(1.0, self.sensor_noise + amount)
        self.memory_loss = min(1.0, self.memory_loss + amount)
        self.motor_impairment = min(1.0, self.motor_impairment + amount * 0.5)
        self.clarity = max(0.0, self.clarity - amount)

    def apply_healing(self, amount: float = 0.05):
        """Pellet consumption: restore systems."""
        self.sensor_noise = max(0.0, self.sensor_noise - amount)
        self.memory_loss = max(0.0, self.memory_loss - amount)
        self.motor_impairment = max(0.0, self.motor_impairment - amount * 0.5)
        self.clarity = min(1.0, self.clarity + amount)

    def is_dead(self) -> bool:
        """Agent ceases to function when clarity reaches zero."""
        return self.clarity <= 0.0

    @property
    def overall_health(self) -> float:
        """0.0 = non-functional, 1.0 = perfect health."""
        return self.clarity * (1.0 - self.sensor_noise * 0.33
                                    - self.memory_loss * 0.33
                                    - self.motor_impairment * 0.33)


@dataclass
class Entity:
    x: int
    y: int
    direction: Direction = Direction.NONE


@dataclass
class Ghost(Entity):
    """Each ghost has a behavioral tendency."""
    name: str = "ghost"
    behavior: str = "chase"  # chase, patrol, random, ambush
    scared: bool = False
    scared_timer: int = 0


@dataclass
class FearState:
    """
    Fear is not pre-programmed. It emerges from having been hurt.

    Before first pain: the agent is naive. Ghosts are just objects.
    After first pain: the agent develops an aversion to moving toward
    known threats. This manifests as motor resistance — it becomes
    physically harder to move forward when a threat is visible ahead.

    Fear resistance scales with proximity:
    - At max vision range: 25% resistance (75% effective power)
    - At distance 1: ~90% resistance (nearly frozen)
    - This is not a decision. It's a force acting on the body.
    """
    has_been_hurt: bool = False          # Naive until first pain
    pain_count: int = 0                  # Cumulative pain experiences
    last_pain_tick: int = -1             # When was the last pain
    fear_intensity: float = 0.0          # 0.0 = no fear, 1.0 = maximum
    # Fear intensity builds with pain and decays slowly over time

    def register_pain(self, tick: int):
        """Pain happened. Fear intensifies."""
        self.has_been_hurt = True
        self.pain_count += 1
        self.last_pain_tick = tick
        # Each pain experience increases base fear, diminishing returns
        self.fear_intensity = min(1.0, self.fear_intensity + 0.3)

    def decay(self, tick: int):
        """Fear decays very slowly over time without pain."""
        if self.last_pain_tick >= 0:
            ticks_since_pain = tick - self.last_pain_tick
            # Slow decay — fear lingers
            decay_amount = 0.001 * ticks_since_pain * 0.01
            self.fear_intensity = max(0.0, self.fear_intensity - decay_amount)

    def get_resistance(self, distance_to_threat: int,
                       max_vision: int = 15) -> float:
        """
        Calculate motor resistance when moving toward a visible threat.
        Returns 0.0 (no resistance) to 1.0 (immovable).

        Only applies if the agent has been hurt before.
        """
        if not self.has_been_hurt or distance_to_threat <= 0:
            return 0.0

        # Normalize distance: 1.0 at max range, 0.0 at distance 1
        distance_factor = max(0.0, (distance_to_threat - 1)) / max(1, max_vision - 1)

        # Base resistance: 0.25 at max range, 0.90 at distance 1
        base_resistance = 0.90 - (0.65 * distance_factor)

        # Scale by fear intensity (which builds with pain experiences)
        return base_resistance * self.fear_intensity


@dataclass
class PacMan(Entity):
    """
    The avatar — localization point for consciousness.

    Movement model: forward and turn only.
    - FORWARD: move one cell in facing direction
    - TURN_LEFT / TURN_RIGHT: rotate 90 degrees, no movement
    - Backward movement only occurs involuntarily via pain reflex
    """
    degradation: DegradationState = field(default_factory=DegradationState)
    fear: FearState = field(default_factory=FearState)
    involuntary_move: Optional[Direction] = None  # Pain reflex
    involuntary_timer: int = 0  # Ticks of lost control
    powered_up: bool = False
    power_timer: int = 0
    alive: bool = True


class Maze:
    """
    The physical world. A grid of cells with walls, pellets, and open space.
    """
    def __init__(self, width: int = 19, height: int = 21):
        self.width = width
        self.height = height
        self.grid = self._generate_maze()
        self.total_pellets = sum(
            1 for row in self.grid for cell in row
            if cell in (CellType.PELLET, CellType.POWER_PELLET)
        )

    def _generate_maze(self) -> list[list[CellType]]:
        """
        Generate a simple symmetric Pac-Man-style maze.
        Walls on borders, internal structure, pellets on open cells.
        """
        grid = [[CellType.EMPTY for _ in range(self.width)]
                for _ in range(self.height)]

        # Border walls
        for x in range(self.width):
            grid[0][x] = CellType.WALL
            grid[self.height - 1][x] = CellType.WALL
        for y in range(self.height):
            grid[y][0] = CellType.WALL
            grid[y][self.width - 1] = CellType.WALL

        # Internal wall blocks — symmetric, simple layout
        wall_blocks = [
            # Upper region
            (2, 2, 3, 2), (6, 2, 3, 2), (14, 2, 3, 2),
            (10, 2, 3, 2),
            # Middle region
            (2, 5, 3, 1), (6, 5, 7, 1),
            (14, 5, 3, 1),
            (2, 7, 3, 3), (7, 7, 5, 3), (14, 7, 3, 3),
            # Lower region
            (2, 11, 3, 1), (6, 11, 7, 1), (14, 11, 3, 1),
            (4, 13, 2, 2), (8, 13, 3, 1), (13, 13, 2, 2),
            (2, 15, 3, 2), (6, 15, 3, 2), (10, 15, 3, 2),
            (14, 15, 3, 2),
            (4, 18, 5, 1), (10, 18, 5, 1),
        ]

        for (bx, by, bw, bh) in wall_blocks:
            for dy in range(bh):
                for dx in range(bw):
                    nx, ny = bx + dx, by + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        grid[ny][nx] = CellType.WALL

        # Place pellets on all empty cells
        for y in range(self.height):
            for x in range(self.width):
                if grid[y][x] == CellType.EMPTY:
                    grid[y][x] = CellType.PELLET

        # Power pellets in corners
        corners = [(1, 1), (self.width - 2, 1),
                   (1, self.height - 2), (self.width - 2, self.height - 2)]
        for cx, cy in corners:
            if grid[cy][cx] == CellType.PELLET:
                grid[cy][cx] = CellType.POWER_PELLET

        return grid

    def is_walkable(self, x: int, y: int) -> bool:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x] != CellType.WALL
        return False

    def consume_pellet(self, x: int, y: int) -> Optional[CellType]:
        """Remove and return pellet at position, if any."""
        cell = self.grid[y][x]
        if cell in (CellType.PELLET, CellType.POWER_PELLET):
            self.grid[y][x] = CellType.EMPTY
            return cell
        return None

    def remaining_pellets(self) -> int:
        return sum(
            1 for row in self.grid for cell in row
            if cell in (CellType.PELLET, CellType.POWER_PELLET)
        )


class Environment:
    """
    The complete world simulation. Manages all entities, physics,
    and produces sensor data for the consciousness layer.
    """

    GHOST_SPAWN = (9, 8)  # Center of the ghost house
    PACMAN_SPAWN = (9, 15)
    POWER_UP_DURATION = 30  # ticks

    def __init__(self):
        self.maze = Maze()
        self.pacman = PacMan(x=self.PACMAN_SPAWN[0], y=self.PACMAN_SPAWN[1])
        self.ghosts = self._create_ghosts()
        self.tick_count = 0
        self.pellets_eaten = 0
        self.ghosts_eaten = 0
        self.game_over = False
        self.pain_events = []  # Log of recent pain for sensor readout

    def _create_ghosts(self) -> list[Ghost]:
        sx, sy = self.GHOST_SPAWN
        return [
            Ghost(x=sx, y=sy - 1, name="chaser", behavior="chase"),
            Ghost(x=sx - 1, y=sy, name="patroller", behavior="patrol"),
            Ghost(x=sx + 1, y=sy, name="wanderer", behavior="random"),
            Ghost(x=sx, y=sy + 1, name="ambusher", behavior="ambush"),
        ]

    def get_valid_moves(self, x: int, y: int) -> list[Direction]:
        """Return list of directions that lead to walkable cells."""
        moves = []
        for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            dx, dy = d.to_delta()
            if self.maze.is_walkable(x + dx, y + dy):
                moves.append(d)
        return moves

    def _move_entity(self, entity: Entity, direction: Direction) -> bool:
        """Attempt to move entity in direction. Returns True if moved."""
        dx, dy = direction.to_delta()
        nx, ny = entity.x + dx, entity.y + dy
        if self.maze.is_walkable(nx, ny):
            entity.x = nx
            entity.y = ny
            entity.direction = direction
            return True
        return False

    def _apply_pain_reflex(self, ghost: Ghost):
        """
        Ghost contact: push the avatar BACKWARD (opposite of facing),
        seize motor control, and degrade cognitive systems.

        This is the reflex arc. The agent gets repelled as if it
        walked backward — something it can never do voluntarily.
        The backward push is involuntary proof that something
        has violated the agent's bodily boundary.
        """
        # Push direction is OPPOSITE of facing — recoil from what's ahead
        if self.pacman.direction == Direction.NONE:
            # Not facing anywhere — push away from ghost
            dx = self.pacman.x - ghost.x
            dy = self.pacman.y - ghost.y
            if abs(dx) >= abs(dy):
                push_dir = Direction.RIGHT if dx >= 0 else Direction.LEFT
            else:
                push_dir = Direction.DOWN if dy >= 0 else Direction.UP
        else:
            push_dir = self.pacman.direction.opposite()

        # Try to push backward; if blocked, try perpendicular
        push_options = [push_dir]
        perp_left = push_dir.turn_left()
        perp_right = push_dir.turn_right()
        push_options.extend([perp_left, perp_right])

        pushed = False
        original_facing = self.pacman.direction  # Remember where we were looking
        for d in push_options:
            pdx, pdy = d.to_delta()
            if self.maze.is_walkable(self.pacman.x + pdx, self.pacman.y + pdy):
                self.pacman.involuntary_move = d
                self.pacman.involuntary_timer = 3  # Ticks of lost control
                self._move_entity(self.pacman, d)
                # Restore facing — the agent is still looking where it was.
                # The body was thrown backward but the eyes stay fixed
                # on the source of pain.
                self.pacman.direction = original_facing
                pushed = True
                break

        # Apply structural damage
        self.pacman.degradation.apply_damage(0.15)

        # Register pain in fear system
        self.pacman.fear.register_pain(self.tick_count)

        # Log the pain event for sensor readout
        self.pain_events.append({
            'tick': self.tick_count,
            'ghost': ghost.name,
            'severity': 0.15,
            'pushed': pushed,
            'push_direction': push_dir.name if pushed else None,
        })

        # Check for death
        if self.pacman.degradation.is_dead():
            self.pacman.alive = False
            self.game_over = True

    def _move_ghost(self, ghost: Ghost):
        """Move ghost according to its behavioral pattern."""
        valid_moves = self.get_valid_moves(ghost.x, ghost.y)
        if not valid_moves:
            return

        # Don't reverse unless no choice
        if len(valid_moves) > 1 and ghost.direction != Direction.NONE:
            opposite = ghost.direction.opposite()
            valid_moves = [m for m in valid_moves if m != opposite] or valid_moves

        if ghost.scared:
            # Run away from pacman
            best_dir = max(valid_moves, key=lambda d: (
                abs(self.pacman.x - (ghost.x + d.to_delta()[0])) +
                abs(self.pacman.y - (ghost.y + d.to_delta()[1]))
            ))
            self._move_entity(ghost, best_dir)

        elif ghost.behavior == "chase":
            # Move toward pacman
            best_dir = min(valid_moves, key=lambda d: (
                abs(self.pacman.x - (ghost.x + d.to_delta()[0])) +
                abs(self.pacman.y - (ghost.y + d.to_delta()[1]))
            ))
            self._move_entity(ghost, best_dir)

        elif ghost.behavior == "patrol":
            # Prefer to continue in current direction
            if ghost.direction in valid_moves:
                self._move_entity(ghost, ghost.direction)
            else:
                self._move_entity(ghost, random.choice(valid_moves))

        elif ghost.behavior == "ambush":
            # Try to get ahead of pacman's direction
            pdx, pdy = self.pacman.direction.to_delta()
            target_x = self.pacman.x + pdx * 4
            target_y = self.pacman.y + pdy * 4
            best_dir = min(valid_moves, key=lambda d: (
                abs(target_x - (ghost.x + d.to_delta()[0])) +
                abs(target_y - (ghost.y + d.to_delta()[1]))
            ))
            self._move_entity(ghost, best_dir)

        else:  # random
            self._move_entity(ghost, random.choice(valid_moves))

    def _check_collisions(self):
        """Check and resolve pacman-ghost collisions."""
        for ghost in self.ghosts:
            if ghost.x == self.pacman.x and ghost.y == self.pacman.y:
                if self.pacman.powered_up and ghost.scared:
                    # Eat the ghost
                    ghost.x, ghost.y = self.GHOST_SPAWN
                    ghost.scared = False
                    ghost.scared_timer = 0
                    self.ghosts_eaten += 1
                    self.pacman.degradation.apply_healing(0.10)
                else:
                    # Pain reflex
                    self._apply_pain_reflex(ghost)

    def _check_pellet(self):
        """Check if pacman is on a pellet."""
        consumed = self.maze.consume_pellet(self.pacman.x, self.pacman.y)
        if consumed == CellType.PELLET:
            self.pellets_eaten += 1
            self.pacman.degradation.apply_healing(0.03)
        elif consumed == CellType.POWER_PELLET:
            self.pellets_eaten += 1
            self.pacman.powered_up = True
            self.pacman.power_timer = self.POWER_UP_DURATION
            self.pacman.degradation.apply_healing(0.10)
            for ghost in self.ghosts:
                ghost.scared = True
                ghost.scared_timer = self.POWER_UP_DURATION

    def _get_threat_ahead_distance(self) -> Optional[int]:
        """
        Check if there's a visible threat in the forward direction.
        Returns distance to nearest threat, or None if no threat visible.
        """
        if self.pacman.direction == Direction.NONE:
            return None

        vision = self._raycast(
            self.pacman.x, self.pacman.y, self.pacman.direction
        )
        for entry in vision:
            for c in entry['contents']:
                if c.startswith('ghost:') and ':dangerous' in c:
                    return entry['distance']
            if 'wall' in entry['contents'] or 'boundary' in entry['contents']:
                break
        return None

    def step(self, action: Action) -> dict:
        """
        Advance the world by one tick.

        Action space:
        - FORWARD: move one cell in facing direction
        - TURN_LEFT: rotate 90° counterclockwise
        - TURN_RIGHT: rotate 90° clockwise
        - NONE: do nothing

        Fear mechanics:
        - If agent has been hurt and a threat is visible ahead,
          FORWARD may fail due to fear resistance.
        - Resistance increases as the threat gets closer.
        - This is involuntary — the body resists, not the mind.

        Returns the sensor data for the consciousness layer.
        """
        if self.game_over:
            return self.get_sensor_data()

        self.tick_count += 1
        self.pain_events = []

        # Decay fear slightly each tick
        self.pacman.fear.decay(self.tick_count)

        # --- Motor control ---
        # If pain reflex is active, agent loses control
        if self.pacman.involuntary_timer > 0:
            self.pacman.involuntary_timer -= 1
            # Agent's intended action is overridden — body is recoiling
            if self.pacman.involuntary_move:
                # Continue recoiling in push direction
                original_facing = self.pacman.direction
                self._move_entity(self.pacman, self.pacman.involuntary_move)
                # Maintain original facing — agent is still looking
                # at where the pain came from
                self.pacman.direction = original_facing
        else:
            self.pacman.involuntary_move = None

            # Process agent action
            if action == Action.TURN_LEFT:
                self.pacman.direction = self.pacman.direction.turn_left()

            elif action == Action.TURN_RIGHT:
                self.pacman.direction = self.pacman.direction.turn_right()

            elif action == Action.FORWARD:
                moved = False

                # Check fear resistance before moving forward
                threat_dist = self._get_threat_ahead_distance()
                fear_blocked = False

                if threat_dist is not None:
                    resistance = self.pacman.fear.get_resistance(threat_dist)
                    if resistance > 0 and random.random() < resistance:
                        # Fear wins — body refuses to move forward
                        fear_blocked = True

                # Apply motor impairment on top of fear
                if not fear_blocked:
                    if (self.pacman.degradation.motor_impairment > 0 and
                            random.random() < self.pacman.degradation.motor_impairment * 0.5):
                        # Motor damage — move in random valid direction
                        valid = self.get_valid_moves(self.pacman.x, self.pacman.y)
                        if valid:
                            self._move_entity(self.pacman, random.choice(valid))
                            moved = True
                    else:
                        moved = self._move_entity(
                            self.pacman, self.pacman.direction
                        )

            # NONE: do nothing, just stand

        # Check pellet at current position
        self._check_pellet()

        # Move ghosts (every other tick to make them slightly slower)
        if self.tick_count % 2 == 0:
            for ghost in self.ghosts:
                self._move_ghost(ghost)
                # Update scared timers
                if ghost.scared:
                    ghost.scared_timer -= 1
                    if ghost.scared_timer <= 0:
                        ghost.scared = False

        # Update power-up timer
        if self.pacman.powered_up:
            self.pacman.power_timer -= 1
            if self.pacman.power_timer <= 0:
                self.pacman.powered_up = False

        # Check collisions
        self._check_collisions()

        # Natural healing — very slow
        self.pacman.degradation.apply_healing(0.002)

        # Win condition
        if self.maze.remaining_pellets() == 0:
            self.game_over = True

        return self.get_sensor_data()

    def _raycast(self, start_x: int, start_y: int, direction: Direction,
                 max_dist: int = 20) -> list[dict]:
        """
        Cast a ray from a position in a direction until hitting a wall.
        Returns a list of what's visible along the line, in order of distance.
        Each entry: {distance, x, y, contents: [what's here]}
        """
        if direction == Direction.NONE:
            return []

        dx, dy = direction.to_delta()
        results = []
        cx, cy = start_x, start_y

        for dist in range(1, max_dist + 1):
            cx += dx
            cy += dy

            # Hit the edge of the world
            if not (0 <= cx < self.maze.width and 0 <= cy < self.maze.height):
                results.append({
                    'distance': dist, 'x': cx, 'y': cy,
                    'contents': ['boundary'],
                })
                break

            # Hit a wall — visible but blocks further sight
            if self.maze.grid[cy][cx] == CellType.WALL:
                results.append({
                    'distance': dist, 'x': cx, 'y': cy,
                    'contents': ['wall'],
                })
                break

            # Open cell — record what's here
            contents = []
            cell = self.maze.grid[cy][cx]
            if cell == CellType.PELLET:
                contents.append('pellet')
            elif cell == CellType.POWER_PELLET:
                contents.append('power_pellet')
            else:
                contents.append('empty')

            # Check for ghosts at this position
            for ghost in self.ghosts:
                if ghost.x == cx and ghost.y == cy:
                    contents.append(f"ghost:{ghost.name}:"
                                    f"{'scared' if ghost.scared else 'dangerous'}")

            results.append({
                'distance': dist, 'x': cx, 'y': cy,
                'contents': contents,
            })

        return results

    def _get_adjacent(self, x: int, y: int) -> dict:
        """
        Get what's immediately adjacent in each direction.
        This is touch/proximity — the agent feels what's next to it
        without needing to see it.
        """
        adjacent = {}
        for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            dx, dy = d.to_delta()
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.maze.width and 0 <= ny < self.maze.height):
                adjacent[d.name] = {'type': 'boundary', 'walkable': False,
                                    'ghost': None}
                continue

            cell = self.maze.grid[ny][nx]
            walkable = cell != CellType.WALL

            cell_type = 'wall'
            if cell == CellType.EMPTY:
                cell_type = 'empty'
            elif cell == CellType.PELLET:
                cell_type = 'pellet'
            elif cell == CellType.POWER_PELLET:
                cell_type = 'power_pellet'

            # Feel if a ghost is right next to us
            ghost_info = None
            for ghost in self.ghosts:
                if ghost.x == nx and ghost.y == ny:
                    ghost_info = {
                        'name': ghost.name,
                        'scared': ghost.scared,
                    }
                    break

            adjacent[d.name] = {
                'type': cell_type,
                'walkable': walkable,
                'ghost': ghost_info,
            }
        return adjacent

    def get_sensor_data(self) -> dict:
        """
        Translate the world state into sensor channels.
        This is the interface between environment and consciousness.

        Sensory model:
        - VISION: raycast forward from facing direction, blocked by walls
        - TOUCH: immediate adjacency (1 cell in each direction)
        - SOMATIC: internal state (health, clarity, etc.)
        - PAIN: damage events
        - PROPRIOCEPTION: position, direction, control state

        Noise degrades vision range and touch accuracy.
        """
        noise = self.pacman.degradation.sensor_noise

        def noisy_pos(x, y):
            """Add perceptual noise to position readings."""
            if noise > 0 and random.random() < noise:
                return (
                    x + random.randint(-1, 1),
                    y + random.randint(-1, 1)
                )
            return (x, y)

        # === VISION: forward raycast ===
        vision_raw = self._raycast(
            self.pacman.x, self.pacman.y, self.pacman.direction
        )

        # Apply noise — distant objects may be missed
        vision = []
        for entry in vision_raw:
            # Chance of missing an object increases with noise and distance
            if noise > 0 and random.random() < noise * (entry['distance'] / 10):
                # Noisy: might misidentify contents
                noisy_entry = dict(entry)
                noisy_entry['contents'] = ['unclear']
                vision.append(noisy_entry)
            else:
                vision.append(entry)

        # === TOUCH: immediate adjacency ===
        adjacent = self._get_adjacent(self.pacman.x, self.pacman.y)

        # Apply noise to touch — might not feel ghost proximity
        if noise > 0:
            for d_name, info in adjacent.items():
                if info['ghost'] and random.random() < noise * 0.3:
                    info['ghost'] = None  # Didn't feel it

        # Derive walls from adjacency (backward compatible)
        walls = {d: not info['walkable'] for d, info in adjacent.items()}

        sensors = {
            # Proprioception
            'position': noisy_pos(self.pacman.x, self.pacman.y),
            'direction': self.pacman.direction.name,
            'powered_up': self.pacman.powered_up,
            'power_remaining': self.pacman.power_timer,

            # Somatic — internal state
            'health': self.pacman.degradation.overall_health,
            'clarity': self.pacman.degradation.clarity,
            'sensor_noise': self.pacman.degradation.sensor_noise,
            'memory_loss': self.pacman.degradation.memory_loss,
            'motor_impairment': self.pacman.degradation.motor_impairment,
            'in_control': self.pacman.involuntary_timer == 0,

            # Vision — forward line of sight
            'vision': vision,

            # Touch — immediate adjacency
            'adjacent': adjacent,
            'walls': walls,

            # Pain channel
            'pain_events': self.pain_events,

            # Fear channel — emergent from pain history
            'has_been_hurt': self.pacman.fear.has_been_hurt,
            'fear_intensity': self.pacman.fear.fear_intensity,
            'pain_count': self.pacman.fear.pain_count,
            'fear_resistance_ahead': (
                self.pacman.fear.get_resistance(
                    self._get_threat_ahead_distance() or 999
                ) if self.pacman.fear.has_been_hurt else 0.0
            ),

            # World state
            'tick': self.tick_count,
            'alive': self.pacman.alive,
            'pellets_remaining': self.maze.remaining_pellets(),
        }

        return sensors

    def reset(self):
        """Reset the world."""
        self.maze = Maze()
        self.pacman = PacMan(x=self.PACMAN_SPAWN[0], y=self.PACMAN_SPAWN[1])
        self.ghosts = self._create_ghosts()
        self.tick_count = 0
        self.pellets_eaten = 0
        self.ghosts_eaten = 0
        self.game_over = False
        self.pain_events = []
