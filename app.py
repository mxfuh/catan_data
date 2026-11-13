import html

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import matplotlib.colors as mcolors

import importlib
import catan_functions
# Streamlit Cloud re-runs app.py after a code update but keeps already imported modules in memory;
# reloading makes sure new functions in catan_functions.py are picked up without rebooting the app.
importlib.reload(catan_functions)
from catan_functions import (fit_excel_into_df, create_hover_data, location_rulers, hall_of_fame,
                             eternal_table, start_position_table, form_table, current_form, form_history,
                             form_by_season, FORM_WINDOW, FORM_HISTORY_WINDOW, FORM_VARIANTS)


def embed_html(html, height):
    """Show our own generated HTML (plotly figure in its frame) in an iframe."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:  # older Streamlit versions without st.iframe
        import streamlit.components.v1 as components
        components.html(html, height=height)

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
            /* Ruhmeshalle: record cards */
            .hall-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 14px;
                margin: 10px 0 24px;
            }
            .hall-card {
                background-color: #fdfaf6;
                border: 3px solid #8B4513;
                border-radius: 12px;
                box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.25);
                padding: 12px 10px 10px;
                text-align: center;
                /* subgrid: title, value, unit, holder, detail line up across the cards of a row */
                display: grid;
                grid-template-rows: subgrid;
                grid-row: span 5;
                row-gap: 3px;
            }
            .hall-title {
                line-height: 1.35;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: 'Castellar', serif;
                font-size: 13px;
                color: #8B4513;
                border-bottom: 1px solid #e0c9a6;
                padding-bottom: 6px;
                margin-bottom: 2px;
            }
            .hall-value {
                font-family: 'Castellar', serif;
                font-size: 32px;
                line-height: 1.15;
                color: #4B2E1F;
            }
            .hall-value.long {
                font-size: 22px;
                line-height: 1.6;
            }
            .hall-unit {
                font-size: 12px;
                color: #6b4a35;
                line-height: 1.4;
            }
            .hall-holder {
                font-family: 'Castellar', serif;
                font-size: 16px;
                color: #4B2E1F;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin-top: 4px;
            }
            .hall-seal {
                width: 13px;
                height: 13px;
                border-radius: 50%;
                border: 2px solid #4B2E1F;
                display: inline-block;
            }
            .hall-detail {
                font-size: 11px;
                color: #7a5a44;
                align-self: end;
                padding-top: 6px;
            }
            .custom-caption {
                font-size: 12px;
                color: #7a5a44;
                margin: -6px 0 18px;
            }
            /* Form: one card per player with flame, 5-game average and the last five games */
            .form-variant {
                font-family: 'Castellar', serif;
                font-size: 15px;
                color: #8B4513;
                margin: 8px 0 4px;
            }
            .form-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
                margin: 6px 0 20px;
                max-width: 664px;
            }
            .form-card {
                background-color: #fdfaf6;
                border: 3px solid #8B4513;
                border-radius: 12px;
                box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.25);
                padding: 10px 6px 8px;
                text-align: center;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 2px;
            }
            .form-flame {
                height: 60px;
                display: flex;
                align-items: flex-end;
            }
            .form-value {
                font-family: 'Castellar', serif;
                font-size: 24px;
                color: #4B2E1F;
                line-height: 1.2;
            }
            .form-blessing {
                font-family: 'Castellar', serif;
                font-size: 11px;
                color: #8B4513;
                line-height: 1.3;
            }
            .form-trend {
                font-size: 11px;
                color: #7a5a44;
            }
            .form-last {
                display: flex;
                gap: 3px;
                margin-top: 4px;
            }
            .form-chip {
                font-size: 10px;
                min-width: 22px;
                padding: 1px 2px;
                border-radius: 4px;
                color: #4B2E1F;
            }
            @media (max-width: 640px) {
                .form-grid { gap: 6px; }
                .form-value { font-size: 18px; }
                .form-chip { min-width: 0; font-size: 9px; }
            }
            /* Tables scroll sideways instead of running off the screen */
            .table-scroll {
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                margin-bottom: 1rem;
            }
            /* Phones: same design, just scaled to fit */
            @media (max-width: 640px) {
                [data-testid="stMainBlockContainer"], .block-container {
                    padding-top: 3rem !important;
                }
                [data-baseweb="tab-list"], [role="tablist"] {
                    gap: 6px !important;
                    flex-wrap: wrap !important;  /* five tabs: two rows instead of hidden tabs */
                    row-gap: 8px !important;
                }
                [role="tab"] {
                    margin-right: 0 !important;
                    padding: 6px 8px !important;
                }
                h3.custom-title {
                    font-size: 6vw;
                }
                .table-scroll table {
                    font-size: 12px !important;
                }
                .table-scroll th, .table-scroll td {
                    padding: 4px 6px !important;
                }
            }
            @media (max-width: 400px) {
                [data-baseweb="tab-list"], [role="tablist"] {
                    gap: 4px !important;
                }
                [role="tab"] {
                    padding: 5px 6px !important;
                }
                [role="tab"], [role="tab"] * {
                    font-size: 11px !important;
                }
            }
    </style>
    <h1 style="text-align: center; font-family: 'Castellar', serif; color: #4B2E1F; font-size: clamp(32px, 11vw, 64px);">Bwanastan</h1>
    """,
    unsafe_allow_html=True
)

