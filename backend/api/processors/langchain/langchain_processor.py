import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any, List, Union, cast
from ...types import RouteType


class StreetAnalysis(BaseModel):
    """Structured output for comprehensive street information and assessment"""

    location: List[str] = Field(
        description="Street name, town/area, administrative authority, and identifying information (USRN, classification numbers)"
    )
    road_characteristics: List[str] = Field(
        description="Detailed road physical characteristics: type (slip road, roundabout, etc.), classification, hierarchy, width measurements, length, directionality, surface conditions, and operational state"
    )
    infrastructure: List[str] = Field(
        description="Infrastructure details: pavement presence and coverage, cycle lane presence and coverage, bus lane presence and coverage, street lighting coverage, and any infrastructure measurements"
    )
    restrictions_and_designations: List[str] = Field(
        description="All special designations, restrictions, regulations, and RAMI data: construction zones, parking restrictions, access restrictions, time-based rules, traffic orders, and special designation areas/lines/points with effective dates"
    )
    traffic_management: List[str] = Field(
        description="Traffic flow characteristics: speed limits, directionality, route hierarchy, trunk road status, primary route designation, and traffic management features"
    )
    assessment_notes: List[str] = Field(
        description="Key observations, notable features, potential concerns, maintenance requirements, or important details for street assessment purposes"
    )
    summary: str = Field(
        description="Comprehensive summary of all street information including road classification, physical characteristics, infrastructure, and any restrictions or designations"
    )


class LandUseAnalysis(BaseModel):
    """Structured output for comprehensive land use and area assessment"""

    location: List[str] = Field(
        description="Area identification: street name, town, administrative area, and geographic context"
    )
    land_use_classification: List[str] = Field(
        description="Detailed land use classifications: OS Land Use Tier A (primary classification), Tier B subtypes, property types, and area categorizations (residential, commercial, industrial, mixed-use, etc.)"
    )
    properties_and_sites: List[str] = Field(
        description="All properties and sites identified: names, descriptions, areas (in square meters), addresses, and specific property details"
    )
    area_statistics: List[str] = Field(
        description="Statistical summary: total area coverage, number of properties, breakdown by land use type, average property sizes, and density information"
    )
    notable_features: List[str] = Field(
        description="Landmarks, distinctive buildings, public facilities, educational institutions, religious buildings, monuments, and other significant features"
    )
    contextual_information: List[str] = Field(
        description="Additional context about the area: development status, change types (new, modified, demolished), version dates, and temporal information"
    )
    summary: str = Field(
        description="Comprehensive summary of land use patterns, property distribution, area characteristics, and key features of the assessed area"
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
            logger.info("Processing comprehensive street information and assessment")
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a street assessment and analysis system providing comprehensive information about street infrastructure and characteristics.

Analyze and report ALL available information including:

LOCATION & IDENTIFICATION:
- Street name, USRN, town, administrative authority
- Road classification and hierarchy.
- Classification numbers.

ROAD CHARACTERISTICS:
- Road type and description (slip road, roundabout, main carriageway, etc.)
- Physical measurements: length, width (average and minimum), elevation
- Directionality and operational state
- Route hierarchy and trunk road status

INFRASTRUCTURE:
- Pavement: presence, coverage percentage, width measurements (left/right)
- Cycle lanes: presence, length, coverage percentage, segregation details
- Bus lanes: presence, length, coverage percentage
- Street lighting: coverage level (well-lit, mostly unlit, etc.)
- Include specific measurements in meters and percentages

RESTRICTIONS & DESIGNATIONS:
- All RAMI special designations (areas, lines, points)
- Traffic restrictions, parking restrictions, access controls
- Construction zones, roadworks, temporary traffic orders
- Effective dates and timeframes for restrictions
- Location descriptions for restrictions

TRAFFIC MANAGEMENT:
- Speed limits
- Traffic flow patterns
- Turn restrictions
- Time-based regulations

Be EXHAUSTIVE and PRECISE. Report every roadlink with its full details. Include all measurements, percentages, and specific values. List everything found in the data.""",
                    ),
                    (
                        "user",
                        "Analyze this street data and provide a comprehensive assessment with all available information:\n\n{context}",
                    ),
                ]
            )
            structured_llm = model.with_structured_output(StreetAnalysis)
            chain = prompt | structured_llm

        case RouteType.LAND_USE.value:
            logger.info("Processing comprehensive land use and area assessment")
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a land use assessment and analysis system providing comprehensive information about properties, buildings, and area characteristics.

Analyze and report ALL available information including:

LOCATION & CONTEXT:
- Street name, town, administrative area
- Geographic and administrative boundaries
- Version dates and temporal information

LAND USE CLASSIFICATION:
- OS Land Use Tier A (primary classification)
- OS Land Use Tier B subtypes
- Detailed property type categorizations
- Classification codes and descriptions

PROPERTIES & SITES:
- Every property and site with complete details:
  * Property names (primary and secondary)
  * Descriptions and types
  * Area measurements (in square meters)
  * Addresses when available
  * Change types (new, modified, demolished, etc.)

AREA STATISTICS:
- Total area coverage in square meters
- Total number of properties
- Breakdown by land use type (residential, commercial, industrial, etc.)
- Property density information
- Average property sizes
- Residential vs commercial vs other ratios

NOTABLE FEATURES:
- Landmarks and monuments
- Public facilities and services
- Educational institutions
- Religious buildings
- Distinctive architectural features
- Parks and public spaces

DEVELOPMENT INFORMATION:
- Change status and types
- Version dates and currency of data
- Development patterns and trends

Be EXHAUSTIVE and DETAILED. List every property with its full details including exact area measurements. Provide complete statistical breakdowns. Include all names, descriptions, and quantitative data.""",
                    ),
                    (
                        "user",
                        "Analyze this land use data and provide a comprehensive assessment with all available information:\n\n{context}",
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
