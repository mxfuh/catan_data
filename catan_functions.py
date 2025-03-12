def fit_excel_into_df(excel_file):
    import pandas as pd
    import numpy as np
    
    # Read data and fix column names.
    cols = list(pd.read_excel(excel_file).iloc[0, :])
    data = pd.read_excel(excel_file).iloc[1:, :]
    data.columns = cols
    
    # Create additional columns.
    data["game_id"] = data["season"] * 100 + data["game"]
    data["month"] = pd.to_datetime(data["Session"]).dt.month
    
    # Split 'geoloc' into 'latitude' and 'longitude'
    data[['latitude', 'longitude']] = data['geoloc'].str.split(', ', expand=True)
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
        
        # Ensure the columns are numeric.
        data[f"p_sum_{resource}"] = pd.to_numeric(data[f"p_sum_{resource}"], errors="coerce")
        data[f"t_sum_{resource}"] = pd.to_numeric(data[f"t_sum_{resource}"], errors="coerce")
        
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
    # Calculate mean scores for each player at each location
    mean_scores = data.groupby(['loc', 'player'])['score'].mean().unstack().fillna(0)
    location_count = data['loc'].value_counts() / 3
    victories = data[data['place'] == 1].groupby(['loc', 'player']).size().unstack(fill_value=0)
    # Create a hover text column
    hover_text_scores = mean_scores.apply(lambda row: '<br>'.join([f"{player}: {score:.2f}" for player, score in row.items()]), axis=1)
    hover_text_victories = victories.apply(lambda row: '<br>'.join([f"{player} Wins: {wins}" for player, wins in row.items()]), axis=1)
    hover_text = '<br><br>' + "<b>Punktedurchschnitt:</b> " + "<br>" + hover_text_scores + '<br><br>' + '<b>Anzahl Spiele:</b> ' + location_count.reindex(hover_text_scores.index).astype(int).apply(lambda x: f"{x}") + "<br><br>" + hover_text_victories
    # Merge this with your original data
    data = data.merge(hover_text.rename('Details'), on='loc', how='left')
    # Ensure unique entries for locations to avoid plot duplication
    data_unique = data.drop_duplicates(subset=['loc'])

    return data_unique

