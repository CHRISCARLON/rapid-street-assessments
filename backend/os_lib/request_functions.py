import requests
import os
import aiohttp


def fetch_data(endpoint: str) -> dict:
    """
    Synchronous function to fetch data from an endpoint

    Args:
        endpoint: str - The endpoint to fetch data from
    Returns:
        dict - The data from the endpoint
    Raises:
        Exception - If the request fails
    """
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException:
        raise


async def fetch_data_auth(endpoint: str) -> dict:
    """
    Asynchronous function to fetch data from an endpoint using OS API key from environment variables

    Args:
        endpoint: str - The endpoint to fetch data from
    Returns:
        dict - The data from the endpoint
    Raises:
        Exception - If the request fails
    """
    os_key = os.getenv("OS_KEY")
    if not os_key:
        raise ValueError("OS_KEY environment variable is not set")

    headers = {"key": os_key, "Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers) as response:
                response.raise_for_status()
                result = await response.json()
                return result
    except aiohttp.ClientError:
        raise