# Build the map figure: each place is colored by its ruler (most wins there), sized by games played
RULER_COLORS = {**player_colors, "Umkämpft": "#8B4513", "Unerobert": "#fdfaf6"}  # tie / no finished game yet
map_df = data_unique.merge(location_rulers(data), on="loc", how="left").dropna(subset=["latitude", "longitude"])
map_df["Spiele"] = map_df["Spiele"].fillna(0)
map_df["size"] = 7 + 2.2 * np.sqrt(map_df["Spiele"])
map_df["Herrscher_Text"] = np.where(
    map_df["Herrscher"].isin(list(player_colors)),
    map_df["Herrscher"] + " (" + map_df["Herrscher_Siege"].fillna(0).astype(int).astype(str) + " Siege)",
    map_df["Herrscher"].fillna("Unerobert"))

fig_map = go.Figure()
for ruler in [r for r in RULER_COLORS if r in set(map_df["Herrscher"])]:
    sub = map_df[map_df["Herrscher"] == ruler]
    # Dark ring underneath (map markers have no outline), so yellow stays visible on the watercolor map
    fig_map.add_trace(go.Scattermapbox(
        lat=sub["latitude"], lon=sub["longitude"], mode="markers",
        marker=dict(size=sub["size"] + 4, color="#4B2E1F"),
        hoverinfo="skip", legendgroup=ruler, showlegend=False))
    fig_map.add_trace(go.Scattermapbox(
        lat=sub["latitude"], lon=sub["longitude"], mode="markers", name=ruler, legendgroup=ruler,
        marker=dict(size=sub["size"], color=RULER_COLORS[ruler]),
        customdata=sub[["loc", "Herrscher_Text", "Details"]],
        hovertemplate="<b>%{customdata[0]}</b><br><br><b>Herrscher:</b> %{customdata[1]}%{customdata[2]}<extra></extra>"))

fig_map.update_layout(
    mapbox=dict(
        style=api_style_url,
        accesstoken=stadia_api_key,
        zoom=4,
        center=dict(lat=data_unique["latitude"].mean(), lon=data_unique["longitude"].mean())
    ),
    autosize=True,
    height=400,
    margin=dict(l=2, r=2, t=2, b=2),
    hoverlabel=dict(bgcolor="#fdfaf6", bordercolor="#8B4513", font=dict(color="#4B2E1F")),
    legend=dict(
        title=dict(text="Herrscher"),
        x=0.01, y=0.01, xanchor="left", yanchor="bottom",
        bgcolor="rgba(253, 250, 246, 0.85)", bordercolor="#8B4513", borderwidth=2,
        font=dict(family="Castellar, serif", size=11, color="#4B2E1F"),
        itemsizing="constant"
    )
)

