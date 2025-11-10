FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache python3 py3-pip

COPY requirements.txt .
COPY router_app.py .
COPY .env .

RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Expose the port from environment
EXPOSE ${TRACE_ROUTER_PORT}

# Use the environment variables for host and port
CMD ["sh", "-c", "python3 -m uvicorn router_app:app --host ${TRACE_ROUTER_IP} --port ${TRACE_ROUTER_PORT}"]

