"""
Documents Generation API endpoint (API 4).
Handles final document generation with separated technology stacks.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
import logging

from app.models.api_models import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    StackDocumentation,
    ErrorResponse
)
from app.middleware.auth import verify_demandei_api_key
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Create router without global authentication dependency
router = APIRouter(
    prefix="/v1/documents",
    tags=["documents"]
)

# External session storage reference
from app.api.v1.questions import session_storage


@router.post("/generate", response_model=DocumentGenerationResponse)
async def generate_documents(
    request: DocumentGenerationRequest,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> DocumentGenerationResponse:
    """
    Generate final project documentation separated by technology stacks.
    
    This is API 4 of the 4-API workflow. It generates comprehensive
    technical documentation organized by technology stacks (Frontend,
    Backend, Database, DevOps) based on confirmed project requirements.
    
    Args:
        request: Document generation request with session ID and options
        authenticated: Authentication verification (injected)
        
    Returns:
        DocumentGenerationResponse: Generated documentation by stack
        
    Raises:
        HTTPException: If session not found or document generation fails
    """
    try:
        logger.info(f"Generating documents for session {request.session_id}")
        
        # Validate session exists and is confirmed
        if request.session_id not in session_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="SESSION_NOT_FOUND",
                    message="Session not found or expired",
                    session_id=request.session_id
                ).dict()
            )
        
        session_data = session_storage[request.session_id]
        
        # Check if summary was confirmed
        if session_data.get("status") != "confirmed_ready_for_documents":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="SUMMARY_NOT_CONFIRMED",
                    message="Summary must be confirmed before generating documents",
                    session_id=request.session_id
                ).dict()
            )
        
        # Generate documentation for each stack
        stacks = []
        
        # Frontend Documentation
        frontend_doc = _generate_frontend_documentation(session_data, request.include_implementation_details)
        stacks.append(frontend_doc)
        
        # Backend Documentation
        backend_doc = _generate_backend_documentation(session_data, request.include_implementation_details)
        stacks.append(backend_doc)
        
        # Database Documentation
        database_doc = _generate_database_documentation(session_data, request.include_implementation_details)
        stacks.append(database_doc)
        
        # DevOps Documentation
        devops_doc = _generate_devops_documentation(session_data, request.include_implementation_details)
        stacks.append(devops_doc)
        
        response = DocumentGenerationResponse(
            session_id=request.session_id,
            stacks=stacks,
            generated_at=datetime.utcnow(),
            total_estimated_effort="16-24 semanas de desenvolvimento",
            recommended_timeline="4-6 meses incluindo testes e deployment"
        )
        
        # Store generated documents in session
        session_data["generated_documents"] = response.dict()
        session_data["status"] = "completed"
        
        logger.info(f"Documents generated successfully for session {request.session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DOCUMENT_GENERATION_FAILED",
                message="Failed to generate project documents",
                details={"error": str(e)},
                session_id=request.session_id
            ).dict()
        )


def _generate_frontend_documentation(session_data: dict, include_details: bool) -> StackDocumentation:
    """Generate frontend stack documentation."""
    
    content = """# Frontend - Documentação Técnica

## Arquitetura Frontend

### Tecnologias Selecionadas
- **Framework**: React 18+ com Next.js 14
- **Linguagem**: TypeScript
- **Estilização**: Tailwind CSS + Styled Components
- **Gerenciamento de Estado**: Zustand ou Redux Toolkit
- **Roteamento**: Next.js App Router

### Estrutura do Projeto
```
src/
├── app/                 # Next.js App Router
├── components/          # Componentes reutilizáveis
├── hooks/              # Custom hooks
├── lib/                # Utilitários e configurações
├── store/              # Gerenciamento de estado
└── types/              # Definições TypeScript
```

### Componentes Principais
1. **Layout Components**
   - Header/Navigation
   - Sidebar
   - Footer
   - Loading States

2. **Feature Components**
   - Dashboard
   - Forms
   - Tables/Lists
   - Modals/Dialogs

