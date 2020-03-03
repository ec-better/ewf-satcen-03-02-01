import yaml
import logging
import click
import pkg_resources
import sys
from .signature import get_signature
import importlib
import os
#import inspect 

logging.basicConfig(stream=sys.stderr, 
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')

@click.command()
@click.option('--cwlfile', '-c')
@click.option('--stdout', is_flag=True)
def main(cwlfile, stdout):
    
    mod = importlib.import_module(__package__)
    #inspect.getargspec(mod.main)

    # read main() signature
    signature = get_signature(mod)
    
    cwl = dict()
    cwl_inputs = dict()

    cwl['cwlVersion'] = 'v1.0'
    cwl['class'] = 'CommandLineTool'
    cwl['baseCommand'] = __package__.split('.')[0].replace('_', '-')
    cwl['stdout'] = 'std.out'
    cwl['stderr'] = 'std.err'

    defaults = dict()

    for key in signature.keys():
        
        if key in ['service', 'input_identifier']:

            continue

        defaults[key] = signature[key]['value']
    
    defaults['stage-in'] = 'Yes'   
        
    with open('default.yaml', 'w') as file:
        yaml.dump(defaults, file, default_flow_style=False)

    params = []

    for index, key in enumerate(list(signature.keys()) + ['stage-in']):

        if key in ['service', 'input_identifier']:

            continue

        params.append(key)


    for index, key in enumerate(params):

        if key in ['service', 'input_identifier']:

            continue

        cwl_inputs[key] = {'type': 'string',
                  'inputBinding': {'position': index + 1,
                                   'prefix': '--{}'.format(key)}
                 }



    cwl['inputs'] = cwl_inputs


    cwl['outputs'] = {'results' : {'type':{'type': 'array',                            
                                  'items': 'File'},
                                  'outputBinding': { 'glob': '*'}
                                 },
                   'std-out': {'type': 'stdout'},
                   'std-err': {'type': 'stderr'},
                   }

    cwl['requirements'] = {'EnvVarRequirement' : {'envDef':
            {'PATH' : os.environ['PATH']}
            }
            }
    

    if stdout:
        yaml.dump(cwl, sys.stdout, default_flow_style=False)
    else:
        with open(cwlfile, 'w') as file:
            yaml.dump(cwl, file, default_flow_style=False)

    logging.info('Done!')

    sys.exit(0)

if __name__ == '__main__':
    
    main()
