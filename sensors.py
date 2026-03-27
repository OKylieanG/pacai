"""
Sensor Interface — Translates raw environment sensor data into
structured channels for the consciousness layer.

Sensory model:
- VISION: forward line of sight, blocked by walls. Primary distance sense.
- TOUCH: immediate adjacency (1 cell). Feels walls, pellets, ghosts nearby.
- SOMATIC: internal state — health, clarity, damage levels.
- PAIN: damage events with source information.
- PROPRIOCEPTION: position, facing, control state.

The agent sees ahead and feels around. It must turn to look.
"""

from dataclasses import dataclass, field
from typing import Optional
from environment import Environment, Direction


@dataclass
class ProprioceptionChannel:
    """Where am I? What am I doing?"""
    position: tuple[int, int]
    direction: str
    in_control: bool  # False during pain reflex
    powered_up: bool
    power_remaining: int


@dataclass
class SomaticChannel:
    """How am I? Internal body state."""
    health: float
    clarity: float
    sensor_quality: float   # 1.0 - noise
    memory_quality: float   # 1.0 - loss
    motor_quality: float    # 1.0 - impairment


@dataclass
class PainChannel:
    """Am I being hurt?"""
    in_pain: bool
    pain_source: Optional[str]
    severity: float
    was_pushed: bool


@dataclass
class VisionObject:
    """Something seen along the line of sight."""
    distance: int
    x: int
    y: int
    contents: list[str]  # 'empty', 'pellet', 'power_pellet', 'wall',
                         # 'ghost:name:status', 'unclear', 'boundary'


@dataclass
class VisionChannel:
    """What do I see ahead of me?"""
    facing: str
    objects: list[VisionObject]
    corridor_length: int  # How far until wall
    sees_threat: bool
    sees_food: bool
    threat_distance: Optional[int]
    food_distance: Optional[int]


@dataclass
class AdjacentCell:
    """What's immediately next to me in one direction."""
    direction: str
    cell_type: str  # 'wall', 'empty', 'pellet', 'power_pellet', 'boundary'
    walkable: bool
    ghost_name: Optional[str]
    ghost_scared: bool


@dataclass
class TouchChannel:
    """What can I feel immediately around me?"""
    cells: list[AdjacentCell]
    open_directions: list[str]
    blocked_directions: list[str]
    touching_ghost: bool
    touching_food: bool


@dataclass
class SensorReadout:
    """
    Complete sensor readout for one tick.
    This is what consciousness polls.
    """
    tick: int
    alive: bool
    proprioception: ProprioceptionChannel
    somatic: SomaticChannel
    pain: PainChannel
    vision: VisionChannel
    touch: TouchChannel
    pellets_remaining: int

    def to_text(self) -> str:
        """
        Convert sensor readout to natural language for Claude instances.
        This is how the consciousness agents will perceive the world.
        """
        lines = [f"=== SENSOR READOUT (Tick {self.tick}) ==="]

        if not self.alive:
            lines.append("STATUS: SYSTEM FAILURE — ALL FUNCTIONS CEASED")
            return "\n".join(lines)

        # Proprioception
        px, py = self.proprioception.position
        lines.append(f"\nBODY: Position ({px}, {py}), "
                     f"facing {self.proprioception.direction}")
        if not self.proprioception.in_control:
            lines.append("!! Motor control overridden by reflex !!")
        if self.proprioception.powered_up:
            lines.append(f"EMPOWERED: {self.proprioception.power_remaining} "
                         f"ticks remaining")

        # Somatic
        s = self.somatic
        lines.append(f"\nINTERNAL STATE:")
        lines.append(f"  Health: {s.health:.0%}")
        lines.append(f"  Clarity: {s.clarity:.0%}")
        lines.append(f"  Sensor quality: {s.sensor_quality:.0%}")
        lines.append(f"  Memory quality: {s.memory_quality:.0%}")
        lines.append(f"  Motor quality: {s.motor_quality:.0%}")

        # Pain
        if self.pain.in_pain:
            lines.append(f"\n!! PAIN: Contact with {self.pain.pain_source}, "
                         f"severity {self.pain.severity:.0%}")
            if self.pain.was_pushed:
                lines.append("  Body was involuntarily pushed away from source")

        # Vision
        v = self.vision
        lines.append(f"\nVISION (facing {v.facing}):")
        if v.facing == "NONE":
            lines.append("  Not facing any direction — no forward vision")
        elif not v.objects:
            lines.append("  Nothing visible")
        else:
            lines.append(f"  Corridor extends {v.corridor_length} cells ahead")
            for obj in v.objects:
                content_str = ', '.join(obj.contents)
                lines.append(f"  Distance {obj.distance}: {content_str}")
            if v.sees_threat:
                lines.append(f"  !! THREAT VISIBLE at distance {v.threat_distance} !!")
            if v.sees_food:
                lines.append(f"  Food visible at distance {v.food_distance}")

        # Touch
        t = self.touch
        lines.append(f"\nTOUCH:")
        lines.append(f"  Can move: {', '.join(t.open_directions)}")
        if t.blocked_directions:
            lines.append(f"  Walls: {', '.join(t.blocked_directions)}")
        for cell in t.cells:
            if cell.ghost_name:
                status = "scared" if cell.ghost_scared else "DANGEROUS"
                lines.append(f"  !! {cell.direction}: Ghost '{cell.ghost_name}' "
                             f"({status}) right next to me !!")
            elif cell.cell_type in ('pellet', 'power_pellet'):
                lines.append(f"  {cell.direction}: {cell.cell_type}")

        if t.touching_ghost:
            lines.append("  !! GHOST ADJACENT !!")

        lines.append(f"\nWorld: {self.pellets_remaining} pellets remaining")

        return "\n".join(lines)


