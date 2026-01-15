# Kerala Carbon Challenge - Project Documentation

**Date Started:** January 15, 2026  
**Team Member:** Solo Developer (with Remote Collaborator)  
**Event:** Hackathon Challenge

---

## 📖 What is This Hackathon About?

### The Challenge: Eco-Friendly Waste Management

This hackathon simulates a **real-world environmental optimization problem** in Kerala, India. The goal is to manage sewage sludge (biosolids) from 4 Sewage Treatment Plants (STPs) and deliver it to 250 farms over 365 days.

### Why This Matters

Sewage sludge contains **nitrogen**, which is like vitamins for plants. Instead of letting it pile up and pollute the environment, we can:
- **Recycle it** as fertilizer for farms
- **Earn carbon credits** by offsetting synthetic fertilizer production
- **Sequester carbon** in the soil
- **Reduce environmental damage** from overflow and pollution

### The Game Mechanics

Think of it as **eco-friendly Tetris** where you manage a recycling fleet:

**The Assets:**
- 4 STPs producing waste daily (10-30 tons/day each)
- 250 farms needing nitrogen fertilizer
- Trucks with 10-ton capacity
- Weather data for the entire year 2025

**The Goal:**
Maximize carbon credits by delivering biosolids to farms efficiently while following strict environmental rules.

---

## 🎯 The Three Critical Rules

### Rule 1: Don't Let Tanks Overflow ❌
- Each STP has limited storage (200-500 tons max)
- New waste arrives every day
- **Penalty:** -1,000 CO2 credits per ton that overflows!
- **Strategy:** Monitor tank levels and prioritize deliveries from full tanks

### Rule 2: Rain-Lock Rule 🌧️
- Cannot deliver to a farm if >30mm of rain will fall in the next 5 days
- Rain washes nitrogen into rivers, causing pollution
- **Penalty:** Delivery is wasted, credits lost
- **Strategy:** Check weather forecast before every delivery

### Rule 3: Don't Over-Apply Nitrogen ⚠️
- Each farm has a specific daily nitrogen requirement
- Giving too much causes leaching into groundwater
- **Penalty:** -10 CO2 credits per kg of excess nitrogen
- **Strategy:** Match delivery amounts to farm needs

---

## ⚖️ How Scoring Works

### You GAIN Points For:

1. **Nitrogen Offset Credits**
   - +5 CO2 credits per kg of nitrogen delivered
   - Biosolids replace synthetic fertilizer (which has high carbon footprint)

2. **Soil Carbon Sequestration**
   - +0.2 CO2 credits per kg of biosolids applied
   - Organic matter in biosolids improves soil health

### You LOSE Points For:

1. **Transport Emissions**
   - -0.9 CO2 credits per km driven
   - Diesel trucks emit carbon

2. **STP Overflow**
   - -1,000 CO2 credits per ton that overflows
   - Biggest penalty in the game!

3. **Nitrogen Over-Application**
   - -10 CO2 credits per kg of excess nitrogen
   - Environmental damage from leaching

4. **Rain-Lock Violations**
   - Wasted delivery + pollution penalty

---

## 📊 The Data We're Working With

### Input Files (Provided by Hackathon):

1. **config.json** - Constants and thresholds
   - Truck capacity: 10 tons
   - Earth radius: 6,371 km (for distance calculations)
   - Nitrogen content: 25 kg/ton of biosolids
   - All penalty and reward values

2. **stp_registry.csv** - 4 Treatment Plants
   - Daily waste production rate
   - Maximum storage capacity
   - GPS coordinates

3. **farm_locations.csv** - 250 Farms
   - Geographic zone (Kuttanad, Palakkad, Highlands, Coastal)
   - Farm area in hectares
   - GPS coordinates

4. **daily_weather_2025.csv** - Weather Forecast
   - Daily rainfall for each of 4 zones
   - Entire year 2025 (365 days)

5. **daily_n_demand.csv** - Nitrogen Requirements
   - How much nitrogen each farm needs per day
   - Based on crop growth stages

6. **sample_submission.csv** - Expected Output Format
   - Shows how to format our solution

---

## 🛠️ What I Built Today (January 15, 2026)

### 1. ✅ Rain-Lock Safety System

**What it does:**  
Checks if it's safe to deliver to a farm based on upcoming rainfall.

**Function Created:** `is_rain_locked(farm_zone, delivery_date, weather_df)`

**How it works:**
- Looks at the next 5 days of weather
- Sums up total rainfall for that zone
- Returns `True` (blocked) if rain > 30mm, `False` (safe) otherwise

**Test Results:**
```
Jan 1, 2025 Deliveries:
- Kuttanad:   ✅ SAFE
- Palakkad:   ✅ SAFE
- Highlands:  ✅ SAFE
- Coastal:    ⛔ BLOCKED (36mm rain on Jan 4th)
```

---

### 2. ✅ Distance Matrix Pre-Calculator

**What it does:**  
Pre-calculates the distance between every STP and every farm using the Haversine formula.

**Files Created:**
- `haversine_distance()` function in main.py
- `build_distance_matrix()` function in main.py
- `output/distance_matrix.csv` - 1,000 pre-calculated routes

**Why this matters:**  
Instead of calculating the same distance 365 times during simulation, we calculate it ONCE and look it up instantly.

**Sample Result:**
```
STP_TVM → F_1000 = 133.08 km
STP_TVM → F_1008 = 52.03 km (much closer!)
```

**Performance:**  
1,000 routes calculated in < 1 second.

---

### 3. ✅ STP Storage Tracker

**What it does:**  
Monitors how full each storage tank is to prevent overflow disasters.

**Class Created:** `STPStorageTracker`

