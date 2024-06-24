#!/usr/bin/env python
import json
import sys

import rasterio
import numpy as np

from formatting import get_coordinates


class Elevator:
    def __init__(self, dem_file: str):
        self.dem = rasterio.open(dem_file)
        self.bounds = self.dem.bounds
        self.inv = ~self.dem.transform
        self.dem_data = self.dem.read(1)

    def meters_one(self, lnglat: tuple[float, float]) -> float:
        xy = self.inv * lnglat
        ele_m = subsample_image(np.asarray([xy]), self.dem_data)
        return ele_m[0][0]

    def meters(self, lnglats: list[tuple[float, float]]) -> list[float]:
        """Determine meters above sea level for a list of points."""
        lnglats_mat = np.asarray(lnglats)
        xs, ys = self.inv * lnglats_mat.T
        xys = np.asarray((xs, ys)).T
        eles = subsample_image(xys, self.dem_data)
        return eles[:, 0].tolist()


# https://stackoverflow.com/a/70509540/388951
def subsample_image(coords, img):
    """
    Given a list of floating point coordinates (Nx2) in the image,
    return the pixel value at each location using bilinear interpolation.
    """
    if len(img.shape) == 2:
        img = np.expand_dims(img, 2)
    xs, ys = coords[:, 0], coords[:, 1]
    pxs = np.floor(xs).astype(int)
    pys = np.floor(ys).astype(int)
    dxs = xs - pxs
    dys = ys - pys
    wxs, wys = 1.0 - dxs, 1.0 - dys

    weights = np.multiply(img[pys, pxs, :].T, wxs * wys).T
    weights += np.multiply(img[pys, pxs + 1, :].T, dxs * wys).T
    weights += np.multiply(img[pys + 1, pxs, :].T, wxs * dys).T
    weights += np.multiply(img[pys + 1, pxs + 1, :].T, dxs * dys).T
    return weights


def add_elevation_to_geojson(geojson, ev):
    for f in geojson['features']:
        geom = f['geometry']
        props = f['properties']
        if geom['type'] == 'Point':
            ele = ev.meters_one(geom['coordinates'])
            props['ele'] = ele
        else:
            coords = get_coordinates(geom)
            eles = ev.meters(coords)
            ele_gain_m = sum(max(0, b - a) for a, b in zip(eles[:-1], eles[1:]))
            ele_loss_m = sum(max(0, a - b) for a, b in zip(eles[:-1], eles[1:]))
            props['ele_gain'] = ele_gain_m
            props['ele_loss'] = ele_loss_m


if __name__ == '__main__':
    input_file, dem_file = sys.argv[1:]
    ev = Elevator(dem_file)
    data = json.load(open(input_file))
    assert data.get('type') == 'FeatureCollection'
    add_elevation_to_geojson(data, ev)
    json.dump(data, sys.stdout)
