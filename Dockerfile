FROM python:3.12-slim

WORKDIR /app

# Install Node.js and npm (required for npx and Google Calendar MCP server)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @cocal/google-calendar-mcp

# Install poetry
RUN pip install poetry==2.2.1

# Copy only necessary files for dependency installation
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --without dev

# Copy application code
COPY main.py ./
COPY src/ ./src/

# Google Calendar credentials are mounted by docker-compose (not baked into the image), so a
# refreshed token survives container re-creation.

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Run the application
CMD ["poetry", "run", "python", "main.py"] 

