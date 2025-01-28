# Unimad Test Backend

This repository contains the backend server for the Unimad Developer Task. This server is required if you're attempting Stage 3 of the task or want full functionality of the frontend application.

## Prerequisites

- Docker Desktop installed on your system
- Basic understanding of Django/DRF (for Stage 3)

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/BVK23/unimad-test-backend
   ```

2. Build and initialize the application:
   ```bash
   # Build the Docker containers
   docker compose build

   # Start containers briefly to create DB
   docker compose up
   # Stop using Ctrl+C after containers are up

   # Run migrations
   docker compose run --rm app sh -c "python manage.py migrate"
   ```

3. Start the server:
   ```bash
   docker compose up
   ```

The server will be available at `http://localhost:8000`

## Admin Interface

- Access the admin interface at `http://localhost:8000/admin`
- Here you can view and manage database contents

- To create a superuser (for admin access):
   ```bash
   # For Windows
   winpty docker-compose run --rm -it app sh -c "python manage.py createsuperuser"
   # For Unix/Linux/Mac
   docker compose run --rm -it app sh -c "python manage.py createsuperuser"
   ```

## Important Notes

- This backend server is essential for the [frontend application](https://github.com/BVK23/unimad-test-frontend) to function properly
- The backend handles:
  - LinkedIn OAuth authentication
  - Access token creation and management
  - API endpoints for frontend functionality

## Stage 3 Resources (Optional)

If you're attempting Stage 3 of the task, you may find these resources helpful:

- [Django Documentation](https://docs.djangoproject.com/en/stable/)
- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- Topics to understand:
  - Django Views and URLs
  - DRF ViewSets and Serializers
  - API Endpoint creation
  - Authentication and Permissions

Feel free to use any additional resources to understand these concepts.
