def fit_excel_into_df(excel_file):
    import pandas as pd
    import numpy as np
    # Read in the data and manage the column misfit
    cols = list(pd.read_excel(excel_file).iloc[0,:])
    data = pd.read_excel(excel_file).iloc[1:,:]
    data.columns = cols
    data["game_id"] = data["season"]*100 + data["game"]
    # Split 'geoloc' into two columns 'latitude' and 'longitude'
    data[['latitude', 'longitude']] = data['geoloc'].str.split(', ', expand=True)
    data['latitude'] = pd.to_numeric(data['latitude'])
    data['longitude'] = pd.to_numeric(data['longitude'])
    # generate total production values
    resources = ["wood","clay","sheep","grain","ore","paper","coin","fabric"]
    for resource in resources:
        data[f"t_sum_{resource}"] = data.groupby(["season", "game"])[f"p_sum_{resource}"].transform("sum")
    # generate cumulative scores
    data["points"] = data["place"].map({1:2,2:1,3:0})
    data["points_cum"] = np.nan #create col
    data["points_cum_ytd"] = np.nan #create col
    points_cum_jhc = data.loc[data["player"]=="JHC"].copy()
    points_cum_pf = data.loc[data["player"]=="PF"].copy()
    points_cum_mf = data.loc[data["player"]=="MF"].copy()
    for dude in [points_cum_jhc,points_cum_mf,points_cum_pf]:
        for i in dude.index:
            
            cutoff = dude.loc[dude.index==i]["game_id"].iloc[0]
            #kumulierte gesamtpunkte setzen
            dude.loc[dude.index==i,"points_cum"] = dude.loc[dude["game_id"]<=cutoff]["points"].sum()
            # kumulierte punkte seit jahresbeginn
            dude.loc[dude.index==i,"points_cum_ytd"] = dude.loc[(dude["game_id"]<=cutoff) & (dude["season"]==int(str(cutoff)[:4]))]["points"].sum()
    # altes data mit neuem ersetzen
    data = pd.concat([points_cum_jhc,points_cum_pf,points_cum_mf]).sort_index()
    #return result
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

