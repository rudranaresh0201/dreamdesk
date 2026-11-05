# DreamDesk: openpilot for computers

## One line
Drop a small agent into an app it has never seen. With no instructions, no LLM and no human, it explores, builds a simulator of the app in its head, practises inside it, then does real tasks.

**Headline metric:** real steps and minutes of practice needed to reach a given success rate on an app kept out of training.

## Problem statement
**GUI agents are increasingly trained inside learned world models, but nobody measures how much those models fool them, and every current system needs huge pretrained models and data it didn't collect itself.**

What the current work shows. Each point is from the sources below; some were read only as abstracts or summaries.

| Gap | Evidence |
|---|---|
| **Imagined success is never checked against real success.** Rewards in the dream come from judges, not from the real app | WM-R1 scores simulated rollouts with an LLM judge. Imagine to Act's multi-step rollouts are judged by a vision-language model and not compared with real ones. DynaWeb uses self-assessed rewards with no uncertainty estimate |
| **Dreams decay over longer rollouts, and the harm is known but not measured** | Imagine to Act reports fidelity dropping with rollout length. GUI-CC finds world models lose consistency over multiple steps. The mobile world-model study found imagined data helped only at first. DynaWeb caps rollouts at 5 steps |
| **The world model is pretrained on fixed data, not built by the agent** | WM-R1 uses a frozen Code2World-8B. CUWM learns from 2,876 offline Office transitions. None explore a new app themselves to build its model |
| **Everything needs large models and big GPUs** | WM-R1: 3–7B policies and an 8B world model on an H200. Imagine to Act: 4–9B image models. ScreenExplorer: 3B policy, about 26 hours on an A100 |
| **Robotics already has a tested fix that hasn't been tried here** | RWM-U and MOPO-PPO use ensemble uncertainty to stop policies exploiting model errors on real robots |

**So the open problem is:** can a small agent build its own world model of an app by exploring, practise inside it without being fooled, and show, measured in the real app, how much the dream overstates success and how much uncertainty fixes it?

## Research questions
1. Can task-free exploration build a useful simulator of a real app in a few thousand real steps?
2. How much does imagined success overstate real success, and do uncertainty penalties and truncated rollouts close the gap?
3. Does experience from many apps make a new app measurably faster to learn?
4. Does a neural dream beat a plain graph of visited screens, and when?

These are untested and may be wrong. A clean negative result still counts.

## How this relates to our other work
| | `computer-use` | `everday-habit` experiments | DreamDesk |
|---|---|---|---|
| **Question** | Where should the agent click: tree or vision? | What do real desktops actually do? | Can an agent teach itself a new app? |
| **Who decides** | An LLM | n/a | A small trained policy |
| **Used here for** | The grounder can fill tree holes after v1 | Sandbox, timing, element identity and world-model design | |

Get the mentor's written OK before publishing anything derived from `everday-habit`.

## Cost: $0
| Job | Free approach |
|---|---|
| Decisions, rewards | Small local policy; code-checked rewards and goal matching. No LLM at train or run time |
| Tasks at scale | Hindsight: any reached screen becomes a practice goal. Hand-written checkers only for the test set |
| Many apps | Installed apps, tarball installs without root, and web apps generated from code templates |
| Real data | Laptop in sandboxes. Native: measured about 4 steps/s with 3 workers. Web: about 88 steps/s per headless Chrome on a tiny page |
| Training | Kaggle T4. About 30 hours a week is commonly reported, not guaranteed |
| Optional text goals | Small local embedding model on CPU, only if goal-by-example works first |

## What the research says
"Full paper" means the paper's full text went through a fetch-and-summarize tool. Everything else is from an abstract or search summary, and the summaries can miss details.

