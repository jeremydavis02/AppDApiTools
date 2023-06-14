# AppDApiTools

This package is setup as a buildable and installable python project.

If you pull the repo, you need to do:
1. python3 -m pip install --upgrade pip (upgrade pip)
2. pip3 install build setuptools (install build and setuptools)
3. Do a python3 -m build (do package build)
It will build a tar.gz and a whl (wheel archive) in /dist

You can take either of those, though python suggest preference to the ".whl"
and do a:
4. pip3 install [tar | whl] into a python or virtual python environment.

It will lay down in the python/bin an executable called appd_api_tools as
the entry point.

The first execution will prompt to configure a config.ini that will be
written to the site-packages/AppDApiTools/config/ following the properties
in the config/sample-config.ini

appd_api_tools -h will give you details of commands but the general
structure is appd_api_tools [API Class] such as appd_api_tools Synthetics -h
etc

You can prompt to reconfigure the config.ini in an environment with 
appd_api_tools --config at anytime as well.