import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go


# stadia maps api key
stadia_api_key = "de89fcde-b15e-4db3-a3d6-08e486eb9af6"
# Construct the style URL for Stadia Maps' "stamen-watercolor" style.
#style_url = f"https://basemaps-api.stadiamaps.com/v1/styles/stamen-watercolor/style.json?api_key={stadia_api_key}"
style_url = "https://tiles.stadiamaps.com/styles/stamen_watercolor.json"


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



# Use the custom CSS class in your title
st.markdown(
    """<h1 style='text-align: center; 
    font-family: \"Castellar\", serif;
    color: #4B2E1F; 
    font-size: 64px;
    '>Bwanastan</h1>""",
    unsafe_allow_html=True
)



# Your map code (using scatter_mapbox as an example)
fig = px.scatter_mapbox(
    data_unique,
    lat='latitude',
    lon='longitude',
    hover_name='loc',
    hover_data={'Details': True, 'latitude': False, 'longitude': False},
    mapbox_style="open-street-map",  # You can choose your preferred style
    zoom=3,
    height=400
)

# Adjust the layout size
fig.update_layout(
    mapbox=dict(
        style=style_url,
        # If required, include the access token (some custom styles need this, others don't)
        accesstoken=stadia_api_key),
    width=600,
    height=400,
    margin=dict(l=2, r=2, t=2, b=2)
)


# # Wrap the Plotly chart in a div with the Victorian frame
# st.markdown('<div class="victorian-frame">', unsafe_allow_html=True)
# st.title('Bwanastan (ab 2022)')
# st.plotly_chart(fig, use_container_width=True)
# st.markdown('</div>', unsafe_allow_html=True)


# Create an HTML snippet with updated CSS for responsiveness and centering.
html_string = f"""
<html>
  <head>
    <style>
      /* Responsive Victorian frame */
      .victorian-frame {{
          border: 5px solid #8B4513;      /* Brown border for vintage feel */
          border-radius: 15px;            /* Rounded corners */
          padding: 10px;
          box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3); /* Drop shadow */
          background-color: #fdfaf6;      /* Warm, light background */
          width: 100%;                    /* Full width */
          max-width: 700px;              /* Maximum width matching your figure */
          margin: 30px auto;              /* Center horizontally with top/bottom margin */
      }}
      body {{
          margin: 0;
          padding: 0;
      }}
      /* Media query for smaller screens */
      @media (max-width: 1200px) {{
          .victorian-frame {{
              max-width: 90%;
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
components.html(html_string,height=510, width=670 ) # 





