from setuptools import setup, find_packages

with open('README.rst') as f:
    readme_file = f.read()

with open('LICENSE') as f:
    license_file = f.read()

setup(
    name='dispersy',
    version='1.0.0',
    description='A system to simplify the design of distributed communities',
    long_description=readme_file,
    author='Tribler',
    url='https://github.com/Tribler/dispersy',
    license=license_file,
    packages=find_packages(exclude=('tests', 'docs'))
)
