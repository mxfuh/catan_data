import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px


cols = list(pd.read_excel("catan_data.xlsx").iloc[0,:])
data = pd.read_excel("catan_data.xlsx").iloc[1:,:]
data.columns = cols


# Split 'geoloc' into two columns 'latitude' and 'longitude'
data[['latitude', 'longitude']] = data['geoloc'].str.split(', ', expand=True)
data['latitude'] = pd.to_numeric(data['latitude'])
data['longitude'] = pd.to_numeric(data['longitude'])


# Calculate mean scores for each player at each location
mean_scores = data.groupby(['loc', 'player'])['score'].mean().unstack().fillna(0)
# Create a hover text column
hover_text = mean_scores.apply(lambda row: '\n'.join([f"{player}: {score:.2f}" for player, score in row.items()]), axis=1)
hover_text = hover_text.rename('mean_scores')
# Merge this with your original data
data = data.merge(hover_text, on='loc', how='left')
# Ensure unique entries for locations to avoid plot duplication
data_unique = data.drop_duplicates(subset=['loc'])


# Create a Plotly map with enhanced hover information
fig = px.scatter_geo(data_unique,
                     lat='latitude',
                     lon='longitude',
                     hover_name='loc', 
                     hover_data={'mean_scores': True, 'latitude': False, 'longitude': False}  # Include mean scores in hoverinfo
                     )

# Integrate with Streamlit
st.title('Interactive Map Dashboard')
st.plotly_chart(fig)