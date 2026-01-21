import re
import requests

class GeocodingService:
    BASE_URL = "https://nominatim.openstreetmap.org/search"

    @staticmethod
    def _sanitize_address(address: str) -> str:
        patterns = [
            r"#\s*\w+",
            r"\b(unit|suite|apt|apartment|ste)\b\.?\s*\w+",
        ]

        cleaned = address.lower()
        for p in patterns:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    @staticmethod
    def geocode(address: str, city: str, province: str, country="Canada"):
        clean_address = GeocodingService._sanitize_address(address)

        query = f"{clean_address}, {city}, {province}, {country}"

        response = requests.get(
            GeocodingService.BASE_URL,
            params={
                "q": query,
                "format": "json",
                "limit": 1
            },
            headers={
                "User-Agent": "businessly/1.0 (benny@fxk3b.com)"
            },
            timeout=10
        )

        if response.status_code != 200:
            raise Exception("Geocoding service error")

        data = response.json()
        if not data:
            raise ValueError("Address not found")

        return float(data[0]["lat"]), float(data[0]["lon"])
