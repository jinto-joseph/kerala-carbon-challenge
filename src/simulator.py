import pandas as pd
import json
import os
from datetime import datetime, timedelta
import math

# ============================================
# LOAD DATA AND CONFIG
# ============================================

with open('data/config.json', 'r') as f:
    config = json.load(f)

farms = pd.read_csv('data/farm_locations.csv')
stps = pd.read_csv('data/stp_registry.csv')
weather = pd.read_csv('data/daily_weather_2025.csv')
demand = pd.read_csv('data/daily_n_demand.csv')

# Convert dates to datetime
weather['date'] = pd.to_datetime(weather['date'])
demand['date'] = pd.to_datetime(demand['date'])

# Set demand date as index for easy lookup
demand = demand.set_index('date')

print("=" * 60)
print("KERALA CARBON CHALLENGE - DECISION ENGINE")
print("=" * 60)

# ============================================
# UTILITY FUNCTIONS
# ============================================

def is_rain_locked(farm_zone, delivery_date, weather_df, 
                   rain_threshold=30, look_ahead_days=5):
    """Check if farm is blocked by rain-lock rule."""
    if isinstance(delivery_date, str):
        delivery_date = pd.to_datetime(delivery_date)
    
    end_date = delivery_date + timedelta(days=look_ahead_days)
    window = weather_df[
        (weather_df['date'] >= delivery_date) & 
        (weather_df['date'] < end_date)
    ]
    total_rainfall = window[farm_zone].sum()
    return total_rainfall > rain_threshold


def haversine_distance(lat1, lon1, lat2, lon2, radius_km=6371):
    """Calculate distance using Haversine formula."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2)**2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return radius_km * c


def build_distance_matrix(stps_df, farms_df, earth_radius):
    """Pre-calculate all STP-to-Farm distances."""
    distance_map = {}
    for _, stp in stps_df.iterrows():
        for _, farm in farms_df.iterrows():
            dist = haversine_distance(
                stp['lat'], stp['lon'],
                farm['lat'], farm['lon'],
                earth_radius
            )
            distance_map[(stp['stp_id'], farm['farm_id'])] = dist
    return distance_map


# Build distance matrix
earth_radius = config['logistics_constants']['haversine_earth_radius_km']
distance_matrix = build_distance_matrix(stps, farms, earth_radius)
print(f"✅ Distance Matrix: {len(distance_matrix)} routes pre-calculated")


# ============================================
# STP STORAGE TRACKER
# ============================================

class STPStorageTracker:
    """Monitor STP tank levels to prevent overflow."""
    
    def __init__(self, stps_df):
        self.storage = {}
        self.max_capacity = {}
        self.daily_input = {}
        
        for _, stp in stps_df.iterrows():
            self.storage[stp['stp_id']] = 0.0
            self.max_capacity[stp['stp_id']] = stp['storage_max_tons']
            self.daily_input[stp['stp_id']] = stp['daily_output_tons']
    
    def add_daily_waste(self, stp_id):
        """Add today's waste generation."""
        self.storage[stp_id] += self.daily_input[stp_id]
    
    def remove_delivery(self, stp_id, tons):
        """Remove waste when delivered to farm."""
        self.storage[stp_id] -= tons
    
    def is_overflowing(self, stp_id):
        """Check if tank exceeded capacity."""
        return self.storage[stp_id] > self.max_capacity[stp_id]
    
    def get_overflow_tons(self, stp_id):
        """Get amount of overflow."""
        if self.is_overflowing(stp_id):
            return self.storage[stp_id] - self.max_capacity[stp_id]
        return 0.0
    
    def get_fullness_percent(self, stp_id):
        """Get tank fullness percentage."""
        return (self.storage[stp_id] / self.max_capacity[stp_id]) * 100
    
    def get_available_biosolid(self, stp_id):
        """Get available biosolid for delivery."""
        return max(0, self.storage[stp_id])
    
    def get_stps_by_fullness(self):
        """Get STPs sorted by fullness (most full first)."""
        fullness = [(stp_id, self.get_fullness_percent(stp_id)) 
                   for stp_id in self.storage.keys()]
        return sorted(fullness, key=lambda x: x[1], reverse=True)


