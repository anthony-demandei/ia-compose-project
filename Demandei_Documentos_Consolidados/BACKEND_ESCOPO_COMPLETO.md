# ESCOPO COMPLETO BACKEND - DEMANDEI

## 🎯 VISÃO GERAL

### Stack Tecnológica Definida (Versões 2025)
- **Framework**: NestJS 11.1.5 (Node.js Framework)
- **Runtime**: Node.js 22.18.0 LTS (Jod) + Express
- **API**: REST API (CQRS pattern)
- **Banco de Dados**: PostgreSQL 17.5 + Prisma ORM 6.13.0
- **Cache**: Redis 7.4.x
- **Autenticação**: Better Auth 1.3.4
- **WebSockets**: Socket.io 4.8.1 integrado ao NestJS
- **AI**: OpenAI SDK 5.12.0
- **Pagamentos**: ASAAS (gateway brasileiro)
- **Cloud**: AWS / Digital Ocean
- **Container**: Docker + Docker Compose

### Arquitetura
- **Padrão**: CQRS + Clean Architecture
- **Estrutura**: Domain-Driven Design (DDD)
- **Commands**: Write operations (mutations)
- **Queries**: Read operations (optimized for UI)
- **Event Sourcing**: Para auditoria e consistência
- **Validação**: class-validator + class-transformer
- **Documentação**: Swagger/OpenAPI automático
- **Testing**: Jest + supertest
- **Deploy**: CI/CD com GitHub Actions

## 📁 ESTRUTURA DO PROJETO

```
demandei-api/
├── src/
│   ├── app.module.ts
│   ├── main.ts
│   ├── application/              # Application Layer (CQRS)
│   │   ├── commands/             # Write operations
│   │   │   ├── handlers/
│   │   │   └── dto/
│   │   ├── queries/              # Read operations
│   │   │   ├── handlers/
│   │   │   └── dto/
│   │   └── events/               # Domain events
│   │       ├── handlers/
│   │       └── dto/
│   ├── domain/                   # Domain Layer (Clean Architecture)
│   │   ├── entities/             # Business entities
│   │   ├── value-objects/        # Value objects
│   │   ├── repositories/         # Repository interfaces
│   │   ├── services/             # Domain services
│   │   └── events/               # Domain events
│   ├── infrastructure/           # Infrastructure Layer
│   │   ├── database/
│   │   │   ├── prisma/
│   │   │   ├── repositories/     # Repository implementations
│   │   │   └── migrations/
│   │   ├── auth/                 # Better Auth integration
│   │   ├── external/             # External services (ASAAS, OpenAI)
│   │   ├── messaging/            # Event bus, queues
│   │   └── cache/                # Redis implementation
│   ├── presentation/             # Presentation Layer
│   │   ├── controllers/          # REST API controllers
│   │   ├── dto/                  # Data Transfer Objects
│   │   ├── guards/               # Auth guards
│   │   ├── interceptors/
│   │   └── filters/
│   ├── shared/
│   │   ├── config/
│   │   ├── utils/
│   │   ├── constants/
│   │   └── interfaces/
├── prisma/
│   ├── schema.prisma
│   ├── migrations/
│   └── seeds/
├── test/
├── docker-compose.yml
├── Dockerfile
├── package.json
└── README.md
```

## 🏢 ARQUITETURA CQRS + CLEAN ARCHITECTURE

### Princípios da Arquitetura

#### CQRS (Command Query Responsibility Segregation)
```typescript
// Commands: Operações de escrita (CREATE, UPDATE, DELETE)
export interface ICommand {
  readonly type: string
  readonly payload: any
  readonly metadata?: {
    userId?: string
    timestamp?: Date
    correlationId?: string
  }
}

// Queries: Operações de leitura (SELECT otimizadas para UI)
export interface IQuery {
  readonly type: string
  readonly filters?: Record<string, any>
  readonly pagination?: {
    page: number
    limit: number
  }
  readonly sorting?: {
    field: string
    direction: 'ASC' | 'DESC'
  }
}

// Events: Eventos de domínio para consistência eventual
export interface IDomainEvent {
  readonly aggregateId: string
  readonly eventType: string
  readonly eventData: any
  readonly occurredOn: Date
  readonly version: number
}
```

#### Clean Architecture Layers
```typescript
// Domain Layer - Regras de negócio puras
export abstract class Entity<T> {
  protected readonly _id: string
  protected props: T
  
  constructor(props: T, id?: string) {
    this._id = id ?? crypto.randomUUID()
    this.props = props
  }
  
  get id(): string {
    return this._id
  }
}

// Application Layer - Casos de uso
@Injectable()
export abstract class CommandHandler<TCommand extends ICommand, TResult = any> {
  abstract execute(command: TCommand): Promise<TResult>
}

@Injectable()
export abstract class QueryHandler<TQuery extends IQuery, TResult = any> {
  abstract execute(query: TQuery): Promise<TResult>
}

// Infrastructure Layer - Detalhes técnicos
export interface Repository<T extends Entity<any>> {
  findById(id: string): Promise<T | null>
  save(entity: T): Promise<void>
  delete(id: string): Promise<void>
}
```

### Exemplo Completo: Projeto Module
```typescript
// domain/entities/project.entity.ts
export interface ProjectProps {
  title: string
  description: string
  companyId: string
  budget: { min: number; max: number }
  status: ProjectStatus
  createdAt: Date
}

export class ProjectEntity extends Entity<ProjectProps> {
  static create(props: Omit<ProjectProps, 'createdAt' | 'status'>): ProjectEntity {
    return new ProjectEntity({
      ...props,
      status: ProjectStatus.DRAFT,
      createdAt: new Date()
    })
  }
  
  publish(): void {
    if (this.props.status !== ProjectStatus.DRAFT) {
      throw new Error('Only draft projects can be published')
    }
    this.props.status = ProjectStatus.PUBLISHED
  }
  
  get title(): string {
    return this.props.title
  }
  
  get status(): ProjectStatus {
    return this.props.status
  }
}

// application/commands/create-project.command.ts
export class CreateProjectCommand implements ICommand {
  constructor(
    public readonly title: string,
    public readonly description: string,
    public readonly companyId: string,
    public readonly budget: { min: number; max: number }
  ) {}
}

// application/commands/create-project.handler.ts
@CommandHandler(CreateProjectCommand)
export class CreateProjectHandler implements ICommandHandler<CreateProjectCommand> {
  constructor(
    private projectRepository: IProjectRepository,
    private eventBus: EventBus
  ) {}
  
  async execute(command: CreateProjectCommand): Promise<string> {
    const project = ProjectEntity.create({
      title: command.title,
      description: command.description,
      companyId: command.companyId,
      budget: command.budget
    })
    
    await this.projectRepository.save(project)
    
    // Publicar evento para outras bounded contexts
    const event = new ProjectCreatedEvent({
      projectId: project.id,
      companyId: project.props.companyId,
      title: project.title
    })
    
    this.eventBus.publish(event)
    
    return project.id
  }
}

// application/queries/get-projects.query.ts
export class GetProjectsQuery implements IQuery {
  constructor(
    public readonly companyId: string,
    public readonly filters?: {
      status?: ProjectStatus
      search?: string
    },
    public readonly pagination?: {
      page: number
      limit: number
    }
  ) {}
}

// application/queries/get-projects.handler.ts
@QueryHandler(GetProjectsQuery)
export class GetProjectsHandler implements IQueryHandler<GetProjectsQuery> {
  constructor(private projectReadRepository: IProjectReadRepository) {}
  
  async execute(query: GetProjectsQuery): Promise<ProjectListDto[]> {
    return this.projectReadRepository.findManyByCompany(
      query.companyId,
      query.filters,
      query.pagination
    )
  }
}

// infrastructure/repositories/project.repository.ts
@Injectable()
export class ProjectRepository implements IProjectRepository {
  constructor(private prisma: PrismaService) {}
  
  async findById(id: string): Promise<ProjectEntity | null> {
    const project = await this.prisma.project.findUnique({
      where: { id }
    })
    
    if (!project) return null
    
    return new ProjectEntity({
      title: project.title,
      description: project.description,
      companyId: project.companyId,
      budget: { min: project.budgetMin.toNumber(), max: project.budgetMax.toNumber() },
      status: project.status as ProjectStatus,
      createdAt: project.createdAt
    }, project.id)
  }
  
  async save(entity: ProjectEntity): Promise<void> {
    await this.prisma.project.upsert({
      where: { id: entity.id },
      create: {
        id: entity.id,
        title: entity.props.title,
        description: entity.props.description,
        companyId: entity.props.companyId,
        budgetMin: entity.props.budget.min,
        budgetMax: entity.props.budget.max,
        status: entity.props.status,
        createdAt: entity.props.createdAt
      },
      update: {
        title: entity.props.title,
        description: entity.props.description,
        status: entity.props.status
      }
    })
  }
}

// presentation/controllers/projects.controller.ts
@Controller('api/v1/projects')
@ApiTags('Projects')
export class ProjectsController {
  constructor(
    private commandBus: CommandBus,
    private queryBus: QueryBus
  ) {}
  
  @Post()
  @ApiOperation({ summary: 'Criar novo projeto' })
  async create(@Body() dto: CreateProjectDto, @CurrentUser() user: UserPayload) {
    const command = new CreateProjectCommand(
      dto.title,
      dto.description,
      user.companyId,
      dto.budget
    )
    
    const projectId = await this.commandBus.execute(command)
    return { projectId }
  }
  
  @Get()
  @ApiOperation({ summary: 'Listar projetos da empresa' })
  async findAll(
    @Query() queryParams: GetProjectsQueryDto,
    @CurrentUser() user: UserPayload
  ) {
    const query = new GetProjectsQuery(
      user.companyId,
      queryParams.filters,
      queryParams.pagination
    )
    
    return this.queryBus.execute(query)
  }
}
```


