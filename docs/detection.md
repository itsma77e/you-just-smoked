# How detection works

All distances are measured in **face widths** when a face is visible, so the cues
behave the same whether you sit close to the camera or far from it.

## Rolling (`perception/cues/rolling.py`)

- **Fires when:** two hands are visible, both wrists are below the mouth, and the thumb, index or middle fingertips of one hand are within about 0.6 face widths of the other hand's.
- **Typing** is excluded because the hands are too far apart.
- **Resting your chin** is excluded because the hands are above the mouth.
- **Clasped hands** still pass a single frame. That is why rolling has a low weight and must be seen for roughly 15–20 seconds before an episode opens.

## Flame (`perception/cues/flame.py`)

A webcam clips a lighter flame to a white core with an orange rim. On a 320 px copy of the frame, the detector looks for connected blobs that:

- are **small**: between 0.01% and 1.5% of the frame, which rules out lamps and windows;
- have a **clipped core**: at least 25% very bright, near-colourless pixels, which rules out skin;
- have a **warm rim**: at least 10% bright orange or yellow pixels, which rules out screens and LEDs;
- sit **near the mouth or a fingertip**, which rules out a candle on the shelf.

If more than 8% of the frame is clipped, the exposure is useless and the frame is skipped.

## Puff (`perception/cues/puff.py`)

- **Fires when:** two fingertips are pinched together, as if holding something thin, within half a face width of the mouth.
- **Confounders:** drinking and nail biting look similar in one frame, so a puff alone never opens an episode.

## Objects (`perception/cues/objects.py`, optional)

- **What it is:** any MediaPipe object detector (`.tflite`), for example one trained with [MediaPipe Model Maker](https://ai.google.dev/edge/mediapipe/solutions/customization/object_detector).
- **Default labels:** `lighter`, `cigarette_pack`, `tobacco_pouch`, `rolling_paper`, `filter_tip`, `cigarette`. They map to the lighter, pack, rolling and cigarette cues.
- **Setup:** see [configuration](configuration.md#objects).

## Weights

| Cue | Weight | Counts as consumption |
|---|---|---|
| rolling | 0.35 | no |
| lighter | 0.5 | no |
| pack | 0.4 | no |
| cigarette | 0.6 | yes |
| flame | 0.9 | yes |
| puff | 0.45 | yes |

- **Threshold:** an episode opens at 1.0.
- **Examples:** a flame plus a puff a few seconds later is enough; so is about 20 seconds of rolling.
- **Changing them:** the weights live in `domain/evidence.py`.

## Tuning

Run `you-just-smoked preview` to see the landmarks, the cues firing on each frame, and the tracker's suspicion level. Nothing is recorded.
