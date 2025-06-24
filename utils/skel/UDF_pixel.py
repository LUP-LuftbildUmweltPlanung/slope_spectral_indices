import numpy as np
import gc
from datetime import date, timedelta

# Global start date
start = date.fromisoformat('1970-01-01')


def forcepy_init(dates, sensors, bandnames):
    """
    Initialize output label for the slope raster.
    Returns:
        List with a single element: ["slope"].
    """
    #print("[DEBUG] forcepy_init called")
    return ["slope"]


def forcepy_pixel(inarray, outarray, dates, sensors, bandnames, nodata, nproc):
    """
    Compute the slope of the time series per pixel using DSWI index.

    inarray:   numpy.ndarray[nDates, nBands, nrows, ncols](Int16)
    outarray:  numpy.ndarray[nOutBands](Float32) - Initialized with no data values
    dates:     numpy.ndarray[nDates](int) - Days since epoch (1970-01-01)
    sensors:   numpy.ndarray[nDates](str) - Sensor names
    bandnames: numpy.ndarray[nBands](str) - Band names
    nodata:    int - No data value
    nproc:     int - Number of allowed processes/threads
    """

    try:
        #print("[DEBUG] forcepy_pixel called")

        inarray = inarray.astype(np.float32)  # Convert to float32
        inarray = inarray[:, :, 0, 0]  # Extract pixel time series
        invalid = inarray == nodata  # Identify no-data values

        valid = np.where(inarray[:, 0] != nodata)[0]  # Select valid time points
        #print(f"[DEBUG] Valid indices found: {len(valid)}")

        if len(valid) < 3:  # Require at least 3 points to compute a meaningful slope
            #print("[DEBUG] Not enough valid data points, setting outarray to nodata")
            outarray[0] = float(nodata)
            return

        inarray[invalid] = np.nan  # Set no-data to NaN
        #print(f"[DEBUG] First 5 valid inarray values: {inarray[valid][:5]}")

        # Extract band indices
        try:
            green = np.argwhere(bandnames == b'GREEN')[0][0]
            red = np.argwhere(bandnames == b'RED')[0][0]
            nir = np.argwhere(bandnames == b'NIR')[0][0]
            swir1 = np.argwhere(bandnames == b'SWIR1')[0][0]
            #print(f"[DEBUG] Band indices - Green: {green}, Red: {red}, NIR: {nir}, SWIR1: {swir1}")
        except IndexError as e:
            #print(f"[ERROR] Band not found: {e}")
            outarray[0] = float(nodata)
            return

        # Get valid values
        vals = inarray[valid, :]

        # Compute DSWI = (NIR + GREEN) / (SWIR1 + RED)
        denominator = (vals[:, swir1] + vals[:, red])
        dswi = (vals[:, nir] + vals[:, green]) / np.where(denominator != 0, denominator, np.nan)
        #print(f"[DEBUG] First 5 computed DSWI values: {dswi[:5]}")

        # Check if DSWI is constant (no variation → slope should be nodata)
        if np.all(dswi == dswi[0]):
            #print("[DEBUG] DSWI values are constant, setting outarray to nodata")
            outarray[0] = float(nodata)
            return

        # Convert dates to numerical format (days since epoch)
        time_values = np.array([dates[i] for i in valid], dtype=np.float32)
        #print(f"[DEBUG] First 5 time values: {time_values[:5]}")

        # Compute slope manually using least squares
        N = len(time_values)
        sum_x = np.sum(time_values)
        sum_y = np.sum(dswi)
        sum_xy = np.sum(time_values * dswi)
        sum_x2 = np.sum(time_values ** 2)

        denominator = (N * sum_x2 - sum_x ** 2)
        #print(f"[DEBUG] Computed slope denominator: {denominator}")

        if denominator != 0:  # Avoid division by zero
            slope = (N * sum_xy - sum_x * sum_y) / denominator

            # Scale slope by 100 to keep two decimal places
            scaled_slope = slope * 100
            scaled_slope = round(scaled_slope,2)

            # Ensure we do not round too much
            #if abs(scaled_slope) < 1e-3:
            #    print("[DEBUG] Slope is too small, but keeping precision")

            outarray[0] = np.float32(scaled_slope)
            #print(f"[DEBUG] Scaled slope: {scaled_slope}, Out array: {outarray[0]}")
        else:
            #print("[DEBUG] Denominator is zero, setting outarray to nodata")
            outarray[0] = float(nodata)

        # Force garbage collection if needed
        gc.collect()

    except Exception as e:
        #print(f"[ERROR] Exception occurred: {e}")
        outarray[0] = float(nodata)  # Ensure outarray gets assigned even if an error occurs