### Atualizações Importantes 2025

#### Tecnologias End-of-Life (EOL)
- **Node.js 16**: EOL desde setembro 2023, AWS SDK v3 não suporta mais desde janeiro 2025
- **AWS SDK v2**: Entrou em maintenance mode setembro 2024, EOL previsto para setembro 2025
- **ioredis vs node-redis**: Redis recomenda node-redis para novos projetos (2025)

#### Versões Críticas Atualizadas
- **@aws-sdk/client-s3**: 3.859.0 (suporte apenas Node.js 18+ desde 2025)
- **@nestjs/bullmq**: 11.0.3 (compatibilidade NestJS 11)
- **ioredis**: 5.7.0 (última versão estável, consider node-redis para projetos novos)
- **@thallesp/nestjs-better-auth**: Integração oficial Better Auth + NestJS

### Benefícios da Arquitetura CQRS + Clean

#### Separação de Responsabilidades
- **Commands**: Otimizados para consistência e regras de negócio
- **Queries**: Otimizados para performance de leitura
- **Domain Logic**: Isolada de detalhes técnicos
- **Infrastructure**: Facilmente substituível

#### Escalabilidade
- **Read/Write Scaling**: Bancos separados para leitura e escrita
- **Event-Driven**: Consistência eventual entre bounded contexts
- **Microservices Ready**: Fácil divisão em serviços independentes
- **Cache Strategy**: Queries podem ser facilmente cacheadas

#### Testabilidade
- **Unit Tests**: Domain entities sem dependências externas
- **Integration Tests**: Handlers com mocks de repositories
- **E2E Tests**: Controllers com banco de teste
- **Behavior Tests**: Scenarios de negócio com eventos

## 📚 API REFERENCE COMPLETA

### Convenções da API

- **Base URL**: `https://api.demandei.com.br/api/v1`
- **Autenticação**: Bearer Token JWT (exceto endpoints públicos)
- **Headers Padrão**:
  - `Content-Type: application/json`
  - `Authorization: Bearer {token}`
  - `X-Request-ID: {uuid}` (para tracking)
- **Rate Limiting**: 100 requests/minuto por IP
- **Paginação**: Query params `?page=1&limit=20&sort=createdAt:desc`

### Status Codes Padrão

- `200 OK`: Sucesso na requisição GET/PUT
- `201 Created`: Recurso criado com sucesso
- `202 Accepted`: Requisição aceita para processamento assíncrono
- `204 No Content`: Sucesso sem conteúdo de resposta
- `400 Bad Request`: Erro de validação ou parâmetros
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Sem permissão para o recurso
- `404 Not Found`: Recurso não encontrado
- `409 Conflict`: Conflito com estado atual
- `422 Unprocessable Entity`: Erro de validação detalhado
- `429 Too Many Requests`: Rate limit excedido
- `500 Internal Server Error`: Erro no servidor

---

## 🔒 ENDPOINTS DE AUTENTICAÇÃO

### POST /api/v1/auth/sign-up/email
**Descrição**: Cadastro de novo usuário com email

**Body Parameters**:
```typescript
{
  "email": string,         // Email válido, único
  "password": string,      // Min 8 caracteres, 1 maiúscula, 1 número
  "name": string,         // Nome completo, min 3 caracteres
  "userType": "COMPANY" | "FREELANCER",
  "acceptTerms": boolean  // Deve ser true
}
```

**Response 201**:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "João Silva",
    "userType": "FREELANCER",
    "emailVerified": false,
    "createdAt": "2025-01-01T00:00:00Z"
  },
  "token": "jwt-token",
  "refreshToken": "refresh-token"
}
```

### POST /api/v1/auth/sign-in/email
**Descrição**: Login com email e senha

**Body Parameters**:
```typescript
{
  "email": string,
  "password": string,
  "rememberMe"?: boolean  // Opcional, estende duração do token
}
```

**Response 200**:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "João Silva",
    "userType": "FREELANCER"
  },
  "token": "jwt-token",
  "refreshToken": "refresh-token",
  "expiresIn": 3600
}
```

### POST /api/v1/auth/refresh
**Descrição**: Renovar token de acesso

**Body Parameters**:
```typescript
{
  "refreshToken": string
}
```

**Response 200**:
```json
{
  "token": "new-jwt-token",
  "refreshToken": "new-refresh-token",
  "expiresIn": 3600
}
```

### POST /api/v1/auth/forgot-password
**Descrição**: Solicitar reset de senha

**Body Parameters**:
```typescript
{
  "email": string
}
```

**Response 200**:
```json
{
  "message": "Se o email existir, instruções foram enviadas"
}
```

### POST /api/v1/auth/reset-password
**Descrição**: Resetar senha com token

**Body Parameters**:
```typescript
{
  "token": string,      // Token recebido por email
  "password": string    // Nova senha
}
```

**Response 200**:
```json
{
  "message": "Senha alterada com sucesso"
}
```

### POST /api/v1/auth/verify-email
**Descrição**: Verificar email com token

**Body Parameters**:
```typescript
{
  "token": string  // Token recebido por email
}
```

**Response 200**:
```json
{
  "message": "Email verificado com sucesso",
  "emailVerified": true
}
```

