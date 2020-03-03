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
    
def hot_spot(s2_product, scl_product, output_name):
    
    gain = 10000
    
    ds_scl = gdal.Open(scl_product)
    scl = ds_scl.GetRasterBand(1).ReadAsArray() 
    
    ds_scl = None
    
    ds = gdal.Open(s2_product)
    b12 = ds.GetRasterBand(1).ReadAsArray()
    
    width = ds.RasterXSize
    height = ds.RasterYSize
    
    input_geotransform = ds.GetGeoTransform()
    input_georef = ds.GetProjectionRef()
    
    ds = None
    
    hot_spot = np.zeros((height, width), dtype=np.uint8)
   
    # Step 1 : mask obvious water pixels (value 3)
    # B12 < 0.04 are flagged as water and thus are excluded
    hot_spot[np.where(b12 > (0.8 * gain))] = 1
    hot_spot[np.where(b12 <= (0.8 * gain))] = 0
    
    # Step 2 : identify obvious fire pixels (value 1)
    hot_spot[np.where((scl == 0) | (scl == 1))] = 2

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
   
    return True



    
    

    
