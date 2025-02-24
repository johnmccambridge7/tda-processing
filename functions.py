import numpy as np
from scipy.ndimage import gaussian_filter, median_filter
from skimage.exposure import match_histograms
from skimage.morphology import skeletonize
from PIL import Image
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


def find_reference(channel, sigma=1, percentile=20, neurite_weight=1.0):
    """
    Selects the reference slice from a 3D channel by combining a robust SNR
    with a neurite score that favors slices containing elongated neuron strands.

    For each z-slice:
      - Apply a Gaussian filter to denoise.
      - Compute the background as the given percentile (default: 20th percentile).
      - Estimate noise via the median absolute deviation (MAD) scaled to std.
      - Compute SNR as (signal - background)/noise, where signal is the mean of pixels above background.
      - Create a binary mask by thresholding at (background + noise).
      - Skeletonize the mask to estimate the total length of elongated structures.
      - Normalize the skeleton length by the image area.
      - Compute a composite score as: composite = SNR + (neurite_weight * normalized_neurite_length)

    The slice with the highest composite score is chosen as the reference.
    """
    best_score = -np.inf
    best_index = 0

    for i in range(channel.shape[0]):
        # Convert slice to float and denoise
        slice_data = channel[i].astype(np.float64)
        denoised = gaussian_filter(slice_data, sigma=sigma)

        # Compute background and noise using robust statistics
        background = np.percentile(denoised, percentile)
        median_val = np.median(denoised)
        mad = np.median(np.abs(denoised - median_val))
        noise = mad * 1.4826  # Scale MAD to approximate std dev
        if noise < 1e-6:
            noise = 1e-6

        # Compute signal and SNR
        above_bg = denoised[denoised > background]
        signal = np.mean(above_bg) if above_bg.size > 0 else np.mean(denoised)
        snr = (signal - background) / noise

        # Compute neurite score:
        # Threshold the denoised image to get bright structures (neurites)
        thresh = background + noise  # This threshold can be tuned as needed
        binary = denoised > thresh

        # Skeletonize the binary mask to capture the elongated structure
        skeleton = skeletonize(binary)
        neurite_length = np.sum(skeleton)  # Total count of skeleton pixels
        norm_neurite_length = neurite_length / (denoised.shape[0] * denoised.shape[1])

        # Compute composite score
        composite_score = snr + neurite_weight * norm_neurite_length

        print(f"Slice {i}: SNR={snr:.2f}, neurite_length={neurite_length}, "
              f"normalized_neurite={norm_neurite_length:.4f}, composite={composite_score:.2f}")

        if composite_score > best_score:
            best_score = composite_score
            best_index = i

    print(f"Selected reference slice: {best_index} with composite score {best_score:.2f}")
    return best_index


def process_channel(channel, channel_idx, progress_callback, preview_callback, reference_callback):
    reference = find_reference(channel)
    normalized = []

    if reference_callback is not None:
        # Convert the reference slice to QPixmap for display
        reference_image = Image.fromarray(channel[reference]).convert("RGB")
        reference_qimage = QImage(reference_image.tobytes(), reference_image.size[0], reference_image.size[1],
                                  QImage.Format_RGB888)
        reference_pixmap = QPixmap.fromImage(reference_qimage).scaled(180, 180, Qt.KeepAspectRatio)
        reference_callback(reference_pixmap)

    for image in channel:
        matched = match_histograms(image, channel[reference])
        normalized_image = median_filter(matched, size=3)
        normalized.append(normalized_image)

        # Create an RGB image placing the normalized image into the correct channel position
        color_image = np.zeros((channel[reference].shape[0], channel[reference].shape[1], 3), dtype=np.uint8)
        # Map input channel index to RGB positions: 0->Red, 1->Green, 2->Blue
        color_map = {0: 0, 1: 1, 2: 2}
        color_position = color_map.get(channel_idx, channel_idx)
        color_image[:, :, color_position] = normalized_image

        if preview_callback is not None:
            preview_image = Image.fromarray(color_image).convert("RGB")
            preview_qimage = QImage(preview_image.tobytes(), preview_image.size[0], preview_image.size[1],
                                    QImage.Format_RGB888)
            preview_pixmap = QPixmap.fromImage(preview_qimage).scaled(180, 180, Qt.KeepAspectRatio)
            preview_callback(preview_pixmap)

        # Update progress by calling the callback function
        progress_callback(1)

    normalized = np.array(normalized)
    return normalized
