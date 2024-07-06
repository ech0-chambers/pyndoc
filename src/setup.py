from setuptools import setup

setup(
    name="pyndoc",
    version="0.1.0",
    packages=["pyndoc"],
    entry_points={"console_scripts": ["pyndoc = pyndoc.__main__:main"]},
    install_requires=[
        "panflute",
        "pyyaml",
        "pint",
    ],
)
