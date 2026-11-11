"""Tests for ingest/excel_rows.py. Run: python ingest/test_excel_rows.py

Works on a temporary copy of catan_data.xlsx; the real file is never written.
The regression tests compare boards read from photos with the rows Max entered by hand.
"""
import datetime as dt
import json
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from board import Board  # noqa: E402
import excel_rows as xr  # noqa: E402

XLSX = HERE.parent / "catan_data.xlsx"
EXAMPLES = HERE / "examples"
TMP = Path(tempfile.mkdtemp())


def board(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def read(path):
    import pandas as pd
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.read_excel(path, header=1)


def copy_xlsx(name):
    p = TMP / name
    shutil.copy(XLSX, p)
    return p


def test_regression_photo_boards_match_excel():
    """Boards read from photos give exactly the values Max has in the Excel."""
    df = read(XLSX)
    cols = xr.NUMBER_COLUMNS + ["sum", "desert"]
    for name, game in [("game_2026_28.json", 28), ("game_2026_29.json", 29)]:
        values = Board(board(name)).values()
        rows = df[(df.season == 2026) & (df.game == game)].set_index("player")
        for p, v in values.items():
            for c in cols:
                assert rows.loc[p, c] == v[c], (name, p, c, rows.loc[p, c], v[c])


def test_pregame_writes_only_new_rows():
    src, out = copy_xlsx("a.xlsx"), TMP / "a_out.xlsx"
    info = xr.write(src, out, lambda wb: xr.add_pregame(
        wb, board("game_2026_29.json"), "PF,MF,JHC", "Tabua (Madeira)", dt.date(2026, 12, 1)))
    before, after = read(src), read(out)
    assert len(after) == len(before) + 3
    import pandas as pd
    # new empty score cells turn int columns into float, so compare values, not dtypes
    pd.testing.assert_frame_equal(after.iloc[:len(before)], before, check_dtype=False)
    new = after.iloc[len(before):]
    assert list(new.player) == ["PF", "MF", "JHC"]
    assert list(new.position) == ["first", "second", "third"]
    assert set(new.game) == {max(before[before.season == 2026].game) + 1}
    assert new.score.isna().all() and new.place.isna().all()
    assert (new.geoloc == "32.683250, -17.069556").all()          # cached VLOOKUP value
    values = info["values"]
    for _, row in new.iterrows():
        assert row["sum"] == values[row.player]["sum"]               # cached SUM value
        assert row["p_sum_clay"] == values[row.player]["p_sum_clay"]
    assert str(new.Session.iloc[0].date()) == "2026-12-01"
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ws = openpyxl.load_workbook(out)["Sheet1"]
    r = len(before) + 3
    assert ws[f"L{r}"].value == f"=SUM(O{r}:V{r})"
    assert ws[f"E{r}"].value.startswith(f"=VLOOKUP(D{r},Sheet2!$I$1:$J$200")


def test_result_fills_open_game():
    src, mid, out = copy_xlsx("b.xlsx"), TMP / "b_mid.xlsx", TMP / "b_out.xlsx"
    xr.write(src, mid, lambda wb: xr.add_pregame(
        wb, board("game_2026_29.json"), "MF,JHC,PF", "Tabua (Madeira)", dt.date(2026, 12, 1)))
    info = xr.write(mid, out, lambda wb: xr.add_result(wb, "mf 6 (1), JHC 14(8),PF 11 (4)"))
    after = read(out).tail(3).set_index("player")
    assert after.loc["JHC", "place"] == 1 and after.loc["PF", "place"] == 2 and after.loc["MF", "place"] == 3
    assert after.loc["JHC", "special"] == 8 and after.loc["MF", "score"] == 6
    assert info["game"] == 30
    # the game is closed now
    try:
        xr.write(out, TMP / "b2.xlsx", lambda wb: xr.add_result(wb, "MF 6 (1), JHC 14 (8), PF 11 (4)"))
    except xr.ExcelError as e:
        assert "Kein offenes Spiel" in str(e)
    else:
        raise AssertionError("second result was accepted")


def test_result_parsing():
    assert xr.parse_result("MF 13 (5), JHC 10 (2), PF 8 (0)") == {
        "MF": [13, 5, 1], "JHC": [10, 2, 2], "PF": [8, 0, 3]}
    for bad, msg in [("MF 10 (2), JHC 10 (3), PF 8 (0)", "Gleichstand"),
                     ("MF 10 (2), JHC 9 (3)", "braucht"),
                     ("MF 10, JHC 9 (3), PF 8 (1)", "Sonder-SP")]:
        try:
            xr.parse_result(bad)
        except xr.ExcelError as e:
            assert msg in str(e), (bad, e)
        else:
            raise AssertionError(bad)
    # ties are fine with explicit places
    assert xr.parse_result("MF 10 (2) Platz 2, JHC 10 (3) Platz 1, PF 8 (0) Platz 3")["JHC"][2] == 1


def test_new_place_needs_coords_and_is_added():
    src = copy_xlsx("c.xlsx")
    try:
        xr.write(src, TMP / "c0.xlsx", lambda wb: xr.add_pregame(
            wb, board("game_2026_29.json"), "MF,JHC,PF", "Neuer Ort", dt.date(2026, 12, 1)))
    except xr.ExcelError as e:
        assert "Koordinaten" in str(e)
    else:
        raise AssertionError("new place without coordinates was accepted")
    out = TMP / "c_out.xlsx"
    info = xr.write(src, out, lambda wb: xr.add_pregame(
        wb, board("game_2026_29.json"), "MF,JHC,PF", "Neuer Ort", dt.date(2026, 12, 1),
        coords="53°33'02.6\"N 9°59'35.5\"E"))
    assert info["geo"] == "53.550722, 9.993194"
    wb = xr.Workbook(out)
    assert wb.places()["Neuer Ort"][1] == "53.550722, 9.993194"
    assert (read(out).tail(3).geoloc == "53.550722, 9.993194").all()


def test_coords():
    assert xr.parse_coords("32.683250, -17.069556") == "32.683250, -17.069556"
    assert xr.parse_coords("32°41'00.0\"N 17°04'10.4\"W") == "32.683333, -17.069556"
    assert xr.parse_coords("53.5507, 9.9932") == "53.550700, 9.993200"


def test_duplicate_game_rejected():
    src = copy_xlsx("d.xlsx")
    try:
        xr.write(src, TMP / "d_out.xlsx", lambda wb: xr.add_pregame(
            wb, board("game_2026_29.json"), "MF,JHC,PF", "Tabua (Madeira)", dt.date(2026, 12, 1), game=29))
    except xr.ExcelError as e:
        assert "schon" in str(e)
    else:
        raise AssertionError("duplicate game was accepted")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, f in tests:
        f()
        print(f"ok  {name}")
    print(f"{len(tests)} Tests bestanden")
