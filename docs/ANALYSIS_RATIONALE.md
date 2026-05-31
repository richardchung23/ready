1. Installation Guide to Technicality
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


2. Why LOS
Tree Canopy Cover (TCC) percentage tells you how much of the ground is covered
by a canopy, but could not be too accurate on a dish's connection. An example 
scenario is a low TCC percentage (like 20%), but it is uphill. Then, the trees
uphill of the dish would block the dish significantly more. Thus, I used LOS,
which includes the height of the obstruction and LOS.

3. Clarifying Risk Tiers
I defined a location to be at risk if the nearest obstacle creates an angle
greater than 15 degrees (will clarify between 15 and 20 degrees below).

We defined three tiers:
- A (< 15 degrees). Clear sky and service is very likely to work well
- B (15-20 degrees). Moderate risk. Service may work but could cut off. An actual visit may be worth before installation.
- C (> 20 degrees). Obstruction. Nearby objects obstruct dish's view.


Main thing to know is that C tier means something is blocking dish's view, A tier
has no nearby objects obstructing the view, and B tier is a bit gray; it could 
or could not work.

4. Data Sources
After convsering with Gemini, I decided to only directly call USGS for ground
elevation in order to calculate LOS. When USE_LIVE_API is true, the pipeline queries
the USGS API for each location's elevation in meters. This is free and is simple.

We decided to omit TCC data and canopy height for the demo to keep it fast. Right
now, TCC is generated using a deterministic formula based on latitude. 

In production, this would be replaced by a query to National Land Cover Database
(NLCD) raster from MRLC. In order to query it, you would have to download the 
entire raster file, which is around 2GB for US, load it into PostGIS, and query it.

Canopy height would come from GLAD Global Canopy Height Model or Microsoft's 
Canopy Height Model, also queried locally via PostGIS.

Note TCC and canopy height are different as TCC only tells you if there are trees
nearby.

5. Limitations
- We assume the dish is always 2 meters off the ground. However, they can be
mounted at different heights (ground, roof, or on a tall pole). A higher mount
would be more clear of obstructions but more difficult to install. Our assumption
is conservative but could be wrong on many installations.

- We only look at nearest obstacle. In reality, it needs clear view in multiple
directions. A complete implementation would check full 360 degree sky.

- We cannot see what is on the roof. So, things like chimneys, HVAC unit, skylights,
etc, can all cause interruptions. Only a physical visit can confirm these things.

- Federal elevation API is unreliable at scale. Even during testing, the USGS API
timed out on many requests, enough to harm the data produced. This is a limitation
of querying a publicly available API at volume.

- Changes are not modeled. Trees can shed leaves, there could be deforestation,
construction, etc. So a location that is B Tier in summer can be A Tier in January.

- This is not a final answer. This is to just state broadband officers prioritize
which locations to physically visit.

