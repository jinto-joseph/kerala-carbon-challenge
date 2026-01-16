"""
Analyze why MORE deliveries = WORSE score
"""
import pandas as pd
import json

print("="*60)
print("SCORE PATTERN ANALYSIS")
print("="*60)

results = [
    {"deliveries": 2099, "predicted": 187632, "actual": -9911618},
    {"deliveries": 2161, "predicted": 446057, "actual": -16440570},  
    {"deliveries": 2002, "predicted": 54362, "actual": -16750449},
    {"deliveries": 8626, "predicted": 475814, "actual": -9078500},
]

print("\nDeliveries vs Actual Score:")
for r in results:
    gap = r['actual'] - r['predicted']
    per_delivery_gap = gap / r['deliveries'] if r['deliveries'] > 0 else 0
    print(f"  {r['deliveries']:4d} deliveries: Predicted {r['predicted']:+10,.0f} → Actual {r['actual']:+10,.0f}")
    print(f"       Gap: {gap:+10,.0f} ({per_delivery_gap:+8,.0f} per delivery)")

print("\n" + "="*60)
print("HYPOTHESIS")
print("="*60)
print("The gap per delivery ranges from -1,700 to -4,700 CO2/delivery")
print("This suggests we're VASTLY under-calculating excess N penalty")
print("")
print("Our calculation: Excess N = delivered N - demanded N")
print("               Penalty = excess * 10")
print("")
print("Kaggle might be: Penalizing ALL nitrogen if ANY is excess?")
print("             Or: Much stricter demand window (1-day not 10-day)?")
print("             Or: Rainfall penalty we're not accounting for?")

# Load current solution
solution = pd.read_csv('output/solution.csv')
deliveries = solution[solution['tons_delivered'] > 0]

print(f"\n" + "="*60)
print(f"CURRENT SOLUTION ANALYSIS")
print(f"="*60)
print(f"Total deliveries: {len(deliveries)}")
print(f"Total biosolids: {deliveries['tons_delivered'].sum():.0f} tons")
print(f"Average per delivery: {deliveries['tons_delivered'].mean():.2f} tons")
print(f"")
print(f"Delivery size distribution:")
precision = deliveries[deliveries['tons_delivered'] < 10.0]
full = deliveries[deliveries['tons_delivered'] == 10.0]
print(f"  Variable (0.1-9.9): {len(precision)} ({len(precision)/len(deliveries)*100:.1f}%)")
print(f"  Full truck (10.0):  {len(full)} ({len(full)/len(deliveries)*100:.1f}%)")

print(f"\n" + "="*60)
print(f"RECOMMENDATION")
print(f"="*60)
print(f"Try submitting sample_submission.csv AS-IS (all zeros)")
print(f"If that scores better than -9M, then ANY delivery hurts")
print(f"If it scores -10M to -11M, then we need ~1000-2000 PERFECT deliveries")