| Work | Covers | Leaves open |
|---|---|---|
| comma, Learning to Drive from a World Model | Policy trained in a world model and shipped | Driving, with fleet data we don't have |
| WM-R1 (full paper) | Mobile policy trained in Code2World-8B on an H200 GPU; AndroidWorld 39.8 vs 30.8 | Pretrained world model, no uncertainty estimate, no imagined-versus-real comparison, no per-app adaptation |
| CUWM (full paper) | Office world model from 2,876 samples | Test-time search only, unseen apps not tested |
| ScreenExplorer (full paper) | Task-free curiosity on a real Linux desktop; 3B model, about 26 hours on an A100 | No imagined policy training reported; warns of the noisy-TV trap |
| UIExplorer | Exploration benchmark on GitLab; reaches 77.2% of a human's coverage at 2,000 steps with structured input | Exploration only, no world model mentioned. Its coverage metric is worth borrowing |
| Imagine to Act (full paper) | Agents trained on image-editing world-model data | Large models, one training run per configuration, rollouts not checked against reality |
| CoAdapt-GUI | Test-time adaptation on unseen mobile apps | Large vision-language model, no world model mentioned |
| WildAWM, MAI-Gym | Synthetic worlds for training, with transfer | Generated environments, not simulators learned by self-exploration |
| How Mobile World Model Guides GUI Agents? | Imagined data helped only at first | Warns our core approach can fail |
| LEXA, Plan2Explore | Explorer and achiever in a world model, zero-shot goals | Robotics and images, not GUIs. This is our recipe to transfer |
| GUI testing studies | Curiosity and Go-Explore-style exploration | **Random testers are often strong**, so curiosity must prove itself |

**Gap:** searches found nothing combining task-free self-exploration, a self-built app simulator, a small non-LLM policy, and measured dream exploitation on real desktop apps. That doesn't prove none exists. Re-check before each gate.

**Design consequence:** apps are nearly deterministic, so explore-then-graph-search may match a neural dream on anything already visited. The neural model must earn its place on **parametric and unvisited situations**, such as sums or text never seen. Graph search is a required baseline, and "the graph wins" is a publishable result.

## System
**Findings reused from `everday-habit`**
- Web and native controls look alike once Chromium accessibility is on: train across both. Needs `--force-renderer-accessibility` and `--password-store=basic`.
- Identify elements by role and name, never position: only `role_position` ever matched a wrong element.
- Changes are 1–3 nodes or 68–152 on Linux: use a small-edit path and a screen-switch path in the world model.
- Real settle is about 85–225 ms against our step of about 600 ms: try waiting on events, then verify no labels shift.
- Timer effects arrive late (tooltips about 600 ms, autosave 3–4 s): record them and report their effect on the model.
- Without `XDG_SESSION_TYPE=x11` Chrome and VS Code escape to the real desktop, and portal access pulls file dialogs there too. The sandbox handles both.

**Pipeline**
```
Unseen app in sandbox
  -> Explorer: go where the 5 world models disagree            (Plan2Explore)
  -> Real transitions -> world-model ensemble
  -> Dream: thousands of batched rollouts                      (Dyna, PPO)
  -> Achiever: reach self-chosen goals                         (LEXA, hindsight replay)
  -> Cut or penalize rollouts where models disagree            (MOPO, truncation)
  -> Real test on code-checked tasks -> new data -> repeat
```
- **Observation:** element tokens with role, name, text, states, depth and box. Boxes are recorded for the playable dream, not needed by the policy.
- **Actions:** press, focus, set text from a small vocabulary, scroll. Discrete only; drag and canvases are out for v1.
- **World model:** predicts element edits, appearing and vanishing elements, and screen switches. It does not regenerate the whole tree.
- **Goals:** a target set of elements from a reached screen. Text goals only as a later add-on.
- **Noisy-TV check:** apps with constantly changing elements, such as clocks, test whether curiosity gets stuck.

## Strategy: learn on the web, prove it on the desktop
Headless Chrome is about 50× faster per step than a native desktop app on a tiny test page (see "Measured so far"). So:
- **Web apps are the fast training ground:** build experience across many generated and open-source web apps, cheaply.
- **Native desktop apps are the hard test:** real steps are slow there, which is exactly where a dream should pay off. Held-out test apps include native apps the agent never trained on.
- **Shared format:** the DevTools tree and AT-SPI name roles differently (`textbox` against `text`), so both map to one role table in the backend.
- **Honest catch:** on web apps, reality is already fast, so the dream's speed advantage is smaller. Its value there has to come from safety and from exploring ahead. Report dream speed against the same kind of app.

## Experiments
Pre-register each one. Use at least 5 seeds, report median with p10 and p90, and test only in real apps. Freeze held-out apps before any training on them.

| Arm | Method | Tests |
|---|---|---|
| Random | Random valid actions | Exploration floor |
| Novelty | Count-based, Go-Explore style | Strong non-neural explorer |
| Curious | Ensemble disagreement | Our explorer |
| Graph | Exploration plus graph search | Non-neural planner to beat |
| Real PPO | PPO on real apps only | Real-steps comparison |
| Dream | PPO in dream, no uncertainty handling | Should show exploitation |
| Dream + penalty / truncation | MOPO style / rollout cutting | The fix |
| Dyna | Best fix plus real data loop | Full system |
| Prior vs scratch | Many-app model against a fresh model on a new app | The transfer claim |

