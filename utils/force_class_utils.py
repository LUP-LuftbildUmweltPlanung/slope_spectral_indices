import os
import subprocess
import time
import shutil
import geopandas as gpd
import os
import subprocess
import time
from tqdm import tqdm
import os
import torch
import rasterio
import numpy as np
import re
from pathlib import Path
from tqdm import tqdm
import glob
import json
import datetime
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.mask import mask
from rasterio.io import MemoryFile

def generate_input_feature_line(tif_path, num_layers):
    sequence = ' '.join(str(i) for i in range(1, num_layers + 1))
    return f"INPUT_FEATURE = {tif_path} {sequence}"


def replace_parameters(filename, replacements):
    with open(filename, 'r') as f:
        content = f.read()
        for key, value in replacements.items():
            content = content.replace(key, value)
    with open(filename, 'w') as f:
        f.write(content)

def extract_coordinates(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    #Skip the first line
    lines = lines[1:]
    #Extract X and Y values
    x_values = [int(line.split('_')[0][1:]) for line in lines]
    y_values = [int(line.split('_')[1][1:]) for line in lines]
    #Extract the desired values
    x_str = f"{min(x_values)} {max(x_values)}"
    y_str = f"{min(y_values)} {max(y_values)}"

    return x_str, y_str

def check_and_reproject_shapefile(shapefile_path, target_epsg=3035):
    # Load the shapefile
    gdf = gpd.read_file(shapefile_path)
    # Check the current CRS of the shapefile
    if gdf.crs.to_epsg() != target_epsg:
        print("Reprojecting shapefile to EPSG: 3035")
        # Reproject the shapefile
        gdf = gdf.to_crs(epsg=target_epsg)
        # Define the new file path
        new_shapefile_path = shapefile_path.replace(".shp", "_3035.shp")
        # Save the reprojected shapefile
        gdf.to_file(new_shapefile_path, driver='ESRI Shapefile')
        print(f"Shapefile reprojected and saved to {new_shapefile_path}")
        return new_shapefile_path
    else:
        print("Shapefile is already in EPSG: 3035")
        return shapefile_path


def force_class_udf(project_name, force_dir, local_dir, base_path, aois, hold, date_range):
    # defining parameters outsourced from main script

    # subprocess.run(['sudo', 'chmod', '-R', '777', f"{Path(temp_folder).parent}"])
    # subprocess.run(['sudo', 'chmod', '-R', '777', f"{Path(scripts_skel).parent}"])
    base_path_script = os.getcwd()
    startzeit = time.time()
    for aoi in aois:
        print(f"FORCE PROCESSING FOR {aoi}")

        basename = os.path.basename(aoi)
        print(f"Checking AOI path: {aoi}")
        if not os.path.exists(aoi):
            print(f"Error: AOI path does not exist -> {aoi}")
        aoi = check_and_reproject_shapefile(aoi)
        print(f"Reprojected AOI path: {aoi}")



        ### get force extend
        os.makedirs(f'{base_path}/process/temp/{project_name}/FORCE/{basename}', exist_ok=True)

        # subprocess.run(['sudo', 'chmod', '-R', '777', f"{temp_folder}/{project_name}/FORCE/{basename}"])

        shutil.copy(f"{base_path_script}/utils/skel/force_cube_sceleton/datacube-definition.prj",
                    f"{base_path}/process/temp/{project_name}/FORCE/{basename}/datacube-definition.prj")

        print(f"Checking AOI path: {aoi} -> Exists: {os.path.exists(aoi)}")

        cmd = f'sudo docker run -v {local_dir} -v {force_dir} -u "$(id -u):$(id -g)" davidfrantz/force ' \
              f'force-tile-extent  {aoi} -d {base_path_script}/utils/skel/force_cube_sceleton -a {base_path}/process/temp/{project_name}/FORCE/{basename}/tile_extent.txt'

        if hold == True:
            subprocess.run(['xterm', '-hold', '-e', cmd])
        else:
            subprocess.run(['xterm', '-e', cmd])

        # subprocess.run(['sudo','chmod','-R','777',f"{temp_folder}/{project_name}/FORCE/{basename}"])

        #generate_tiles_to_process(base_path, project_name, basename)

        ### mask
        os.makedirs(f"{base_path}/process/temp/_mask/{project_name}/{basename}", exist_ok=True)

        # subprocess.run(['sudo', 'chmod', '-R', '777', f"{mask_folder}"])

        shutil.copy(f"{base_path_script}/utils/skel/force_cube_sceleton/datacube-definition.prj",
                    f"{base_path}/process/temp/_mask/{project_name}/{basename}/datacube-definition.prj")
        cmd = f'sudo docker run -v {local_dir} -u "$(id -u):$(id -g)" davidfrantz/force ' \
              f"force-cube -o {base_path}/process/temp/_mask/{project_name}/{basename} " \
              f"{aoi}"

        if hold == True:
            subprocess.run(['xterm', '-hold', '-e', cmd])
        else:
            subprocess.run(['xterm', '-e', cmd])
        # subprocess.run(['sudo','chmod','-R','777',f"{mask_folder}/{project_name}/{basename}"])

        ###mask mosaic
        cmd = f'sudo docker run -v {local_dir} -u "$(id -u):$(id -g)" davidfrantz/force ' \
              f"force-mosaic {base_path}/process/temp/_mask/{project_name}/{basename}"

        if hold == True:
            subprocess.run(['xterm', '-hold', '-e', cmd])
        else:
            subprocess.run(['xterm', '-e', cmd])

        # subprocess.run(['sudo','chmod','-R','777',f"{temp_folder}/{project_name}/FORCE/{basename}"])

        ###force param

        os.makedirs(f"{base_path}/process/temp/{project_name}/FORCE/{basename}/provenance", exist_ok=True)
        os.makedirs(f"{base_path}/process/temp/{project_name}/FORCE/{basename}/tiles_tss", exist_ok=True)

        shutil.copy(f"{base_path_script}/utils/skel/force_cube_sceleton/datacube-definition.prj",
                    f"{base_path}/process/temp/{project_name}/FORCE/{basename}/datacube-definition.prj")
        shutil.copy(f"{base_path_script}/utils/skel/force_cube_sceleton/datacube-definition.prj",
                    f"{base_path}/process/temp/{project_name}/FORCE/{basename}/tiles_tss/datacube-definition.prj")
        shutil.copy(f"{base_path_script}/utils/skel/tsa_UDF.prm",
                    f"{base_path}/process/temp/{project_name}/FORCE/{basename}/UDF_prm.prm")
        shutil.copy(f"{base_path_script}/utils/skel/UDF_pixel.py",
                    f"{base_path}/process/temp/{project_name}/FORCE/{basename}/UDF_slope.py")

        X_TILE_RANGE, Y_TILE_RANGE = extract_coordinates(f"{base_path}/process/temp/{project_name}/FORCE/{basename}/tile_extent.txt")
        DATE_RANGE = date_range

        # Define replacements
        replacements = {
            # INPUT/OUTPUT DIRECTORIES
            f'DIR_LOWER = NULL': f'DIR_LOWER = {force_dir.split(":")[0]}/FORCE/C1/L2/ard',
            f'DIR_HIGHER = NULL': f'DIR_HIGHER = {base_path}/process/temp/{project_name}/FORCE/{basename}/tiles_tss',
            f'DIR_PROVENANCE = NULL': f'DIR_PROVENANCE = {base_path}/process/temp/{project_name}/FORCE/{basename}/provenance',
            # MASKING
            f'DIR_MASK = NULL': f'DIR_MASK = {base_path}/process/temp/_mask/{project_name}/{basename}',
            f'BASE_MASK = NULL': f'BASE_MASK = {os.path.basename(aoi).replace(".shp", ".tif")}',
            # PROCESSING EXTENT AND RESOLUTION
            f'X_TILE_RANGE = 0 0': f'X_TILE_RANGE = {X_TILE_RANGE}',
            f'Y_TILE_RANGE = 0 0': f'Y_TILE_RANGE = {Y_TILE_RANGE}',
            f'DATE_RANGE = YYYY-MM-DD YYYY-MM-DD': f'DATE_RANGE = {DATE_RANGE}',
            f'FILE_PYTHON = NULL': f'FILE_PYTHON = {base_path}/process/temp/{project_name}/FORCE/{basename}/UDF_slope.py',
        }
        # Replace parameters in the file
        replace_parameters(f"{base_path}/process/temp/{project_name}/FORCE/{basename}/UDF_prm.prm", replacements)

    endzeit = time.time()
    print("FORCE-Processing beendet nach " + str((endzeit - startzeit) / 60) + " Minuten")

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