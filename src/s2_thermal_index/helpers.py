import os
import sys
import pandas as pd
import otbApplication
import lxml.etree as etree
import numpy as np
import math
from os.path import exists
import ogr
import gdal 
from osgeo.gdalconst import GA_ReadOnly
from ogr import osr
import geopandas as gp
import json

def polygonize(url, date, originator):
    
    ds = gdal.Open(url)
    
    srs = osr.SpatialReference(wkt=ds.GetProjection())
    
    band = ds.GetRasterBand(1)
    band_array = band.ReadAsArray()

    out_geojson = 'polygonized.json'

    driver = ogr.GetDriverByName('GeoJSON')

    out_data_source = driver.CreateDataSource(out_geojson + "")
    out_layer = out_data_source.CreateLayer('polygonized', srs=srs)

    new_field = ogr.FieldDefn('hot_spot', ogr.OFTInteger)
    out_layer.CreateField(new_field)

    gdal.Polygonize(band, None, out_layer, 0, [], callback=None )

    out_data_source = None
    ds = None

    data = json.loads(open(out_geojson).read())
    gdf = gp.GeoDataFrame.from_features(data['features'])
    gdf = gdf[gdf['hot_spot'] == 1]
    gdf['date'] = date
    gdf['originator'] = originator
    
    gdf.crs = {'init':'epsg:{}'.format(srs.GetAttrValue('AUTHORITY', 1))}
    
    os.remove(out_geojson)
    
    return gdf

def analyse(row, data_path):
    
    series = dict()
    
    series['utm_zone'] = row['identifier'][39:41]
    series['latitude_band'] = row['identifier'][41]
    series['grid_square']  = row['identifier'][42:44]
    series['local_path'] = os.path.join(data_path, row['identifier'])
    
    return pd.Series(series)


def get_band_path(row, band):
    
    ns = {'xfdu': 'urn:ccsds:schema:xfdu:1',
          'safe': 'http://www.esa.int/safe/sentinel/1.1',
          'gml': 'http://www.opengis.net/gml'}
    
    path_manifest = os.path.join(row['local_path'],
                                 row['identifier'] + '.SAFE', 
                                'manifest.safe')
    
    root = etree.parse(path_manifest)
    
    bands = [band]

    for index, band in enumerate(bands):

        sub_path = os.path.join(row['local_path'],
                                row['identifier'] + '.SAFE',
                                root.xpath('//dataObjectSection/dataObject/byteStream/fileLocation[contains(@href,("%s%s")) and contains(@href,("%s")) ]' % (row['latitude_band'],
                                row['grid_square'], 
                                band), 
                                  namespaces=ns)[0].attrib['href'][2:])
    
    return sub_path

def contrast_enhancement(in_tif, out_tif, hfact=1.0):

    ContrastEnhancement = otbApplication.Registry.CreateApplication("ContrastEnhancement")

    ContrastEnhancement.SetParameterString("in", in_tif)
    ContrastEnhancement.SetParameterString("out", out_tif)
    ContrastEnhancement.SetParameterOutputImagePixelType("out", otbApplication.ImagePixelType_uint8)
    ContrastEnhancement.SetParameterFloat("nodata", 0.0)
    ContrastEnhancement.SetParameterFloat("hfact", hfact)
    ContrastEnhancement.SetParameterInt("bins", 256)
    ContrastEnhancement.SetParameterInt("spatial.local.w", 500)
    ContrastEnhancement.SetParameterInt("spatial.local.h", 500)
    ContrastEnhancement.SetParameterString("mode","lum")

    ContrastEnhancement.ExecuteAndWriteOutput()

    return True 

def radius_index(i, j, d, width, height):
    
    i_ind1 = i - d
    i_ind2 = i + d + 1
    j_ind1 = j - d
    j_ind2 = j + d + 1
    
    if i_ind1 < 0:
        i_ind1 = 0
    
    if i_ind2 >= width:
        i_ind2 = width-1
    
    if j_ind1 < 0:
        j_ind1 = 0
    
    if j_ind2 >= height:
        j_ind2 = height-1

    return i_ind1, i_ind2, j_ind1, j_ind2
    
