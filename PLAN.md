# DreamDesk: openpilot for computers

## One line
Drop a small agent into an app it has never seen. With no instructions, no LLM and no human, it explores, builds a simulator of the app in its head, practises inside it, then does real tasks.

**Headline metric:** real steps and minutes of practice needed to reach a given success rate on an app kept out of training.

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
| 2 | 3 | Explorers | Curious or Novelty beats Random on coverage in a majority of test apps | Use the best simple explorer and report it |
| 3 (Level 1) | 4–5 | World model, playable dream | Beats Copy and Memo on unvisited transitions at horizon 5, and runs at least 100× real speed | Publish environment and exploration benchmark |
| 4 (Level 2) | 6–7 | Goal agent, all dream arms | Results either way; Dream beating Graph on parametric tasks is the hoped result | Publish the exploitation or graph result |
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
| Random explores as well as curiosity | Novelty and Random are baselines; use whatever wins |
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
