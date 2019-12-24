import setuptools

py_classifiers = [f"Programming Language :: Python :: {version}" for version in ["3.7"]]


extras_require = {
    "test": [
        "factory-boy>=2.12.0,<3.0.0",
        "pytest>=4.6.3,<5.0.0",
        "pytest-xdist>=1.30.0",
        "pytest-trio>=0.5.2",
    ],
    "lint": [
        "mypy>=0.701,<1.0",
        "mypy-protobuf==1.15",
        "black==19.3b0",
        "isort==4.3.21",
        "flake8>=3.7.7,<4.0.0",
        "flake8-bugbear",
    ],
    "dev": [
        "bumpversion>=0.5.3,<1",
        "docformatter",
        "setuptools>=36.2.0",
        "tox>=3.13.2,<4.0.0",
        "twine",
        "wheel",
    ],
}

extras_require["dev"] = (
    extras_require["test"] + extras_require["lint"] + extras_require["dev"]
)


with open("./README.md") as readme:
    long_description = readme.read()


setuptools.setup(
    name="libp2p",
    description="libp2p implementation written in python",
    version="0.1.2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    maintainer="The Ethereum Foundation",
    maintainer_email="snakecharmers@ethereum.org",
    url="https://github.com/ethereum/py-libp2p",
    license="MIT/APACHE2.0",
    platforms=["unix", "linux", "osx"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
    ]
    + py_classifiers,
    python_requires=">=3.7,<4",
    install_requires=[
        "pycryptodome>=3.9.2,<4.0.0",
        "base58>=1.0.3,<2.0.0",
        "pymultihash>=0.8.2",
        "multiaddr>=0.0.8,<0.1.0",
        "rpcudp>=3.0.0,<4.0.0",
        "lru-dict>=1.1.6",
        "protobuf>=3.10.0,<4.0.0",
        "coincurve>=10.0.0,<11.0.0",
        "fastecdsa==1.7.4",
        "pynacl==1.3.0",
        "trio-asyncio>=0.10.0",
        "trio>=0.13.0",
        "async-service>=0.1.0a2,<0.2.0",
        "async-exit-stack==1.0.1",
    ],
    extras_require=extras_require,
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    zip_safe=False,
    keywords="libp2p p2p",
)
