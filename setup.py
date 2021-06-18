from setuptools import setup, find_packages

classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Financial and Insurance Industry",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Programming Language :: Python :: 3.6"
]

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open('LICENSE', "r", encoding="utf-8") as f:
    _license = f.read()

setup(
    name="peepop",
    version="0.0.1",
    description="Create automated cryptocurrency bots that trade for you while you sleep",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='',
    author='Rohit Agrawal',
    author_email="rohitagrawalofficialmail@gmail.com",
    license=_license,
    classifiers=classifiers,
    keywords="",
    packages=find_packages(exclude=('tests', 'docs')),
    python_requires=">=3.6",
    install_requires=['']
)