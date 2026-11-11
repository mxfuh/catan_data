"""Catan (Städte & Ritter): board geometry and pre-game values for catan_data.xlsx.

The board description is a dict (JSON), e.g. extracted from a photo:

    {
      "hexes":   {"A1": ["ore", 10], ..., "C3": ["desert", null]},
      "harbors": [{"edge": "A1:NW-N", "type": "gen"}, ...],
      "players": {
        "yellow": {"buildings": [{"at": "B2:S", "type": "settlement"}, {"at": "D3:N", "type": "city"}],
                   "roads": ["B2:S-SW", "D3:N-NE"]},
        "blue": {...}, "red": {...}
      }
    }

Layout: 19 pointy-top hexes in horizontal rows A-E with 3-4-5-4-3 hexes, numbered left to right
(see ingest/README.md and the reference picture). A corner is "hex:corner" with corner N, NE, SE, S,
SW or NW; an edge (road, harbor) is "hex:corner-corner" with two neighbouring corners of that hex.
Any of the hexes touching a corner/edge may be used to name it. Player keys are colors (yellow = MF,
blue = PF, red = JHC) or the player codes themselves.

Rules (decided by Max, 2026-11-11):
- Production: sum of dice weights (pips) of the hexes next to a building. A city doubles clay and
  grain; on wood, sheep and ore it yields one resource plus one trade good (paper, fabric, coin).
- count_num: distinct numbers next to the player's buildings; count_res: distinct raw resources
  (trade goods not counted); sum: all eight production columns added up.
- port_X: a building stands on one of the two corners of a harbor of type X.
- prox_port_X: a corner of such a harbor can be reached with exactly one more road plus one
  settlement, continuing an existing own road. Not if another player blocks it (road on that edge,
  building on the corner or next to it). If port_X is 1, prox_port_X stays 0 (as in the existing data).
"""
import math

ROWS = "ABCDE"
ROW_LEN = [3, 4, 5, 4, 3]
HEXES = [f"{r}{i + 1}" for r, n in zip(ROWS, ROW_LEN) for i in range(n)]
CORNERS = ["N", "NE", "SE", "S", "SW", "NW"]
RESOURCES = ["wood", "clay", "sheep", "grain", "ore"]
GOODS = {"wood": "paper", "ore": "coin", "sheep": "fabric"}
PRODUCTION = RESOURCES + ["paper", "coin", "fabric"]
HARBOR_TYPES = RESOURCES + ["gen"]
PIPS = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}
CENTER = {"C3"}
SECOND_RING = {"B2", "B3", "C2", "C4", "D2", "D3"}
COLORS = {"yellow": "MF", "blue": "PF", "red": "JHC"}
PLAYERS = ["MF", "PF", "JHC"]
COLUMNS = (["desert", "sum", "count_num", "count_res"] + [f"p_sum_{p}" for p in PRODUCTION]
           + [f"port_{t}" for t in HARBOR_TYPES] + [f"prox_port_{t}" for t in HARBOR_TYPES])

# standard board contents, only used for plausibility warnings
STANDARD_RESOURCES = {"wood": 4, "clay": 3, "sheep": 4, "grain": 4, "ore": 3, "desert": 1}
STANDARD_NUMBERS = {2: 1, 3: 2, 4: 2, 5: 2, 6: 2, 8: 2, 9: 2, 10: 2, 11: 2, 12: 1}
STANDARD_HARBORS = {"gen": 4, "wood": 1, "clay": 1, "sheep": 1, "grain": 1, "ore": 1}

_S3 = math.sqrt(3)
_CORNER_OFFSET = {"N": (0, 1), "NE": (_S3 / 2, .5), "SE": (_S3 / 2, -.5),
                  "S": (0, -1), "SW": (-_S3 / 2, -.5), "NW": (-_S3 / 2, .5)}


class BoardError(ValueError):
    """The description can't be turned into a board (unknown hex, impossible corner, ...)."""


def hex_center(label):
    r = ROWS.index(label[0])
    i = int(label[1:]) - 1
    return ((i - (ROW_LEN[r] - 1) / 2) * _S3, (2 - r) * 1.5)


def corner_point(label, corner):
    cx, cy = hex_center(label)
    dx, dy = _CORNER_OFFSET[corner]
    return (cx + dx, cy + dy)


def _key(point):
    return (round(point[0] * 1000), round(point[1] * 1000))


def pips(number):
    return PIPS.get(number, 0) if number is not None else 0


