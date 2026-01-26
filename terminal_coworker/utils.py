import hashlib
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from pathlib import Path

def calculate_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()

def preprocess_image(image_path: Path) -> list[Image.Image]:
    """
    Returns list of PIL Images: [Original, Contrast, Binary]
    """
    try:
        img = Image.open(image_path)
        
        # 1. Original (resized if huge)
        img.thumbnail((1500, 1500)) 
        
        # 2. High Contrast
        enhancer = ImageEnhance.Contrast(img)
        img_contrast = enhancer.enhance(1.5)
        
        # 3. Binarized (using OpenCV for better thresholding)
        open_cv_image = np.array(img.convert('L')) 
        # Apply adaptive thresholding
        binarized = cv2.adaptiveThreshold(
            open_cv_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        img_bin = Image.fromarray(binarized)

        return [img, img_contrast, img_bin]

    except Exception as e:
        print(f"Warning: Image preprocessing failed for {image_path}: {e}")
        return []