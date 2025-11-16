from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class OSFeatures(ABC):
    """
    Abstract base class for OS features

    This class is used to get the features of a given path type and usrn.
    For land-use routes, bbox is also required. bbox_crs and crs are optional.
    """

    @abstractmethod
    async def get_features(
        self,
        path_type: str,
        usrn: Optional[str] = None,
        bbox: Optional[str] = None,
        bbox_crs: Optional[str] = None,
        crs: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass


class LLMSummary(ABC):
    """
    Abstract base class for LLM summary

    This class is used to summarize the results of a given data and route type.
    """

    @abstractmethod
    async def summarise_results(
        self, data: Dict[str, Any], route_type: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def pre_process_street_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def pre_process_land_use_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass


class BBOXGeometry(ABC):
    """
    Abstract base class for BBOX geometry

    This class is used to get the bounding box of a given USRN and buffer distance.
    """

    @abstractmethod
    async def get_bbox_from_usrn(self, usrn: str, buffer_distance: float = 50) -> tuple:
        pass
