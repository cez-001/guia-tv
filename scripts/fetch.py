#!/usr/bin/env python3
"""Vai buscar a programação dos canais em canais.txt (via tv_grab_pt_vodafone, do XMLTV) e gera data/epg.json."""
import json, os, re, subprocess, sys, tempfile, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

GRAB = "tv_grab_pt_vodafone"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "epg.json")
WANTED = os.path.join(HERE, "..", "canais.txt")
LISBON = ZoneInfo("Europe/Lisbon")


def run(args):
    r = subprocess.run([GRAB, *args], capture_output=True, text=True, timeout=3000)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"Erro ao executar {GRAB} {' '.join(args)}:\n{r.stderr[-2000:]}")
    return r.stdout


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ts(s):
    s = s.strip()
    try:
        return int(datetime.strptime(s, "%Y%m%d%H%M%S %z").timestamp())
    except ValueError:
        return int(datetime.strptime(s[:14], "%Y%m%d%H%M%S").replace(tzinfo=LISBON).timestamp())


def pick_channels(available, wanted):
    """available: [(id, name)]; wanted: [str]. Devolve (ids escolhidos, nomes não encontrados)."""
    items = []
    for cid, name in available:
        n = norm(name)
        items.append((cid, n, n.replace(" ", ""), re.sub(r" hd$", "", n).replace(" ", "")))
    chosen, missing = [], []
    for line in wanted:
        n = norm(re.sub(r"^\d+\s*[.)\-]\s*", "", line))
        if not n:
            continue
        ns = n.replace(" ", "")
        m = next((x for x in items if x[1] == n), None) or next((x for x in items if x[2] == ns), None) \
            or next((x for x in items if x[3] == ns), None)
        if not m and len(ns) > 4:
            cand = [x for x in items if ns in x[2]]
            if len(cand) == 1:
                m = cand[0]
        if m:
            if m[0] not in chosen:
                chosen.append(m[0])
        else:
            missing.append(line.strip())
    return chosen, missing


def main():
    cfg = os.path.join(tempfile.mkdtemp(), "grab.conf")
    open(cfg, "w").close()
    avail = [(c.get("id"), (c.findtext("display-name") or c.get("id")).strip())
             for c in ET.fromstring(run(["--config-file", cfg, "--list-channels"])).iter("channel")]
    if not avail:
        sys.exit("A lista de canais veio vazia.")
    print(f"{len(avail)} canais disponíveis na fonte.")

    wanted = [l.strip() for l in open(WANTED, encoding="utf-8")] if os.path.exists(WANTED) else []
    ids, missing = pick_channels(avail, wanted)
    if missing:
        print("Não encontrei:", ", ".join(missing))
        print("::group::Canais disponíveis na fonte")
        print("\n".join(sorted(n for _, n in avail)))
        print("::endgroup::")
    if not ids:
        print("Nenhum canal de canais.txt reconhecido; vou buscar todos.")
        ids = [i for i, _ in avail]
    print(f"A obter {len(ids)} canais...")

    with open(cfg, "w") as f:
        f.write("".join(f"channel={i}\n" for i in ids))

    root = ET.fromstring(run(["--config-file", cfg, "--days", "4", "--quiet"]))
    channels, progs = {}, {}
    for c in root.iter("channel"):
        icon = c.find("icon")
        src = icon.get("src") if icon is not None else ""
        src = re.sub(r"/width/\d+/height/\d+", "/width/240/height/150", src)
        channels[c.get("id")] = {
            "id": c.get("id"),
            "name": (c.findtext("display-name") or c.get("id")).strip(),
            "icon": src,
        }
    cutoff = datetime.now(timezone.utc).timestamp() - 8 * 3600
    films = set()
    for p in root.iter("programme"):
        try:
            s, e = ts(p.get("start")), ts(p.get("stop"))
        except (TypeError, ValueError):
            continue
        if e < cutoff:
            continue
        title = (p.findtext("title") or "").strip()
        info = {}
        y = re.match(r"\d{4}", (p.findtext("date") or "").strip())
        if y:
            info["y"] = int(y.group())
        cats = [c.text.strip() for c in p.findall("category") if c.text and c.text.strip()]
        if cats:
            info["g"] = ", ".join(cats[:2])
        is_ep = p.find("episode-num") is not None
        if not is_ep and "y" in info:
            info["f"] = 1                      # candidato a filme
            films.add((title, info["y"]))
        progs.setdefault(p.get("channel"), []).append(
            [s, e, title, (p.findtext("desc") or "").strip()[:320], info]
        )

    try:
        import imdb
        print(f"A procurar notas do IMDb para {len(films)} filmes...")
        found = imdb.ratings_for(films)
        for lst in progs.values():
            for pr in lst:
                k = (pr[2], pr[4].get("y"))
                if pr[4].get("f") and k in found:
                    pr[4]["r"], _, pr[4]["i"] = found[k]
        print(f"Notas encontradas: {len(found)} de {len(films)}")
    except Exception as ex:
        print("Sem notas do IMDb desta vez:", ex)

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