# Runs fit(width) whenever the plot's width changes (also when a hidden tab is opened).
# fit returns the layout for that width; it is only applied when it differs from the last one.
def fit_on_resize_js(fit_body):
    return """
var gd = document.getElementById('{plot_id}');
var last = null;
function fit(w) {""" + fit_body + """}
new ResizeObserver(function () {
    var w = gd.getBoundingClientRect().width;
    if (!w) return;
    var upd = fit(w), key = JSON.stringify(upd);
    if (key !== last) { last = key; Plotly.relayout(gd, upd); }
}).observe(gd);
"""

# Narrow screens: zoom out so the same area stays visible (desktop: map is 650px wide -> zoom 4 unchanged)
MAP_FIT_JS = fit_on_resize_js("""
    // phones: the legend moves below the map (.map-legend), so it doesn't cover the places
    return {'mapbox.zoom': w < 640 ? Math.round((4 + Math.log2(w / 650)) * 10) / 10 : 4,
            'showlegend': window.innerWidth > 640};
""")

rulers_shown = [r for r in RULER_COLORS if r in set(map_df["Herrscher"])]
map_legend_html = ('<div class="map-legend"><span>Herrscher:</span>'
                   + "".join(f'<span><i style="background-color: {RULER_COLORS[r]};"></i>{html.escape(r)}</span>' for r in rulers_shown)
                   + '</div>')

html_string = f"""
<html>
  <head>
    <style>
      @font-face {{
        font-family: 'Castellar';
        src: url('https://raw.githubusercontent.com/mxfuh/catan_data/main/font/castellar-regular.woff2') format('woff2'),
             url('https://raw.githubusercontent.com/mxfuh/catan_data/main/font/castellar-regular.ttf') format('truetype');
        font-display: swap;
      }}
      .victorian-frame {{
        box-sizing: border-box;
        border: 5px solid #8B4513;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3);
        background-color: #fdfaf6;
        width: 100%;
        max-width: 680px;  /* desktop size as before (iframe used to be fixed at 680px) */
        margin: 30px 0;
      }}
      body {{
          margin: 0;
          padding: 0;
      }}
      @media (max-width: 640px) {{
          /* on touch screens the plotly toolbar stays visible and covers the plot */
          .modebar-container {{
              display: none !important;
          }}
          .victorian-frame {{
              margin: 10px 0;
          }}
          .victorian-frame .map-legend {{
              display: flex;
          }}
      }}
      .map-legend {{
          display: none;
          flex-wrap: wrap;
          justify-content: center;
          gap: 4px 14px;
          padding-top: 8px;
          font-family: 'Castellar', serif;
          font-size: 11px;
          color: #4B2E1F;
      }}
      .map-legend span {{
          display: inline-flex;
          align-items: center;
          gap: 5px;
      }}
      .map-legend i {{
          width: 10px;
          height: 10px;
          border-radius: 50%;
          border: 2px solid #4B2E1F;
      }}
    </style>
  </head>
  <body>
    <div class="victorian-frame">
      {fig_map.to_html(include_plotlyjs='cdn', full_html=False, config={'responsive': True}, post_script=MAP_FIT_JS)}
      {map_legend_html}
    </div>
  </body>
</html>
"""

##############################################################
############# CREATE Interaktiven Saisonverlauf Line graph ################
##############################################################

# Get unique years and players (finished games only, pre-game rows have no points yet)
played = data[data['complete']]
years = sorted(played['season'].unique())
players = played['player'].unique()

# Build the figure with one trace per (year, player) combination.
fig_saisonverlauf = go.Figure()
visibility_dict = {}  # Track trace indices per year
trace_idx = 0

for year in years:
    visibility_dict[year] = []
    for player in players:
        filtered_df = played[(played['season'] == year) & (played['player'] == player)]
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

# Create dropdown buttons to filter by year (newest first).
dropdown_buttons = []
for year in reversed(years):
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

# Set initial visibility to the newest year (top entry of the dropdown, shown as active).
initial_year = years[-1]
initial_vis = [False] * trace_idx
for idx in visibility_dict[initial_year]:
    initial_vis[idx] = True
for i in range(trace_idx):
    fig_saisonverlauf.data[i].visible = initial_vis[i]