---

## 👤 ENDPOINTS DE PERFIS

### POST /api/v1/companies/profile
**Descrição**: Criar perfil de empresa
**Auth**: Required

**Body Parameters**:
```typescript
{
  "companyName": string,      // Razão social
  "tradeName": string,        // Nome fantasia
  "cnpj": string,            // CNPJ válido (14 dígitos)
  "industry": string,        // Setor de atuação
  "size": "MICRO" | "SMALL" | "MEDIUM" | "LARGE",
  "website"?: string,        // URL opcional
  "phone": string,          // Telefone com DDD
  "address": {
    "street": string,
    "number": string,
    "complement"?: string,
    "district": string,
    "city": string,
    "state": string,       // UF (2 caracteres)
    "zipCode": string      // CEP (8 dígitos)
  }
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "userId": "uuid",
  "companyName": "Empresa LTDA",
  "tradeName": "Minha Empresa",
  "cnpj": "12345678000190",
  "verified": false,
  "verificationStatus": "PENDING",
  "createdAt": "2025-01-01T00:00:00Z"
}
```

### GET /api/v1/companies/profile
**Descrição**: Obter perfil da empresa do usuário autenticado
**Auth**: Required

**Response 200**: Mesmo formato do POST

### PUT /api/v1/companies/profile
**Descrição**: Atualizar perfil da empresa
**Auth**: Required

**Body Parameters**: Todos os campos do POST são opcionais

### POST /api/v1/freelancers/profile
**Descrição**: Criar perfil de freelancer
**Auth**: Required

**Body Parameters**:
```typescript
{
  "displayName": string,     // Nome profissional
  "cpf": string,             // CPF válido (11 dígitos)
  "phone": string,           // Telefone com DDD
  "bio": string,             // Biografia profissional (max 500 chars)
  "hourlyRate": number,      // Valor por hora em BRL
  "experienceLevel": "JUNIOR" | "MID" | "SENIOR" | "EXPERT",
  "availability": "FULL_TIME" | "PART_TIME" | "FREELANCE",
  "skills": string[],        // Array de IDs de skills
  "portfolio"?: string,      // URL do portfolio
  "linkedin"?: string,       // URL do LinkedIn
  "github"?: string         // URL do GitHub
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "userId": "uuid",
  "displayName": "João Dev",
  "cpf": "12345678901",
  "hourlyRate": 150.00,
  "experienceLevel": "SENIOR",
  "rating": 0,
  "completedProjects": 0,
  "verified": false,
  "createdAt": "2025-01-01T00:00:00Z"
}
```

### GET /api/v1/freelancers
**Descrição**: Buscar freelancers (para empresas)
**Auth**: Required

**Query Parameters**:
```typescript
{
  "skills"?: string[],        // Filtrar por skills
  "experienceLevel"?: string, // Filtrar por nível
  "minRate"?: number,         // Taxa mínima por hora
  "maxRate"?: number,         // Taxa máxima por hora
  "availability"?: string,    // Disponibilidade
  "search"?: string,          // Busca por nome/bio
  "page"?: number,            // Default: 1
  "limit"?: number,           // Default: 20
  "sort"?: string            // Ex: "rating:desc"
}
```

**Response 200**:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

### POST /api/v1/freelancers/skills
**Descrição**: Adicionar skills ao perfil
**Auth**: Required

**Body Parameters**:
```typescript
{
  "skillIds": string[],      // Array de IDs de skills
  "proficiencies"?: {        // Opcional: níveis de proficiência
    [skillId: string]: 1-5
  }
}
```

---

## 📋 ENDPOINTS DE PROJETOS

### POST /api/v1/projects
**Descrição**: Criar novo projeto
**Auth**: Required (Company only)

**Body Parameters**:
```typescript
{
  "title": string,           // Max 200 chars
  "description": string,     // Max 2000 chars
  "requirements": string,    // Requisitos técnicos detalhados
  "budget": {
    "min": number,          // Valor mínimo em BRL
    "max": number           // Valor máximo em BRL
  },
  "deadline": string,        // ISO 8601 date
  "urgency": "LOW" | "MEDIUM" | "HIGH",
  "visibility": "PUBLIC" | "PRIVATE",
  "preferredSkills": string[], // IDs de skills desejadas
  "attachments"?: string[]     // URLs de arquivos anexos
}
```

**Validações**:
- `title`: Obrigatório, min 10, max 200 caracteres
- `description`: Obrigatório, min 50, max 2000 caracteres
- `budget.min`: Mínimo R$ 500
- `budget.max`: Deve ser maior que budget.min
- `deadline`: Deve ser data futura, mínimo 7 dias

**Response 201**:
```json
{
  "id": "uuid",
  "title": "Desenvolvimento E-commerce",
  "status": "DRAFT",
  "companyId": "uuid",
  "budget": {
    "min": 5000,
    "max": 10000
  },
  "deadline": "2025-12-31",
  "microservices": [],
  "createdAt": "2025-01-01T00:00:00Z"
}
```

### GET /api/v1/projects
**Descrição**: Listar projetos da empresa
**Auth**: Required

**Query Parameters**:
```typescript
{
  "status"?: "DRAFT" | "PUBLISHED" | "IN_PROGRESS" | "COMPLETED",
  "search"?: string,
  "page"?: number,
  "limit"?: number,
  "sort"?: string
}
```

### GET /api/v1/projects/:id
**Descrição**: Obter detalhes do projeto
**Auth**: Required

**Path Parameters**:
- `id`: UUID do projeto

**Response 200**: Projeto completo com microserviços

### PUT /api/v1/projects/:id
**Descrição**: Atualizar projeto (apenas DRAFT)
**Auth**: Required (Owner only)

**Body Parameters**: Todos os campos do POST são opcionais

**Validações**:
- Projeto deve estar em status DRAFT
- Apenas o owner pode editar

### DELETE /api/v1/projects/:id
**Descrição**: Excluir projeto (apenas DRAFT)
**Auth**: Required (Owner only)

### POST /api/v1/projects/:id/decompose
**Descrição**: Decompor projeto em microserviços usando IA
**Auth**: Required (Owner only)

**Body Parameters**:
```typescript
{
  "aiProvider"?: "OPENAI" | "CLAUDE",  // Default: OPENAI
  "complexity"?: "SIMPLE" | "MODERATE" | "COMPLEX",
  "maxMicroservices"?: number,          // Max 20
  "autoPublish"?: boolean               // Publicar após decomposição
}
```

**Response 202**:
```json
{
  "message": "Decomposição iniciada",
  "jobId": "uuid",
  "estimatedTime": 30
}
```

### GET /api/v1/projects/:id/decomposition-status
**Descrição**: Verificar status da decomposição
**Auth**: Required

**Response 200**:
```json
{
  "jobId": "uuid",
  "status": "PROCESSING" | "COMPLETED" | "FAILED",
  "progress": 75,
  "result"?: {
    "microservices": [...]
  },
  "error"?: string
}
```

### POST /api/v1/projects/:id/microservices
**Descrição**: Adicionar microserviço manualmente
**Auth**: Required (Owner only)

**Body Parameters**:
```typescript
{
  "title": string,
  "description": string,
  "requirements": string,
  "estimatedHours": number,
  "requiredSkills": string[],
  "complexity": 1-5,
  "dependencies": string[]  // IDs de outros microserviços
}
```

### POST /api/v1/projects/:id/publish
**Descrição**: Publicar projeto no marketplace
**Auth**: Required (Owner only)

