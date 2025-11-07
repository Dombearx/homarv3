FROM python:3.12-slim

WORKDIR /app

# Install poetry
RUN pip install poetry==1.8.3

# Copy only necessary files for dependency installation
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY main.py ./
COPY src/ ./src/

# Expose port
EXPOSE 8070

# Run the application
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8070"]

