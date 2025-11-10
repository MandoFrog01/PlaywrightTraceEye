FROM node:20-alpine

WORKDIR /app

# Install only the Playwright package (without browsers)
RUN npm install -g playwright@1.49.0

# Copy env file
COPY .env .

# Expose the trace viewer port
EXPOSE ${TRACE_VIEWER_PORT}

# Start the trace viewer server
CMD ["sh", "-c", "npx playwright show-trace --host 0.0.0.0 --port ${TRACE_VIEWER_PORT}"]
