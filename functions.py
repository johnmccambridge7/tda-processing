import numpy as np
from skimage.exposure import match_histograms
from scipy.ndimage import median_filter
from PIL import Image
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


def find_reference(channel):
    # Compute the mean and standard deviation along the z-axis
    means = np.mean(channel, axis=(1, 2))
    stds = np.std(channel, axis=(1, 2))

    # Compute the SNR for each z-slice
    snrs = 10 * np.log10(means / stds)

    # Find the index of the z-slice with the highest SNR
    reference = np.argmax(snrs)

    return reference


def process_channel(channel, channel_idx, progress_callback, preview_callback, reference_callback):
    reference = find_reference(channel)
    normalized = []

    if reference_callback is not None:
        # Convert the reference channel to QPixmap
        reference_image = Image.fromarray(channel[reference]).convert("RGB")
        reference_qimage = QImage(reference_image.tobytes(), reference_image.size[0], reference_image.size[1],
                                  QImage.Format_RGB888)
        reference_pixmap = QPixmap.fromImage(reference_qimage).scaled(180, 180, Qt.KeepAspectRatio)

        reference_callback(reference_pixmap)

    for image in channel:
        matched = match_histograms(image, channel[reference])
        normalized.append(median_filter(matched, size=3))

        # Create RGB image with the channel in the correct position based on channel_idx
        # Organize channels as: Green (idx 0), Red (idx 1), Blue (idx 2)
        color_image = np.zeros((channel[reference].shape[0], channel[reference].shape[1], 3), dtype=np.uint8)
        # Map input channel index to RGB position (R=0, G=1, B=2)
        color_map = {
            0: 0,  # First channel (0) goes to Red (0)
            1: 1,  # Second channel (1) goes to Green (1)
            2: 2   # Third channel (2) stays as Blue (2)
        }
        color_position = color_map.get(channel_idx, channel_idx)
        color_image[:, :, color_position] = normalized[-1]

        if preview_callback is not None:
            preview_image = Image.fromarray(color_image).convert("RGB")
            preview_qimage = QImage(preview_image.tobytes(), preview_image.size[0], preview_image.size[1],
                                    QImage.Format_RGB888)
            preview_pixmap = QPixmap.fromImage(preview_qimage).scaled(180, 180, Qt.KeepAspectRatio)

            preview_callback(preview_pixmap)

        # Update progress by calling the callback function
        progress_callback(1)

        # Removed percentage calculation to prevent 'NoneType' error
        # Ensure that progress_label_callback is handled externally based on progress updates

    # Use numpy array for efficient in-place operation
    normalized = np.array(normalized)

    return normalized

# before: 80.7450921535492s
# after: 47.067004919052124s
