# Architecture

Ports and adapters around a pure core. The rule is simple: **decisions live in
`domain/`, which has no I/O**, and everything that touches the outside world is
a small adapter behind a protocol.

```
src/you_just_smoked/
├── domain/        pure logic: cues, evidence, episode tracker, stats, sampling policy
├── perception/    frame -> scene (MediaPipe) -> cue observations (one detector per cue)
├── capture/       webcam adapter and the open/close policy
├── storage/       SQLite episode log with numbered migrations
├── notify/        user-facing text (en, it) and native notifications with buttons
├── ui/            tray icon and menu
├── runtime/       the engine loop, its commands, ports and published status
├── app/           config, file locations, composition root, preview window
└── cli.py         entry point
```

## Data flow

1. The **sampling policy** (`domain/sampling.py`) looks at the tracker phase and
   the current suspicion, and picks `OFF`, `SNAPSHOT` (open, grab, release) or
   `STREAM` (keep open at 2 fps).
2. The **camera controller** grabs a frame in that mode.
3. The **perception pipeline** turns it into a `Scene` (hands, main face, in
   aspect-correct units) once, then runs every cue detector on it. Detectors are
   stateless and cheap.
4. Each `CueObservation` goes to the **episode tracker**, which emits events.
5. The **engine** reacts to events:
   - `EpisodeOpened` sends the nudge.
   - `EpisodeClosed` is written to the log.

## The episode tracker

`domain/tracker.py` is the heart of the "one nudge per cigarette" promise.

```
IDLE ──evidence ≥ threshold──▶ ACTIVE ──quiet──▶ REFRACTORY ──time──▶ IDLE
                                 │  ▲
                          "wait" │  │ consumption evidence ≥ threshold
                                 ▼  │
                              POSTPONED ──quiet──▶ IDLE (resisted)
```

- **Evidence** (`domain/evidence.py`):
  - Each observation adds `weight × confidence` to a running total that halves every 45 s.
  - A cue counts at most once every 5 s, so streaming faster does not inflate it.
- **IDLE → ACTIVE** is the only transition that emits `EpisodeOpened`, so a second nudge for the same cigarette is impossible by construction.
- **POSTPONED** waits for *consumption* cues only (flame, puff, cigarette). Fiddling with the rolled cigarette after choosing to wait does not count as giving in.
- **REFRACTORY** ignores cues for a few minutes after an episode, including after a false alarm, so the same cause cannot immediately nag again.

## Threads

- **Main thread:** the tray (macOS requires it).
- **Engine thread:** creates and owns everything stateful — database, models and camera. Nothing stateful is shared.
- **How they talk:** the tray and the notification buttons only put commands on a queue. The engine publishes an immutable `Status` that the tray renders.

## Testing

- **Domain:** tested directly, with fixed timestamps.
- **Detectors:** tested with hand-written landmarks and synthetic images.
- **Engine:** tested end to end with in-memory fakes for every port (`tests/fakes.py`).
- **No camera needed:** none of the tests use one.
