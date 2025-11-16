from typing import Optional, Literal
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from loguru import logger
from ..interfaces.interfaces import OSFeatures, BBOXGeometry, LLMSummary
from ..services.services import OSFeatureService, DataService, LangChainSummaryService
from ..processors.tts.tts_processor import convert_summary_to_speech
from ..types import RouteType

# Voice types for TTS
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


# Dependency injection functions
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


# Create FastAPI router
router = APIRouter()


@router.get(
    "/street-info-llm",
    summary="Fetch detailed street information with a LLM summary",
    tags=["Street Info"],
)
async def get_street_info_llm_route(
    usrn: str = Query(..., description="Unique Street Reference Number"),
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
    try:
        path_type = RouteType.STREET_INFO.value

        # Process features
        features = await feature_service.get_features(
            path_type=path_type, usrn=usrn
        )

        simplified_features = await llm_summary_service.pre_process_street_info(
            features
        )
        llm_summary = await llm_summary_service.summarise_results(
            simplified_features, path_type
        )

        # If voice parameter is provided, convert to audio
        if voice:
            audio_bytes = await convert_summary_to_speech(
                summary_data=llm_summary.get("llm_summary", {}),
                voice=voice,
                response_format="mp3",
            )
            return Response(
                content=audio_bytes,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename=street-info-{usrn}.mp3",
                    "Accept-Ranges": "bytes",
                },
            )

        return llm_summary

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal error in get_street_info_llm_route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/land-use-info-llm",
    summary="Fetch land use information with a LLM summary",
    tags=["Land Use"],
)
async def get_land_use_llm_route(
    usrn: str = Query(..., description="Unique Street Reference Number"),
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
    try:
        path_type = RouteType.LAND_USE.value

        # Get bbox from USRN
        minx, miny, maxx, maxy = await geometry_service.get_bbox_from_usrn(usrn)
        bbox = f"{minx},{miny},{maxx},{maxy}"
        crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
        bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

        # Process features
        features = await feature_service.get_features(
            path_type=path_type, usrn=usrn, bbox=bbox, bbox_crs=bbox_crs, crs=crs
        )

        simplified_features = await llm_summary_service.pre_process_land_use_info(
            features
        )
        llm_summary = await llm_summary_service.summarise_results(
            simplified_features, path_type
        )

        # If voice parameter is provided, convert to audio
        if voice:
            audio_bytes = await convert_summary_to_speech(
                summary_data=llm_summary.get("llm_summary", {}),
                voice=voice,
                response_format="mp3",
            )
            return Response(
                content=audio_bytes,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename=land-use-{usrn}.mp3",
                    "Accept-Ranges": "bytes",
                },
            )

        return llm_summary

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal error in get_land_use_llm_route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