### APIs e Integrações
- Integração com backend via Axios/Fetch
- Autenticação JWT
- Upload de arquivos
- Notificações em tempo real (WebSocket)

### Performance e SEO
- Server-Side Rendering (SSR)
- Static Site Generation (SSG)
- Code Splitting automático
- Otimização de imagens
- Meta tags dinâmicas

### Testes
- Jest + Testing Library para testes unitários
- Cypress para testes E2E
- Storybook para documentação de componentes
"""

    if include_details:
        content += """
### Implementação Detalhada

#### Configuração Inicial
```bash
npx create-next-app@latest projeto --typescript --tailwind --eslint
cd projeto
npm install zustand axios react-hook-form zod
```

#### Estrutura de Componentes
```typescript
// components/ui/Button.tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
  onClick?: () => void
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  children,
  onClick
}) => {
  return (
    <button
      className={`btn btn-${variant} btn-${size}`}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
```

#### Store Configuration (Zustand)
```typescript
// store/appStore.ts
import { create } from 'zustand'

interface AppState {
  user: User | null
  isLoading: boolean
  setUser: (user: User) => void
  setLoading: (loading: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  isLoading: false,
  setUser: (user) => set({ user }),
  setLoading: (isLoading) => set({ isLoading })
}))
```
"""
    
    return StackDocumentation(
        stack_type="frontend",
        title="Frontend Development Stack",
        content=content,
        technologies=["React", "Next.js", "TypeScript", "Tailwind CSS", "Zustand"],
        estimated_effort="6-8 semanas"
    )


def _generate_backend_documentation(session_data: dict, include_details: bool) -> StackDocumentation:
    """Generate backend stack documentation."""
    
    content = """# Backend - Documentação Técnica

## Arquitetura Backend

### Tecnologias Selecionadas
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0
- **Validação**: Pydantic V2
- **Autenticação**: JWT com FastAPI-Users
- **Cache**: Redis
- **Task Queue**: Celery + Redis

### Estrutura do Projeto
```
src/
├── api/                # Endpoints da API
├── core/               # Configurações e utilitários
├── db/                 # Database models e migrations
├── services/           # Lógica de negócio
├── schemas/            # Pydantic models
└── tests/              # Testes automatizados
```

### Endpoints Principais
1. **Autenticação**
   - POST /auth/login
   - POST /auth/register
   - POST /auth/refresh

2. **Usuários**
   - GET /users/me
   - PUT /users/me
   - GET /users/{id}

3. **Core Features**
   - CRUD operations
   - File uploads
   - Search endpoints
   - Reporting APIs

### Arquitetura de Serviços
- Repository Pattern para acesso a dados
- Service Layer para lógica de negócio
- Dependency Injection nativo do FastAPI
- Background tasks para operações assíncronas

### Segurança
- Autenticação JWT
- Rate limiting
- CORS configurado
- Validação de entrada robusta
- Logs de auditoria

### Performance
- Connection pooling
- Query optimization
- Caching estratégico
- Compressão de responses
"""

    if include_details:
        content += """
### Implementação Detalhada

#### Configuração do Projeto
```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.connect()
    yield
    # Shutdown
    await database.disconnect()

app = FastAPI(
    title="Project API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Model Example
```python
# db/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### Service Layer
```python
# services/user_service.py
from typing import Optional
from db.models import User
from schemas.user import UserCreate, UserUpdate

class UserService:
    async def create_user(self, user_data: UserCreate) -> User:
        # Implementation
        pass
    
    async def get_user(self, user_id: int) -> Optional[User]:
        # Implementation
        pass
```
"""
    
    return StackDocumentation(
        stack_type="backend",
        title="Backend Development Stack",
        content=content,
        technologies=["FastAPI", "Python", "SQLAlchemy", "Pydantic", "Redis", "Celery"],
        estimated_effort="8-10 semanas"
    )


def _generate_database_documentation(session_data: dict, include_details: bool) -> StackDocumentation:
    """Generate database stack documentation."""
    
    content = """# Database - Documentação Técnica

