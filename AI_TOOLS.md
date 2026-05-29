## AI Tools Used

## Gemini

Used for: Initial project setup (init.sql, requirements.txt)

Divergences:
- It initially gave me larger datatypes like INTEGER/NUMERIC, but I shortened it
with SMALLINT/CHAR/REAL when I could to reduce disk space
- It also forgot about NOT NULL constraints, but I added them because they are
essential to the correctness of the pipeline
- It added redundant columns like is_served and reason, but I removed them b/c
it would waste storage at scale and can be derived at query

