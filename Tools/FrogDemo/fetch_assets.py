"""Download the demo's prop GLBs into ExternalAssets/stylized-assets.

The props come straight from Meshy's CDN (links in asset_urls.json, and
library_urls.json for the basic asset library, which lands in library/); the
packaged frog (SK_Frog.glb) ships next to this script. Afterwards it cuts the
ground bases off the plants (strip_bases.py). Run with any Python 3:

    python Tools/FrogDemo/fetch_assets.py
"""
import json
import os
import shutil
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "ExternalAssets", "stylized-assets")
sys.path.insert(0, HERE)
import strip_bases  # noqa: E402


def fetch(urls, out):
    os.makedirs(out, exist_ok=True)
    for name, url in json.load(open(os.path.join(HERE, urls))).items():
        dest = os.path.join(out, f"{name}.glb")
        if os.path.exists(dest):
            continue
        print("downloading", name)
        urllib.request.urlretrieve(url, dest + ".part")
        os.replace(dest + ".part", dest)


def main():
    os.makedirs(os.path.join(OUT, "demo"), exist_ok=True)
    fetch("asset_urls.json", OUT)
    fetch("library_urls.json", os.path.join(OUT, "library"))
    shutil.copyfile(os.path.join(HERE, "SK_Frog.glb"), os.path.join(OUT, "demo", "SK_Frog.glb"))
    print("cutting the ground bases off the plants")
    strip_bases.main(OUT)
    print("assets ready in", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
