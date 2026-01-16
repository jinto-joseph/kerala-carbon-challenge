"""
Rain-Lock Verification Script
=============================

Critical audit for final submission: Verify ZERO rain violations in solution.csv

With 6,297 deliveries (vs 2,642 in binary version), we have 2.4x more opportunities
for rain violations. This script checks every single delivery against the 5-day
rainfall forecast to ensure 100% compliance with the Rain-Lock rule.

Usage:
    python src/verify_rain_lock.py
"""

import pandas as pd
from datetime import datetime, timedelta
import json

# Load data
print("=" * 60)
print("RAIN-LOCK VERIFICATION - FINAL SUBMISSION AUDIT")
print("=" * 60)
print()

# Load config
with open('data/config.json') as f:
    config = json.load(f)
    
rain_threshold = config['environmental_thresholds']['rain_lock_threshold_mm']

# Load data files
print("Loading data files...")
solution = pd.read_csv('output/solution.csv')
weather = pd.read_csv('data/daily_weather_2025.csv', parse_dates=['date'])
weather.set_index('date', inplace=True)
farms = pd.read_csv('data/farm_locations.csv')

# Create farm zone lookup
farm_zones = dict(zip(farms['farm_id'], farms['zone']))

print(f"✅ Loaded {len(solution)} delivery records")
print(f"✅ Rain threshold: {rain_threshold}mm over 5 days")
print()

# Filter only actual deliveries (tons > 0)
actual_deliveries = solution[solution['tons_delivered'] > 0].copy()
print(f"🚚 Total deliveries to verify: {len(actual_deliveries)}")
print()

# Check each delivery
violations = []
checked = 0

for idx, delivery in actual_deliveries.iterrows():
    delivery_date = pd.to_datetime(delivery['date'])
    farm_id = delivery['farm_id']
    farm_zone = farm_zones.get(farm_id)
    
    if farm_zone is None:
        print(f"⚠️  WARNING: Unknown farm {farm_id}")
        continue
    
    # Check next 5 days of rain
    total_rain = 0.0
    for i in range(5):
        check_date = delivery_date + timedelta(days=i)
        if check_date in weather.index:
            total_rain += weather.loc[check_date, farm_zone]
    
    # Check for violation
    if total_rain > rain_threshold:
        violations.append({
            'date': delivery_date.strftime('%Y-%m-%d'),
            'stp_id': delivery['stp_id'],
            'farm_id': farm_id,
            'farm_zone': farm_zone,
            'tons_delivered': delivery['tons_delivered'],
            '5day_rain_mm': round(total_rain, 2)
        })
    
    checked += 1
    
    # Progress indicator
    if checked % 1000 == 0:
        print(f"   Checked {checked:,} deliveries...")

print()
print("=" * 60)
print("VERIFICATION RESULTS")
print("=" * 60)
print()
print(f"✅ Total deliveries checked: {checked:,}")
print(f"🎯 Rain-Lock violations found: {len(violations)}")
print()

if len(violations) == 0:
    print("🎉 SUCCESS! ZERO RAIN VIOLATIONS DETECTED!")
    print("   All deliveries comply with the Rain-Lock rule.")
    print("   Solution is submission-ready! ✅")
else:
    print("❌ CRITICAL ERRORS DETECTED!")
    print()
    print("The following deliveries violate the Rain-Lock rule:")
    print()
    
    for i, v in enumerate(violations[:10], 1):  # Show first 10
        print(f"{i}. Date: {v['date']}, Farm: {v['farm_id']} ({v['farm_zone']})")
        print(f"   Tons: {v['tons_delivered']}, 5-day rain: {v['5day_rain_mm']}mm")
        print()
    
    if len(violations) > 10:
        print(f"   ... and {len(violations) - 10} more violations")
    
    print()
    print("⚠️  SOLUTION NEEDS FIXING BEFORE SUBMISSION!")

print()
print("=" * 60)
print()

# Export violations if any
if len(violations) > 0:
    violations_df = pd.DataFrame(violations)
    violations_df.to_csv('output/rain_lock_violations.csv', index=False)
    print(f"📄 Violations exported to: output/rain_lock_violations.csv")
else:
    print("📊 COMPLIANCE STATS:")
    print(f"   - Deliveries verified: {checked:,}")
    print(f"   - Violation rate: 0.00%")
    print(f"   - Compliance rate: 100.00% ✅")
    print()
    print("   This demonstrates robust weather-aware decision-making!")

print()
print("Verification complete.")