def hot_spot(s2_product, output_name, output_composite_name):
    
    gain = 10000
    
    ds = gdal.Open(s2_product)
    
    b8A = ds.GetRasterBand(1).ReadAsArray()
    b12 = ds.GetRasterBand(2).ReadAsArray()
     
    width = ds.RasterXSize
    height = ds.RasterYSize
    
    input_geotransform = ds.GetGeoTransform()
    input_georef = ds.GetProjectionRef()
    
    hot_spot = np.zeros((height, width), dtype=np.uint8)
    
    r = np.zeros((height, width))
    
    # Calculate ratio r and difference delta
    r[np.where(b8A > 0)] = b12[np.where(b8A > 0)] / b8A[np.where(b8A > 0)]
    delta = b12 - b8A
 
    b8A = None
    # Step 1 : mask obvious water pixels (value 3)
    # B12 < 0.04 are flagged as water and thus are excluded
    hot_spot[np.where(b12 < (0.04 * gain))] = 3

    # Step 2 : identify obvious fire pixels (value 1)
    hot_spot[np.where((hot_spot == 0) & (r > 2) & (delta > (0.15 * gain)))] = 1

    # Step 3 : identify candidate fire pixels (value 2)
    hot_spot[np.where((hot_spot == 0) & (r > 1.1) & (delta > (0.1 * gain)))] = 2

    # Step 4 : background characterization around candidate fire pixelscase of large fire.
    hot_spot[np.where(hot_spot == 3)] = 0
    
    
    for j in range(width):

        for i in range(height):

            # If the pixel is a candidate fire pixel (value = 2), we have to decide
            if hot_spot[i, j] == 2:

                # Find an appropriate size for a square window centered on the candidate fire pixel
                # default size is 91 x 91 pixels (1820m * 1820m)
                # We increase the size while the number of no obvious or candidate fire pixels is less than the half of total pixels in the window.
                d = 91
                i_ind1, i_ind2, j_ind1, j_ind2 = radius_index(i, j, d, width, height)
                nbr_pixels = math.floor(math.pow(d, 2) / 2)

                while np.size(np.where(hot_spot[i_ind1:i_ind2,j_ind1:j_ind2] == 0))/2 < nbr_pixels:
                    d += 8
                    i_ind1,i_ind2,j_ind1,j_ind2 = radius_index(i,j,d,width,height)
                    nbr_pixels = math.floor(math.pow(d,2) / 2)

                # background_characterization in the defined square window centered on the candidate fire pixel
                # Statistics are computed for pixels within the background : mean and stdv of r; 
                # mean and stdv of B12
                r_m =  np.mean(r[np.where(hot_spot[i_ind1:i_ind2,j_ind1:j_ind2] == 0)])
                r_std = np.std(r[np.where(hot_spot[i_ind1:i_ind2,j_ind1:j_ind2] == 0)])

                B12_m = np.mean(b12[np.where(hot_spot[i_ind1:i_ind2,j_ind1:j_ind2] == 0)])
                B12_std = np.std(b12[np.where(hot_spot[i_ind1:i_ind2,j_ind1:j_ind2] == 0)])

                # Step 5 : Contextual tests
                # Here we decide for all candidate fire pixels (value 2) if they are fire (value 1) or not (value 0)
                # Two conditions have to be sattisfied to flag a candidate pixel as fire pixel
                if ( r[i,j] > r_m + max((3 * r_std),(0.5 * gain)) ) and ( b12[i,j] > b12_m + max((3 * b12_std),(0.05 * gain)) ):
                    hot_spot[i,j] = 1
                else:
                    hot_spot[i,j] = 0
    
    driver = gdal.GetDriverByName('GTiff')
    
    output = driver.Create(output_name, 
                           width, 
                           height, 
                           1, 
                           gdal.GDT_Byte)
        
    output.SetGeoTransform(input_geotransform)
    output.SetProjection(input_georef)
    output.GetRasterBand(1).WriteArray(hot_spot)

    output.FlushCache()
    
    red_band = ds.GetRasterBand(3).ReadAsArray().astype(float)
    green_band = ds.GetRasterBand(4).ReadAsArray().astype(float)
    blue_band = ds.GetRasterBand(5).ReadAsArray().astype(float)
    
    # rescale
    red_band = (red_band / 4095.0 * 255).astype(int)
    green_band = (green_band / 4095.0 * 255).astype(int)
    blue_band = (blue_band / 4095.0 * 255).astype(int)
    
    if np.max(hot_spot) > 0:
        red_band[np.where(hot_spot == 1)] = 255
        green_band[np.where(hot_spot == 1)] = 0
        blue_band[np.where(hot_spot == 1)] = 0
    
    driver = gdal.GetDriverByName('GTiff')
    
    output = driver.Create(output_composite_name, 
                           width, 
                           height, 
                           3, 
                           gdal.GDT_Byte)
        
    output.SetGeoTransform(input_geotransform)
    output.SetProjection(input_georef)
    output.GetRasterBand(1).WriteArray(red_band)
    output.GetRasterBand(2).WriteArray(green_band)
    output.GetRasterBand(3).WriteArray(blue_band)
    
    output.FlushCache()
    
    return True



    
    

    
