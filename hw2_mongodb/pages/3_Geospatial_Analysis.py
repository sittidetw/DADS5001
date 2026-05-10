"""
pages/3_Geospatial_Analysis.py
-------------------------------
Data notes:
  - coordinates extracted as longitude/latitude floats in utils
  - neighbourhood = government_area (suburb often empty)
  - price already float (Decimal128 handled in utils)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import load_listings, PLOTLY_TEMPLATE, COLOR_SEQUENCE

st.set_page_config(page_title="Geospatial Analysis | Airbnb Dashboard", page_icon="🗺️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0f1117; }
h1 { color: #FF5A5F !important; } h2, h3 { color: #e0e6f0 !important; }
[data-testid="stSidebar"] { background-color: #13151f; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🗺️ Geospatial Analysis")
st.markdown("Interactive maps visualizing listing density, price distributions, and availability patterns across global markets.")
st.divider()

try:
    df = load_listings()

    # Keep only rows with valid coordinates and price
    geo_df = df[
        df["latitude"].notna() & df["longitude"].notna() & df["price"].notna()
    ].copy()

    # Remove top-1% price outliers
    price_99 = geo_df["price"].quantile(0.99)
    geo_df = geo_df[geo_df["price"] <= price_99]

    st.markdown(f"📍 **{len(geo_df):,} listings** with valid coordinates.")

    # ---------------------------------------------------------------------------
    # Sidebar filters
    # ---------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("## 🎛️ Filters")
        markets = ["All"] + sorted(geo_df["market"].dropna().unique().tolist())
        sel_market = st.selectbox("Market", markets, key="geo_market")
        if sel_market != "All":
            geo_df = geo_df[geo_df["market"] == sel_market]

        room_types = ["All"] + sorted(geo_df["room_type"].dropna().unique().tolist())
        sel_room = st.selectbox("Room Type", room_types, key="geo_room")
        if sel_room != "All":
            geo_df = geo_df[geo_df["room_type"] == sel_room]

        max_pts = st.slider(
            "Max map points", 200, min(5000, len(geo_df)),
            min(2000, len(geo_df)), step=200
        )

    # Sample to avoid browser overload
    map_df = geo_df.sample(n=min(max_pts, len(geo_df)), random_state=42)

    # -----------------------------------------------------------------------
    # Chart 1 — Scatter mapbox: price heat
    # -----------------------------------------------------------------------
    st.markdown("### 🏷️ Listing Locations Colored by Nightly Price")
    fig1 = px.scatter_mapbox(
        map_df, lat="latitude", lon="longitude",
        color="price", size="price", size_max=12,
        color_continuous_scale="RdYlGn_r",
        range_color=[map_df["price"].quantile(0.05), map_df["price"].quantile(0.95)],
        zoom=1,
        center={"lat": map_df["latitude"].mean(), "lon": map_df["longitude"].mean()},
        mapbox_style="carto-darkmatter",
        title="Airbnb Listings — Price Heat Map",
        hover_name="name",
        hover_data={"price": ":$,.0f", "room_type": True,
                    "market": True, "latitude": False, "longitude": False},
        template=PLOTLY_TEMPLATE,
    )
    fig1.update_layout(
        height=520, coloraxis_colorbar=dict(title="Price ($)"),
        margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig1, use_container_width=True)

    # -----------------------------------------------------------------------
    # Chart 2 — Density mapbox: review volume
    # -----------------------------------------------------------------------
    st.markdown("### 🔥 Review Volume Density Heatmap")
    rev_df = map_df[map_df["number_of_reviews"] > 0].copy()
    fig2 = px.density_mapbox(
        rev_df, lat="latitude", lon="longitude",
        z="number_of_reviews", radius=18,
        zoom=1, mapbox_style="carto-darkmatter",
        color_continuous_scale="YlOrRd",
        title="Review Volume Density",
        template=PLOTLY_TEMPLATE,
    )
    fig2.update_layout(
        height=480, coloraxis_colorbar=dict(title="Review Volume"),
        margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # -----------------------------------------------------------------------
    # Row: Chart 3 + Chart 4
    # -----------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        # Chart 3 — Top neighbourhoods by listing volume
        # Use government_area (neighbourhood) — richer than suburb
        nb_df = geo_df[geo_df["neighbourhood"].notna() & (geo_df["neighbourhood"] != "")]
        top_nb = (
            nb_df.groupby("neighbourhood")
            .agg(listings=("price", "count"), avg_price=("price", "median"))
            .reset_index()
            .sort_values("listings", ascending=False)
            .head(20)
        )
        fig3 = px.bar(
            top_nb, x="listings", y="neighbourhood", orientation="h",
            color="avg_price", color_continuous_scale="RdYlGn",
            title="Top 20 Neighbourhoods by Listing Volume",
            labels={"neighbourhood": "Neighbourhood", "listings": "Listings",
                    "avg_price": "Median Price ($)"},
            template=PLOTLY_TEMPLATE, text="listings",
        )
        fig3.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig3.update_layout(
            height=560, yaxis={"categoryorder": "total ascending"},
            coloraxis_colorbar=dict(title="Median Price ($)"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        # Chart 4 — Average price per market (horizontal bar)
        mkt_price = (
            geo_df[geo_df["market"].notna()]
            .groupby("market")["price"]
            .agg(avg_price="mean", listings="count")
            .reset_index()
            .sort_values("avg_price", ascending=False)
            .head(20)
        )
        fig4 = px.bar(
            mkt_price, x="avg_price", y="market", orientation="h",
            color="avg_price", color_continuous_scale="Blues",
            title="Average Nightly Price by Market",
            labels={"market": "Market", "avg_price": "Avg Price ($)"},
            template=PLOTLY_TEMPLATE, text="avg_price",
            hover_data={"listings": ":,"},
        )
        fig4.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig4.update_layout(
            height=560, yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)

    # -----------------------------------------------------------------------
    # Chart 5 — Availability 365 by market (box)
    # -----------------------------------------------------------------------
    st.markdown("### 📅 Annual Availability Distribution by Market")
    avail_df = geo_df[
        geo_df["availability_365"].notna() & geo_df["market"].notna()
    ]
    top_markets = avail_df["market"].value_counts().head(10).index
    avail_df = avail_df[avail_df["market"].isin(top_markets)]

    fig5 = px.box(
        avail_df, x="market", y="availability_365",
        color="market", color_discrete_sequence=COLOR_SEQUENCE,
        title="Days Available per Year by Market (Top 10)",
        labels={"market": "Market", "availability_365": "Days Available (out of 365)"},
        template=PLOTLY_TEMPLATE, points=False,
    )
    fig5.update_layout(
        height=420, showlegend=False, xaxis_tickangle=-30,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig5, use_container_width=True)

except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.exception(e)
