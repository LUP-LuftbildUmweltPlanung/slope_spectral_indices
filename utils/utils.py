
import subprocess
import time
import os
import rasterio
from tqdm import tqdm
import glob
import geopandas as gpd
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.io import MemoryFile

def create_folder_structure(base_path):
    # Define the folder structure
    folder_structure = [
        'process',
        'process/data',
        'process/results',
        'process/temp',
        'process/temp/_mask'
    ]

    # Create each folder if it does not exist
    for folder in folder_structure:
        path = os.path.join(base_path, folder)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created folder: {path}")
        else:
            print(f"Folder already exists: {path}")

def execute_cmd(base_path, project_name, basename, hold, local_dir, force_dir):
    cmd = f'sudo docker run -v {local_dir} -v {force_dir} -u "$(id -u):$(id -g)" davidfrantz/force ' \
          "force-higher-level " \
          f"{base_path}/process/temp/{project_name}/FORCE/{basename}/UDF_prm.prm"

    if hold == True:
        subprocess.run(['xterm', '-hold', '-e', cmd])
    else:
        subprocess.run(['xterm','-e', cmd])

def mosaic_rasters(base_path, project_name, basename, aoi_path=None, dtype="uint16"):
    """
    Mosaic rasters, optionally clip using AOI shapefile, and export with compression and compact dtype.
    Shows progress bars and step timings.
    """

    start_total = time.time()

    # Step 1: Find input raster files
    input_paths = glob.glob(f"{base_path}/process/temp/{project_name}/FORCE/{basename}/tiles_tss/X*/*.tif")
    print(f"Found {len(input_paths)} raster tiles.")
    if not input_paths:
        raise ValueError("No input .tif files found! Check your path.")

    # Step 2: Read rasters with progress bar
    src_files_to_mosaic = []
    start_read = time.time()
    for fp in tqdm(input_paths, desc="Reading raster tiles", unit="tile"):
        src_files_to_mosaic.append(rasterio.open(fp))
    end_read = time.time()
    print(f"✔ Finished reading in {end_read - start_read:.2f} seconds.")

    # Step 3: Mosaic the rasters
    print("🔄 Merging rasters...")
    start_merge = time.time()
    mosaic, out_transform = merge(src_files_to_mosaic)
    end_merge = time.time()
    print(f"✔ Merged in {end_merge - start_merge:.2f} seconds.")

    # Step 4: Prepare metadata
    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_transform,
        "compress": "deflate",
        "predictor": 2,
        "zlevel": 6,
        "dtype": dtype
    })

    # Step 5: Clip with AOI if provided
    if aoi_path:
        print("📐 Clipping mosaic with AOI...")
        start_clip = time.time()
        aoi_gdf = gpd.read_file(aoi_path)
        if aoi_gdf.crs != out_meta["crs"]:
            aoi_gdf = aoi_gdf.to_crs(out_meta["crs"])
        shapes = [geom.__geo_interface__ for geom in aoi_gdf.geometry]

        # Write to memory and re-open to clip the entire mosaic
        with MemoryFile() as memfile:
            with memfile.open(**out_meta) as temp_ds:
                temp_ds.write(mosaic)
            with memfile.open() as temp_ds:
                mosaic, out_transform = mask(dataset=temp_ds, shapes=shapes, crop=True)

        out_meta.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform
        })
        end_clip = time.time()
        print(f"✔ Clipped in {end_clip - start_clip:.2f} seconds.")

    # Step 6: Set up output
    output_dir = f"{base_path}/process/results/{project_name}"
    os.makedirs(output_dir, exist_ok=True)
    first_name = os.path.splitext(os.path.basename(input_paths[0]))[0]
    output_filename = os.path.join(output_dir, f"{first_name}.tif")

    # Step 7: Prepare band descriptions
    descriptions = src_files_to_mosaic[0].descriptions
    if descriptions and all(desc is not None for desc in descriptions):
        out_meta["descriptions"] = tuple(descriptions)

    # Step 8: Write mosaic and set band descriptions
    print("💾 Saving mosaic to disk...")
    start_write = time.time()
    with rasterio.open(output_filename, "w", **out_meta) as dest:
        dest.write(mosaic)
        for i, desc in tqdm(enumerate(descriptions, 1), total=len(descriptions), desc="Setting band descriptions"):
            dest.set_band_description(i, desc)
    end_write = time.time()
    print(f"✔ Saved in {end_write - start_write:.2f} seconds.")

    # Step 9: Close all rasters
    for src in src_files_to_mosaic:
        src.close()

    end_total = time.time()
    print(f"\n🎉 Mosaic saved to: {output_filename}")
    print(f"⏱ Total time: {end_total - start_total:.2f} seconds")

    return output_filename
