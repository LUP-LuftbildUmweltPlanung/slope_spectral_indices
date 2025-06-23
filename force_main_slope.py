###### execute force dynamically ##########
### requirements: sudo apt-get install xterm
############################################
import subprocess
import time
import os
import glob
from utils.utils import create_folder_structure, execute_cmd, mosaic_rasters
from utils.force_class_utils import force_class_udf

base_path = '/rvt_mount'                                               # This should be only one folder directory to assure that "local_dir" is correct
project_name = "hassberge_slope"                                                   # Project Name defined for vitalitat_3cities_data storage
force_dir = "/force:/force"                                             # Mount Point for Force-Datacube
local_dir = f"{base_path}:{base_path}"                                     # Mount Point for local Drive
hold = False                                                             # if True, cmd must be closed manually - recommended for debugging FORCE

#DEfine the date range and area of interest
date_range = "2019-01-01 2019-12-31"                                                    #Format YYYY-MM-DD
aois = glob.glob("/rvt_mount/vitalitat_3cities_data/process/data/Hassberge/Landkreis_Hassberge_3035.shp")      # Define multiple or single AOI-Shapefile

#General functions                                                                      # To debug, run function by function
#create_folder_structure(base_path)                                                      #Creates the folder structure b
#force_class_udf(project_name, force_dir, local_dir, base_path, date_range, aois, hold)  #Creates prm file
basename = os.path.basename (aois[0])                                                   #Redirects the outputs following the aois path
execute_cmd(base_path, project_name, basename, hold, local_dir, force_dir)              #Executes the calculation
mosaic_rasters(base_path, project_name, basename, aoi_path=None, dtype="int16")
