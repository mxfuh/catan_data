"""Compute the pre-game columns from a board description and draw a sketch for confirmation.

    python ingest/catan_board.py board.json --order PF,MF,JHC --png skizze.png
    python ingest/catan_board.py board.json --json          # values as JSON (for the Excel step)
    python ingest/catan_board.py --reference referenz.png   # picture of the naming scheme
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from board import Board, BoardError, PLAYERS, PRODUCTION, HARBOR_TYPES  # noqa: E402

START = ["first", "second", "third"]
RES_DE = {"wood": "Holz", "clay": "Lehm", "sheep": "Schaf", "grain": "Getr.", "ore": "Erz",
          "paper": "Papier", "coin": "Münze", "fabric": "Stoff", "gen": "3:1"}


def parse_order(text):
    order = [p.strip().upper() for p in text.split(",") if p.strip()]
    if sorted(order) != sorted(PLAYERS):
        raise SystemExit(f"--order braucht alle drei Spieler genau einmal, z.B. PF,MF,JHC (bekommen: {text})")
    return {p: START[i] for i, p in enumerate(order)}


def report(board, values, positions):
    lines = []
    for w in board.warnings:
        lines.append(f"⚠️ {w}")
    lines.append(f"Wüste: {board.desert_position()}")
    for p, v in values.items():
        pos = f" · {positions[p]}" if positions else ""
        lines.append(f"\n{p}{pos}: Gesamtproduktion {v['sum']} · {v['count_num']} Zahlen · {v['count_res']} Rohstoffe")
        for b in board.describe_buildings(p):
            lines.append(f"  {b}")
        lines.append("  " + ", ".join(f"{RES_DE[r]} {v[f'p_sum_{r}']}" for r in PRODUCTION if v[f"p_sum_{r}"]))
        ports = [RES_DE[t] for t in HARBOR_TYPES if v[f"port_{t}"]]
        prox = [RES_DE[t] for t in HARBOR_TYPES if v[f"prox_port_{t}"]]
        lines.append(f"  Hafen direkt: {', '.join(ports) or '–'} · Hafen in Reichweite: {', '.join(prox) or '–'}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", help="board description (JSON)")
    ap.add_argument("--order", help="start order, e.g. PF,MF,JHC")
    ap.add_argument("--png", help="write a sketch of the recognized board")
    ap.add_argument("--json", action="store_true", help="print the values as JSON")
    ap.add_argument("--reference", help="write the picture of the naming scheme and exit")
    args = ap.parse_args()

    if args.reference:
        from sketch import draw_reference
        draw_reference(args.reference)
        print(f"Referenzbild: {args.reference}")
        return
    if not args.board:
        ap.error("board.json fehlt")

    try:
        board = Board(json.loads(Path(args.board).read_text(encoding="utf-8")))
    except BoardError as e:
        raise SystemExit(f"Brett ungültig: {e}")
    positions = parse_order(args.order) if args.order else None
    values = board.values()
    if positions:
        for p in values:
            values[p]["position"] = positions[p]

    if args.png:
        from sketch import draw_board
        draw_board(board, args.png, title="Erkanntes Brett – bitte prüfen")
    if args.json:
        print(json.dumps({"warnings": board.warnings, "players": values}, ensure_ascii=False, indent=1))
    else:
        print(report(board, values, positions))


if __name__ == "__main__":
    main()
