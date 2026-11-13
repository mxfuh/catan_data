def fit_excel_into_df(excel_file):
    import pandas as pd
    import numpy as np
    
    # Read data and fix column names.
    cols = list(pd.read_excel(excel_file).iloc[0, :])
    data = pd.read_excel(excel_file).iloc[1:, :]
    data.columns = cols

    # Ensure numeric columns are numeric; placeholders like "-" or "?" become NaN.
    text_cols = ["Session", "loc", "geoloc", "player", "position", "desert"]
    for col in data.columns:
        if col not in text_cols:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # Drop stray rows (e.g. only a season number filled in).
    data = data.dropna(subset=["season", "game", "player"]).copy()
    data[["season", "game"]] = data[["season", "game"]].astype(int)
    data["place"] = data["place"].astype("Int64")

    # Pre-game data may be pushed before the game is finished: a game only counts once score and place are entered.
    data["complete"] = data["score"].notna() & data["place"].notna()

    # Create additional columns.
    data["game_id"] = data["season"] * 100 + data["game"]
    data["month"] = pd.to_datetime(data["Session"], errors="coerce").dt.month

    # Split 'geoloc' into 'latitude' and 'longitude' (reindex keeps two columns even if every geoloc is missing)
    data[['latitude', 'longitude']] = data['geoloc'].astype("string").str.split(', ', n=1, expand=True).reindex(columns=[0, 1])
    data['latitude'] = pd.to_numeric(data['latitude'], errors='coerce')
    data['longitude'] = pd.to_numeric(data['longitude'], errors='coerce')
    
    # Generate additional information columns.
    resources = []
    for colname in [col for col in data if "t_sum" in col]:
        resources.append(colname[6:])  # extract resource name
    for resource in resources:
        # Generate total production values (using min_count=1 so that groups with all NaN return NaN).
        data[f"t_sum_{resource}"] = data.groupby(["season", "game"])[f"p_sum_{resource}"].transform(
            lambda x: x.sum(min_count=1)
        )

        # Generate share of production values safely.
        data[f"share_{resource}"] = np.nan  # default to NaN
        mask = data[f"t_sum_{resource}"] != 0
        data.loc[mask, f"share_{resource}"] = (
            data.loc[mask, f"p_sum_{resource}"] / data.loc[mask, f"t_sum_{resource}"]
        )
    
    # Generate points column.
    data["points"] = data["place"].map({1: 2, 2: 1, 3: 0})
    
    # Sort by game_id to ensure cumulative sums are in order.
    data = data.sort_values("game_id")
    
    # Compute cumulative points (overall and year-to-date) in a vectorized manner.
    data["points_cum"] = data.groupby("player")["points"].cumsum()
    data["points_cum_ytd"] = data.groupby(["season", "player"])["points"].cumsum()
    
    return data




def create_hover_data(data):
    # Only finished games count for scores, game counts and wins
    played = data[data['complete']]
    # Calculate mean scores for each player at each location
    mean_scores = played.groupby(['loc', 'player'])['score'].mean().unstack().fillna(0)
    location_count = played['loc'].value_counts() / 3
    victories = played[played['place'] == 1].groupby(['loc', 'player']).size().unstack(fill_value=0)
    # Create a hover text column
    hover_text_scores = mean_scores.apply(lambda row: '<br>'.join([f"{player}: {score:.2f}" for player, score in row.items()]), axis=1)
    hover_text_victories = victories.apply(lambda row: '<br>'.join([f"{player} Wins: {wins}" for player, wins in row.items()]), axis=1)
    hover_text = '<br><br>' + "<b>Punktedurchschnitt:</b> " + "<br>" + hover_text_scores + '<br><br>' + '<b>Anzahl Spiele:</b> ' + location_count.reindex(hover_text_scores.index).astype(int).apply(lambda x: f"{x}") + "<br><br>" + hover_text_victories
    # Merge this with your original data
    data = data.merge(hover_text.rename('Details'), on='loc', how='left')
    data['Details'] = data['Details'].fillna('<br><br>Noch kein Spiel abgeschlossen')
    # Ensure unique entries for locations to avoid plot duplication
    data_unique = data.drop_duplicates(subset=['loc'])

    return data_unique


##############################################
######## Ruhmeshalle, Tabellen, Karte ########
##############################################

TRADE_GOODS = ["paper", "coin", "fabric"]
START_LABELS = {"first": "1. Position", "second": "2. Position", "third": "3. Position"}


