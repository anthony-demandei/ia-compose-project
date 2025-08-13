# 🚀 Quick Start Guide - IA Compose API

**Guia rápido para configurar e testar a API em 5 minutos**

---

## 📋 Setup Rápido

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis
```bash
export DEMANDEI_API_KEY=your_demandei_api_key
export OPENAI_API_KEY=your_openai_api_key
```

### 3. Iniciar Servidor
```bash
python main.py
```

**✅ API disponível em:** http://localhost:8001

---

## 🌐 Acessar Documentação

- **Swagger UI (Recomendado)**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **Health Check**: http://localhost:8001/health

---

## 🧪 Teste Rápido via curl

### 1. Health Check (sem autenticação)
```bash
curl http://localhost:8001/health
```

### 2. Analisar Projeto (API 1)
```bash
curl -X POST http://localhost:8001/v1/project/analyze \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "project_description": "Sistema de e-commerce para venda de roupas online com carrinho de compras, pagamento via PIX e cartão, gestão de estoque. Orçamento: R$ 150.000, Prazo: 5 meses"
  }'
```

**Resposta esperada:**
```json
{
  "session_id": "uuid-gerado",
  "questions": [...],
  "total_questions": 3,
  "estimated_completion_time": 5,
  "project_classification": {
    "type": "web_application",
    "complexity": "moderate"
  }
}
```

### 3. Responder Perguntas (API 2)
```bash
curl -X POST http://localhost:8001/v1/questions/respond \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-do-passo-anterior",
    "answers": [
      {"question_code": "Q001", "selected_choices": ["web_app"]},
      {"question_code": "Q002", "selected_choices": ["small"]}
    ],
    "request_next_batch": true
  }'
```

### 4. Gerar Resumo (API 3)
```bash
curl -X POST http://localhost:8001/v1/summary/generate \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-do-passo-anterior",
    "include_assumptions": true
  }'
```

### 5. Confirmar Resumo
```bash
curl -X POST http://localhost:8001/v1/summary/confirm \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-do-passo-anterior",
    "confirmed": true
  }'
```

### 6. Gerar Documentação (API 4)
```bash
curl -X POST http://localhost:8001/v1/documents/generate \
  -H "Authorization: Bearer your_demandei_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-do-passo-anterior",
    "format_type": "markdown",
    "include_implementation_details": true
  }'
```

**Resposta esperada:**
```json
{
  "session_id": "uuid",
  "stacks": [
    {
      "stack_type": "frontend",
      "title": "Frontend Development Stack",
      "content": "# Frontend - Documentação Técnica...",
      "technologies": ["React", "Next.js", "TypeScript"],
      "estimated_effort": "6-8 semanas"
    },
    // ... outros stacks (backend, database, devops)
  ],
  "total_estimated_effort": "16-24 semanas de desenvolvimento"
}
```

---

## 🧪 Executar Testes

```bash
# Todos os testes
DEMANDEI_API_KEY=test_key OPENAI_API_KEY=test_key python -m pytest tests/test_api_flows.py -v

# Resultado esperado: 13 passed
```

---

## ⚠️ Troubleshooting

### Erro 401 - Unauthorized
- ✅ Verifique se `DEMANDEI_API_KEY` está configurada
- ✅ Certifique-se de usar `Authorization: Bearer your_key`

### Erro 422 - Validation Error  
- ✅ `project_description` deve ter 50-8000 caracteres
- ✅ Verifique formato JSON da requisição

### Erro 404 - Session Not Found
- ✅ Use o `session_id` retornado pela API anterior
- ✅ Sessions têm tempo de expiração

### Servidor não inicia
- ✅ Instale dependências: `pip install -r requirements.txt`
- ✅ Configure `OPENAI_API_KEY` (obrigatória)
- ✅ Verifique se porta 8001 está livre

---

## 📊 Swagger UI Features

**No Swagger UI (http://localhost:8001/docs):**

1. **🔒 Authorize**: Clique e configure `Bearer your_demandei_api_key`
2. **📝 Try it out**: Teste endpoints diretamente na interface
3. **📋 Examples**: Veja exemplos pré-configurados
4. **📖 Schemas**: Explore modelos de dados
5. **❌ Error Responses**: Veja códigos de erro possíveis

---

## 🔄 Workflow Completo

```mermaid
graph TD
    A[POST /v1/project/analyze] --> B[session_id + questions]
    B --> C[POST /v1/questions/respond]
    C --> D{More questions?}
    D -->|Yes| C
    D -->|No| E[POST /v1/summary/generate]
    E --> F[POST /v1/summary/confirm]
    F --> G[POST /v1/documents/generate]
    G --> H[Frontend + Backend + Database + DevOps docs]
```

---

**✅ Pronto! Agora você pode integrar a API com a plataforma Demandei.**

Para documentação completa, consulte: [README.md](./README.md)