class Geometry:
    """Corners (vertices) and edges of the 19-hex board, independent of what lies on it."""

    def __init__(self):
        self.vertex_hexes = {}   # vertex key -> set of hex labels touching it
        self.vertex_pos = {}
        self.edge_hexes = {}     # frozenset of 2 vertex keys -> set of hex labels
        for h in HEXES:
            keys = []
            for c in CORNERS:
                k = _key(corner_point(h, c))
                self.vertex_hexes.setdefault(k, set()).add(h)
                self.vertex_pos[k] = corner_point(h, c)
                keys.append(k)
            for a, b in zip(keys, keys[1:] + keys[:1]):
                self.edge_hexes.setdefault(frozenset((a, b)), set()).add(h)
        self.neighbours = {k: set() for k in self.vertex_hexes}
        for e in self.edge_hexes:
            a, b = tuple(e)
            self.neighbours[a].add(b)
            self.neighbours[b].add(a)

    def vertex(self, spec):
        """'B2:S' -> vertex key."""
        try:
            h, c = spec.strip().upper().split(":")
        except ValueError:
            raise BoardError(f"Ecke '{spec}' hat nicht das Format Feld:Ecke, z.B. B2:S")
        if h not in HEXES:
            raise BoardError(f"Unbekanntes Feld '{h}' in '{spec}'")
        if c not in CORNERS:
            raise BoardError(f"Unbekannte Ecke '{c}' in '{spec}' (erlaubt: {', '.join(CORNERS)})")
        return _key(corner_point(h, c))

    def edge(self, spec):
        """'B2:S-SW' -> edge (frozenset of two vertex keys)."""
        try:
            h, cs = spec.strip().upper().split(":")
            c1, c2 = cs.split("-")
        except ValueError:
            raise BoardError(f"Kante '{spec}' hat nicht das Format Feld:Ecke-Ecke, z.B. B2:S-SW")
        e = frozenset((self.vertex(f"{h}:{c1}"), self.vertex(f"{h}:{c2}")))
        if e not in self.edge_hexes:
            raise BoardError(f"'{spec}': {c1} und {c2} sind keine benachbarten Ecken")
        return e

    def name_vertex(self, key):
        """Readable name of a corner: its hexes, e.g. 'B2/B3/C3'."""
        return "/".join(sorted(self.vertex_hexes[key]))

    def is_coastal(self, edge):
        return len(self.edge_hexes[edge]) == 1


GEOMETRY = Geometry()


def player_code(key):
    k = str(key).strip()
    if k.lower() in COLORS:
        return COLORS[k.lower()]
    if k.upper() in PLAYERS:
        return k.upper()
    raise BoardError(f"Unbekannter Spieler/Farbe '{key}' (erlaubt: gelb/yellow, blau/blue, rot/red oder MF, PF, JHC)")


