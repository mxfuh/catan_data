"""Write a game into catan_data.xlsx without re-saving the workbook.

    python ingest/excel_rows.py pregame catan_data.xlsx brett.json --order MF,JHC,PF --loc "Tabua (Madeira)"
    python ingest/excel_rows.py result  catan_data.xlsx "MF 6 (1), JHC 14 (8), PF 11 (4)"
    python ingest/excel_rows.py places  catan_data.xlsx

Saving with openpyxl would drop the cached formula values (geoloc, sum) and Max's drop-down lists.
So this script edits the sheet XML inside the zip directly. It changes only the new cells and checks
afterwards that every existing cell and every other part of the file is still the same.
"""
import argparse
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from board import Board, BoardError, PLAYERS  # noqa: E402

SHEET1 = "xl/worksheets/sheet1.xml"
SHEET2 = "xl/worksheets/sheet2.xml"
SST = "xl/sharedStrings.xml"
EDITABLE = {SHEET1, SHEET2, SST}
POSITIONS = ["first", "second", "third"]
# Old rows look up Sheet2!$I$1:$J$13, which has room for only 13 places. New rows use a wider range.
LOOKUP = "Sheet2!$I$1:$J$200"
NUMBER_COLUMNS = (["count_num", "count_res"]
                  + [f"p_sum_{r}" for r in ["wood", "clay", "sheep", "grain", "ore", "paper", "coin", "fabric"]]
                  + [f"port_{t}" for t in ["wood", "clay", "sheep", "grain", "ore", "gen"]]
                  + [f"prox_port_{t}" for t in ["wood", "clay", "sheep", "grain", "ore", "gen"]])
EXCEL_EPOCH = dt.date(1899, 12, 30)

CELL_RE = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)
ROW_RE = re.compile(r'<row r="(\d+)"[^>]*?(?:/>|>.*?</row>)', re.S)
CELL_XML_RE = re.compile(r'<c r="[A-Z]+\d+"[^>]*?(?:/>|>.*?</c>)', re.S)


class ExcelError(ValueError):
    pass


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def col_letters(index):
    s = ""
    while index:
        index, rem = divmod(index - 1, 26)
        s = chr(65 + rem) + s
    return s


NUMBER_LETTERS = [col_letters(col_index("M") + i) for i in range(len(NUMBER_COLUMNS))]  # M … AH