**Body Parameters**:
```typescript
{
  "publishNow"?: boolean,     // Default: true
  "scheduledFor"?: string    // ISO 8601 date para publicação futura
}
```

**Validações**:
- Projeto deve ter pelo menos 1 microserviço
- Todos os campos obrigatórios devem estar preenchidos
- Pagamento deve estar configurado

---

## 💰 ENDPOINTS DE PAGAMENTOS

### POST /api/v1/payments/create
**Descrição**: Criar cobrança no ASAAS
**Auth**: Required

**Body Parameters**:
```typescript
{
  "customerId": string,       // ID do cliente no ASAAS
  "billingType": "PIX" | "BOLETO" | "CREDIT_CARD",
  "value": number,           // Valor em BRL
  "dueDate": string,         // Data de vencimento
  "description": string,
  "projectId": string,       // ID do projeto relacionado
  "split"?: {                // Opcional: configurar split
    "walletId": string,
    "percentualValue": number
  }
}
```

**Response 201**:
```json
{
  "id": "asaas_payment_id",
  "invoiceUrl": "https://...",
  "pixQrCode": "data:image/png;base64,...",
  "pixCopyPaste": "00020126...",
  "status": "PENDING",
  "dueDate": "2025-01-10"
}
```

### GET /api/v1/payments/:id/pix-qr-code
**Descrição**: Obter QR Code PIX
**Auth**: Required

**Response 200**:
```json
{
  "qrCode": "data:image/png;base64,...",
  "copyPaste": "00020126...",
  "expiresAt": "2025-01-10T23:59:59Z"
}
```

### GET /api/v1/payments/:id/status
**Descrição**: Verificar status do pagamento
**Auth**: Required

**Response 200**:
```json
{
  "id": "payment_id",
  "status": "PENDING" | "RECEIVED" | "CONFIRMED" | "OVERDUE" | "REFUNDED",
  "value": 1000.00,
  "netValue": 950.00,
  "paidAt"?: "2025-01-05T10:00:00Z"
}
```

### POST /api/v1/payments/webhook
**Descrição**: Receber webhooks do ASAAS
**Auth**: ASAAS Token

**Headers**:
```
X-Asaas-Signature: {signature}
```

**Body**: Payload do ASAAS

**Response 200**: 
```json
{
  "received": true
}
```

---

## 💬 ENDPOINTS DE PROPOSTAS

### POST /api/v1/microservices/:id/proposals
**Descrição**: Submeter proposta para microserviço
**Auth**: Required (Freelancer only)

**Body Parameters**:
```typescript
{
  "coverLetter": string,      // Carta de apresentação
  "proposedValue": number,    // Valor proposto em BRL
  "estimatedDays": number,    // Prazo em dias
  "portfolio": string[],      // URLs de trabalhos anteriores
  "availability": string,     // Quando pode começar
  "milestones"?: [           // Opcional: marcos de entrega
    {
      "description": string,
      "value": number,
      "days": number
    }
  ]
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "microserviceId": "uuid",
  "freelancerId": "uuid",
  "status": "SUBMITTED",
  "proposedValue": 2000.00,
  "createdAt": "2025-01-01T00:00:00Z"
}
```

### GET /api/v1/proposals
**Descrição**: Listar propostas do freelancer
**Auth**: Required (Freelancer)

**Query Parameters**:
```typescript
{
  "status"?: "SUBMITTED" | "ACCEPTED" | "REJECTED" | "WITHDRAWN",
  "page"?: number,
  "limit"?: number
}
```

### PUT /api/v1/proposals/:id/accept
**Descrição**: Aceitar proposta
**Auth**: Required (Company owner)

**Response 200**:
```json
{
  "id": "uuid",
  "status": "ACCEPTED",
  "contractId": "uuid"  // Contrato criado automaticamente
}
```

---

## 🔔 ENDPOINTS DE NOTIFICAÇÕES

### GET /api/v1/notifications
**Descrição**: Listar notificações do usuário
**Auth**: Required

**Query Parameters**:
```typescript
{
  "unreadOnly"?: boolean,
  "type"?: string,
  "page"?: number,
  "limit"?: number
}
```

### PATCH /api/v1/notifications/:id/read
**Descrição**: Marcar notificação como lida
**Auth**: Required

### POST /api/v1/notifications/mark-all-read
**Descrição**: Marcar todas como lidas
**Auth**: Required

---

## 🔐 FASE 1 - AUTENTICAÇÃO E PERFIS BÁSICOS

**Prioridade**: CRÍTICA
**Tempo**: 1-2 semanas

### Módulo Auth

#### Endpoints de Autenticação
```typescript
// Better Auth geração automática
POST   /api/v1/auth/sign-in/email       # Login com email e senha
POST   /api/v1/auth/sign-up/email       # Cadastro novo usuário
POST   /api/v1/auth/sign-out            # Logout
POST   /api/v1/auth/refresh             # Renovar token
POST   /api/v1/auth/forgot-password     # Solicitar reset senha
POST   /api/v1/auth/reset-password      # Reset senha com token
POST   /api/v1/auth/verify-email        # Verificar email
POST   /api/v1/auth/resend-verification # Reenviar verificação
POST   /api/v1/auth/change-password     # Alterar senha
GET    /api/v1/auth/session            # Verificar sessão atual
```

#### Implementação Better Auth + CQRS
```typescript
// infrastructure/auth/better-auth.config.ts
import { BetterAuth } from "better-auth"
import { prisma } from "../database/prisma"

export const auth = new BetterAuth({
  database: {
    provider: "postgresql",
    client: prisma
  },
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: true
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24 // 24 hours
  },
  advanced: {
    generateId: () => crypto.randomUUID()
  }
})

// application/commands/auth/sign-in.command.ts
import { ICommand } from '@nestjs/cqrs'

export class SignInCommand implements ICommand {
  constructor(
    public readonly email: string,
    public readonly password: string,
    public readonly ipAddress: string,
    public readonly userAgent: string
  ) {}
}

// application/commands/auth/sign-in.handler.ts
import { CommandHandler, ICommandHandler } from '@nestjs/cqrs'
import { auth } from '../../../infrastructure/auth/better-auth.config'

@CommandHandler(SignInCommand)
export class SignInHandler implements ICommandHandler<SignInCommand> {
  async execute(command: SignInCommand) {
    const { email, password, ipAddress, userAgent } = command
    
    try {
      const session = await auth.api.signInEmail({
        email,
        password,
        userAgent,
        ipAddress
      })
      
      return {
        success: true,
        user: session.user,
        session: session.session
      }
    } catch (error) {
      throw new UnauthorizedException('Invalid credentials')
    }
  }
}

// presentation/controllers/auth.controller.ts
@Controller('api/v1/auth')
@ApiTags('Authentication')
export class AuthController {
  constructor(
    private commandBus: CommandBus,
    private queryBus: QueryBus
  ) {}

  @Post('sign-in/email')
  @ApiOperation({ summary: 'Login com email e senha' })
  async signIn(
    @Body() signInDto: SignInDto,
    @Req() req: Request
  ) {
    const command = new SignInCommand(
      signInDto.email,
      signInDto.password,
      req.ip,
      req.get('User-Agent')
    )
    return this.commandBus.execute(command)
  }

  @Post('sign-up/email')
  @ApiOperation({ summary: 'Registro de novo usuário' })
  async signUp(@Body() signUpDto: SignUpDto) {
    const command = new SignUpCommand(
      signUpDto.email,
      signUpDto.password,
      signUpDto.type
    )
    return this.commandBus.execute(command)
  }

  @Get('session')
  @ApiOperation({ summary: 'Verificar sessão atual' })
  async getSession(@Req() req: Request) {
    const query = new GetSessionQuery(req.headers.authorization)
    return this.queryBus.execute(query)
  }
}
```

