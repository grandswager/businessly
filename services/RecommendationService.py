import math
from typing import Optional, List
from services.DatabaseService import business_profiles, sponsored_businesses

class RecommendationService:
    """
    Service responsible for generating personalized business recommendations
    based on user location, filters, and ranking logic.

    Uses MongoDB geospatial queries combined with custom scoring logic.
    """

    @staticmethod
    def recommend(
        user_lat: float,
        user_lng: float,
        max_distance_km: float = 10,
        min_rating: float = 0,
        categories=None,
        user_query=None,
        limit: int = 20,
        offset: int = 0
    ):

        pipeline = [{"$geoNear": {"near": {"type": "Point", "coordinates": [user_lng, user_lat]}, "distanceField": "distance_m", "maxDistance": int(max_distance_km * 1000), "spherical": True}},]

        # Optional category filter
        if categories:
            pipeline.append({"$match": {"category": {"$in": categories}}})

        # Optional text search (case-insensitive regex match)
        if user_query:
            pipeline.append({"$match": {"$or": [{"name": {"$regex": user_query, "$options": "i"}}, {"description": {"$regex": user_query, "$options": "i"}}]}})

        pipeline.append({"$facet": {"results": [{"$skip": offset}, {"$limit": limit}], "totalCount": [{"$count": "count"}]}})

        data = list(business_profiles.aggregate(pipeline))[0]

        results = data["results"]
        total = data["totalCount"][0]["count"] if data["totalCount"] else 0

        enriched_results = []

        # Post-processing: compute rating, distance, and ranking score
        for b in results:

            # Compute average rating
            users_rated = int(b.get("users_rated", 0))
            combined_rating = float(b.get("combined_rating", 0))
            rating = (combined_rating / users_rated if users_rated > 0 else 0)

            # Skip businesses below minimum rating threshold
            if rating < min_rating:
                continue

            distance_km = RecommendationService._distance_km(user_lat, user_lng, b["location"]["coordinates"][1], b["location"]["coordinates"][0])

            # Enrich business object with computed values
            b["rating"] = round(rating, 1)
            b["distance_km"] = round(distance_km, 2)
            b["score"] = RecommendationService._score(b, rating, distance_km)

            enriched_results.append(b)

        enriched_results.sort(key=lambda x: x["score"], reverse=True)

        return enriched_results, total

    @staticmethod
    def _score(business: dict, rating: float, distance_km: float) -> float:
        """
        Compute recommendation score for a business.

        Scoring formula:
            (rating * 2) + log(bookmarks + 1) - (distance_km * 0.2)

        Factors:
        - Rating is heavily weighted.
        - Bookmarks increase popularity influence (logarithmic scaling).
        - Distance reduces score (closer businesses rank higher).

        Returns:
        - float score value
        """
        bookmarks = int(business.get("bookmarks", 0))
        return (rating * 2) + math.log(bookmarks + 1) - (distance_km * 0.2)

    @staticmethod
    def _distance_km(lat1, lng1, lat2, lng2):
        """
        Calculate the distance between two geographic coordinates
        using the Haversine formula.

        Parameters:
        - lat1, lng1: User coordinates
        - lat2, lng2: Business coordinates

        Returns:
        - Distance in kilometers (float)
        """

        # Earth's radius in kilometers
        R = 6371

        # Convert differences to radians
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        # Haversine formula
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(lat1)) *
            math.cos(math.radians(lat2)) *
            math.sin(dlng / 2) ** 2
        )

        # Great-circle distance
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    @staticmethod
    def recommend_sponsored_business(
        user_lat: float,
        user_lng: float,
        max_distance_km: float = 20
    ) -> Optional[dict]:
        """
        Returns a random sponsored business within the given distance (default 20km).

        Steps:
        1. Find sponsored businesses within max_distance_km
        2. Randomly pick one
        3. Return None if no sponsored businesses found
        """

        pipeline = [
            {
                "$geoNear": {
                    "near": {
                        "type": "Point",
                        "coordinates": [user_lng, user_lat]
                    },
                    "distanceField": "distance_m",
                    "maxDistance": int(max_distance_km * 1000),
                    "spherical": True
                }
            },
            {"$sample": {"size": 1}}
        ]

        result = list(sponsored_businesses.aggregate(pipeline))
        return result[0] if result else None
