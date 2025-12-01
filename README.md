# Playwright Trace Viewer Router

A service that provides user-friendly URLs to access Playwright trace files stored in Allure reports. This project simplifies the process of viewing Playwright traces by creating a routing layer between Allure test results and the Playwright trace viewer.

## Overview

The Playwright Trace Viewer Router consists of two main components:

1. **Trace Router** - A FastAPI application that:
   - Accepts user-friendly URLs with project, suite, and test names
   - Queries the Allure server to find the corresponding trace file
   - Redirects to the Playwright trace viewer with the correct trace file URL

2. **Trace Viewer** - A containerized instance of the Playwright trace viewer that:
   - Serves the Playwright trace viewer UI
   - Loads trace files from URLs provided by the router

## Prerequisites

- Docker and Docker Compose
- Access to an Allure server with test results containing Playwright traces

## Configuration

Copy the sample environment file to create your own configuration:

```bash
cp dotenv_sample .env
```

Edit the `.env` file to configure:

- `ALLURE_SERVER`: URL of your Allure server
- `ROUTING_DOMAIN`: (Optional) Centralized domain for HTTPS routing (e.g., `https://ip-10-90-107-91.jfrogdev.org`)
- `TRACE_VIEWER_IP`: IP address for the trace viewer service (used for local development)
- `TRACE_ROUTER_IP`: IP address for the router service
- `TRACE_VIEWER_PORT`: Port for the trace viewer service
- `TRACE_ROUTER_PORT`: Port for the router service
- `REQUEST_TIMEOUT`: Timeout for requests to the Allure server

**Note:** When `ROUTING_DOMAIN` is set, the router will use it for generating trace viewer and attachment URLs. Otherwise, it falls back to local configuration.

## Installation and Usage

### Starting the Services

Build and start the services using Docker Compose:

```bash
docker-compose build
docker-compose up -d
```

To rebuild and restart after configuration changes:

```bash
docker-compose build e2e-playwright-trace-router
docker-compose up -d e2e-playwright-trace-router
```

This will start both the router and trace viewer services.

### Accessing Traces

Access your Playwright traces using the following URL format:

```
http://<TRACE_ROUTER_IP>:<TRACE_ROUTER_PORT>/<project_id>/<suite_name>/<test_name>
```

Example:
```
http://localhost:1234/2511040101/TestSuitePaginationScansList/test_scans_list_artifact_pagination
```

### API Endpoints

- `GET /`: Service information and usage instructions
- `GET /health`: Health check endpoint
- `GET /{project_id}/{suite_name}/{test_name}`: Main endpoint to route to a specific trace

## Project Structure

- `router_app.py`: FastAPI application for routing
- `Dockerfile`: Docker configuration for the router service
- `trace-viewer.Dockerfile`: Docker configuration for the Playwright trace viewer
- `docker-compose.yml`: Docker Compose configuration for both services
- `requirements.txt`: Python dependencies
- `dotenv_sample`: Sample environment configuration

## Development

### Running Locally

To run the router service locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python router_app.py
```

## Troubleshooting

If you encounter issues:

1. Check that the Allure server is accessible
2. Verify that the test exists in Allure and has a Playwright trace attachment
3. Check the router logs for detailed error messages:
   ```bash
   docker logs e2e-playwright-trace-router