# Set tighter margins for the line graph
# Adjust figure layout to give room for legend and dropdown
fig_saisonverlauf.update_layout(
    showlegend = False,
    autosize = True,  # width comes from the frame (max 600px, as before)
    height = 350,
    margin=dict(l=20, r=2, t=2, b=2),  # adjust margins if needed
    paper_bgcolor='#fdfaf6',  # Changes the overall background of the graph
    plot_bgcolor='#fdfaf6'    # Changes the background of the plot area (the area behind the data)
)


# On narrow screens shrink the title and move the year dropdown to the left edge so they don't overlap
CHART_FIT_JS = fit_on_resize_js("""
    return w < 500 ? {'title.font.size': w < 320 ? 12 : 14, 'title.x': 0.6, 'updatemenus[0].x': 0}
                   : {'title.font.size': 22, 'title.x': 0.5, 'updatemenus[0].x': 0.05};
""")

# Plotly figure in the parchment frame (used by Geschichte and Form)
def chart_frame(fig_html):
    return f"""
<html>
  <head>
    <style>
      @font-face {{
        font-family: 'Castellar';
        src: url('https://raw.githubusercontent.com/mxfuh/catan_data/main/font/castellar-regular.woff2') format('woff2'),
             url('https://raw.githubusercontent.com/mxfuh/catan_data/main/font/castellar-regular.ttf') format('truetype');
        font-display: swap;
      }}
      .victorian-frame {{
        box-sizing: border-box;
        overflow: visible;  /* Allow content to overflow if needed */
        border: 5px solid #8B4513;
        border-radius: 15px;
        padding: 20px; /* Reduced padding for a tighter frame */
        box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3);
        background-color: #fdfaf6;
        width: 100%;
        max-width: 664px;  /* desktop size as before (iframe used to be fixed at 680px) */
        margin: 20px 0;
      }}
      .plot-box {{
        max-width: 600px;
      }}
      body {{
          margin: 10;
          padding: 10;
      }}
      @media (max-width: 640px) {{
          /* on touch screens the plotly toolbar stays visible and covers the plot */
          .modebar-container {{
              display: none !important;
          }}
          .victorian-frame {{
              padding: 10px;
              margin: 10px 0;
          }}
      }}
    </style>
  </head>
  <body>
    <div class="victorian-frame">
      <div class="plot-box">
        {fig_html}
      </div>
    </div>
  </body>
</html>
"""


html_string2 = chart_frame(fig_saisonverlauf.to_html(include_plotlyjs='cdn', full_html=False, config={'responsive': True},
                                                     post_script=CHART_FIT_JS))


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


def style_standings(df, higher_better, lower_better, formats):
    """Same parchment gradient as above, per column; for 'lower is better' columns the gradient is reversed."""
    styled = df.style.format(formats)
    if higher_better:
        styled = styled.background_gradient(cmap=custom_cmap, subset=higher_better)
    if lower_better:
        styled = styled.background_gradient(cmap=custom_cmap.reversed(), subset=lower_better)
    return styled


df_eternal = eternal_table(data)
styled_eternal = style_standings(
    df_eternal,
    higher_better=["Siege", "Siegquote", "Ø Punkte", "Meisterpunkte", "Meistertitel"],
    lower_better=["Ø Platz"],
    formats={"Siegquote": "{:.1%}", "Ø Punkte": "{:.2f}", "Ø Platz": "{:.2f}"})

df_start = start_position_table(data)
styled_start = style_standings(
    df_start,
    higher_better=["Siegquote", "Ø Punkte", "Ø Gesamtproduktion", "Ø Handelswaren"],
    lower_better=["Ø Platz"],
    formats={"Siegquote": "{:.1%}", "Ø Punkte": "{:.2f}", "Ø Platz": "{:.2f}",
             "Ø Gesamtproduktion": "{:.1f}", "Ø Handelswaren": "{:.1f}"})


