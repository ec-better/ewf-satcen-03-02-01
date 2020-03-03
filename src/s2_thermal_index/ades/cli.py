import os
import sys
import importlib
from setuptools.config import read_configuration
import inspect
from argparse import ArgumentParser
import cioppy
import logging
from .data import get_references
from .signature import get_signature, log_param_update
import shutil 

logging.basicConfig(stream=sys.stderr, 
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')

def main():
    
    mod = importlib.import_module(__package__)
    inspect.getargspec(mod.main)

    # read main() signature
    signature = get_signature(mod)

    # create CLI 
    parser = ArgumentParser()

    for key in signature.keys():
        
        if key in ['service']:
            continue

        if key in ['data_path']:
            parser.add_argument('--{}'.format(key),
                                action='store',
                                dest=key,
                                default=signature[key]['value'],
                                help='Folder containing the data')
            
            parser.add_argument('--stage-in',
                                action='store',
                                    dest='stage_in',
                                    default='Yes',
                                    help='Stage-in the input reference(s)', 
                                    choices=['Yes', 'No'])

        else:
 
            if 'options' in signature[key].keys():
                    parser.add_argument('--{}'.format(key),
                                        action='store',
                                        dest=key,
                                        default=signature[key]['value'],
                                        help=signature[key]['abstract'],
                                        choices=signature[key]['options'].split(','))
            else:
                parser.add_argument('--{}'.format(key),
                                        action='store',
                                        dest=key,
                                        default=signature[key]['value'],
                                        help=signature[key]['abstract'])


    args = parser.parse_args()
        
    # update the data_path key (if available), its value is used for the stage-in (if set)
    if 'data_path' in vars(args).keys():
        
        log_param_update(signature, 'data_path', vars(args)['data_path'])        
        signature['data_path']['value'] = vars(args)['data_path']
        
    # Set values from CLI
    
    for key, value in vars(args).items():
        
        if key in ['stage_in', 'data_path']:
            continue

        log_param_update(signature, key, value)
        signature[key]['value'] = value 
        
        if key in ['input_reference', 'input_reference_stack']:
               
            if 'stage_in' in vars(args).keys():

                retrieved, identifiers = get_references(signature[key]['value'].split(','),
                                                       signature['data_path']['value'],
                                                       False if args.stage_in == 'No' else True)
        
    updated_args = [signature[key] for key in inspect.getargspec(mod.main).args]

    logging.info('Process!')
    
    mod.main(*updated_args)
    
    if args.stage_in == 'Yes':
        
        logging.info('Clean-up staged-data')
        
        for path in retrieved:
            
            if os.path.isdir(path):  
                
                shutil.rmtree(path)
                
            if os.path.isfile(path):
                
                os.remove(path)
    
    logging.info('Done!')

    sys.exit(0)

if __name__ == '__main__':
    main()