"""
Home.py
-------
Executive Summary, Navigation Hub, and Market Overview for the Airbnb MongoDB Dashboard.

Data notes (sample_airbnb.listingsAndReviews):
  - 5,555 total documents
  - price/cleaning_fee/security_deposit: BSON Decimal128 → float via utils._to_float()
  - minimum_nights: stored as string → cast to numeric in utils
  - instant_bookable field does NOT exist in this dataset
  - review_scores_rating: scale 0-100
  - is_superhost: native Python bool
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import init_connection, load_listings, PLOTLY_TEMPLATE, COLOR_SEQUENCE

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Airbnb Analytics Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — dark premium theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0f1117; }
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1d2e 0%, #16213e 100%);
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    [data-testid="metric-container"] label {
        color: #a0a8c0 !important; font-size: 0.78rem !important;
        font-weight: 500 !important; letter-spacing: 0.05em !important;
        text-transform: uppercase;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #ffffff !important; font-size: 1.8rem !important; font-weight: 700 !important;
    }
    h1 { color: #FF5A5F !important; letter-spacing: -0.5px; }
    h2, h3 { color: #e0e6f0 !important; }
    [data-testid="stSidebar"] { background-color: #13151f; }
    .info-card {
        background: linear-gradient(135deg, #1a1d2e 0%, #16213e 100%);
        border: 1px solid #2a2d3e; border-left: 4px solid #FF5A5F;
        border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
    }
    .info-card h4 { color: #FF5A5F; margin-bottom: 6px; }
    .info-card p  { color: #a0a8c0; font-size: 0.9rem; margin: 0; }
    .badge-success {
        background: #00A699; color: white; font-size: 0.72rem; font-weight: 600;
        padding: 2px 10px; border-radius: 20px; letter-spacing: 0.05em;
    }
    .divider { border-top: 1px solid #2a2d3e; margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
# with st.sidebar:
#     st.markdown("## 🏠 Airbnb Dashboard")
#     st.markdown("---")
#     st.markdown("**Data Source**")
#     st.markdown("`sample_airbnb.listingsAndReviews`")
#     st.markdown("**Total Documents**  \n5,555 listings")
#     st.markdown("---")
#     st.markdown("### 📑 Navigation")
#     st.page_link("Home.py",                              label="🏠 Home & Market Overview")
#     st.page_link("pages/2_Pricing_Dynamics.py",          label="💰 Pricing Dynamics")
#     st.page_link("pages/3_Geospatial_Analysis.py",       label="🗺️ Geospatial Analysis")
#     st.page_link("pages/4_Property_Characteristics.py",  label="🏡 Property Characteristics")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("# 🏠 Airbnb Analytics Dashboard")
st.markdown(
    "> **An end-to-end analytical platform** powered by MongoDB Atlas and the "
    "`sample_airbnb` dataset. Explore pricing trends, market dynamics, geospatial "
    "patterns, and property characteristics across **5,555 global Airbnb listings**."
)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Connection & data load
# ---------------------------------------------------------------------------
try:
    client = init_connection()
    client.admin.command("ping")

    col_status, _ = st.columns([1, 5])
    with col_status:
        st.markdown('<span class="badge-success">● CONNECTED</span>', unsafe_allow_html=True)

    df = load_listings()

    # -----------------------------------------------------------------------
    # KPI metrics
    # -----------------------------------------------------------------------
    st.markdown("### 📈 Key Performance Indicators")

    total_listings  = len(df)
    median_price    = df["price"].median()
    total_reviews   = int(df["number_of_reviews"].sum())
    avg_score       = df["score_rating"].dropna().mean()     # scale 0–100
    unique_markets  = df["market"].nunique()
    # is_superhost is a pandas BooleanDtype — cast to bool first
    superhost_pct   = (df["is_superhost"].astype(bool).sum() / total_listings * 100)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🏘️ Total Listings",      f"{total_listings:,}")
    c2.metric("💵 Median Price / Night", f"${median_price:,.0f}")
    c3.metric("⭐ Total Reviews",        f"{total_reviews:,}")
    c4.metric("🏅 Avg Rating Score",    f"{avg_score:.1f} / 100")
    c5.metric("🌍 Unique Markets",       f"{unique_markets}")
    c6.metric("🦸 Superhost Listings",  f"{superhost_pct:.1f}%")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Global market bar chart
    # -----------------------------------------------------------------------
    st.markdown("### 🌐 Global Listing Distribution by Market")

    market_counts = (
        df[df["market"].notna()]
        .groupby("market")
        .agg(listings=("price", "count"), median_price=("price", "median"))
        .reset_index()
        .sort_values("listings", ascending=False)
        .head(20)
    )

    fig = px.bar(
        market_counts,
        x="market",
        y="listings",
        color="median_price",
        color_continuous_scale="RdYlGn",
        title="Top 20 Markets by Listing Volume  (color = median nightly price)",
        labels={"market": "Market", "listings": "Listings",
                "median_price": "Median Price ($)"},
        template=PLOTLY_TEMPLATE,
        hover_data={"median_price": ":$.0f", "listings": ":,"},
        text="listings",
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(
        height=400,
        xaxis_tickangle=-35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="Median Price ($)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ============================= MARKET OVERVIEW SECTIONS ====================================
    st.markdown("## 📊 Market Overview")
    st.markdown("Macro-level trends across property types, room categories, cancellation policies, and host growth.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### 🏘️ Supply & Structure")
    col1, col2 = st.columns([3, 2])

    # Chart 1 — Top property types (horizontal bar)
    with col1:
        prop_counts = (
            df["property_type"].value_counts()
            .reset_index()
            .rename(columns={"property_type": "Property Type", "count": "Listings"})
            .head(15)
        )
        fig1 = px.bar(
            prop_counts, x="Listings", y="Property Type", orientation="h",
            color="Listings", color_continuous_scale="RdYlGn",
            title="Top 15 Property Types by Listing Count",
            template=PLOTLY_TEMPLATE, text="Listings",
        )
        fig1.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig1.update_layout(
            height=460, yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2 — Room type donut
    with col2:
        room_counts = df["room_type"].value_counts().reset_index()
        room_counts.columns = ["Room Type", "Count"]
        fig2 = px.pie(
            room_counts, names="Room Type", values="Count", hole=0.55,
            color_discrete_sequence=COLOR_SEQUENCE,
            title="Room Type Distribution", template=PLOTLY_TEMPLATE,
        )
        fig2.update_traces(
            textposition="inside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{value:,} listings (%{percent})<extra></extra>",
        )
        fig2.update_layout(
            height=460,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.markdown("### 📋 Policies & Hosts")
    col3, col4 = st.columns([2, 3])

    # Chart 3 — Cancellation policy donut
    with col3:
        cancel_counts = df["cancellation_policy"].value_counts().reset_index()
        cancel_counts.columns = ["Policy", "Count"]
        fig3 = px.pie(
            cancel_counts, names="Policy", values="Count", hole=0.5,
            color_discrete_sequence=COLOR_SEQUENCE,
            title="Cancellation Policy Breakdown", template=PLOTLY_TEMPLATE,
        )
        fig3.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{value:,} listings (%{percent})<extra></extra>",
        )
        fig3.update_layout(
            height=420,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Chart 4 — Top hosts by listing count
    with col4:
        top_hosts = (
            df.groupby("host_name")["price"]
            .agg(count="count", median_price="median")
            .reset_index()
            .sort_values("count", ascending=False)
            .head(15)
        )
        fig4 = px.bar(
            top_hosts, x="host_name", y="count",
            color="median_price", color_continuous_scale="RdYlGn",
            title="Top 15 Hosts by Number of Listings",
            labels={"host_name": "Host", "count": "Listings",
                    "median_price": "Median Price ($)"},
            template=PLOTLY_TEMPLATE,
            hover_data={"median_price": ":$.0f", "count": ":,"},
            text="count",
        )
        fig4.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig4.update_layout(
            height=420, xaxis_tickangle=-35,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)

    # Chart 5 — Superhost vs regular host
    st.markdown("#### Superhost vs Regular Host — Listing Count & Median Price")
    sh = df.copy()
    sh["Superhost"] = sh["is_superhost"].astype(bool).map(
        {True: "⭐ Superhost", False: "Regular Host"}
    )
    sh_summary = (
        sh.groupby("Superhost")
        .agg(listings=("price", "count"), median_price=("price", "median"),
             avg_reviews=("number_of_reviews", "mean"))
        .reset_index()
    )

    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        x=sh_summary["Superhost"], y=sh_summary["listings"],
        name="Listings", marker_color="#FF5A5F",
        text=sh_summary["listings"].map("{:,}".format), textposition="outside",
    ))
    fig5.add_trace(go.Scatter(
        x=sh_summary["Superhost"], y=sh_summary["median_price"],
        name="Median Price ($)", yaxis="y2",
        mode="markers", marker=dict(size=14, color="#FFB400", symbol="diamond"),
    ))
    fig5.update_layout(
        yaxis=dict(title="Number of Listings", showgrid=False),
        yaxis2=dict(title="Median Price ($)", overlaying="y", side="right", showgrid=False),
        template=PLOTLY_TEMPLATE, height=360,
        legend=dict(orientation="h", y=1.08),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig5, use_container_width=True)

    st.divider()

    st.markdown("### 📅 Host Growth")
    
    # Chart 6 — Listing growth timeline
    timeline_df = df[df["first_review"].notna()].copy()
    timeline_df["year_month"] = timeline_df["first_review"].dt.to_period("M").dt.to_timestamp()
    monthly = timeline_df.groupby("year_month").size().reset_index(name="new_listings")
    monthly["cumulative_listings"] = monthly["new_listings"].cumsum()

    fig6 = px.area(
        monthly, x="year_month", y="cumulative_listings",
        title="Cumulative Listing Growth Over Time (by First Review Date)",
        labels={"year_month": "Date", "cumulative_listings": "Cumulative Active Listings"},
        template=PLOTLY_TEMPLATE, color_discrete_sequence=["#FF5A5F"],
    )
    fig6.update_traces(
        fill="tozeroy", line_width=2,
        hovertemplate="<b>%{x|%b %Y}</b><br>Total active listings: %{y:,}<extra></extra>",
    )
    fig6.update_layout(
        height=420, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig6, use_container_width=True)

    # New listings active per year
    monthly["year"] = monthly["year_month"].dt.year
    yearly = monthly.groupby("year")["new_listings"].sum().reset_index()
    peak_year = int(yearly.loc[yearly["new_listings"].idxmax(), "year"])

    fig7 = px.bar(
        yearly, x="year", y="new_listings",
        color="new_listings", color_continuous_scale="RdYlGn",
        title="New Active Listings per Year (by First Review Date)",
        labels={"year": "Year", "new_listings": "Listings with First Review"},
        template=PLOTLY_TEMPLATE, text="new_listings",
    )
    fig7.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig7.update_layout(
        height=360, coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig7, use_container_width=True)
    st.info(
        f"📈 **Peak listing activity year:** {peak_year} — "
        "most listings received their first review in this year. "
        "*(Note: `host_since` is not available in this dataset; `first_review` is used as a proxy.)*"
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Page navigator cards (Updated)
    # -----------------------------------------------------------------------
    # st.markdown("### 🗂️ Explore the Dashboard")
    # nc1, nc2 = st.columns(2)
    # with nc1:
    #     st.markdown("""
    #     <div class="info-card">
    #         <h4>💰 Pricing Dynamics</h4>
    #         <p>Understand what drives listing prices — review scores, neighbourhood effects, fees, and room type premiums.</p>
    #     </div>
    #     """, unsafe_allow_html=True)
    # with nc2:
    #     st.markdown("""
    #     <div class="info-card">
    #         <h4>🗺️ Geospatial Analysis</h4>
    #         <p>Interactive Mapbox maps showing listing density, price heat, and availability across global markets.</p>
    #     </div>
    #     """, unsafe_allow_html=True)
    
    # st.markdown("""
    #     <div class="info-card">
    #         <h4>🏡 Property Characteristics</h4>
    #         <p>Deep-dive into bedroom counts, amenities, minimum stays, and their revenue impact.</p>
    #     </div>
    # """, unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Raw data preview
    # -----------------------------------------------------------------------
    with st.expander("🔍 Raw Data Preview (first 100 rows)"):
        preview_cols = [c for c in ["name", "market", "property_type", "room_type",
                                     "price", "bedrooms", "beds", "number_of_reviews",
                                     "score_rating", "cancellation_policy"] if c in df.columns]
        st.dataframe(df[preview_cols].head(100), use_container_width=True)

    with st.expander("📐 DataFrame Schema & Null Counts"):
        info_df = pd.DataFrame({
            "dtype": df.dtypes.astype(str),
            "non_null": df.notna().sum(),
            "null": df.isna().sum(),
            "null_%": (df.isna().sum() / len(df) * 100).round(1),
        })
        st.dataframe(info_df, use_container_width=True)

except Exception as e:
    st.error(f"❌ Could not connect to MongoDB: {e}")
    st.info(
        "**Troubleshooting:**\n"
        "1. Whitelist your IP in MongoDB Atlas → Network Access.\n"
        "2. Verify URI in `.streamlit/secrets.toml` under `[connection.mongo]`.\n"
        "3. Ensure `pymongo` and `certifi` are installed."
    )
