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
    
    print(os.environ['OTB_APPLICATION_PATH'])
    
    # read main() signature
    signature = get_signature(mod)
    
    cwl = dict()
    cwl_inputs = dict()

    cwl['cwlVersion'] = 'v1.0'


    node_workflow = dict()

    node_workflow['id'] = 'node'  
    node_workflow['class'] = 'CommandLineTool'
    node_workflow['baseCommand'] = __package__.split('.')[0].replace('_', '-')
    node_workflow['stdout'] = 'std.out'
    node_workflow['stderr'] = 'std.err'

    defaults = dict()

    for key in signature.keys():

        if key in ['service', 'input_identifier']:

            continue

        if key in ['input_reference']:
            defaults[key] = signature[key]['value'].split(',')
        else:
            defaults[key] = signature[key]['value']

    defaults['stage-in'] = 'Yes'   

    with open('default.yaml', 'w') as file:
        yaml.dump(defaults, file, default_flow_style=False)


    # read the parameters 
    node_inputs = dict()
    main_inputs = dict()
    step_inputs = dict()

    input_index = 1

    for index, key in enumerate(list(signature.keys())):

        if key in ['service', 'input_identifier']:

            continue


        if key == 'input_reference':

            main_inputs[key] = 'string[]'

            node_inputs['inp{}'.format(input_index)] = {'type': 'string',
                       'inputBinding': {'position': input_index,
                                       'prefix': '--{}'.format(key)}
                     }

            step_inputs['inp{}'.format(input_index)] = key

            scatter_input = 'inp{}'.format(input_index)

        if key == 'data_path':

            main_inputs[key] = 'string'

            node_inputs['inp{}'.format(input_index)] = {'type': 'string',
                               'default': '/workspace/data',
                      'inputBinding': {'position': input_index,
                                       'prefix': '--{}'.format(key) 
                                       }
                     }

            step_inputs['inp{}'.format(input_index)] = key

            input_index += 1

            main_inputs['stage-in'] = 'string'

            node_inputs['inp{}'.format(input_index)] = {'type': 'string',
                               'default': 'Yes',
                               'inputBinding': {'position': input_index,
                                       'prefix': '--{}'.format('stage-in') 
                                       }
                              }
            step_inputs['inp{}'.format(input_index)] = 'stage-in'

        if key not in ['service', 'input_identifier', 'input_reference', 'data_path']:

            main_inputs[key] = 'string'

            node_inputs['inp{}'.format(input_index)] = {'type': 'string',
                      'inputBinding': {'position': input_index,
                                       'prefix': '--{}'.format(key)}
                     }

            step_inputs['inp{}'.format(input_index)] = key

        input_index += 1


    node_workflow['inputs'] = node_inputs

    node_workflow['outputs'] = {'results' : {'outputBinding': { 'glob': '*'},
                                             'type': {'items': 'File', 
                                                      'type': 'array'}                                        
                                 }}

    node_workflow['stdout'] = 'std.out'
    node_workflow['stderr'] = 'std.err'

    if ';' in os.environ['PATH']:

        path = os.environ['PATH'].split(';')[1]

    else:

        path = os.environ['PATH']

    node_workflow['requirements'] = {'EnvVarRequirement' : {'envDef':
            {'PATH' : path,
            'OTB_APPLICATION_PATH' : os.environ['OTB_APPLICATION_PATH'],
            'PYTHONPATH': os.environ['PYTHONPATH']}
            }
            }
    
    cwl_main = dict()

    cwl_main['class'] = 'Workflow'

    cwl_main['id'] = 'main'


    cwl_main['inputs'] = main_inputs

    if 'input_reference' in signature.keys():
        cwl_main['requirements'] = [{'class': 'ScatterFeatureRequirement'}]

        cwl_main['steps'] = {'step1': {'scatter': scatter_input,
                                   'scatterMethod': 'dotproduct',
                                  'in': step_inputs,
                                   'out': ['results'],
                                   'run': '#node'
                                  }
                        }    

    else:
        cwl_main['steps'] = {'step1': {'in': step_inputs,
                                       'out': ['results'],
                                       'run': '#node'
                                  }
                        } 


    if 'input_reference' in signature.keys():

        cwl_main['outputs'] = [{'id': 'outss',
                                'outputSource': ['step1/results'],
                                'type': {'type': 'array',
                                        'items': {'type': 'array',
                                                    'items': 'File'}}}
                              ]


    else:

        cwl_main['outputs'] = [{'id': 'outss',
                                'outputSource': ['step1/results'],
                            'type': {'type': 'array',
                                     'items': 'File'}}]


    cwl['$graph'] = [node_workflow, cwl_main]

    if stdout:
        yaml.dump(cwl, sys.stdout, default_flow_style=False)
    else:
        with open(cwlfile, 'w') as file:
            yaml.dump(cwl, file, default_flow_style=False)

    logging.info('Done!')

    sys.exit(0)

if __name__ == '__main__':
    
    main()