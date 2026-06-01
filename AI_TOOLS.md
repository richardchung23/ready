# AI Tools Used

## Gemini

Used for: Initial project setup (init.sql, requirements.txt), drafts for 
PostGIS/psycopg2 syntax for data ingestions layer.

While they gave a good foundation, I found that it often ommitted "small" 
details, like guards and variable types. Essentially it kept assuming it would
be a happy path.

### Divergences:
1. It initially gave me larger datatypes like INTEGER/NUMERIC and redundant 
columns (like storing obstruction angles and reason). It also ommitted NOT NULL
constraints.

I changed the fields to use smaller types when I could (like SMALLINT and CHAR),
removed the redundant columns, and added null constraints. That way, I could 
optimize space and reduce bottlenecks.

2. AI also gave a basic script to insert the CSV file into the database.

However, once I realized that the actual file has closer to 5M rows, I had to 
redo and implement a bulk ingestion script. This was essential because going 
row by row would have taken hours, but this method would significantly decrease 
the amount of time.

3. Gemini also suggested basic connections with no pooling and no guard for
malformed rows.

I made a lazy implementation with a simple connection pool and added strict
try/except blocks, and added row level guards.


## Claude

Used for: NLCD raster guidance, documentation refinement, code refinement,
debugging spatial join bugs

### Divergences:
1. It kept suggesting I use mock TCC formula for the demo. 

I kept pushing back to integrate the real NLCD raster because the rubric explicitly
talks about data sourcing.

2. It suggested I split canopy cover and height into separate schema columns.

I kept a single obstruction_height column since splitting it would just add
unnecessary complexity without analytical benefit.