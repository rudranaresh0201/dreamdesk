# Stage 2 pre-registration: do explorers find more of an app than random pressing?

Written 2026-11-03, before the measured runs. A pilot of 120 steps per run on Clocks and Text Editor (`data/pilot/`) was used only to find bugs. It showed the first screen definition counted window titles holding typed text, so the definition below was fixed after the pilot and before any measured run. Pilot numbers aren't part of the results.

## Question
In apps it has never seen, with no task and no reward, does count-based novelty discover more distinct screens than pressing at random?

The literature warns that random testers are often strong, so this is a real test, not a formality.

## Apps
10 apps in the sandbox, from `dreamdesk/apps.py`: calculator, text-editor, files, characters, clocks, disk-usage, font-viewer, image-viewer, logs, resources.
- LibreOffice is left out: its reads take about 0.8 s even before states and boxes.
- Resources changes by itself while idle: it's the noisy-TV check, reported separately as well as in the totals.

## Explorers
- **Random:** every usable action equally likely.
- **Novelty:** in each screen, the action tried least often there, with ties broken at random.

Curiosity by ensemble disagreement needs the world model, so it moves to Stage 3.

Both explorers use the same rules:
- **Actions:** press, focus, or type one of "hello", "42" or "test", in the order given by `DeskEnv.actions()`.
- **Excluded:** window controls, quitting, killing processes, and elements whose states say they're disabled.
- **Episodes:** the app is relaunched every 30 steps.
- **Budget:** 500 real steps per run.
- **Seeds:** 5 per app and explorer. That's 100 runs.

## Measures
- **Screen:** the set of interactive elements, meaning pressable or editable, each as role, name and the states checked, pressed, expanded, selected and modal, plus which kinds of dialog, menu or similar container are open. Text contents and window titles are left out. This is `screen_key` in `dreamdesk/explore.py`. Screens are recomputed from saved snapshots by `dreamdesk/coverage.py`.
- **Primary:** distinct screens after 500 steps.
- **Secondary:**
    - distinct pressable or editable elements discovered
    - distinct transitions (screen, action, next screen)
    - the curve at 100, 250 and 500 steps
    - share of actions that changed nothing
    - errors and step time

## Comparison and gate
- For each app, compare the median of the primary measure across 5 seeds for novelty and for random.
- **Gate:** novelty's median is higher in a majority of apps, at least 6 of 10, as `PLAN.md` requires.
- Also reported: for each app, whether every novelty seed beats every random seed, so it's clear where the difference is consistent.

## Prediction
Novelty will win in most apps, because random keeps repeating the same few presses. The gap will be smallest in apps with few actions, such as disk-usage and font-viewer. In Resources, novelty may chase screens that change by themselves.

## Interruptions
Runs are resumed with `scripts/explore_all.sh`. A finished run is kept. An unfinished run is moved to `data/explore/interrupted/` and redone from its first step with the same seed. Every interruption gets recorded here.
