import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.colors as mcolors

from catan_functions import fit_excel_into_df, create_hover_data

# Define custom colors for each player.
player_colors = {
    'PF': '#075eb5',   # nice deep blue
    'JHC': '#FF4500',   # fiery red
    'MF': '#FFD700'     # strong and visible yellow
}

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


### 
# Main title with custom font
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
        h3.custom-title {
          font-family: Castellar, serif;
          font-size: 26px;
          color: #4B2E1F;
            }
                /* Custom styling for tab buttons */
            [role="tab"] {
                background-color: #ffe4c2 !important;
                background-size: cover !important;
                border: 3px solid #8B4513 !important;
                border-radius: 8px !important;
                font-family: 'Times New Roman', serif !important;
                font-size: 24px !important;
                color: #8B4513 !important;
                margin-right: 10px !important;
                padding: 8px 16px !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 0 10px rgba(0,0,0,0.5) !important;
            }
            [role="tab"]:focus {
                outline: none !important;
            }
            [role="tab"][aria-selected="true"] {
                box-shadow: 0 0 10px rgba(0,0,0,0.5) !important;
            }
            [data-baseweb="tab-border"] {
                display: none !important;
            }
            [data-baseweb="tab-highlight"] {
                display: none !important;
            }
            [role="tab"], [role="tab"] * {
                font-family: 'Castellar', serif !important;
                font-size: 12px !important;
            }
    </style>
    <h1 style="text-align: center; font-family: 'Castellar', serif; color: #4B2E1F; font-size: 64px;">Bwanastan</h1>
    """,
    unsafe_allow_html=True
)

# Build the map figure
fig_map = px.scatter_mapbox(
    data_unique,
    lat='latitude',
    lon='longitude',
    hover_name='loc',
    hover_data={'Details': True, 'latitude': False, 'longitude': False},
    mapbox_style="open-street-map",
    zoom=4,
    height=400
)

fig_map.update_layout(
    mapbox=dict(
        style=api_style_url,
        accesstoken=stadia_api_key
    ),
    width=650,
    height=400,
    margin=dict(l=2, r=2, t=2, b=2)
)

html_string = f"""
<html>
  <head>
    <style>
      .victorian-frame {{
        box-sizing: border-box;
        border: 5px solid #8B4513;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3);
        background-color: #fdfaf6;
        width: 100%;
        max-width: 670px;
        margin: 30px auto;
      }}
      body {{
          margin: 0;
          padding: 0;
      }}
      @media (max-width: 1200px) {{
          .victorian-frame {{
              max-width: 100%;
          }}
      }}
    </style>
  </head>
  <body>
    <div class="victorian-frame">
      {fig_map.to_html(include_plotlyjs='cdn', full_html=False)}
    </div>
  </body>
</html>
"""

##############################################################
############# CREATE Interaktiven Saisonverlauf Line graph ################
##############################################################

# Get unique years and players
years = sorted(data['season'].unique())
players = data['player'].unique()

# Build the figure with one trace per (year, player) combination.
fig_saisonverlauf = go.Figure()
visibility_dict = {}  # Track trace indices per year
trace_idx = 0

for year in years:
    visibility_dict[year] = []
    for player in players:
        filtered_df = data[(data['season'] == year) & (data['player'] == player)]
        fig_saisonverlauf.add_trace(go.Scatter(
            x=filtered_df['game'],
            y=filtered_df['points_cum_ytd'],
            mode='lines+markers',
            name=player,
            line=dict(color=player_colors.get(player, 'black')),
            marker=dict(
                color=player_colors.get(player, 'black'),
                size=4,
                symbol='circle'
            ),
            customdata=filtered_df[['loc', "month"]],
            hovertemplate=
                f"Spieler: {player}<br>" +
                'Spiel: %{x}<br>' +
                'Punkte: %{y}<br>' +
                'Ort: %{customdata[0]}<br>' +
                'Monat: %{customdata[1]}<extra></extra>'
        ))
        visibility_dict[year].append(trace_idx)
        trace_idx += 1

# Create dropdown buttons to filter by year.
dropdown_buttons = []
for year in years:
    vis = [False] * trace_idx
    for idx in visibility_dict[year]:
        vis[idx] = True
    dropdown_buttons.append(
        dict(
            label=str(year),
            method='update',
            args=[{'visible': vis}]
        )
    )

fig_saisonverlauf.update_layout(
    updatemenus=[{
        'buttons': dropdown_buttons,
        'direction': 'down',
        'showactive': True,
        'x': 0.05,
        'y': 1.15,
        'xanchor': 'left',
        'yanchor': 'top'
    }],
    title=dict(
        text='<b>MEISTERSCHAFTSVERLAUF</b>',
        font=dict(
            family='Castellar',
            size=22,
            color='#4B2E1F'
        ),
        x=0.5,
        xanchor='center'
    )
)

fig_saisonverlauf.update_xaxes(showticklabels=False, showgrid=False, zeroline=False, ticks="")
fig_saisonverlauf.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, ticks="")

# Set initial visibility to the first year.
initial_year = years[0]
initial_vis = [False] * trace_idx
for idx in visibility_dict[initial_year]:
    initial_vis[idx] = True
for i in range(trace_idx):
    fig_saisonverlauf.data[i].visible = initial_vis[i]



# Set tighter margins for the line graph
# Adjust figure layout to give room for legend and dropdown
fig_saisonverlauf.update_layout(
    showlegend = False,
    width = 600,
    height = 350,
    margin=dict(l=20, r=2, t=2, b=2),  # adjust margins if needed
    paper_bgcolor='#fdfaf6',  # Changes the overall background of the graph
    plot_bgcolor='#fdfaf6'    # Changes the background of the plot area (the area behind the data)
)


html_string2 = f"""
<html>
  <head>
    <style>
      .victorian-frame {{
        box-sizing: border-box;
        overflow: visible;  /* Allow content to overflow if needed */
        border: 5px solid #8B4513;
        border-radius: 15px;
        padding: 20px; /* Reduced padding for a tighter frame */
        box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3);
        background-color: #fdfaf6;
        width: 100%;
        max-width: 670px;
        margin: 20px auto;
      }}
      body {{
          margin: 10;
          padding: 10;
      }}
      @media (max-width: 1200px) {{
          .victorian-frame {{
              max-width: 100%;
          }}
      }}
    </style>
  </head>
  <body>
    <div class="victorian-frame">
      {fig_saisonverlauf.to_html(include_plotlyjs='cdn', full_html=False)}
    </div>
  </body>