# ============================================
# CARBON CREDIT ACCOUNTANT
# ============================================

class CarbonCreditAccountant:
    """Track carbon credits and penalties in real-time."""
    
    def __init__(self, config):
        self.config = config
        self.total_credits = 0.0
        self.total_penalties = 0.0
        
        # Breakdown tracking
        self.nitrogen_credits = 0.0
        self.soil_carbon_credits = 0.0
        self.transport_emissions = 0.0
        self.overflow_penalties = 0.0
        self.excess_n_penalties = 0.0
        
        # Constants from config
        self.n_content = config['agronomic_constants']['nitrogen_content_kg_per_ton_biosolid']
        self.n_offset_credit = config['agronomic_constants']['synthetic_n_offset_credit_kg_co2_per_kg_n']
        self.soil_carbon_gain = config['agronomic_constants']['soil_organic_carbon_gain_kg_co2_per_kg_biosolid']
        self.diesel_emission = config['logistics_constants']['diesel_emission_factor_kg_co2_per_km']
        self.leaching_penalty = config['agronomic_constants']['leaching_penalty_kg_co2_per_kg_excess_n']
        self.overflow_penalty = config['environmental_thresholds']['stp_overflow_penalty_kg_co2_per_ton']
    
    def calculate_delivery_score(self, tons_delivered, distance_km, n_demand_kg, n_delivered_kg):
        """
        Calculate net carbon credits for a single delivery.
        
        Returns: net_credits, breakdown_dict
        """
        # CREDITS
        nitrogen_credit = n_delivered_kg * self.n_offset_credit
        soil_credit = (tons_delivered * 1000) * self.soil_carbon_gain  # tons to kg
        
        # PENALTIES
        transport_cost = distance_km * self.diesel_emission
        
        # Excess nitrogen penalty (if delivered more than needed)
        excess_n = max(0, n_delivered_kg - n_demand_kg)
        excess_penalty = excess_n * self.leaching_penalty
        
        net_credits = nitrogen_credit + soil_credit - transport_cost - excess_penalty
        
        breakdown = {
            'nitrogen_credit': nitrogen_credit,
            'soil_credit': soil_credit,
            'transport_cost': transport_cost,
            'excess_penalty': excess_penalty,
            'net_credits': net_credits
        }
        
        return net_credits, breakdown
    
    def record_delivery(self, tons_delivered, distance_km, n_demand_kg, n_delivered_kg):
        """Record a delivery and update totals."""
        net_credits, breakdown = self.calculate_delivery_score(
            tons_delivered, distance_km, n_demand_kg, n_delivered_kg
        )
        
        # Update totals
        self.nitrogen_credits += breakdown['nitrogen_credit']
        self.soil_carbon_credits += breakdown['soil_credit']
        self.transport_emissions += breakdown['transport_cost']
        self.excess_n_penalties += breakdown['excess_penalty']
        self.total_credits += (breakdown['nitrogen_credit'] + breakdown['soil_credit'])
        self.total_penalties += (breakdown['transport_cost'] + breakdown['excess_penalty'])
    
    def record_overflow(self, overflow_tons):
        """Record STP overflow penalty."""
        penalty = overflow_tons * self.overflow_penalty
        self.overflow_penalties += penalty
        self.total_penalties += penalty
    
    def get_net_score(self):
        """Get final net carbon credit score."""
        return self.total_credits - self.total_penalties
    
    def get_summary(self):
        """Get detailed scoring summary."""
        return {
            'total_credits': self.total_credits,
            'nitrogen_offset_credits': self.nitrogen_credits,
            'soil_carbon_credits': self.soil_carbon_credits,
            'total_penalties': self.total_penalties,
            'transport_emissions': self.transport_emissions,
            'overflow_penalties': self.overflow_penalties,
            'excess_n_penalties': self.excess_n_penalties,
            'net_score': self.get_net_score()
        }


# ============================================
# DECISION ENGINE
# ============================================

def get_7day_n_demand(farm_id, current_date, demand_df, days=14):
    """Get total nitrogen demand for next N days (for buffer trick)."""
    total_demand = 0.0
    for i in range(days):
        check_date = current_date + timedelta(days=i)
        if check_date in demand_df.index and farm_id in demand_df.columns:
            total_demand += demand_df.loc[check_date, farm_id]
    return total_demand


