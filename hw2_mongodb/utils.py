"""
utils.py
--------
Shared utility functions for the Airbnb MongoDB Dashboard.
Provides a cached MongoDB client and a cached data-loading helper.

Key data-type facts about sample_airbnb.listingsAndReviews:
  - price, cleaning_fee, security_deposit, bathrooms: BSON Decimal128  → must convert via str()
  - minimum_nights, maximum_nights: stored as STRING, not int         → cast to numeric
  - instant_bookable: field does NOT exist in this dataset             → skip
  - host.host_since: field does NOT exist in this dataset             → skip (use first_review)
  - review_scores_rating: scale 0–100 (integer)
  - address.suburb: often empty string — use government_area instead
  - address.location.coordinates: list [lon, lat]
"""

import streamlit as st
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import certifi
import pandas as pd


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@st.cache_resource
def init_connection() -> MongoClient:
    """Create and cache a MongoClient using .streamlit/secrets.toml credentials."""
    uri = st.secrets["connection"]["mongo"]["uri"]
    return MongoClient(uri, server_api=ServerApi("1"), tlsCAFile=certifi.where())


# ---------------------------------------------------------------------------
# Helper: safely convert BSON Decimal128 (or anything) to float
# ---------------------------------------------------------------------------

def _to_float(val):
    """Convert BSON Decimal128 / str / int / float → Python float, or None."""
    if val is None:
        return None
    try:
        return float(str(val))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_listings() -> pd.DataFrame:
    """
    Fetch all documents from sample_airbnb.listingsAndReviews and return
    a clean, flat pandas DataFrame with properly typed columns.

    Handles known quirks:
      - Decimal128 price fields converted via str(val)
      - minimum_nights / maximum_nights cast from str → int
      - government_area used as neighbourhood (suburb is often empty)
      - coordinates extracted from GeoJSON list [lon, lat]
    """
    client = init_connection()
    col = client["sample_airbnb"]["listingsAndReviews"]

    projection = {
        "_id": 0,
        "name": 1,
        "property_type": 1,
        "room_type": 1,
        "bed_type": 1,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "accommodates": 1,
        "minimum_nights": 1,
        "maximum_nights": 1,
        "price": 1,
        "cleaning_fee": 1,
        "security_deposit": 1,
        "extra_people": 1,
        "cancellation_policy": 1,
        "amenities": 1,
        "number_of_reviews": 1,
        "review_scores": 1,
        "host.host_name": 1,
        "host.host_is_superhost": 1,
        "host.host_listings_count": 1,
        "address.market": 1,
        "address.country": 1,
        "address.suburb": 1,
        "address.government_area": 1,
        "address.location.coordinates": 1,
        "availability.availability_30": 1,
        "availability.availability_60": 1,
        "availability.availability_90": 1,
        "availability.availability_365": 1,
        "first_review": 1,
        "last_review": 1,
    }

    docs = list(col.find({}, projection))

    # ------------------------------------------------------------------
    # Manual extraction (avoid json_normalize losing Decimal128 context)
    # ------------------------------------------------------------------
    rows = []
    for d in docs:
        host    = d.get("host", {}) or {}
        address = d.get("address", {}) or {}
        loc     = address.get("location", {}) or {}
        coords  = loc.get("coordinates")          # [lon, lat] or None
        avail   = d.get("availability", {}) or {}
        rs      = d.get("review_scores", {}) or {}

        rows.append({
            # Identifiers
            "name":             d.get("name"),
            # Listing attributes
            "property_type":    d.get("property_type"),
            "room_type":        d.get("room_type"),
            "bed_type":         d.get("bed_type"),
            "bedrooms":         d.get("bedrooms"),
            "beds":             d.get("beds"),
            "bathrooms":        _to_float(d.get("bathrooms")),
            "accommodates":     d.get("accommodates"),
            "minimum_nights":   d.get("minimum_nights"),   # str — cast later
            "maximum_nights":   d.get("maximum_nights"),   # str — cast later
            # Pricing (Decimal128 → float)
            "price":            _to_float(d.get("price")),
            "cleaning_fee":     _to_float(d.get("cleaning_fee")),
            "security_deposit": _to_float(d.get("security_deposit")),
            "extra_people":     _to_float(d.get("extra_people")),
            # Policies & amenities
            "cancellation_policy": d.get("cancellation_policy"),
            "amenities":           d.get("amenities", []),
            # Reviews
            "number_of_reviews":   d.get("number_of_reviews"),
            "score_rating":        rs.get("review_scores_rating"),
            "score_accuracy":      rs.get("review_scores_accuracy"),
            "score_cleanliness":   rs.get("review_scores_cleanliness"),
            "score_location":      rs.get("review_scores_location"),
            "score_value":         rs.get("review_scores_value"),
            # Host (host_since does not exist in this collection)
            "host_name":           host.get("host_name"),
            "is_superhost":        host.get("host_is_superhost"),  # bool
            "host_listings_count": host.get("host_listings_count"),
            # Address
            "market":              address.get("market"),
            "country":             address.get("country"),
            "suburb":              address.get("suburb"),
            "neighbourhood":       address.get("government_area"),  # richer than suburb
            # Coordinates
            "longitude":   coords[0] if isinstance(coords, list) and len(coords) == 2 else None,
            "latitude":    coords[1] if isinstance(coords, list) and len(coords) == 2 else None,
            # Availability
            "availability_30":  avail.get("availability_30"),
            "availability_60":  avail.get("availability_60"),
            "availability_90":  avail.get("availability_90"),
            "availability_365": avail.get("availability_365"),
            # Dates
            "first_review": d.get("first_review"),
            "last_review":  d.get("last_review"),
        })

    df = pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Type coercions
    # ------------------------------------------------------------------
    # minimum / maximum nights are strings in this dataset
    for col_name in ["minimum_nights", "maximum_nights"]:
        df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

    # Ensure numeric types
    for col_name in ["bedrooms", "beds", "accommodates", "number_of_reviews",
                     "host_listings_count", "availability_30", "availability_60",
                     "availability_90", "availability_365",
                     "score_rating", "score_accuracy", "score_cleanliness",
                     "score_location", "score_value"]:
        df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

    # Dates
    for col_name in ["first_review", "last_review"]:
        df[col_name] = pd.to_datetime(df[col_name], errors="coerce")

    # is_superhost: keep as bool (already bool from MongoDB)
    df["is_superhost"] = df["is_superhost"].astype("boolean")

    # Clean empty suburb → use neighbourhood instead
    df["suburb"] = df["suburb"].replace("", None)

    return df


# ---------------------------------------------------------------------------
# Shared Plotly theme
# ---------------------------------------------------------------------------

PLOTLY_TEMPLATE = "plotly_dark"
COLOR_SEQUENCE = [
    "#FF5A5F", "#FC642D", "#00A699", "#484848",
    "#FFB400", "#7B68EE", "#20B2AA", "#FF69B4",
]
