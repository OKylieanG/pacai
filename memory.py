"""
Memory Stack — Long-term memory for the consciousness layer.

Each conscious state (a tick's sensor readout converted to text) is saved
as a MemoryEntry. The Will can consolidate consecutive entries into a single
summary with higher importance.

Stack management:
- Fixed capacity. When full, the oldest entry with the lowest importance
  is evicted.
- Importance = base_importance * span (span = number of ticks covered).
- Consolidated entries always outrank single instants at equal base importance
  because their span multiplier is > 1.
"""

from dataclasses import dataclass


@dataclass
class MemoryEntry:
    """A single unit of long-term memory."""
    text: str               # Natural language — raw sensor text or Will-written summary
    tick: int               # World tick when this entry was created
    span: int               # Number of ticks this entry covers
    importance: float       # base_importance * span
    is_consolidated: bool   # True if written by the Will as a summary


class MemoryStack:
    """
    Fixed-capacity stack of MemoryEntry objects.

    Eviction policy: when full, remove the oldest entry with the
    lowest importance score. Importance is pre-multiplied by span,
    so consolidated entries (span > 1) naturally resist eviction.
    """

    def __init__(self, max_size: int = 200):
        self.max_size = max_size
        self._entries: list[MemoryEntry] = []

    def push(self, entry: MemoryEntry) -> None:
        """Add an entry. Evict if over capacity."""
        self._entries.append(entry)
        if len(self._entries) > self.max_size:
            self._evict()

    def _evict(self) -> None:
        """Remove the oldest entry with the minimum importance."""
        if not self._entries:
            return
        min_importance = min(e.importance for e in self._entries)
        candidates = [e for e in self._entries if e.importance == min_importance]
        oldest = min(candidates, key=lambda e: e.tick)
        self._entries.remove(oldest)

    def remove(self, entries: list[MemoryEntry]) -> None:
        """Remove specific entries (used during consolidation)."""
        for entry in entries:
            try:
                self._entries.remove(entry)
            except ValueError:
                pass

    def get_all(self) -> list[MemoryEntry]:
        """Return all entries in chronological order."""
        return sorted(self._entries, key=lambda e: e.tick)

    def format_for_retrieval(self) -> str:
        """
        Format the full stack as text for the memory retrieval subsystem.
        Each entry is labeled with its tick, span, and importance.
        """
        if not self._entries:
            return "(No memories yet)"

        lines = ["=== LONG-TERM MEMORY ==="]
        for entry in self.get_all():
            label = f"[Tick {entry.tick}"
            if entry.span > 1:
                label += f"\u2013{entry.tick + entry.span - 1}"
            label += f", importance={entry.importance:.2f}"
            if entry.is_consolidated:
                label += ", summary"
            label += "]"
            lines.append(f"{label}\n{entry.text}\n")

        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._entries)
