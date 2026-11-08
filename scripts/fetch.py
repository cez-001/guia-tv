#!/usr/bin/env python3
"""Vai buscar a programação (via tv_grab_pt_vodafone, do projeto XMLTV) e gera data/epg.json."""
import json, os, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

GRAB = "tv_grab_pt_vodafone"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "epg.json")
LISBON = ZoneInfo("Europe/Lisbon")


def run(args):
    r = subprocess.run([GRAB, *args], capture_output=True, text=True, timeout=3000)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"Erro ao executar {GRAB} {' '.join(args)}:\n{r.stderr[-2000:]}")
    return r.stdout


def ts(s):
    s = s.strip()
    try:
        return int(datetime.strptime(s, "%Y%m%d%H%M%S %z").timestamp())
    except ValueError:
        return int(datetime.strptime(s[:14], "%Y%m%d%H%M%S").replace(tzinfo=LISBON).timestamp())


def main():
    cfg = os.path.join(tempfile.mkdtemp(), "grab.conf")
    open(cfg, "w").close()
    ids = [c.get("id") for c in ET.fromstring(run(["--config-file", cfg, "--list-channels"])).iter("channel")]
    if not ids:
        sys.exit("A lista de canais veio vazia.")
    with open(cfg, "w") as f:
        f.write("".join(f"channel={i}\n" for i in ids))

    root = ET.fromstring(run(["--config-file", cfg, "--days", "7", "--quiet"]))
    channels, progs = {}, {}
    for c in root.iter("channel"):
        icon = c.find("icon")
        channels[c.get("id")] = {
            "id": c.get("id"),
            "name": (c.findtext("display-name") or c.get("id")).strip(),
            "icon": icon.get("src") if icon is not None else "",
        }
    cutoff = datetime.now(timezone.utc).timestamp() - 3 * 3600
    for p in root.iter("programme"):
        try:
            s, e = ts(p.get("start")), ts(p.get("stop"))
        except (TypeError, ValueError):
            continue
        if e < cutoff:
            continue
        progs.setdefault(p.get("channel"), []).append(
            [s, e, (p.findtext("title") or "").strip(), (p.findtext("desc") or "").strip()[:300]]
        )
    for k in progs:
        progs[k].sort()
    out = {
        "generated": int(datetime.now(timezone.utc).timestamp()),
        "channels": [channels[i] for i in channels if i in progs],
        "programmes": progs,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out['channels'])} canais, {sum(map(len, progs.values()))} programas")


if __name__ == "__main__":
    main()