def hall_card(record):
    color = player_colors.get(record["holder"], "#8B4513")
    e = html.escape
    return ('<div class="hall-card">'
            f'<div class="hall-title">{e(record["title"])}</div>'
            f'<div class="hall-value{" long" if len(record["value"]) > 5 else ""}">{e(record["value"])}</div>'
            f'<div class="hall-unit">{e(record["unit"])}</div>'
            f'<div class="hall-holder"><span class="hall-seal" style="background-color: {color};"></span>{e(str(record["holder"]))}</div>'
            f'<div class="hall-detail">{e(record["detail"])}</div>'
            '</div>')


records = hall_of_fame(data)
n_games = data.loc[data["complete"], "game_id"].nunique()
hall_html = '<div class="hall-grid">' + "".join(hall_card(r) for r in records) + '</div>'


##############################################
################ Form (Ist vs. Prognose) #####
##############################################

form = form_table(data, "predict/predictions.csv")


def blessing(value):
    """Bumbas Urteil über die Form (gleiche Stufen wie die Flamme)."""
    return ("Von Bumba gesegnet" if value >= 2 else "In Bumbas Gunst" if value >= 1
            else "Geduldet" if value >= 0 else "Von Bumba verlassen")


def flame(value):
    """Flame from big/red (clearly above the prediction) to small/grey (below)."""
    if value >= 2:
        color, size = "#C0392B", 58
    elif value >= 1:
        color, size = "#E67E22", 48
    elif value >= 0:
        color, size = "#F4C430", 38
    else:
        color, size = "#A39E98", 30
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true">'
            f'<path fill="{color}" d="M12 1.5c.6 3.2-1.4 5-3.1 6.9C7.2 10.3 5.5 12.4 5.5 15.4c0 3.9 2.9 7.1 6.5 7.1'
            f's6.5-3.2 6.5-7.1c0-2.8-1.4-4.6-2.6-6.1-.3 1.5-1 2.6-2.1 3.1.4-3.5-.4-7.4-1.8-10.9z"/>'
            '<path fill="#fdfaf6" fill-opacity="0.45" d="M12 13c.3 1.6-.7 2.4-1.5 3.3-.6.7-1 1.4-1 2.4'
            ' 0 1.6 1.1 2.8 2.5 2.8s2.5-1.2 2.5-2.8c0-1.4-.8-2.3-1.4-3-.1.7-.5 1.2-1 1.4.1-1.5-.1-2.8-.1-4.1z"/>'
            '</svg>')


def signed(value, star=False):
    return f"{value:+.1f}".replace("-", "−") + ("*" if star else "")


def form_card(row):
    color = player_colors.get(row["player"], "#8B4513")
    if pd.isna(row["prev"]):
        trend = ""
    else:
        delta = row["form"] - row["prev"]
        arrow = "↑" if delta > 0.05 else "↓" if delta < -0.05 else "→"
        trend = f'{arrow} {signed(delta)} zu den {FORM_WINDOW} Spielen davor'
    chips = "".join(
        f'<span class="form-chip" style="background-color: {"#f3c9a0" if v > 0 else "#e4e0db"};">{signed(v)}</span>'
        for v in row["last"])
    return ('<div class="form-card">'
            f'<div class="hall-holder"><span class="hall-seal" style="background-color: {color};"></span>{html.escape(row["player"])}</div>'
            f'<div class="form-flame">{flame(row["form"])}</div>'
            f'<div class="form-value">{signed(row["form"], row["oof"])}</div>'
            f'<div class="form-blessing">{blessing(row["form"])}</div>'
            f'<div class="form-trend">{trend}</div>'
            f'<div class="form-last">{chips}</div>'
            '</div>')