class SensorInterface:
    """
    Translates raw environment sensor dict into structured
    SensorReadout for the consciousness layer.
    """

    def process(self, raw_sensors: dict) -> SensorReadout:
        """Convert raw sensor dict to structured readout."""

        # Proprioception
        proprioception = ProprioceptionChannel(
            position=raw_sensors['position'],
            direction=raw_sensors['direction'],
            in_control=raw_sensors['in_control'],
            powered_up=raw_sensors['powered_up'],
            power_remaining=raw_sensors['power_remaining'],
        )

        # Somatic
        somatic = SomaticChannel(
            health=raw_sensors['health'],
            clarity=raw_sensors['clarity'],
            sensor_quality=1.0 - raw_sensors['sensor_noise'],
            memory_quality=1.0 - raw_sensors['memory_loss'],
            motor_quality=1.0 - raw_sensors['motor_impairment'],
        )

        # Pain
        pain_events = raw_sensors['pain_events']
        if pain_events:
            latest = pain_events[-1]
            pain = PainChannel(
                in_pain=True,
                pain_source=latest['ghost'],
                severity=latest['severity'],
                was_pushed=latest['pushed'],
            )
        else:
            pain = PainChannel(
                in_pain=False,
                pain_source=None,
                severity=0.0,
                was_pushed=False,
            )

        # Vision
        vision_objects = [
            VisionObject(
                distance=v['distance'],
                x=v['x'], y=v['y'],
                contents=v['contents'],
            )
            for v in raw_sensors['vision']
        ]

        # Compute corridor length (distance to wall/boundary)
        corridor_length = 0
        for obj in vision_objects:
            if 'wall' in obj.contents or 'boundary' in obj.contents:
                corridor_length = obj.distance
                break
            corridor_length = obj.distance

        # Find threats and food in vision
        threat_dist = None
        food_dist = None
        for obj in vision_objects:
            for c in obj.contents:
                if c.startswith('ghost:') and ':dangerous' in c:
                    if threat_dist is None:
                        threat_dist = obj.distance
                if c in ('pellet', 'power_pellet'):
                    if food_dist is None:
                        food_dist = obj.distance

        vision = VisionChannel(
            facing=raw_sensors['direction'],
            objects=vision_objects,
            corridor_length=corridor_length,
            sees_threat=threat_dist is not None,
            sees_food=food_dist is not None,
            threat_distance=threat_dist,
            food_distance=food_dist,
        )

        # Touch
        adjacent = raw_sensors['adjacent']
        touch_cells = []
        open_dirs = []
        blocked_dirs = []
        touching_ghost = False
        touching_food = False

        for dir_name, info in adjacent.items():
            ghost_name = None
            ghost_scared = False
            if info['ghost']:
                ghost_name = info['ghost']['name']
                ghost_scared = info['ghost']['scared']
                touching_ghost = True

            if info['type'] in ('pellet', 'power_pellet'):
                touching_food = True

            if info['walkable']:
                open_dirs.append(dir_name)
            else:
                blocked_dirs.append(dir_name)

            touch_cells.append(AdjacentCell(
                direction=dir_name,
                cell_type=info['type'],
                walkable=info['walkable'],
                ghost_name=ghost_name,
                ghost_scared=ghost_scared,
            ))

        touch = TouchChannel(
            cells=touch_cells,
            open_directions=open_dirs,
            blocked_directions=blocked_dirs,
            touching_ghost=touching_ghost,
            touching_food=touching_food,
        )

        return SensorReadout(
            tick=raw_sensors['tick'],
            alive=raw_sensors['alive'],
            proprioception=proprioception,
            somatic=somatic,
            pain=pain,
            vision=vision,
            touch=touch,
            pellets_remaining=raw_sensors['pellets_remaining'],
        )
