# Computing in the Catskills

What's wrong with a little math in the woods?

Question: What's the least amount of hiking you have to do to hike all [33 of the Catskills High Peaks][peaks]?

## Gallery of solutions

### Shortest hiking distance

This [set of 11 hikes][geojson-95.2] weighs in at 95.2 miles of total hiking:

[![A set of 11 through hikes at 95.2 miles](/gallery/11-through-hikes-95.2-miles.png)][geojson-95.2]

Out-and-backs:

1. Windham High Peak from Peck Rd (5.94 miles)
1. Kaaterskill High Peak from Cortina Ln (6.51 miles)
1. Halcott Mountain from SR 42 (3.13 miles)
1. Panther Mountain from Giant Ledge Trailhead (6.04 miles)
1. Balsam Lake Mountain via Dry Brook Ridge (3.27 miles)
1. Bearpen & Vly from County Road 3 (6.46 miles)

Through hikes:

7. Blackhead Range from Barnum Rd to Big Hollow Rd (3 peaks / 6.98 miles)
7. Devil's Path East from Prediger Rd to Mink Hollow Rd (4 peaks / 8.32)
7. FirBBiE Loop from Burnham Hollow to McKinley Hollow (4 peaks / 12.23 miles)
7. The Nine from Oliverea Rd to Peekamoose Rd (9 peaks / 16.47 miles)
7. Super Spruceton from Shaft Rd to Spruceton Rd (6 peaks / 19.85 miles)

### Shortest hike using only loop / out-and-back hikes

Best solution is 12 hikes / 104.89 miles.

TODO: add image and explain this one.

## Quickstart

    poetry install
    # Generate possible hikes
    poetry run python loops.py
    # Find the minimal set of hikes
    poetry run python subset_cover.py

To regenerate data, see below.

## Notes on the problem

Data comes mostly from OpenStreetMap with a few tweaks:

- High peaks have been shifted to be on paths / herd paths.
- I've added a few strategic bushwhacks using tracks from my [personal experience][blog].

The result of all this (including parking lots, high peaks, trailheads, trail junctions and hikes between all of them) is in `network.geojson`.

Finding the shortest set of hikes maps onto a few famous problems in Computer Science.

### Traveling Salesman Problem

The [Traveling Salesman Problem][tsp] asks what the most efficient order is to visit a set of N cities, ending back where you started. To map the Catskills hiking problem onto the TSP:

- Add an artificial node to the graph and connect all parking lots to it with a distance of zero. This simulates free driving between trailheads (since we only care about hiking distance).
- Use all-pairs shortest paths to construct a subgraph consisting only of the 33 high peaks. The distances between them will reflect segments of longer hikes and they may go between two parking lots (if the fastest way from peak A to peak B is to hike to a parking lot and drive to another trailhead).
- Run a TSP solver on this subgraph to get an optimal sequence of peaks.
- Map this solution back onto the larger graph. Trips through the artificial node split the solution into multiple separate hikes.

To find the 12 hike / 95.4 mile solution I used Google's [OR-Tools] TSP solver.

### Set Cover Problem

The [Set Cover Problem][scp] is another famous [NP-Complete] problem in Computer Science. It asks you to find the smallest collection of subsets whose union is the complete set.

The hiking problem maps onto the _Weighted_ Set Cover problem. In our case:

- The "universe" is the 33 high peaks.
- The subsets are possible hikes (the subset being the subset of high peaks that they visit).
- The weight is the mileage for each hike.

To answer the hiking question using a Set Cover solver, we first need to generate the set of all possible hikes in the Catskills. With some clever filtering and optimization, this doesn't wind up being too bad. (TODO: explain this)

Then we can run a set cover solver to get our set of hikes directly. This [old Python repo][SetCoverPy] works great. It's very fast compared to the TSP solver (<1s vs. minutes to hours) and finds equally good solutions.

This approach is nice because it gives us more flexibility to answer variations of the problem. For example, we can only allow loop hikes or set a max distance on any one hike by filtering the set of hikes that we give the solver.

## Data ingestion flow

Pull down data from OSM using the Overpass API:

    for query in queries/*.txt; poetry run python run_overpass_query.py $query

Next, augment the trails with some key bushwhacks that aren't in OSM:

    poetry run python augment_trails.py
    # produces data/additional-trails.json (just the extra bushwhacks) and
    #          data/combined-trails.json (all the trails)

This will create fake OSM node and way IDs. These are all negative numbers to distinguish them from real IDs.

The file `data/peaks-3500.json` is a hand-edited version of `data/peaks.json`. The nodes for peaks in OSM tend not to be on trails and in some cases (Vly) they are actually quite far off. The next step is to make a version of the peaks that are connected to the trail graph:

    poetry run python shift_peaks.py
    # produces data/peaks-connected.json

Next we produce the preliminary `network.geojson` file, which connects trailheads to peaks via trails:

    poetry run python extract_network.py
    # produces data/network.geojson

This script also removes lots of trails that don't connect to a high peak. A "trailhead" is a node where the road network and the trail network meet. It might be on private land, or it might be in a residential area where you can't park. For that reason it's better to start and end hikes with parking lots:

    poetry run python parking_lots.py
    # produces data/network+parking.geojson

This is the key file that `loops.py`, `tsp.py` and `subset_cover.py` work off of.

[peaks]: http://catskill-3500-club.org/peaks.php
[geojson-95.2]: https://geojson.io/#id=github:danvk/computing-in-the-catskills/blob/main/gallery/11-through-hikes-95.2-miles.geojson
[blog]: https://www.danvk.org/catskills/
[tsp]: https://en.wikipedia.org/wiki/Travelling_salesman_problem
[or-tools]: https://developers.google.com/optimization/routing/tsp
[scp]: https://en.wikipedia.org/wiki/Set_cover_problem
[np-complete]: https://en.wikipedia.org/wiki/NP-completeness
[SetCoverPy]: https://github.com/guangtunbenzhu/SetCoverPy
