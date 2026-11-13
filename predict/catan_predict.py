"""Pre-game → post-game prediction for Catan (Städte & Ritter).

Sobald für ein Spiel alle drei Pre-Game-Zeilen erfasst sind, aber noch kein Score, sagt ein NN-Ensemble
Score und Sondersiegpunkte voraus (Platz = Rang des Scores), einmal mit und einmal ohne Spieler-Variable.

    python predict/catan_predict.py --data catan_data.xlsx --state STATE_DIR [--notify] [--force]

Ohne --notify wird die Nachricht nur ausgegeben. Das Modell wird nur neu trainiert, wenn sich die
abgeschlossenen Spiele geändert haben; jede Prognose geht pro Spiel (und Stand der Pre-Game-Daten) einmal raus.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

PLAYERS = ["MF", "JHC", "PF"]
RESOURCES = ["wood", "clay", "sheep", "grain", "ore", "paper", "coin", "fabric"]
PORTS = ["wood", "clay", "sheep", "grain", "ore", "gen"]
# Was vor dem Spiel feststehen muss, damit eine Prognose rausgeht
PRE_GAME = (["position", "desert", "sum", "count_num", "count_res"]
            + [f"p_sum_{r}" for r in RESOURCES]
            + [f"port_{p}" for p in PORTS] + [f"prox_port_{p}" for p in PORTS])
TARGETS = ["score", "special"]
START = {"first": 1, "second": 2, "third": 3}

# Gewählt per gruppierter 5-fach-CV (Spiele bleiben zusammen), siehe Commit-Beschreibung
HIDDEN, DROPOUT, WEIGHT_DECAY, EPOCHS, LR, SEEDS = 64, 0.3, 1.0, 80, 3e-3, 5
VARIANTS = {"with_player": "Mit Spieler-Info", "no_player": "Ohne Spieler-Info (nur Setzung)"}


##############################################
############# Daten & Features ###############
##############################################

def load(path):
    from catan_functions import fit_excel_into_df

    data = fit_excel_into_df(path)
    for col in [c for c in data if c.startswith("share_")]:
        data[col] = data[col].fillna(0)  # Rohstoff, den niemand produziert
    for val in ["outer", "second", "center"]:
        data[f"desert_{val}"] = (data["desert"] == val).astype(int)
    for val in ["first", "second", "third"]:
        data[f"position_{val}"] = (data["position"] == val).astype(int)
    for val in PLAYERS:
        data[f"player_{val}"] = (data["player"] == val).astype(int)
    data["sum_resources"] = data[[f"p_sum_{r}" for r in RESOURCES[:5]]].sum(axis=1)
    data["sum_tradegoods"] = data[[f"p_sum_{r}" for r in RESOURCES[5:]]].sum(axis=1)
    data["std_resources"] = data[[f"p_sum_{r}" for r in RESOURCES]].std(axis=1)
    # eigene Gesamtproduktion minus Schnitt der beiden Gegner
    table = data.groupby("game_id")["sum"].transform("sum")
    data["sum_rel"] = data["sum"] - (table - data["sum"]) / 2

    # Ein Spiel ist nutzbar, wenn genau die drei Spieler mit vollständigen Pre-Game-Daten drin sind
    pre_ok = data[PRE_GAME].notna().all(axis=1) & data["player"].isin(PLAYERS)
    per_game = data.assign(pre_ok=pre_ok).groupby("game_id").agg(
        n=("player", "size"), n_players=("player", "nunique"), pre_ok=("pre_ok", "all"),
        complete=("complete", "all"), no_score=("score", lambda s: s.isna().all()))
    usable = (per_game["n"] == 3) & (per_game["n_players"] == 3) & per_game["pre_ok"]
    data["train"] = data["game_id"].map(usable & per_game["complete"]).astype(bool)
    data["pending"] = data["game_id"].map(usable & per_game["no_score"]).astype(bool)
    return data.sort_values(["game_id", "position"]).reset_index(drop=True)


def feature_cols(data, with_player):
    cols = [c for c in data if c.startswith(("p_sum_", "share_", "port_", "prox_port_", "desert_", "position_"))]
    cols += ["sum", "count_num", "count_res", "sum_resources", "sum_tradegoods", "std_resources", "sum_rel"]
    if with_player:
        cols += [f"player_{p}" for p in PLAYERS]
    return cols


##############################################
################# Modell #####################
##############################################

def _net(n_in):
    import torch.nn as nn
    return nn.Sequential(
        nn.Linear(n_in, HIDDEN), nn.Softplus(), nn.Dropout(DROPOUT),
        nn.Linear(HIDDEN, HIDDEN // 2), nn.Softplus(), nn.Dropout(DROPOUT),
        nn.Linear(HIDDEN // 2, len(TARGETS)),
    )


def fit(X, Y):
    """Ensemble aus SEEDS Netzen; Y darf NaN enthalten (special fehlt in frühen Spielen) → maskierter Loss."""
    import torch

    mx, sx = X.mean(0), X.std(0)
    sx[sx == 0] = 1
    my, sy = np.nanmean(Y, 0), np.nanstd(Y, 0)
    Xt = torch.tensor((X - mx) / sx, dtype=torch.float32)
    mask = torch.tensor(~np.isnan(Y), dtype=torch.float32)
    Yt = torch.tensor(np.nan_to_num((Y - my) / sy), dtype=torch.float32)
    nets = []
    for seed in range(SEEDS):
        torch.manual_seed(seed)
        net = _net(X.shape[1])
        opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        for _ in range(EPOCHS):
            net.train()
            opt.zero_grad()
            loss = (((net(Xt) - Yt) ** 2 * mask).sum(0) / mask.sum(0)).mean()
            loss.backward()
            opt.step()
        nets.append(net.eval())
    return {"nets": nets, "mx": mx, "sx": sx, "my": my, "sy": sy}


def predict(model, X):
    import torch

    Xt = torch.tensor((X - model["mx"]) / model["sx"], dtype=torch.float32)
    with torch.no_grad():
        out = np.mean([net(Xt).numpy() for net in model["nets"]], axis=0)
    return out * model["sy"] + model["my"]


def oof_predictions(data, cols, folds=5):
    """Jedes Spiel wird von einem Modell vorhergesagt, das es nicht gesehen hat (Spiele bleiben zusammen)."""
    games = data["game_id"].unique()
    np.random.default_rng(0).shuffle(games)
    pred = np.full((len(data), len(TARGETS)), np.nan)
    for fold in np.array_split(games, folds):
        test = data["game_id"].isin(fold).values
        model = fit(data.loc[~test, cols].values.astype(float), data.loc[~test, TARGETS].values.astype(float))
        pred[test] = predict(model, data.loc[test, cols].values.astype(float))
    return pred


def out_of_fold(data, cols, folds=5):
    """Ehrliche Fehlerschätzung aus den Out-of-Fold-Prognosen."""
    pred = oof_predictions(data, cols, folds)
    resid = data["score"].values - pred[:, 0]
    baseline = np.abs(data["score"] - data["score"].mean()).mean()
    return {"mae": float(np.abs(resid).mean()), "sigma": float(resid.std()), "mae_baseline": float(baseline)}


def train_all(data):
    train = data[data["train"]].reset_index(drop=True)
    models = {}
    for variant in VARIANTS:
        cols = feature_cols(train, variant == "with_player")
        model = fit(train[cols].values.astype(float), train[TARGETS].values.astype(float))
        model.update(cols=cols, n_games=int(train["game_id"].nunique()), **out_of_fold(train, cols))
        models[variant] = model
    return models


def win_probs(scores, sigma, draws=20000):
    """Siegchance: Prognose + normalverteilter Fehler in der Größe des Out-of-Fold-Fehlers."""
    sims = scores + np.random.default_rng(1).normal(0, sigma, (draws, len(scores)))
    return np.bincount(sims.argmax(1), minlength=len(scores)) / draws


##############################################
########### Zustand & Nachricht ##############
##############################################

def file_sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def frame_sha(df):
    return hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()


def load_models(state_dir, sig):
    import torch
    path = os.path.join(state_dir, "model.pt")
    if not os.path.exists(path):
        return None
    saved = torch.load(path, weights_only=False)
    if saved.get("sig") != sig:
        return None
    models = saved["models"]
    for variant, model in models.items():
        nets = []
        for sd in model["nets"]:
            net = _net(len(model["cols"]))
            net.load_state_dict(sd)
            nets.append(net.eval())
        model["nets"] = nets
    return models


def save_models(state_dir, sig, models):
    import torch
    plain = {v: dict(m, nets=[n.state_dict() for n in m["nets"]]) for v, m in models.items()}
    torch.save({"sig": sig, "models": plain}, os.path.join(state_dir, "model.pt"))


def game_predictions(game, models):
    return {v: predict(m, game[m["cols"]].values.astype(float)) for v, m in models.items()}


def format_message(game, models, preds):
    first = game.iloc[0]
    lines = [f"🎲 **Catan-Prognose** · Saison {first['season']}, Spiel {first['game']} · {first['loc']}", "", "**Setzung**"]
    # Gesamtproduktion = Summe der Würfelfrequenzen aller Felder (pro 36 Würfe)
    for _, row in game.sort_values("position").iterrows():
        lines.append(f"{START[row['position']]}. {row['player']:<3} Gesamtproduktion {row['sum']:.0f}"
                     f" ({row['sum_resources']:.0f} Rohstoffe + {row['sum_tradegoods']:.0f} Handelswaren)")
    for variant, title in VARIANTS.items():
        model = models[variant]
        pred = preds[variant]
        probs = win_probs(pred[:, 0], model["sigma"])
        lines += ["", f"**{title}**"]
        for rank, i in enumerate(np.argsort(-pred[:, 0]), start=1):
            row = game.iloc[i]
            lines.append(f"{rank}. {row['player']:<3} {pred[i, 0]:5.1f} Punkte (davon {pred[i, 1]:.1f} Sonder-SP)"
                         f" · Sieg {probs[i]:.0%}")
    m = models["with_player"]
    lines += ["", f"Modell: NN-Ensemble, trainiert auf {m['n_games']} Spielen. Typischer Fehler im Test ±"
                  f"{m['mae']:.2f} Punkte mit / ±{models['no_player']['mae']:.2f} ohne Spieler-Info "
                  f"(immer den Mittelwert tippen: ±{m['mae_baseline']:.2f})."]
    return "\n".join(lines)


def notify(text, subject, cfg):
    """Discord + Mail über den Mailbot auf dem VPS (Empfänger aus der Config im State-Ordner)."""
    import discord_notify
    import graph

    discord_notify.send(text)
    msg = {
        "subject": subject,
        "internetMessageHeaders": [{"name": "X-Claude-Mailbot", "value": "1"}],
        "body": {"contentType": "Text", "content": text.replace("**", "")},
        "toRecipients": [{"emailAddress": {"address": a}} for a in cfg["mail_to"]],
    }
    since = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    err = None
    for wait in MAIL_RETRY_WAITS + [None]:
        try:
            graph.request("POST", "/me/sendMail", body={"saveToSentItems": True, "message": msg})
            return
        except BaseException as e:  # graph.request beendet mit SystemExit; Discord-Nachricht ist dann schon raus
            err = e
        # Nur Gateway-Fehler/Timeouts wiederholen; bei 504 kann die Mail trotzdem raus sein
        if wait is None or not _transient(err):
            break
        time.sleep(wait)
        if _already_sent(graph, subject, since):
            return
    discord_notify.send(f"⚠️ Catan-Prognose: Mailversand fehlgeschlagen: {err}"[:1900])


MAIL_RETRY_WAITS = [60, 300, 900]  # Sekunden vor den Wiederholungen (Timer startet den Dienst solange nicht neu)


def _transient(e):
    msg = str(e)
    return any(f"-> {c}:" in msg for c in (500, 502, 503, 504)) or "timed out" in msg.lower() \
        or isinstance(e, (TimeoutError, ConnectionError, OSError))


def _already_sent(graph, subject, since):
    try:
        r = graph.request("GET", "/me/mailFolders/sentitems/messages?$select=subject&$top=10"
                                 f"&$filter=sentDateTime%20ge%20{since}")
        return any(m.get("subject") == subject for m in r.get("value", []))
    except BaseException:
        return False


##############################################
######## Prognose-Archiv (Form-Tab) ##########
##############################################

# Jede gesendete Prognose landet in predict/predictions.csv (source=live). Für ältere Spiele gibt es
# rückgerechnete Out-of-Fold-Werte (source=oof, computed = Rechendatum), die das Dashboard markiert.
PRED_FILE = os.path.join(REPO, "predict", "predictions.csv")
PRED_FIELDS = ["season", "game", "player", "variant", "pred_score", "source", "computed"]


def _row_key(row):
    return (int(row["season"]), int(row["game"]), row["player"], row["variant"], row["source"])


def read_predictions():
    import csv
    if not os.path.exists(PRED_FILE):
        return []
    return list(csv.DictReader(open(PRED_FILE, encoding="utf-8")))


def write_predictions(rows):
    import csv
    rows = sorted({_row_key(r): r for r in rows}.values(), key=_row_key)
    with open(PRED_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRED_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows({k: r[k] for k in PRED_FIELDS} for r in rows)


def live_rows(game, preds, day):
    return [{"season": int(row["season"]), "game": int(row["game"]), "player": row["player"], "variant": variant,
             "pred_score": f"{pred[i, 0]:.2f}", "source": "live", "computed": day}
            for variant, pred in preds.items() for i, (_, row) in enumerate(game.iterrows())]


def sync_predictions(state):
    """Live-Prognosen aus dem State ins Archiv schreiben und pushen. Klappt der Push nicht (z.B. weil parallel
    gepusht wurde), holt run.sh beim nächsten Lauf main neu und dieser Schritt versucht es erneut."""
    import subprocess
    live = [r for rows in state.get("predictions", {}).values() for r in rows]
    if not live:
        return
    old = read_predictions()
    write_predictions(old + live)  # gleiche Schlüssel: der State (neueste Prognose) gewinnt
    if read_predictions() == old:
        return
    git = ["git", "-C", REPO]
    try:
        subprocess.run(git + ["add", PRED_FILE], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "Prognose-Archiv aktualisiert",
                              "-m", "Automatisch vom Prognose-Lauf (predict/catan_predict.py)."], check=True)
        subprocess.run(git + ["push", "-q", "origin", "HEAD:main"], check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Prognose-Archiv nicht gepusht, nächster Lauf versucht es erneut: {e}", file=sys.stderr)


def backfill(data, day):
    """Out-of-Fold-Prognosen für alle abgeschlossenen Spiele ins Archiv schreiben (einmalig/bei Bedarf)."""
    train = data[data["train"]].reset_index(drop=True)
    rows = [r for r in read_predictions() if r["source"] != "oof"]
    for variant in VARIANTS:
        pred = oof_predictions(train, feature_cols(train, variant == "with_player"))
        rows += [{"season": int(row["season"]), "game": int(row["game"]), "player": row["player"],
                  "variant": variant, "pred_score": f"{pred[i, 0]:.2f}", "source": "oof", "computed": day}
                 for i, row in train.iterrows()]
    write_predictions(rows)
    print(f"{train['game_id'].nunique()} Spiele rückgerechnet → {PRED_FILE}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=os.path.join(REPO, "catan_data.xlsx"))
    p.add_argument("--state", required=True)
    p.add_argument("--notify", action="store_true", help="Discord + Mail senden statt nur ausgeben")
    p.add_argument("--force", action="store_true", help="auch bei unveränderter Excel prüfen")
    p.add_argument("--backfill", action="store_true",
                   help="Out-of-Fold-Prognosen aller abgeschlossenen Spiele nach predict/predictions.csv schreiben")
    a = p.parse_args()
    if a.backfill:
        return backfill(load(a.data), datetime.date.today().isoformat())

    os.makedirs(a.state, exist_ok=True)
    state_path = os.path.join(a.state, "state.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {"sent": {}}
    if a.notify:
        sync_predictions(state)
    sha = file_sha(a.data)
    if sha == state.get("xlsx_sha") and not a.force:
        return  # Excel unverändert → nichts zu tun (torch wird gar nicht erst geladen)
    cfg = {}
    if a.notify:
        cfg = json.load(open(os.path.join(a.state, "config.json"), encoding="utf-8"))
        sys.path.insert(0, os.path.expanduser(cfg["mailbot_dir"]))

    try:
        data = load(a.data)
        pending = data[data["pending"]]
        if not pending.empty:
            sig = frame_sha(data.loc[data["train"], ["game_id", "player"] + PRE_GAME + TARGETS])
            models = load_models(a.state, sig)
            if models is None:
                models = train_all(data)
                save_models(a.state, sig, models)
            for game_id, game in pending.groupby("game_id"):
                key, fp = str(game_id), frame_sha(game[["player"] + PRE_GAME])
                if state["sent"].get(key) == fp:
                    continue
                game = game.reset_index(drop=True)
                preds = game_predictions(game, models)
                text = format_message(game, models, preds)
                if key in state["sent"]:
                    text = text.replace("Catan-Prognose**", "Catan-Prognose** (aktualisiert)", 1)
                subject = f"Catan-Prognose Saison {game['season'].iloc[0]}, Spiel {game['game'].iloc[0]}"
                if a.notify:
                    notify(text, subject, cfg)
                else:
                    print(text + "\n")
                state["sent"][key] = fp
                if a.notify:
                    day = datetime.date.today().isoformat()
                    state.setdefault("predictions", {})[key] = live_rows(game, preds, day)
    except Exception as e:
        # Einmal pro Excel-Stand melden, nicht alle paar Minuten erneut
        if a.notify:
            import discord_notify
            discord_notify.send(f"⚠️ Catan-Prognose fehlgeschlagen: {type(e).__name__}: {e}"[:1900])
        state["xlsx_sha"] = sha
        json.dump(state, open(state_path, "w", encoding="utf-8"), indent=1)
        raise
    state["xlsx_sha"] = sha
    json.dump(state, open(state_path, "w", encoding="utf-8"), indent=1)
    if a.notify:
        sync_predictions(state)


if __name__ == "__main__":
    main()
