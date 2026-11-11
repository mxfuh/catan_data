"""Draw a recognized board (for confirmation) and the reference picture of the naming scheme."""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle

from board import (GEOMETRY, HEXES, CORNERS, corner_point, hex_center, pips, COLORS)

HEX_COLORS = {"wood": "#2e6b30", "clay": "#b5562b", "sheep": "#9ccc65", "grain": "#e8c547",
              "ore": "#8d8d8d", "desert": "#e9d8a6"}
RES_DE = {"wood": "Holz", "clay": "Lehm", "sheep": "Schaf", "grain": "Getreide", "ore": "Erz",
          "desert": "Wüste", "gen": "3:1"}
PLAYER_COLORS = {"MF": "#FFD700", "PF": "#075eb5", "JHC": "#FF4500"}
INK = "#4B2E1F"
SEA = "#a9d3e8"


def _hex_polygon(label, **kw):
    return Polygon([corner_point(label, c) for c in CORNERS], closed=True, **kw)


def _new_axes(title):
    fig, ax = plt.subplots(figsize=(8, 8.4))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-6.2, 6.2)
    ax.set_ylim(-6.0, 6.0)
    fig.patch.set_facecolor("#fdfaf6")
    ax.add_patch(Circle((0, 0), 5.9, color=SEA, zorder=0))
    if title:
        ax.set_title(title, color=INK, fontsize=13, fontfamily="serif")
    return fig, ax


def _draw_harbor(ax, edge, htype):
    a, b = (GEOMETRY.vertex_pos[v] for v in edge)
    (h,) = GEOMETRY.edge_hexes[edge]
    cx, cy = hex_center(h)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, ny = mx - cx, my - cy
    n = math.hypot(nx, ny)
    px, py = mx + nx / n * 0.75, my + ny / n * 0.75
    for v in (a, b):
        ax.plot([v[0], px], [v[1], py], color="#8B4513", lw=2.5, zorder=2, solid_capstyle="round")
    face = HEX_COLORS.get(htype, "#fdfaf6")
    ax.add_patch(Circle((px, py), 0.36, facecolor=face, edgecolor=INK, lw=1.5, zorder=3))
    ax.text(px, py, "3:1" if htype == "gen" else RES_DE[htype][:4] + "\n2:1", ha="center", va="center",
            fontsize=6.5, color="white" if htype in ("wood", "clay") else INK, zorder=4, fontweight="bold")


def draw_board(board, path, title=None):
    """board: ingest.board.Board"""
    fig, ax = _new_axes(title)
    for h in HEXES:
        res, num = board.hexes[h]
        ax.add_patch(_hex_polygon(h, facecolor=HEX_COLORS[res], edgecolor="#fdfaf6", lw=2, zorder=1))
        cx, cy = hex_center(h)
        ax.text(cx, cy + 0.62, h, ha="center", va="center", fontsize=7, color=INK, alpha=0.8, zorder=2)
        if num:
            ax.add_patch(Circle((cx, cy - 0.05), 0.33, facecolor="#fdfaf6", edgecolor=INK, lw=1, zorder=2))
            ax.text(cx, cy - 0.02, str(num), ha="center", va="center", fontsize=11, zorder=3,
                    color="#b00000" if pips(num) == 5 else INK, fontweight="bold")
            ax.text(cx, cy - 0.28, "·" * pips(num), ha="center", va="center", fontsize=8, zorder=3,
                    color="#b00000" if pips(num) == 5 else INK)
        else:
            ax.text(cx, cy, RES_DE[res], ha="center", va="center", fontsize=8, color=INK, zorder=2)
    for edge, htype in board.harbors:
        _draw_harbor(ax, edge, htype)
    for edge, player in board.roads.items():
        a, b = (GEOMETRY.vertex_pos[v] for v in edge)
        ax.plot([a[0], b[0]], [a[1], b[1]], color=INK, lw=7.5, zorder=5, solid_capstyle="round")
        ax.plot([a[0], b[0]], [a[1], b[1]], color=PLAYER_COLORS[player], lw=5, zorder=6, solid_capstyle="round")
    for v, (player, kind) in board.buildings.items():
        x, y = GEOMETRY.vertex_pos[v]
        col = PLAYER_COLORS[player]
        if kind == "city":
            ax.add_patch(Rectangle((x - 0.24, y - 0.24), 0.48, 0.48, facecolor=col, edgecolor=INK, lw=2, zorder=7))
        else:
            ax.add_patch(Circle((x, y), 0.19, facecolor=col, edgecolor=INK, lw=2, zorder=7))
    # legend
    ly = -5.75
    for i, (p, col) in enumerate(PLAYER_COLORS.items()):
        ax.add_patch(Circle((-5.6 + i * 1.5, ly), 0.15, facecolor=col, edgecolor=INK, lw=1.5, zorder=8))
        ax.text(-5.35 + i * 1.5, ly, p, va="center", fontsize=9, color=INK)
    ax.text(5.9, ly, "● Siedlung   ■ Stadt", ha="right", va="center", fontsize=9, color=INK)
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_reference(path):
    """Naming scheme: hex labels, corner names (shown on C3) and an example for edges."""
    fig, ax = _new_axes("Benennung: Felder A1–E3, Ecken N/NE/SE/S/SW/NW, Kanten z.B. C3:N-NE")
    for h in HEXES:
        ax.add_patch(_hex_polygon(h, facecolor="#ffe4c2", edgecolor="#8B4513", lw=1.5, zorder=1))
        cx, cy = hex_center(h)
        ax.text(cx, cy, h, ha="center", va="center", fontsize=14, color=INK, fontweight="bold", zorder=2)
    cx, cy = hex_center("C3")
    for c in CORNERS:
        x, y = corner_point("C3", c)
        ax.add_patch(Circle((x, y), 0.07, color="#960000", zorder=3))
        ax.text(cx + (x - cx) * 0.68, cy + (y - cy) * 0.68, c, ha="center", va="center", fontsize=9,
                color="#960000", fontweight="bold", zorder=3)
    a, b = corner_point("C3", "N"), corner_point("C3", "NE")
    ax.plot([a[0], b[0]], [a[1], b[1]], color="#960000", lw=4, zorder=3)
    ax.text(-5.9, -5.75, "Reihen von oben nach unten (3-4-5-4-3 Felder), Felder von links nach rechts.\n"
            "Spitze Felder nach oben. Jede Ecke/Kante darf über jedes angrenzende Feld benannt werden.",
            fontsize=8.5, color=INK, va="center")
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
