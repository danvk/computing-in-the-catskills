"""Let's make sure every parking lot has a name."""

import json


if __name__ == '__main__':
    extra_names = json.load(open('data/extra-lot-names.json'))
    id_to_name = {id: name for id, name in extra_names}
    fs = json.load(open('data/network+parking.geojson'))['features']
    lots = [f for f in fs if f['properties'].get('type') == 'parking-lot']
    print(f'Found {len(lots)} parking lots.')

    num_named, num_unnamed = 0, 0
    for lot in lots:
        p = lot['properties']
        node = p['id']
        # print(node_link(p["id"], p.get("name")))
        name = p.get('name') or id_to_name.get(node)
        if name:
            num_named += 1
        else:
            num_unnamed += 1

        print(
            node,
            '\t',
            p['url'],
            '\t',
            name,
        )

    print(f'  Named: {num_named}')
    print(f'Unnamed: {num_unnamed}')
