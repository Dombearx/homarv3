# Homarv3 FastAPI Application

A simple FastAPI application template with health check and interaction endpoints, following Python and FastAPI best practices.

## Features

- **Health Check Endpoint** (`/health`): Returns service status and uptime
- **Interaction Endpoint** (`/api/v1/interact`): Processes user interactions with mocked logic (1-second delay)
- **Proper Error Handling**: Custom exceptions and error responses
- **Request/Response Logging**: Comprehensive logging for debugging
- **Type Hints**: Full type annotation support
- **Pydantic Models**: Request/response validation
- **Configuration Management**: Environment-based configuration
- **CORS Support**: Configurable CORS middleware
- **API Documentation**: Auto-generated OpenAPI docs (in debug mode)

## Project Structure

```
homarv3/
├── src/
│   └── homarv3/
│       ├── api/
│       │   └── routes.py          # API route definitions
│       ├── core/
│       │   ├── config.py          # Configuration management
│       │   ├── exceptions.py      # Custom exceptions
│       │   └── logging.py         # Logging configuration
│       ├── models/
│       │   └── schemas.py         # Pydantic models
│       ├── services/
│       │   └── interaction_service.py  # Business logic
│       └── main.py                # FastAPI application
├── tests/
│   └── test_api.py               # API tests
├── main.py                       # Entry point
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── pyproject.toml               # Project configuration
└── env.example                  # Environment variables example
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd homarv3
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **For development**:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Configuration

Copy `env.example` to `.env` and modify as needed:

```bash
cp env.example .env
```

Available configuration options:
- `APP_NAME`: Application name
- `DEBUG`: Enable debug mode
- `HOST`: Server host
- `PORT`: Server port
- `API_PREFIX`: API route prefix
- `CORS_ORIGINS`: CORS allowed origins
- `LOG_LEVEL`: Logging level

## Running the Application

### Development Mode
```bash
python main.py
```

### Production Mode
```bash
uvicorn src.homarv3.main:app --host 0.0.0.0 --port 8000
```

The application will be available at:
- **API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs (debug mode only)

## API Endpoints

### Health Check
- **GET** `/health`
- Returns service status, timestamp, version, and uptime

### Interaction
- **POST** `/api/v1/interact`
- Processes user interactions with mocked logic
- Request body:
  ```json
  {
    "message": "Your message here",
    "user_id": "optional_user_id"
  }
  ```
- Response includes processed message, timestamp, request ID, and processing time

## Testing

Run tests with pytest:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src/homarv3
```

## Code Quality

The project includes several code quality tools:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing

Run all quality checks:
```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
pytest
```

## Development

### Adding New Endpoints

1. Add route handlers in `src/homarv3/api/routes.py`
2. Add Pydantic models in `src/homarv3/models/schemas.py`
3. Add business logic in `src/homarv3/services/`
4. Add tests in `tests/test_api.py`

### Error Handling

Custom exceptions are defined in `src/homarv3/core/exceptions.py` and automatically handled by FastAPI exception handlers.

### Logging

The application uses structured logging. Logs include request/response information and error details.

## License

MIT License - see LICENSE file for details.