def score_and_rank_farms(stp_id, current_date, farms_df, distance_matrix, 
                         weather_df, demand_df, accountant, truck_capacity=10):
    """
    Score and rank all farms for a given STP.
    
    Returns: List of (farm_id, score, details) sorted by score (highest first)
    """
    scores = []
    n_per_ton = accountant.n_content
    
    for _, farm in farms_df.iterrows():
        farm_id = farm['farm_id']
        farm_zone = farm['zone']
        
        # FILTER 1: Rain-Lock Check
        if is_rain_locked(farm_zone, current_date, weather_df):
            continue
        
        # BUFFER TRICK: Check 14-day demand
        two_week_demand = get_7day_n_demand(farm_id, current_date, demand_df, days=14)
        
        # Calculate delivery amount (10 tons max)
        tons_to_deliver = truck_capacity
        n_to_deliver = tons_to_deliver * n_per_ton  # kg of nitrogen
        
        # Get distance
        distance = distance_matrix[(stp_id, farm_id)]
        
        # Calculate net score for this delivery
        # Use 2-week demand to reduce excess penalty
        net_score, _ = accountant.calculate_delivery_score(
            tons_to_deliver, distance, two_week_demand, n_to_deliver
        )
        
        # Accept any delivery with positive net score
        if net_score > 0:
            scores.append((farm_id, net_score, {
                'distance': distance,
                'week_demand': two_week_demand,
                'n_to_deliver': n_to_deliver,
                'tons': tons_to_deliver
            }))
    
    # Sort by score (highest first)
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


# ============================================
# MAIN SIMULATION LOOP
# ============================================

def run_simulation():
    """Run the complete 365-day simulation."""
    
    print("\n🚀 Starting 365-Day Simulation...")
    print("=" * 60)
    
    # Initialize
    tracker = STPStorageTracker(stps)
    accountant = CarbonCreditAccountant(config)
    
    # Track all deliveries for output
    deliveries = []
    
    # Simulation parameters
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2025-12-31')
    truck_capacity = config['logistics_constants']['truck_capacity_tons']
    safe_threshold = 70.0  # Keep tanks below 70% when possible
    
    # Track nitrogen delivered to each farm (to avoid over-application)
    farm_n_delivered = {farm_id: {} for farm_id in farms['farm_id']}
    
    current_date = start_date
    day_num = 0
    
    while current_date <= end_date:
        day_num += 1
        
        # === MORNING UPDATE: Add daily waste ===
        for stp_id in tracker.storage.keys():
            tracker.add_daily_waste(stp_id)
        
        # === CHECK FOR OVERFLOW ===
        for stp_id in tracker.storage.keys():
            if tracker.is_overflowing(stp_id):
                overflow = tracker.get_overflow_tons(stp_id)
                accountant.record_overflow(overflow)
                # Cap at max capacity
                tracker.storage[stp_id] = tracker.max_capacity[stp_id]
        
        # === DELIVERY PLANNING ===
        # Get STPs sorted by fullness
        stps_by_fullness = tracker.get_stps_by_fullness()
        
        # Process each STP (most full first)
        for stp_id, fullness_pct in stps_by_fullness:
            # Get available biosolid
            available = tracker.get_available_biosolid(stp_id)
            if available < truck_capacity:
                continue
            
            # Determine delivery urgency based on fullness
            if fullness_pct > 80:
                max_deliveries = 20  # CRITICAL - empty urgently
            elif fullness_pct > 50:
                max_deliveries = 15  # WARNING - increase deliveries
            else:
                max_deliveries = 10  # NORMAL operations
            
            # Score and rank farms
            ranked_farms = score_and_rank_farms(
                stp_id, current_date, farms, distance_matrix,
                weather, demand, accountant, truck_capacity
            )
            
            # Dispatch trucks to top-scoring farms
            deliveries_made = 0
            
            for farm_id, score, details in ranked_farms:
                if deliveries_made >= max_deliveries:
                    break
                
                # Check if we have enough biosolid
                if tracker.get_available_biosolid(stp_id) < truck_capacity:
                    break
                
                # Make the delivery
                tons = details['tons']
                n_delivered = details['n_to_deliver']
                week_demand = details['week_demand']
                distance = details['distance']
                
                # Record the delivery
                tracker.remove_delivery(stp_id, tons)
                accountant.record_delivery(tons, distance, week_demand, n_delivered)
                
                deliveries.append({
                    'date': current_date,
                    'stp_id': stp_id,
                    'farm_id': farm_id,
                    'tons_delivered': tons
                })
                
                deliveries_made += 1
        
        # Progress update every 30 days
        if day_num % 30 == 0 or day_num == 1:
            print(f"\n📅 Day {day_num} ({current_date.date()}):")
            for stp_id in sorted(tracker.storage.keys()):
                fullness = tracker.get_fullness_percent(stp_id)
                print(f"  {stp_id}: {fullness:5.1f}% full")
            score = accountant.get_net_score()
            print(f"  💰 Current Score: {score:,.0f} CO2 credits")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    print("\n" + "=" * 60)
    print("✅ SIMULATION COMPLETE!")
    print("=" * 60)
    
    return deliveries, tracker, accountant


