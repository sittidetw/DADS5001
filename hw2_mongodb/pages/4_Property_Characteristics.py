"""
pages/4_Property_Characteristics.py
-------------------------------------
Data notes:
  - instant_bookable field does NOT exist in sample_airbnb — replaced with
    cancellation_policy comparison (flexible vs strict)
  - bed_type field IS available in this dataset
  - minimum_nights already cast to numeric in utils (was a string)
  - amenities: native Python list from MongoDB
  - bathrooms: Decimal128 → float (handled in utils)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from utils import load_listings, PLOTLY_TEMPLATE, COLOR_SEQUENCE

st.set_page_config(
    page_title="Property Characteristics | Airbnb Dashboard",
    page_icon="🏡", layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0f1117; }
h1 { color: #FF5A5F !important; } h2, h3 { color: #e0e6f0 !important; }
[data-testid="stSidebar"] { background-color: #13151f; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🏡 Property Characteristics")
st.markdown(
    "Deep dive into the physical attributes of listings — bedrooms, amenities, "
    "minimum stays, cancellation flexibility, and their impact on price and reviews."
)
st.divider()

try:
    df = load_listings()

    # Remove top-1% price outliers
    price_99 = df["price"].quantile(0.99)
    df_clean = df[df["price"].notna() & (df["price"] <= price_99)].copy()

    # ---------------------------------------------------------------------------
    # Sidebar filters
    # ---------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("## 🎛️ Filters")
        markets = ["All"] + sorted(df_clean["market"].dropna().unique().tolist())
        sel_market = st.selectbox("Market", markets, key="prop_market")
        if sel_market != "All":
            df_clean = df_clean[df_clean["market"] == sel_market]

        room_types = ["All"] + sorted(df_clean["room_type"].dropna().unique().tolist())
        sel_room = st.selectbox("Room Type", room_types, key="prop_room")
        if sel_room != "All":
            df_clean = df_clean[df_clean["room_type"] == sel_room]

    st.markdown(f"**Showing {len(df_clean):,} listings** after filters.")

    # -----------------------------------------------------------------------
    # Row 1: Bedrooms vs price + Beds vs price
    # -----------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        # Chart 1 — Bedrooms vs. median price (dual axis: bar + count line)
        bed_price = (
            df_clean[df_clean["bedrooms"].notna() & (df_clean["bedrooms"] <= 10)]
            .groupby("bedrooms")["price"]
            .agg(median_price="median", count="count")
            .reset_index()
        )
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=bed_price["bedrooms"], y=bed_price["median_price"],
            name="Median Price ($)",
            marker=dict(color=bed_price["median_price"],
                        colorscale="RdYlGn", showscale=True,
                        colorbar=dict(title="$", x=1.0)),
            text=bed_price["median_price"].map("${:,.0f}".format),
            textposition="outside",
            hovertemplate="<b>%{x} bedrooms</b><br>Median: $%{y:,.0f}<extra></extra>",
        ))
        fig1.add_trace(go.Scatter(
            x=bed_price["bedrooms"], y=bed_price["count"],
            name="Listing Count", yaxis="y2",
            mode="lines+markers",
            marker=dict(color="#FFB400", size=8),
            line=dict(dash="dot"),
            hovertemplate="<b>%{x} bedrooms</b><br>Count: %{y:,}<extra></extra>",
        ))
        fig1.update_layout(
            title="Bedrooms vs. Median Price & Listing Count",
            xaxis_title="Number of Bedrooms",
            yaxis=dict(title="Median Price ($)", showgrid=False),
            yaxis2=dict(title="Listing Count", overlaying="y", side="right", showgrid=False),
            template=PLOTLY_TEMPLATE, height=420,
            legend=dict(orientation="h", y=1.08),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Chart 2 — Beds vs. median price
        beds_price = (
            df_clean[df_clean["beds"].notna() & (df_clean["beds"] <= 15)]
            .groupby("beds")["price"]
            .agg(median_price="median", count="count")
            .reset_index()
        )
        fig2 = px.bar(
            beds_price, x="beds", y="median_price",
            color="median_price", color_continuous_scale="Blues",
            title="Number of Beds vs. Median Nightly Price",
            labels={"beds": "Number of Beds", "median_price": "Median Price ($)"},
            template=PLOTLY_TEMPLATE, text="median_price",
            hover_data={"count": ":,"},
        )
        fig2.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig2.update_layout(
            height=420, coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # -----------------------------------------------------------------------
    # Chart 3 — Top amenities (horizontal bar)
    # -----------------------------------------------------------------------
    st.markdown("### 🛎️ Most Common Amenities")
    all_amenities = []
    for amenity_list in df_clean["amenities"].dropna():
        if isinstance(amenity_list, list):
            all_amenities.extend(amenity_list)

    if all_amenities:
        amenity_counts = Counter(all_amenities)
        top_amenities = (
            pd.DataFrame(amenity_counts.most_common(20), columns=["Amenity", "Count"])
            .sort_values("Count")
        )
        fig3 = px.bar(
            top_amenities, x="Count", y="Amenity", orientation="h",
            color="Count", color_continuous_scale="RdYlGn",
            title="Top 20 Most Common Amenities",
            labels={"Count": "Number of Listings Offering", "Amenity": ""},
            template=PLOTLY_TEMPLATE, text="Count",
        )
        fig3.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig3.update_layout(
            height=540, coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    # -----------------------------------------------------------------------
    # Row 2: Minimum nights histogram + Review vs capacity
    # -----------------------------------------------------------------------
    col3, col4 = st.columns(2)

    with col3:
        # Chart 4 — Minimum nights distribution (min_nights already numeric)
        min_df = df_clean[
            df_clean["minimum_nights"].notna() & (df_clean["minimum_nights"] <= 30)
        ]
        fig4 = px.histogram(
            min_df, x="minimum_nights",
            color="room_type", color_discrete_sequence=COLOR_SEQUENCE,
            title="Minimum Nights Distribution (≤ 30 nights)",
            labels={"minimum_nights": "Minimum Nights Required", "count": "Listings"},
            template=PLOTLY_TEMPLATE, nbins=30, barmode="overlay", opacity=0.75,
        )
        fig4.update_layout(
            height=380, legend=dict(orientation="h", y=1.08),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col4:
        # Chart 5 — Review volume vs. accommodates (capacity)
        cap_df = df_clean[
            df_clean["accommodates"].notna() & df_clean["number_of_reviews"].notna()
        ].copy()
        fig5 = px.scatter(
            cap_df, x="accommodates", y="number_of_reviews",
            color="room_type", color_discrete_sequence=COLOR_SEQUENCE,
            title="Review Volume vs. Property Capacity",
            labels={"accommodates": "Max Guests (Capacity)",
                    "number_of_reviews": "Number of Reviews",
                    "room_type": "Room Type"},
            template=PLOTLY_TEMPLATE, opacity=0.5,
            hover_data={"price": ":$,.0f"},
            trendline="lowess", trendline_scope="overall",
            trendline_color_override="#FFB400",
        )
        fig5.update_layout(
            height=380,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig5, use_container_width=True)

    # -----------------------------------------------------------------------
    # Chart 6 — Cancellation policy: price & review comparison
    # (replaces instant_bookable which does not exist in this dataset)
    # -----------------------------------------------------------------------
    st.markdown("### 📋 Cancellation Policy Impact on Price & Reviews")
    cancel_summary = (
        df_clean.groupby("cancellation_policy")
        .agg(
            avg_price=("price", "mean"),
            median_price=("price", "median"),
            avg_reviews=("number_of_reviews", "mean"),
            listing_count=("price", "count"),
        )
        .reset_index()
        .sort_values("avg_price", ascending=False)
    )

    fig6 = go.Figure()
    fig6.add_trace(go.Bar(
        x=cancel_summary["cancellation_policy"],
        y=cancel_summary["avg_price"],
        name="Avg Price ($)", marker_color="#FF5A5F",
        text=cancel_summary["avg_price"].map("${:,.0f}".format),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg Price: $%{y:,.0f}<br>Count: " +
                      cancel_summary["listing_count"].map("{:,}".format) + "<extra></extra>",
    ))
    fig6.add_trace(go.Scatter(
        x=cancel_summary["cancellation_policy"],
        y=cancel_summary["avg_reviews"],
        name="Avg Reviews", yaxis="y2",
        mode="markers+lines",
        marker=dict(size=12, color="#00A699", symbol="diamond"),
        hovertemplate="<b>%{x}</b><br>Avg Reviews: %{y:.1f}<extra></extra>",
    ))
    fig6.update_layout(
        title="Cancellation Policy — Average Price & Review Count",
        xaxis_title="Cancellation Policy",
        yaxis=dict(title="Average Price ($)", showgrid=False),
        yaxis2=dict(title="Avg Number of Reviews", overlaying="y", side="right", showgrid=False),
        template=PLOTLY_TEMPLATE, height=420,
        legend=dict(orientation="h", y=1.08),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig6, use_container_width=True)
    st.info(
        "💡 **Note:** The `instant_bookable` field does not exist in the "
        "`sample_airbnb.listingsAndReviews` dataset. "
        "Cancellation policy is used here as the equivalent booking-flexibility dimension."
    )

    # -----------------------------------------------------------------------
    # Bonus: Bed type breakdown
    # -----------------------------------------------------------------------
    with st.expander("🛏️ Bed Type Distribution & Pricing"):
        if "bed_type" in df_clean.columns:
            bed_type_summary = (
                df_clean.groupby("bed_type")
                .agg(count=("price", "count"), avg_price=("price", "mean"))
                .reset_index()
                .sort_values("count", ascending=False)
            )
            fig_bt = px.bar(
                bed_type_summary, x="bed_type", y="count",
                color="avg_price", color_continuous_scale="RdYlGn",
                title="Listings by Bed Type",
                labels={"bed_type": "Bed Type", "count": "Listings",
                        "avg_price": "Avg Price ($)"},
                template=PLOTLY_TEMPLATE, text="count",
            )
            fig_bt.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig_bt.update_layout(
                height=360,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_bt, use_container_width=True)

    # -----------------------------------------------------------------------
    # Summary stats
    # -----------------------------------------------------------------------
    with st.expander("📊 Property Statistics Summary"):
        cols_of_interest = [c for c in [
            "bedrooms", "beds", "bathrooms", "accommodates",
            "minimum_nights", "price", "number_of_reviews", "score_rating"
        ] if c in df_clean.columns]
        st.dataframe(df_clean[cols_of_interest].describe().round(2), use_container_width=True)

except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.exception(e)
