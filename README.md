# Andikar Backend API

Backend API Gateway for Andikar AI services. This API provides a centralized gateway for text humanization, AI detection, and other services.

## Recent Updates

- **Pydantic v2 Migration**: Migrated from Pydantic v1 to v2, implementing the new BaseSettings from pydantic-settings
- **Added Dockerfile**: For containerized deployment
- **Added Startup Script**: Easier deployment with automatic database connection and initialization

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| PORT | Port to run the API on | 8080 |
| DATABASE_URL | Database connection string | sqlite:///./andikar.db |
| DATABASE_PUBLIC_URL | Public database URL (overrides DATABASE_URL if set) | None |
| SECRET_KEY | JWT secret key | "mysecretkey" |
| HUMANIZER_API_URL | URL to the text humanizer service | https://web-production-3db6c.up.railway.app |
| AI_DETECTOR_API_URL | URL to the AI detection service | https://ai-detector-api.example.com |
| DEBUG | Enable debug mode | 0 |

## Running Locally

### Prerequisites

- Python 3.11+
- PostgreSQL (recommended) or SQLite

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/granitevolition/andikar-backend-api.git
   cd andikar-backend-api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Run the application:
   ```bash
   ./start.sh
   ```

## Running with Docker

1. Build the Docker image:
   ```bash
   docker build -t andikar-backend-api .
   ```

2. Run the container:
   ```bash
   docker run -p 8080:8080 \
     -e DATABASE_URL=postgresql://user:password@host:port/dbname \
     -e SECRET_KEY=your_secret_key \
     andikar-backend-api
   ```

## API Endpoints

- **Authentication**:
  - POST `/token`: Obtain JWT token
  - POST `/users/register`: Register a new user

- **User Management**:
  - GET `/users/me`: Get current user details
  - PUT `/users/me`: Update user details

- **Text Services**:
  - POST `/api/humanize`: Humanize text
  - POST `/api/detect`: Detect AI-generated content

- **Payment Integration**:
  - POST `/api/payments/mpesa/initiate`: Initiate M-Pesa payment
  - POST `/api/payments/mpesa/callback`: M-Pesa callback
  - POST `/api/payments/simulate`: Simulate payment (testing only)

- **System**:
  - GET `/`: API information
  - GET `/health`: API health check

## Deployment on Railway

This API is configured for easy deployment on Railway.app:

1. Connect your repository to Railway
2. Add the required environment variables
3. Deploy

Railway will automatically use the provided Dockerfile and startup script.