# ============================================
# RUN AND EXPORT
# ============================================

if __name__ == "__main__":
    # Run simulation
    deliveries, final_tracker, final_accountant = run_simulation()
    
    # === PRINT RESULTS ===
    print("\n📊 FINAL RESULTS:")
    print("=" * 60)
    
    summary = final_accountant.get_summary()
    print(f"\n💰 CARBON CREDIT BREAKDOWN:")
    print(f"  Nitrogen Offset Credits:  +{summary['nitrogen_offset_credits']:>12,.0f}")
    print(f"  Soil Carbon Credits:      +{summary['soil_carbon_credits']:>12,.0f}")
    print(f"  ----------------------------------------")
    print(f"  Total Credits:            +{summary['total_credits']:>12,.0f}")
    print(f"\n💸 PENALTIES:")
    print(f"  Transport Emissions:      -{summary['transport_emissions']:>12,.0f}")
    print(f"  Overflow Penalties:       -{summary['overflow_penalties']:>12,.0f}")
    print(f"  Excess N Penalties:       -{summary['excess_n_penalties']:>12,.0f}")
    print(f"  ----------------------------------------")
    print(f"  Total Penalties:          -{summary['total_penalties']:>12,.0f}")
    print(f"\n🎯 NET CARBON CREDITS:      {summary['net_score']:>12,.0f}")
    print("=" * 60)
    
    print(f"\n📦 Total Deliveries Made: {len(deliveries)}")
    
    # === EXPORT SOLUTION ===
    print("\n💾 Exporting solution...")
    
    # Create output dataframe matching sample_submission format
    output = []
    
    for stp_id in stps['stp_id']:
        for farm_id in farms['farm_id']:
            current_date = pd.Timestamp('2025-01-01')
            end_date = pd.Timestamp('2025-12-31')
            
            while current_date <= end_date:
                # Check if there was a delivery on this date
                tons = 0.0
                for delivery in deliveries:
                    if (delivery['date'] == current_date and 
                        delivery['stp_id'] == stp_id and 
                        delivery['farm_id'] == farm_id):
                        tons = delivery['tons_delivered']
                        break
                
                output.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'stp_id': stp_id,
                    'farm_id': farm_id,
                    'tons_delivered': tons
                })
                
                current_date += timedelta(days=1)
    
    # Create DataFrame
    solution_df = pd.DataFrame(output)
    solution_df.insert(0, 'id', range(len(solution_df)))
    
    # Save to CSV
    os.makedirs('output', exist_ok=True)
    solution_df.to_csv('output/solution.csv', index=False)
    print(f"✅ Solution saved to: output/solution.csv")
    
    # Save summary metrics
    summary_json = {
        'simulation_date': datetime.now().isoformat(),
        'total_deliveries': len(deliveries),
        'carbon_credits': summary
    }
    
    with open('output/summary_metrics.json', 'w') as f:
        json.dump(summary_json, f, indent=2)
    print(f"✅ Summary metrics saved to: output/summary_metrics.json")
    
    print("\n🎉 ALL DONE! Ready for submission!")
