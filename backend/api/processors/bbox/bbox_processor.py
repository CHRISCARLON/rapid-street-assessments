import os
from shapely.wkt import loads
import asyncio

from logging_config import get_logger
from ...db.database_pool import MotherDuckPool

logger = get_logger(__name__)


async def get_bbox_from_usrn(usrn: str, buffer_distance: float = 50) -> tuple:
    """Get bounding box coordinates for a given USRN"""
    pool = MotherDuckPool()
    try:
        async with pool.get_connection() as con:
            schema = os.getenv("USRN_SCHEMA")
            table_name = os.getenv("USRN_TABLE")

            logger.debug(f"Schema: {schema}, Table: {table_name}")

            if not all([schema, table_name]):
                raise ValueError("Missing schema or table name environment variables")

            query = f"""
                SELECT geometry
                FROM {schema}.{table_name}
                WHERE usrn = ?
            """

            logger.debug(f"Executing query for USRN: {usrn}")
            result = await asyncio.to_thread(con.execute, query, [usrn])
            df = result.fetchdf()

            if df.empty:
                logger.warning(f"No geometry found for USRN: {usrn}")
                raise ValueError(f"No geometry found for USRN: {usrn}")

            logger.debug(f"Query result shape: {df.shape}")
            geom = loads(df["geometry"].iloc[0])
            buffered = geom.buffer(
                buffer_distance, cap_style="square", single_sided=False
            )
            logger.debug(f"Successfully buffered geometry for USRN: {usrn}")

            return tuple(round(coord) for coord in buffered.bounds)
    except Exception as e:
        logger.error(f"Error in get_bbox_from_usrn: {str(e)}")
        raise
