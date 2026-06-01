# 1. Installation Guide to Technicality
From what I gathered on the Starlink Installation Guide, the dish needs a completely
clear view of the sky to maintain a connection, even instructing users to elevate
the dish if there were obstructions. It identified things like trees, poles, 
and buildings that could interrupt the service. The guide also stated that it
would automatically tilt based on the hemisphere it is in for the optimal connection.

This simplifies to the question on if any nearby objects break the dish's line
of sight to the sky at low elevation angles. I used a line of sight (LOS) 
calculation with a 20 degree minimum elevation angle, which I gathered from this
article: 
https://www.pcmag.com/news/starlink-dishes-cleared-to-receive-signals-at-lower-elevation-angles.
The installation guide did not mention a numerical value, which is why I searched it up.

Thus, for each location, we would compute the obstruction angle, like as if it was
a right triangle, and compare it with the threshold. If the angle was above,
then it would be considered to be at risk.


# 2. Why LOS
Tree Canopy Cover (TCC) percentage tells you how much of the ground is covered
by a canopy, but could not be too accurate on a dish's connection. An example 
scenario is a low TCC percentage (like 20%), but it is uphill. Then, the trees
uphill of the dish would block the dish significantly more. Thus, I used LOS,
which incorporates both the height of the obstruction and its distance from the 
dish to compute a precise angular measurement.

## Why not other approaches?
We cannot use the Starlink app as it requires physical access with a device. It
cannot be applied remotely across 4.6M locations. Our approach approximates the 
same assessment using publicly available data.

We also did not use building footprint datasets for a couple of reasons. First,
I felt that the target population is mostly rural, where more nature would block
the dish. Second, integrating building heights requires either a separate raster 
join or a nearest-neighbor vector query against polygon footprints, adding 
complexity and straining on resources. Also, building heights are not included 
in the datasets and would actually require another source.


# 3. Clarifying Risk Tiers
I defined a location to be at risk if the nearest obstacle creates an angle
greater than 15 degrees.

We defined three tiers:
- A (< 15 degrees). Clear sky and service is very likely to work well
- B (15-20 degrees). Moderate risk. Service may work but could cut off. An actual visit may be worth before installation.
- C (> 20 degrees). Obstruction. Nearby objects obstruct dish's view.


Main thing to know is that C tier means something is blocking dish's view, A tier
has no nearby objects obstructing the view, and B tier is a bit gray; it could 
or could not work.


# 4. Data Sources
## Dataset to Obstruction Factor Mapping

| Dataset | Source | Obstruction Factor |
|---------|--------|--------------------|
| USGS 3DEP Elevation | USGS National Map API | Terrain height — needed to compute relative elevation difference between dish and nearby obstacles |
| NLCD Tree Canopy Cover | MRLC NLCD 2023 | Vegetation presence — guide identifies trees and foliage as a primary source of signal interruption |

The install guide does not quantify obstruction angles numerically. The 20° 
threshold used in this analysis is sourced from Starlink's FCC licensing 
documentation, confirmed by PCMag's coverage of the ruling. The guide's physical 
description of required sky visibility translates directly to this geometric threshold.

I decided to only directly call USGS for ground elevation in order to calculate 
LOS. When USE_LIVE_API is true, the pipeline queries the USGS API for each 
location's elevation in meters. This is free and is simple.

For Tree Canopy Cover (TCC), rather than calling a remote API, I downloaded the
publicly available National Land Cover Database (NLCD) raster from MRLC and loaded
it into PostGIS. During batch analysis, TCC values are extracted via a single
spatial join per batch rather than per row lookups. This avoids 4.6M individual
database round-trips per batch and keeps Python layer lightweight.

We decided to omit canopy height data for the demo. It was omitted because no 
point-query REST API exists for it. 

In production, canopy height would come from GLAD Global Canopy Height Model or Microsoft's 
Canopy Height Model, load it into PostGIS, and queried locally via PostGIS, similar
to how TCC is handled.

Note TCC and canopy height are different as TCC only tells you if there are trees
nearby.

## Data Quality Issues Found

The locations CSV was compiled from multiple provider submissions over several 
filing periods, which introduced several quality concerns:

Duplicate locations: Multiple providers may have committed to serve the same 
location, resulting in duplicate location_ids across submissions. Handled via 
`ON CONFLICT (location_id) DO NOTHING` in the ingestion query — only the first 
occurrence is retained.

Malformed rows: Some rows contained non-numeric latitude/longitude values or 
missing required fields. Handled via per-row try/except guards in process_csv.py 
that skip and log malformed rows without crashing the pipeline.

Missing geoid_cb: The Census Block GEOID column did not seem to be 
missing in the dataset, but is treated as optional defensively — 
`row.get('geoid_cb')` defaults to None rather than raising a KeyError in case 
it is absent in future provider submissions.

No coordinate validation: Latitude and longitude values are cast to float but 
not validated against realistic US bounds. A production system would reject 
coordinates outside the continental US bounding box.

# 5. Limitations
- We assume the dish is always 2 meters off the ground. However, they can be
mounted at different heights (ground, roof, or on a tall pole). A higher mount
would be more clear of obstructions but more difficult to install. Our assumption
is conservative but could be wrong on many installations. This cannot be determined remotely.

- We also assume the nearest obstacle is 15 meters away. This is a 
conservative default representing a typical residential setback. In reality, 
an obstacle could be 5 meters away or 50 meters away. Production would require a 
nearest-neighbor spatial query against a tree canopy or building footprint 
dataset to get the real distance.

- We only look at nearest obstacle. In reality, it needs clear view in multiple
directions. A complete implementation would check full 360 degree sky.

- When running in batch mode without live API, elevation defaults to 200 meters for all
locations. So, locations in mountainous terrain versus flatlands will have different
possible obstructions that this placeholder cannot capture.

- We cannot see what is on the roof. So, things like chimneys, HVAC unit, skylights,
etc, can all cause interruptions. Only a physical visit can confirm these things.
This cannot be determined remotely.

- Federal elevation API is unreliable at scale. Even during testing, the USGS API
timed out on many requests, enough to harm the data produced. This is a limitation
of querying a publicly available API at volume.

- Changes are not modeled. Trees can shed leaves, there could be deforestation,
construction, etc. So a location that is B Tier in summer can be A Tier in January.

- This is not a final answer. This is to just state broadband officers prioritize
which locations to physically visit.

