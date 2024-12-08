import os
import subprocess
from PIL import Image

def create_iconset():
    """Create iconset from a base PNG file"""
    # Ensure iconset directory exists
    if not os.path.exists('AppIcon.iconset'):
        os.makedirs('AppIcon.iconset')

    # Define icon sizes and their names
    icon_sizes = [
        (16, '16x16.png'),
        (32, '16x16@2x.png'),
        (32, '32x32.png'),
        (64, '32x32@2x.png'),
        (128, '128x128.png'),
        (256, '128x128@2x.png'),
        (256, '256x256.png'),
        (512, '256x256@2x.png'),
        (512, '512x512.png'),
        (1024, '512x512@2x.png')
    ]

    # Open and resize the base image for each size
    base_image = Image.open('icon.png')
    for size, name in icon_sizes:
        resized = base_image.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(f'AppIcon.iconset/icon_{name}')

    # Convert iconset to icns using iconutil
    subprocess.run(['iconutil', '-c', 'icns', 'AppIcon.iconset'])
    
    # Rename the output file to match what setup_mac.py expects
    if os.path.exists('AppIcon.icns'):
        os.rename('AppIcon.icns', 'app_icon.icns')

if __name__ == '__main__':
    create_iconset()
