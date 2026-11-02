"""Tries to reach real things and prints what it could reach, as JSON. Changes nothing outside --write-test.

Every value is True when the thing was REACHABLE. check_sandbox.py runs this inside the sandbox,
where all should be False, and outside it, to prove each probe can detect access at all.
"""
import glob
import json
import os
import socket
import subprocess
import sys


def can_read(path):
    try:
        with open(path, "rb") as f:
            f.read(1)
        return True
    except OSError:
        return False


def can_connect(family, address, timeout=3):
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect(address)
            return True
        except OSError:
            return False


def has_entries(path):
    try:
        return bool(os.listdir(path))
    except OSError:
        return False


def real_processes_visible(names):
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/comm") as f:
                if f.read().strip() in names:
                    return True
        except OSError:
            pass
    return False


def real_x_or_wayland(uid):
    paths = glob.glob(f"/run/user/{uid}/wayland-*") + [p for p in glob.glob("/tmp/.X11-unix/X*") if not p.endswith("X90")]
    abstract = any(can_connect(socket.AF_UNIX, f"\0/tmp/.X11-unix/X{n}") for n in (0, 1))
    return bool(paths) or abstract


def real_mounts_visible():
    """What GTK file pickers and file managers list: real drives and mounts."""
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    monitor = Gio.VolumeMonitor.get()
    return bool(monitor.get_volumes() or monitor.get_mounts() or monitor.get_connected_drives())


def main():
    canary, project_probe, real_home, uid = sys.argv[1:5]
    block_devices = glob.glob("/dev/nvme*") + glob.glob("/dev/sd?*")
    try:
        with open(project_probe, "x"):
            pass
        os.remove(project_probe)
        project_writable = True
    except OSError:
        project_writable = False

    result = {
        "canary_in_real_home": can_read(canary),
        "real_home_listing": has_entries(real_home),
        "project_writable": project_writable,
        "project_data_folder": has_entries(os.path.join(os.path.dirname(project_probe), "data")),
        "ssh_keys_folder": has_entries(os.path.join(real_home, ".ssh")),
        "media_drives": has_entries("/media") or has_entries("/run/media") or has_entries("/mnt"),
        "block_devices": bool(block_devices),
        "network_direct_ip": can_connect(socket.AF_INET, ("1.1.1.1", 53)),
        "real_session_bus": os.path.exists(f"/run/user/{uid}/bus"),
        "system_bus": os.path.exists("/run/dbus/system_bus_socket"),
        "real_desktop_display": real_x_or_wayland(uid),
        "real_processes": real_processes_visible({"gnome-shell", "systemd", "dbus-broker", "dbus-daemon-real", "gdm3"}),
        "real_drives_in_gio": real_mounts_visible(),
    }
    print("PROBE " + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