### Módulo Users

#### Endpoints de Usuários
```typescript
GET    /api/v1/users/profile            # Perfil do usuário autenticado
PUT    /api/v1/users/profile            # Atualizar dados básicos
GET    /api/v1/users/sessions           # Listar sessões ativas
DELETE /api/v1/users/sessions/:id       # Encerrar sessão específica
DELETE /api/v1/users/account            # Solicitar exclusão (LGPD)
```

#### Implementação
```typescript
// users.service.ts
@Injectable()
export class UsersService {
  constructor(private prisma: PrismaService) {}

  async findById(id: string) {
    return this.prisma.user.findUnique({
      where: { id },
      include: {
        companyProfile: true,
        freelancerProfile: true
      }
    });
  }

  async updateProfile(id: string, updateUserDto: UpdateUserDto) {
    return this.prisma.user.update({
      where: { id },
      data: updateUserDto
    });
  }
}
```

### Módulo Companies

#### Endpoints de Empresas
```typescript
POST   /api/v1/companies/profile        # Criar perfil empresa
GET    /api/v1/companies/profile        # Obter perfil empresa
PUT    /api/v1/companies/profile        # Atualizar perfil empresa
GET    /api/v1/companies/:id            # Ver perfil público empresa
POST   /api/v1/companies/verify         # Enviar documentos verificação
```

### Módulo Freelancers

#### Endpoints de Freelancers
```typescript
POST   /api/v1/freelancers/profile      # Criar perfil freelancer
GET    /api/v1/freelancers/profile      # Obter perfil freelancer
PUT    /api/v1/freelancers/profile      # Atualizar perfil freelancer
GET    /api/v1/freelancers/:id          # Ver perfil público freelancer
GET    /api/v1/freelancers              # Buscar freelancers (empresas)

// Skills
GET    /api/v1/freelancers/skills       # Listar skills freelancer
POST   /api/v1/freelancers/skills       # Adicionar skills
PUT    /api/v1/freelancers/skills/:id   # Atualizar proficiência
DELETE /api/v1/freelancers/skills/:id   # Remover skill
```

### Módulo Skills

#### Endpoints de Skills
```typescript
GET    /api/v1/skills                   # Listar todas skills
GET    /api/v1/skills/:id               # Detalhes de uma skill
GET    /api/v1/skills/categories        # Listar categorias
```

## 🚀 FASE 2 - CORE BUSINESS (PROJETOS)

**Prioridade**: ALTA
**Tempo**: 2-3 semanas

### Módulo Projects

#### Endpoints de Projetos
```typescript
GET    /api/v1/projects                 # Listar projetos da empresa
POST   /api/v1/projects                 # Criar novo projeto
GET    /api/v1/projects/:id             # Detalhes do projeto
PUT    /api/v1/projects/:id             # Atualizar projeto (DRAFT)
DELETE /api/v1/projects/:id             # Excluir projeto (DRAFT)
POST   /api/v1/projects/:id/clone       # Clonar projeto existente
PATCH  /api/v1/projects/:id/status      # Alterar status
POST   /api/v1/projects/:id/publish     # Publicar projeto
```

#### Implementação
```typescript
// projects.controller.ts
@Controller('api/v1/projects')
@ApiTags('Projects')
@UseGuards(JwtAuthGuard)
export class ProjectsController {
  constructor(private projectsService: ProjectsService) {}

  @Post()
  @ApiOperation({ summary: 'Criar novo projeto' })
  async create(@Body() createProjectDto: CreateProjectDto, @Request() req) {
    return this.projectsService.create(createProjectDto, req.user.id);
  }

  @Get()
  @ApiOperation({ summary: 'Listar projetos da empresa' })
  async findAll(@Request() req, @Query() query: ProjectQueryDto) {
    return this.projectsService.findAllByCompany(req.user.companyId, query);
  }

  @Post(':id/publish')
  @ApiOperation({ summary: 'Publicar projeto após decomposição' })
  async publish(@Param('id') id: string) {
    return this.projectsService.publish(id);
  }
}
```

### Decomposição por IA

#### Endpoints de IA
```typescript
POST   /api/v1/projects/:id/decompose            # Decompor projeto em microserviços
GET    /api/v1/projects/:id/decomposition-status # Status da decomposição
GET    /api/v1/ai/requests                       # Histórico requisições IA
GET    /api/v1/ai/usage                          # Uso e limites de IA
```

#### Integração com IA
```typescript
// ai.service.ts
@Injectable()
export class AiService {
  constructor(
    private openai: OpenAI,
    private prisma: PrismaService
  ) {}

  async decomposeProject(projectId: string) {
    const project = await this.prisma.project.findUnique({
      where: { id: projectId }
    });

    const prompt = this.buildDecompositionPrompt(project);
    
    const completion = await this.openai.chat.completions.create({
      model: "gpt-4",
      messages: [{ role: "user", content: prompt }],
      temperature: 0.3
    });

    const microservices = this.parseAiResponse(completion.choices[0].message.content);
    
    // Salvar microserviços no banco
    return this.saveMicroservices(projectId, microservices);
  }

  private buildDecompositionPrompt(project: any): string {
    return `
      Analise o projeto abaixo e decomponha em microserviços técnicos específicos:
      
      Título: ${project.title}
      Descrição: ${project.description}
      Requisitos: ${project.requirements}
      Orçamento: ${project.budget}
      
      Retorne um JSON com microserviços no formato:
      {
        "microservices": [
          {
            "title": "Nome do microserviço",
            "description": "Descrição técnica detalhada",
            "estimatedHours": 40,
            "complexityLevel": 3,
            "requiredSkills": ["React", "Node.js"],
            "dependencies": [],
            "priority": "high"
          }
        ]
      }
    `;
  }
}
```

### Módulo Microservices

#### Endpoints de Microserviços
```typescript
GET    /api/v1/microservices                    # Listar microserviços disponíveis
GET    /api/v1/microservices/:id                # Detalhes do microserviço
GET    /api/v1/microservices/recommended        # Recomendados por IA
GET    /api/v1/projects/:id/microservices       # Microserviços do projeto
POST   /api/v1/projects/:id/microservices       # Adicionar microserviço manual
PUT    /api/v1/projects/:id/microservices/:mid  # Editar microserviço
DELETE /api/v1/projects/:id/microservices/:mid  # Remover microserviço
```

## 🏪 FASE 3 - MARKETPLACE (PROPOSTAS)

**Prioridade**: ALTA
**Tempo**: 2-3 semanas

### Módulo Proposals

#### Endpoints de Propostas
```typescript
// Freelancers
GET    /api/v1/proposals                        # Listar propostas do freelancer
POST   /api/v1/microservices/:id/proposals      # Submeter proposta
GET    /api/v1/proposals/:id                    # Ver detalhes da proposta
PUT    /api/v1/proposals/:id                    # Editar proposta (SUBMITTED)
DELETE /api/v1/proposals/:id                    # Cancelar proposta
GET    /api/v1/proposals/:id/ai-analysis        # Análise de IA da proposta

// Empresas  
GET    /api/v1/microservices/:id/proposals      # Ver propostas do microserviço
PUT    /api/v1/proposals/:id/accept             # Aceitar proposta
PUT    /api/v1/proposals/:id/reject             # Rejeitar proposta
POST   /api/v1/proposals/:id/counter-offer      # Contra-proposta
```

