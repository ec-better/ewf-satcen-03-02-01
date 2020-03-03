import inspect
import logging
import sys

logging.basicConfig(stream=sys.stderr, 
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')

def log_param_update(signature, key, param_value):
    
    # log some information but not all of it
    if key in ['data_path', 'input_reference', 'input_reference_stack']:
      
        msg = 'Update parameter {} with value \'{}\''.format(key, 
                                                                param_value)

        msg = 'Update parameter {} with value \'{}\''.format(key, 
                                                                param_value)
    elif signature[key]['identifier'] == '_T2Username':

        msg = 'Update parameter {} with value \'{}***\''.format(key, 
                                                                param_value[0:3])

    elif signature[key]['identifier'] == '_T2ApiKey':

        msg = 'Update parameter {} with value \'{}***{}\''.format(key, 
                                                                  param_value[0:3],
                                                                  param_value[-3:])
    else:
        msg = 'Update parameter {} with value \'{}\''.format(key, 
                                                             param_value)

    logging.info(msg)
    
    return True

def get_signature(module):
    
    # read the child app Python module main function signature
    signature = dict()

    for index, arg in enumerate(inspect.getargspec(module.main).args):

        signature[arg] = [item[1] for item in inspect.getmembers(module) if arg in item][0]
    
    signature['service'] = module.service

    return signature