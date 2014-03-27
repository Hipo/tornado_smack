from setuptools import setup

setup(
    name='tornado-smack',
    version='1.0.3',
    long_description=__doc__,
    packages=['tornado_smack'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['tornado', 'werkzeug'],
    entry_points = {
        'console_scripts': [
        ],
    }
)
