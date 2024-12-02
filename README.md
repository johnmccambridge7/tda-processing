# TDA Processing App

![TDA Processing App Logo](path/to/logo.png) *(Replace with actual logo if available)*

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setting Up the Virtual Environment](#setting-up-the-virtual-environment)
  - [Installing Dependencies](#installing-dependencies)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Introduction

TDA Processing App is a powerful and user-friendly application designed for processing microscopy images, specifically `.lsm` and `.czi` file formats. Leveraging the capabilities of PyQt5 for its graphical interface and robust image processing libraries, this application allows users to efficiently handle, process, and save their microscopy data with ease.

## Features

- **User-Friendly Interface**: Intuitive GUI built with PyQt5 for easy navigation and operation.
- **Batch Processing**: Process multiple image files simultaneously, saving time and effort.
- **Channel Processing**: Handle individual image channels with options for normalization and matching histograms.
- **Preview & Reference**: Real-time previews of image channels and reference channels for better accuracy.
- **Metadata Extraction**: Automatically extracts and utilizes metadata from image files for accurate scaling and processing.
- **Progress Tracking**: Monitor processing progress with detailed progress bars and status updates.
- **Custom Fonts & Styling**: Enhanced UI aesthetics with custom fonts and color schemes.

## Installation

### Prerequisites

- **Python 3.7 or higher**: Ensure you have Python installed on your machine. You can download it from [Python's official website](https://www.python.org/downloads/).
- **Git**: Required for cloning the repository. Download from [Git's official website](https://git-scm.com/downloads).

### Setting Up the Virtual Environment

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/tda-processing-app.git
   cd tda-processing-app
   ```

2. **Create a Virtual Environment**

   It's recommended to use a virtual environment to manage dependencies.

   ```bash
   python3 -m venv venv
   ```

3. **Activate the Virtual Environment**

   - **Windows**

     ```bash
     venv\Scripts\activate
     ```

   - **macOS and Linux**

     ```bash
     source venv/bin/activate
     ```

### Installing Dependencies

With the virtual environment activated, install the required packages using `pip`:

