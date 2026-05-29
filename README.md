# ready
Ready.net challenge

```bash
pip install -r requirements.txt
```

# Notes for starlink

Basically any object that blocks the line of sight between the satellite and 
dish (things like buildings, poles, and trees). 

It requires a completely clear view. If the dish is not the tallest object in 
its immediate surroundings, then there are chances of interruption.

Publicly available datasets are TCC, USGS, 

I cannot model relatively small things, like chimneys, poles, or thin trees.
There are also just modern changes, like construction, deforestation/destruction,
seasonal changes, etc.


# Design Choices

Once the data was shared to me, I realized it was actually way more than 1M rows.
So, I had to 