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

# Create a Plotly map
fig = px.scatter_geo(data,
                     lat='latitude',
                     lon='longitude',
                     hover_name='loc', # this column will be displayed in the hover information
                     )

# Integrate with Streamlit
st.title('Interactive Map Dashboard')
st.plotly_chart(fig)