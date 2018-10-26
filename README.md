Traumatic Brain Injury (TBI) Radiologic Imaging Common Data Element Extrator
===================================================================================

The package is maintained by Margaret Mahan at the University of Minnesota


Installation
-------------

Download or fork project on GitHub. Where you place the project will be the ``root_path``.

Using Anaconda, the data science platform in Python, create an enviroment using the yaml file.

``cd root_path/scipts``

``conda env create -f tbi_cde_env.yml``

This will create an environment with the required Python packages.

To alias your environment for ease of use:

``CONDA_ENVS=<enter path to environments>``

	For example: /home/username/anaconda/envs

``SCRIPT_ENV=$CONDA_ENVS/tbi_cde_env``

``PYTHON=$SCRIPT_ENV/bin/python3.6``

Download and install spaCy model

``$PYTHON -m spacy download en``


Tutorials
----------

For using .ipynb use Jupyter

``JUPYTER=$SCRIPT_ENV/bin/jupyter-notebook``

For using .py use Spyder

``SPYDER=$SCRIPT_ENV/bin/spyder``
