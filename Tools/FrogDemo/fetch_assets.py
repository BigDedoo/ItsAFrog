"""Download the demo's prop GLBs into ExternalAssets/stylized-assets.

The props come straight from Meshy's CDN (links in asset_urls.json); the
packaged frog (SK_Frog.glb) ships next to this script. Run with any Python 3:

    python Tools/FrogDemo/fetch_assets.py
"""
import json
import os
import shutil
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "ExternalAssets", "stylized-assets")


def main():
    os.makedirs(os.path.join(OUT, "demo"), exist_ok=True)
    for name, url in json.load(open(os.path.join(HERE, "asset_urls.json"))).items():
        dest = os.path.join(OUT, f"{name}.glb")
        if os.path.exists(dest):
            continue
        print("downloading", name)
        urllib.request.urlretrieve(url, dest + ".part")
        os.replace(dest + ".part", dest)
    shutil.copyfile(os.path.join(HERE, "SK_Frog.glb"), os.path.join(OUT, "demo", "SK_Frog.glb"))
    print("assets ready in", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
