from services.DatabaseService import sponsored_businesses
from services.GeocodingService import GeocodingService

def create_sponsored_business(address: str, business_uuid: str):
    """
    Takes full address string (e.g. "96 Cornell Park Ave #4, Markham, ON")
    Uses it only for geocoding.
    Stores only uuid + GeoJSON location.
    """

    try:
        street, city, province = [part.strip() for part in address.split(",")]
    except ValueError:
        raise ValueError(
            "Address must be in format: 'Street, City, Province'"
        )

    coords = GeocodingService.geocode(
        address=street,
        city=city,
        province=province
    )

    sponsored_data = {
        "uuid": business_uuid,
        "location": {
            "type": "Point",
            "coordinates": [coords[1], coords[0]]  # [lng, lat]
        }
    }

    return sponsored_businesses.insert_one(sponsored_data)

while True:
    create_sponsored_business(input("Address (street, city, province): "), input("Uuid: "))
