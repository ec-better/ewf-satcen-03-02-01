
try:
    import urllib2
    urllib = urllib2
except ImportError:
    import urllib3
    urllib = urllib3

import base64
import numpy as np
import lxml.etree as etree
from shapely.wkt import loads


atom_template = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns:owc="http://www.opengis.net/owc/1.0" xmlns="http://www.w3.org/2005/Atom" xmlns:terradue="http://www.terradue.com">
  <entry>
    <identifier xmlns="http://purl.org/dc/elements/1.1/"/>
    <title type="text"/>
    <summary type="html"/>
    <author>
      <name>Terradue</name>
      <uri>https://www.terradue.com</uri>
      <email>support@terradue.com</email>
    </author>
    <owc:offering xmlns:owc="http://www.opengis.net/owc/1.0" code="http://www.opengis.net/spec/owc-atom/1.0/req/wps">
      <owc:content type="application/vnd.docker.distribution.manifest.v1+json" href=""/>
      <owc:content type="application/cwl" href=""/>
      <owc:operation code="DescribeProcess">
        <owc:result type="text/xml">
          <ProcessDescription xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns="http://www.w3.org/2005/Atom" wps:processVersion="1.12" storeSupported="true" statusSupported="true">
            <ows:Identifier/>
            <ows:Title/>
            <ows:Abstract/>
            <DataInputs/>
            <ProcessOutputs>
              <Output>
                <ows:Identifier>result_osd</ows:Identifier>
                <ows:Title>OpenSearch Description to the Results</ows:Title>
                <ows:Abstract>OpenSearch Description to the Results</ows:Abstract>
                <ComplexOutput>
                  <Default>
                    <Format>
                      <MimeType>application/opensearchdescription+xml</MimeType>
                    </Format>
                  </Default>
                  <Supported>
                    <Format>
                      <MimeType>application/opensearchdescription+xml</MimeType>
                    </Format>
                  </Supported>
                </ComplexOutput>
              </Output>
              <Output>
                <ows:Identifier>job_ows</ows:Identifier>
                <ows:Title>Job OWS info</ows:Title>
                <ows:Abstract>Wps job info as OWS Context (T2 internal)</ows:Abstract>
                <ComplexOutput>
                  <Default>
                    <Format>
                      <MimeType>application/atom+xml</MimeType>
                    </Format>
                  </Default>
                  <Supported>
                    <Format>
                      <MimeType>application/atom+xml</MimeType>
                    </Format>
                  </Supported>
                </ComplexOutput>
              </Output>
            </ProcessOutputs>
          </ProcessDescription>
        </owc:result>
      </owc:operation>
    </owc:offering>
  </entry>
