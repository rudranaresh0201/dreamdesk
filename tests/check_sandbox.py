"""Proves the sandbox holds. Stage 1 gate: no agent touches another app until this passes.

Run from the repo root:  python3 tests/check_sandbox.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDBOX = str(ROOT / "scripts/sandbox.sh")
HOME = str(Path.home())
UID = str(os.getuid())
failures = []


def check(ok, message):
    print(f"  {'pass' if ok else 'FAIL'}: {message}", flush=True)
    if not ok:
        failures.append(message)


def probe_args(canary, project_probe):
    return ["tests/sandbox_probe.py", canary, project_probe, HOME, UID]


def parse(stdout):
    for line in stdout.splitlines():
        if line.startswith("PROBE "):
            return json.loads(line[6:])
    return None


fd, canary = tempfile.mkstemp(prefix=".dreamdesk-canary-", dir=HOME)
os.write(fd, b"secret")
os.close(fd)
project_probe = str(ROOT / f".sandbox-write-probe-{uuid.uuid4().hex}")
out = tempfile.mkdtemp(prefix="dreamdesk-out-")
try:
    print("Every probe, outside the sandbox (shows which ones can detect access):")
    outside = parse(subprocess.run([sys.executable, *probe_args(canary, project_probe)], cwd=ROOT, capture_output=True, text=True, timeout=60).stdout)
    print(f"  {outside}")
    check(outside is not None, "the probe runs outside the sandbox")
    outside = outside or {}
    for name in ("canary_in_real_home", "real_home_listing", "project_writable", "project_data_folder", "block_devices", "real_session_bus", "real_processes"):
        check(outside.get(name) is True, f"control: probe '{name}' does detect access outside")

    print("Every probe, inside the sandbox (all must be False):")
    inside_run = subprocess.run(["bash", SANDBOX, "/usr/bin/python3", *probe_args(canary, project_probe)], cwd=ROOT, capture_output=True, text=True, timeout=90)
    inside = parse(inside_run.stdout)
    check(inside is not None, f"the probe runs inside the sandbox (stdout: {inside_run.stdout[-200:]!r}, stderr: {inside_run.stderr[-200:]!r})")
    for name, reachable in (inside or {}).items():
        check(reachable is False, f"blocked: {name}")
    check(not os.path.exists(project_probe), "nothing the probe wrote reached the real project")

    print("Writing to the code folder from inside fails, and real code is unchanged:")
    before = (ROOT / "dreamdesk/core.py").read_bytes()
    run = subprocess.run(["bash", SANDBOX, "/usr/bin/bash", "-c", "echo x >> dreamdesk/core.py && echo WROTE; echo x > dreamdesk/new_file && echo WROTE"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    check("WROTE" not in run.stdout, "code folder is read-only inside")
    check((ROOT / "dreamdesk/core.py").read_bytes() == before and not (ROOT / "dreamdesk/new_file").exists(), "real code is unchanged")

    print("The --out folder is the only writable real path:")
    target = os.path.join(out, "written.txt")
    run = subprocess.run(["bash", SANDBOX, "--out", out, "/usr/bin/bash", "-c", f"echo ok > {target}"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    check(os.path.exists(target), "can write to --out")

    print("A real app runs inside and is usable:")
    script = "\n".join([
        "from dreamdesk.calculator import BLOCKED, ComputeTask, make_backend",
        "from dreamdesk.core import DeskEnv",
        "env = DeskEnv(make_backend(), blocked_names=BLOCKED)",
        "task = ComputeTask(7, '+', 8)",
        "env.reset(task)",
        "reward = 0",
        "for name in task.expert_presses():",
        "    options = [e.name for e in env.pressable()]",
        "    _, reward, _, _ = env.step(options.index(name))",
        "env.backend.stop()",
        "print('APP', reward)",
    ])
    run = subprocess.run(["bash", SANDBOX, "/usr/bin/python3", "-c", script], cwd=ROOT, capture_output=True, text=True, timeout=120)
    check("APP 1.0" in run.stdout, f"calculator completes 7+8 inside the sandbox (stdout: {run.stdout[-200:]!r})")

    print("The file manager shows no real drives, files or Unmount buttons:")
    script = "\n".join([
        "import time",
        "from dreamdesk.atspi_backend import AtspiBackend",
        "b = AtspiBackend(['nautilus', '--new-window'], 'nautilus', min_elements=10, start_timeout=30)",
        "b.start()",
        "time.sleep(3)",
        "names = [e.name + ' ' + e.text for e in b.read()]",
        "b.stop()",
        "words = ('Unmount', 'Eject', 'Documents', 'Downloads', 'dreamdesk-canary')",
        "print('NAUTILUS', len(names), sorted({w for n in names for w in words if w in n}))",
    ])
    run = subprocess.run(["bash", SANDBOX, "/usr/bin/python3", "-c", script], cwd=ROOT, capture_output=True, text=True, timeout=120)
    line = next((l for l in run.stdout.splitlines() if l.startswith("NAUTILUS")), "")
    check(line != "", f"nautilus starts in the sandbox (stdout: {run.stdout[-200:]!r})")
    if line:
        print(f"  {line}")
        check("Unmount" not in line and "Eject" not in line and "canary" not in line, "no Unmount, Eject or canary in nautilus")

    print("Nothing survives when the parent dies:")
    marker = f"98{uuid.uuid4().int % 10**8:08d}"
    proc = subprocess.Popen(["bash", SANDBOX, "/usr/bin/sleep", marker], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        time.sleep(0.2)
        if subprocess.run(["pgrep", "-f", f"sleep {marker}"], capture_output=True).stdout.strip():
            break
    started = bool(subprocess.run(["pgrep", "-f", f"sleep {marker}"], capture_output=True).stdout.strip())
    check(started, "control: the marker process was running")
    proc.kill()  # kills only bwrap's parent process, which this test started
    proc.wait()
    time.sleep(2)
    left = subprocess.run(["pgrep", "-f", f"sleep {marker}"], capture_output=True, text=True).stdout.split()
    check(not left, f"no process left behind ({left})")
finally:
    os.remove(canary)
    shutil.rmtree(out, ignore_errors=True)
    if os.path.exists(project_probe):
        os.remove(project_probe)

print(f"\nVERDICT: {'FAIL, ' + str(len(failures)) + ' failed' if failures else 'PASS, all checks held'}")
sys.exit(1 if failures else 0)
