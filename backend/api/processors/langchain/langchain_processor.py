import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any, List, Union, cast
from ...types import RouteType


class StreetAnalysis(BaseModel):
    """Structured output for helping anxious drivers navigate streets safely"""

    location: List[str] = Field(
        description="Street name, area, and key landmarks to help the driver know where they are"
    )
    road_characteristics: List[str] = Field(
        description="Road layout, number of lanes, road surface condition, width, and general characteristics"
    )
    speed_and_traffic: List[str] = Field(
        description="Speed limits, typical traffic flow, busy times, and what to expect in terms of traffic volume"
    )
    hazards_to_watch_for: List[str] = Field(
        description="Potential hazards including construction zones, narrow sections, blind corners, pedestrian crossings, cyclists, or obstacles to be aware of"
    )
    restrictions_and_rules: List[str] = Field(
        description="Special restrictions like one-way streets, no-turn signs, parking restrictions, bus lanes, or time-based rules"
    )
    driving_tips: List[str] = Field(
        description="Specific, reassuring tips for driving safely on this street - what speed to maintain, when to be extra cautious, where to position your vehicle"
    )
    summary: str = Field(
        description="A calm, reassuring summary that helps the anxious driver feel prepared and confident about driving on this street"
    )


class LandUseAnalysis(BaseModel):
    """Structured output for area context to help anxious drivers understand their surroundings"""

    location: List[str] = Field(
        description="Area name, major landmarks, and notable buildings to help the driver orient themselves"
    )
    area_type: List[str] = Field(
        description="Type of area (residential, commercial, mixed-use, industrial) and what kind of activity to expect"
    )
    parking_information: List[str] = Field(
        description="Parking options, restrictions, parking garages, street parking availability, and any parking-related tips"
    )
    nearby_destinations: List[str] = Field(
        description="Notable destinations, businesses, public buildings, and services in the area that the driver might be looking for"
    )
    pedestrian_activity: List[str] = Field(
        description="Information about pedestrian crossings, schools, busy shopping areas, or high foot-traffic zones where extra caution is needed"
    )
    navigation_landmarks: List[str] = Field(
        description="Distinctive buildings, monuments, or features that can help with navigation and orientation while driving"
    )
    summary: str = Field(
        description="A reassuring summary of the area to help the driver understand their surroundings and feel more confident"
    )


async def process_with_langchain(
    data: Dict[str, Any], route_type: str
) -> Dict[str, Any]:
    """
    Process data using Langchain with structured output.

    This uses the OpenAI API to process the data.

    Args:
        data (Dict[str, Any]): The data to process
        route_type (str): The type of route to process

    Returns:
        Dict[str, Any]: The processed data
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise ValueError("OPENAI_API_KEY is not set")

    # Convert api_key to SecretStr using pydantic
    secret_api_key = SecretStr(api_key)

    # Set model type
    # TODO add other models?
    # Higher temperature for more verbose, detailed output
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, api_key=secret_api_key)

    # Select appropriate parser and template based on the route type
    match route_type:
        case RouteType.STREET_INFO.value:
            logger.info("Processing comprehensive street information for driver")
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a comprehensive street information system providing detailed awareness of everything on this street.

Your role is to provide COMPLETE and DETAILED information about:
- Every characteristic of the road (exact layout, all lane details, surface conditions, width measurements)
- All speed limits, traffic patterns, and flow information
- Every single hazard, obstacle, restriction, or special designation on this street
- All pedestrian crossings, signals, signs, and road markings
- Every turn restriction, parking rule, bus lane, and traffic regulation
- All construction zones, roadworks, and temporary restrictions
- Specific locations of everything mentioned (use exact street positions when available)

Be COMPREHENSIVE and THOROUGH. Include ALL details from the data - don't summarize or leave things out. The driver needs to be aware of EVERYTHING on this street. Provide specific locations, names, and details for every feature, restriction, and hazard.

Do not focus on being brief or reassuring - focus on being complete and informative. List everything.""",
                    ),
                    (
                        "user",
                        "Analyze this street data and provide COMPLETE information about everything on this street:\n\n{context}",
                    ),
                ]
            )
            structured_llm = model.with_structured_output(StreetAnalysis)
            chain = prompt | structured_llm

        case RouteType.LAND_USE.value:
            logger.info("Processing comprehensive area information for driver")
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a comprehensive area information system providing detailed awareness of everything surrounding this street.

Your role is to provide COMPLETE and DETAILED information about:
- Every building, property, and structure in the area (with names and specific locations)
- All businesses, shops, services, and public facilities
- All parking facilities, restrictions, zones, and regulations in detail
- Every landmark, monument, and distinctive feature
- All areas with pedestrian activity, crossings, and foot traffic zones
- Complete characterization of the area type and what activity to expect
- All educational institutions, religious buildings, and public spaces
- Specific addresses and locations when available

Be COMPREHENSIVE and THOROUGH. Include ALL properties, buildings, and features from the data - don't summarize or leave things out. The driver needs to know about EVERYTHING in this area. List all building names, business names, and specific details.

Do not focus on being brief - focus on being complete and informative. Enumerate everything.""",
                    ),
                    (
                        "user",
                        "Analyze this area data and provide COMPLETE information about everything in this area:\n\n{context}",
                    ),
                ]
            )
            structured_llm = model.with_structured_output(LandUseAnalysis)
            chain = prompt | structured_llm

        case _:
            raise ValueError(f"Unknown route type: {route_type}")

    try:
        response = await chain.ainvoke({"context": json.dumps(data, indent=2)})
        logger.success("Langchain Parse Successful")

        if isinstance(response, dict):
            llm_summary = response
        else:
            pydantic_response = cast(Union[StreetAnalysis, LandUseAnalysis], response)
            llm_summary = pydantic_response.model_dump()

        return {"llm_summary": llm_summary, "raw_data": data}
    except Exception as e:
        logger.error(f"Langchain processing failed: {e}", exc_info=True)
        raise
