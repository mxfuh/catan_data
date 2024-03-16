import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


cols = list(pd.read_excel("catan_data.xlsx").iloc[0,:])
data = pd.read_excel("catan_data.xlsx").iloc[1:,:]
data.columns = cols


# Split 'geoloc' into two columns 'latitude' and 'longitude'
data[['latitude', 'longitude']] = data['geoloc'].str.split(', ', expand=True)
data['latitude'] = pd.to_numeric(data['latitude'])
data['longitude'] = pd.to_numeric(data['longitude'])


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


# Create a Plotly map with enhanced hover information
fig = px.scatter_geo(data_unique,
                     lat='latitude',
                     lon='longitude',
                     hover_name='loc', 
                     hover_data={'Details': True, 'latitude': False, 'longitude': False}  # Include mean scores in hoverinfo
                     )


# Integrate with Streamlit
st.title('Bwanastan (ab 2022)')
st.plotly_chart(fig)