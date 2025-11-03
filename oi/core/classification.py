
from __future__ import annotations
import polars as pl

def abc_class(df: pl.DataFrame, sku_col="sku", qty_col="qty") -> pl.DataFrame:
    agg = df.group_by(sku_col).agg(pl.col(qty_col).sum().alias("annual_qty"))
    tot = agg["annual_qty"].sum()
    agg = (agg.with_columns((pl.col("annual_qty")/tot).alias("share"))
              .sort("annual_qty", descending=True)
              .with_columns(pl.cumsum("share").alias("cum_share")))
    def tier(c):
        if c <= 0.8: return "A"
        if c <= 0.95: return "B"
        return "C"
    return agg.with_columns(pl.col("cum_share").map_elements(tier).alias("ABC"))

def xyz_class(df: pl.DataFrame, sku_col="sku", qty_col="qty") -> pl.DataFrame:
    cv = df.group_by(sku_col).agg(pl.col(qty_col).std().alias("std"),
                                  pl.col(qty_col).mean().alias("mean"))
    cv = cv.with_columns((pl.col("std")/pl.col("mean").clip_min(1e-9)).alias("cv"))
    def tier(x):
        if x <= 0.5: return "X"
        if x <= 1.0: return "Y"
        return "Z"
    return cv.with_columns(pl.col("cv").map_elements(tier).alias("XYZ"))
