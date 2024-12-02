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

# TDA Processing App 🔬

<div align="center">

![TDA Processing App Logo](assets/logo.png)

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

*Advanced Microscopy Image Processing Made Simple*

[Getting Started](#getting-started) • [Documentation](#documentation) • [Contributing](#contributing) • [Support](#support)

</div>

## 🌟 Overview

TDA Processing App is a sophisticated yet user-friendly application designed for processing microscopy images, specifically optimized for `.lsm` and `.czi` file formats. Built with PyQt5 and powered by cutting-edge image processing algorithms, it streamlines the workflow of microscopy data analysis while maintaining scientific precision.

## ✨ Key Features

- 🖥️ **Modern Interface**: Sleek, intuitive GUI built with PyQt5
- 🚀 **High-Performance Processing**: Optimized algorithms for efficient image processing
- 📦 **Batch Processing**: Handle multiple files simultaneously
- 🎨 **Advanced Channel Processing**: 
  - Intelligent histogram matching
  - Automated reference channel selection
  - Real-time preview capabilities
- 📊 **Smart Metadata Handling**: Automatic extraction and utilization of image metadata
- 📈 **Progress Tracking**: Detailed visual feedback on processing status
- 🎯 **Precision Controls**: Fine-tuned scaling and processing parameters

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- Git (for cloning the repository)
- Operating System: Windows 10+, macOS 10.14+, or Linux

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/tda-processing-app.git
   cd tda-processing-app
   ```

2. **Set Up Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Documentation

### Basic Usage

1. **Launch the Application**
   ```bash
   python main.py
   ```

2. **Load Images**
   - Use "Browse Directory" for batch processing
   - Use "Load Image" for single file processing
   - Drag and drop files directly into the application

3. **Configure Processing**
   - Adjust scaling parameters if needed
   - Select reference channels
   - Configure output preferences

4. **Process Images**
   - Monitor progress in real-time
   - Preview results
   - Access processed files in the output directory

### Advanced Features

- **Batch Processing**: Process entire directories of images while maintaining consistent parameters
- **Channel Management**: Fine-tune individual channel processing with preview capabilities
- **Metadata Integration**: Automatic scaling and parameter adjustment based on image metadata
- **Custom Output**: Flexible output options with configurable file naming and directory structure

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

- Code Style
- Development Setup
- Pull Request Process
- Bug Reports
- Feature Requests

## 🛠️ Development

### Project Structure
```
tda-processing-app/
├── main.py           # Application entry point
├── functions.py      # Core processing functions
├── constants.py      # Configuration constants
├── requirements.txt  # Dependencies
└── fonts/           # Custom UI fonts
```

### Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Dr. Penelope L. Tir - Project Lead
- John L. McCambridge - Core Developer
- The Scientific Imaging Community

## 📬 Support

- 📧 Email: support@tdaprocessing.org
- 💬 Issues: [GitHub Issues](https://github.com/yourusername/tda-processing-app/issues)
- 📚 Wiki: [Project Wiki](https://github.com/yourusername/tda-processing-app/wiki)

---
<div align="center">
Made with ❤️ by the TDA Processing Team
</div>