class Board:
    def __init__(self, description):
        g = GEOMETRY
        self.g = g
        self.warnings = []
        # hexes
        self.hexes = {}
        for label, value in description.get("hexes", {}).items():
            label = label.strip().upper()
            if label not in HEXES:
                raise BoardError(f"Unbekanntes Feld '{label}'")
            res, num = value[0].strip().lower(), value[1]
            if res not in RESOURCES + ["desert"]:
                raise BoardError(f"Feld {label}: unbekannter Rohstoff '{res}'")
            if res == "desert":
                num = None
            elif num not in PIPS:
                raise BoardError(f"Feld {label}: Zahl {num} ist nicht möglich")
            self.hexes[label] = (res, num)
        missing = [h for h in HEXES if h not in self.hexes]
        if missing:
            raise BoardError(f"Felder fehlen: {', '.join(missing)}")
        # harbors: vertex key -> harbor type
        self.harbors = []
        for hb in description.get("harbors", []):
            e = g.edge(hb["edge"])
            t = hb["type"].strip().lower()
            if t not in HARBOR_TYPES:
                raise BoardError(f"Hafen {hb['edge']}: unbekannter Typ '{t}'")
            if not g.is_coastal(e):
                raise BoardError(f"Hafen {hb['edge']} liegt nicht an der Küste")
            self.harbors.append((e, t))
        # buildings and roads
        self.buildings = {}  # vertex key -> (player, 'settlement'|'city')
        self.roads = {}      # edge -> player
        for pkey, pdata in description.get("players", {}).items():
            player = player_code(pkey)
            for b in pdata.get("buildings", []):
                v = g.vertex(b["at"])
                kind = b.get("type", "settlement").strip().lower()
                if kind not in ("settlement", "city"):
                    raise BoardError(f"{player}: Gebäudetyp '{kind}' unbekannt (settlement oder city)")
                if v in self.buildings:
                    raise BoardError(f"Ecke {b['at']} ist doppelt bebaut")
                self.buildings[v] = (player, kind)
            for r in pdata.get("roads", []):
                e = g.edge(r)
                if e in self.roads:
                    raise BoardError(f"Kante {r} hat zwei Straßen")
                self.roads[e] = player
        self._check()

    def _check(self):
        g = self.g
        res_count = {}
        num_count = {}
        for res, num in self.hexes.values():
            res_count[res] = res_count.get(res, 0) + 1
            if num is not None:
                num_count[num] = num_count.get(num, 0) + 1
        if res_count != STANDARD_RESOURCES:
            self.warnings.append(f"Ungewöhnliche Feldverteilung: {res_count}")
        if num_count != STANDARD_NUMBERS:
            self.warnings.append(f"Ungewöhnliche Zahlenverteilung: {dict(sorted(num_count.items()))}")
        hb_count = {}
        for _, t in self.harbors:
            hb_count[t] = hb_count.get(t, 0) + 1
        if hb_count != STANDARD_HARBORS:
            self.warnings.append(f"Ungewöhnliche Häfen: {hb_count} (erwartet 4× 3:1 und je 1× 2:1)")
        for v, (player, _) in self.buildings.items():
            for n in g.neighbours[v]:
                if n in self.buildings:
                    self.warnings.append(f"Abstandsregel verletzt: {g.name_vertex(v)} und {g.name_vertex(n)}")
        for e, player in self.roads.items():
            at_building = any(self.buildings.get(v, (None,))[0] == player for v in e)
            at_road = any(p == player and o != e and (o & e) for o, p in self.roads.items())
            if not (at_building or at_road):
                self.warnings.append(f"Straße von {player} an {'–'.join(g.name_vertex(v) for v in e)} hängt an nichts Eigenem")
        for player in PLAYERS:
            kinds = sorted(k for p, k in self.buildings.values() if p == player)
            nroads = sum(1 for p in self.roads.values() if p == player)
            if kinds and (kinds != ["city", "settlement"] or nroads != 2):
                self.warnings.append(f"{player}: {kinds.count('settlement')} Siedlung(en), {kinds.count('city')} "
                                     f"Stadt/Städte, {nroads} Straße(n) – üblich sind 1 Siedlung, 1 Stadt, 2 Straßen")

    # --- derived values -------------------------------------------------
    def desert_position(self):
        desert = [h for h, (res, _) in self.hexes.items() if res == "desert"]
        if len(desert) != 1:
            return None
        h = desert[0]
        return "center" if h in CENTER else "second" if h in SECOND_RING else "outer"

    def _corner_free(self, v):
        """A settlement may be built on v: no building on v or any neighbouring corner."""
        return v not in self.buildings and not any(n in self.buildings for n in self.g.neighbours[v])

    def player_values(self, player):
        g = self.g
        prod = {p: 0 for p in PRODUCTION}
        numbers, resources = set(), set()
        own = [v for v, (p, _) in self.buildings.items() if p == player]
        for v in own:
            kind = self.buildings[v][1]
            for h in g.vertex_hexes[v]:
                res, num = self.hexes[h]
                if res == "desert":
                    continue
                w = pips(num)
                numbers.add(num)
                resources.add(res)
                prod[res] += w
                if kind == "city":
                    if res in GOODS:
                        prod[GOODS[res]] += w
                    else:
                        prod[res] += w
        port = {t: 0 for t in HARBOR_TYPES}
        prox = {t: 0 for t in HARBOR_TYPES}
        own_road_ends = {v for e, p in self.roads.items() if p == player for v in e}
        for edge, t in self.harbors:
            for h in edge:
                if self.buildings.get(h, (None,))[0] == player:
                    port[t] = 1
                elif self._corner_free(h):
                    # one more road from the end of an own road to h: edge not taken by anyone,
                    # and no foreign building on that road end (roads can't pass through it)
                    for n in g.neighbours[h]:
                        if (n in own_road_ends and frozenset((n, h)) not in self.roads
                                and self.buildings.get(n, (player,))[0] == player):
                            prox[t] = 1
        for t in HARBOR_TYPES:
            if port[t]:
                prox[t] = 0
        out = {"desert": self.desert_position(), "sum": sum(prod.values()),
               "count_num": len(numbers), "count_res": len(resources)}
        out.update({f"p_sum_{p}": prod[p] for p in PRODUCTION})
        out.update({f"port_{t}": port[t] for t in HARBOR_TYPES})
        out.update({f"prox_port_{t}": prox[t] for t in HARBOR_TYPES})
        return out

    def values(self):
        """Pre-game columns for every player with buildings on the board."""
        present = sorted({p for p, _ in self.buildings.values()}, key=PLAYERS.index)
        return {p: self.player_values(p) for p in present}

    def describe_buildings(self, player):
        """Readable list, e.g. ['Stadt: Erz 8, Holz 6, Schaf 3', ...]."""
        names = {"wood": "Holz", "clay": "Lehm", "sheep": "Schaf", "grain": "Getreide", "ore": "Erz", "desert": "Wüste",
                 "gen": "3:1"}
        out = []
        for v, (p, kind) in self.buildings.items():
            if p != player:
                continue
            fields = sorted((self.hexes[h] for h in self.g.vertex_hexes[v]), key=lambda rn: -pips(rn[1]))
            txt = ", ".join(names[r] + (f" {n}" if n else "") for r, n in fields)
            hb = [t for e, t in self.harbors if v in e]
            out.append(f"{'Stadt' if kind == 'city' else 'Siedlung'} ({self.g.name_vertex(v)}): {txt}"
                       + (f" · Hafen {names[hb[0]]}" if hb else ""))
        return out
