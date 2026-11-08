"""Notas do IMDb a partir dos ficheiros públicos (datasets.imdbws.com, uso pessoal e não comercial).

Procura cada filme pelo título (original, internacional ou português/brasileiro) e pelo ano.
"""
import os, re, subprocess, unicodedata
from collections import defaultdict

BASE = os.environ.get("IMDB_BASE", "https://datasets.imdbws.com/")


def norm(s):
    s = re.sub(r"\([^)]*\)", " ", s or "")          # tira "(V.O.)", "(V.P.)", etc.
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("&", " e ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _stream(name, pattern=None):
    grep = f" | grep -P '{pattern}'" if pattern else ""
    cmd = f"set -o pipefail; curl -sfL '{BASE}{name}' | gunzip -c{grep}"
    p = subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    n = 0
    for line in p.stdout:
        n += 1
        yield line.rstrip("\n").split("\t")
    p.wait()
    if n == 0:
        raise RuntimeError(f"não consegui ler {name} (código {p.returncode})")


def ratings_for(films):
    """films: conjunto de (título, ano|None). Devolve {(título, ano): (nota, votos, tconst)}."""
    wanted = {norm(t) for t, _ in films}
    wanted.discard("")
    idx = defaultdict(set)   # título normalizado -> tconst
    year = {}                # tconst -> ano de estreia

    for r in _stream("title.basics.tsv.gz", r"\t(movie|tvMovie)\t"):
        if len(r) < 6 or r[1] not in ("movie", "tvMovie"):
            continue
        year[r[0]] = int(r[5]) if r[5].isdigit() else None
        for t in (r[2], r[3]):
            n = norm(t)
            if n in wanted:
                idx[n].add(r[0])

    for r in _stream("title.akas.tsv.gz", r"\t(PT|BR)\t"):
        if len(r) >= 4 and r[3] in ("PT", "BR") and r[0] in year:
            n = norm(r[2])
            if n in wanted:
                idx[n].add(r[0])

    need = set().union(*idx.values()) if idx else set()
    rating = {}
    for r in _stream("title.ratings.tsv.gz"):
        if r[0] in need:
            try:
                rating[r[0]] = (float(r[1]), int(r[2]))
            except ValueError:
                pass

    out = {}
    for t, y in films:
        cands = [c for c in idx.get(norm(t), ()) if c in rating]
        if y:
            cands = [c for c in cands if year.get(c) and abs(year[c] - y) <= 1]
            min_votes = 200
        else:
            min_votes = 20000   # sem ano, só aceitamos filmes muito conhecidos
        cands = [c for c in cands if rating[c][1] >= min_votes]
        if cands:
            best = max(cands, key=lambda c: rating[c][1])
            out[(t, y)] = (rating[best][0], rating[best][1], best)
    return out
