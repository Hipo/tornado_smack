from setuptools import setup

setup(
    name='tornado-smack',
    version='1.0.4',
    long_description=__doc__,
    description='Syntactic sugar for tornado',
    url='https://github.com/Hipo/tornado_smack',
    packages=['tornado_smack'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['tornado', 'werkzeug'],
    entry_points = {
        'console_scripts': [
        ],
    }
)
