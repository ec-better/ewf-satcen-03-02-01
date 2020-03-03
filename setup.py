from setuptools import setup, find_packages
from io import open

console_scripts = """
[console_scripts]
{1}={0}.ades.cli:main
run-node-1={0}.ades.run:main
app-gen={0}.ades.app_descriptor:main
cwl-gen={0}.ades.cwl:main
ows-gen={0}.ades.owscontext:main""".format(find_packages('src')[0],
                                           find_packages('src')[0].replace('_', '-'))

setup(entry_points=console_scripts,
      packages=find_packages(where='src'),
      package_dir={'': 'src'}) 