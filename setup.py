"""
    tbi-extractor
"""
import setuptools

VERSION = "0.3.1"

with open("README.md", "r") as f:
    LONG_DESCRIPTION = f.read()

setuptools.setup(
    name="tbi-extractor",
    version=VERSION,
    description="tbiExtractor: Automated extraction of common data elements for traumatic brain injury.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    project_urls={"Source Code": "https://github.com/margaretmahan/tbiExtractor"},
    author="Margaret Mahan",
    author_email="mahan027@umn.edu",
    license="MIT",
    url="https://github.com/margaretmahan/tbiExtractor",
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: MIT",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.6.6",
    install_requires=[
        "pyConTextNLP==0.6.2.0",
        "networkx==1.11",
        "numpy>=1.15.0",
        "pandas>=0.23.4",
        "spacy==2.0.12",
    ],
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={"": ["data/*.tsv"]},
)
