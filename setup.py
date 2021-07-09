from distutils.core import setup
from pathlib import Path

_version = (Path(__file__).parent/'VERSION').read_text()

setup(
    name = 'sepal_ui',      
    packages = [
        'sepal_ui', 
        'sepal_ui.scripts', 
        'sepal_ui.frontend', 
        'sepal_ui.sepalwidgets', 
        'sepal_ui.aoi', 
        'sepal_ui.message',
        'sepal_ui.mapping', 
        'sepal_ui.translator',
        'sepal_ui.model'
    ],   
    package_data={'sepal_ui': ['scripts/*.csv', 'scripts/*.md', 'message/*.json', 'bin/module_factory']},
    version = _version,   
    license='MIT',        
    description = 'Wrapper for ipyvuetify widgets to unify the display of voila dashboards in SEPAL platform',
    long_description = open('README.rst').read(),
    long_description_content_type = 'text/x-rst',
    author = 'Pierrick Rambaud',                   
    author_email = 'pierrick.rambaud49@gmail.com',  
    url = 'https://github.com/12rambau/sepal_ui',
    download_url = f'https://github.com/12rambau/sepal_ui/archive/v_{_version}.tar.gz',
    keywords = ['UI', 'Python', 'widget', 'sepal'], 
    install_requires=[
        'haversine',
        'ipyvuetify',
        'geemap',
        'earthengine-api',
        'markdown',
        'xarray_leaflet',
        'shapely',
        'geopandas',
        'pandas',
        'deepdiff',
        'colorama',
        'Deprecated',
        'Unidecode',
        'natsort'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',  
        'Programming Language :: Python :: 3.6',
    ],
)