if not form.empty:
    oof_day = pd.to_datetime(form.loc[form["oof"], "computed"]).max()
    oof_note = (f'* enthält rückgerechnete Prophezeiungen (Out-of-Fold, berechnet am {oof_day:%d.%m.%Y}): '
                'Das Modell kannte das Spiel nicht, die Prophezeiung entstand aber erst nachträglich. '
                'Ohne Sternchen bzw. durchgezogene Linie: tatsächlich verkündete Prophezeiungen.') if pd.notna(oof_day) else ""

    current = current_form(form)
    form_cards_html = ""
    for variant, title in FORM_VARIANTS.items():
        rows = current[current["variant"] == variant].set_index("player").reindex(
            [p for p in player_colors if p in set(current["player"])]).reset_index()
        form_cards_html += (f'<div class="form-variant">{title}</div><div class="form-grid">'
                            + "".join(form_card(r) for _, r in rows.iterrows()) + '</div>')

    # History: rolling average per player; dashed while a back-calculated value is in the window
    hist = form_history(form, FORM_HISTORY_WINDOW)
    game_seq = {g: i + 1 for i, g in enumerate(sorted(hist["game_id"].unique()))}
    hist["seq"] = hist["game_id"].map(game_seq)
    def history_chart(variant, season, y, oof, hover, tickformat, zero_line):
        """Line per player over the games; dashed where oof is set. season=None shows the whole history."""
        h_all = hist[hist["variant"] == variant]
        if season is not None:
            h_all = h_all[h_all["season"] == season]
        fig = go.Figure()
        for player in player_colors:
            h = h_all[h_all["player"] == player].dropna(subset=[y])
            calc, live = h[h[oof]], h[~h[oof]]
            if not calc.empty and not live.empty:
                live = pd.concat([calc.tail(1), live])  # connect both parts
            for part, dash in [(calc, "dash"), (live, "solid")]:
                if part.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=part["seq"], y=part[y], mode="lines", name=player,
                    line=dict(color=player_colors[player], width=2, dash=dash),
                    customdata=part[["season", "game"]],
                    hovertemplate=f"Spieler: {player}<br>Saison %{{customdata[0]}}, Spiel %{{customdata[1]}}<br>"
                                  f"{hover}<extra></extra>"))
        if zero_line:
            fig.add_hline(y=0, line=dict(color="#8B4513", width=1))
        # season boundaries as light lines with the year above
        for s, g in h_all.groupby("season"):
            fig.add_vline(x=g["seq"].min() - 0.5, line=dict(color="#e0c9a6", width=1))
            fig.add_annotation(x=g["seq"].min(), y=1, yref="paper", text=str(s), showarrow=False,
                               xanchor="left", yanchor="bottom", font=dict(size=10, color="#7a5a44"))
        fig.update_layout(
            showlegend=False, autosize=True, height=330,
            margin=dict(l=30, r=4, t=24, b=4),
            paper_bgcolor="#fdfaf6", plot_bgcolor="#fdfaf6",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False, tickformat=tickformat, tickfont=dict(color="#7a5a44")))
        return chart_frame(fig.to_html(include_plotlyjs='cdn', full_html=False, config={'responsive': True}))

    # Basis of both charts: single games or a rolling average; dashed while a back-calculated value is in the window
    HISTORY_BASES = {"Einzelspiel": 1, "5 Spiele": 5, "10 Spiele": 10}
    by = hist.groupby(["variant", "player"])
    for w in HISTORY_BASES.values():
        for col in ["resid", "pred_score"]:
            hist[f"{col}_{w}"] = by[col].transform(lambda s: s.rolling(w, min_periods=w).mean())
        hist[f"oof_{w}"] = by["oof"].transform(lambda s: s.rolling(w, min_periods=1).max()).astype(bool)

    def basis_label(w):
        return "" if w == 1 else f"Ø letzte {w}: "

    def form_chart(variant, season=None, w=FORM_HISTORY_WINDOW):
        return history_chart(variant, season, f"resid_{w}", f"oof_{w}",
                             f"{basis_label(w)}%{{y:+.1f}}", "+.0f", zero_line=True)

    # Same chart with Erwins Prophezeiung itself (predicted points)
    def prophecy_chart(variant, season=None, w=1):
        return history_chart(variant, season, f"pred_score_{w}", f"oof_{w}",
                             f"{basis_label(w)}Prophezeiung %{{y:.1f}} Punkte", "~.1f", zero_line=False)

    form_seasons = sorted(hist["season"].unique(), reverse=True)

    def basis_filter(key, default):
        """Single games / rolling 5 / rolling 10; nothing selected = default."""
        chosen = st.segmented_control("Basis", list(HISTORY_BASES), default=default,
                                      label_visibility="collapsed", key=key)
        return HISTORY_BASES[chosen or default]

    def basis_caption(w):
        return "Jedes Spiel einzeln." if w == 1 else f"Gleitender Schnitt über {w} Spiele."

    def season_filter(key):
        """Year buttons above a chart; nothing selected = whole history."""
        chosen = st.segmented_control("Jahr", ["Alle"] + [str(s) for s in form_seasons], default="Alle",
                                      label_visibility="collapsed", key=key)
        return None if chosen in (None, "Alle") else int(chosen)

    def season_table(variant):
        mean, oof = form_by_season(form)[variant]
        cols = [p for p in player_colors if p in mean.columns]
        mean, oof = mean[cols], oof[cols]
        text = mean.apply(lambda c: [("" if pd.isna(v) else signed(v, oof.at[s, c.name])) for s, v in c.items()])
        lim = max(abs(mean.min().min()), abs(mean.max().max()), 1)
        diverging = mcolors.LinearSegmentedColormap.from_list("form", ["#bdb5aa", "#fdfaf6", "#d9773a"])
        colors = mean.apply(lambda c: [f"background-color: {mcolors.to_hex(diverging((v / lim + 1) / 2))}"
                                       if pd.notna(v) else "" for v in c])
        text.index.name, text.columns.name = None, "Saison"
        return text.style.apply(lambda _: colors.values, axis=None)





