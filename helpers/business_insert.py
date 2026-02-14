import uuid
import random
import re
from services.DatabaseService import business_profiles
from services.GeocodingService import GeocodingService


class BusinessService:
    @staticmethod
    def create_business_profile(business_data: dict):
        return business_profiles.insert_one(business_data)


def generate_random_phone():
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"


def parse_input(input_string: str):
    """
    Example input:
    Daisies Convenience Store : 96 Cornell Park Ave #4, Markham, ON L6B 1B6;
    DESCRIPTION;
    (https://image-url.jpg)
    """

    # Split name from rest
    name_part, rest = input_string.split(":", 1)
    business_name = name_part.strip()

    # Split address, description, image URL
    parts = [p.strip() for p in rest.split(";")]

    if len(parts) < 3:
        raise ValueError("Input must include address, description, and image URL")

    address_part = parts[0]
    description = parts[1]

    # Extract image URL from parentheses
    image_match = re.search(r"\((https?://.+?)\)", parts[2])
    if not image_match:
        raise ValueError("Image URL format is invalid")

    image_url = image_match.group(1)

    # Extract street, city, province, postal code
    address_match = re.match(
        r"(.+?),\s*(.+?),\s*([A-Z]{2})\s*([A-Z]\d[A-Z]\s?\d[A-Z]\d)",
        address_part
    )

    if not address_match:
        raise ValueError("Address format is invalid")

    street_address = address_match.group(1).strip()
    city = address_match.group(2).strip()
    province = address_match.group(3).strip()
    postal_code = address_match.group(4).replace(" ", "").upper()[:6]

    return {
        "business_name": business_name,
        "address": street_address,
        "city": city,
        "province": province,
        "postal_code": postal_code,
        "description": description,
        "image_url": image_url,
    }


def build_business_object(parsed_data: dict):
    coords = GeocodingService.geocode(
        address=parsed_data["address"],
        city=parsed_data["city"],
        province=parsed_data["province"]
    )

    CATEGORY = input("Category: ").title()

    users_rated = random.randint(1, 20)
    ratings = [random.randint(1, 5) for _ in range(users_rated)]
    combined_rating = sum(ratings)

    bookmarks = random.randint(1, 100)

    return {
        "uuid": str(uuid.uuid4()),
        "name": parsed_data["business_name"],
        "category": CATEGORY,
        "address": parsed_data["address"],
        "city": parsed_data["city"],
        "province": parsed_data["province"],
        "country": "Canada",
        "postal_code": parsed_data["postal_code"],
        "location": {
            "type": "Point",
            "coordinates": [coords[1], coords[0]]
        },
        "description": parsed_data["description"],
        "phone": generate_random_phone(),
        "socials": {
            "instagram": None,
            "website": None
        },
        "image_url": parsed_data["image_url"],
        "combined_rating": combined_rating,
        "users_rated": users_rated,
        "bookmarks": bookmarks,
        "comments": {},
        "coupons": {}
    }


def process_and_insert(input_string: str):
    parsed = parse_input(input_string)
    business = build_business_object(parsed)
    return BusinessService.create_business_profile(business)

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    while True:
        input_data = input("Enter input in format: ")

        result = process_and_insert(input_data)
        print("Inserted business ID:", result.inserted_id)
