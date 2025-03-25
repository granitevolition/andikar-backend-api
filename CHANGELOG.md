# Changelog

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