def _played(data):
    """Finished games only, sorted chronologically and by place."""
    return data[data["complete"]].sort_values(["game_id", "place"])


def location_rulers(data):
    """Per location: number of finished games and its ruler (player with the most wins there)."""
    import pandas as pd
    played = _played(data)
    games = played.groupby("loc")["game_id"].nunique()
    wins = played[played["place"] == 1].groupby(["loc", "player"]).size().unstack(fill_value=0)
    rows = []
    for loc in data["loc"].dropna().unique():
        if loc in wins.index and wins.loc[loc].max() > 0:
            w = wins.loc[loc]
            top = w[w == w.max()]
            ruler = top.index[0] if len(top) == 1 else "Umkämpft"
            ruler_wins = int(w.max())
        else:
            ruler, ruler_wins = "Unerobert", 0
        rows.append({"loc": loc, "Spiele": int(games.get(loc, 0)), "Herrscher": ruler, "Herrscher_Siege": ruler_wins})
    return pd.DataFrame(rows, columns=["loc", "Spiele", "Herrscher", "Herrscher_Siege"])


def _date(row):
    import pandas as pd
    date = pd.to_datetime(row.get("Session"), errors="coerce")
    return "" if pd.isna(date) else date.strftime("%d.%m.%Y")


def _where(row, game=True):
    """'Ort · Saison 2024, Spiel 5 · 12.03.2024' (without season/game if game=False)."""
    parts = [str(row["loc"])]
    if game:
        parts.append(f"Saison {row['season']}, Spiel {row['game']}")
    if _date(row):
        parts.append(_date(row))
    return " · ".join(parts)


def _times(n):
    return f" · {n}× erreicht" if n > 1 else ""


def _most_recent(rows):
    return rows.sort_values("game_id").iloc[-1]


def _longest_runs(played):
    """Longest run of wins and of games without a win, per player: {player: (length, last row of the run)}."""
    wins, droughts = {}, {}
    for player, rows in played.groupby("player"):
        cur_w = cur_d = 0
        for _, row in rows.sort_values("game_id").iterrows():
            if row["place"] == 1:
                cur_w, cur_d = cur_w + 1, 0
                if cur_w >= wins.get(player, (0, None))[0]:
                    wins[player] = (cur_w, row)
            else:
                cur_w, cur_d = 0, cur_d + 1
                if cur_d >= droughts.get(player, (0, None))[0]:
                    droughts[player] = (cur_d, row)
    return wins, droughts


def _best_run(runs):
    """Longest run over all players; ties go to the most recent one."""
    if not runs:
        return None
    return max(runs.items(), key=lambda kv: (kv[1][0], kv[1][1]["game_id"]))


