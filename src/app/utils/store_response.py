import asyncio
import json
import os

# import aiofiles
from typing import Any, Dict


async def store_json_response(params: Dict[str, Any]) -> bool:
    """
    Stores a JSON response to the specified file path asynchronously.

    Args:
        params (Dict[str, Any]): Dictionary containing 'response' and 'file_path'
            - response: The JSON response to store
            - file_path: The path where to save the JSON file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract response and file_path from the params dictionary
        response = params["response"]
        file_path = params["file_path"]

        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            # Use asyncio.to_thread for CPU-bound operations that don't have async alternatives
            await asyncio.to_thread(
                lambda: os.makedirs(directory, exist_ok=True)
            )

        # Prepare the JSON data (CPU-bound operation)
        json_data = await asyncio.to_thread(
            lambda: json.dumps(response, indent=4, ensure_ascii=False)
        )

        # Write the JSON data to file with proper formatting (I/O-bound operation)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        # async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        #     await f.write(json_data)

        return True

    except TypeError as e:
        print(f"Error: Response is not JSON serializable - {str(e)}")
        return False
    except IOError as e:
        print(f"Error: Failed to write to file {file_path} - {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return False


async def store_txt_response(params: Dict[str, Any]) -> bool:
    """
    Stores a text response to the specified file path asynchronously.

    Args:
        params (Dict[str, Any]): Dictionary containing 'response' and 'file_path'
            - response: The text response to store
            - file_path: The path where to save the text file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract response and file_path from the params dictionary
        response = params["response"]
        file_path = params["file_path"]

        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            # Use asyncio.to_thread for CPU-bound operations that don't have async alternatives
            await asyncio.to_thread(
                lambda: os.makedirs(directory, exist_ok=True)
            )

        # Write the text data to file with proper formatting (I/O-bound operation)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response)
        # async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        #     await f.write(response)

        return True

    except IOError as e:
        print(f"Error: Failed to write to file {file_path} - {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return False