class Workbook:
    """The xlsx as zip parts; only the two sheets and the shared strings are ever edited."""

    def __init__(self, path):
        with zipfile.ZipFile(path) as z:
            self.infos = z.infolist()
            self.parts = {i.filename: z.read(i.filename) for i in self.infos}
        self.xml = {name: self.parts[name].decode("utf-8") for name in EDITABLE}
        self.strings = [
            "".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S))
            for si in re.findall(r"<si>(.*?)</si>", self.xml[SST], re.S)
        ]
        self._new_string_refs = 0

    # ---- reading -------------------------------------------------------------------------------
    def cells(self, sheet):
        """{row: {column: value}} with shared strings resolved and numbers as float."""
        out = {}
        for col, row, attrs, inner in CELL_RE.findall(self.xml[sheet]):
            m = re.search(r"<v>(.*?)</v>", inner or "", re.S)
            if not m:
                continue
            v = m.group(1)
            if 't="s"' in attrs:
                v = self.strings[int(v)]
            elif 't="str"' not in attrs and 't="inlineStr"' not in attrs:
                try:
                    v = float(v)
                except ValueError:
                    pass
            out.setdefault(int(row), {})[col] = v
        return out

    def places(self):
        """{place name: (row in Sheet2, 'lat, lon')} from Sheet2 I:J."""
        return {c["I"]: (r, c.get("J")) for r, c in self.cells(SHEET2).items() if "I" in c}

    def games(self):
        """{(season, game): {player: row}} from Sheet1."""
        out = {}
        for r, c in self.cells(SHEET1).items():
            if r < 3 or c.get("F") not in PLAYERS or not isinstance(c.get("A"), float):
                continue
            out.setdefault((int(c["A"]), int(c["C"])), {})[c["F"]] = r
        return out

    # ---- writing -------------------------------------------------------------------------------
    def string_ref(self, text):
        self._new_string_refs += 1
        if text in self.strings:
            return self.strings.index(text)
        self.strings.append(text)
        self.xml[SST] = self.xml[SST].replace("</sst>", f"<si><t>{escape(text)}</t></si></sst>", 1)
        return len(self.strings) - 1

    def set_cells(self, sheet, row, cells, row_attrs=' spans="1:34" x14ac:dyDescent="0.35"'):
        """Add cells {column: '<c …/>'} to a row, keeping column order. Existing cells are never touched."""
        x = self.xml[sheet]
        m = re.search(rf'<row r="{row}"[^>]*?(?:/>|>(.*?)</row>)', x, re.S)
        if m:
            merged = {re.match(r'<c r="([A-Z]+)', c).group(1): c for c in CELL_XML_RE.findall(m.group(1) or "")}
            clash = set(merged) & set(cells)
            if clash:
                raise ExcelError(f"Zeile {row}: Zellen {sorted(clash)} sind schon gefüllt")
            merged.update(cells)
            head = re.match(r"<row [^>]*?(?=/?>)", m.group(0)).group(0)
            new = head + ">" + "".join(merged[c] for c in sorted(merged, key=col_index)) + "</row>"
            self.xml[sheet] = x[:m.start()] + new + x[m.end():]
        else:
            rows = [int(r) for r in ROW_RE.findall(x)]
            new = f'<row r="{row}"{row_attrs}>' + "".join(cells[c] for c in sorted(cells, key=col_index)) + "</row>"
            later = [r for r in rows if r > row]
            if later:
                pos = re.search(rf'<row r="{min(later)}"', x).start()
            else:
                pos = x.index("</sheetData>")
            self.xml[sheet] = x[:pos] + new + x[pos:]
        self._fix_dimension(sheet)

    def _fix_dimension(self, sheet):
        x = self.xml[sheet]
        m = re.search(r'<dimension ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"/>', x)
        if not m:
            return
        last = max(int(r) for r in ROW_RE.findall(x))
        if last > int(m.group(4)):
            self.xml[sheet] = x.replace(m.group(0), f'<dimension ref="{m.group(1)}{m.group(2)}:{m.group(3)}{last}"/>', 1)

    def save(self, path):
        sst = self.xml[SST]
        m = re.search(r'<sst [^>]*>', sst)
        head = m.group(0)
        count = re.search(r'count="(\d+)"', head)
        new_head = head
        if count:
            new_head = new_head.replace(count.group(0), f'count="{int(count.group(1)) + self._new_string_refs}"', 1)
        unique = re.search(r'uniqueCount="(\d+)"', head)
        if unique:
            new_head = new_head.replace(unique.group(0), f'uniqueCount="{len(self.strings)}"', 1)
        self.xml[SST] = sst.replace(head, new_head, 1)
        with zipfile.ZipFile(path, "w") as z:
            for info in self.infos:
                data = self.xml[info.filename].encode("utf-8") if info.filename in EDITABLE else self.parts[info.filename]
                z.writestr(info, data, compress_type=info.compress_type)


# ---- helpers ---------------------------------------------------------------------------------------
def parse_coords(text):
    """'32.683250, -17.069556' or Google Maps DMS like 32°41'00.0"N 17°04'10.4"W → '32.683250, -17.069556'."""
    dms = re.findall(r"(\d+(?:\.\d+)?)\s*°\s*(?:(\d+(?:\.\d+)?)\s*['′]\s*)?(?:(\d+(?:\.\d+)?)\s*[\"″]\s*)?([NSEOW])",
                     text, re.I)
    if len(dms) == 2:
        vals = {}
        for d, m, s, hemi in dms:
            v = float(d) + float(m or 0) / 60 + float(s or 0) / 3600
            hemi = hemi.upper()
            if hemi in "SW":
                v = -v
            vals["lat" if hemi in "NS" else "lon"] = v
        if len(vals) != 2:
            raise ExcelError(f"Koordinaten unklar: {text}")
        lat, lon = vals["lat"], vals["lon"]
    else:
        nums = re.findall(r"-?\d+(?:\.\d+)?", text)
        if len(nums) != 2:
            raise ExcelError(f"Koordinaten unklar (erwartet z.B. '32.68325, -17.06956'): {text}")
        lat, lon = map(float, nums)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ExcelError(f"Koordinaten außerhalb des gültigen Bereichs: {text}")
    return f"{lat:.6f}, {lon:.6f}"