**Metrics:** real success against real steps, exploitation gap, new states per 1,000 steps, changed-element accuracy against horizon on unvisited transitions, dream steps per second.

## Roadmap
Estimates at 12–15 hours a week. Every level ships something even if the next fails.

| Stage | Weeks | Build | Gate | If it fails |
|---|---|---|---|---|
| 0 | Now | Finish calculator run, Arm A, read remaining papers | Pipeline works end to end; no paper does this exact study | Reproduce the paper and test what it left out |
| 1 | 1–2 | Sandbox, recorder v2, app survey | **All escape tests pass**; at least 12 usable apps | Fewer apps; nothing runs outside the sandbox |
| 2 | 3 | Explorers: Random and Novelty (`experiments/explore_prereg.md`). Curious moves to Stage 3, because it needs the world-model ensemble | Novelty beats Random on distinct screens in at least 6 of 10 apps. **Failed, 4 of 10** (`experiments/explore_results.md`) | Use the best simple explorer and report it. Neither was clearly best, so Stage 3 trains on all 100 runs |
| 3 (Level 1) | 4–5 | World model, playable dream | Beats Copy and Memo on unvisited transitions at horizon 5, and runs at least 100× real speed. **Passed: 6 of 6 gate apps, +0.221 vs Memo [+0.201, +0.239], 153×** (`experiments/world_model_results.md`) | Publish environment and exploration benchmark |
| 4 (Level 2) | 6–7 | Goal agent, all dream arms | Results either way; Dream beating Graph on parametric tasks is the hoped result. **H1 failed:** Dream beat Random pooled (+5.4 [+0.8, +9.8]) but not on never-practised goals (−0.2 [−5.1, +4.8]); Graph beat Dream by 20.9 points; dream−real gap −2.3 pooled (`experiments/stage4_results.md`) | Publish the exploitation or graph result |
| 5 (Level 3) | 8–10 | 20–30 apps, template web apps, prior vs scratch | Prior needs fewer real steps than scratch on held-out apps, with intervals not overlapping | Paper stops at Level 2 |
| 6 (Level 4) | 11 | Zero and low-practice test | Measured either way | State the limit plainly |
| 7 | 12 | Paper, repo, videos | Public release | n/a |

**Demos:** playable dream at Stage 3, seed wall at Stage 2 onward, "wins in the dream, fails for real" at Stage 4, learning timelapse at Stage 5.

**Teaching:** each stage teaches its concept using these runs, with explain-it-back checks. CartPole PPO gets finished before Stage 4.

## Safety and limits
- **Sandbox blocker:** no agent acts in any app but the calculator outside `scripts/sandbox.sh`. `tests/check_sandbox.py` must pass first.
- **Never exposed to agents:** terminals, Disks, Update Manager, keyring, online accounts, email, Discord.
- **Claims:** tree-only view, discrete actions, small models, one Linux version. No fleet-scale data, so comma is an analogy for the method, not a claim of equal scale. Never say "any app".

## Risks
| Risk | Response |
|---|---|
| Someone publishes this first | The field moves weekly. Re-check before each gate, and post early |
| Graph search matches the dream | Test parametric tasks; report it if it still wins |
| Random explores as well as curiosity | Novelty and Random are baselines; use whatever wins. Stage 2 already found random as good as novelty on screens |
| Transfer across apps doesn't appear | Per-app self-teaching still ships at Levels 1–2 |
| Laptop too slow for many apps | Measure in the survey; cut slow apps such as LibreOffice |
| Dream isn't much faster than reality | Stage 3 gate requires at least 100× native speed; report web separately |
| Web-to-desktop transfer fails | Held-out native tests would show it; train on some native apps too |

## Measured so far
Calculator probe in `spikes/`, on a private display, n=39 steps, 5 resets.

| What | Median | p10 | p90 |
|---|---|---|---|
| Time until a press appears in the tree | about 360 ms | | |
| Tree read (107 nodes) | 67 ms | 60 | 89 |
| Full step (act, 0.45 s settle, read) | 555 ms | 524 | 629 |
| Nodes changed per press | 1 | 1 | 1 |
| Fresh app start (reset) | 524 ms | 452 | 628 |

Environment check on the calculator (`tests/check_calculator.py`, 2026-11-02):

