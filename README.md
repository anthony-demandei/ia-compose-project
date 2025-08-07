# IA Task Composer - Intelligent Intake System

Sistema inteligente de intake para levantamento de requisitos de projetos de software, utilizando IA e arquitetura multi-agent para gerar documentação técnica completa.

## 🚀 Características Principais

- **Intake Inteligente**: Sistema de perguntas dinâmicas baseado em IA
- **Multi-Agent Architecture**: Múltiplos agentes especializados para análise profunda
- **Análise de Completude V3.0**: Sistema avançado de scoring e validação
- **Classificação Universal**: Identifica automaticamente o tipo e domínio do projeto
- **Geração de Documentação**: Produz especificações técnicas detalhadas
- **Memory System**: Integração com ZEP para memória contextual
- **Context Inference Engine**: Análise semântica com GPT-4 para evitar redundâncias

## 📋 Pré-requisitos

- Python 3.11+
- OpenAI API Key
- Redis (opcional, para cache)
- Docker (opcional, para containerização)

## 🔧 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/Demandei-Corlabs/ia-task-composer.git
cd ia-task-composer
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
# Crie um arquivo .env na raiz do projeto
cat > .env << EOL
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini
ENVIRONMENT=development
DEBUG=true
USE_LOCAL_STORAGE=true
LOCAL_STORAGE_PATH=./storage
PORT=8000
EOL
```

## 🏃‍♂️ Como Executar

### Desenvolvimento Local

```bash
python main.py
```

O sistema estará disponível em `http://localhost:8000`

### Com Docker

```bash
docker-compose up
```

## 🌐 Endpoints Principais

### Interface Web
- `/` - Interface principal de intake

### API REST
- `POST /api/intake/sessions` - Criar nova sessão de intake
- `GET /api/intake/sessions/{id}/questions` - Obter próximas perguntas
- `POST /api/intake/sessions/{id}/answers` - Enviar respostas
- `GET /api/intake/sessions/{id}/summary` - Gerar resumo
- `POST /api/multi-agent/analyze` - Análise multi-agent avançada
- `GET /health` - Status do sistema

## 🏗️ Arquitetura

### Estrutura do Projeto

```
ia-task-composer/
├── app/
│   ├── api/                  # Endpoints FastAPI
│   │   ├── intake.py         # API do sistema intake
│   │   └── multi_agent.py    # API multi-agente
│   ├── core/                 # Lógica central
│   │   ├── state_machine.py  # Máquina de estados
│   │   └── validation_engine.py # Motor de validação
│   ├── models/               # Modelos Pydantic
│   ├── services/             # Serviços principais
│   │   ├── intake_engine.py  # Motor principal
│   │   ├── context_inference_engine.py # Inferência contextual
│   │   ├── dynamic_question_generator.py # Geração dinâmica
│   │   ├── briefing_completeness_analyzer.py # Análise de completude
│   │   ├── universal_project_classifier.py # Classificador universal
│   │   └── multi_agent_coordinator.py # Coordenador multi-agent
│   ├── templates/            # Prompts do sistema
│   ├── utils/                # Utilitários
│   └── data/                 # Catálogos e regras
│       ├── question_catalog_v2.yaml
│       └── validation_rules_v2.yaml
├── static/                   # Interface web
│   ├── index.html           # Interface principal
│   └── css/
├── storage/                  # Armazenamento local
└── main.py                   # Entrada principal
```

## 🤖 Sistema Multi-Agent

O sistema utiliza 5 agentes especializados que trabalham em conjunto:

### Agentes Disponíveis

1. **Technical Architect Agent**
   - Arquitetura e decisões técnicas
   - Stack tecnológica e integrações
   - Padrões e best practices

2. **Business Analyst Agent**
   - Requisitos de negócio
   - ROI e métricas de sucesso
   - Processos e fluxos

3. **Industry Expert Agent**
   - Conhecimento específico do domínio
   - Regulamentações setoriais
   - Tendências de mercado

4. **Compliance Expert Agent**
   - LGPD, GDPR, PCI-DSS
   - Segurança e privacidade
   - Auditoria e conformidade

5. **Performance Engineer Agent**
   - Escalabilidade e otimização
   - Métricas de performance
   - Arquitetura de alta disponibilidade

## 📊 Sistema de Completude V3.0

### Níveis de Completude

| Nível | Faixa | Descrição |
|-------|-------|-----------|
| **Crítico** | 0-40% | Informações essenciais ausentes |
| **Básico** | 40-60% | Funcional mas incompleto |
| **Bom** | 60-80% | Bem definido, algumas lacunas |
| **Excelente** | 80-100% | Especificação completa |

### Dimensões Avaliadas

- **Clareza dos Objetivos** (20%)
- **Definição de Usuários** (15%)
- **Escopo Funcional** (25%)
- **Requisitos Técnicos** (20%)
- **Restrições e Políticas** (10%)
- **Critérios de Sucesso** (10%)

## 🎯 Tipos de Projetos Suportados

- **SaaS** - Software as a Service
- **E-commerce** - Plataformas de vendas online
- **Fintech** - Soluções financeiras
- **Healthtech** - Sistemas de saúde
- **Edtech** - Plataformas educacionais
- **Marketplace** - Plataformas multi-sided
- **Enterprise** - Sistemas corporativos
- **Mobile/Web Apps** - Aplicações multiplataforma
- **API/Microservices** - Arquiteturas distribuídas
- **IoT** - Internet das Coisas
- **AI/ML** - Inteligência Artificial

## 🔐 Segurança

- **Sanitização de Dados**: Remoção automática de PII
- **Validação de Entrada**: Em todos os endpoints
- **Rate Limiting**: Configurável por ambiente
- **Logging Seguro**: Sem exposição de dados sensíveis
- **Compliance**: LGPD, GDPR ready

## 🛠️ Desenvolvimento

### Ferramentas de Qualidade

```bash
# Formatação com Black
python -m black . --line-length 100

# Linting com Ruff
python -m ruff check . --fix

# Type checking (opcional)
mypy app/
```

### Variáveis de Ambiente

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Application
ENVIRONMENT=development
DEBUG=true
USE_LOCAL_STORAGE=true
LOCAL_STORAGE_PATH=./storage

# Features
ENABLE_CONTEXT_INFERENCE=true
ENABLE_SMART_FILTERING=true
ENABLE_MULTI_AGENT=true

# Optional Services
USE_REDIS_CACHE=false
ZEP_API_KEY=your-zep-key
```

## 📝 Documentação Gerada

O sistema gera automaticamente:

1. **Especificações Técnicas**
   - Arquitetura proposta
   - Stack tecnológica
   - Integrações necessárias

2. **Documentação de Negócio**
   - User stories
   - Casos de uso
   - Jornadas do usuário

3. **Planejamento**
   - Roadmap de implementação
   - Estimativas de esforço
   - Análise de riscos

4. **Requisitos**
   - Funcionais e não-funcionais
   - Critérios de aceitação
   - Métricas de sucesso

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Proprietary - Demandei Corlabs. Todos os direitos reservados.

## 📞 Suporte

Para suporte, entre em contato com a equipe Demandei ou abra uma issue no repositório.

---

**Demandei Corlabs** - Transformando ideias em especificações técnicas completas com IA