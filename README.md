# Enron Email Dataset to Neo4j

This project helps you import the Enron email dataset into a Neo4j graph database for the App Dev GDIT/Praxis project.
# Setup

1. ## Setup Git LFS and clone the repository
If you're on Mac, you can install Git LFS using Homebrew:
```bash
brew install git-lfs
```
If you're on Windows, git-lfs comes with Git for Windows.

Then, initialize git lfs on your user account:
```bash
git lfs install
```

Then, clone the repository OR pull the latest changes:
```bash
# cloning
git clone https://github.com/ADC-GDIT-Spring-2025/Backend.git   # for HTTPS
git clone git@github.com:ADC-GDIT-Spring-2025/Backend.git       # for SSH
git checkout origin/data-pipeline

# pulling latest changes
git pull
```
If you have git lfs setup, the parsed dataset from LFS should automatically be pulled with the normal changes.

If you want to ensure that the parsed dataset has been pulled from LFS, run:
```bash
git lfs pull
```

2. ## Install the required Python packages (recommended to install in a venv):
```bash
# create and activate the venv
python3 -m venv .venv

# or, if you want to use a specific python version like 3.11 (if you have it installed)
python3.11 -m venv .venv

# activate the venv
source .venv/bin/activate

# install the required packages
pip install -r requirements.txt
```


### Notes
the `util/deprecated` directory contains scripts that attempt to manually parse the Enron email dataset.
- `fetch_data.py` is a script to get the __raw enron email dataset__ from the internet, and it __should only be run once!__
- `old_parser.py` and `node_models.py` are files that attempt to parse the raw dataset into custom Python objects. These are __deprecated__ and __should not be used__, as we are now parsing the dataset into json files.
