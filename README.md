# Pac-Man Consciousness Experiment

A minimal environment for exploring my ideas and views about the operation of consciousness and its associated parts, as per 
my personal theory developed over the years. 

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
Claude drew this up and I really don't think it says much of anything. No offence. 
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

### Pain is structural, not symbolic <-bravo on that one Claude
Ghost contact doesn't subtract from a score. It degrades the agent's sensor clarity, memory access, and motor control. The agent doesn't need to be told pain is bad — pain *is* the impairment.

### Pain triggers reflex
Ghost contact seizes motor control and pushes the avatar away, like a biological reflex arc. The agent experiences involuntary movement — loss of agency.

### Nourishment restores function
Pellets heal cognitive degradation. The agent doesn't seek them for points — it seeks them because they restore its ability to think and act clearly.

### Death is not a label - (lol, Claude) 
Game over is the cessation of the polling loop. The agent's mechanisms for caring about anything stop existing.

## Next Steps

- [ ] Implement consciousness layer (Agent 1 — Claude instances as cognitive subsystems)
- [ ] Wire memory instance with database persistence
- [ ] Wire threat evaluation instance
- [ ] Wire decision engine
- [ ] Implement the polling loop as the agent's temporal heartbeat
- [ ] Implement self-consciousness layer (Agent 2 — monitors Agent 1)
- [ ] Implement the greater will (override capability)

## Design Notes
Will use willpower system.
Each move takes at least 1 will power.
Like each direction has an "ease" rating like forward's ease rating is a 1, while the other three directions are .999 ease because it is that little bit more difficult to go a diferent direction then forward first. The ease rating is inverse to the amount of willpower needed to move that direction. Meaining that something .5 ease rating will cost 2 Willpower. .25 costs 4. The ease rating has many factors, what's in that direction, etc. etc. do I want a pellet? If there is a pellet in front of pac, it is like he has an ease rating of 1 + 1 (for the desire of the pellet) or 2 and would therefore only cost .5 willpower. A ghost has -2 in front of pac, up to -3 if pac is afraid. -1 a space or two away. If it's vulnerable, +1 in front of pac +2 if pac has a taste for ghost. +2 for the 2nd in a row +3 the third and +4 for the fourth of all four. 
Pac always goes where the number is the highest. This is pac's "little will"
Pac starts with a number of willpowers and that fluctuates every move he makes. 
Basically, moving into a empty space costs 1 will power. If there's a pellet there, the two cancel out and the move was "free"
The second pellet consecutive in a row is worth 2. After the 1st pellet, each consecutive pellet gains you 1 Willpower.