| Check | Result |
|---|---|
| Scripted expert on random tasks | 25/25 |
| Step, waiting only until the tree settles | median 536 ms, p10 495, p90 612, n=146 |
| Reset by relaunching the app | median 563 ms, p10 548, p90 658, n=25 |
| Elements changed per press | median 2, p90 7, max 7 |
| Start state identical across 5 resets | Yes |
| Typing the answer without the sum counts as success | No |
| Random agent, tasks of the form `d + d` | 0/10, and it closed the app in 1 episode |

Arm A, behaviour cloning on the calculator (`experiments/arm_a_results.md`, 2026-11-03): **gate passed**. Held-out success was a median of 98% (p10 96.4, p90 100) across 5 seeds, against 0% for a random player on the same 100 sums. It never recovered after a wrong press, and most failures were repeating the last digit. One failure was probably the environment checking success before the screen settled.

Recorder v2 (2026-11-03, all in the sandbox): elements now carry states and boxes, and the agent can press, focus, and type a word from a small vocabulary. After a change, the environment waits for 250 ms with no further change (40 ms on web) before reading the result, which fixes the early read seen in Arm A.

| Check | Result |
|---|---|
| Text editor (`tests/check_editor.py`) | Focuses the document, types "hello world", success read from the real app. Reads take 112 ms with states and boxes, against 82 ms without |
| Web (`tests/check_web.py`) | Typing works and sets the focused state. Step median 54 ms, about 18 steps/s, slower than before because of the settle wait and state reading |
| Calculator (`tests/check_calculator.py`) | Expert 25/25, start state identical, cheat still blocked. Step median 825 ms (p10 742, p90 1,019), up from 536; reset 976 ms, up from 563 |

The settle wait costs about half again per desktop step. Whether 250 ms can be shortened without missing late updates is untested.

Sandbox check (`tests/check_sandbox.py`, 2026-11-02): all escape checks held, with controls showing the probes detect access outside the sandbox. Blocked: real home and files, real drives, network, real session and system buses, real desktop display, real processes. The calculator completes a sum inside, and the file manager shows no drives or Unmount buttons.

App survey inside the sandbox (`scripts/survey_apps.sh`, 2026-11-02), reads only, with collection running at the same time. "Starts" doesn't yet mean an agent can do useful work in it; pressing isn't tested yet.

| App | Nodes | Read, ms | Pressable |
|---|---|---|---|
| Calculator | 107 | 104 | 32 |
| Text editor | 85 | 75 | 7 |
| Files | 146 | 126 | 12 |
| Characters | 144 | 163 | 5 |
| Clocks | 92 | 88 | 10 |
| Disk usage | 60 | 58 | 4 |
| Font viewer | 67 | 75 | 5 |
| Image viewer | 57 | 56 | 8 |
| Logs | 73 | 65 | 9 |
| Resources | 120 | 116 | 8 |
| LibreOffice Writer | 2,220 | 776 | 1,351 |
| LibreOffice Impress | 2,064 | 691 | 1,114 |
| LibreOffice Draw | 2,007 | 747 | 1,151 |
| LibreOffice Math | 598 | 174 | 254 |

- 14 real apps start and read. Four are LibreOffice, whose counts include closed menu items.
- **Don't work yet:** Settings (doesn't start), LibreOffice Calc and Papers (survey times out, cause unconfirmed), Help (needs WebKit's own sandbox disabled, so it's left out).
- **Noisy-TV candidate:** Resources changed 12 elements in 5 idle seconds; every other working app changed 0.
- **Chrome through AT-SPI:** doesn't register inside the sandbox, cause unknown. Web apps use DevTools instead.

Headless Chrome through DevTools (`dreamdesk/spike_cdp.py`, in the sandbox, 2026-11-02): tiny todo page, one environment, 10 episodes of 20 presses, with collection running at the same time.

| What | Result |
|---|---|
| Step | median 11.3 ms, p90 17.4, n=200 |
| Steps per second | about 88 |
| Full tree read | median 3.1 ms, 18–170 nodes |
| Reset by reloading the page | median 26 ms |
| Cold start | 921 ms |
| Press produced no change | 0 of 200 |

Web backend through the shared environment (`tests/check_web.py`, same page, in the sandbox, 2026-11-02), waiting until the page settles: step median 17.0 ms, p90 20.3, n=100, about 59 steps/s. Reset median 36.9 ms, n=5, with an identical start state each time.