##############################################
############# TAB NAVIGATION ################
##############################################

# Use st.tabs for a more integrated navigation experience.
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Die Lande", "Geschichte", "Wirtschaft", "Ruhmeshalle", "Bumbas Segen"])

with tab1:
    embed_html(html_string, height=510)



with tab2:
    embed_html(html_string2, height=500)

    if not df_eternal.empty:
        st.markdown('<h3 class="custom-title">Ewige Tabelle</h3>', unsafe_allow_html=True)
        st.markdown('<div class="table-scroll">' + styled_eternal.to_html() + '</div>', unsafe_allow_html=True)
        st.markdown('<div class="custom-caption">Meisterpunkte: 2 für einen Sieg, 1 für Platz 2. '
                    'Meistertitel: meiste Meisterpunkte einer Saison, die laufende Saison zählt noch nicht.</div>',
                    unsafe_allow_html=True)



with tab3:
    st.markdown('<h3 class="custom-title">Durchschnittliche Produktion <br>pro Lehen</h3>', unsafe_allow_html=True)
    st.markdown('<div class="table-scroll">' + styled_df_p.to_html() + '</div>', unsafe_allow_html=True)
    
    st.markdown('<h3 class="custom-title">Durchschnittliche Gesamtproduktion <br>nach Jahr</h3>', unsafe_allow_html=True)
    st.markdown('<div class="table-scroll">' + styled_df_t.to_html() + '</div>', unsafe_allow_html=True)
    
    st.markdown('<h3 class="custom-title">Anteile einzelner Lehen <br>an Gesamtproduktion <br>(kumuliert)</h3>', unsafe_allow_html=True)
    st.markdown('<div class="table-scroll">' + styled_ratio_df.to_html() + '</div>', unsafe_allow_html=True)
    
    st.markdown('<h3 class="custom-title">Anteile einzelner Lehen <br>an Gesamtproduktion <br>(Spielbasis)</h3>', unsafe_allow_html=True)
    st.markdown('<div class="table-scroll">' + styled_share_df.to_html() + '</div>', unsafe_allow_html=True)

    st.markdown('<h3 class="custom-title">Durchschnittlicher Produktionsanteil <br>nach Platzierung</h3>', unsafe_allow_html=True)
    st.markdown('<div class="table-scroll">' + styled_df_place.to_html() + '</div>', unsafe_allow_html=True)  

    st.markdown('<h3 class="custom-title">Durchschnittlicher Produktionsanteil <br>nach Platzierung und Jahr</h3>', unsafe_allow_html=True)
    st.markdown('<div class="table-scroll">' + styled_df_place_season.to_html() + '</div>', unsafe_allow_html=True)

    if not df_start.empty:
        st.markdown('<h3 class="custom-title">Vorteil der <br>Startposition</h3>', unsafe_allow_html=True)
        st.markdown('<div class="table-scroll">' + styled_start.to_html() + '</div>', unsafe_allow_html=True)
        st.markdown('<div class="custom-caption">Nur abgeschlossene Spiele. Handelswaren: Papier, Münzen, Stoff.</div>',
                    unsafe_allow_html=True)


