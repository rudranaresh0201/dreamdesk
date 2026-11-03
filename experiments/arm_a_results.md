# Arm A results: behaviour cloning on the calculator

Pre-registration: [`arm_a_prereg.md`](arm_a_prereg.md), including three recorded interruptions. Raw per-episode results are in `runs/arm_a/` (not in git), and the report was computed by `dreamdesk/report_arm_a.py` on 2026-11-03.

## Result
**Gate passed.** On 100 held-out sums in the real calculator, the cloned policy succeeded a median of 98% of the time, across 5 seeds. The random player succeeded 0% of the time on the same sums.

| Measure | Median | p10 | p90 | By seed |
|---|---|---|---|---|
| Held-out success, % | 98.0 | 96.4 | 100.0 | 97, 96, 100, 98, 100 |
| Train-side success, % (50 sums) | 100.0 | 96.0 | 100.0 | 96, 100, 100, 96, 100 |
| Random player, held-out, % | 0.0 | | | |
| Offline held-out press accuracy, % (256 presses) | 99.6 | 99.6 | 100.0 | |

| Held-out success by op | Median % | p10 | p90 | Sums per seed |
|---|---|---|---|---|
| `+` | 97.1 | 91.8 | 100.0 | 34 |
| `*` | 100.0 | 98.1 | 100.0 | 31 |
| `-` | 100.0 | 97.1 | 100.0 | 35 |

- **Data:** 2,296 training presses from expert episodes, out of 1,547 collected episodes. That's fewer than the pre-registered "about 1,900", because collection stopped early.
- **Training:** best epochs were 150, 150, 150, 9 and 150. Four seeds were still improving at the 150-epoch limit.
- **Errors:** no episode errored or closed the app.

## How it failed
9 of 500 held-out episodes failed.

| Seed | Goal | Pressed | What went wrong |
|---|---|---|---|
| 0 | `7×28` | `7×82…` | Digits in the wrong order |
| 0 | `3−45` | `3−4=…` | Pressed `=` one digit early |
| 0 | `9+87` | `9+77…` | Wrong digit |
| 1 | `5+12` | `5+11…` | Repeated a digit |
| 1 | `5+2` | `5+22…` | Repeated the last digit instead of pressing `=` |
| 1 | `92+57` | `92+57==…` | **Every press was correct, but success wasn't detected** (see below) |
| 1 | `9+2` | `9+22…` | Repeated the last digit instead of pressing `=` |
| 3 | `1+7` | `1+77…` | Repeated the last digit instead of pressing `=` |
| 3 | `91−75` | `91−755…` | Repeated the last digit instead of pressing `=` |

- **Most mistakes come at the end of a number:** the policy loses track of whether the last digit is already typed, and repeats it. 5 of 9 failures are this. A likely cause is how the display text is encoded: characters are summed with their positions, which makes the length of the display hard to read exactly. That isn't confirmed.
- **No recovery, as predicted:** 0 episodes won after a wrong press. The expert data contains no mistakes, so the policy never saw how to recover.
- **One probable environment miss:** for `92+57`, the policy pressed exactly the expert's sequence, but the episode didn't end with success after `=`. It then pressed `=` again, which changed the screen. A likely cause is that the result appeared after the environment stopped waiting, so the success check read the screen too early. That would make the true held-out success slightly higher than reported. It's not confirmed, and the result stands as measured.

## Against the prediction
The pre-registration predicted median held-out success above 80%, failures on unseen op and last-digit pairs, and no recovery after a wrong press.
- **Above 80%:** right.
- **No recovery:** right.
- **Where it fails:** partly wrong. The failures cluster on deciding when a number ends, not on any particular op or last digit.

## What this means
- The pipeline works end to end: data, training, real-app testing and the report.
- The calculator is too easy to separate methods. A copying policy already reaches 98%, so it's only a pipeline check, not a research result. The next stages need harder, multi-step apps.
- Two things to carry forward:
    - Check success after the screen has fully settled, before trusting a failure.
    - Recovery from mistakes is exactly what RL and the dream are supposed to add.
