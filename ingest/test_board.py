"""Tests for ingest/board.py. Run: python ingest/test_board.py

Expected values for the example board are computed by hand (see comments), not by the code.
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from board import GEOMETRY, Board, BoardError  # noqa: E402

EXAMPLE = json.loads((HERE / "examples" / "example_board.json").read_text(encoding="utf-8"))


def board_with(change):
    d = copy.deepcopy(EXAMPLE)
    change(d)
    return Board(d)


def test_geometry():
    assert len(GEOMETRY.vertex_hexes) == 54
    assert len(GEOMETRY.edge_hexes) == 72
    assert sum(GEOMETRY.is_coastal(e) for e in GEOMETRY.edge_hexes) == 30
    # the same corner named from three hexes
    assert GEOMETRY.vertex("B2:S") == GEOMETRY.vertex("C2:NE") == GEOMETRY.vertex("C3:NW")
    assert GEOMETRY.edge("B2:S-SE") == GEOMETRY.edge("C3:NW-N")


def test_example_values():
    b = Board(EXAMPLE)
    assert b.warnings == [], b.warnings
    v = b.values()
    assert b.desert_position() == "center"

    # MF: city B2/C2/C3 = clay 6 (5 pips, doubled -> 10), wood 11 (2 -> wood 2 + paper 2), desert;
    #     settlement A1/A2/B2 = ore 10 (3), sheep 2 (1), clay 6 (5)
    mf = v["MF"]
    assert (mf["p_sum_clay"], mf["p_sum_wood"], mf["p_sum_paper"], mf["p_sum_ore"], mf["p_sum_sheep"]) == (15, 2, 2, 3, 1)
    assert (mf["sum"], mf["count_num"], mf["count_res"]) == (23, 4, 4)
    # road A1:SE -> A2:NW, one more road reaches A2:N (sheep harbor) and A1:N (3:1 harbor)
    assert mf["prox_port_sheep"] == 1 and mf["prox_port_gen"] == 1
    assert sum(mf[f"port_{t}"] for t in ["wood", "clay", "sheep", "grain", "ore", "gen"]) == 0

    # PF: city B3/B4/C4 = sheep 4 (3 -> sheep 3 + fabric 3), clay 10 (3 -> 6), wood 3 (2 -> wood 2 + paper 2);
    #     settlement on the 3:1 harbor corner C5:SE = ore 8 (5)
    pf = v["PF"]
    assert (pf["p_sum_sheep"], pf["p_sum_fabric"], pf["p_sum_clay"], pf["p_sum_wood"], pf["p_sum_paper"],
            pf["p_sum_ore"]) == (3, 3, 6, 2, 2, 5)
    assert (pf["sum"], pf["count_num"], pf["count_res"]) == (21, 4, 4)
    assert pf["port_gen"] == 1
    assert pf["prox_port_ore"] == 1          # road C5:SE -> C5:NE, one more road to C5:N (ore harbor)
    assert pf["prox_port_gen"] == 0          # port_gen already 1

    # JHC: city C4/C5/D4 = sheep 5 (4 -> 4 + fabric 4), wood 3 (2 -> 2 + paper 2), ore 8 (5 -> 5 + coin 5);
    #      settlement D1/D2/E1 = wood 8 (5), ore 3 (2), clay 5 (4)
    jhc = v["JHC"]
    assert (jhc["p_sum_wood"], jhc["p_sum_clay"], jhc["p_sum_sheep"], jhc["p_sum_ore"], jhc["p_sum_paper"],
            jhc["p_sum_coin"], jhc["p_sum_fabric"]) == (7, 4, 4, 7, 2, 5, 4)
    assert (jhc["sum"], jhc["count_num"], jhc["count_res"]) == (33, 3, 4)
    assert jhc["prox_port_gen"] == 1         # road ends on E1:NW, one more road to E1:SW (both 3:1 harbor)
    assert jhc["prox_port_wood"] == 1        # road D4:N -> C5:S, one more road to D4:SE (wood harbor)


def test_road_pointing_away_does_not_count():
    # MF's settlement road now points to A1:S instead of towards the harbors: two roads needed -> 0
    def change(d):
        d["players"]["yellow"]["roads"][0] = "A1:SE-S"
    mf = board_with(change).values()["MF"]
    assert mf["prox_port_sheep"] == 0 and mf["prox_port_gen"] == 0


def test_blocked_by_foreign_road():
    # a red road on the edge PF would need (C5:NE - C5:N) blocks the ore harbor
    def change(d):
        d["players"]["red"]["roads"].append("C5:NE-N")
    assert board_with(change).values()["PF"]["prox_port_ore"] == 0


def test_blocked_by_foreign_building_next_to_harbor():
    # a yellow settlement on B4:NE (next to the harbor corner C5:N) makes C5:N unbuildable;
    # the other harbor corner B4:NE is then taken itself -> PF can't reach the ore harbor
    def change(d):
        d["players"]["yellow"]["buildings"].append({"at": "B4:NE", "type": "settlement"})
    b = board_with(change)
    assert b.values()["PF"]["prox_port_ore"] == 0
    assert b.values()["MF"]["port_ore"] == 1


def test_errors_and_warnings():
    for bad in [lambda d: d["hexes"].pop("C3"),
                lambda d: d["hexes"].__setitem__("A1", ["ore", 7]),
                lambda d: d["harbors"].append({"edge": "C3:N-NE", "type": "gen"}),   # not at the coast
                lambda d: d["players"]["blue"]["roads"].append("C4:N-S")]:           # not neighbouring corners
        try:
            board_with(bad)
        except BoardError:
            continue
        raise AssertionError("BoardError expected")

    def too_close(d):
        d["players"]["red"]["buildings"].append({"at": "B2:SE", "type": "settlement"})  # next to MF's city
    assert any("Abstandsregel" in w for w in board_with(too_close).warnings)


if __name__ == "__main__":
    tests = [f for name, f in sorted(globals().items()) if name.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"{len(tests)} Tests bestanden")