This is a best case: a tiny page with no network, and the spike's steps only wait for the first change. Real web apps will be slower. Chrome runs with `--no-sandbox` because its own sandbox can't start inside ours, so bubblewrap is the only isolation layer for it.

### Stage 2: novelty vs random exploration
100 runs, 10 apps × 2 explorers × 5 seeds × 500 steps, in the sandbox, 2026-11-03 to 04 (`experiments/explore_results.md`).
- **Gate failed:** novelty's median count of distinct screens was higher than random's in 4 of 10 apps. It was lower in 3 and tied in 3, with seeds overlapping in every app.
- **Novelty found more distinct transitions in 7 of 10 apps.** This was a secondary measure.
- Disk-usage and font-viewer saturate in 500 steps.
- Median step 884 ms.
- Files had 365 typing errors, from typing into an unnamed field that refuses text. Fix this before Stage 3.

### Stage 3: world model
5-member ensemble, 2-layer transformer, trained on seeds 0–2 of all 100 Stage 2 runs. Tested once on seed 4, 2026-11-05 (`experiments/world_model_results.md`).
- **Gate passed:** at horizon 5 on unvisited windows, it beat Copy and Memo in 6 of 6 gate apps. The equal-weight mean gain over Memo was +0.221, with a 95% interval of [+0.201, +0.239]. The slowest app ran at 173 predictions/s, 153× a real step.
- The ensemble beat every single member in every gate app.
- Memo won only in image-viewer, on all and on visited windows.
- Disagreement flags wrong predictions only moderately: median AUROC 0.665, above 0.7 in 4 of 10 apps. Check it against simpler uncertainty signals before Stage 4 relies on it.
- Thresholds 0.7/0.7 sit at the grid's edge.

### Stage 4: policy trained in the dream
PPO achiever, trained only in the Stage 3 dream (3 seeds × Dream and Penalty arms, 1,500 iterations). Tested once on 294 test-seed goals, 2026-11-06 (`experiments/stage4_results.md`).
- **H1 failed.** Dream beat Random by +5.4 points pooled, but by −0.2 [−5.1, +4.8] on the 221 goals no Dream seed practised. On practised goals: 86% vs 64%.
- **The dream mostly didn't lie:** dream vs real success was −2.3 points pooled. Per app it ranged −19 to +20, and only disk-usage over-promised (20% vs 0%).
- **The policy didn't generalise:** it learned the goals it practised, not a goal-reaching skill.
- **Graph planning reached 48% of never-practised goals,** double the Dream policy. Next: plan inside the world model instead of a learned policy (needs its own prereg).
- **The disagreement penalty cost 2.5 points** [−4.6, −0.3] (Clocks −8, Files −14), because there was little exploitation to prevent.

## Open checks
- Read UIExplorer, CoAdapt-GUI, WildAWM and MAI-Gym in full; only abstracts so far.
- Whether Kaggle allows headless browsers: no source found. Test it directly, since web collection could then run there.
- Real web app speed: test on real open-source apps with waiting until the page settles.
- Kaggle quota: not officially fixed; about 30 GPU-hours a week as commonly reported.

## Sources
- comma: https://arxiv.org/abs/2504.19077 and https://blog.comma.ai/011release/
- WM-R1: https://arxiv.org/html/2608.27508
- CUWM: https://arxiv.org/html/2602.17365v1
- ScreenExplorer: https://arxiv.org/html/2505.19095
- UIExplorer: https://arxiv.org/abs/2506.17779
- Imagine to Act: https://arxiv.org/html/2610.05861
- CoAdapt-GUI: https://arxiv.org/abs/2608.11588
- WildAWM: https://arxiv.org/abs/2610.26828
- MAI-Gym: https://arxiv.org/abs/2610.20939
- Mobile world model study: https://arxiv.org/abs/2605.10347
- DynaWeb: https://arxiv.org/html/2601.22149v1
- GUI-CC: https://arxiv.org/html/2609.00048
- Decision-value paper: https://arxiv.org/html/2610.24372
- RWM-U and MOPO-PPO: https://arxiv.org/abs/2504.16680
- Adaptive rollout truncation: https://arxiv.org/html/2609.21482
- LEXA: https://arxiv.org/abs/2110.09514
- Plan2Explore: https://arxiv.org/abs/2005.05960
- Web GUI testing study: https://arxiv.org/abs/2606.16650
- Kaggle quota summary: https://gpuperhour.com/blog/free-cloud-gpus-and-credits
