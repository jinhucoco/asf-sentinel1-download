#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge NASADEM/SRTM hgt tiles into one ENVI-format DEM (.dat + .hdr).

SARscape DEM pre-processing step 1 (see run_dem.bat):
  hgt x N  --merge-->  <name>.dat (ENVI float32, WGS84 Geographic)
then ImportEnviOriginal (Geoidal DEM / EGM96) then ToolsGeoid (SUBTRACT).

Usage:
  python merge_hgt_dem.py --input n38e102.hgt n38e103.hgt --output minqin.dat
  # or:
  python merge_hgt_dem.py --input "dir/*.hgt" --output minqin.dat

Tiles are placed by their (lat, lon) corner: each 1x1 deg tile keeps its
geographic position; tiles are merged into one raster. hgt is big-endian
int16 (3601x3601), output is little-endian float32 with an ENVI .hdr.
"""
import argparse
import glob
import os
import struct
import sys

HGT_N = 3601  # rows/cols per 1-deg tile
PIX = 1.0 / 3600.0  # 30 m ~ 1/3600 deg


def parse_hgt(path):
    """Return (lat_max, lon_min, values) for one hgt tile."""
    base = os.path.basename(path)
    # n38e102.hgt -> lat start 38N, lon start 102E
    lat_s = base[1:3]
    lon_s = base[3:6]
    try:
        lat_max = float(lat_s)  # tile covers [lat, lat+1]
        lon_min = float(lon_s)
    except ValueError:
        sys.exit(f"bad hgt name (expect n38e102.hgt): {path}")
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) != HGT_N * HGT_N * 2:
        sys.exit(f"unexpected size for {path}: {len(raw)} bytes")
    vals = struct.unpack(">%dh" % (HGT_N * HGT_N), raw)
    return lat_max, lon_min, vals


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", nargs="+", required=True, help="hgt files or glob")
    ap.add_argument("--output", required=True, help="output .dat (ENVI)")
    args = ap.parse_args()

    files = []
    for p in args.input:
        if any(ch in p for ch in "*?"):
            files.extend(sorted(glob.glob(p)))
        else:
            files.append(p)
    files = [os.path.abspath(f) for f in files if f.lower().endswith(".hgt")]
    if not files:
        sys.exit("no .hgt input files")

    # Place tiles on a global grid keyed by (lat_index, lon_index)
    grid = {}
    lat_idx = set()
    lon_idx = set()
    for f in files:
        lat_max, lon_min, vals = parse_hgt(f)
        li = int(round(lat_max))  # row key: tile covering [lat, lat+1]
        oi = int(round(lon_min))
        if (li, oi) in grid:
            sys.exit(f"duplicate tile: {f}")
        grid[(li, oi)] = (f, vals)
        lat_idx.add(li)
        lon_idx.add(oi)

    lat_idx = sorted(lat_idx, reverse=True)  # north first
    lon_idx = sorted(lon_idx)
    n_rows = len(lat_idx) * HGT_N
    n_cols = len(lon_idx) * HGT_N
    lat_max = max(lat_idx) + 1.0
    lon_min = min(lon_idx)

    print(f"tiles: {len(files)} -> {n_cols}x{n_rows}, origin ({lon_min},{lat_max})")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "wb") as out:
        for li in lat_idx:
            for r in range(HGT_N):
                row = []
                for oi in lon_idx:
                    _, vals = grid[(li, oi)]
                    row.extend(vals[r * HGT_N : (r + 1) * HGT_N])
                out.write(struct.pack("<%df" % n_cols, *[float(v) for v in row]))

    hdr = os.path.splitext(args.output)[0] + ".hdr"
    with open(hdr, "w", encoding="utf-8") as h:
        h.write("ENVI\n")
        h.write(f"description = {{merged NASADEM/SRTM hgt}}\n")
        h.write(f"samples = {n_cols}\n")
        h.write(f"lines = {n_rows}\n")
        h.write("bands = 1\n")
        h.write("header offset = 0\n")
        h.write("file type = ENVI Standard\n")
        h.write("data type = 4\n")  # float32
        h.write("interleave = bsq\n")
        h.write("byte order = 0\n")  # little endian
        h.write(
            "map info = {Geographic Lat/Lon, 1.0000, 1.0000, "
            f"{lon_min:.6f}, {lat_max:.6f}, {PIX:.8f}, {PIX:.8f}, WGS-84, units=Degrees}}"
            "\n"
        )
        h.write("coordinate system string = {GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\","
                "SPHEROID[\"WGS 84\",6378137,298.257223563]],PRIMEM[\"Greenwich\",0],"
                "UNIT[\"degree\",0.0174532925199433]]}\n")
    print(f"wrote {args.output} + {hdr}")


if __name__ == "__main__":
    main()
