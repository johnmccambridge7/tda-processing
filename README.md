
# TDA Processing App
<img width="1714" alt="Screenshot 2025-02-23 at 11 01 22 PM" src="https://github.com/user-attachments/assets/a934d90e-e85b-4e11-811b-a74b07232974" />

[![Python 3.7+](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

High-performance microscopy image processing application for `.lsm` and `.czi` formats. Implements automated channel processing with histogram matching and reference-based normalization.

## Features

- Batch processing of microscopy image files
- Automated channel processing:
  - Reference channel selection via SNR optimization
  - Histogram matching for intensity normalization
  - Median filtering for noise reduction
- Real-time processing previews
- Metadata extraction and scaling parameter handling
- Progress tracking with detailed status updates

## Installation

### Install from Source (For Developers)
```bash
# Clone repository
git clone https://github.com/johnmccambridge7/tda-processing.git
cd tda-processing

# Create virtual environment
python3 -m venv venv #may be python instead of python3
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

## Usage

### For Development Installation
```bash
# From the repository root
python3 -m tda_processing_app.main #may be python instead of python3
```

### Processing Workflow

1. Load images:
   - Select directory for batch processing
   - Load single file
   - Drag and drop supported files

2. Configure parameters:
   - Scaling factors (x, y, z)
   - Resolution
   - Microscope-specific settings

3. Process images:
   - Real-time preview of channel processing
   - Progress monitoring
   - Output validation

## Technical Details

### Project Structure
```
tda-processing-app/
├── main.py           # PyQt5 application entry point
├── functions.py      # Image processing core functions
├── constants.py      # Configuration and parameters
└── requirements.txt  # Python dependencies
```

### Key Components

- **Channel Processing**: Implements SNR-based reference selection and histogram matching
- **Metadata Handling**: Extracts and applies microscope-specific parameters
- **UI Framework**: PyQt5-based interface with real-time preview capabilities
- **Output Generation**: Multi-channel TIFF generation with metadata preservation

## Development

Run tests:
```bash
python -m pytest tests/
```

## License

MIT License - See [LICENSE](LICENSE)

## Issues & Support

[GitHub Issues](https://github.com/johnmccambridge7/tda-processing-app/issues)
