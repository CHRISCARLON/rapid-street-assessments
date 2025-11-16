import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger
from os_lib.os_data_object import OSDataObject
from ...types import RouteType


async def process_single_collection(
    path_type: str,
    usrn: str,
    bbox: Optional[str] = None,
    bbox_crs: Optional[str] = None,
    crs: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process features based on path type with support for both street info and land use routes

    Args:
        path_type: str - The route path type ('land-use' or 'street-info')
        usrn: str - USRN for filtering (required for street-info, used for land-use context)
        bbox: Optional[str] - Bounding box for land use queries (required for land-use route)
        bbox_crs: Optional[str] - CRS for bounding box (optional, defaults used if not provided)
        crs: Optional[str] - Target CRS for response (optional, defaults used if not provided)

    Returns:
        Dict containing the combined feature collection

    Raises:
        ValueError: For validation errors
        Exception: For other errors
    """
    try:
        if not usrn:
            raise ValueError("A valid usrn is required")

        # Define route type as this is use to determine the collections to query
        route_type = RouteType(path_type)

        # Create OS data object
        os_data = OSDataObject()

        # Define collection IDs based on path type
        match route_type:
            case RouteType.STREET_INFO:
                logger.info(f"Processing street info for USRN: {usrn}")
                collection_ids = [
                    "trn-ntwk-street-1",
                    "trn-rami-specialdesignationarea-1",
                    "trn-rami-specialdesignationline-1",
                    "trn-rami-specialdesignationpoint-1",
                ]

                # Create coroutines for RAMI/Network collections
                feature_coroutines = [
                    os_data.get_single_collection_feature(
                        collection_id=collection_id,
                        query_attr="usrn",
                        query_attr_value=usrn,
                    )
                    for collection_id in collection_ids
                ]

            # TODO: Add building collection back in the future?
            case RouteType.LAND_USE:
                logger.info(f"Processing land use for USRN: {usrn}")
                collection_ids = [
                    # "bld-fts-building-1",
                    "lus-fts-site-1"
                ]
                if not bbox:
                    raise ValueError("A valid bbox is required for land use queries")

                # Create coroutines for Land Use/Building collections
                feature_coroutines = [
                    os_data.get_single_collection_feature(
                        collection_id=collection_id,
                        bbox=bbox,
                        bbox_crs=bbox_crs
                        or "http://www.opengis.net/def/crs/EPSG/0/27700",
                        crs=crs or "http://www.opengis.net/def/crs/EPSG/0/27700",
                    )
                    for collection_id in collection_ids
                ]

            case _:
                raise ValueError(f"Unsupported path type: {path_type}")

        # Gather and await all coroutines
        feature_results = await asyncio.gather(
            *feature_coroutines, return_exceptions=True
        )

        # Process results
        all_features: List[Dict[str, Any]] = []
        latest_timestamp: Optional[str] = None
        roadlink_ids: List[str] = []

        for collection_id, result in zip(collection_ids, feature_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {collection_id}: {str(result)}")
                continue

            if not isinstance(result, dict) or "features" not in result:
                logger.error(f"Invalid response format from {collection_id}")
                continue

            # Filter out geometry from each feature - as they are very large (clogs it up)
            # TODO: Remove the .copy() here as it is wasteful - change in place?
            # Just unpack here with the ** Syntax
            filtered_features = []
            for feature in result["features"]:
                feature_copy = feature.copy()
                if "geometry" in feature_copy:
                    del feature_copy["geometry"]

                if "geometry" in feature_copy:
                    raise ValueError(
                        f"Failed to remove geometry from feature in {collection_id}"
                    )

                filtered_features.append(feature_copy)

                if route_type == RouteType.STREET_INFO and collection_id == "trn-ntwk-street-1":
                    roadlinkreference = feature.get("properties", {}).get("roadlinkreference", [])
                    for ref in roadlinkreference:
                        if isinstance(ref, dict) and "roadlinkid" in ref:
                            roadlink_ids.append(ref["roadlinkid"])

            logger.success(
                f"Geometries removed from {collection_id}: {len(filtered_features)} features"
            )
            all_features.extend(filtered_features)

            if result.get("timeStamp"):
                if latest_timestamp is None or result["timeStamp"] > latest_timestamp:
                    latest_timestamp = result["timeStamp"]

        # Fetch roadlink features if we found any roadlink IDs (STREET_INFO route only)
        if route_type == RouteType.STREET_INFO and roadlink_ids:
            logger.info(f"Fetching {len(roadlink_ids)} roadlink features")

            roadlink_coroutines = [
                os_data.get_single_collection_feature(
                    collection_id="trn-ntwk-roadlink-5",
                    feature_id=roadlink_id
                )
                for roadlink_id in roadlink_ids
            ]

            roadlink_results = await asyncio.gather(
                *roadlink_coroutines, return_exceptions=True
            )

            # Process roadlink results
            roadlink_count = 0
            for roadlink_id, roadlink_result in zip(roadlink_ids, roadlink_results):
                if isinstance(roadlink_result, Exception):
                    logger.error(f"Failed to fetch roadlink {roadlink_id}: {str(roadlink_result)}")
                    continue

                if not isinstance(roadlink_result, dict):
                    logger.error(f"Invalid roadlink response format for {roadlink_id}")
                    continue

                if "properties" not in roadlink_result:
                    logger.warning(f"Roadlink {roadlink_id} has no properties - skipping")
                    continue

                # TODO: Need to remove the dot cotton from here too!
                roadlink_feature = roadlink_result.copy()
                if "geometry" in roadlink_feature:
                    del roadlink_feature["geometry"]

                if "properties" in roadlink_feature:
                    all_features.append(roadlink_feature)
                    roadlink_count += 1
                else:
                    logger.error(f"Properties lost for roadlink {roadlink_id} - not adding to LLM data")

                if roadlink_result.get("timeStamp"):
                    if latest_timestamp is None or roadlink_result["timeStamp"] > latest_timestamp:
                        latest_timestamp = roadlink_result["timeStamp"]

            logger.success(f"Successfully added {roadlink_count} roadlink features with full attributes to LLM data")

        if not all_features:
            logger.warning(f"No features found for USRN: {usrn}")

        return {
            "type": "FeatureCollection",
            "numberReturned": len(all_features),
            "timeStamp": latest_timestamp or "",
            "features": all_features,
        }

    except ValueError as ve:
        logger.error(f"Validation error in process_features: {ve}")
        raise
    except Exception as e:
        logger.error(f"Error in process_features: {e}")
        raise
