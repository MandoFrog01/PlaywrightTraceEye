import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
import requests
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Playwright Trace Viewer Router",
    description="Routes user-friendly URLs to Playwright trace viewer with Allure integration",
    version="1.0.0"
)

# Configuration from environment variables
ALLURE_SERVER = os.getenv("ALLURE_SERVER")
TRACE_VIEWER_IP = os.getenv("TRACE_VIEWER_IP")
TRACE_VIEWER_PORT = os.getenv("TRACE_VIEWER_PORT")
TRACE_ROUTER_IP = os.getenv("TRACE_ROUTER_IP")
TRACE_ROUTER_PORT = os.getenv("TRACE_ROUTER_PORT")
TRACE_VIEWER_PATH = f"http://{TRACE_VIEWER_IP}:{TRACE_VIEWER_PORT}/trace/index.html"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))


def find_test_in_data(json_data, suite_name, test_name):
    """
    Directly search for a test in the JSON data structure.
    
    Args:
        json_data: The JSON data to search through
        suite_name: Name of the test suite
        test_name: Name of the test
        
    Returns:
        dict: The test data if found, None otherwise
    """
    stack = [json_data]
    current_suite = None
    
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
            
        name = node.get('name', '')
        
        # Identify suite
        if 'TestSuite' in name or 'Test' in name:
            current_suite = name
            
        # Check if this is the test we're looking for
        if current_suite == suite_name and name == test_name and 'uid' in node:
            return node
            
        # Traverse children
        if 'children' in node:
            stack.extend(node['children'])
            
    return None


def get_attachment_by_name(test_result: dict, name: str) -> Optional[dict]:
    def _search_steps(steps: list) -> Optional[dict]:
        """Search through nested steps recursively."""
        for step in steps:
            for att in step.get('attachments', ()):
                if att.get('name') == name:
                    return att

            # Early exit if found in nested steps
            if step.get('steps'):
                result = _search_steps(step['steps'])
                if result:
                    return result
        return None


    # Search beforeStages (setup fixtures)
    for stage in test_result.get('beforeStages', ()):
        for att in stage.get('attachments', ()):
            if att.get('name') == name:
                return att

        if stage.get('steps'):
            result = _search_steps(stage['steps'])
            if result:
                return result

    # Search afterStages (teardown fixtures)
    for stage in test_result.get('afterStages', ()):
        for att in stage.get('attachments', ()):
            if att.get('name') == name:
                return att

        if stage.get('steps'):
            result = _search_steps(stage['steps'])
            if result:
                return result

    return None


def get_test_attachments(project_id: str, suite_name: str, test_name: str) -> Optional[str]:
    """
    Query Allure API to get attachments for a specific test

    :param project_id: Allure project ID
    :param suite_name: Test suite name
    :param test_name: Test name
    :return: Attachment source filename or None
    """
    try:
        # Get suites data from Allure
        url = f"{ALLURE_SERVER}/allure-docker-service/projects/{project_id}/reports/latest/data/suites.json"
        logger.info(f"Fetching suites from: {url}")

        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        suites_data = response.json()

        test_data = find_test_in_data(suites_data, suite_name, test_name)

        if not test_data:
            logger.error(f"Test not found: {suite_name}/{test_name}")
            return None

        # Get the test result details using the UID
        test_uid = test_data.get('uid')
        if test_uid:
            result_url = f"{ALLURE_SERVER}/allure-docker-service/projects/{project_id}/reports/latest/data/test-cases/{test_uid}.json"
            logger.info(f"Fetching test details from: {result_url}")

            result_response = requests.get(result_url, timeout=REQUEST_TIMEOUT)
            result_response.raise_for_status()
            result_data = result_response.json()

            attachment_dict = get_attachment_by_name(result_data, "Test Tracing")
            logger.info(f"Found attachment: {attachment_dict.get('source') if attachment_dict else None}")
            return attachment_dict.get('source') if attachment_dict else None

        return None

    except Exception as e:
        logger.error(f"Error fetching test attachments: {e}")
        return None



