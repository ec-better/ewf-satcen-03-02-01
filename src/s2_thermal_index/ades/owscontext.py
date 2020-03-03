import click
import sys
import sys
import os 
from .atom import Atom
from .atom import atom_template
import lxml.etree as etree
import logging
import click
import pkg_resources
from .signature import get_signature
import importlib

@click.command()
@click.option('--docker', '-d')
@click.option('--cwlfile', '-c')
@click.option('--owsfile', '-o')
@click.option('--stdout', is_flag=True)
def main(docker, cwlfile, owsfile, stdout):
    
    mod = importlib.import_module(__package__)

    signature = get_signature(mod)
    
    ows_context = Atom.from_template(atom_template)
    
    ows_context.set_identifier('application_package_{}'.format(signature['service']['identifier'].replace('-', '_')))
    ows_context.set_title('Application package for {} '.format(signature['service']['title']))
    
    ows_context.set_summary('Application package {}'.format(signature['service']['abstract']))
    
    ows_context.set_process_identifier('http://www.opengis.net/spec/owc-atom/1.0/req/wps', signature['service']['identifier'])
    ows_context.set_process_title('http://www.opengis.net/spec/owc-atom/1.0/req/wps', signature['service']['title'])
    ows_context.set_process_abstract('http://www.opengis.net/spec/owc-atom/1.0/req/wps', signature['service']['abstract'])
    
    for key in signature.keys():
        
        if key in ['input_identifier', 'input_identifiers', 'service', 'data_path']:
            
            continue    
    
        ows_context.add_data_input('http://www.opengis.net/spec/owc-atom/1.0/req/wps', 
                                   signature[key])
    
    ows_context.set_content_href('http://www.opengis.net/spec/owc-atom/1.0/req/wps', 
                                 'application/cwl',
                                 cwlfile)

    ows_context.set_content_href('http://www.opengis.net/spec/owc-atom/1.0/req/wps', 
                                 'application/vnd.docker.distribution.manifest.v1+json',
                                 docker)
    
    
    if stdout:

        print('<?xml version="1.0" encoding="UTF-8"?>')
        print(etree.tostring(ows_context.root, pretty_print=True).decode())
    
    else:
        with open(owsfile, 'w') as file:
            
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write(etree.tostring(ows_context.root, 
                                      pretty_print=True).decode())

    sys.exit(0)

if __name__ == '__main__':
    
    main()