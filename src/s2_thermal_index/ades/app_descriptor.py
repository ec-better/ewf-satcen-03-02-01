import sys
import os
import lxml.etree as etree
import os
import inspect
import importlib
from .signature import get_signature
import click 

def app_descriptor(signature):

    version = '1.0'
    namespaces = dict()

    namespaces['xsi'] = 'http://www.w3.org/2001/XMLSchema-instance'
    
    for key, value in namespaces.items():
        etree.register_namespace(key, value)

    root = etree.Element('{{}}application'.format(namespaces['xsi']))
    root.attrib['id'] = 'application'
    
    job_templates = etree.SubElement(root, 'jobTemplates')
    
    job_template = etree.SubElement(job_templates, 'jobTemplate')
    job_template.attrib['id'] = 'job'
    
    se = etree.SubElement(job_template, 'streamingExecutable')
    se.text = '/application/job/run.sh'
    
    df = etree.SubElement(job_template, 'defaultParameters')
    
    for key in signature.keys():
        
        if key in ['input_reference', 'input_reference_stack', 'service', 'data_path']:
            
            continue

        param = etree.SubElement(df, 'parameter')
        param.attrib['id'] = signature[key]['identifier']
        param.attrib['title'] = signature[key]['title']
        param.attrib['abstract'] = signature[key]['abstract']
        param.attrib['scope'] = 'runtime'
        param.attrib['type'] = 'LiteralData'
        
        if 'maxOccurs' in signature[key].keys():
            
            param.attrib['maxOccurs'] = signature[key]['maxOccurs']
           
        if 'minOccurs' in signature[key].keys():
            
            param.attrib['minOccurs'] = signature[key]['minOccurs']
        
        if 'options' in signature[key].keys():
            options = etree.SubElement(param, 'options')
            
            for option_value in signature[key]['options'].split(','):
                option = etree.SubElement(options, 'option')
                option.text = option_value
                
            default = etree.SubElement(options, 'default')
            default.text = signature[key]['value']
        else:
            
            param.text = signature[key]['value']
            
    djc = etree.SubElement(job_template, 'defaultJobconf')
    
    conf_prop = etree.SubElement(djc, 'property')
    conf_prop.attrib['id'] = 'mapred.task.timeout'
    conf_prop.text = '10800000'
    
    if 'input_reference_stack' in signature.keys():
        
        conf_prop = etree.SubElement(djc, 'property')
        conf_prop.attrib['id'] = 'ciop.job.max.tasks'
        conf_prop.text = '1'
    
    workflow = etree.SubElement(root, 'workflow')
    for key in ['id', 'title', 'abstract']:
        try:
            workflow.attrib[key] = signature['service'][key]
        except KeyError:
            workflow.attrib[key] = signature['service']['identifier'] 
   
    wv =  etree.SubElement(workflow, 'workflowVersion')
    wv.text = '1.0'
    
    node = etree.SubElement(workflow, 'node')
    node.attrib['id'] = 'node'
    
    job = etree.SubElement(node, 'job') 
    job.attrib['id'] = 'job'
    
    sources = etree.SubElement(node, 'sources') 

    source = etree.SubElement(sources, 'source') 
    
    source.attrib['refid'] = 'string:list'
    source.attrib['scope'] = 'runtime'
    
    if 'input_reference_stack' in signature.keys():
        for key in ['id', 'title', 'abstract']:
            try:
                source.attrib[key] = signature['input_reference_stack'][key]
            except KeyError:
                source.attrib[key] = signature['input_reference_stack']['identifier']    

        
        source.text = signature['input_reference_stack']['value']
        
    if 'input_reference' in signature.keys():
        for key in ['id', 'title', 'abstract']:
            try:
                source.attrib[key] = signature['input_reference'][key]
            except KeyError:
                source.attrib[key] = signature['input_reference']['identifier']    

        
        source.text = signature['input_reference']['value']
    
    return root #etree.tostring(root, pretty_print=True)

@click.command()
@click.option('--descriptor', '-d')
@click.option('--stdout', is_flag=True)
def main(descriptor, stdout):
    
    app_descriptor_file = descriptor 
    
    mod = importlib.import_module(__package__)
    inspect.getargspec(mod.main)

    # read main() signature
    signature = get_signature(mod)

    print(signature)

    if stdout:
        
        print('<?xml version="1.0" encoding="UTF-8"?>')
        print(etree.tostring(app_descriptor(signature), pretty_print=True).decode())
    
    else:
        
        with open(descriptor, 'w') as file:

            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write(etree.tostring(app_descriptor(signature), pretty_print=True).decode())

    sys.exit(0)

if __name__ == '__main__':
   
    main()
    