import logging
import cioppy
import sys

logging.basicConfig(stream=sys.stderr, 
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')

def get_references(references, data_path, stage_in=True):

    ciop = cioppy.Cioppy()
    
    if len(references) == 1 and stage_in:
        
        logging.info('Stage-in product to {}'.format(data_path))
        
    if len(references) > 1 and stage_in:
        
        logging.info('Stage-in {} products to {}'.format(len(references), 
                                                             data_path))

    retrieved = []
    identifier = []
    
    for index, reference in enumerate(references):
        
        logging.info('The input reference (#{} of {}) is: {}'.format(index+1,
                                                                     len(references),
                                                                     reference))

        search_params = dict()
        search_params['do'] = 'terradue'

        search = ciop.search(end_point=reference,
                             params=search_params,
                             output_fields='enclosure,identifier',
                             model='GeoTime')

        assert(search)

        identifier.append(search[0]['identifier'])
        
        logging.info('The input reference identifier is: {}'.format(search[0]['identifier']))
        
        if stage_in:
            
            logging.info('Retrieve {} from {}'.format(search[0]['identifier'], 
                                                      search[0]['enclosure']))

            local_path = ciop.copy(search[0]['enclosure'], 
                                   data_path)

            logging.info('Staged {}'.format(local_path))

            assert(local_path)

            retrieved.append(local_path)
        else:
            retrieved.append('')
        
    return retrieved, identifier
