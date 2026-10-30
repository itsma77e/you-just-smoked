# Configuration

Everything has a sensible default, so a config file is optional.

- **Where it goes:** create `config.toml` at the path shown by `you-just-smoked paths`.
- **Unknown keys are rejected:** a typo is reported instead of being silently ignored.

```toml
# "auto" follows the system language; "en" and "it" are available.
language = "auto"

[camera]
index = 0            # which camera to use
keep_open = false    # true: cheaper snapshots, but the camera light stays on
# width = 1280       # leave unset to keep the camera default (opens faster)
# height = 720

[sampling]
idle_seconds = 15    # time between snapshots when nothing is happening
stream_seconds = 0.5 # time between frames while something looks suspicious
active_seconds = 20  # time between snapshots during an episode
away_seconds = 60    # time between snapshots when nobody is at the desk

[episode]
threshold = 1.0          # evidence needed to open an episode; higher = fewer false alarms
quiet_minutes = 6        # no cues for this long ends an episode
refractory_minutes = 5   # cues are ignored for this long after an episode

[objects]
# model = "~/models/smoking-objects.tflite"
# min_score = 0.5
```

## Objects

Set `objects.model` to the path of a MediaPipe object detector to enable lighter, pack, rolling-paper, filter-tip and cigarette detection. Labels are matched by name; see [detection](detection.md#objects-perceptioncuesobjectspy-optional).