def parse_order(text):
    order = [p.strip().upper() for p in re.split(r"[,\s]+", text) if p.strip()]
    if sorted(order) != sorted(PLAYERS):
        raise ExcelError(f"Reihenfolge braucht alle drei Spieler genau einmal, z.B. MF,JHC,PF (bekommen: {text})")
    return order


RESULT_RE = re.compile(r"\b(MF|JHC|PF)\b\s*:?\s*(\d+)\s*(?:\(\s*(\d+)\s*\))?(?:\s*(?:Platz|P\.?|#)\s*(\d))?", re.I)


def parse_result(text):
    """'MF 6 (1), JHC 14 (8), PF 11 (4)' → {player: [score, special, place or None]}."""
    found = {}
    for p, score, special, place in RESULT_RE.findall(text):
        p = p.upper()
        if p in found:
            raise ExcelError(f"{p} steht doppelt im Ergebnis")
        found[p] = [int(score), int(special) if special else None, int(place) if place else None]
    if sorted(found) != sorted(PLAYERS):
        raise ExcelError(f"Ergebnis braucht MF, JHC und PF (erkannt: {', '.join(found) or 'nichts'})")
    missing_special = [p for p, v in found.items() if v[1] is None]
    if missing_special:
        raise ExcelError(f"Sonder-SP fehlen für {', '.join(missing_special)} (Format: 'MF 13 (5)')")
    if all(v[2] is None for v in found.values()):
        scores = sorted((v[0] for v in found.values()), reverse=True)
        if len(set(scores)) < len(scores):
            raise ExcelError("Gleichstand bei den Punkten – bitte Plätze angeben, z.B. 'MF 10 (2) Platz 1'")
        for v in found.values():
            v[2] = scores.index(v[0]) + 1
    elif any(v[2] is None for v in found.values()) or sorted(v[2] for v in found.values()) != [1, 2, 3]:
        raise ExcelError("Plätze unvollständig – entweder für alle drei angeben oder für keinen")
    return found


def number(v):
    return str(int(v)) if float(v).is_integer() else str(v)


# ---- the two operations -------------------------------------------------------------------------
def add_pregame(wb, board_desc, order, loc, date, coords=None, game=None):
    board = Board(board_desc)
    values = board.values()
    order = parse_order(order) if isinstance(order, str) else order
    season = date.year
    games = wb.games()
    game = game or max([g for s, g in games if s == season], default=0) + 1
    if (season, game) in games:
        raise ExcelError(f"Spiel {season}/{game} steht schon in der Tabelle")

    places = wb.places()
    if loc in places:
        geo = places[loc][1]
        if coords and parse_coords(coords) != geo:
            raise ExcelError(f"{loc} steht schon mit anderen Koordinaten in der Tabelle ({geo})")
    else:
        if not coords:
            known = ", ".join(sorted(places))
            raise ExcelError(f"Ort '{loc}' ist neu – bitte Koordinaten mitschicken. Bekannte Orte: {known}")
        geo = parse_coords(coords)
        row2 = max(r for r, _ in places.values()) + 1
        wb.set_cells(SHEET2, row2, {
            "I": f'<c r="I{row2}" t="s"><v>{wb.string_ref(loc)}</v></c>',
            "J": f'<c r="J{row2}" t="s"><v>{wb.string_ref(geo)}</v></c>',
        }, row_attrs=' spans="1:14" x14ac:dyDescent="0.35"')

    first = max(wb.cells(SHEET1)) + 1
    serial = (date - EXCEL_EPOCH).days
    written = {}
    for i, p in enumerate(order):
        r, v = first + i, values[p]
        cells = {
            "A": f'<c r="A{r}"><v>{season}</v></c>',
            "B": f'<c r="B{r}" s="5"><v>{serial}</v></c>',
            "C": f'<c r="C{r}"><v>{game}</v></c>',
            "D": f'<c r="D{r}" t="s"><v>{wb.string_ref(loc)}</v></c>',
            "E": f'<c r="E{r}" t="str"><f>VLOOKUP(D{r},{LOOKUP},2,FALSE)</f><v>{escape(geo)}</v></c>',
            "F": f'<c r="F{r}" t="s"><v>{wb.string_ref(p)}</v></c>',
            "J": f'<c r="J{r}" t="s"><v>{wb.string_ref(POSITIONS[i])}</v></c>',
            "K": f'<c r="K{r}" t="s"><v>{wb.string_ref(v["desert"])}</v></c>',
            "L": f'<c r="L{r}"><f>SUM(O{r}:V{r})</f><v>{v["sum"]}</v></c>',
        }
        for letter, col in zip(NUMBER_LETTERS, NUMBER_COLUMNS):
            cells[letter] = f'<c r="{letter}{r}"><v>{v[col]}</v></c>'
        wb.set_cells(SHEET1, r, cells)
        written[r] = p
    return {"season": season, "game": game, "rows": written, "values": values, "warnings": board.warnings,
            "new_place": loc not in places, "geo": geo}


