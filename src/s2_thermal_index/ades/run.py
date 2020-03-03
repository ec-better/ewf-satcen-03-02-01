
from __future__ import absolute_import
import os
import sys
import inspect
import atexit
import uuid
import shutil
import importlib
import cioppy 
from setuptools.config import read_configuration
import io
from .data import get_references
from .signature import get_signature, log_param_update

# define the exit codes
SUCCESS = 0
ERR_RESOLUTION = 10
ERR_STAGEIN = 20
ERR_NO_OUTPUT = 30

ciop = cioppy.Cioppy()

# add a trap to exit gracefully
def clean_exit(exit_code):

    log_level = 'INFO'
    
    if exit_code != SUCCESS:
        log_level = 'ERROR'  
   
    msg = {SUCCESS: 'Processing successfully concluded',
           ERR_RESOLUTION: 'Could not resolve product enclosure',
           ERR_STAGEIN: 'Could not stage-in product', 
           ERR_NO_OUTPUT: 'Missing output'}
 
    ciop.log(log_level, msg[exit_code])  
        
def create_data_path():
    
    data_path = os.path.join('/tmp',
                             'workspace-{}'.format(str(uuid.uuid4())), 
                             'data') 
    os.makedirs(data_path)
    
    return data_path
    
def create_runtime_dir():
    
    # create the unique folder for the execution results
    runtime_dir = os.path.join(ciop.tmp_dir,
                               str(uuid.uuid4()))    

    os.makedirs(runtime_dir)
    os.chdir(runtime_dir)
    
    return runtime_dir
    
def main():
       
    env_name = None
    
    mod = importlib.import_module(__package__)
    inspect.getargspec(mod.main)

    # read main() signature
    signature = get_signature(mod)
    
    # update the parameter values with the run parameters 
    for key in signature.keys():
    
        if key in ['input_identifier', 'input_identifiers', 'input_reference', 'input_reference_stack', 'service', 'data_path']:
            continue

        param_value = ciop.getparam(signature[key]['identifier'])
        
        log_param_update(signature, key, param_value)
                             
        signature[key]['value'] = param_value   
    
    
    # fan-in - if the key 'input_reference_stack' is available, it's a fan-in application
    if 'input_reference_stack' in signature.keys():
        
        ciop.log('INFO', 'Fan-in application')
        input_references = []
        
        # read the catalog references passed via stdin
        for reference in sys.stdin:
            ciop.log('INFO', reference.rstrip())
            input_references.append(reference.rstrip())

        # update the input_references values
        param_value = ','.join(input_references)
        
        log_param_update(signature, 'input_reference_stack', param_value)
        
        signature['input_reference_stack']['value'] = param_value
        
        # if the child app has the key data_path in the signature 
        # it expects to read the staged-in data there so do the stage-in
        if 'data_path' in signature.keys():

            data_path = create_data_path()
            
            # update the data_path values
            log_param_update(signature, 'data_path', data_path)
        
            signature['data_path']['value'] = data_path
            
            # stage-in
            retrieved, identifiers = get_references(input_references, 
                                                    data_path,
                                                    True)
          
        # create the unique folder for the execution results
        runtime = create_runtime_dir()
        ciop.log('INFO', 'Runtime directory is: {}'.format(runtime)) 
        
        try:
            
            updated_args = [signature[key] for key in inspect.getargspec(mod.main).args]

            mod.main(*updated_args)

        except: 
            
            raise
                
        # publish the results
        ciop.log('INFO', 'Publishing') 
        
        ciop.publish(runtime, metalink=True, recursive=True) 
                
    # one-to-one
    if 'input_reference' in signature.keys():
        
        ciop.log('INFO', 'Fan-out application')
        # Loops over all the inputs
        input_references = []
        for input_reference in sys.stdin:
            ciop.log('INFO', input_reference.rstrip())
            input_references.append(input_reference.rstrip())
    
        for input_reference in input_references:

            if 'data_path' in signature.keys():

                data_path = create_data_path()
            
                # update the data_path values
                log_param_update(signature, 'data_path', data_path)

                signature['data_path']['value'] = data_path

                # stage-in
                retrieved, identifier = get_references([input_reference], 
                                                       data_path,
                                                       True)
            
            log_param_update(signature, 'input_reference', input_reference)
            signature['input_reference']['value'] = input_reference
            
            # create the unique folder for the execution results
            runtime = create_runtime_dir()
               
            try:
                
                updated_args = [signature[key] for key in inspect.getargspec(mod.main).args]

                mod.main(*updated_args)

                # publish the results
                ciop.log('INFO', 'Publishing results') 
                ciop.publish(runtime,
                             metalink=True, 
                             recursive=True) 

                if 'data_path' in signature.keys(): 
                
                    shutil.rmtree(data_path)
            
            except: 
            
                raise
            
            
    sys.exit(0)
    
if __name__ == '__main__':
                     
    try:
        main()
    except SystemExit as e:
        if e.args[0]:
            clean_exit(e.args[0])
        raise
    else:
        atexit.register(clean_exit, 0)
