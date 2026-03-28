"""
Consciousness Layer — The polling loop.

This is the temporal heartbeat of the agent. Each tick is one moment
of consciousness. The agent does not experience time between ticks.

Architecture:
- Each tick: sense -> remember -> evaluate -> decide -> act
- Every tick's state is saved to the memory stack
- Deviations from status quo open a string of ticks
- When the string closes (return to status quo for N stable ticks),
  the Will consolidates it into a single memory:
    importance = max_base_importance_in_string * span
- Pain and fear scale base importance so ghost events are retained longer
"""

import time
from sensors import SensorInterface, SensorReadout
from environment import Environment, Action
from memory import MemoryEntry, MemoryStack
from subsystems import (
    call_memory_retrieval,
    call_threat_evaluation,
    call_decision_engine,
    call_consolidation,
)


# --- Status quo detection thresholds ---
DEVIATION_FEAR_THRESHOLD = 0.1      # resistance_ahead above this = deviation
DEVIATION_CLARITY_DROP = 0.05       # clarity drop per tick above this = deviation
STABLE_TICKS_REQUIRED = 3           # ticks of stability before closing a string

# --- Base importance values ---
IMPORTANCE_NORMAL = 1.0
IMPORTANCE_FEAR_ACTIVE = 1.5        # fear resistance is active
IMPORTANCE_THREAT_VISIBLE = 1.3     # ghost visible in forward vision
IMPORTANCE_PAIN_MULTIPLIER = 8.0    # multiplied by pain severity (0.15 -> 2.2 total)


def _base_importance(readout: SensorReadout) -> float:
    """Calculate base importance for a single tick's state."""
    importance = IMPORTANCE_NORMAL

    if readout.pain.in_pain:
        importance += readout.pain.severity * IMPORTANCE_PAIN_MULTIPLIER

    if readout.fear.resistance_ahead > DEVIATION_FEAR_THRESHOLD:
        importance = max(importance, IMPORTANCE_FEAR_ACTIVE)

    if readout.vision.sees_threat:
        importance = max(importance, IMPORTANCE_THREAT_VISIBLE)

    return importance


def _is_deviated(readout: SensorReadout, last_clarity: float) -> bool:
    """
    Determine if the current state deviates from status quo.
    Status quo = calm, in control, no threats, no food interaction.
    """
    if readout.pain.in_pain:
        return True
    if not readout.proprioception.in_control:
        return True
    if readout.fear.resistance_ahead > DEVIATION_FEAR_THRESHOLD:
        return True
    if readout.vision.sees_threat:
        return True
    if readout.touch.touching_food:
        return True
    if readout.proprioception.powered_up:
        return True
    if last_clarity - readout.somatic.clarity > DEVIATION_CLARITY_DROP:
        return True
    return False


class ConsciousnessLoop:
    """
    The lesser will — a polling loop over sensor channels.

    Each cycle:
    1. Read sensors
    2. Save conscious state to memory
    3. Check for deviation / string management
    4. Retrieve relevant memories
    5. Evaluate threat
    6. Decide action
    7. Act
    """

    def __init__(
        self,
        env: Environment,
        tick_delay: float = 0.5,
        memory_size: int = 200,
        verbose: bool = True,
    ):
        self.env = env
        self.sensor_interface = SensorInterface()
        self.memory = MemoryStack(max_size=memory_size)
        self.tick_delay = tick_delay
        self.verbose = verbose

        # String tracking
        self._current_string: list[MemoryEntry] = []
        self._in_deviation: bool = False
        self._stable_ticks: int = 0
        self._last_clarity: float = 1.0

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _compute_string_importance(self, entries: list[MemoryEntry]) -> float:
        """
        Importance of a consolidated string =
        max base importance of any entry * number of ticks in the string.
        """
        base = max(e.importance for e in entries)
        return base * len(entries)

    def _close_string(self):
        """
        The string has ended (returned to status quo).
        If it covered more than one tick, consolidate it into one memory.
        Replace the individual entries with the consolidated summary.
        """
        if not self._current_string:
            return

        if len(self._current_string) == 1:
            # Single-tick deviation — already saved, just clear the string
            self._current_string = []
            return

        # Multi-tick string — consolidate via the Will
        self._log(f"  [Will] Consolidating string of {len(self._current_string)} ticks...")
        summary = call_consolidation(self._current_string)
        importance = self._compute_string_importance(self._current_string)
        span = len(self._current_string)
        first_tick = self._current_string[0].tick

        consolidated = MemoryEntry(
            text=summary,
            tick=first_tick,
            span=span,
            importance=importance,
            is_consolidated=True,
        )

        # Remove individual entries, replace with consolidated
        self.memory.remove(self._current_string)
        self.memory.push(consolidated)

        self._log(f"  [Memory] Saved: \"{summary}\" (importance={importance:.2f}, span={span})")
        self._current_string = []

    def _update_string_tracking(self, entry: MemoryEntry, readout: SensorReadout):
        """Track deviation strings. Open, accumulate, and close them."""
        deviated = _is_deviated(readout, self._last_clarity)

        if deviated:
            self._stable_ticks = 0
            if not self._in_deviation:
                self._in_deviation = True
                self._log(f"  [String] Deviation opened at tick {entry.tick}")
            self._current_string.append(entry)

        else:
            if self._in_deviation:
                # Accumulate stability ticks — include transition back in the string
                self._stable_ticks += 1
                self._current_string.append(entry)

                if self._stable_ticks >= STABLE_TICKS_REQUIRED:
                    self._in_deviation = False
                    self._stable_ticks = 0
                    self._log(f"  [String] Deviation closed, {len(self._current_string)} ticks total")
                    self._close_string()

    def run(self):
        """Run the consciousness loop until death or game over."""
        self._log("=== CONSCIOUSNESS ONLINE ===")

        action = Action.NONE

        while True:
            raw = self.env.step(action)
            readout = self.sensor_interface.process(raw)

            if not readout.alive:
                self._log("=== SYSTEM FAILURE — POLLING LOOP CEASED ===")
                break

            if self.env.game_over:
                self._log("=== GAME OVER ===")
                break

            state_text = readout.to_text()
            self._log(f"\n--- Tick {readout.tick} ---")

            # Save this instant to memory
            base_imp = _base_importance(readout)
            entry = MemoryEntry(
                text=state_text,
                tick=readout.tick,
                span=1,
                importance=base_imp,
                is_consolidated=False,
            )
            self.memory.push(entry)

            # Update string tracking
            self._update_string_tracking(entry, readout)
            self._last_clarity = readout.somatic.clarity

            # === Cognitive subsystems ===
            self._log(f"  [Memory] Querying {len(self.memory)} entries...")
            memory_text = call_memory_retrieval(self.memory, state_text)

            self._log(f"  [Threat] Evaluating...")
            threat_text = call_threat_evaluation(state_text)

            self._log(f"  [Decision] Choosing action...")
            action = call_decision_engine(state_text, memory_text, threat_text)

            self._log(f"  => {action.name}")

            time.sleep(self.tick_delay)

        self._log("=== CONSCIOUSNESS OFFLINE ===")


if __name__ == "__main__":
    env = Environment()
    loop = ConsciousnessLoop(env, tick_delay=0.3)
    loop.run()