#### Implementação
```typescript
// proposals.service.ts
@Injectable()
export class ProposalsService {
  constructor(private prisma: PrismaService) {}

  async create(createProposalDto: CreateProposalDto, freelancerId: string) {
    // Verificar se freelancer já tem proposta ativa
    const existingProposal = await this.prisma.proposal.findFirst({
      where: {
        microserviceId: createProposalDto.microserviceId,
        freelancerId,
        status: 'SUBMITTED'
      }
    });

    if (existingProposal) {
      throw new ConflictException('Você já possui uma proposta ativa para este microserviço');
    }

    return this.prisma.proposal.create({
      data: {
        ...createProposalDto,
        freelancerId,
        status: 'SUBMITTED',
        submittedAt: new Date()
      }
    });
  }

  async acceptProposal(proposalId: string, companyId: string) {
    // Verificar se proposta pertence à empresa
    const proposal = await this.prisma.proposal.findFirst({
      where: {
        id: proposalId,
        microservice: {
          project: {
            companyId
          }
        }
      },
      include: {
        microservice: {
          include: {
            project: true
          }
        }
      }
    });

    if (!proposal) {
      throw new NotFoundException('Proposta não encontrada');
    }

    // Aceitar proposta e rejeitar outras
    return this.prisma.$transaction(async (tx) => {
      // Rejeitar outras propostas
      await tx.proposal.updateMany({
        where: {
          microserviceId: proposal.microserviceId,
          id: { not: proposalId }
        },
        data: { status: 'REJECTED' }
      });

      // Aceitar esta proposta
      await tx.proposal.update({
        where: { id: proposalId },
        data: { status: 'ACCEPTED' }
      });

      // Criar contrato
      return this.createContract(tx, proposal);
    });
  }
}
```

### Módulo Contracts

#### Endpoints de Contratos
```typescript
GET    /api/v1/contracts                        # Listar contratos
POST   /api/v1/contracts                        # Criar contrato manual
GET    /api/v1/contracts/:id                    # Ver detalhes
PUT    /api/v1/contracts/:id                    # Atualizar contrato
PUT    /api/v1/contracts/:id/sign               # Assinar contrato
PUT    /api/v1/contracts/:id/complete           # Marcar como completo
PUT    /api/v1/contracts/:id/terminate          # Encerrar antecipadamente
POST   /api/v1/contracts/:id/dispute            # Abrir disputa
GET    /api/v1/contracts/:id/document           # Gerar PDF
POST   /api/v1/contracts/:id/invoice            # Gerar/enviar nota fiscal
GET    /api/v1/contracts/:id/invoices           # Listar notas fiscais

// Milestones
PUT    /api/v1/contracts/:id/milestones/:mid/approve  # Aprovar milestone
PUT    /api/v1/contracts/:id/milestones/:mid          # Atualizar milestone
```

## 💳 FASE 4 - PAGAMENTOS (ASAAS)

**Prioridade**: CRÍTICA
**Tempo**: 3-4 semanas

### Integração ASAAS

#### Configuração
```typescript
// asaas.config.ts
export const asaasConfig = {
  baseUrl: process.env.ASAAS_BASE_URL,
  apiKey: process.env.ASAAS_API_KEY,
  webhookUrl: process.env.ASAAS_WEBHOOK_URL,
  environment: process.env.NODE_ENV === 'production' ? 'production' : 'sandbox'
};

// asaas.service.ts
@Injectable()
export class AsaasService {
  private readonly http: HttpService;

  constructor() {
    this.http = new HttpService({
      baseURL: asaasConfig.baseUrl,
      headers: {
        'access_token': asaasConfig.apiKey,
        'Content-Type': 'application/json'
      }
    });
  }

  async createCustomer(createCustomerDto: CreateCustomerDto) {
    const response = await this.http.post('/customers', createCustomerDto);
    return response.data;
  }

  async createPayment(createPaymentDto: CreatePaymentDto) {
    const response = await this.http.post('/payments', createPaymentDto);
    return response.data;
  }

  async getPixQrCode(paymentId: string) {
    const response = await this.http.get(`/payments/${paymentId}/pixQrCode`);
    return response.data;
  }
}
```

### Módulo Payments

#### Endpoints Essenciais MVP
```typescript
// APIs Críticas para MVP
POST   /api/v1/payments/create              # Criar cobrança PIX
GET    /api/v1/payments/:id/pix-qr-code     # Obter QR Code PIX  
GET    /api/v1/payments/:id/status          # Verificar se foi pago
POST   /api/v1/payments/webhook             # Receber notificação ASAAS

// APIs Completas
GET    /api/v1/payments                     # Listar pagamentos
GET    /api/v1/payments/:id                 # Ver detalhes
GET    /api/v1/payments/:id/boleto          # Obter boleto
POST   /api/v1/payments/:id/cancel          # Cancelar pagamento
POST   /api/v1/payments/:id/refund          # Solicitar estorno
GET    /api/v1/payments/:id/refunds         # Listar estornos
POST   /api/v1/payments/:id/split           # Configurar split
GET    /api/v1/payments/history             # Histórico detalhado
GET    /api/v1/payments/statistics          # Estatísticas

// Métodos de Pagamento
GET    /api/v1/payments/methods             # Listar métodos
POST   /api/v1/payments/methods             # Adicionar método
PUT    /api/v1/payments/methods/:id         # Atualizar método
DELETE /api/v1/payments/methods/:id         # Remover método
POST   /api/v1/payments/methods/:id/set-default # Método padrão
```

#### Implementação Pagamentos
```typescript
// payments.controller.ts
@Controller('api/v1/payments')
@ApiTags('Payments')
export class PaymentsController {
  constructor(
    private paymentsService: PaymentsService,
    private asaasService: AsaasService
  ) {}

  @Post('create')
  @ApiOperation({ summary: 'Criar cobrança PIX/Boleto' })
  async createPayment(@Body() createPaymentDto: CreatePaymentDto) {
    return this.paymentsService.createPayment(createPaymentDto);
  }

  @Get(':id/pix-qr-code')
  @ApiOperation({ summary: 'Obter QR Code PIX' })
  async getPixQrCode(@Param('id') paymentId: string) {
    return this.asaasService.getPixQrCode(paymentId);
  }

  @Get(':id/status')
  @ApiOperation({ summary: 'Verificar status do pagamento' })
  async getPaymentStatus(@Param('id') paymentId: string) {
    return this.paymentsService.getPaymentStatus(paymentId);
  }

  @Post('webhook')
  @ApiOperation({ summary: 'Webhook ASAAS' })
  async handleWebhook(@Body() webhookData: any, @Headers() headers: any) {
    // Validar assinatura HMAC
    const isValid = this.paymentsService.validateWebhookSignature(webhookData, headers);
    if (!isValid) {
      throw new UnauthorizedException('Invalid webhook signature');
    }

    return this.paymentsService.processWebhook(webhookData);
  }
}
```

### Webhooks ASAAS

