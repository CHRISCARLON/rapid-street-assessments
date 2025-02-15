import json
import requests
import asyncio
from loguru import logger
from robyn import Response
from robyn.robyn import QueryParams
from robyn_lib.utils.process_features import process_features
from robyn_lib.utils.utils import get_bbox_from_usrn

async def get_land_use_route(query_params: QueryParams) -> Response:
    """API route to get features data from both building and land use collections"""
    
    # Define the collection IDs for the land use route
    COLLECTION_IDS = [
        "bld-fts-building-1", 
        "lus-fts-site-1",     
    ]

    try:
        # Get USRN from query params
        usrn = query_params.get('usrn')
        if not usrn:
            raise ValueError("Missing required parameter: usrn")

        # Calculate bbox once from USRN
        minx, miny, maxx, maxy = await get_bbox_from_usrn(usrn)
        bbox = f"{minx},{miny},{maxx},{maxy}"
        bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
        crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

        # Create coroutines for concurrent execution using the same bbox
        feature_coroutines = [
            process_features(
                collection_id=collection_id,
                usrn=usrn,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs,
            )
            for collection_id in COLLECTION_IDS
        ]

        # Gather and await all coroutines
        feature_results = await asyncio.gather(*feature_coroutines, return_exceptions=True)

        all_features = []
        latest_timestamp = None

        # Process results and handle any individual collection failures
        for collection_id, result in zip(COLLECTION_IDS, feature_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {collection_id}: {str(result)}")
                continue

            if not isinstance(result, dict) or 'features' not in result:
                logger.error(f"Invalid response format from {collection_id}")
                continue

            # Remove filtering and directly add features
            all_features.extend(result['features'])

            # Keep track of the latest timestamp
            if result.get('timeStamp'):
                if latest_timestamp is None or result['timeStamp'] > latest_timestamp:
                    latest_timestamp = result['timeStamp']

        filtered_response = {
            'type': 'FeatureCollection',
            'numberReturned': len(all_features),
            'timeStamp': latest_timestamp or "",
            'features': all_features
        }

        return Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            description=json.dumps(filtered_response),
        )

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if hasattr(http_err, 'response') else 500
        logger.error(f"HTTP error occurred: {http_err}")
        return Response(
            status_code=status_code,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(http_err)}),
        )

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(ve)}),
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return Response(
            status_code=500,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(e)}),
        )