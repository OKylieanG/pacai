"""
Cognitive Subsystems — Stateless Claude API calls.

Each subsystem is a single API call. They are not agents.
State lives in the orchestrator, not here.

Subsystems:
- memory_retrieval: Given the memory stack and current state, what's relevant?
- threat_evaluation: Given the current state, what's the threat situation?
- decision_engine: Given everything, choose an Action.
- consolidation: Given a string of conscious states, write one summary.
"""

import os
import anthropic
from environment import Action
from memory import MemoryEntry, MemoryStack

MODEL = "claude-sonnet-4-20250514"

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def call_memory_retrieval(stack: MemoryStack, current_state_text: str) -> str:
    """
    Given the full memory stack and current sensor state,
    return the memories most relevant to this moment.
    """
    stack_text = stack.format_for_retrieval()

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=512,
        system=(
            "You are the memory subsystem of a conscious agent navigating a maze. "
            "You have access to the agent's long-term memory stack and its current "
            "sensor state. Your job is to identify which memories are most relevant "
            "to the current moment and summarize them concisely. "
            "Focus on: past pain events, known threat locations, food sources, "
            "patterns that match the current situation. "
            "If nothing is relevant, say so briefly. Be concise."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"CURRENT STATE:\n{current_state_text}\n\n"
                f"MEMORY STACK:\n{stack_text}\n\n"
                "What from memory is relevant to this moment?"
            )
        }]
    )
    return response.content[0].text


def call_threat_evaluation(current_state_text: str) -> str:
    """
    Assess the current threat situation from sensor data.
    Returns a brief threat assessment.
    """
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=256,
        system=(
            "You are the threat evaluation subsystem of a conscious agent. "
            "You receive the agent's current sensor state and assess danger. "
            "Consider: visible threats and distance, fear resistance levels, "
            "pain currently active, involuntary movement. "
            "Output: threat level (none/low/medium/high/critical), "
            "what the threat is, recommended avoidance direction if any. "
            "Be concise."
        ),
        messages=[{
            "role": "user",
            "content": f"CURRENT STATE:\n{current_state_text}\n\nAssess the threat."
        }]
    )
    return response.content[0].text


def call_decision_engine(
    current_state_text: str,
    memory_text: str,
    threat_text: str,
) -> Action:
    """
    Given sensor state, relevant memories, and threat assessment,
    choose the next action. Returns an Action enum value.
    """
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=128,
        system=(
            "You are the decision engine of a conscious agent navigating a maze. "
            "You receive the agent's sensor state, relevant memories, and threat assessment. "
            "Choose one action: FORWARD, TURN_LEFT, TURN_RIGHT, or NONE.\n\n"
            "Movement rules:\n"
            "- FORWARD: move one cell in facing direction (may be blocked by fear or walls)\n"
            "- TURN_LEFT: rotate 90\u00b0 left (no movement)\n"
            "- TURN_RIGHT: rotate 90\u00b0 right (no movement)\n"
            "- NONE: stand still\n\n"
            "Goals: avoid ghosts, collect pellets to restore clarity, survive.\n"
            "Respond with ONLY the action word: FORWARD, TURN_LEFT, TURN_RIGHT, or NONE."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"CURRENT STATE:\n{current_state_text}\n\n"
                f"RELEVANT MEMORIES:\n{memory_text}\n\n"
                f"THREAT ASSESSMENT:\n{threat_text}\n\n"
                "Choose action:"
            )
        }]
    )

    raw = response.content[0].text.strip().upper()
    action_map = {
        "FORWARD": Action.FORWARD,
        "TURN_LEFT": Action.TURN_LEFT,
        "TURN_RIGHT": Action.TURN_RIGHT,
        "NONE": Action.NONE,
    }
    return action_map.get(raw, Action.NONE)


def call_consolidation(entries: list[MemoryEntry]) -> str:
    """
    Given a string of consecutive conscious states that form a meaningful
    episode, write a single natural language summary describing what happened
    and why it was significant.
    """
    entries_text = "\n\n".join(
        f"[Tick {e.tick}]\n{e.text}" for e in entries
    )

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=150,
        system=(
            "You are the memory consolidation function of a conscious agent. "
            "You receive a sequence of conscious states that form a meaningful episode "
            "(a deviation from the agent's normal baseline). "
            "Write ONE concise sentence (max 30 words) describing what happened "
            "and what was significant about it. "
            "Write from the agent's perspective. Focus on cause and effect. "
            "Example: 'Touched a ghost while moving forward, was pushed back, "
            "clarity degraded significantly.'"
        ),
        messages=[{
            "role": "user",
            "content": (
                f"EPISODE ({len(entries)} ticks):\n{entries_text}\n\n"
                "Summarize what happened:"
            )
        }]
    )
    return response.content[0].text.strip()
