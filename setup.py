"""
Setup configuration for DMUR Analysis package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('pytest') and not line.startswith('black'):
            # Only include runtime dependencies, not dev dependencies
            if line.split('>=')[0] in [
                'numpy', 'pandas', 'scikit-learn', 'scipy', 'shapely', 
                'geopandas', 'matplotlib', 'folium', 'requests', 'click', 
                'pyyaml', 'python-dotenv'
            ]:
                requirements.append(line)

# Development dependencies
dev_requirements = [
    'pytest>=6.0.0',
    'pytest-cov>=3.0.0',
    'pytest-mock>=3.6.0',
    'black>=22.0.0',
    'isort>=5.10.0',
    'flake8>=4.0.0',
    'mypy>=0.950',
    'sphinx>=4.0.0',
    'sphinx-rtd-theme>=1.0.0',
    'sphinxcontrib-napoleon>=0.7'
]

setup(
    name="dmur-analysis",
    version="1.0.0",
    author="DMUR Analysis Team",
    author_email="contact@dmur-analysis.com",
    description="Downtown Mixed-Use Readiness Analysis Toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/dmur-analysis",
    project_urls={
        "Bug Tracker": "https://github.com/your-org/dmur-analysis/issues",
        "Documentation": "https://dmur-analysis.readthedocs.io/",
        "Source Code": "https://github.com/your-org/dmur-analysis",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "sphinxcontrib-napoleon>=0.7"
        ],
        "test": [
            "pytest>=6.0.0",
            "pytest-cov>=3.0.0",
            "pytest-mock>=3.6.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "dmur-fetch=dmur_analysis.cli.fetch_businesses:main",
            "dmur-analyze=dmur_analysis.cli.analyze_downtown:main",
            "dmur-score=dmur_analysis.cli.calculate_dmur:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "urban-planning", "gis", "downtown-analysis", "mixed-use", 
        "real-estate", "openstreetmap", "spatial-analysis", "dmur"
    ],
)