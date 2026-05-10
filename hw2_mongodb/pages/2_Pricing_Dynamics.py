"""
pages/2_Pricing_Dynamics.py
---------------------------
Data notes:
  - price / cleaning_fee / security_deposit are already Python floats (Decimal128 handled in utils)
  - minimum_nights is already numeric (cast from string in utils)
  - score_rating: scale 0-100 (integer)
  - neighbourhood column = government_area (more granular than suburb)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import load_listings, PLOTLY_TEMPLATE, COLOR_SEQUENCE

st.set_page_config(page_title="Pricing Dynamics | Airbnb Dashboard", page_icon="💰", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0f1117; }
h1 { color: #FF5A5F !important; } h2, h3 { color: #e0e6f0 !important; }
[data-testid="stSidebar"] { background-color: #13151f; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 💰 Pricing Dynamics")
st.markdown("Understand what drives listing prices — review scores, neighbourhood effects, fees, and room type premiums.")
st.divider()

try:
    df = load_listings()

    # Remove top-1% price outliers for visual clarity
    price_99 = df["price"].quantile(0.99)
    df_clean = df[df["price"].notna() & (df["price"] <= price_99)].copy()

    # ---------------------------------------------------------------------------
    # Sidebar filters
    # ---------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("## 🎛️ Filters")
        markets = ["All"] + sorted(df_clean["market"].dropna().unique().tolist())
        sel_market = st.selectbox("Market", markets)
        if sel_market != "All":
            df_clean = df_clean[df_clean["market"] == sel_market]

        room_types = ["All"] + sorted(df_clean["room_type"].dropna().unique().tolist())
        sel_room = st.selectbox("Room Type", room_types)
        if sel_room != "All":
            df_clean = df_clean[df_clean["room_type"] == sel_room]

        price_max = int(df_clean["price"].max())
        price_range = st.slider("Price Range ($/night)", 0, price_max, (0, price_max))
        df_clean = df_clean[
            (df_clean["price"] >= price_range[0]) & (df_clean["price"] <= price_range[1])
        ]

    st.markdown(f"**Showing {len(df_clean):,} listings** after filters.")

    # -----------------------------------------------------------------------
    # Row 1: Price vs. rating scatter + Box plot by market
    # -----------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        # Chart 1 — Price vs. review rating (score_rating is 0–100)
        scatter_df = df_clean[df_clean["score_rating"].notna()].copy()
        fig1 = px.scatter(
            scatter_df, x="score_rating", y="price",
            color="room_type", color_discrete_sequence=COLOR_SEQUENCE,
            title="Price vs. Review Rating Score (0–100)",
            labels={"score_rating": "Review Score (0–100)", "price": "Price per Night ($)",
                    "room_type": "Room Type"},
            template=PLOTLY_TEMPLATE, opacity=0.55,
            hover_data={"price": ":$,.0f", "score_rating": ":.0f", "market": True},
            trendline="lowess", trendline_scope="overall",
            trendline_color_override="#FFB400",
        )
        fig1.update_layout(
            height=420, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Chart 2 — Price distribution by top markets (box plot)
        top_markets = df_clean["market"].value_counts().head(10).index
        box_df = df_clean[df_clean["market"].isin(top_markets)]
        fig2 = px.box(
            box_df, x="market", y="price",
            color="market", color_discrete_sequence=COLOR_SEQUENCE,
            title="Price Distribution by Market (Top 10)",
            labels={"market": "Market", "price": "Price per Night ($)"},
            template=PLOTLY_TEMPLATE, points=False,
        )
        fig2.update_layout(
            height=420, showlegend=False, xaxis_tickangle=-35,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # -----------------------------------------------------------------------
    # Row 2: Cleaning fee vs price + Security deposit vs price
    # -----------------------------------------------------------------------
    col3, col4 = st.columns(2)

    with col3:
        # Chart 3 — Cleaning fee scatter
        fee_df = df_clean[
            df_clean["cleaning_fee"].notna() & (df_clean["cleaning_fee"] > 0)
        ].copy()
        fee_99 = fee_df["cleaning_fee"].quantile(0.99)
        fee_df = fee_df[fee_df["cleaning_fee"] <= fee_99]
        fig3 = px.scatter(
            fee_df, x="cleaning_fee", y="price",
            color="room_type", color_discrete_sequence=COLOR_SEQUENCE,
            title="Cleaning Fee vs. Nightly Price",
            labels={"cleaning_fee": "Cleaning Fee ($)", "price": "Price per Night ($)"},
            template=PLOTLY_TEMPLATE, opacity=0.5,
            hover_data={"price": ":$,.0f", "cleaning_fee": ":$,.0f"},
            trendline="ols", trendline_scope="overall",
            trendline_color_override="#FFB400",
        )
        fig3.update_layout(
            height=380, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        # Chart 4 — Security deposit scatter
        dep_df = df_clean[
            df_clean["security_deposit"].notna() & (df_clean["security_deposit"] > 0)
        ].copy()
        dep_99 = dep_df["security_deposit"].quantile(0.99)
        dep_df = dep_df[dep_df["security_deposit"] <= dep_99]
        fig4 = px.scatter(
            dep_df, x="security_deposit", y="price",
            color="room_type", color_discrete_sequence=COLOR_SEQUENCE,
            title="Security Deposit vs. Nightly Price",
            labels={"security_deposit": "Security Deposit ($)", "price": "Price per Night ($)"},
            template=PLOTLY_TEMPLATE, opacity=0.5,
            hover_data={"price": ":$,.0f", "security_deposit": ":$,.0f"},
            trendline="ols", trendline_scope="overall",
            trendline_color_override="#00A699",
        )
        fig4.update_layout(
            height=380, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)

    # -----------------------------------------------------------------------
    # Row 3: Mean vs Median by room type + Violin
    # -----------------------------------------------------------------------
    col5, col6 = st.columns(2)

    with col5:
        # Chart 5 — Mean vs Median price by room type
        room_price = (
            df_clean.groupby("room_type")["price"]
            .agg(mean_price="mean", median_price="median", count="count")
            .reset_index()
            .sort_values("mean_price", ascending=False)
        )
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=room_price["room_type"], y=room_price["mean_price"],
            name="Mean Price", marker_color="#FF5A5F",
            text=room_price["mean_price"].map("${:,.0f}".format),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Mean: $%{y:,.0f}<extra></extra>",
        ))
        fig5.add_trace(go.Scatter(
            x=room_price["room_type"], y=room_price["median_price"],
            name="Median Price", mode="markers+lines",
            marker=dict(size=10, color="#FFB400", symbol="diamond"),
            hovertemplate="<b>%{x}</b><br>Median: $%{y:,.0f}<extra></extra>",
        ))
        fig5.update_layout(
            title="Mean vs. Median Price by Room Type",
            xaxis_title="Room Type", yaxis_title="Price per Night ($)",
            template=PLOTLY_TEMPLATE, height=380,
            legend=dict(orientation="h", y=1.08),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col6:
        # Chart 6 — Price violin by room type
        fig6 = px.violin(
            df_clean, x="room_type", y="price",
            color="room_type", color_discrete_sequence=COLOR_SEQUENCE,
            box=True, points=False,
            title="Price Distribution — Violin by Room Type",
            labels={"room_type": "Room Type", "price": "Price per Night ($)"},
            template=PLOTLY_TEMPLATE,
        )
        fig6.update_layout(
            height=380, showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig6, use_container_width=True)

    # -----------------------------------------------------------------------
    # Summary table
    # -----------------------------------------------------------------------
    with st.expander("📊 Price Summary Statistics by Room Type"):
        summary = (
            df_clean.groupby("room_type")["price"]
            .describe(percentiles=[0.25, 0.5, 0.75])
            .round(2)
            .reset_index()
        )
        st.dataframe(summary, use_container_width=True)

except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.exception(e)
