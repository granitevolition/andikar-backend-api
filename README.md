# Andikar Backend API Gateway

A comprehensive backend API gateway that integrates the Andikar frontend with various external services including text humanization, AI detection, and M-Pesa payments.

## Features

- **API Gateway**: Central interface for all external services
- **Authentication**: JWT-based authentication and authorization
- **User Management**: Registration, profiles, and subscription management
- **Service Integration**:
  - Text Humanizer API
  - AI Detection API (configurable)
  - M-Pesa Payment Processing
- **MongoDB Integration**: Persistent storage for users, transactions, and logs
- **Rate Limiting**: Prevent API abuse
- **Logging & Monitoring**: Comprehensive logging for debugging and analytics
- **Health Checks**: Monitor system and service health
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Technologies

- **FastAPI**: High-performance web framework
- **MongoDB**: NoSQL database for flexible data storage
- **Pydantic**: Data validation and settings management
- **JWT**: Secure authentication
- **HTTPX**: Asynchronous HTTP client
- **Docker**: Containerization for consistent deployment
- **Nginx**: Reverse proxy and load balancing (optional)

## Prerequisites

- Python 3.9+
- Docker and Docker Compose (recommended)
- MongoDB 4.4+ (handled by Docker)

## Quick Start

### Using Docker (Recommended)

1. Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/granitevolition/andikar-backend-api.git
cd andikar-backend-api
```

2. Copy the example environment file and configure it:

```bash
cp .env.example .env
# Edit .env file with your settings
```

3. Start the services using Docker Compose:

```bash
docker-compose up --build
```

4. The API will be available at http://localhost:8000

### Manual Installation

1. Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/granitevolition/andikar-backend-api.git
cd andikar-backend-api
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the example environment file and configure it:

```bash
cp .env.example .env
# Edit .env file with your settings
```

5. Start the application:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

6. The API will be available at http://localhost:8000

## Configuration

The application is configured using environment variables, which can be set in the `.env` file:

### General Settings
- `PORT`: Port to run the application on (default: 8000)
- `SECRET_KEY`: Secret key for JWT token generation
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Database Settings
- `MONGODB_URL`: MongoDB connection URL
- `DATABASE_NAME`: MongoDB database name

### API Endpoints
- `HUMANIZER_API_URL`: URL of the text humanizer API
- `AI_DETECTOR_API_URL`: URL of the AI detection API

### M-Pesa Integration
- `MPESA_CONSUMER_KEY`: M-Pesa API consumer key
- `MPESA_CONSUMER_SECRET`: M-Pesa API consumer secret
- `MPESA_PASSKEY`: M-Pesa API passkey
- `MPESA_SHORTCODE`: M-Pesa shortcode
- `MPESA_CALLBACK_URL`: URL for M-Pesa callbacks

### Rate Limiting
- `RATE_LIMIT_REQUESTS`: Maximum requests per period
- `RATE_LIMIT_PERIOD`: Period for rate limiting in seconds

## API Documentation

The API documentation is available at http://localhost:8000/docs when the application is running. This provides a detailed interactive documentation of all available endpoints.

## Key API Endpoints

### Authentication
- `POST /token`: Authenticate user and get JWT token

### User Management
- `POST /users/register`: Register a new user
- `GET /users/me`: Get current user profile
- `PUT /users/me`: Update user profile

### Text Services
- `POST /api/humanize`: Humanize text
- `POST /api/detect`: Detect AI content

### Payments
- `POST /api/payments/mpesa/initiate`: Initiate M-Pesa payment
- `POST /api/payments/mpesa/callback`: Receive M-Pesa payment notification
- `POST /api/payments/simulate`: Simulate payment (for testing)

### System
- `GET /health`: Check system health
- `GET /`: API information

## Deployment

### Railway Deployment

This application is configured for easy deployment on Railway.app:

1. Push the repository to GitHub
2. Create a new project on Railway.app
3. Link the GitHub repository
4. Add environment variables from your `.env` file
5. Deploy the application

## License

This project is licensed under the MIT License - see the LICENSE file for details.