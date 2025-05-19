"""
Setup script for the bestehorn-llm-manager package.
"""
from setuptools import setup, find_packages

setup(
    name="bestehorn-llm-manager",
    version="0.1.0",
    description="A robust wrapper for AWS Bedrock's Converse API with multi-region and CRIS support by Markus Bestehorn",
    author="Markus Bestehorn",
    author_email="markus.bestehorn@googlemail.com",
    url="https://www.linkedin.com/in/markus-bestehorn/",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.26.0",
        "botocore>=1.29.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    project_urls={
        "LinkedIn": "https://www.linkedin.com/in/markus-bestehorn/",
    },
)