def hall_of_fame(data):
    """Records over all finished games. Each record: title, value, unit, holder (player), detail."""
    played = _played(data)
    if played.empty:
        return []
    records = []

    def rec(title, value, unit, holder, detail):
        records.append(dict(title=title, value=value, unit=unit, holder=holder, detail=detail))

    first = played[played["place"] == 1].set_index("game_id")
    second = played[played["place"] == 2].set_index("game_id")
    margin = (first["score"] - second["score"]).dropna()

    if not margin.empty:
        # Erdrutschsieg: largest lead of the winner over second place
        top = margin[margin == margin.max()]
        gid = top.index.max()
        w = first.loc[gid]
        rec("Erdrutschsieg", f"+{int(margin.max())}", "Punkte Vorsprung", w["player"],
            f"{int(w['score'])} : {int(second.loc[gid, 'score'])} · {_where(w)}{_times(len(top))}")

        # Haaresbreite: smallest lead; holder = who won that tightly most often
        low = margin[margin == margin.min()]
        by_player = first.loc[low.index, "player"].value_counts()
        n = int(margin.min())
        rec("Haaresbreite", f"{n}", "Punkt Vorsprung" if n == 1 else "Punkte Vorsprung", by_player.index[0],
            f"{len(low)}× so knapp entschieden, davon {by_player.iloc[0]}× für {by_player.index[0]}")

    wins, droughts = _longest_runs(played)
    best = _best_run(wins)
    if best:
        player, (n, row) = best
        rec("Siegesserie", f"{n}", "Siege in Folge", player, f"bis {_where(row)}")
    worst = _best_run(droughts)
    if worst:
        player, (n, row) = worst
        rec("Durststrecke", f"{n}", "Spiele ohne Sieg in Folge", player, f"bis {_where(row)}")

    losers = played[played["place"] > 1]
    if not losers.empty:
        top = losers[losers["score"] == losers["score"].max()]
        row = _most_recent(top)
        rec("Bitterste Niederlage", f"{int(row['score'])}", f"Punkte und trotzdem Platz {int(row['place'])}",
            row["player"], _where(row) + _times(len(top)))

    winners = played[(played["place"] == 1) & played["sum"].notna()]
    if not winners.empty:
        top = winners[winners["sum"] == winners["sum"].min()]
        row = _most_recent(top)
        rec("Aus dem Nichts", f"{row['sum']:.0f}", "Gesamtproduktion und trotzdem Sieg", row["player"],
            _where(row) + _times(len(top)))

    last = played[(played["place"] == 3) & played["sum"].notna()]
    if not last.empty:
        top = last[last["sum"] == last["sum"].max()]
        row = _most_recent(top)
        rec("Reich, aber glücklos", f"{row['sum']:.0f}", "Gesamtproduktion und trotzdem Letzter", row["player"],
            _where(row) + _times(len(top)))

    special = played[played["special"].notna()]
    if not special.empty:
        top = special[special["special"] == special["special"].max()]
        row = _most_recent(top)
        rec("Meister der Sonderpunkte", f"{row['special']:.0f}", "Sondersiegpunkte in einem Spiel", row["player"],
            _where(row) + _times(len(top)))

    # Glorreichstes Turnier: most wins in one session (same date and place, often several days); fewer games wins ties
    sessions = played.assign(day=played["Session"].astype(str))
    evening = sessions.groupby(["day", "loc"]).agg(n=("game_id", "nunique"), last=("game_id", "max"))
    ev = sessions[sessions["place"] == 1].groupby(["day", "loc", "player"]).size().rename("w").reset_index()
    ev = ev.join(evening, on=["day", "loc"])
    if not ev.empty:
        best_ev = ev.sort_values(["w", "n", "last"], ascending=[False, True, False]).iloc[0]
        when = sessions[sessions["game_id"] == best_ev["last"]].iloc[0]
        rec("Glorreichstes Turnier", f"{best_ev['w']} von {best_ev['n']}", "Spielen eines Treffens gewonnen",
            best_ev["player"], _where(when, game=False))

    def win_rates(keys, min_games):
        t = played.groupby(keys).agg(n=("game_id", "nunique"), w=("place", lambda s: int((s == 1).sum())))
        t = t[t["n"] >= min_games].copy()
        t["rate"] = t["w"] / t["n"]
        return t

    # Rekordsaison: best win rate within one season (at least 10 games)
    seasons = win_rates(["season", "player"], 10)
    if not seasons.empty:
        (season, player), row = max(seasons.iterrows(), key=lambda kv: (kv[1]["rate"], kv[0][0]))
        rec("Rekordsaison", f"{row['rate']:.0%}", "Siegquote in einer Saison", player,
            f"Saison {season}: {int(row['w'])} von {int(row['n'])} Spielen")

    # Uneinnehmbare Festung: best win rate at one location (at least 5 games there)
    places = win_rates(["loc", "player"], 5)
    if not places.empty:
        (loc, player), row = max(places.iterrows(), key=lambda kv: (kv[1]["rate"], kv[1]["n"]))
        rec("Uneinnehmbare Festung", f"{row['rate']:.0%}", "Siegquote an einem Ort", player,
            f"{loc}: {int(row['w'])} von {int(row['n'])} Spielen")

    top = played[played["score"] == played["score"].min()]
    row = _most_recent(top)
    rec("Tiefster Fall", f"{int(row['score'])}", "Punkte in einem Spiel", row["player"], _where(row) + _times(len(top)))

    return records


def eternal_table(data):
    """All-time standings per player, sorted by championship points (2/1/0 per game)."""
    import pandas as pd
    played = _played(data)
    if played.empty:
        return pd.DataFrame()
    t = played.groupby("player").agg(
        Spiele=("game_id", "nunique"),
        Siege=("place", lambda s: int((s == 1).sum())),
        Punkte=("score", "mean"),
        Platz=("place", "mean"),
        Meisterpunkte=("points", "sum"),
    )
    t.insert(2, "Siegquote", t["Siege"] / t["Spiele"])
    # Season titles: most championship points at season end; the running (latest) season does not count yet
    done = played[played["season"] < played["season"].max()]
    final = done.groupby(["season", "player"])["points"].sum().unstack(fill_value=0)
    titles = final.eq(final.max(axis=1), axis=0).sum() if not final.empty else pd.Series(dtype=int)
    t["Meistertitel"] = titles.reindex(t.index, fill_value=0).astype(int)
    t["Meisterpunkte"] = t["Meisterpunkte"].astype(int)
    t = t.rename(columns={"Punkte": "Ø Punkte", "Platz": "Ø Platz"})
    t = t.sort_values(["Meisterpunkte", "Siege"], ascending=False)
    t.index.name = "Spieler"
    return t


