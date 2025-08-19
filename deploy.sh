#!/bin/bash

# =============================================================================
# IA Compose API - Deploy Script for Coolify
# =============================================================================
# This script helps deploy the IA Compose API to Coolify
# URL: https://compose.demandei.com.br
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ia-compose-api"
DOMAIN="compose.demandei.com.br"
REGISTRY="ghcr.io/demandei"  # Update with your registry

echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}IA Compose API - Deployment Script${NC}"
echo -e "${GREEN}==============================================================================${NC}"

# Function to print colored messages
print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in production environment
check_environment() {
    print_info "Checking environment..."
    
    if [ ! -f ".env.production" ]; then
        print_error ".env.production file not found!"
        print_info "Please create .env.production with your production settings"
        exit 1
    fi
    
    print_success "Environment file found"
}

# Build Docker image
build_image() {
    print_info "Building Docker image..."
    
    # Build with production optimizations
    docker build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --cache-from ${REGISTRY}/${PROJECT_NAME}:latest \
        --tag ${REGISTRY}/${PROJECT_NAME}:latest \
        --tag ${REGISTRY}/${PROJECT_NAME}:$(git rev-parse --short HEAD) \
        --file Dockerfile \
        .
    
    print_success "Docker image built successfully"
}

# Push to registry (if using external registry)
push_image() {
    print_info "Pushing image to registry..."
    
    # Login to registry if needed
    # docker login ${REGISTRY}
    
    docker push ${REGISTRY}/${PROJECT_NAME}:latest
    docker push ${REGISTRY}/${PROJECT_NAME}:$(git rev-parse --short HEAD)
    
    print_success "Image pushed to registry"
}

# Deploy to Coolify
deploy_coolify() {
    print_info "Deploying to Coolify..."
    
    # Option 1: Using Coolify CLI (if installed)
    if command -v coolify &> /dev/null; then
        coolify deploy \
            --app ${PROJECT_NAME} \
            --domain ${DOMAIN} \
            --env-file .env.production
    else
        print_info "Coolify CLI not found. Using Docker Compose..."
        
        # Option 2: Using docker-compose for Coolify
        docker-compose -f docker-compose.production.yml up -d
    fi
    
    print_success "Deployment initiated"
}

# Run database migrations (if needed)
run_migrations() {
    print_info "Running database migrations..."
    
    # Example: Run Alembic migrations
    # docker exec ${PROJECT_NAME} alembic upgrade head
    
    print_info "No migrations to run (using local storage)"
}

# Health check
health_check() {
    print_info "Performing health check..."
    
    # Wait for service to be ready
    sleep 10
    
    # Check health endpoint
    response=$(curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN}/health || echo "000")
    
    if [ "$response" = "200" ]; then
        print_success "Health check passed! Service is running at https://${DOMAIN}"
    else
        print_error "Health check failed. Response code: $response"
        print_info "Checking logs..."
        docker logs ${PROJECT_NAME} --tail 50
        exit 1
    fi
}

# Create necessary volumes and directories
prepare_volumes() {
    print_info "Preparing volumes..."
    
    # Create volume directories if they don't exist
    mkdir -p volumes/redis
    mkdir -p storage/documents
    mkdir -p storage/sessions
    mkdir -p logs
    
    # Set permissions
    chmod 755 volumes/redis
    chmod 755 storage/documents
    chmod 755 storage/sessions
    chmod 755 logs
    
    print_success "Volumes prepared"
}

# Main deployment flow
main() {
    echo ""
    print_info "Starting deployment process..."
    echo ""
    
    # Step 1: Check environment
    check_environment
    
    # Step 2: Prepare volumes
    prepare_volumes
    
    # Step 3: Build image
    build_image
    
    # Step 4: Push to registry (optional)
    # push_image
    
    # Step 5: Deploy to Coolify
    deploy_coolify
    
    # Step 6: Run migrations
    run_migrations
    
    # Step 7: Health check
    health_check
    
    echo ""
    print_success "Deployment completed successfully!"
    echo -e "${GREEN}==============================================================================${NC}"
    echo -e "${GREEN}Service URL: https://${DOMAIN}${NC}"
    echo -e "${GREEN}API Docs: https://${DOMAIN}/docs${NC}"
    echo -e "${GREEN}Health: https://${DOMAIN}/health${NC}"
    echo -e "${GREEN}==============================================================================${NC}"
}

# Handle script arguments
case "${1:-}" in
    build)
        build_image
        ;;
    push)
        push_image
        ;;
    deploy)
        deploy_coolify
        ;;
    health)
        health_check
        ;;
    prepare)
        prepare_volumes
        ;;
    *)
        main
        ;;
esac