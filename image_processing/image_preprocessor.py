"""
Image preprocessing module for the InsurTech platform.

This module provides functions for preprocessing images before they are
analyzed by the YOLO model for damage detection.
"""
import os
import logging
from typing import Tuple, Optional, List
from PIL import Image, ImageOps, ImageEnhance, UnidentifiedImageError
import numpy as np

# Configure logger
logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """
    Preprocesses images for optimal YOLO model inference.
    
    This class provides methods to validate, resize, and enhance images
    before they are passed to the vehicle damage detection model.
    """
    
    def __init__(self, target_size: Tuple[int, int] = (640, 640),
                 allowed_formats: List[str] = ['jpg', 'jpeg', 'png']):
        """
        Initialize the image preprocessor.
        
        Args:
            target_size: Target image dimensions (width, height)
            allowed_formats: List of allowed image file formats
        """
        self.target_size = target_size
        self.allowed_formats = [fmt.lower() for fmt in allowed_formats]
        logger.info(f"Initialized ImagePreprocessor with target size {target_size}")
        
    def validate_image(self, image_path: str) -> bool:
        """
        Validate if the image exists and has a supported format.
        
        Args:
            image_path: Path to the image to validate
            
        Returns:
            True if the image is valid, False otherwise
        """
        # Check if file exists
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return False
            
        # Check file extension
        file_ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        if file_ext not in self.allowed_formats:
            logger.error(f"Unsupported image format: {file_ext}. Allowed formats: {self.allowed_formats}")
            return False
            
        # Try opening the image
        try:
            with Image.open(image_path) as img:
                # Check if image is corrupted
                img.verify()
            return True
        except (UnidentifiedImageError, IOError) as e:
            logger.error(f"Invalid or corrupted image: {image_path}. Error: {e}")
            return False
            
    def preprocess(self, image_path: str) -> Optional[str]:
        """
        Preprocess an image for optimal model inference.
        
        Args:
            image_path: Path to the image to preprocess
            
        Returns:
            Path to the preprocessed image or None if preprocessing failed
        """
        if not self.validate_image(image_path):
            return None
            
        try:
            # Open image
            with Image.open(image_path) as img:
                # Convert to RGB (in case of RGBA or other formats)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize with aspect ratio preservation
                img = ImageOps.contain(img, self.target_size)
                
                # Create a new blank image with target dimensions
                new_img = Image.new('RGB', self.target_size, (0, 0, 0))
                
                # Paste the resized image in the center
                paste_pos = ((self.target_size[0] - img.width) // 2,
                             (self.target_size[1] - img.height) // 2)
                new_img.paste(img, paste_pos)
                
                # Enhance contrast slightly
                enhancer = ImageEnhance.Contrast(new_img)
                new_img = enhancer.enhance(1.2)
                
                # Save preprocessed image
                output_path = f"{os.path.splitext(image_path)[0]}_preprocessed.jpg"
                new_img.save(output_path, quality=95)
                
                logger.info(f"Image preprocessed successfully: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {e}")
            return None 