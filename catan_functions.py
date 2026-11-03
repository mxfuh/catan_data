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

