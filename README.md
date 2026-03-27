# Pac-Man Consciousness Experiment

A minimal environment for exploring artificial consciousness, built on a two-layer model:

1. **Consciousness** — A polling loop over sensor channels. An agent that reads its sensors and acts. The philosophical zombie layer.
2. **Self-Consciousness** — A second agent that monitors the first, modeling its behavior and enabling the greater will.

## Architecture

```
┌──────────────────────────────────────────────┐
│              SELF-CONSCIOUSNESS              │
│        (Agent 2 — monitors Agent 1)          │
│           The Greater Will                   │
└──────────────────┬───────────────────────────┘
                   │ observes / overrides
┌──────────────────▼───────────────────────────┐
│               CONSCIOUSNESS                  │
│          (Agent 1 — polling loop)            │
│            The Lesser Will                   │
│                                              │
│  ┌─────────┐ ┌────────┐ ┌─────────────────┐ │
│  │ Memory  │ │ Threat │ │ Decision Engine │ │
│  │Instance │ │Eval    │ │    Instance     │ │
│  │(Claude) │ │Instance│ │   (Claude)      │ │
│  └────┬────┘ └───┬────┘ └───────┬─────────┘ │
│       └──────────┴──────────────┘            │
└──────────────────┬───────────────────────────┘
                   │ sensors / actions
┌──────────────────▼───────────────────────────┐
│              ENVIRONMENT                     │
│          Pac-Man Grid World                  │
│                                              │
│  Pain = degradation + involuntary movement   │
│  Nourishment = restoration of clarity        │
│  Death = cessation of the polling loop       │
└──────────────────────────────────────────────┘
```

## Files

- `src/environment.py` — Grid world, entities, physics, collision, degradation
- `src/renderer.py` — Pygame visualization + manual play mode
- `src/sensors.py` — Translates world state into structured sensor channels

## Running

### Manual Play (test the environment)
```bash
cd src
python renderer.py
```
- Arrow keys / WASD to move
- R to reset
- ESC to quit
- Watch the health panel — ghost contact degrades your cognitive systems

## Design Principles

### Pain is structural, not symbolic
Ghost contact doesn't subtract from a score. It degrades the agent's sensor clarity, memory access, and motor control. The agent doesn't need to be told pain is bad — pain *is* the impairment.

### Pain triggers reflex
Ghost contact seizes motor control and pushes the avatar away, like a biological reflex arc. The agent experiences involuntary movement — loss of agency.

### Nourishment restores function
Pellets heal cognitive degradation. The agent doesn't seek them for points — it seeks them because they restore its ability to think and act clearly.

### Death is not a label
Game over is the cessation of the polling loop. The agent's mechanisms for caring about anything stop existing.

## Next Steps

- [ ] Implement consciousness layer (Agent 1 — Claude instances as cognitive subsystems)
- [ ] Wire memory instance with database persistence
- [ ] Wire threat evaluation instance
- [ ] Wire decision engine
- [ ] Implement the polling loop as the agent's temporal heartbeat
- [ ] Implement self-consciousness layer (Agent 2 — monitors Agent 1)
- [ ] Implement the greater will (override capability)
