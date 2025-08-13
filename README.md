# IA Compose API - REST Microservice for Demandei Platform

🤖 **Microserviço REST inteligente para análise de requisitos de projetos de software**

API desenvolvida exclusivamente para a **Plataforma Demandei**, utilizando IA para transformar descrições de projetos em documentação técnica completa e estruturada, organizada por stacks tecnológicos.

---

## 📋 Índice

- [🚀 Características Principais](#-características-principais)
- [🔄 Workflow das 4 APIs](#-workflow-das-4-apis)
- [📋 Pré-requisitos](#-pré-requisitos)
- [🔧 Instalação](#-instalação)
- [🏃‍♂️ Como Executar](#️-como-executar)
- [🌐 API Documentation](#-api-documentation)
- [🔐 Autenticação](#-autenticação)
- [📡 Endpoints Detalhados](#-endpoints-detalhados)
- [📝 Exemplos de Uso](#-exemplos-de-uso)
- [❌ Códigos de Erro](#-códigos-de-erro)
- [🧪 Testes](#-testes)
- [🏗️ Arquitetura](#️-arquitetura)

---

## 🚀 Características Principais

- ✅ **4-API Workflow**: Fluxo simplificado e otimizado para plataforma Demandei
- ✅ **Autenticação por API Key**: Acesso exclusivo para plataforma Demandei  
- ✅ **Perguntas Dinâmicas**: Sistema de múltipla escolha inteligente com IA
- ✅ **Documentação por Stacks**: Frontend, Backend, Database, DevOps separados
- ✅ **Análise de Projeto**: Classificação automática de tipo e complexidade
- ✅ **Geração JSON**: Output estruturado para fácil integração
- ✅ **Swagger UI**: Documentação interativa completa
- ✅ **Validação Robusta**: Pydantic v2 para validação de entrada
- ✅ **Tratamento de Erros**: Respostas estruturadas e códigos HTTP apropriados

---

## 🔄 Workflow das 4 APIs

```mermaid
graph LR
    A[1. Project Analysis] --> B[2. Questions Response]
    B --> C[3. Summary Generation]
    C --> D[4. Documents Generation]
    
    A --> E[Session ID gerado]
    B --> F[Perguntas dinâmicas]
    C --> G[Resumo para confirmação]
    D --> H[Documentação final]
```

### Fluxo Detalhado

1. **🔍 API 1**: `POST /v1/project/analyze`
   - Recebe descrição do projeto
   - Classifica tipo e complexidade
   - Gera perguntas dinâmicas de múltipla escolha
   - Retorna session_id para próximas chamadas

2. **❓ API 2**: `POST /v1/questions/respond`
   - Processa respostas às perguntas
   - Determina se precisa de mais perguntas
   - Controla fluxo até ter informações suficientes

3. **📝 API 3**: `POST /v1/summary/generate` + `POST /v1/summary/confirm`
   - Gera resumo inteligente do projeto
   - Permite confirmação ou rejeição do usuário
   - Prepara dados para documentação

4. **📄 API 4**: `POST /v1/documents/generate`
   - Produz documentação técnica completa
   - Separa por stacks: Frontend, Backend, Database, DevOps
   - Inclui estimativas e tecnologias recomendadas

---

## 📋 Pré-requisitos

- **Python 3.11+**
- **OpenAI API Key** (para geração de perguntas e documentação)
- **Demandei API Key** (para autenticação)

---

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/Demandei-Corlabs/ia-compose-project.git
cd ia-compose-project
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite as variáveis obrigatórias:
DEMANDEI_API_KEY=your_fixed_api_key_for_demandei_platform
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
```

### Variáveis de Ambiente Completas

```env
# API Keys (OBRIGATÓRIAS)
DEMANDEI_API_KEY=your_demandei_api_key
OPENAI_API_KEY=your_openai_api_key

# Configuração da Aplicação
ENVIRONMENT=development
DEBUG=true
PORT=8001

# OpenAI
OPENAI_MODEL=gpt-4o-mini

# Armazenamento Local
USE_LOCAL_STORAGE=true
LOCAL_STORAGE_PATH=./storage
```

---

## 🏃‍♂️ Como Executar

### Desenvolvimento Local (Recomendado)
```bash
export DEMANDEI_API_KEY=your_api_key
export OPENAI_API_KEY=your_openai_key
python main.py
```

### Usando startup script
```bash
chmod +x start_server.sh
./start_server.sh
```

### Com Docker
```bash
docker-compose up
```

**🌐 A API estará disponível em:** `http://localhost:8001`

---

## 🌐 API Documentation

### Documentação Interativa

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

### Base URL
```
http://localhost:8001
```

---

## 🔐 Autenticação

**Todos os endpoints (exceto health checks) requerem autenticação Bearer Token:**

```http
Authorization: Bearer your_demandei_api_key
Content-Type: application/json
```

### Exemplo de Cabeçalho
```bash
curl -H "Authorization: Bearer your_demandei_api_key" \
     -H "Content-Type: application/json" \
     http://localhost:8001/v1/project/analyze
```

---

## 📡 Endpoints Detalhados

### 🏥 Health Checks

| Endpoint | Método | Autenticação | Descrição |
|----------|--------|--------------|-----------|
| `/health` | GET | ❌ Não | Status geral da API |
| `/v1/project/health` | GET | ❌ Não | Status do serviço de análise |
| `/v1/questions/health` | GET | ❌ Não | Status do serviço de perguntas |
| `/v1/summary/health` | GET | ❌ Não | Status do serviço de resumo |
| `/v1/documents/health` | GET | ❌ Não | Status do serviço de documentos |

### 🔍 API 1: Project Analysis

**`POST /v1/project/analyze`**

Analisa a descrição do projeto e gera a primeira sequência de perguntas.

#### Request
```json
{
  "project_description": "Sistema de gestão para clínica médica com 5 médicos e 300 pacientes/mês. Funcionalidades: agendamento online, prontuários eletrônicos, prescrições digitais, faturamento. Orçamento: R$ 120.000, Prazo: 6 meses",
  "metadata": {
    "source": "demandei_platform",
    "user_id": "user123"
  }
}
```

#### Response (200)
```json
{
  "session_id": "sess_abc123def456",
  "questions": [
    {
      "code": "Q001",
      "text": "Qual o tipo principal da aplicação?",
      "choices": [
        {
          "id": "web_app",
          "text": "Aplicação Web",
          "description": "Sistema acessível via navegador"
        },
        {
          "id": "mobile_app", 
          "text": "Aplicativo Mobile",
          "description": "App nativo ou híbrido"
        },
        {
          "id": "desktop_app",
          "text": "Aplicação Desktop", 
          "description": "Software instalado localmente"
        }
      ],
      "required": true,
      "allow_multiple": false,
      "category": "business"
    }
  ],
  "total_questions": 5,
  "estimated_completion_time": 8,
  "project_classification": {
    "type": "web_application",
    "complexity": "moderate", 
    "domain": "healthcare",
    "confidence": 0.85
  }
}
```

#### Validações
- `project_description`: 50-8000 caracteres
- `metadata`: Opcional, objeto JSON

---

### ❓ API 2: Questions Response

**`POST /v1/questions/respond`**

Processa respostas às perguntas e retorna próximo lote ou status de conclusão.

#### Request
```json
{
  "session_id": "sess_abc123def456",
  "answers": [
    {
      "question_code": "Q001",
      "selected_choices": ["web_app"],
      "custom_text": null
    },
    {
      "question_code": "Q002", 
      "selected_choices": ["medium", "react"],
      "custom_text": null
    }
  ],
  "request_next_batch": true
}
```

#### Response - Mais Perguntas (200)
```json
{
  "session_id": "sess_abc123def456",
  "response_type": "more_questions",
  "next_questions": [
    {
      "code": "Q003",
      "text": "Qual orçamento estimado?",
      "choices": [
        {"id": "low", "text": "Até R$ 50.000"},
        {"id": "medium", "text": "R$ 50.000 - R$ 200.000"},
        {"id": "high", "text": "R$ 200.000 - R$ 500.000"}
      ],
      "required": true,
      "allow_multiple": false,
      "category": "business"
    }
  ],
  "completion_percentage": 45.0,
  "message": "Perguntas processadas. 1 pergunta adicional."
}
```

#### Response - Pronto para Resumo (200)
```json
{
  "session_id": "sess_abc123def456",
  "response_type": "ready_for_summary",
  "next_questions": null,
  "completion_percentage": 100.0,
  "message": "Informações suficientes coletadas. Pronto para gerar resumo."
}
```

---

### 📝 API 3: Summary Generation

**`POST /v1/summary/generate`**

Gera resumo inteligente baseado nas respostas coletadas.

#### Request
```json
{
  "session_id": "sess_abc123def456",
  "include_assumptions": true
}
```

#### Response (200)
```json
{
  "session_id": "sess_abc123def456",
  "summary": "# Resumo do Projeto\n\n## Visão Geral\nSistema de gestão para clínica médica...",
  "key_points": [
    "Aplicação web com interface moderna",
    "Necessidade de integração com APIs externas",
    "Requisitos de performance moderados"
  ],
  "assumptions": [
    "Assumido uso de banco de dados relacional (PostgreSQL)",
    "Inferido hospedagem em cloud pública",
    "Pressuposto desenvolvimento responsivo para mobile"
  ],
  "confidence_score": 0.92,
  "requires_confirmation": true
}
```

**`POST /v1/summary/confirm`**

Confirma ou rejeita o resumo gerado.

#### Request
```json
{
  "session_id": "sess_abc123def456",
  "confirmed": true,
  "additional_notes": "Resumo aprovado, pode prosseguir"
}
```

#### Response (200)
```json
{
  "session_id": "sess_abc123def456", 
  "confirmation_status": "confirmed",
  "message": "Resumo confirmado. Pronto para gerar documentação técnica.",
  "next_step": "document_generation",
  "ready_for_documents": true
}
```

---

### 📄 API 4: Documents Generation

**`POST /v1/documents/generate`**

Gera documentação técnica final separada por stacks tecnológicos.

#### Request
```json
{
  "session_id": "sess_abc123def456",
  "format_type": "markdown",
  "include_implementation_details": true
}
```

#### Response (200)
```json
{
  "session_id": "sess_abc123def456",
  "stacks": [
    {
      "stack_type": "frontend",
      "title": "Frontend Development Stack",
      "content": "# Frontend - Documentação Técnica\n\n## Arquitetura Frontend...",
      "technologies": ["React", "Next.js", "TypeScript", "Tailwind CSS"],
      "estimated_effort": "6-8 semanas"
    },
    {
      "stack_type": "backend", 
      "title": "Backend Development Stack",
      "content": "# Backend - Documentação Técnica\n\n## Arquitetura Backend...",
      "technologies": ["FastAPI", "Python", "SQLAlchemy", "Redis"],
      "estimated_effort": "8-10 semanas"
    },
    {
      "stack_type": "database",
      "title": "Database Stack", 
      "content": "# Database - Documentação Técnica\n\n## Arquitetura de Dados...",
      "technologies": ["PostgreSQL", "Redis", "Alembic"],
      "estimated_effort": "2-3 semanas"
    },
    {
      "stack_type": "devops",
      "title": "DevOps and Infrastructure Stack",
      "content": "# DevOps - Documentação Técnica\n\n## Infraestrutura...",
      "technologies": ["Docker", "AWS", "GitHub Actions", "Terraform"],
      "estimated_effort": "3-4 semanas"
    }
  ],
  "generated_at": "2025-01-06T15:30:00Z",
  "total_estimated_effort": "16-24 semanas de desenvolvimento",
  "recommended_timeline": "4-6 meses incluindo testes e deployment"
}
```

---

## 📝 Exemplos de Uso

### Exemplo Completo: Workflow de E-commerce

```bash
# 1. Análise do Projeto
curl -X POST http://localhost:8001/v1/project/analyze \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "project_description": "Plataforma de e-commerce B2C para venda de produtos de beleza. Funcionalidades: catálogo com filtros, carrinho, múltiplos gateways de pagamento, sistema de avaliações, programa de fidelidade. Orçamento: R$ 200.000, Prazo: 8 meses"
  }'

# Response: session_id + perguntas iniciais

# 2. Resposta às Perguntas
curl -X POST http://localhost:8001/v1/questions/respond \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123def456",
    "answers": [
      {"question_code": "Q001", "selected_choices": ["web_app"]},
      {"question_code": "Q002", "selected_choices": ["react", "node"]}
    ],
    "request_next_batch": true
  }'

# 3. Geração do Resumo
curl -X POST http://localhost:8001/v1/summary/generate \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123def456",
    "include_assumptions": true
  }'

# 4. Confirmação do Resumo
curl -X POST http://localhost:8001/v1/summary/confirm \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123def456",
    "confirmed": true
  }'

# 5. Geração da Documentação
curl -X POST http://localhost:8001/v1/documents/generate \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123def456",
    "format_type": "markdown",
    "include_implementation_details": true
  }'
```

---

## ❌ Códigos de Erro

### Códigos HTTP e Estrutura de Erro

Todos os erros seguem o padrão estruturado:

```json
{
  "error_code": "ERROR_TYPE",
  "message": "Descrição legível do erro",
  "details": {
    "additional": "information"
  },
  "session_id": "sess_abc123def456"
}
```

### Códigos de Status HTTP

| Código | Descrição | Quando Ocorre |
|--------|-----------|---------------|
| **200** | ✅ Sucesso | Operação completada com sucesso |
| **400** | ❌ Bad Request | Dados inválidos ou estado inválido |
| **401** | 🔒 Unauthorized | API key ausente ou inválida |
| **404** | 🔍 Not Found | Session ID não encontrado |
| **422** | 📝 Validation Error | Erro de validação Pydantic |
| **500** | 💥 Internal Error | Erro interno do servidor |

### Códigos de Erro Específicos

#### Autenticação
```json
// 401 - API key ausente
{
  "error_code": "API_KEY_MISSING",
  "message": "API key required",
  "details": null
}

// 401 - API key inválida  
{
  "error_code": "INVALID_API_KEY",
  "message": "Invalid API key",
  "details": null
}
```

#### Validação
```json
// 422 - Descrição muito curta
{
  "error_code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "details": {
    "field": "project_description",
    "constraint": "min_length",
    "limit": 50
  }
}
```

#### Session Management
```json
// 404 - Session não encontrada
{
  "error_code": "SESSION_NOT_FOUND", 
  "message": "Session not found or expired",
  "session_id": "sess_invalid123"
}

// 400 - Summary não confirmado
{
  "error_code": "SUMMARY_NOT_CONFIRMED",
  "message": "Summary must be confirmed before generating documents",
  "session_id": "sess_abc123def456"
}
```

#### Processamento
```json
// 500 - Erro na geração de perguntas
{
  "error_code": "QUESTION_GENERATION_FAILED",
  "message": "Failed to generate questions for project",
  "details": {
    "error": "OpenAI API timeout"
  },
  "session_id": "sess_abc123def456"
}
```

---

## 🧪 Testes

### Executar Testes

```bash
# Todos os testes
DEMANDEI_API_KEY=test_key OPENAI_API_KEY=test_key python -m pytest tests/test_api_flows.py -v

# Testes específicos
pytest tests/test_api_flows.py::TestProjectTypes::test_healthcare_management_system -v

# Com cobertura
pytest --cov=app tests/test_api_flows.py
```

### Categorias de Testes

- **TestProjectTypes** (5 testes): Diferentes tipos de projetos
- **TestAPIAuthentication** (3 testes): Autenticação e segurança
- **TestHealthEndpoints** (2 testes): Health checks
- **TestAPIValidation** (3 testes): Validação de entrada

### Resultado Esperado
```
13 passed, 21 warnings in 0.63s
================ 13 passed ================
```

---

## 🏗️ Arquitetura

### Estrutura do Projeto

```
ia-compose-project/
├── app/
│   ├── api/
│   │   └── v1/                   # APIs principais
│   │       ├── project.py        # API 1: Project Analysis
│   │       ├── questions.py      # API 2: Questions Response
│   │       ├── summary.py        # API 3: Summary Generation
│   │       └── documents.py      # API 4: Documents Generation
│   ├── middleware/
│   │   └── auth.py              # Autenticação Bearer Token
│   ├── models/
│   │   └── api_models.py        # Modelos Pydantic
│   ├── services/
│   │   └── question_engine.py   # Geração de perguntas IA
│   └── utils/
│       └── pii_safe_logging.py  # Logging seguro
├── tests/
│   └── test_api_flows.py        # Testes das 4 APIs
├── main.py                      # Aplicação FastAPI
├── requirements.txt             # Dependências
├── .env.example                 # Exemplo de configuração
├── docker-compose.yml           # Container setup
└── README.md                    # Esta documentação
```

### Tecnologias Utilizadas

- **FastAPI** - Framework web moderno e rápido
- **Pydantic v2** - Validação e serialização de dados
- **OpenAI API** - Geração inteligente de perguntas
- **Uvicorn** - Servidor ASGI
- **pytest** - Framework de testes
- **Docker** - Containerização

### Padrões de Design

- **Repository Pattern** - Para acesso a dados
- **Dependency Injection** - FastAPI nativo
- **Bearer Token Authentication** - Segurança API
- **Error Handling Middleware** - Tratamento centralizado
- **Structured Logging** - Logs seguros sem PII

---

## 🤝 Integração com Plataforma Demandei

### Fluxo de Integração

1. **Demandei Platform** chama `POST /v1/project/analyze`
2. **Usuário** responde perguntas via interface Demandei
3. **Demandei Platform** submete respostas via `POST /v1/questions/respond`
4. **Repeat** até `response_type: "ready_for_summary"`
5. **Demandei Platform** gera e confirma resumo
6. **Demandei Platform** solicita documentação final
7. **IA Compose API** retorna documentação por stacks

### Session Management

- Sessions são **stateful** e armazenadas em memória (desenvolvimento)
- Cada session tem **ID único** para rastreamento
- Sessions **expiram** após inatividade (configurável)
- **Thread-safe** para múltiplas requests simultâneas

---

## 📞 Suporte e Contribuição

### Suporte
- **Email**: support@demandei.com
- **Documentation**: http://localhost:8001/docs
- **Issues**: Entre em contato com a equipe Demandei

### Licença
**Proprietary License** - Demandei Corlabs. Todos os direitos reservados.

---

**🚀 Demandei Corlabs** - Transformando ideias em especificações técnicas completas com IA

*Versão: 3.0.0 | Última atualização: 2025-01-06*