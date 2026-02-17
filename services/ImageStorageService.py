import cloudinary
import cloudinary.uploader
from PIL import Image
import io

import os
import dotenv
dotenv.load_dotenv()

class ImageStorageService:
    """
    Service responsible for handling image uploads and deletions
    using Cloudinary as the cloud storage provider.

    Features:
    - File size validation (max 5MB)
    - Image format validation (JPEG, PNG only)
    - Secure Cloudinary upload
    - Overwrite existing images by public_id
    """

    # Maximum allowed upload size (5MB)
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

    # Allowed image formats (validated via Pillow)
    ALLOWED_FORMATS = {"JPEG", "PNG"}

    def __init__(self):
        """
        Initialize Cloudinary configuration using environment variables.
        Must be set before performing any uploads or deletions.
        """
        cloudinary.config(
            cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
            api_key=os.environ.get("CLOUDINARY_API_KEY"),
            api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
            secure=True  # Force HTTPS URLs
        )

    def upload_profile_picture(self, user_uuid: str, file_bytes: bytes) -> str:
        """
        Upload or replace a user's profile picture.

        Parameters:
        - user_uuid (str): Unique identifier of the user.
        - file_bytes (bytes): Raw image file bytes.

        Returns:
        - str: Secure URL of uploaded image.

        Raises:
        - ValueError: If file is empty, too large, or invalid format.
        """

        # Ensure file is provided
        if not file_bytes:
            raise ValueError("File is empty")

        # Enforce file size limit
        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError("File too large (max 5MB)")

        # Validate image integrity and format
        img_format = self._validate_image(file_bytes)

        if not img_format: raise ValueError("Invalid file format.")

        # Use deterministic public_id so uploads overwrite previous image
        public_id = f"pfp/{user_uuid}"

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            overwrite=True,        # Replace existing image
            resource_type="image",
            invalidate=True        # Clear CDN cache
        )

        return result["secure_url"]
    
    def upload_business_picture(self, business_uuid: str, file_bytes: bytes) -> str:
        """
        Upload or replace a business profile image.

        Parameters:
        - business_uuid (str): Unique identifier of the business.
        - file_bytes (bytes): Raw image file bytes.

        Returns:
        - str: Secure URL of uploaded image.

        Raises:
        - ValueError: If file is empty, too large, or invalid.
        """

        # Ensure file is provided
        if not file_bytes:
            raise ValueError("File is empty")

        # Enforce file size limit
        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError("File too large (max 5MB)")

        # Validate image integrity and format
        img_format = self._validate_image(file_bytes)

        if not img_format: raise ValueError("Invalid file format.")

        # Use deterministic public_id so uploads overwrite previous image
        public_id = f"businesses/{business_uuid}"

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            invalidate=True
        )

        return result["secure_url"]

    def delete_profile_picture(self, user_uuid: str) -> bool:
        """
        Delete a user's profile picture from Cloudinary.

        Parameters:
        - user_uuid (str): Unique identifier of the user.

        Returns:
        - bool: True if deletion was successful, False otherwise.
        """

        public_id = f"pfp/{user_uuid}"

        result = cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            invalidate=True  # Invalidate CDN cache
        )

        return result.get("result") == "ok"

    def _validate_image(self, file_bytes: bytes) -> str:
        """
        Validate that uploaded bytes represent a valid image file.

        Steps:
        - Attempt to open image using Pillow.
        - Verify integrity (detect corruption).
        - Ensure format is allowed (JPEG or PNG).

        Parameters:
        - file_bytes (bytes): Raw file data.

        Returns:
        - str: Detected image format (e.g., "JPEG", "PNG").

        Raises:
        - ValueError: If image is corrupted or unsupported format.
        """

        try:
            # Load image from memory
            img = Image.open(io.BytesIO(file_bytes))

            # Verify file integrity (checks corruption without full decode)
            img.verify()

            img_format = img.format

        except Exception:
            raise ValueError("Invalid image file")

        # Ensure format is allowed
        if img_format not in self.ALLOWED_FORMATS:
            raise ValueError("Only JPG and PNG images are allowed")

        return img_format
