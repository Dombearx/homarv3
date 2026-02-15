FROM python:3.12-slim

WORKDIR /app

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

# copy credentials for google calendar mcp server
COPY gcp-oauth.keys.json ./
COPY mcp-google-calendar-token.json ./


# Run the application
CMD ["poetry", "run", "python", "main.py"] 