@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and container orchestration
    """
    return {"status": "healthy"}


@app.get("/")
async def root():
    """
    Root endpoint with service information and usage instructions
    """
    
    return {
        "service": "Playwright Trace Viewer Router",
        "version": "1.0.0",
        "usage": f"http://{TRACE_ROUTER_IP}:{TRACE_ROUTER_PORT}/{{project_id}}/{{suite_name}}/{{test_name}}",
        "example": f"http://{TRACE_ROUTER_IP}:{TRACE_ROUTER_PORT}/2511040101/TestSuitePaginationScansList/test_scans_list_artifact_pagination",
        "endpoints": {
            "health": "/health",
            "route_to_trace": "/{project_id}/{suite_name}/{test_name}",
            "get_attachment_url": "/api/attachment-url/{project_id}/{suite_name}/{test_name}"
        }
    }


@app.get("/api/attachment-url/{project_id}/{suite_name}/{test_name}")
async def get_attachment_url(project_id: str, suite_name: str, test_name: str):
    """
    Get the attachment URL for a specific test without redirecting

    - **project_id**: Allure project identifier
    - **suite_name**: Test suite name (e.g., TestSuitePaginationScansList)
    - **test_name**: Test method name (e.g., test_scans_list_artifact_pagination)

    Example: `/api/attachment-url/2511040101/TestSuitePaginationScansList/test_scans_list_artifact_pagination`

    This endpoint will:
    1. Query Allure for the test results
    2. Find the Playwright trace attachment
    3. Return the attachment URL and trace viewer URL as JSON

    Returns:
        JSON response with attachment_url, trace_viewer_url, and metadata
    """

    # Get attachments for this test
    attachment_filename = get_test_attachments(project_id, suite_name, test_name)

    if not attachment_filename:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Test not found or no Playwright trace attachments available",
                "project_id": project_id,
                "suite_name": suite_name,
                "test_name": test_name,
                "hint": "Check if the test exists and has Playwright trace attachments"
            }
        )

    # Construct the attachment URL
    attachment_url = (f"{ALLURE_SERVER}/allure-docker-service/projects/{project_id}/"
                     f"reports/latest/data/attachments/{attachment_filename}")

    return {
        "project_id": project_id,
        "suite_name": suite_name,
        "test_name": test_name,
        "attachment_url": attachment_url
    }


@app.get("/{project_id}/{suite_name}/{test_name}")
async def route_to_trace(project_id: str, suite_name: str, test_name: str):
    """
    Route user-friendly URL to Playwright trace viewer

    - **project_id**: Allure project identifier
    - **suite_name**: Test suite name (e.g., TestSuitePaginationScansList)
    - **test_name**: Test method name (e.g., test_scans_list_artifact_pagination)

    Example: `/2511040101/TestSuitePaginationScansList/test_scans_list_artifact_pagination`

    This endpoint will:
    1. Query Allure for the test results
    2. Find the Playwright trace attachment
    3. Redirect to the trace viewer with the attachment URL
    """
    logger.info(f"Routing request: {project_id}/{suite_name}/{test_name}")


    # Get attachments for this test
    attachment_filename = get_test_attachments(project_id, suite_name, test_name)

    if not attachment_filename:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Test not found or no Playwright trace attachments available",
                "project_id": project_id,
                "suite_name": suite_name,
                "test_name": test_name,
                "hint": "Check if the test exists and has Playwright trace attachments"
            }
        )

    # Construct the attachment URL
    attachment_url = (f"{ALLURE_SERVER}/allure-docker-service/projects/{project_id}/"
                     f"reports/latest/data/attachments/{attachment_filename}")

    logger.info(f"Attachment URL: {attachment_url}")
    # Construct the trace viewer URL with the attachment
    trace_viewer_url = f"{TRACE_VIEWER_PATH}?trace={attachment_url}"
    logger.info(trace_viewer_url)


    # Redirect to the trace viewer
    return RedirectResponse(url=trace_viewer_url, status_code=302)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=TRACE_ROUTER_IP, port=int(TRACE_ROUTER_PORT), log_level="info")