**Key Features:**
- Tracks current storage level for all 4 STPs
- Simulates daily waste accumulation
- Records deliveries (removes waste from storage)
- Identifies which tank is most critical
- Visual status dashboard with color coding

**Example Output:**
```
🛢️  STP STORAGE STATUS:
STP_GVR    [██████████░░░░░░░░░░]  50.0% (100/200 tons) 🟢 OK
STP_KCH    [██████████░░░░░░░░░░]  50.0% (150/300 tons) 🟢 OK
STP_KKD    [██████████░░░░░░░░░░]  50.0% (200/400 tons) 🟢 OK
STP_TVM    [████████████░░░░░░░░]  60.0% (300/500 tons) 🟡 WARNING

🎯 Most Critical Tank: STP_TVM
```

**Methods Available:**
- `simulate_day()` - Add daily waste
- `remove_delivery(stp_id, tons)` - Record truck delivery
- `is_overflowing(stp_id)` - Check for overflow
- `get_fullness_percent(stp_id)` - Get tank capacity %
- `get_most_full_stp()` - Find priority target
- `get_status_report()` - Print visual dashboard

---

## 📁 Project Structure

```
kerala-carbon-challenge/
├── data/                          # Input data (provided)
│   ├── config.json                # Constants & thresholds
│   ├── daily_weather_2025.csv     # 365 days of rainfall
│   ├── farm_locations.csv         # 250 farms
│   ├── stp_registry.csv           # 4 STPs
│   ├── daily_n_demand.csv         # Farm nitrogen needs
│   └── sample_submission.csv      # Output format template
│
├── output/                        # Generated files
│   └── distance_matrix.csv        # ✅ Pre-calculated distances
│
├── src/                           # Source code
│   └── main.py                    # Complete utility toolkit
│
├── .venv/                         # Python virtual environment
│
├── DOCUMENTATION.md               # This file
└── README_UTILITIES.md            # Technical reference guide
```

---

## 🎮 Current Status

### ✅ Completed Today:
- [x] Environment setup (Python, pandas)
- [x] Data loading and validation
- [x] Rain-Lock safety checker
- [x] Distance matrix calculator (1,000 routes)
- [x] STP storage tracking system
- [x] Visual monitoring dashboard
- [x] Documentation

### 🔄 In Progress:
- [ ] Optimization algorithm (delivery scheduler)
- [ ] 365-day simulation loop
- [ ] Carbon credit scoring system
- [ ] Solution export to submission format

### 📅 Next Steps (Tomorrow):
1. Build the decision engine (which trucks go where)
2. Implement carbon credit calculation
3. Run full 365-day simulation
4. Optimize for maximum carbon credits
5. Generate final submission file

---

## 🧠 Strategy for Tomorrow

### The Algorithm Approach:

```
FOR each day (1 to 365):
    1. Add today's waste to all STP tanks
    
    2. Check for overflow risk:
       - Find which STP is most full
       - Priority: Empty critical tanks first
    
    3. For each potential delivery:
       a. Check rain-lock (is farm zone safe?)
       b. Check distance (closer = less emissions)
       c. Check nitrogen demand (match farm needs)
       d. Calculate net carbon credits
    
    4. Select best deliveries:
       - Maximize: Carbon credits
       - Minimize: Transport emissions
       - Constraint: 10 tons per truck
    
    5. Update storage tracker
    
    6. Record deliveries
END
```

### Key Insights:

**Distance Matters:**  
A 100km delivery costs 90 CO2 in transport emissions. The nitrogen credits must exceed this to be profitable.

**Overflow is Disaster:**  
One overflow (1,000 CO2 penalty) can wipe out 200 successful deliveries. Tank management is critical!

**Weather is Everything:**  
A rain-locked delivery is a complete waste. Always check forecast!

---

## 🏆 Success Metrics

To win this hackathon, our solution needs to:

1. **Zero overflows** - Perfect STP management
2. **Zero rain violations** - Smart weather awareness
3. **Minimize transport** - Deliver to nearby farms when possible
4. **Match demand** - No nitrogen over-application
5. **Maximize coverage** - Use all 365 days efficiently

**Target:** Positive carbon credits (net benefit to environment)

---

## 📚 Resources & References

- **Haversine Formula:** Used for calculating distances on Earth's curved surface
- **Biosolids Science:** [Video Explanation](https://www.youtube.com/watch?v=KXm7JouReRM)
- **Carbon Credits:** Trading system for greenhouse gas reductions
- **Nitrogen Cycle:** How excess nitrogen causes environmental damage

---

## 🤝 Collaboration Notes

Working with a remote team member. Division of tasks:

**My Role (Local):**
- Core algorithm development
- Tank management system
- Simulation engine
- Code optimization

**Partner's Role (Remote):**
- Weather data analysis
- Environmental impact report
- Optimization testing
- Final presentation slides

**Communication:** Shared folder for code synchronization

---

## 💡 Lessons Learned Today

1. **Pre-calculation saves time:** Distance matrix eliminates 364,000+ redundant calculations
2. **Visual feedback helps:** Tank status bars make debugging much easier
3. **Modular design:** Separate utilities (rain check, distance, storage) can be tested independently
4. **Configuration matters:** Never hardcode - everything from config.json
5. **Real-world impact:** This isn't just a game - biosolid recycling is a real environmental solution

---

## 🚀 Ready for Tomorrow!

All foundation utilities are complete and tested. Tomorrow we focus on the optimization brain - the algorithm that makes smart decisions to maximize our carbon credit score.

**Current state:** Infrastructure ready ✅  
**Next milestone:** Working 365-day simulator  
**Final goal:** Optimal delivery schedule for maximum environmental benefit

---

*Last Updated: January 15, 2026*