</html>
"""


##############################################
############# Production Tables ##############
##############################################

# Group and aggregate the data
df_p = data[["season", "player"] + [col for col in data if "p_sum_" in col]].groupby(["season", "player"]).mean()
df_p = df_p.rename(columns = {col:col[6:] for col in df_p})
###### the following not for display, just calculating a table with season shares
df_t_calc = data[["season", "player"] + [col for col in data if "t_sum_" in col]].groupby(["season", "player"]).mean()
df_t_calc = df_t_calc.rename(columns = {col:col[6:] for col in df_t_calc})
# Now perform elementwise division
ratio_df = df_p / df_t_calc
######### this one for display: average total production per season
df_t = data[["season"] + [col for col in data if "t_sum_" in col]].groupby(["season"]).mean()
df_t = df_t.rename(columns = {col:col[6:] for col in df_t})

###### actual shares, aggregated from per-game shares
share_df = data[["season", "player"] + [col for col in data if "share_" in col]].groupby(["season", "player"]).mean()
share_df = share_df.rename(columns = {col:col[6:] for col in share_df})

###### average share of production by finishing place
df_place = data[["place"] + [col for col in data if "share_" in col]].groupby(["place"]).mean()
df_place = df_place.rename(columns = {col:col[6:] for col in df_place})
df_place_season = data[["season", "place"] + [col for col in data if "share_" in col]].groupby(["season", "place"]).mean()
df_place_season = df_place_season.rename(columns = {col:col[6:] for col in df_place_season})

# create heatmaps
# Define your light and dark shades. Replace these with your desired hex colors.
light_shade = "#ffe4c2"  # light shade (for smallest values)
dark_shade = "#b5864a"   # dark shade (for largest values)  #8B4513

# Create a custom linear colormap from the two colors.
custom_cmap = mcolors.LinearSegmentedColormap.from_list("custom_shade", [light_shade, dark_shade])




styled_df_p = df_p.style.background_gradient(cmap=custom_cmap).format("{:.2f}")
styled_df_t = df_t.style.background_gradient(cmap=custom_cmap).format("{:.2f}")
styled_ratio_df = ratio_df.style.background_gradient(cmap=custom_cmap).format("{:.1%}")
styled_share_df = share_df.style.background_gradient(cmap=custom_cmap).format("{:.1%}")
styled_df_place = df_place.style.background_gradient(cmap=custom_cmap).format("{:.1%}")
styled_df_place_season = df_place_season.style.background_gradient(cmap=custom_cmap).format("{:.1%}")





##############################################
############# TAB NAVIGATION ################
##############################################

# Use st.tabs for a more integrated navigation experience.
tab1, tab2, tab3 = st.tabs(["Die Lande", "Geschichte", "Wirtschaft"])

with tab1:
    components.html(html_string, height=510, width=680)



with tab2:
    components.html(html_string2, height=500, width=680)



with tab3:
    st.markdown('<h3 class="custom-title">Durchschnittliche Produktion <br>pro Lehen</h3>', unsafe_allow_html=True)
    st.markdown(styled_df_p.to_html(), unsafe_allow_html=True)
    
    st.markdown('<h3 class="custom-title">Durchschnittliche Gesamtproduktion <br>nach Jahr</h3>', unsafe_allow_html=True)
    st.markdown(styled_df_t.to_html(), unsafe_allow_html=True)
    
    st.markdown('<h3 class="custom-title">Anteile einzelner Lehen <br>an Gesamtproduktion <br>(kumuliert)</h3>', unsafe_allow_html=True)
    st.markdown(styled_ratio_df.to_html(), unsafe_allow_html=True)
    
    st.markdown('<h3 class="custom-title">Anteile einzelner Lehen <br>an Gesamtproduktion <br>(Spielbasis)</h3>', unsafe_allow_html=True)
    st.markdown(styled_share_df.to_html(), unsafe_allow_html=True)

    st.markdown('<h3 class="custom-title">Durchschnittlicher Produktionsanteil <br>nach Platzierung</h3>', unsafe_allow_html=True)
    st.markdown(styled_df_place.to_html(), unsafe_allow_html=True)  

    st.markdown('<h3 class="custom-title">Durchschnittlicher Produktionsanteil <br>nach Platzierung und Jahr</h3>', unsafe_allow_html=True)
    st.markdown(styled_df_place_season.to_html(), unsafe_allow_html=True)


