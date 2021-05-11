#!/usr/bin/env python3
import setuptools

setuptools.setup(
    name="svgtinyconverter",
    version="0.0.1",
    description="SVG to SVG Tiny Converter",
    license="AGPLv3+",
    author="Jan Holthuis",
    author_email="holthuis.jan@googlemail.com",
    url='https://github.com/Holzhaus/svgtinyconverter',
    platforms=('Any'),
    install_requires=['tinycss>=0.4'],
    packages=setuptools.find_packages(),
    zip_safe=True,
    entry_points={
        'console_scripts': [
           'svgtinyconverter = svgtinyconverter:main'
        ]},
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Pre-processors",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Utilities"
    ],
    keywords="svg tiny converter"
)