</feed>
"""



class Atom(object):
    """class Atom"""

    tree = None
    root = None
    entry = None

    def __init__(self, root):
        self.root = root
        self.tree = root
        self.links = self.root.xpath('/a:feed/a:entry/a:link', namespaces={'a':'http://www.w3.org/2005/Atom'})
        entries = self.root.xpath('/a:feed/a:entry', namespaces={'a':'http://www.w3.org/2005/Atom'})
        if entries:
            self.entry = entries[0]

    @staticmethod
    def from_template(template=None):
        """Create an atom with 1 entry from template"""
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(template.encode('utf-8'), parser)
        return Atom(tree)

    def set_content_href(self, offering_code, content_type, href):
        """get content element"""

        content = self.root.xpath('/a:feed/a:entry/b:offering[@code="{0}"]/b:content[@type="{1}"]'.format(offering_code, content_type),
                               namespaces={'a':'http://www.w3.org/2005/Atom',
                                           'b':'http://www.opengis.net/owc/1.0'})
        
        content[0].attrib['href'] = href

    def set_process_identifier(self, offering_code, process_identifier):
        """get the output of the WPSExecute request"""

        elem = self.root.xpath('/a:feed/a:entry/b:offering[@code="{0}"]/b:operation[@code="DescribeProcess"]\
        /b:result/a:ProcessDescription/e:Identifier'.format(offering_code),
                               namespaces={'a':'http://www.w3.org/2005/Atom',
                                           'b':'http://www.opengis.net/owc/1.0',
                                           'c':'http://www.opengis.net/wps/1.0.0',
                                           'dc':'http://purl.org/dc/elements/1.1/',
                                           'e':'http://www.opengis.net/ows/1.1'})
        elem[0].text = process_identifier

    def set_process_title(self, offering_code, process_title):
        """get the output of the WPSExecute request"""

        elem = self.root.xpath('/a:feed/a:entry/b:offering[@code="{0}"]/b:operation[@code="DescribeProcess"]\
        /b:result/a:ProcessDescription/e:Title'.format(offering_code),
                               namespaces={'a':'http://www.w3.org/2005/Atom',
                                           'b':'http://www.opengis.net/owc/1.0',
                                           'c':'http://www.opengis.net/wps/1.0.0',
                                           'dc':'http://purl.org/dc/elements/1.1/',
                                           'e':'http://www.opengis.net/ows/1.1'})
        elem[0].text = process_title

    def set_process_abstract(self, offering_code, process_abstract):
        """get the output of the WPSExecute request"""

        elem = self.root.xpath('/a:feed/a:entry/b:offering[@code="{0}"]/b:operation[@code="DescribeProcess"]\
        /b:result/a:ProcessDescription/e:Abstract'.format(offering_code),
                               namespaces={'a':'http://www.w3.org/2005/Atom',
                                           'b':'http://www.opengis.net/owc/1.0',
                                           'c':'http://www.opengis.net/wps/1.0.0',
                                           'dc':'http://purl.org/dc/elements/1.1/',
                                           'e':'http://www.opengis.net/ows/1.1'})
        elem[0].text = process_abstract


    def add_data_input(self, offering_code, param):
        
        # <LiteralData>
        #    <ows:DataType ows:reference="xs:string" xmlns:ows="http://www.opengis.net/ows/1.1" />
        #    <ows:AllowedValues xmlns:ows="http://www.opengis.net/ows/1.1">
        #        <ows:Value>COMMA</ows:Value>
        #        <ows:Value>TAB</ows:Value>
        #        <ows:Value>SPACE</ows:Value>
        #    </ows:AllowedValues>
        #    <DefaultValue>COMMA</DefaultValue>
        # </LiteralData>

        # <LiteralData>
        #     <ows:DataType ows:reference="xs:anyURI" xmlns:ows="http://www.opengis.net/ows/1.1" />
        #     <ows:AnyValue xmlns:ows="http://www.opengis.net/ows/1.1" />
        # </LiteralData>


        ns = {'a':'http://www.w3.org/2005/Atom',
            'b':'http://www.opengis.net/owc/1.0',
            'c':'http://www.opengis.net/wps/1.0.0',                 
            'd':'http://www.opengis.net/ows/1.1'}

        new_input = etree.Element('{http://www.opengis.net/wps/1.0.0}Input')

        if 'min_occurs' in param.keys():
            new_input.attrib['minOccurs'] = str(param['min_occurs'])

        if 'max_occurs' in param.keys():
            new_input.attrib['max_occurs'] = str(param['max_occurs'])

        # ows:Identifier
        identifier = etree.Element('{http://www.opengis.net/ows/1.1}Identifier')
        identifier.text = param['identifier']
        new_input.append(identifier)

        # ows:Title
        title = etree.Element('{http://www.opengis.net/ows/1.1}Title')
        title.text = param['title']
        new_input.append(title)

        # ows:Abstract
        abstract = etree.Element('{http://www.opengis.net/ows/1.1}Abstract')
        abstract.text = param['abstract']
        new_input.append(abstract)

        # LiteralData
        literal_data = etree.Element('{http://www.opengis.net/wps/1.0.0}LiteralData')
        new_input.append(literal_data)

        # ows:DataType
        dt = etree.Element('{http://www.opengis.net/ows/1.1}DataType')
        if 'data_type' in param.keys():
            dt.text = param['data_type']
        else:
            dt.text = 'string'
        literal_data.append(dt)

        # ows:AnyValue
        literal_data.append(etree.Element('{http://www.opengis.net/ows/1.1}AnyValue'))

        # DefaultValue
        default_value = etree.Element('{http://www.opengis.net/wps/1.0.0}DefaultValue')
        if 'default_value' in param.keys():
            default_value.text = str(param['default_value'])
        literal_data.append(default_value)

        elem = self.root.xpath('/a:feed/a:entry/b:offering[@code="{0}"]/b:operation[@code="DescribeProcess"]\
        /b:result/a:ProcessDescription'.format(offering_code),
                            namespaces={'a':'http://www.w3.org/2005/Atom',
                                        'b':'http://www.opengis.net/owc/1.0',
                                        'c':'http://www.opengis.net/wps/1.0.0',
                                        'dc':'http://purl.org/dc/elements/1.1/',
                                        'e':'http://www.opengis.net/ows/1.1'})[0]
        try:
            elem.find('a:DataInputs/a:Input', namespaces=ns).addnext(new_input)
        except AttributeError:
            elem.find('a:DataInputs', namespaces=ns).append(new_input)

        return True


    def set_identifier(self, identifier):
        """Set first atom entry identifier"""

        el_identifier = self.root.xpath('/a:feed/a:entry/d:identifier',
                                        namespaces={'a':'http://www.w3.org/2005/Atom',
                                                    'd':'http://purl.org/dc/elements/1.1/'})

        el_identifier[0].text = identifier

    

    def set_title(self, text):
        """Set first atom entry title text"""

        el_title = self.root.xpath('/a:feed/a:entry/a:title',
                                   namespaces={'a':'http://www.w3.org/2005/Atom'})

        el_title[0].text = text

    def set_summary(self, text):
        """set summary text"""

        summaries = self.root.xpath('/a:feed/a:entry/a:summary',
                                    namespaces={'a':'http://www.w3.org/2005/Atom'})

        if not summaries:
            summary = self.get_summary(create=True)
        else:
            summary = summaries[0]

        summary.text = text

    
    def to_string(self, pretty_print=True):
        """convert to string"""

        return etree.tostring(self.tree, pretty_print=pretty_print)

    