## Arquitetura de Dados

### Tecnologias Selecionadas
- **SGBD Principal**: PostgreSQL 15+
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Backup**: pg_dump + cloud storage

### Estrutura do Banco

#### Tabelas Principais
1. **users** - Gestão de usuários
2. **projects** - Projetos do sistema
3. **sessions** - Sessões de usuário
4. **audit_logs** - Logs de auditoria

### Schema de Dados
```sql
-- Usuários
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projetos
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Estratégia de Backup
- Backup diário automático
- Retenção de 30 dias
- Backup incremental a cada 6 horas
- Teste de restore mensal

### Performance
- Índices estratégicos
- Query optimization
- Connection pooling
- Particionamento por data (se necessário)

### Segurança
- Encriptação em repouso
- SSL/TLS para conexões
- Usuários com privilégios mínimos
- Auditoria de acesso
"""

    if include_details:
        content += """
### Implementação Detalhada

#### Configuração Database
```python
# core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_database():
    async with AsyncSessionLocal() as session:
        yield session
```

#### Migration Setup
```bash
# Inicializar Alembic
alembic init alembic

# Criar migration
alembic revision --autogenerate -m "Initial migration"

# Aplicar migration
alembic upgrade head
```

#### Índices Recomendados
```sql
-- Performance indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_projects_owner_id ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at);

-- Composite indexes
CREATE INDEX idx_projects_owner_status ON projects(owner_id, status);
```
"""
    
    return StackDocumentation(
        stack_type="database",
        title="Database Stack",
        content=content,
        technologies=["PostgreSQL", "Redis", "SQLAlchemy", "Alembic"],
        estimated_effort="2-3 semanas"
    )


def _generate_devops_documentation(session_data: dict, include_details: bool) -> StackDocumentation:
    """Generate DevOps stack documentation."""
    
    content = """# DevOps - Documentação Técnica

## Infraestrutura e Deploy

### Tecnologias Selecionadas
- **Cloud Provider**: AWS (ou Azure/GCP)
- **Containerização**: Docker + Docker Compose
- **Orquestração**: Amazon ECS ou Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoramento**: CloudWatch + Sentry
- **CDN**: CloudFront

### Ambientes
1. **Development** - Local com Docker Compose
2. **Staging** - Cloud environment para testes
3. **Production** - Cloud environment otimizado

### Arquitetura de Deploy
```
Internet → LoadBalancer → Frontend (S3+CloudFront)
                      ↓
                   API Gateway → Backend (ECS)
                                   ↓
                              Database (RDS)
                              Cache (ElastiCache)
```

### Pipeline CI/CD
1. **Commit** → GitHub
2. **Tests** → Automated testing
3. **Build** → Docker images
4. **Deploy** → Staging environment
5. **Approval** → Manual review
6. **Production** → Automatic deployment

### Monitoramento
- Application Performance Monitoring (APM)
- Error tracking com Sentry
- Logs centralizados
- Métricas de negócio
- Alertas automáticos

### Segurança
- HTTPS everywhere
- WAF (Web Application Firewall)
- VPC com subnets privadas
- IAM roles com menor privilégio
- Secrets management

### Backup Strategy
- Database backups automáticos
- Application data backup
- Infrastructure as Code backup
- Disaster recovery plan
"""

    if include_details:
        content += """
### Implementação Detalhada

#### Docker Configuration
```dockerfile
# Dockerfile (Backend)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/appdb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

#### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml run --rm backend pytest
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to AWS
        run: |
          # AWS deployment commands
```
"""
    
    return StackDocumentation(
        stack_type="devops",
        title="DevOps and Infrastructure Stack",
        content=content,
        technologies=["Docker", "AWS", "GitHub Actions", "CloudWatch", "Terraform"],
        estimated_effort="3-4 semanas"
    )


@router.get("/health")
async def documents_health_check():
    """Health check for documents service."""
    return {
        "status": "healthy",
        "service": "document-generation",
        "version": "1.0.0"
    }