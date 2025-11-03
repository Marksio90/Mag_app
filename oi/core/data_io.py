
from __future__ import annotations
import io
import polars as pl
import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def read_csv(path_or_file) -> pl.DataFrame:
    if hasattr(path_or_file, "read"):
        data = path_or_file.read()
        return pl.read_csv(io.BytesIO(data))
    return pl.read_csv(path_or_file)

def to_pandas(df) -> pd.DataFrame:
    return df.to_pandas() if isinstance(df, pl.DataFrame) else df