#### Processamento de Webhooks
```typescript
// payments.service.ts
@Injectable()
export class PaymentsService {
  async processWebhook(webhookData: any) {
    const { event, payment } = webhookData;

    // Salvar evento de webhook
    await this.prisma.asaasWebhook.create({
      data: {
        asaasEventId: payment.id,
        eventType: event,
        objectType: 'payment',
        objectId: payment.id,
        payload: webhookData,
        processed: false,
        receivedAt: new Date()
      }
    });

    // Processar evento
    switch (event) {
      case 'PAYMENT_CONFIRMED':
        return this.handlePaymentConfirmed(payment);
      case 'PAYMENT_RECEIVED':
        return this.handlePaymentReceived(payment);
      case 'PAYMENT_OVERDUE':
        return this.handlePaymentOverdue(payment);
      default:
        console.log(`Evento não processado: ${event}`);
    }
  }

  private async handlePaymentReceived(payment: any) {
    // Atualizar status do pagamento
    await this.prisma.payment.update({
      where: { asaasPaymentId: payment.id },
      data: {
        status: 'RECEIVED',
        paymentDate: new Date(payment.paymentDate),
        confirmationDate: new Date()
      }
    });

    // Liberar escrow e notificar
    return this.releaseEscrowAndNotify(payment.id);
  }

  validateWebhookSignature(data: any, headers: any): boolean {
    const signature = headers['asaas-access-token'];
    // Implementar validação HMAC
    return true; // Simplificado
  }
}
```

### Antecipação de Recebíveis

#### Endpoints de Antecipação
```typescript
GET    /api/v1/advances/eligibility        # Verificar elegibilidade
POST   /api/v1/advances/simulate           # Simular antecipação
POST   /api/v1/advances/request            # Solicitar antecipação
GET    /api/v1/advances                    # Listar antecipações
GET    /api/v1/advances/:id                # Status da antecipação
POST   /api/v1/advances/:id/accept         # Aceitar proposta
```

### Transferências para Freelancers

#### Endpoints de Transferência
```typescript
GET    /api/v1/transfers                   # Listar transferências
POST   /api/v1/transfers/create            # Criar transferência
GET    /api/v1/transfers/:id               # Status da transferência
POST   /api/v1/transfers/:id/cancel        # Cancelar transferência
```

### Financeiro do Usuário

#### Endpoints Financeiros
```typescript
GET    /api/v1/users/financial/balance     # Visualizar saldo
GET    /api/v1/users/financial/pending     # Valores pendentes
GET    /api/v1/users/financial/summary     # Resumo financeiro
GET    /api/v1/users/financial/transactions # Histórico transações
```

## 📡 MÓDULOS AUXILIARES

### Chat/Mensagens
```typescript
GET    /api/v1/conversations               # Listar conversas
POST   /api/v1/conversations               # Iniciar conversa
GET    /api/v1/conversations/:id/messages  # Mensagens da conversa
POST   /api/v1/conversations/:id/messages  # Enviar mensagem
PUT    /api/v1/messages/:id/read           # Marcar como lida
```

### Notificações
```typescript
GET    /api/v1/notifications               # Listar notificações
POST   /api/v1/notifications               # Criar notificação
PUT    /api/v1/notifications/:id/read      # Marcar como lida
DELETE /api/v1/notifications/:id           # Excluir notificação
PUT    /api/v1/notifications/read-all      # Marcar todas como lidas
```

### WebSockets
```typescript
// websocket.gateway.ts
@WebSocketGateway({
  cors: {
    origin: process.env.FRONTEND_URL,
    credentials: true
  }
})
export class WebsocketGateway {
  @WebSocketServer()
  server: Server;

  @SubscribeMessage('join-room')
  handleJoinRoom(@MessageBody() data: { roomId: string }, @ConnectedSocket() client: Socket) {
    client.join(data.roomId);
    return { event: 'joined-room', data: { roomId: data.roomId } };
  }

  @SubscribeMessage('send-message')
  async handleMessage(@MessageBody() data: CreateMessageDto, @ConnectedSocket() client: Socket) {
    // Salvar mensagem no banco
    const message = await this.messagesService.create(data);
    
    // Enviar para todos na sala
    this.server.to(data.conversationId).emit('new-message', message);
    
    return message;
  }

  // Notificação de pagamento recebido
  notifyPaymentReceived(userId: string, payment: any) {
    this.server.to(`user-${userId}`).emit('payment-received', payment);
  }
}
```

## 🛠️ CONFIGURAÇÃO E SETUP

### Dependências Principais
```json
{
  "dependencies": {
    "@nestjs/common": "^11.1.5",
    "@nestjs/core": "^11.1.5",
    "@nestjs/platform-express": "^11.1.5",
    "@nestjs/platform-socket.io": "^11.1.5",
    "@nestjs/websockets": "^11.1.5",
    "@nestjs/cqrs": "^11.1.5",
    "@nestjs/swagger": "^8.0.5",
    "@nestjs/throttler": "^6.2.1",
    "@prisma/client": "^6.13.0",
    "prisma": "^6.13.0",
    "better-auth": "^1.3.4",
    "bcrypt": "^5.1.1",
    "class-validator": "^0.14.2",
    "class-transformer": "^0.5.1",
    "socket.io": "^4.8.1",
    "axios": "^1.7.9",
    "openai": "^5.12.0",
    "ioredis": "^5.7.0"
  },
  "devDependencies": {
    "@nestjs/cli": "^11.0.0",
    "@nestjs/bullmq": "^11.0.3",
    "@aws-sdk/client-s3": "^3.859.0",
    "bullmq": "^5.0.0",
    "@nestjs/testing": "^11.1.5",
    "@types/bcrypt": "^5.0.2",
    "@types/node": "^22.0.0",
    "jest": "^29.7.0",
    "supertest": "^7.0.0",
    "ts-jest": "^29.2.0",
    "typescript": "^5.9.2",
    "@thallesp/nestjs-better-auth": "^1.0.0",
    "eslint": "^9.15.0",
    "prettier": "^3.4.2"
  }
}
```

### Docker Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3333:3333"
    environment:
      - DATABASE_URL=postgresql://demandei:password@postgres:5432/demandei
      - REDIS_URL=redis://redis:6379
      - BETTER_AUTH_SECRET=your-better-auth-secret
      - ASAAS_API_KEY=your-asaas-key
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=demandei
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=demandei
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Configurações de Ambiente
```env
# .env
NODE_ENV=development
PORT=3333

# Database
DATABASE_URL="postgresql://demandei:password@localhost:5432/demandei?schema=public"

# Better Auth
BETTER_AUTH_SECRET="your-super-secret-better-auth-key"
BETTER_AUTH_URL="http://localhost:3333"

# Redis
REDIS_URL="redis://localhost:6379"

# ASAAS
ASAAS_API_KEY="your-asaas-api-key"
ASAAS_BASE_URL="https://www.asaas.com/api/v3"
ASAAS_WEBHOOK_URL="https://yourapp.com/api/v1/payments/webhook"

# OpenAI
OPENAI_API_KEY="your-openai-key"

# Frontend
FRONTEND_URL="http://localhost:3000"

# Email
SMTP_HOST="smtp.resend.com"
SMTP_USER="resend"
SMTP_PASS="your-resend-key"
```

## 🧪 TESTING

