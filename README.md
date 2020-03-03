## ewf-satcen-03-02-01

### Local build 

To build this application, the requirements are:

* conda=4.6.14
* conda build 3.18

The best solution for the compliance with these requirements is to create a dedicated environment and avoid adding module requirements for the application environment.

```bash
conda create -y -q -n build_env 
```

```bash
conda install -n build_env conda=4.6.14 conda-build cwl_runner -y -q
```

Now, in the root application folder (it contains the conda.recipe folder), build the application with:

```bash
<path to build_env>/bin/conda build .
```

Note: to find the path to <path to build_env> 

```bash
conda env list
```

Checking conda version:

```bash
$ /workspace/.conda/envs/build_env/bin/conda -V
conda 4.6.14
```

### Deployment dry-run

Create a dedicated environment named env_app

```bash
conda create -y -q -n env_app 
```

In the dedicated environment, install the application built previously with:

```bash
<path to build_env>/bin/conda install -n build_env -y -n env_app -c file://<path to local build channel> -c terradue -c defaults -c conda-forge <application module> 
```

Example:

```bash
/workspace/.conda/envs/build_env/bin/conda install -y -n env_app -c file:///workspace/.conda/envs/build_env/conda-bld -c terradue -c defaults -c conda-forge s2_gefolki_multitemporal
```

Activate the environment:

```bash
conda activate env_app 
```

Print the application help:

```bash
s2-gefolki-multitemporal --help
```

Test the Ellip application descriptor generation

```bash
app-gen --stdout 
```

Test the CWL generation

```bash
cwl-gen --stdout 
```

Test the OWS Context generation

```bash
ows-gen -c dummy -d dummy --stdout 
```

To remove the env_app environment, do:

```bash
conda remove -n env_app --all 
```

