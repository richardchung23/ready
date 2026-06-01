# Ready LEO Satellite Coverage Risk Analysis
Agent geospatial pipeline that finds locations that may be obstructed for satellite
broadband. Shows Starlink coverage for ~4.6M locations.

# Architecture
Check out docs/ARCHITECTURE.md

Boundaries:
- The supervisor agent is the one that orchestrates the whole thing. It calls the
data and analysis tools and then translates it back to the user in plain English.

- Data sourcing layer is all database I/O. No analysis logic.

- Analysis layer is all math, no direct database access

# Risk Tiers

| Tier | Obstruction Angle | English |
| --- | --- | --- |
| A | < 15 deg | Clear line of sight, low risk |
| B | 15 - 20 deg | Marginal clearance, medium risk |
| C | > 20 deg | Obstructions in the way, high risk |

The 20 deg threshold came from PCMag reporting on Starlink's minimum elevation angles.


# Installations/Setup
```bash
docker-compose up -d
pip install -r requirements.txt
cp .env.example .env
python src/init_db.py
python src/process_csv.py
python src/analysis.py
python src/insights.py
python src/supervisor.py
```

# Decision Log

- Chose a "centralized" based approach as prompt mentions to have clear 
boundaries and is also easier to parallelize workers at scale. A single agent
handling everything could stall: if API call fails, then you would lose everything.
I would not revisit this.

- Used PostGIS for its spatial indexing, and it also allowed for geometry ops.
May revisit if portability becomes an issue.

- Preloaded APIs over web search. This was to make it deterministic and has no
rate limit risk. I would not revisit this.

- Batch SQL updates over per row calls. This decreases token cost drastically.
I would not revisit this.

- Bulk inserts to make it faster. I would not revisit this.

- Decided to use NLCD TCC raster data directly in PostGIS via spatial joins 
instead of per-row API calls to external services. This avoids 4.6M individual 
database round-trips per batch, keeping the pipeline faster.