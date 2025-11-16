from typing import Dict, Any


async def langchain_pre_process_street_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplifies street information data by removing redundant info and extracting roadlink details.

    Args:
        data: Raw street information data dictionary

    Returns:
        Dict containing simplified street data including roadlinks
    """

    # Extract common street information from first feature
    if not data.get("features"):
        return data

    # Find the street feature (should be first, but let's be safe)
    street_feature = None
    for feature in data["features"]:
        if feature["properties"].get("usrn"):
            street_feature = feature
            break

    if not street_feature:
        return data

    base_street = {
        "usrn": street_feature["properties"]["usrn"],
        "street_name": street_feature["properties"].get("designatedname1_text"),
        "town": street_feature["properties"].get("townname1_text"),
        "authority": {
            "name": street_feature["properties"].get("responsibleauthority_name"),
            "area": street_feature["properties"].get("administrativearea1_text"),
        },
        "geometry": {"length": street_feature["properties"].get("geometry_length")},
        "operational_state": street_feature["properties"].get("operationalstate"),
        "operational_state_date": street_feature["properties"].get("operationalstatedate"),
    }

    # Separate features by type
    simplified_designations = []
    simplified_roadlinks = []

    for feature in data["features"]:
        props = feature["properties"]

        # Identify feature type based on properties
        # Roadlinks have 'osid' or 'toid' and roadclassification
        is_roadlink = "osid" in props or ("toid" in props and "roadclassification" in props)

        # Skip the base street feature
        if props.get("description") == "Designated Street Name":
            continue

        if is_roadlink:
            # Extract roadlink information
            roadlink = {
                "id": props.get("osid"),
                "name": props.get("name1_text"),
                "description": props.get("description"),
                "classification": {
                    "type": props.get("roadclassification"),
                    "number": props.get("roadclassificationnumber"),
                    "hierarchy": props.get("routehierarchy"),
                },
                "physical": {
                    "length_m": props.get("geometry_length_m"),
                    "width_avg_m": props.get("roadwidth_average"),
                    "width_min_m": props.get("roadwidth_minimum"),
                },
                "directionality": props.get("directionality"),
                "operational_state": props.get("operationalstate"),
                "infrastructure": {
                    "pavement_left_m": props.get("presenceofpavement_left_m"),
                    "pavement_right_m": props.get("presenceofpavement_right_m"),
                    "pavement_coverage_pct": props.get("presenceofpavement_overallpercentage"),
                    "cycle_lane_m": props.get("presenceofcyclelane_overall_m"),
                    "cycle_lane_coverage_pct": props.get("presenceofcyclelane_overallpercentage"),
                    "bus_lane_m": props.get("presenceofbuslane_overall_m"),
                    "bus_lane_coverage_pct": props.get("presenceofbuslane_overallpercentage"),
                    "street_lighting": props.get("presenceofstreetlight_coverage"),
                },
            }

            # Remove None values
            roadlink = {k: v for k, v in roadlink.items() if v is not None}
            if "physical" in roadlink:
                roadlink["physical"] = {k: v for k, v in roadlink["physical"].items() if v is not None}
            if "infrastructure" in roadlink:
                roadlink["infrastructure"] = {k: v for k, v in roadlink["infrastructure"].items() if v is not None}
            if "classification" in roadlink:
                roadlink["classification"] = {k: v for k, v in roadlink["classification"].items() if v is not None}

            simplified_roadlinks.append(roadlink)
        else:
            # Handle designation features (RAMI data)
            simplified_feature = {
                "type": props.get("description"),
                "designation": props.get("designation"),
                "timeframe": props.get("timeinterval"),
                "location": props.get("locationdescription"),
                "details": props.get("designationdescription"),
                "effective_date": props.get("effectivestartdate"),
                "end_date": props.get("effectiveenddate"),
            }

            # Only include non-None values
            simplified_feature = {
                k: v for k, v in simplified_feature.items() if v is not None
            }
            simplified_designations.append(simplified_feature)

    result = {
        "street": base_street,
        "designations": simplified_designations,
        "metadata": {
            "timestamp": data.get("timeStamp"),
            "number_returned": data.get("numberReturned"),
        },
    }

    # Only include roadlinks if we found any
    if simplified_roadlinks:
        result["roadlinks"] = simplified_roadlinks

    return result


async def langchain_pre_process_land_use_info(data: dict) -> dict:
    """
    Simplifies land use data by extracting key information and removing redundant info.

    Args:
        data: Raw land use data dictionary

    Returns:
        Dict containing simplified properties and summary stats
    """
    if not data.get("features"):
        return data

    simplified_features = []
    total_area = 0
    residential_count = 0
    commercial_count = 0

    for feature in data["features"]:
        props = feature["properties"]

        # Extract core property information
        property_info = {
            "property": {
                "name": props.get("name1_text"),
                "secondary_name": props.get("name2_text"),
                "description": props.get("description"),
                "area": props.get("geometry_area"),
            },
            "classification": {
                "type": props.get("oslandusetiera"),
                "subtypes": props.get("oslandusetierb", []),
                "status": props.get("changetype"),
            },
        }

        # Update statistics
        if property_info["property"]["area"]:
            total_area += property_info["property"]["area"]

        if "Residential" in property_info["classification"]["type"]:
            residential_count += 1
        elif "Commercial" in property_info["classification"]["type"]:
            commercial_count += 1

        simplified_features.append(property_info)

    # Calculate summary statistics
    stats = {
        "total_properties": len(simplified_features),
        "total_area": round(total_area, 2),
        "residential_count": residential_count,
        "commercial_count": commercial_count,
        "average_property_size": round(total_area / len(simplified_features), 2)
        if simplified_features
        else 0,
    }

    return {
        "features": simplified_features,
        "statistics": stats,
        "metadata": {
            "count": data.get("numberReturned"),
            "timestamp": data.get("timeStamp"),
        },
    }
