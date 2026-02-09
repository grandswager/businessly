import math
from typing import Optional, List
from services.DatabaseService import business_profiles

class RecommendationService:
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

        if categories:
            pipeline.append({"$match": {"category": {"$in": categories}}})

        if user_query:
            pipeline.append({"$match": {"$or": [{"name": {"$regex": user_query, "$options": "i"}}, {"description": {"$regex": user_query, "$options": "i"}}]}})

        pipeline.append({"$facet": {"results": [{"$skip": offset}, {"$limit": limit}], "totalCount": [{"$count": "count"}]}})

        data = list(business_profiles.aggregate(pipeline))[0]

        results = data["results"]
        total = data["totalCount"][0]["count"] if data["totalCount"] else 0

        enriched_results = []

        for b in results:
            users_rated = int(b.get("users_rated", 0))
            combined_rating = float(b.get("combined_rating", 0))
            rating = (combined_rating / users_rated if users_rated > 0 else 0)

            if rating < min_rating:
                continue

            distance_km = RecommendationService._distance_km(user_lat, user_lng, b["location"]["coordinates"][1], b["location"]["coordinates"][0])

            b["rating"] = round(rating, 1)
            b["distance_km"] = round(distance_km, 2)
            b["score"] = RecommendationService._score(b, rating, distance_km)

            enriched_results.append(b)

        enriched_results.sort(key=lambda x: x["score"], reverse=True)

        return enriched_results, total

    @staticmethod
    def _score(business: dict, rating: float, distance_km: float) -> float:
        bookmarks = int(business.get("bookmarks", 0))
        return (rating * 2) + math.log(bookmarks + 1) - (distance_km * 0.2)

    @staticmethod
    def _distance_km(lat1, lng1, lat2, lng2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(lat1)) *
            math.cos(math.radians(lat2)) *
            math.sin(dlng / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