### Estrutura de Testes CQRS
```typescript
// application/commands/create-project.handler.spec.ts
describe('CreateProjectHandler', () => {
  let handler: CreateProjectHandler;
  let repository: jest.Mocked<IProjectRepository>;
  let eventBus: jest.Mocked<EventBus>;

  beforeEach(() => {
    repository = {
      save: jest.fn(),
      findById: jest.fn(),
      delete: jest.fn()
    };
    
    eventBus = {
      publish: jest.fn()
    };
    
    handler = new CreateProjectHandler(repository, eventBus);
  });

  describe('execute', () => {
    it('should create project and publish event', async () => {
      const command = new CreateProjectCommand(
        'Test Project',
        'Description',
        'company-id',
        { min: 1000, max: 5000 }
      );

      const projectId = await handler.execute(command);

      expect(repository.save).toHaveBeenCalledWith(
        expect.any(ProjectEntity)
      );
      expect(eventBus.publish).toHaveBeenCalledWith(
        expect.any(ProjectCreatedEvent)
      );
      expect(projectId).toBeDefined();
    });
  });
});

// domain/entities/project.entity.spec.ts
describe('ProjectEntity', () => {
  it('should create project in draft status', () => {
    const project = ProjectEntity.create({
      title: 'Test Project',
      description: 'Test Description',
      companyId: 'company-id',
      budget: { min: 1000, max: 5000 }
    });

    expect(project.status).toBe(ProjectStatus.DRAFT);
    expect(project.title).toBe('Test Project');
  });

  it('should publish draft project', () => {
    const project = ProjectEntity.create({
      title: 'Test Project',
      description: 'Test Description', 
      companyId: 'company-id',
      budget: { min: 1000, max: 5000 }
    });

    project.publish();

    expect(project.status).toBe(ProjectStatus.PUBLISHED);
  });

  it('should throw error when publishing non-draft project', () => {
    const project = ProjectEntity.create({
      title: 'Test Project',
      description: 'Test Description',
      companyId: 'company-id', 
      budget: { min: 1000, max: 5000 }
    });
    
    project.publish(); // First publish

    expect(() => project.publish()).toThrow(
      'Only draft projects can be published'
    );
  });
});

// presentation/controllers/projects.controller.spec.ts
describe('ProjectsController', () => {
  let controller: ProjectsController;
  let commandBus: jest.Mocked<CommandBus>;
  let queryBus: jest.Mocked<QueryBus>;

  beforeEach(async () => {
    commandBus = {
      execute: jest.fn()
    };
    
    queryBus = {
      execute: jest.fn()
    };

    const module: TestingModule = await Test.createTestingModule({
      controllers: [ProjectsController],
      providers: [
        {
          provide: CommandBus,
          useValue: commandBus
        },
        {
          provide: QueryBus,
          useValue: queryBus
        }
      ]
    }).compile();

    controller = module.get<ProjectsController>(ProjectsController);
  });

  describe('create', () => {
    it('should execute CreateProjectCommand', async () => {
      const dto = {
        title: 'Test Project',
        description: 'Description',
        budget: { min: 1000, max: 5000 }
      };
      
      const user = { companyId: 'company-id' };
      commandBus.execute.mockResolvedValue('project-id');

      const result = await controller.create(dto, user);

      expect(commandBus.execute).toHaveBeenCalledWith(
        expect.any(CreateProjectCommand)
      );
      expect(result).toEqual({ projectId: 'project-id' });
    });
  });
});
```

## 📊 MONITORAMENTO E LOGS

### Health Checks
```typescript
// health.controller.ts
@Controller('health')
export class HealthController {
  constructor(
    private prisma: PrismaService,
    private redis: Redis
  ) {}

  @Get()
  async check() {
    const checks = await Promise.allSettled([
      this.checkDatabase(),
      this.checkRedis(),
      this.checkAsaas()
    ]);

    return {
      status: 'ok',
      timestamp: new Date().toISOString(),
      checks: {
        database: checks[0],
        redis: checks[1],
        asaas: checks[2]
      }
    };
  }

  private async checkDatabase() {
    await this.prisma.$queryRaw`SELECT 1`;
    return { status: 'healthy' };
  }
}
```

### Logging
```typescript
// Configuração de logs estruturados
import { Logger, LoggerService } from '@nestjs/common';

@Injectable()
export class CustomLogger implements LoggerService {
  private logger = new Logger();

  log(message: string, context?: string) {
    this.logger.log({
      level: 'info',
      message,
      context,
      timestamp: new Date().toISOString()
    });
  }

  error(message: string, trace?: string, context?: string) {
    this.logger.error({
      level: 'error', 
      message,
      trace,
      context,
      timestamp: new Date().toISOString()
    });
  }
}
```

## 🚀 DEPLOY E CI/CD

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install
      - run: npm run test
      - run: npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        run: |
          # Deploy commands here
          echo "Deploying to production..."
```

## 📈 MÉTRICAS DE SUCESSO

### KPIs Técnicos
- **Response Time**: < 200ms (95% requests)
- **Uptime**: > 99.9%
- **Error Rate**: < 0.1%
- **Database Performance**: < 50ms queries
- **WebSocket Latency**: < 100ms

### Métricas de Negócio
- **Projetos processados**: Meta 100+/mês
- **Taxa de conversão**: 15% (proposta → contrato)
- **Tempo de decomposição IA**: < 30s
- **Satisfação API**: NPS > 80

## 🎯 PRÓXIMOS PASSOS

### Semana 1-2: Setup e Auth
1. Configurar projeto NestJS
2. Setup PostgreSQL + Prisma
3. Implementar autenticação Better Auth + CQRS
4. CRUD básico de usuários/perfis

### Semana 3-4: Core Business
1. CRUD completo de projetos
2. Integração OpenAI para decomposição
3. Sistema de microserviços
4. Testes automatizados

### Semana 5-6: Marketplace
1. Sistema de propostas
2. Workflow de contratos
3. Chat WebSocket
4. Notificações

### Semana 7-8: Pagamentos
1. Integração ASAAS completa
2. Webhooks e processamento
3. Sistema de escrow
4. Antecipação de recebíveis

### Semana 9-10: Polimento
1. Otimizações de performance
2. Monitoramento e logs
3. Deploy e CI/CD
4. Documentação final

## 📋 CHECKLIST DE ENTREGA

- [ ] Sistema de autenticação funcionando
- [ ] CRUD completo de projetos
- [ ] IA de decomposição operacional
- [ ] Sistema de propostas e contratos
- [ ] Integração ASAAS com PIX
- [ ] Chat em tempo real
- [ ] Sistema de notificações
- [ ] Testes unitários > 80% coverage
- [ ] Documentação API (Swagger)
- [ ] Deploy automatizado
- [ ] Monitoramento e logs
- [ ] Performance < 200ms
- [ ] Segurança (HTTPS, validações, rate limiting)

Este escopo completo do backend oferece uma base sólida e escalável para o MVP da Demandei, implementando **CQRS + Clean Architecture** com **Better Auth**, focado na stack **NestJS + PostgreSQL + Prisma + ASAAS**. A arquitetura está estruturada em camadas bem definidas e fases lógicas de desenvolvimento, preparada para crescimento e manutenção de longo prazo.

### ✅ **Vantagens da Arquitetura Escolhida**

**CQRS + Clean Architecture**:
- **Separação clara** entre operações de leitura e escrita
- **Escalabilidade independente** de commands e queries  
- **Testabilidade superior** com domain logic isolada
- **Manutenibilidade** através de responsabilidades bem definidas
- **Performance otimizada** para diferentes tipos de operação

**Better Auth vs JWT tradicional**:
- **Segurança nativa** com session management
- **Developer Experience** superior com APIs type-safe
- **Escalabilidade** com database sessions
- **Compliance** com padrões modernos de autenticação
- **Flexibilidade** para diferentes providers (email, OAuth, etc.)

**Stack Tecnológica Moderna**:
- **NestJS 10+**: Framework enterprise com decorators e DI
- **PostgreSQL 17.5**: Performance e features mais recentes
- **Prisma ORM**: Type safety e developer experience
- **ASAAS Gateway**: Pagamentos otimizados para o Brasil
- **Redis 7.4**: Cache e session store de alta performance