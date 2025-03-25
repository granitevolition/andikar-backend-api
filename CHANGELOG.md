# Changelog

## [1.0.6] - 2025-03-25

### Fixed
- Fixed database migration error with existing tables by adding checks before running migrations
- Added improved global exception handling in FastAPI app
- Enhanced error logging with stack traces for better debugging
- Improved root endpoint with detailed environment information
- Added better authentication error handling
- Fixed Transaction model field references in callback endpoint

## [1.0.5] - 2025-03-25

### Fixed
- Fixed SQLAlchemy SQL execution error by using text() function for prepared statements
- Updated database connection code in all modules to use text() function
- Improved error handling for database connections 
- Fixed compatibility issue with newer versions of SQLAlchemy

## [1.0.4] - 2025-03-25

### Fixed
- Added support for `DATABASE_PUBLIC_URL` when `DATABASE_URL` is not reachable
- Added network diagnostics tools to Docker image for better connection debugging
- Added automatic host reachability checks with fallback to public URLs
- Enhanced database connection code to try multiple connection methods
- Added IP resolution diagnostics to help troubleshoot Railway networking issues
- Improved SQLite fallback mechanisms when PostgreSQL is unavailable

## [1.0.3] - 2025-03-25

### Fixed
- Fixed missing DATABASE_URL environment variable issues
- Added SQLite fallback for database when no PostgreSQL is available
- Enhanced startup script to handle missing environment variables
- Added auto-detection of Railway's PostgreSQL environment variables
- Improved robustness of the application when key services are unavailable
- Added detailed Railway deployment instructions in README

## [1.0.2] - 2025-03-25

### Fixed
- Fixed database connection issues in the Alembic migrations
- Added retry logic and better error handling for database connections
- Added database health check in startup script to wait for database to be ready
- Improved logging for database connection attempts
- Enhanced PostgreSQL connection parameters for better reliability

## [1.0.1] - 2025-03-25

### Fixed
- Fixed SQLAlchemy model error by renaming reserved 'metadata' attribute to 'transaction_metadata' in Transaction model
- Fixed PORT environment variable handling in startup.sh script 
- Fixed Procfile to use startup.sh for proper environment handling
- Updated initial migration file to use 'transaction_metadata' instead of 'metadata'
- Simplified Docker Compose command to use startup.sh script
- Updated README with PostgreSQL information and troubleshooting guidelines

## [1.0.0] - 2025-03-25

### Added
- Initial release of the Andikar Backend API Gateway
- Authentication with JWT tokens
- User management
- Text humanization API integration
- PostgreSQL database integration with SQLAlchemy
- Docker and Docker Compose support
- Railway.app deployment configuration
