from typing import Optional, Literal
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from logging_config import get_logger
from ..interfaces.interfaces import OSFeatures, BBOXGeometry, LLMSummary
from ..services.services import OSFeatureService, DataService, LangChainSummaryService
from ..processors.tts.tts_processor import convert_summary_to_speech
from ..types import RouteType

logger = get_logger(__name__)

VoiceType = Literal[
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
]


@lru_cache()
def get_feature_service() -> OSFeatures:
    """Dependency provider for OSFeatureService."""
    return OSFeatureService()


@lru_cache()
def get_geometry_service() -> BBOXGeometry:
    """Dependency provider for geometry operations."""
    return DataService()


@lru_cache()
def get_llm_summary_service() -> LLMSummary:
    """Dependency provider for LLM Summary Service."""
    return LangChainSummaryService()


router = APIRouter()

# TODO: Don't need two functions make into one a dispatch based on route
@router.get(
    "/street-info-llm",
    summary="Fetch detailed street information with a LLM summary",
    tags=["Street Info"],
)
async def get_street_info_llm_route(
    usrn: str = Query(
        ...,
        description="Unique Street Reference Number (numeric)",
        pattern=r"^\d+$",
        min_length=1,
        max_length=20,
    ),
    voice: Optional[VoiceType] = Query(
        None, description="Optional: Voice type for audio output (returns MP3)"
    ),
    feature_service: OSFeatures = Depends(get_feature_service),
    geometry_service: BBOXGeometry = Depends(get_geometry_service),
    llm_summary_service: LLMSummary = Depends(get_llm_summary_service),
):
    """
    Summary of network and RAMI data.

    Returns JSON by default, or audio if voice parameter is provided.
    """
    logger.info(
        f"Street info request: USRN={usrn}, voice={voice}", extra={"usrn": usrn}
    )

    try:
        path_type = RouteType.STREET_INFO.value

        logger.debug(f"Fetching features for USRN: {usrn}", extra={"usrn": usrn})
        features = await feature_service.get_features(path_type=path_type, usrn=usrn)

        logger.debug(
            f"Pre-processing street info for USRN: {usrn}", extra={"usrn": usrn}
        )
        simplified_features = await llm_summary_service.pre_process_street_info(
            features
        )

        logger.debug(f"Generating LLM summary for USRN: {usrn}", extra={"usrn": usrn})
        llm_summary = await llm_summary_service.summarise_results(
            simplified_features, path_type
        )

        if voice:
            logger.debug(
                f"Converting to speech: voice={voice}, USRN={usrn}",
                extra={"usrn": usrn},
            )
            audio_bytes = await convert_summary_to_speech(
                summary_data=llm_summary.get("llm_summary", {}),
                voice=voice,
                response_format="mp3",
            )
            logger.info(
                f"Street info audio generated: USRN={usrn}, size={len(audio_bytes)} bytes",
                extra={"usrn": usrn},
            )
            return Response(
                content=audio_bytes,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename=street-info-{usrn}.mp3",
                    "Accept-Ranges": "bytes",
                },
            )

        logger.info(f"Street info completed: USRN={usrn}", extra={"usrn": usrn})
        return llm_summary

    except ValueError as ve:
        logger.warning(
            f"Validation error for USRN {usrn}: {str(ve)}", extra={"usrn": usrn}
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(
            f"Internal error in get_street_info_llm_route for USRN {usrn}: {e}",
            extra={"usrn": usrn},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/land-use-info-llm",
    summary="Fetch land use information with a LLM summary",
    tags=["Land Use"],
)
async def get_land_use_llm_route(
    usrn: str = Query(
        ...,
        description="Unique Street Reference Number (numeric)",
        pattern=r"^\d+$",
        min_length=1,
        max_length=20,
    ),
    voice: Optional[VoiceType] = Query(
        None, description="Optional: Voice type for audio output (returns MP3)"
    ),
    feature_service: OSFeatures = Depends(get_feature_service),
    geometry_service: BBOXGeometry = Depends(get_geometry_service),
    llm_summary_service: LLMSummary = Depends(get_llm_summary_service),
):
    """
    Summary of Land use and building information.

    Returns JSON by default, or audio if voice parameter is provided.
    """
    logger.info(f"Land use request: USRN={usrn}, voice={voice}", extra={"usrn": usrn})

    try:
        path_type = RouteType.LAND_USE.value

        logger.debug(f"Fetching bounding box for USRN: {usrn}", extra={"usrn": usrn})
        minx, miny, maxx, maxy = await geometry_service.get_bbox_from_usrn(usrn)
        bbox = f"{minx},{miny},{maxx},{maxy}"
        crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
        bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

        logger.debug(
            f"Fetching land use features with bbox for USRN: {usrn}",
            extra={"usrn": usrn},
        )
        features = await feature_service.get_features(
            path_type=path_type, usrn=usrn, bbox=bbox, bbox_crs=bbox_crs, crs=crs
        )

        logger.debug(
            f"Pre-processing land use info for USRN: {usrn}", extra={"usrn": usrn}
        )
        simplified_features = await llm_summary_service.pre_process_land_use_info(
            features
        )

        logger.debug(f"Generating LLM summary for USRN: {usrn}", extra={"usrn": usrn})
        llm_summary = await llm_summary_service.summarise_results(
            simplified_features, path_type
        )

        if voice:
            logger.debug(
                f"Converting to speech: voice={voice}, USRN={usrn}",
                extra={"usrn": usrn},
            )
            audio_bytes = await convert_summary_to_speech(
                summary_data=llm_summary.get("llm_summary", {}),
                voice=voice,
                response_format="mp3",
            )
            logger.info(
                f"Land use audio generated: USRN={usrn}, size={len(audio_bytes)} bytes",
                extra={"usrn": usrn},
            )
            return Response(
                content=audio_bytes,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename=land-use-{usrn}.mp3",
                    "Accept-Ranges": "bytes",
                },
            )

        logger.info(f"Land use completed: USRN={usrn}", extra={"usrn": usrn})
        return llm_summary

    except ValueError as ve:
        logger.warning(
            f"Validation error for land use request for USRN {usrn}: {str(ve)}",
            extra={"usrn": usrn},
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(
            f"Internal error in get_land_use_llm_route for USRN {usrn}: {e}",
            extra={"usrn": usrn},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
