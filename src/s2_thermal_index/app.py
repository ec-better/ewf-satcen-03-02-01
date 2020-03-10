import os
import sys
from .helpers import *
from geopandas import GeoDataFrame
import pandas as pd
import cioppy
from shapely.geometry import box
from shapely.wkt import loads
import numpy as np
import datetime
import gdal
import shutil
import logging

logging.basicConfig(stream=sys.stderr, 
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')

service = dict([('title', 'SATCEN Sentinel-2 thermal index'),
                ('abstract', 'SATCEN Sentinel-2 thermal index'),
                ('identifier', 'ewf-satcen-03-02-01')])



aoi_wkt = dict([('identifier', 'aoi'),
                ('value', '152.117,-31.128,152.457,-30.817'),
                ('title', 'Area of interest in WKT or bbox'),
                ('abstract', 'Area of interest using a polygon in Well-Known-Text format or bounding box'),
                ('max_occurs', '1')])



input_reference = dict([('identifier', 'input_reference'),
                        ('title', 'S2 references'),
                        ('abstract', 'S2 input reference as a comma separated list of catalogue references'),
                        ('value', 'https://catalog.terradue.com/sentinel2/search?uid=S2A_MSIL2A_20191107T235251_N0213_R130_T56JML_20191108T014647'),
                        ('min_occurs', '1')])



data_path = dict([('value', '/workspace/data')])

def main(input_reference, data_path):
    
    
    os.environ['OTB_MAX_RAM_HINT'] = '4096'
    
    ciop = cioppy.Cioppy()
    temp_results = []

    search_params = dict()
    
    for index, entry in enumerate(input_reference['value'].split(',')):

        temp_results.append(ciop.search(end_point=entry, 
                            params=search_params,
                            output_fields='identifier,self,wkt,startdate,enddate,enclosure,orbitDirection,cc', 
                            model='EOP')[0])
    
    sentinel2_search = GeoDataFrame(temp_results)

    sentinel2_search['startdate'] = pd.to_datetime(sentinel2_search['startdate'])
    sentinel2_search['enddate'] = pd.to_datetime(sentinel2_search['enddate'])
    sentinel2_search['wkt'] = sentinel2_search['wkt'].apply(loads)    
            
    sentinel2_search = sentinel2_search.merge(sentinel2_search.apply(lambda row: analyse(row, 
                                                                                         data_path['value']), 
                                                                     axis=1), 
                                             left_index=True,
                                             right_index=True)
    
    composites = []

    bands = ['B12', 'B8A', 'B04']

    for index, row in sentinel2_search.iterrows():

        # cloud mask
        logging.info('Cloud mask 20%')
        mask_prb = get_mask_prob(row)
        
        output_name = '{}_CLOUD_MASK_20.tif'.format(row['identifier'])
        
        cloud_mask(mask_prb, 20, output_name)
        
        cog(output_name)
        
        metadata(output_name,
                 'Cloud mask 20% {}'.format(row['identifier']),
                 row)
        
        
        vrt_bands = []

        for j, band in enumerate(bands):

            vrt_bands.append(get_band_path(row, band))

        vrt = '{0}.vrt'.format(row['identifier'])
        ds = gdal.BuildVRT(vrt,
                           vrt_bands,
                           srcNodata=0,
                           xRes=10, 
                           yRes=10,
                           separate=True)
        
        ds.FlushCache()

        tif = '{}_ACTIVE_FIRE_UInt16.tif'.format(row['identifier'])
        
        logging.info('Convert {} to UInt16'.format(row['identifier']))

        metadata(tif,
                 'RGB UInt16 Composite {}'.format(row['identifier']),
                 row)
        
        gdal.Translate(tif,
                       vrt,
                       outputType=gdal.GDT_UInt16)
        
        cog(tif)
        
        tif =  '{0}.tif'.format(row['identifier'])
        
        logging.info('Convert {} to byte'.format(row['identifier']))

        gdal.Translate(tif,
                       vrt,
                       outputType=gdal.GDT_Byte, 
                       scaleParams=[[0, 10000, 0, 255]])
        
        
        tif_e =  '{}_ACTIVE_FIRE.tif'.format(row['identifier'])

        contrast_enhancement(tif, tif_e)

        composites.append(tif_e)
        os.remove(tif)
        os.remove(vrt)

        cog(tif_e)
        
        metadata(tif_e, 
                 'RGB Composite {}'.format(row['identifier']),
                 row)
    
        vrt = '{0}.vrt'.format(row['identifier'])
        ds = gdal.BuildVRT(vrt,
                           [get_band_path(row, 'SCL')],
                           separate=True)
        ds.FlushCache()

        scl_tif =  '{0}_SCL.tif'.format(row['identifier'])

        metadata(scl_tif,
                 'Scene Classification {}'.format(row['identifier']),
                 row)
        
        gdal.Translate(scl_tif,
                       vrt,
                       xRes=10, 
                       yRes=10,
                       outputType=gdal.GDT_Byte, 
                       resampleAlg=gdal.GRA_Mode)

        cog(scl_tif)
               
    bands = ['B12']

    #resampleAlg=gdal.GRA_Mode,
    for index, row in sentinel2_search.iterrows():

        vrt_bands = []

        for j, band in enumerate(bands):

            vrt_bands.append(get_band_path(row, band))

        vrt = '{0}.vrt'.format(row['identifier'])
        ds = gdal.BuildVRT(vrt,
                           vrt_bands,
                           srcNodata=0,
                           xRes=10, 
                           yRes=10,
                           separate=True)
        ds.FlushCache()

        tif =  '{0}.tif'.format(row['identifier'])

        gdal.Translate(tif,
                       vrt,
                       outputType=gdal.GDT_UInt16)


        hot_spot_name = '{}_HOT_SPOT.tif'.format(row['identifier'])
        metadata(hot_spot_name, 
                 'Hot spot {}'.format(row['identifier']),
                 row)
        
        logging.info('Hot spot detection for {}'.format(row['identifier']))
        hot_spot(tif,
                 scl_tif,
                 hot_spot_name)
    
        cog(hot_spot_name)
    
        logging.info('Vectorize detected hot spots in {}'.format(row['identifier']))
        
        results_gdf = polygonize(hot_spot_name, row['startdate'], row['identifier'])
        
        results_gdf.to_file('{}_HOT_SPOT_VECTOR.geojson'.format(row['identifier']),
                            driver='GeoJSON')
        
        metadata('{}_HOT_SPOT_VECTOR.geojson'.format(row['identifier']),
                 'Hot spot vector {}'.format(row['identifier']),
                 row)
        
        os.remove(tif)
        os.remove(vrt)
        
if __name__ == '__main__':
    
    main()
    
    
    
    


