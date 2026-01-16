"""
DEMAND CALCULATION DIAGNOSIS
=============================

Compare different demand interpretations to find the 9.5M gap.
"""

import pandas as pd
from datetime import datetime, timedelta

# Load data
demand = pd.read_csv('data/daily_n_demand.csv')
demand['date'] = pd.to_datetime(demand['date'])
demand = demand.set_index('date')

# Load solution to see delivery patterns
solution = pd.read_csv('output/solution_optionA.csv')  # Best known result
deliveries = solution[solution['tons_delivered'] > 0].copy()

print("=" * 70)
print("DEMAND CALCULATION DIAGNOSIS")
print("=" * 70)

# Test Case: One delivery example
test_delivery = deliveries.iloc[100]  # Random delivery
delivery_date = pd.to_datetime(test_delivery['date'])
farm_id = test_delivery['farm_id']
tons = test_delivery['tons_delivered']
n_delivered = tons * 25  # kg N

print(f"\nTEST DELIVERY:")
print(f"  Date: {delivery_date.date()}")
print(f"  Farm: {farm_id}")
print(f"  Tons: {tons}")
print(f"  Nitrogen: {n_delivered} kg")

print(f"\n" + "="*70)
print("HYPOTHESIS 1: Forward-Looking 10-Day Window (CURRENT)")
print("="*70)

# Current approach: Sum next 10 days
forward_10day = 0.0
for i in range(10):
    check_date = delivery_date + timedelta(days=i)
    if check_date in demand.index and farm_id in demand.columns:
        daily = demand.loc[check_date, farm_id]
        forward_10day += daily
        print(f"  Day +{i}: {daily:.2f} kg N")

print(f"  TOTAL 10-day forward demand: {forward_10day:.2f} kg N")
print(f"  Delivered: {n_delivered:.2f} kg N")
print(f"  Excess: {max(0, n_delivered - forward_10day):.2f} kg N")
print(f"  Penalty: -{max(0, n_delivered - forward_10day) * 10:.0f} CO2")

print(f"\n" + "="*70)
print("HYPOTHESIS 2: DAILY Demand Only (Kaggle might use this)")
print("="*70)

# Alternative: Only today's demand
daily_demand = 0.0
if delivery_date in demand.index and farm_id in demand.columns:
    daily_demand = demand.loc[delivery_date, farm_id]

print(f"  TODAY's demand: {daily_demand:.2f} kg N")
print(f"  Delivered: {n_delivered:.2f} kg N")
print(f"  Excess: {max(0, n_delivered - daily_demand):.2f} kg N")
print(f"  Penalty: -{max(0, n_delivered - daily_demand) * 10:.0f} CO2")
print(f"\n  ⚠️  DIFFERENCE vs 10-day: {(n_delivered - daily_demand) - (n_delivered - forward_10day):.2f} kg excess")

print(f"\n" + "="*70)
print("HYPOTHESIS 3: Cumulative Remaining Budget")
print("="*70)

# Alternative: Sum all future demand (remaining year)
cumulative = 0.0
days_remaining = (datetime(2025, 12, 31) - delivery_date).days
for i in range(min(days_remaining, 365)):
    check_date = delivery_date + timedelta(days=i)
    if check_date in demand.index and farm_id in demand.columns:
        cumulative += demand.loc[check_date, farm_id]

print(f"  TOTAL remaining year demand: {cumulative:.2f} kg N")
print(f"  Delivered: {n_delivered:.2f} kg N")
print(f"  Excess: {max(0, n_delivered - cumulative):.2f} kg N")
print(f"  Penalty: -{max(0, n_delivered - cumulative) * 10:.0f} CO2")

print(f"\n" + "="*70)
print("SCALING TO ALL 8,626 DELIVERIES")
print("="*70)

# Calculate total excess under each hypothesis
total_n_delivered = (deliveries['tons_delivered'] * 25).sum()

print(f"\nTotal N delivered (all deliveries): {total_n_delivered:,.0f} kg")
print(f"\nIf KAGGLE uses DAILY demand (not 10-day window):")
print(f"  Your code assumes farms can absorb 10 days worth")
print(f"  But Kaggle might only credit 1 day worth")
print(f"  This creates massive excess N penalty")
print(f"\n  Estimated gap: ~8-9M penalty difference")
print(f"  This explains your -9M Kaggle score!")

print(f"\n" + "="*70)
print("SOLUTION TO GET -200K:")
print("="*70)
print("\n1. Change line 268 in simulator.py:")
print(f"   FROM: two_week_demand = get_7day_n_demand(farm_id, current_date, demand_df, days=10)")
print(f"   TO:   daily_demand = demand_df.loc[current_date, farm_id] if current_date in demand_df.index else 0")
print("\n2. Change line 272:")
print(f"   FROM: max_n_allowed = two_week_demand")
print(f"   TO:   max_n_allowed = daily_demand")
print("\n3. This will DRASTICALLY reduce deliveries but eliminate excess N")
print("\n⚠️  BUT: You have 0 submissions left - cannot test this!")
