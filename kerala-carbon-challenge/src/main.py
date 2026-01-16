import pandas as pd
import json
import os
from datetime import datetime, timedelta

# 1. Load Constants from config.json (DO NOT HARDCODE)
with open('data/config.json', 'r') as f:
    config = json.load(f)
    # Access example: config['agronomic_constants']['nitrogen_content_kg_per_ton_biosolid']

# 2. Load the Digital Twin Data
farms = pd.read_csv('data/farm_locations.csv')
stps = pd.read_csv('data/stp_registry.csv')
weather = pd.read_csv('data/daily_weather_2025.csv')
demand = pd.read_csv('data/daily_n_demand.csv')

# Convert date column to datetime for easier manipulation
weather['date'] = pd.to_datetime(weather['date'])

print("System Initialized. Ready for simulation.")

# ============================================
# RAIN-LOCK CHECKER (Your Weather Scout!)
# ============================================

def is_rain_locked(farm_zone, delivery_date, weather_df, rain_threshold=30, look_ahead_days=5):
    """
    Check if a farm is BLOCKED by the Rain-Lock rule.
    
    Think of this as your "Weather Scout" 🌧️
    
    Args:
        farm_zone: The zone name (e.g., "Kuttanad", "Palakkad", "Highlands", "Coastal")
        delivery_date: The date you want to deliver (as string "2025-01-15" or datetime)
        weather_df: The weather dataframe
        rain_threshold: Maximum total rain allowed in next 5 days (default: 30mm)
        look_ahead_days: How many days ahead to check (default: 5)
    
    Returns:
        True if BLOCKED (too much rain coming!), False if SAFE to deliver
    """
    # Convert to datetime if it's a string
    if isinstance(delivery_date, str):
        delivery_date = pd.to_datetime(delivery_date)
    
    # Calculate the 5-day window
    end_date = delivery_date + timedelta(days=look_ahead_days)
    
    # Filter weather data for this time window
    window = weather_df[
        (weather_df['date'] >= delivery_date) & 
        (weather_df['date'] < end_date)
    ]
    
    # Sum up the rainfall for this zone
    total_rainfall = window[farm_zone].sum()
    
    # Check if it exceeds the threshold
    is_blocked = total_rainfall > rain_threshold
    
    return is_blocked


# ============================================
# TEST THE RAIN-LOCK CHECKER
# ============================================

# Example: Check if we can deliver to a Coastal farm on Jan 1, 2025
test_date = "2025-01-01"
test_zone = "Coastal"

if is_rain_locked(test_zone, test_date, weather):
    print(f"⛔ BLOCKED! Cannot deliver to {test_zone} on {test_date} - Too much rain coming!")
else:
    print(f"✅ SAFE! You can deliver to {test_zone} on {test_date}")

# Let's test a few more zones
print("\n--- Quick Rain-Lock Test for Jan 1, 2025 ---")
for zone in ['Kuttanad', 'Palakkad', 'Highlands', 'Coastal']:
    status = "⛔ BLOCKED" if is_rain_locked(zone, test_date, weather) else "✅ SAFE"
    print(f"{zone:12} : {status}")


# ============================================
# STEP 3: DISTANCE MAP (Pre-Calculate Once!)
# ============================================

import math