def start_position_table(data):
    """Win rate, score and production by start position (finished games only)."""
    import pandas as pd
    played = _played(data).copy()
    if played.empty:
        return pd.DataFrame()
    played["goods"] = played[[f"p_sum_{g}" for g in TRADE_GOODS]].sum(axis=1, min_count=1)
    t = played.groupby("position").agg(
        Spiele=("game_id", "nunique"),
        Siegquote=("place", lambda s: (s == 1).mean()),
        Punkte=("score", "mean"),
        Platz=("place", "mean"),
        Produktion=("sum", "mean"),
        Handelswaren=("goods", "mean"),
    )
    t = t.reindex([p for p in START_LABELS if p in t.index]).rename(index=START_LABELS)
    t.index.name = "Startposition"
    return t.rename(columns={"Punkte": "Ø Punkte", "Platz": "Ø Platz",
                             "Produktion": "Ø Gesamtproduktion", "Handelswaren": "Ø Handelswaren"})



##############################################
################ Form-Tab ####################
##############################################

FORM_WINDOW = 5           # "derzeit": letzte 5 Spiele
FORM_HISTORY_WINDOW = 5  # Formkurve: gleiches Fenster wie die Form-Karten
FORM_VARIANTS = {"with_player": "Mit Spieler-Info", "no_player": "Ohne Spieler-Info"}


def form_table(data, pred_file):
    """Ist-Punkte minus Prognose je Spiel, Spieler und Variante. Echte (gesendete) Prognosen haben Vorrang;
    sonst die rückgerechnete Out-of-Fold-Prognose (oof=True, computed = Rechendatum)."""
    import os
    import pandas as pd
    if not os.path.exists(pred_file):
        return pd.DataFrame()
    preds = pd.read_csv(pred_file)
    preds["oof"] = preds["source"] == "oof"
    # live vor oof: nach oof sortieren und je Schlüssel den ersten Eintrag nehmen
    preds = preds.sort_values("oof").drop_duplicates(["season", "game", "player", "variant"])
    played = _played(data)[["game_id", "season", "game", "player", "score"]]
    t = played.merge(preds, on=["season", "game", "player"])
    t["resid"] = t["score"] - t["pred_score"]
    return t.sort_values(["variant", "player", "game_id"]).reset_index(drop=True)


def current_form(form):
    """Je Variante und Spieler: Schnitt der letzten FORM_WINDOW Spiele, die Spiele davor zum Vergleich."""
    import pandas as pd
    rows = []
    for (variant, player), g in form.groupby(["variant", "player"]):
        last, prev = g.tail(FORM_WINDOW), g.iloc[:-FORM_WINDOW].tail(FORM_WINDOW)
        rows.append({"variant": variant, "player": player, "form": last["resid"].mean(),
                     "prev": prev["resid"].mean() if len(prev) else float("nan"),
                     "last": list(last["resid"]), "oof": bool(last["oof"].any())})
    return pd.DataFrame(rows)


def form_history(form, window=FORM_HISTORY_WINDOW):
    """Gleitender Schnitt über window Spiele je Spieler; rolling_oof, wenn ein rückgerechneter Wert im Fenster ist."""
    t = form.copy()
    by = t.groupby(["variant", "player"])
    t["rolling"] = by["resid"].transform(lambda s: s.rolling(window, min_periods=window).mean())
    t["rolling_oof"] = by["oof"].transform(lambda s: s.rolling(window, min_periods=1).max()).astype(bool)
    return t


def form_by_season(form):
    """Ø Abweichung je Saison (Zeilen) und Spieler (Spalten) für jede Variante; Sternchen, wenn Rückrechnung drin."""
    out = {}
    for variant, g in form.groupby("variant"):
        mean = g.pivot_table(index="season", columns="player", values="resid", aggfunc="mean")
        oof = g.pivot_table(index="season", columns="player", values="oof", aggfunc="max").astype(bool)
        out[variant] = (mean, oof)
    return out
