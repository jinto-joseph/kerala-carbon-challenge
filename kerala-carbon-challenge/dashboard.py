import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =====================================================
# Load data (CORRECT PATHS)
# =====================================================
farms = pd.read_csv("data/farm_locations.csv")
stps = pd.read_csv("data/stp_registry.csv")
solution = pd.read_csv("output/solution.csv")   # ← CONFIRMED PATH

solution["date"] = pd.to_datetime(solution["date"]).dt.date

# =====================================================
# Fixed STP color identity
# =====================================================
STP_COLORS = {
    "STP_TVM": "#FF4C4C",   # Red
    "STP_KCH": "#4CC9F0",   # Cyan
    "STP_GVR": "#F4A261",   # Orange
    "STP_KKD": "#9B5DE5"    # Purple
}

# =====================================================
# Slider snaps to delivery days only (demo-friendly)
# =====================================================
delivery_dates = sorted(
    solution.loc[solution["tons_delivered"] > 0, "date"].unique()
)

with st.sidebar:
    st.header("Controls")
    selected_date = st.slider(
        "📅 Delivery Day",
        min_value=delivery_dates[0],
        max_value=delivery_dates[-1],
        value=delivery_dates[0]
    )

# =====================================================
# Filter deliveries
# =====================================================
daily = solution[
    (solution["date"] == selected_date) &
    (solution["tons_delivered"] > 0)
]

# =====================================================
# Header + KPIs
# =====================================================
st.title("🚛 Biosolid Logistics — Daily Execution View")

col1, col2, col3 = st.columns(3)
col1.metric("Active STPs", daily["stp_id"].nunique())
col2.metric("Farms Served", daily["farm_id"].nunique())
col3.metric("Total Tons Delivered", f"{daily['tons_delivered'].sum():.1f}")

st.caption(
    "Truck routes are color-coded by STP. "
    "Only rain-safe, demand-valid deliveries are shown."
)

# =====================================================
# Join coordinates
# =====================================================
daily = daily.merge(
    stps[["stp_id", "lat", "lon"]],
    on="stp_id",
    how="left"
).rename(columns={"lat": "stp_lat", "lon": "stp_lon"})

daily = daily.merge(
    farms[["farm_id", "lat", "lon"]],
    on="farm_id",
    how="left"
).rename(columns={"lat": "farm_lat", "lon": "farm_lon"})

# =====================================================
# Plot
# =====================================================
fig = go.Figure()

# ---- Truck routes (one trace per STP) ----
for stp_id, group in daily.groupby("stp_id"):
    line_lats, line_lons = [], []

    for _, row in group.iterrows():
        line_lats.extend([row.stp_lat, row.farm_lat, None])
        line_lons.extend([row.stp_lon, row.farm_lon, None])

    fig.add_trace(go.Scattermapbox(
        lat=line_lats,
        lon=line_lons,
        mode="lines",
        line=dict(width=2.5, color=STP_COLORS.get(stp_id, "white")),
        name=f"{stp_id} trucks"
    ))

# ---- STP markers ----
fig.add_trace(go.Scattermapbox(
    lat=stps["lat"],
    lon=stps["lon"],
    mode="markers+text",
    marker=dict(
        size=14,
        color=[STP_COLORS.get(x, "white") for x in stps["stp_id"]]
    ),
    text=stps["stp_id"],
    textposition="top center",
    name="STPs"
))

# ---- Farm markers ----
fig.add_trace(go.Scattermapbox(
    lat=farms["lat"],
    lon=farms["lon"],
    mode="markers",
    marker=dict(size=6, color="#2ECC71"),
    name="Farms"
))

fig.update_layout(
    mapbox_style="carto-darkmatter",
    mapbox_zoom=6,
    mapbox_center=dict(
        lat=farms["lat"].mean(),
        lon=farms["lon"].mean()
    ),
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=650,
    legend=dict(
        title="Delivery Origin (STP)",
        orientation="h",
        y=-0.08
    )
)

st.subheader(f"📍 Truck movements on {selected_date}")
st.plotly_chart(fig, use_container_width=True)
