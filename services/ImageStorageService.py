import cloudinary
import cloudinary.uploader
from PIL import Image
import io

import os
import dotenv
dotenv.load_dotenv()

class ImageStorageService:
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
    ALLOWED_FORMATS = {"JPEG", "PNG"}

    def __init__(self):
        cloudinary.config(
            cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
            api_key=os.environ.get("CLOUDINARY_API_KEY"),
            api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
            secure=True
        )

    def upload_profile_picture(self, user_uuid: str, file_bytes: bytes) -> str:
        if not file_bytes:
            raise ValueError("File is empty")

        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError("File too large (max 5MB)")

        img_format = self._validate_image(file_bytes)

        if not img_format: raise ValueError("Invalid file format.")

        public_id = f"pfp/{user_uuid}"

        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            invalidate=True
        )

        return result["secure_url"]
    
    def upload_business_picture(self, business_uuid: str, file_bytes: bytes) -> str:
        if not file_bytes:
            raise ValueError("File is empty")

        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError("File too large (max 5MB)")

        img_format = self._validate_image(file_bytes)

        if not img_format: raise ValueError("Invalid file format.")

        public_id = f"businesses/{business_uuid}"

        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            invalidate=True
        )

        return result["secure_url"]

    def delete_profile_picture(self, user_uuid: str) -> bool:
        public_id = f"pfp/{user_uuid}"

        result = cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            invalidate=True
        )

        return result.get("result") == "ok"

    def _validate_image(self, file_bytes: bytes) -> str:
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()
            img_format = img.format
        except Exception:
            raise ValueError("Invalid image file")

        if img_format not in self.ALLOWED_FORMATS:
            raise ValueError("Only JPG and PNG images are allowed")

        return img_format
