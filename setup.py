import setuptools

setuptools.setup(
    name = "simplepup",
    version = "0.0.1",

    description = "PuppetDB access library and query tool",
    author = "Daniel Parks",
    author_email = "os-simplepup@demonhorse.org",
    url = "http://github.com/danielparks/simplepup",
    license = "BSD",
    long_description = open("README.rst").read(),

    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
    ],

    packages = [ "simplepup" ],
    install_requires = [
        "click",
        "paramiko",
        "requests"
    ],

    include_package_data = True,
    entry_points = {
        "console_scripts": [
            "simplepup = simplepup.cli.query:main"
        ]
    }
)
