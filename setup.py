import setuptools


with open("README.md", "r") as readme_file:
    long_description = readme_file.read()


tests_require = ["pytest", "pytest-cov", "pre-commit"]


setuptools.setup(
    name="pytest-split",
    use_scm_version=dict(write_to="src/pytest_split/_version.py"),
    author="Jerry Pussinen",
    author_email="jerry.pussinen@gmail.com",
    description="Pytest plugin for splitting test suite based on test execution time",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jerry-git/pytest-split",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    setup_requires=["setuptools-scm"],
    tests_require=tests_require,
    install_requires=["pytest"],
    extras_require={"testing": tests_require},
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Framework :: Pytest",
    ],
    entry_points={"pytest11": ["pytest-split = pytest_split.plugin"]},
)