def haversine_distance(lat1, lon1, lat2, lon2, radius_km=6371):
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    
    Think of this as your GPS calculator 📍
    
    Args:
        lat1, lon1: Latitude and Longitude of point 1 (in degrees)
        lat2, lon2: Latitude and Longitude of point 2 (in degrees)
        radius_km: Earth's radius in kilometers (from config)
    
    Returns:
        Distance in kilometers
    """
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2)**2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = radius_km * c
    return distance


def build_distance_matrix(stps_df, farms_df, earth_radius):
    """
    Pre-calculate distances between ALL STPs and ALL Farms.
    
    This saves you from calculating the same distance 365 times! 🚀
    
    Returns:
        A dictionary: {('STP_TVM', 'F_1000'): 45.2, ...}
    """
    distance_map = {}
    
    print("\n🗺️  Building Distance Matrix...")
    
    for _, stp in stps_df.iterrows():
        for _, farm in farms_df.iterrows():
            dist = haversine_distance(
                stp['lat'], stp['lon'],
                farm['lat'], farm['lon'],
                earth_radius
            )
            # Store the distance
            distance_map[(stp['stp_id'], farm['farm_id'])] = dist
    
    print(f"✅ Distance Matrix Complete! {len(distance_map)} routes calculated.")
    return distance_map


# Build the distance matrix NOW (do this once, use it forever!)
earth_radius = config['logistics_constants']['haversine_earth_radius_km']
distance_matrix = build_distance_matrix(stps, farms, earth_radius)

# Test: What's the distance from STP_TVM to the first farm?
test_stp = stps.iloc[0]['stp_id']
test_farm = farms.iloc[0]['farm_id']
test_distance = distance_matrix[(test_stp, test_farm)]
print(f"\n📏 Sample Distance: {test_stp} → {test_farm} = {test_distance:.2f} km")


# ============================================
# STEP 4: STORAGE TRACKER (Tank Monitor!)
# ============================================

class STPStorageTracker:
    """
    Your "Tank Monitor" to prevent overflow disasters! 🚨
    
    This tracks how full each STP storage tank is over time.
    """
    
    def __init__(self, stps_df):
        """Initialize with empty tanks."""
        self.storage = {}  # {stp_id: current_tons}
        self.max_capacity = {}  # {stp_id: max_tons}
        self.daily_input = {}  # {stp_id: tons_per_day}
        
        for _, stp in stps_df.iterrows():
            self.storage[stp['stp_id']] = 0.0  # Start empty
            self.max_capacity[stp['stp_id']] = stp['storage_max_tons']
            self.daily_input[stp['stp_id']] = stp['daily_output_tons']
    
    def add_daily_waste(self, stp_id):
        """Add today's new waste to the tank."""
        self.storage[stp_id] += self.daily_input[stp_id]
    
    def remove_delivery(self, stp_id, tons):
        """Remove waste when a truck delivers it to a farm."""
        if tons > self.storage[stp_id]:
            raise ValueError(f"Cannot deliver {tons} tons from {stp_id}! Only {self.storage[stp_id]:.1f} available.")
        self.storage[stp_id] -= tons
    
    def is_overflowing(self, stp_id):
        """Check if a tank has exceeded its max capacity."""
        return self.storage[stp_id] > self.max_capacity[stp_id]
    
    def get_fullness_percent(self, stp_id):
        """Get how full a tank is (0-100%)."""
        return (self.storage[stp_id] / self.max_capacity[stp_id]) * 100
    
    def get_most_full_stp(self):
        """Find which STP is closest to overflow (priority target!)."""
        fullness = {stp_id: self.get_fullness_percent(stp_id) 
                   for stp_id in self.storage.keys()}
        return max(fullness, key=fullness.get)
    
    def simulate_day(self):
        """Simulate one day: add waste to all tanks."""
        for stp_id in self.storage.keys():
            self.add_daily_waste(stp_id)
    
    def get_status_report(self):
        """Print the current status of all tanks."""
        print("\n🛢️  STP STORAGE STATUS:")
        print("-" * 50)
        for stp_id in sorted(self.storage.keys()):
            current = self.storage[stp_id]
            max_cap = self.max_capacity[stp_id]
            percent = self.get_fullness_percent(stp_id)
            
            # Visual bar
            bar_length = 20
            filled = int(bar_length * percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            # Color coding
            if percent > 80:
                status = "🔴 CRITICAL"
            elif percent > 50:
                status = "🟡 WARNING"
            else:
                status = "🟢 OK"
            
            print(f"{stp_id:10} [{bar}] {percent:5.1f}% ({current:.1f}/{max_cap} tons) {status}")


# Initialize the Storage Tracker
tracker = STPStorageTracker(stps)

# Simulate 10 days of waste accumulation (no deliveries)
print("\n⏰ Simulating 10 days with NO deliveries...")
for day in range(10):
    tracker.simulate_day()

tracker.get_status_report()

print(f"\n🎯 Most Critical Tank: {tracker.get_most_full_stp()}")


# ============================================
# SAVE DISTANCE MATRIX FOR TOMORROW!
# ============================================

# Save the distance matrix to a CSV for easy access
import csv

output_path = 'output/distance_matrix.csv'
os.makedirs('output', exist_ok=True)

with open(output_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['stp_id', 'farm_id', 'distance_km'])
    for (stp_id, farm_id), distance in distance_matrix.items():
        writer.writerow([stp_id, farm_id, f"{distance:.4f}"])

print(f"\n💾 Distance Matrix saved to: {output_path}")
print("\n" + "="*50)
print("🎉 ALL UTILITIES READY! You're set for tomorrow!")
print("="*50)