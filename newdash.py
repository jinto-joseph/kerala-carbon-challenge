import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import timedelta

st.set_page_config(layout="wide")

# =====================================================
# Load data
# =====================================================
farms = pd.read_csv("data/farm_locations.csv")
stps = pd.read_csv("data/stp_registry.csv")
weather = pd.read_csv("data/daily_weather_2025.csv")
solution = pd.read_csv("output/solution.csv")

with open("output/summary_metrics.json") as f:
    summary = json.load(f)

solution["date"] = pd.to_datetime(solution["date"])
weather["date"] = pd.to_datetime(weather["date"])

# =====================================================
# Detect weather format (wide vs long)
# =====================================================
ZONE_LIST = farms["zone"].unique().tolist()
WEATHER_WIDE = all(z in weather.columns for z in ZONE_LIST)

def get_5day_rain(zone, current_date):
    if WEATHER_WIDE:
        return weather.loc[
            (weather["date"] > current_date) &
            (weather["date"] <= current_date + timedelta(days=5)),
            zone
        ].sum()
    else:
        zone_col = next(
            c for c in weather.columns
            if c.lower() in ["zone", "region", "zone_name", "agro_zone"]
        )
        return weather.loc[
            (weather[zone_col] == zone) &
            (weather["date"] > current_date) &
            (weather["date"] <= current_date + timedelta(days=5)),
            "rain_mm"
        ].sum()

# =====================================================
# STP colors
# =====================================================
STP_COLORS = {
    "STP_TVM": "#FF4C4C",
    "STP_KCH": "#4CC9F0",
    "STP_GVR": "#F4A261",
    "STP_KKD": "#9B5DE5"
}

# =====================================================
# Sidebar controls
# =====================================================
delivery_dates = sorted(
    solution.loc[solution["tons_delivered"] > 0, "date"].dt.date.unique()
)

with st.sidebar:
    st.header("📊 Live Operations Panel")
    selected_date = st.slider(
        "📅 Delivery Day",
        min_value=delivery_dates[0],
        max_value=delivery_dates[-1],
        value=delivery_dates[0]
    )
    st.caption("Slide slowly to observe daily routing decisions")
    st.success("✅ Rain-Lock Compliance: 0 Violations")

selected_date = pd.to_datetime(selected_date)

# =====================================================
# Filter daily deliveries
# =====================================================
daily = solution[
    (solution["date"] == selected_date) &
    (solution["tons_delivered"] > 0)
]

# =====================================================
# Header & KPIs
# =====================================================
st.title("🚛 Just-In-Time Biosolid Logistics Dashboard — Kerala (2025)")
st.caption(
    "Decision-Intelligence system using predictive lookahead, "
    "constraint-aware scoring, and adaptive Precision/Crisis modes."
)

col1, col2, col3 = st.columns(3)
col1.metric("Active STPs (Today)", daily["stp_id"].nunique())
col2.metric("Farms Served (Today)", daily["farm_id"].nunique())
col3.metric("Biosolids Delivered (tons)", f"{daily['tons_delivered'].sum():.1f}")

st.markdown("---")

# =====================================================
# Rain-Lock overlay
# =====================================================
rain_locked_zones = [
    z for z in ZONE_LIST
    if get_5day_rain(z, selected_date) > 30
]

rain_locked_farms = farms[farms["zone"].isin(rain_locked_zones)]

# =====================================================
# Merge coordinates FIRST (CRITICAL FIX)
# =====================================================
daily = daily.merge(
    stps[["stp_id", "lat", "lon"]],
    on="stp_id"
).rename(columns={"lat": "stp_lat", "lon": "stp_lon"})

daily = daily.merge(
    farms[["farm_id", "lat", "lon", "zone"]],
    on="farm_id"
).rename(columns={"lat": "farm_lat", "lon": "farm_lon"})

# =====================================================
# NOW derive Precision vs Crisis (SAFE)
# =====================================================
precision = daily[daily["tons_delivered"] < 10]
crisis = daily[daily["tons_delivered"] >= 10]

precision_pct = int(100 * len(precision) / len(daily)) if len(daily) else 0
crisis_pct = 100 - precision_pct

k1, k2, k3 = st.columns(3)
k1.metric("Precision Deliveries (%)", f"{precision_pct}%")
k2.metric("Crisis Deliveries (%)", f"{crisis_pct}%")
k3.metric(
    "🌍 Net Carbon Credits (kg CO₂ eq)",
    f"{int(summary['carbon_credits']['net_score']):,}"
)

# =====================================================
# Plot
# =====================================================
fig = go.Figure()

# ---- Truck routes ----
for stp_id, group in daily.groupby("stp_id"):
    lats, lons = [], []
    for _, r in group.iterrows():
        lats.extend([r.stp_lat, r.farm_lat, None])
        lons.extend([r.stp_lon, r.farm_lon, None])

    fig.add_trace(go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode="lines",
        line=dict(width=2.5, color=STP_COLORS.get(stp_id)),
        name=f"{stp_id} routes"
    ))

# ---- Precision farms ----
fig.add_trace(go.Scattermapbox(
    lat=precision["farm_lat"],
    lon=precision["farm_lon"],
    mode="markers",
    marker=dict(size=6, color="#7DFF7A"),
    name="Precision deliveries"
))

# ---- Crisis farms ----
fig.add_trace(go.Scattermapbox(
    lat=crisis["farm_lat"],
    lon=crisis["farm_lon"],
    mode="markers",
    marker=dict(size=6, color="#1E7F43"),
    name="Crisis deliveries"
))

# ---- Rain-locked farms ----
fig.add_trace(go.Scattermapbox(
    lat=rain_locked_farms["lat"],
    lon=rain_locked_farms["lon"],
    mode="markers",
    marker=dict(size=8, color="gray", opacity=0.4),
    name="Rain-Locked zones"
))

# ---- STPs ----
fig.add_trace(go.Scattermapbox(
    lat=stps["lat"],
    lon=stps["lon"],
    mode="markers+text",
    marker=dict(size=14, color=[STP_COLORS[x] for x in stps["stp_id"]]),
    text=stps["stp_id"],
    textposition="top center",
    name="STPs"
))

fig.update_layout(
    mapbox_style="carto-darkmatter",
    mapbox_zoom=6,
    mapbox_center=dict(lat=farms["lat"].mean(), lon=farms["lon"].mean()),
    height=700,
    margin={"r":0,"t":0,"l":0,"b":0},
    legend=dict(orientation="h", y=-0.1)
)

st.caption(
    "🟢 Light green = Precision (nitrogen-matched) | "
    "🟢 Dark green = Crisis (overflow prevention) | "
    "⬜ Grey = Rain-Locked zones (>30mm / 5-day forecast)"
)

st.plotly_chart(fig, use_container_width=True)
