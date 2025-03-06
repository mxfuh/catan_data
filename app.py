import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go

from catan_functions import fit_excel_into_df
from catan_functions import create_hover_data



# stadia maps api key mit url
stadia_api_key = "de89fcde-b15e-4db3-a3d6-08e486eb9af6"
api_style_url = "https://tiles.stadiamaps.com/styles/stamen_watercolor.json?api_key=de89fcde-b15e-4db3-a3d6-08e486eb9af6"

##############################################                 
########## get data from excel file ##########
##############################################

data = fit_excel_into_df("catan_data.xlsx")

##############################################
##############################################




##############################################################
############# CREATE INTERACTIVE AND COOL MAP ################
##############################################################

# create hover data
data_unique = create_hover_data(data)

# Use the custom CSS class in your title
st.markdown(
    """
    <style>
      @font-face {
        font-family: 'Castellar';
        src: url('https://raw.githubusercontent.com/mxfuh/catan_data/main/font/castellar-regular.woff2') format('woff2'),
             url('https://raw.githubusercontent.com/mxfuh/catan_data/main/font/castellar-regular.ttf') format('truetype');
        font-weight: normal;
        font-style: normal;
        font-display: swap;
      }
    </style>
    <h1 style="text-align: center; font-family: 'Castellar', serif; color: #4B2E1F; font-size: 64px;">Bwanastan</h1>
    """,
    unsafe_allow_html=True
)



# st.markdown(
#     """<h1 style='text-align: center; 
#     font-family: \"Castellar\", serif;
#     color: #4B2E1F; 
#     font-size: 64px;
#     '>Bwanastan</h1>""",
#     unsafe_allow_html=True
# )

# map code (using scatter_mapbox as an example)
fig = px.scatter_mapbox(
    data_unique,
    lat='latitude',
    lon='longitude',
    hover_name='loc',
    hover_data={'Details': True, 'latitude': False, 'longitude': False},
    mapbox_style="open-street-map",  # You can choose your preferred style
    zoom=4,
    height=400
)

# Adjust the layout size
fig.update_layout(
    mapbox=dict(
        style=api_style_url,
        # If required, include the access token (some custom styles need this, others don't)
        accesstoken=stadia_api_key),
    width=650,
    height=400,
    margin=dict(l=2, r=2, t=2, b=2)
)

# Create an HTML snippet with updated CSS for responsiveness and centering.
html_string = f"""
<html>
  <head>
    <style>
      /* Responsive Victorian frame */
      .victorian-frame {{
          box-sizing: border-box;  /* Include border and padding in the element's width */
        border: 5px solid #8B4513;      /* Brown border for vintage feel */
        border-radius: 15px;            /* Rounded corners */
        padding: 10px;
        box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3); /* Drop shadow */
        background-color: #fdfaf6;      /* Warm, light background */
        width: 100%;                    /* Full width */
        max-width: 670px;              /* Maximum width matching your figure */
        margin: 30px auto;              /* Center horizontally with top/bottom margin */
      }}
      body {{
          margin: 0;
          padding: 0;
      }}
      /* Media query for smaller screens */
      @media (max-width: 1200px) {{
          .victorian-frame {{
              max-width: 100%;
          }}
      }}
    </style>
  </head>
  <body>
    <div class="victorian-frame">
      {fig.to_html(include_plotlyjs='cdn', full_html=False)}
    </div>
  </body>
</html>
"""

# Embed the HTML with the custom frame in your Streamlit app
components.html(html_string,height=510, width=680 ) # 



#####################################################
#####################################################





