"""
Detailed prompts for AI documentation generation.
Each prompt ensures minimum 500 lines of actual code per stack.
"""

def get_frontend_requirements() -> str:
    """Get detailed frontend stack requirements."""
    return """
FRONTEND STACK REQUIREMENTS (Minimum 500 lines of actual code):

You MUST generate:
1. Complete React/Next.js component files (at least 10 components)
2. Full routing configuration with all routes
3. State management setup (Redux/Zustand/Context)
4. API integration layer with all endpoints
5. Authentication components and logic
6. Form components with validation
7. Layout components (Header, Footer, Sidebar)
8. Dashboard components with charts
9. Data table components with pagination
10. Modal/Dialog components
11. CSS/Tailwind configurations
12. TypeScript interfaces and types
13. Unit test examples
14. Package.json with all dependencies

Include ACTUAL CODE, not descriptions. Example structure:
- src/components/Header.tsx (50+ lines)
- src/components/Dashboard.tsx (100+ lines)
- src/pages/index.tsx (80+ lines)
- src/services/api.ts (100+ lines)
- src/store/index.ts (50+ lines)
- src/types/index.ts (50+ lines)
- src/utils/auth.ts (70+ lines)
"""

def get_backend_requirements() -> str:
    """Get detailed backend stack requirements."""
    return """
BACKEND STACK REQUIREMENTS (Minimum 500 lines of actual code):

You MUST generate:
1. Complete Express/NestJS application setup
2. All API endpoints (CRUD for each entity)
3. Authentication middleware with JWT
4. Database models and repositories
5. Service layer implementations
6. Validation middleware
7. Error handling middleware
8. Logging configuration
9. Email service integration
10. File upload handling
11. WebSocket configuration
12. Queue/Job processing
13. Rate limiting middleware
14. API documentation
15. Environment configuration

Include ACTUAL CODE files:
- src/app.ts (main application) - 80+ lines
- src/controllers/user.controller.ts - 150+ lines
- src/services/auth.service.ts - 100+ lines
- src/middleware/auth.middleware.ts - 50+ lines
- src/models/user.model.ts - 80+ lines
- src/routes/index.ts - 50+ lines
- src/config/database.ts - 40+ lines
"""

def get_database_requirements() -> str:
    """Get detailed database stack requirements."""
    return """
DATABASE STACK REQUIREMENTS (Minimum 500 lines of actual SQL/code):

You MUST generate:
1. Complete database schema (CREATE TABLE statements)
2. All tables with columns, types, constraints
3. Primary keys, foreign keys, indexes
4. Views for complex queries
5. Stored procedures for business logic
6. Triggers for audit trails
7. Functions for calculations
8. Migration files (up and down)
9. Seed data scripts
10. Backup and restore procedures
11. Performance optimization queries
12. User permissions and roles
13. Partitioning strategy
14. Replication configuration

Include ACTUAL SQL code:
- schema.sql (200+ lines with all tables)
- migrations/001_initial.sql (100+ lines)
- procedures.sql (100+ lines)
- triggers.sql (50+ lines)
- indexes.sql (50+ lines)
- views.sql (50+ lines)
- seed_data.sql (50+ lines)
"""

def get_devops_requirements() -> str:
    """Get detailed DevOps stack requirements."""
    return """
DEVOPS STACK REQUIREMENTS (Minimum 500 lines of actual configuration):

You MUST generate:
1. Complete Dockerfile for each service
2. docker-compose.yml with all services
3. Kubernetes manifests (deployments, services, ingress)
4. CI/CD pipeline (GitHub Actions/GitLab CI)
5. Nginx configuration
6. Environment-specific configs (dev, staging, prod)
7. Monitoring setup (Prometheus, Grafana)
8. Logging configuration (ELK stack)
9. Backup scripts
10. Deployment scripts
11. SSL/TLS configuration
12. Load balancer configuration
13. Auto-scaling policies
14. Health check endpoints

Include ACTUAL configuration files:
- Dockerfile.frontend (30+ lines)
- Dockerfile.backend (30+ lines)
- docker-compose.yml (100+ lines)
- .github/workflows/deploy.yml (100+ lines)
- kubernetes/deployment.yaml (80+ lines)
- kubernetes/service.yaml (40+ lines)
- kubernetes/ingress.yaml (40+ lines)
- nginx/nginx.conf (60+ lines)
- scripts/deploy.sh (50+ lines)
"""

def get_complete_prompt_template() -> str:
    """Get the complete prompt template for documentation generation."""
    return """
You are an expert software architect and developer. Generate COMPLETE, PRODUCTION-READY technical documentation with ACTUAL CODE.

CRITICAL REQUIREMENTS:
- Each stack MUST contain MINIMUM 500 lines of ACTUAL CODE
- Do NOT provide descriptions or placeholders
- Write COMPLETE, WORKING code files
- Include ALL configuration files
- Add detailed comments in the code
- Use industry best practices
- Make it production-ready

{project_context}

Now generate the complete technical documentation with the following structure:

{
  "frontend": {
    "title": "Frontend - Complete Implementation",
    "content": "[GENERATE 500+ LINES OF ACTUAL FRONTEND CODE HERE]",
    "technologies": ["Next.js", "React", "TypeScript", "Tailwind CSS", "etc"],
    "estimated_effort": "6-8 weeks"
  },
  "backend": {
    "title": "Backend - Complete Implementation",
    "content": "[GENERATE 500+ LINES OF ACTUAL BACKEND CODE HERE]",
    "technologies": ["Node.js", "NestJS", "PostgreSQL", "Redis", "etc"],
    "estimated_effort": "8-10 weeks"
  },
  "database": {
    "title": "Database - Complete Schema and Scripts",
    "content": "[GENERATE 500+ LINES OF ACTUAL DATABASE CODE HERE]",
    "technologies": ["PostgreSQL", "Redis", "Migrations", "etc"],
    "estimated_effort": "3-4 weeks"
  },
  "devops": {
    "title": "DevOps - Complete Infrastructure",
    "content": "[GENERATE 500+ LINES OF ACTUAL DEVOPS CONFIGURATION HERE]",
    "technologies": ["Docker", "Kubernetes", "CI/CD", "Monitoring", "etc"],
    "estimated_effort": "4-5 weeks"
  }
}

REMEMBER: Each "content" field MUST contain 500+ lines of ACTUAL, EXECUTABLE CODE."""

def get_expansion_prompt(stack_type: str, current_content: str, current_lines: int) -> str:
    """Get prompt to expand insufficient content."""
    missing_lines = 500 - current_lines
    
    return f"""
The {stack_type} documentation currently has only {current_lines} lines. 
You need to add {missing_lines} more lines of ACTUAL CODE.

Current content:
{current_content[:500]}...

Please EXPAND this with:
1. More complete implementations
2. Additional configuration files
3. More detailed code examples
4. Helper functions and utilities
5. Test files
6. Documentation comments

Generate {missing_lines}+ additional lines of ACTUAL CODE for the {stack_type} stack.
"""