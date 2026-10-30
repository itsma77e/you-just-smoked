# Contributing

Thanks for helping people smoke a little less.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

These must pass before a pull request is merged; CI runs the same commands.

```bash
ruff format --check .
ruff check .
mypy
pytest
```

## Guidelines

- **Keep `domain/` pure.** No camera, disk, clock or network in there. Pass time in, return events out.
- **One cue, one detector.** A new signal is a new file in `perception/cues/` that implements `CueDetector`. Register it in `app/bootstrap.py` and give it a weight in `domain/evidence.py`.
- **Test without hardware.** Use hand-written landmarks (`tests/factories.py`) or synthetic images, and the fakes in `tests/fakes.py` for the engine.
- **Privacy is a feature.** Never write frames to disk or send anything over the network. An opt-in dataset collector must be explicit, local and off by default.
- **Be kind in the copy.** Messages encourage waiting; they never shame.
- **Translations:** add a language to `notify/messages.py`. A test checks that every key is present.

## Reporting false alarms or misses

Run `you-just-smoked preview` and describe what you were doing, which cues fired, and your camera position. Please do not attach images of people.
