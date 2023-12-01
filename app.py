import numpy as np
import pandas as pd
import streamlit
import plotly


cols = list(pd.read_excel("catan_data.xlsx").iloc[0,:])
data = pd.read_excel("catan_data.xlsx").iloc[1:,:]
data.columns = cols


