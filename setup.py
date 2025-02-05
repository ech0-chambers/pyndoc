from setuptools import setup

setup(
    name="pyndoc",
    version="0.1.5",
    packages=["pyndoc"],
    entry_points={"console_scripts": ["pyndoc = pyndoc.__main__:main"]},
    install_requires=[
        "panflute",
        "pyyaml",
        "pint",
    ],
    package_data = {
        "pyndoc": ["filter.py"]
    },
    include_package_data=True,
)
