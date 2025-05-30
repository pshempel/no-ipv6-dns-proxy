#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

def read_readme():
    if os.path.exists('README.md'):
        with open('README.md', 'r', encoding='utf-8') as f:
            return f.read()
    return "DNS CNAME Flattening Proxy"

def read_requirements():
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return ['twisted>=18.0.0', 'pyopenssl>=18.0.0', 'service-identity>=18.1.0']

setup(
    name='dns-proxy',
    version='1.0.0',
    description='DNS CNAME Flattening Proxy',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='DNS Proxy Team',
    author_email='admin@example.com',
    url='https://github.com/example/dns-proxy',
    
    packages=find_packages(),
    include_package_data=True,
    
    install_requires=read_requirements(),
    
    entry_points={
        'console_scripts': [
            'dns-proxy=dns_proxy.main:main',
        ],
    },
    
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: Name Service (DNS)',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
    ],
    
    python_requires='>=3.9',
)
