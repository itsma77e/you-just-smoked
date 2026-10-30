# you-just-smoked

A local webcam companion that notices when you're about to smoke (rolling, lighter, pack, flame) and tells you how long it's been since your last one. One episode, one nudge. No cloud.

> **Your last one was 47 min ago.**
> 6 today. Can you make it to 1 h?
>
> `[ I'll wait ]` `[ Smoking anyway ]` `[ Not smoking ]`

It does not try to make you quit. It tries to buy you a little time between cigarettes, because a few minutes, many times a day, add up.

## What you see

Nothing, while you work. There is only a small icon by the clock.

- **When you're about to smoke** (rolling in front of the camera, or bringing a lighter or flame to your face), a card slides in once, with a chime:
  - how long ago your last one was;
  - how many you have had today;
  - the choice between **I'll wait**, **Smoking anyway** and **Not smoking**.
- **I'll wait** turns the card into a countdown to the goal it offered ("16 min ago, can you make it to 30?" counts down 14 minutes; never more than 25), with small tips: a glass of water, three deep breaths...
  - **Hide** folds it into a small tab on the screen edge that keeps showing the time left. Click the tab to open it again.
  - When time is up it chimes, comes back by itself and celebrates the minutes you gained.
- **The tray icon** shows today's numbers. From its menu you can:
  - open the **statistics** card: live timer, week chart, longest gap, achievements;
  - log a cigarette it missed;
  - pause it for an hour;
  - quit.
- **Achievements:** first wait, first one skipped, one hour clear, two hours clear, 30 minutes gained, three skipped in a day, fewer than the day before.

## How it works

```
 webcam ──▶ hands + face ──▶ cues ──▶ evidence ──▶ episode ──▶ one nudge
 (sparse)   (MediaPipe)      rolling   decays       state       and an
                             flame     over time    machine     honest log
                             puff
                             objects*
```

- **Many cues, one decision.** Rolling, a flame near your face, a hand at your mouth: each cue only adds evidence, and evidence fades within about a minute. A single glimpse means nothing. Several cues close together open an **episode**.
- **One nudge per cigarette.** Only opening an episode shows the nudge. Lighting up, puffing and everything else that follows just refines the same episode, and then a short quiet period stops one long cigarette from counting twice.
- **Your answer matters.**
  - **I'll wait:** the episode is put on hold. If you light up later, it is logged with the time you held off. If you don't, it is logged as resisted.
  - **Smoking anyway:** nothing else bothers you.
  - **Not smoking:** it is kept as a label for tuning and never counted.
- **The camera is off most of the time.** It takes one snapshot every 15 seconds and then releases the camera. It streams at 2 fps only while something looks suspicious, and it turns off completely while paused or right after a cigarette.

The full design is in [docs/architecture.md](docs/architecture.md) and the cue heuristics are in [docs/detection.md](docs/detection.md).

## Privacy

- Everything runs on your computer. No account, no network calls except the one-time download of two public MediaPipe models, which are pinned by SHA-256.
- Frames are analysed in memory and discarded. **No image or video is ever written to disk.**
- The only data stored is a small SQLite log of episodes: start and end time, outcome, and the cue that triggered it. `you-just-smoked paths` shows where it lives.

## Install

Requires Python 3.11 or newer, on Windows, macOS (Apple Silicon) or Linux (x86-64 or arm64). On Linux, install Tk too (`sudo apt install python3-tk`); window corners are square there.

```bash
git clone https://github.com/itsma77e/you-just-smoked.git
cd you-just-smoked
python -m venv .venv
```

Activate the environment (Windows: `.venv\Scripts\activate`, macOS/Linux: `source .venv/bin/activate`), then:

```bash
pip install -e .
```

## Use

```bash
you-just-smoked            # start watching, with an icon in the tray
you-just-smoked preview    # live window: landmarks, cues and tracker state
you-just-smoked status     # today's numbers
you-just-smoked paths      # where config, data and logs live
```

Use **I just smoked** in the tray menu for cigarettes it could not see (smoking outside, for example).

Run `preview` once to check that your hands are in frame when you roll. Most laptop cameras only see your face, so raising the screen or tilting it down a little helps a lot.

Settings are optional; see [docs/configuration.md](docs/configuration.md).

## What it can and cannot see

| Cue | Status | How |
|---|---|---|
| Rolling | works out of the box | both hands' fingertips together below the face |
| Flame near face or hand | works out of the box | small clipped-white blob with a warm rim |
| Hand at mouth (puff) | works out of the box | pinched fingertips at the mouth; never enough alone |
| Lighter, pack, papers, filter tips, cigarette | needs a model | optional MediaPipe object detector you supply |

There is no public dataset for packs, lighters or rolling papers yet. Building one, collected locally and opt-in, is the main item on the roadmap.

These are heuristics, so expect some false alarms at first. Answering **Not smoking** is exactly the data that will let us calibrate them.

## Resource use

Measured on a Windows laptop, idle at the desk:

- **CPU:** about 4% of one core on average. Most of it is opening and closing the camera; analysing a frame takes about 25 ms.
- **Memory:** about 270 MB in total.
  - Most of it is the MediaPipe runtime.
  - The interface is plain Tk drawn with Pillow (about 20 MB), not a web view (about 280 MB).
  - The camera runs in a small helper process. Windows leaks a few MB every time a webcam is opened, so the helper is restarted every 20 opens and the app's memory stays flat.

If you don't mind the camera light staying on, `keep_open = true` makes snapshots cheaper.

## Roadmap

- Opt-in local dataset collector and a trained object detector for lighters, packs, papers and filter tips.
- Per-user calibration from your answers.
- Packaged builds that start at login.
- More languages (currently English and Italian).

## Contributing

Contributions are welcome, especially data, detection ideas and translations. See [CONTRIBUTING.md](CONTRIBUTING.md).

## A note on health

This is not a medical device and not a substitute for support. If you want to quit, free help works and is worth it. The [WHO quitting tobacco page](https://www.who.int/activities/quitting-tobacco) lists options, and most countries have a free national quitline.

## License

[MIT](LICENSE)
