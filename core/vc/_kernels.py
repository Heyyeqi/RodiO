"""
Internal kernel helpers — pure numpy implementations of Gaussian blur
and morphological operations used across the VC Layer.

No scipy dependency, no GPU, no file I/O.
"""

import numpy as np


def gaussian_kernel_2d(sigma: float, size: int) -> np.ndarray:
    """Build a normalised 2D Gaussian kernel of the given pixel size."""
    if size % 2 == 0:
        size += 1
    k = np.arange(-(size // 2), size // 2 + 1, dtype=float)
    g1d = np.exp(-k ** 2 / (2 * sigma ** 2))
    g1d /= g1d.sum()
    kernel = np.outer(g1d, g1d)
    kernel /= kernel.sum()
    return kernel.astype(np.float32)


def convolve2d(arr: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """
    2D convolution with edge-replication padding.
    Works on float arrays of shape (H, W).
    """
    arr = arr.astype(np.float32)
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = np.pad(arr, ((ph, ph), (pw, pw)), mode='edge')

    result = np.zeros_like(arr, dtype=np.float32)
    for i in range(kh):
        for j in range(kw):
            result += padded[i:i + arr.shape[0], j:j + arr.shape[1]] * kernel[i, j]
    return result


def gaussian_blur(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur to a 2D float array."""
    if sigma <= 0:
        return arr.astype(np.float32)
    size = max(3, int(6 * sigma + 1)) | 1   # always odd
    size = min(size, min(arr.shape) | 1)     # clamp to array size
    k = gaussian_kernel_2d(sigma, size)
    return convolve2d(arr, k)


def gaussian_blur_rgb(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur independently to each channel of (H, W, 3)."""
    if sigma <= 0:
        return arr.astype(np.float32)
    out = np.empty_like(arr, dtype=np.float32)
    for c in range(arr.shape[2]):
        out[:, :, c] = gaussian_blur(arr[:, :, c], sigma)
    return out


def binary_dilation(mask: np.ndarray, radius: int = 1) -> np.ndarray:
    """Simple max-pooling dilation on a bool/float mask."""
    padded = np.pad(mask.astype(np.float32), radius, mode='constant', constant_values=0)
    H, W = mask.shape
    out = np.zeros((H, W), dtype=np.float32)
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            out = np.maximum(out, padded[radius + dr:radius + dr + H,
                                         radius + dc:radius + dc + W])
    return out > 0


def detect_boundary(mask: np.ndarray) -> np.ndarray:
    """
    Return a float array where 1.0 marks boundary pixels
    (pixels adjacent to a different class in the 4-connected neighbourhood).
    """
    mask_f = mask.astype(np.float32)
    # Compute local variance via 3×3 max − min
    padded = np.pad(mask_f, 1, mode='edge')
    local_max = np.zeros_like(mask_f)
    local_min = np.full_like(mask_f, 1e9)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            patch = padded[1 + dr:1 + dr + mask_f.shape[0],
                           1 + dc:1 + dc + mask_f.shape[1]]
            local_max = np.maximum(local_max, patch)
            local_min = np.minimum(local_min, patch)
    return (local_max - local_min).astype(np.float32)


def clamp(arr: np.ndarray, lo: float = 0.0, hi: float = 1.0) -> np.ndarray:
    return np.clip(arr, lo, hi)