def open_games(wb):
    cells = wb.cells(SHEET1)
    return {k: rows for k, rows in wb.games().items() if all("G" not in cells[r] for r in rows.values())}


def add_result(wb, text, game=None):
    result = parse_result(text)
    candidates = open_games(wb)
    if game:
        if game not in wb.games():
            raise ExcelError(f"Spiel {game[0]}/{game[1]} gibt es nicht")
        if game not in candidates:
            raise ExcelError(f"Spiel {game[0]}/{game[1]} hat schon ein Ergebnis")
        key = game
    elif not candidates:
        raise ExcelError("Kein offenes Spiel ohne Ergebnis gefunden – erst die Pre-Game-Daten eintragen")
    elif len(candidates) > 1:
        names = ", ".join(f"{s}/{g}" for s, g in sorted(candidates))
        raise ExcelError(f"Mehrere offene Spiele ({names}) – bitte angeben, welches")
    else:
        key = next(iter(candidates))
    rows = wb.games()[key]
    if sorted(rows) != sorted(PLAYERS):
        raise ExcelError(f"Spiel {key[0]}/{key[1]} hat nicht genau die Zeilen für MF, JHC und PF")
    for p, (score, special, place) in result.items():
        r = rows[p]
        wb.set_cells(SHEET1, r, {
            "G": f'<c r="G{r}"><v>{score}</v></c>',
            "H": f'<c r="H{r}"><v>{special}</v></c>',
            "I": f'<c r="I{r}"><v>{place}</v></c>',
        })
    return {"season": key[0], "game": key[1], "result": result, "rows": rows}


# ---- safety check ------------------------------------------------------------------------------
def verify(before_path, after_path, expected):
    """expected: {sheet: {row: set(columns)}} that may be new. Everything else must be unchanged."""
    before, after = Workbook(before_path), Workbook(after_path)
    for name, data in before.parts.items():
        if name not in EDITABLE and after.parts.get(name) != data:
            raise ExcelError(f"Unerwartete Änderung in {name}")
    if after.strings[:len(before.strings)] != before.strings:
        raise ExcelError("Bestehende Texte (shared strings) haben sich verändert")
    for sheet in (SHEET1, SHEET2):
        old, new = before.cells(sheet), after.cells(sheet)
        allowed = expected.get(sheet, {})
        for r in set(old) | set(new):
            o, n = old.get(r, {}), new.get(r, {})
            for c in set(o) | set(n):
                if o.get(c) != n.get(c) and c not in allowed.get(r, set()):
                    raise ExcelError(f"Unerwartete Änderung in {sheet} {c}{r}: {o.get(c)!r} → {n.get(c)!r}")
            for c in allowed.get(r, set()):
                if c in o:
                    raise ExcelError(f"{c}{r} war schon gefüllt")
    # The raw XML of every old cell must be byte-identical too (formulas, styles, cached values).
    for sheet in (SHEET1, SHEET2):
        new_cells = set(CELL_XML_RE.findall(after.xml[sheet]))
        for cell in CELL_XML_RE.findall(before.xml[sheet]):
            if cell not in new_cells:
                raise ExcelError(f"Zelle verändert in {sheet}: {cell[:80]}")
    return True


