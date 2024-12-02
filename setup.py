from setuptools import setup, find_packages

setup(
    name='tda-processing-app',
    version='1.0.0',
    description='A PyQt5 Application for TDA Processing',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'fonts': ['SF-Pro-Regular.otf', 'SF-Pro.ttf'],
    },
    install_requires=[
        'contourpy==1.2.1',
        'customtkinter==5.2.2',
        'cycler==0.12.1',
        'darkdetect==0.8.0',
        'dearpygui==2.0.0',
        'fonttools==4.53.1',
        'imageio==2.35.1',
        'kiwisolver==1.4.5',
        'lazy_loader==0.4',
        'matplotlib==3.9.2',
        'networkx==3.3',
        'numpy==2.1.0',
        'packaging==24.1',
        'pillow==10.4.0',
        'pyparsing==3.1.4',
        'PyQt5==5.15.11',
        'PyQt5-Qt5==5.15.15',
        'PyQt5_sip==12.15.0',
        'python-dateutil==2.9.0.post0',
        'scikit-image==0.24.0',
        'scipy==1.14.1',
        'six==1.16.0',
        'tifffile==2024.8.24',
        'tkinterdnd2==0.4.2',
    ],
    entry_points={
        'gui_scripts': [
            'tda-processing-app=main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',  # Update if you choose a different license
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
