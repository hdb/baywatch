from setuptools import setup

with open("readme.md", "r") as fh:
    long_description = fh.read()

exec(open('baywatch/version.py').read())

setup(
    name = 'bay-watch',
    version = __version__,
    description = 'todo',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author = 'Hudson Bailey',
    author_email = 'hudsondiggsbailey@gmail.com',
    url="https://github.com/hdb/baywatch",
    packages = ['baywatch'],
    package_data = {
        'baywatch': ['data/*.json', 'data/*.txt']
    },
    scripts=['bin/baywatch'],
    install_requires = [
        'requests>=2.27.1',
        'textual==0.1.17',
        'textual_inputs==0.2.5',
        'ck-widgets==0.2.0',
        'pyfiglet>=0.8.post1',
        'transmission-rpc==3.3.0',
        'pyperclip>=1.8.2',
    ],
    license='MIT',
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Topic :: Communications :: File Sharing",
    ),
)
