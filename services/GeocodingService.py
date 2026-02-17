import re
import requests

class GeocodingService:
    """
    Service responsible for converting a physical address into
    geographic coordinates (latitude, longitude).

    Uses the OpenStreetMap Nominatim API for geocoding.
    """

    # Base endpoint for Nominatim search API
    BASE_URL = "https://nominatim.openstreetmap.org/search"

    @staticmethod
    def _sanitize_address(address: str) -> str:
        """
        Clean and normalize an address string before sending it
        to the geocoding API.

        Removes:
        - Unit numbers (e.g., "#101")
        - Apartment/suite identifiers (e.g., "Suite 200", "Apt 4B")
        - Floor indicators

        This improves geocoding accuracy by focusing on the main street address.

        Parameters:
        - address (str): Raw address input.

        Returns:
        - str: Cleaned and normalized address.
        """

        # Patterns to remove unit/suite/floor information
        patterns = [
            r"#\s*\w+",  # Matches "#123"
            r"\b(unit|suite|apt|apartment|ste|floor|ground)\b\.?\s*\w+",
        ]

        # Normalize to lowercase for consistent cleaning
        cleaned = address.lower()

        # Remove unwanted patterns
        for p in patterns:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)

        # Remove leading/trailing whitespace
        return cleaned.strip()

    @staticmethod
    def geocode(address: str, city: str, province: str, country="Canada"):
        """
        Convert an address into latitude and longitude coordinates.

        Parameters:
        - address (str): Street address (e.g., "123 Main St").
        - city (str): City name.
        - province (str): Province or state.
        - country (str): Country name (default: Canada).

        Returns:
        - (float, float): Tuple containing (latitude, longitude).

        Raises:
        - Exception: If external service returns non-200 status.
        - ValueError: If no results are found.
        """

        # Clean address to improve matching accuracy
        clean_address = GeocodingService._sanitize_address(address)

        # Construct full query string
        query = f"{clean_address}, {city}, {province}, {country}"

        # Send GET request to Nominatim API
        response = requests.get(
            GeocodingService.BASE_URL,
            params={
                "q": query,       # Full address query
                "format": "json", # JSON response format
                "limit": 1        # Only need best match
            },
            headers={
                # Required by Nominatim usage policy
                "User-Agent": "businessly/1.0 (benny@fxk3b.com)"
            },
            timeout=10  # Prevent hanging requests
        )

        # Check for API failure
        if response.status_code != 200:
            raise Exception("Geocoding service error")

        data = response.json()

        # No results returned
        if not data:
            raise ValueError("Address not found")

        # Return latitude and longitude as floats
        return float(data[0]["lat"]), float(data[0]["lon"])