with tab4:
    st.markdown('<h3 class="custom-title">Ruhmeshalle</h3>', unsafe_allow_html=True)
    if records:
        st.markdown(f'<div class="custom-caption">Rekorde aus {n_games} abgeschlossenen Spielen seit {data["season"].min()}.</div>',
                    unsafe_allow_html=True)
        st.markdown(hall_html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="custom-caption">Noch kein Spiel abgeschlossen.</div>', unsafe_allow_html=True)


with tab5:
    st.markdown('<h3 class="custom-title">Bumbas Segen</h3>', unsafe_allow_html=True)
    if form.empty:
        st.markdown('<div class="custom-caption">Seine Eminenz Erwin hat noch nichts prophezeit.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="custom-caption">Ist-Punkte minus die Prophezeiung Seiner Eminenz Erwin (der Prognose), Schnitt der letzten {FORM_WINDOW} Spiele. '
                    'Mit Spieler-Info: verglichen mit dem eigenen Normalniveau. Ohne: was man aus seiner Setzung macht. '
                    'Flamme: rot = von Bumba gesegnet (ab +2), orange = in Bumbas Gunst (ab +1), gelb = geduldet (ab 0), '
                    'grau = von Bumba verlassen.</div>', unsafe_allow_html=True)
        st.markdown(form_cards_html, unsafe_allow_html=True)

        st.markdown('<h3 class="custom-title">Segenskurve</h3>', unsafe_allow_html=True)
        chosen = st.radio("Variante", list(FORM_VARIANTS.values()), horizontal=True,
                          index=list(FORM_VARIANTS).index("no_player"),  # default: nur Setzung
                          label_visibility="collapsed", key="form_variant")
        basis_f = basis_filter("form_basis", "10 Spiele")
        season_f = season_filter("form_season")
        embed_html(form_chart(next(v for v, t in FORM_VARIANTS.items() if t == chosen), season_f, basis_f), height=400)
        st.markdown(f'<div class="custom-caption">Ist-Punkte minus Prophezeiung. {basis_caption(basis_f)} '
                    'Gestrichelt: rückgerechnet.</div>', unsafe_allow_html=True)

        st.markdown('<h3 class="custom-title">Die Prophezeiungen Seiner Eminenz Erwin</h3>', unsafe_allow_html=True)
        chosen_p = st.radio("Variante", list(FORM_VARIANTS.values()), horizontal=True,
                            index=list(FORM_VARIANTS).index("no_player"),  # default: nur Setzung
                            label_visibility="collapsed", key="prophecy_variant")
        variant_p = next(v for v, t in FORM_VARIANTS.items() if t == chosen_p)
        basis_p = basis_filter("prophecy_basis", "Einzelspiel")
        season_p = season_filter("prophecy_season")
        embed_html(prophecy_chart(variant_p, season_p, basis_p), height=400)
        st.markdown(f'<div class="custom-caption">Die Prophezeiungen Seiner Eminenz Erwin in Punkten. {basis_caption(basis_p)} '
                    'Gestrichelt: rückgerechnet.</div>', unsafe_allow_html=True)

        st.markdown('<h3 class="custom-title">Segen nach Jahr</h3>', unsafe_allow_html=True)
        for variant, title in FORM_VARIANTS.items():
            st.markdown(f'<div class="form-variant">{title}</div>', unsafe_allow_html=True)
            st.markdown('<div class="table-scroll">' + season_table(variant).to_html() + '</div>', unsafe_allow_html=True)
        if oof_note:
            st.markdown(f'<div class="custom-caption">{oof_note}</div>', unsafe_allow_html=True)
