# Dorftipster

**Dorfromantik tile placement helper**

This application was designed to support you in playing the game Dorfromantik.
It will boost the playing experience, especially in the later game as the suggestions will help you make good decisions and will ultimately allow you to continue your session for a very long time.

![Game example](img/game_example.png)
![Game example tile placement helper](img/game_example_helper.png)

Key features:
- Allows you to easily mirror the actual game in the tile placement helper application
- Makes useful suggestions as to where to place the next tile
- Considers groups and many other criteria in order to make a good suggestion
- Allows to "watch" coordinates when you would like to focus on placing on specific positions
- Gives you many additional infos that will benefit your game and decision making

# Table of Contents
1. [Installation](#installation)
    - [System-level dependencies](#system-level-dependencies)
    - [Installing Python and pip](#installing-python-and-pip)
    - [Installing Dependencies](#installing-dependencies)
    - [Running the Application](#running-the-application)
2. [How to: Detailed information](#how-to-detailed-information)

# Installation
## System-level dependencies

Before running the project, make sure you have the following system-level dependencies installed:

### Ubuntu/Debian
```
sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx libegl1-mesa libxkbcommon0 libdbus-1-3
```

### macOS and Windows
On Windows and macOS, OpenGL should be available by default.

## Installing Python and pip

**Please note:** The project requires Python 3.8 or higher

### Windows
1. Download Python 3.13 from [python.org](https://www.python.org/downloads/) (please note that Python >= 3.14 is not yet supported)
2. Run the installer and check "Add Python to PATH" option.
3. Complete the installation.

### macOS
1. Install Homebrew if not already installed:
    `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. Install Python:
    `brew install python`

### Linux
1. Update package list:
    `sudo apt update`
2. Install Python and pip:
    `sudo apt install python3-full python3-pip`

## Installing Dependencies

Open a terminal and navigate to the project directory:
    `cd path/to/dorftipster`

Create a virtual environment within python (in the project directory) and activate it:

```
python -m venv .venv
source .venv/bin/activate
```

Ensure latest version of pip:

```
python -m pip install --upgrade pip
```

Install the required packages:
    `pip install -r requirements.txt`

## Running the Application

Run the application from the project directory:
    `python -m src`

(If there is no symlink for `python`, use `python3` instead)

# How to: Detailed information
For more detailed information on the user interface, how to use Dorftipster and how ratings are computed, see the [Wiki](https://github.com/nikghub/dorftipster/wiki/How-to) page.