def write(path, out, operation):
    wb = Workbook(path)
    info = operation(wb)
    wb.save(out)
    expected = {SHEET1: {}, SHEET2: {}}
    if "values" in info:
        cols = {"A", "B", "C", "D", "E", "F", "J", "K", "L", *NUMBER_LETTERS}
        expected[SHEET1] = {r: cols for r in info["rows"]}
        if info["new_place"]:
            row2 = max(r for r, _ in Workbook(out).places().values())
            expected[SHEET2] = {row2: {"I", "J"}}
    else:
        expected[SHEET1] = {r: {"G", "H", "I"} for r in info["rows"].values()}
    verify(path, out, expected)
    return info


# ---- CLI ---------------------------------------------------------------------------------------
def summary_pregame(info):
    lines = [f"Spiel {info['season']}/{info['game']} eingetragen (Zeilen {min(info['rows'])}–{max(info['rows'])})."]
    if info["new_place"]:
        lines.append(f"Neuer Ort angelegt: {info['geo']}")
    for r, p in info["rows"].items():
        v = info["values"][p]
        lines.append(f"{p}: Produktion {v['sum']}, {v['count_num']} Zahlen, {v['count_res']} Rohstoffe")
    lines += [f"⚠️ {w}" for w in info["warnings"]]
    return "\n".join(lines)


def summary_result(info):
    order = sorted(info["result"].items(), key=lambda kv: kv[1][2])
    parts = [f"{v[2]}. {p} {v[0]} ({v[1]})" for p, v in order]
    return f"Ergebnis für Spiel {info['season']}/{info['game']} eingetragen: " + ", ".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pregame", help="Pre-Game-Zeilen aus einer Brett-Beschreibung anlegen")
    p.add_argument("xlsx")
    p.add_argument("board", help="Brett-Beschreibung (JSON)")
    p.add_argument("--order", required=True, help="Startreihenfolge, z.B. MF,JHC,PF")
    p.add_argument("--loc", required=True, help="Ort, wie in Sheet2 Spalte I")
    p.add_argument("--coords", help="nur für neue Orte: '32.68325, -17.06956' oder Google-Maps-Grad")
    p.add_argument("--date", help="Spieltag JJJJ-MM-TT (Standard: heute)")
    p.add_argument("--game", type=int, help="Spielnummer (Standard: letzte der Saison + 1)")
    p.add_argument("--out", help="Zieldatei (Standard: xlsx überschreiben)")
    r = sub.add_parser("result", help="Ergebnis ins offene Spiel eintragen")
    r.add_argument("xlsx")
    r.add_argument("text", help="z.B. 'MF 6 (1), JHC 14 (8), PF 11 (4)'")
    r.add_argument("--game", help="Saison/Spiel, z.B. 2026/29 (Standard: das einzige offene Spiel)")
    r.add_argument("--out")
    pl = sub.add_parser("places", help="bekannte Orte und offene Spiele zeigen")
    pl.add_argument("xlsx")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "places":
            wb = Workbook(args.xlsx)
            for name, (_, geo) in sorted(wb.places().items()):
                print(f"{name}: {geo}")
            games = wb.games()
            last = max(games)
            print(f"Letztes Spiel: {last[0]}/{last[1]}")
            print("Offene Spiele: " + (", ".join(f"{s}/{g}" for s, g in sorted(open_games(wb))) or "keine"))
            return
        out = args.out or args.xlsx
        if args.cmd == "pregame":
            desc = json.loads(Path(args.board).read_text(encoding="utf-8"))
            date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
            tmp = Path(out).with_suffix(".tmp.xlsx")
            info = write(args.xlsx, tmp, lambda wb: add_pregame(wb, desc, args.order, args.loc, date,
                                                                  args.coords, args.game))
            tmp.replace(out)
            print(summary_pregame(info))
        else:
            game = tuple(int(x) for x in args.game.split("/")) if args.game else None
            tmp = Path(out).with_suffix(".tmp.xlsx")
            info = write(args.xlsx, tmp, lambda wb: add_result(wb, args.text, game))
            tmp.replace(out)
            print(summary_result(info))
    except (ExcelError, BoardError) as e:
        raise SystemExit(f"Nicht eingetragen: {e}")


if __name__ == "__main__":
    main()
