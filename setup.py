from setuptools import setup, find_packages

classifiers = [
    "Development Status :: 1 - Planning",
    "Intended Audience :: Financial and Insurance Industry",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3"
]

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open('LICENSE.md', "r", encoding="utf-8") as f:
    license = f.read()

setup(
    name="moonlander",
    version="0.0.1",
    description="stock trading",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='',
    author='Rohit Agrawal',
    author_email="rohitagrawalofficialmail@gmail.com",
    license=license,
    classifiers=classifiers,
    keywords="",
    test_suite="tests",
    packages=find_packages(exclude=('tests', 'docs')),
    python_requires=">=3.6",
    install_requires=['']
)