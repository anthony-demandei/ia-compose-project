# BANCO DE DADOS SCHEMA COMPLETO - DEMANDEI

## 🎯 VISÃO GERAL

### Stack Tecnológica Definida
- **Banco Principal**: PostgreSQL 17.5
- **ORM**: Prisma (para NestJS) / Drizzle ORM (alternativa)
- **Cache**: Redis 8.0
- **Search Engine**: PostgreSQL Full-text Search + GIN indexes
- **File Storage**: AWS S3 / MinIO
- **Backup**: PostgreSQL Point-in-time Recovery (PITR)
- **Monitoring**: PostgreSQL Stats + pgAdmin

### Características da Arquitetura
- **ACID Compliance**: Transações seguras para operações críticas
- **Row Level Security (RLS)**: Isolamento de dados por tenant
- **Extensões**: UUID, JSONB, Full-text Search, Temporal Tables
- **Particionamento**: Por data (logs) e por tenant (escalabilidade)
- **Replicação**: Primary-Replica para alta disponibilidade
- **Criptografia**: Dados sensíveis criptografados (AES-256)

## 📊 ARQUITETURA DE DADOS

### Princípios de Design
- **Domain-Driven Design (DDD)**: Modelagem baseada no domínio do negócio
- **Event Sourcing**: Auditoria completa de mudanças críticas
- **CQRS Pattern**: Separação de leitura e escrita para performance
- **Soft Delete**: Exclusões lógicas para preservar integridade
- **Temporal Data**: Histórico de alterações para compliance
- **Multi-tenant**: Isolamento de dados por empresa

### Padrões de Nomenclatura
```sql
-- Tabelas: snake_case no plural
CREATE TABLE users (...);
CREATE TABLE company_profiles (...);

-- Colunas: snake_case descritivo  
user_id, created_at, email_verified_at

-- Índices: prefixo + tabela + coluna + tipo
idx_users_email_unique
idx_projects_company_id_btree

-- Constraints: prefixo + tabela + condição
ck_users_email_format
fk_projects_company_id

-- Sequences: tabela + id + seq
users_id_seq
```

## 🗂️ SCHEMA PRISMA COMPLETO

### Schema Base
```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ======================
// MÓDULO DE USUÁRIOS
// ======================

model User {
  id        String   @id @default(uuid()) @db.Uuid
  email     String   @unique @db.VarChar(255)
  password  String   @db.VarChar(255)
  type      UserType @default(FREELANCER)
  
  // Verificação de email
  emailVerified     Boolean   @default(false)
  emailVerifiedAt   DateTime?
  emailVerifyToken  String?   @unique @db.VarChar(255)
  
  // Two-factor authentication
  twoFactorEnabled Boolean @default(false)
  twoFactorSecret  String? @db.VarChar(32)
  
  // Controle de acesso
  isActive     Boolean   @default(true)
  lastLoginAt  DateTime?
  loginAttempts Int      @default(0)
  lockedUntil   DateTime?
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  companyProfile    CompanyProfile?
  freelancerProfile FreelancerProfile?
  sessions          UserSession[]
  notifications     Notification[]
  sentMessages      Message[]           @relation("MessageSender")
  receivedMessages  Message[]           @relation("MessageReceiver")
  reviews           Review[]
  auditLogs         AuditLog[]
  
  // Financeiro
  asaasCustomer AsaasCustomer?
  paymentsSent  Payment[]      @relation("PaymentPayer")
  paymentsReceived Payment[]   @relation("PaymentPayee")
  
  @@map("users")
}

enum UserType {
  COMPANY
  FREELANCER
  ADMIN
  
  @@map("user_type")
}

model UserSession {
  id               String    @id @default(uuid()) @db.Uuid
  userId           String    @db.Uuid
  tokenHash        String    @unique @db.VarChar(255)
  refreshTokenHash String?   @unique @db.VarChar(255)
  ipAddress        String    @db.Inet
  userAgent        String    @db.Text
  expiresAt        DateTime
  revokedAt        DateTime?
  createdAt        DateTime  @default(now())
  
  // Relacionamentos
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  @@index([userId])
  @@index([expiresAt])
  @@map("user_sessions")
}

// ======================
// MÓDULO DE PERFIS
// ======================

model CompanyProfile {
  id          String @id @default(uuid()) @db.Uuid
  userId      String @unique @db.Uuid
  
  // Dados corporativos
  companyName    String  @db.VarChar(255)
  tradingName    String? @db.VarChar(255)
  cnpj           String  @unique @db.VarChar(18)
  businessArea   String  @db.VarChar(100)
  companySize    CompanySize
  description    String? @db.Text
  website        String? @db.VarChar(255)
  
  // Endereço
  address Json @db.JsonB // { street, number, complement, city, state, zipCode, country }
  
  // Verificação
  verificationStatus     VerificationStatus @default(PENDING)
  verificationDocuments  String[] // URLs dos documentos
  verifiedAt             DateTime?
  
  // ASAAS integration
  asaasAccountType String? @db.VarChar(20) // "JURIDICA"
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  user     User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  projects Project[]
  
  @@index([cnpj])
  @@index([verificationStatus])
  @@map("company_profiles")
}

enum CompanySize {
  STARTUP      // 1-10 funcionários
  SMALL        // 11-50 funcionários  
  MEDIUM       // 51-200 funcionários
  LARGE        // 200+ funcionários
  ENTERPRISE   // 1000+ funcionários
  
  @@map("company_size")
}

model FreelancerProfile {
  id     String @id @default(uuid()) @db.Uuid
  userId String @unique @db.Uuid
  
  // Dados pessoais
  fullName         String  @db.VarChar(255)
  cpf              String  @unique @db.VarChar(14)
  professionalTitle String @db.VarChar(255)
  bio              String? @db.Text
  
  // Dados profissionais
  hourlyRate       Decimal  @db.Decimal(10,2)
  availability     Int      @default(40) // horas por semana
  workPreference   WorkPreference @default(REMOTE)
  
  // Portfólio
  portfolioUrl String? @db.VarChar(255)
  githubUrl    String? @db.VarChar(255)
  linkedinUrl  String? @db.VarChar(255)
  
  // Dados bancários (criptografados)
  bankDetails String? @db.Text // JSON criptografado
  pixKey      String? @db.VarChar(255) // Criptografado
  
  // ASAAS integration
  asaasAccountType String? @db.VarChar(20) // "FISICA" or "MEI"
  
  // Métricas
  rating            Decimal @default(0) @db.Decimal(3,2)
  completedProjects Int     @default(0)
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  user           User                    @relation(fields: [userId], references: [id], onDelete: Cascade)
  skills         FreelancerSkill[]
  proposals      Proposal[]
  contracts      Contract[]              @relation("ContractFreelancer")
  reviews        Review[]                @relation("ReviewFreelancer")
  transfers      AsaasTransfer[]
  
  @@index([cpf])
  @@index([rating])
  @@index([hourlyRate])
  @@map("freelancer_profiles")
}

enum WorkPreference {
  REMOTE
  ONSITE
  HYBRID
  
  @@map("work_preference")
}

enum VerificationStatus {
  PENDING
  APPROVED
  REJECTED
  INCOMPLETE
  
  @@map("verification_status")
}

// ======================
// MÓDULO DE SKILLS
// ======================

model Skill {
  id          String @id @default(uuid()) @db.Uuid
  name        String @unique @db.VarChar(100)
  slug        String @unique @db.VarChar(100)
  description String? @db.Text
  category    String @db.VarChar(50)
  isActive    Boolean @default(true)
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  freelancerSkills FreelancerSkill[]
  projectSkills    ProjectSkill[]
  
  @@index([category])
  @@index([isActive])
  @@map("skills")
}

model FreelancerSkill {
  id           String @id @default(uuid()) @db.Uuid
  freelancerId String @db.Uuid
  skillId      String @db.Uuid
  proficiency  SkillProficiency @default(INTERMEDIATE)
  yearsOfExperience Int @default(0)
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  freelancer FreelancerProfile @relation(fields: [freelancerId], references: [id], onDelete: Cascade)
  skill      Skill             @relation(fields: [skillId], references: [id])
  
  @@unique([freelancerId, skillId])
  @@index([proficiency])
  @@map("freelancer_skills")
}

enum SkillProficiency {
  BEGINNER     // 0-1 ano
  INTERMEDIATE // 1-3 anos
  ADVANCED     // 3-5 anos
  EXPERT       // 5+ anos
  
  @@map("skill_proficiency")
}

// ======================
// MÓDULO DE PROJETOS
// ======================

model Project {
  id        String @id @default(uuid()) @db.Uuid
  companyId String @db.Uuid
  
  // Dados básicos
  title       String @db.VarChar(255)
  description String @db.Text
  
  // Requisitos e especificações
  requirements Json   @db.JsonB // Estrutura rica de requisitos
  attachments  String[] // URLs de arquivos
  
  // Orçamento e prazo
  budgetMin Decimal   @db.Decimal(12,2)
  budgetMax Decimal   @db.Decimal(12,2)
  deadline  DateTime?
  
  // Status e controle
  status       ProjectStatus @default(DRAFT)
  priority     Priority      @default(MEDIUM)
  
  // IA Metrics
  complexityScore  Decimal @default(0) @db.Decimal(3,2) // 0-10
  estimatedHours   Int     @default(0)
  aiConfidence     Decimal @default(0) @db.Decimal(3,2) // 0-1
  
  // Metadados
  tags         String[]
  viewsCount   Int      @default(0)
  
  // Pagamentos
  paymentMethodPreference PaymentMethod @default(PIX)
  
  // Timestamps
  publishedAt DateTime?
  closedAt    DateTime?
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
  
  // Relacionamentos
  company       CompanyProfile  @relation(fields: [companyId], references: [id])
  microservices Microservice[]
  skills        ProjectSkill[]
  contracts     Contract[]
  
  @@index([companyId, status])
  @@index([status, publishedAt])
  @@index([budgetMin, budgetMax])
  @@map("projects")
}

enum ProjectStatus {
  DRAFT        // Em criação
  DECOMPOSING  // IA processando
  PUBLISHED    // Aberto para propostas
  IN_PROGRESS  // Em execução
  COMPLETED    // Finalizado
  CANCELLED    // Cancelado
  
  @@map("project_status")
}

enum Priority {
  LOW
  MEDIUM
  HIGH
  URGENT
  
  @@map("priority")
}

model ProjectSkill {
  id        String @id @default(uuid()) @db.Uuid
  projectId String @db.Uuid
  skillId   String @db.Uuid
  required  Boolean @default(true)
  weight    Decimal @default(1) @db.Decimal(3,2) // Peso da skill (0-1)
  
  // Relacionamentos
  project Project @relation(fields: [projectId], references: [id], onDelete: Cascade)
  skill   Skill   @relation(fields: [skillId], references: [id])
  
  @@unique([projectId, skillId])
  @@map("project_skills")
}

// ======================
// MÓDULO DE MICROSERVIÇOS
// ======================

model Microservice {
  id        String @id @default(uuid()) @db.Uuid
  projectId String @db.Uuid
  
  // Identificação
  title       String @db.VarChar(255)
  description String @db.Text
  
  // Especificações técnicas
  requirements Json @db.JsonB // Requisitos específicos do micro-serviço
  
  // Estimativas
  estimatedHours   Int     @default(0)
  complexityLevel  Int     @default(1) // 1-5
  
  // Dependências
  dependencies    String[] @db.Uuid[] // IDs de outros microserviços
  orderSequence   Int      @default(0)
  
  // Status
  status       MicroserviceStatus @default(OPEN)
  priority     Priority           @default(MEDIUM)
  
  // IA Metrics
  aiConfidence    Decimal @default(0) @db.Decimal(3,2)
  requiredSkills  String[] // Array de skill names
  
  // Preço
  priceRange Json @db.JsonB // { min: number, max: number }
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  project   Project    @relation(fields: [projectId], references: [id], onDelete: Cascade)
  proposals Proposal[]
  
  @@index([projectId, status])
  @@index([status, priority])
  @@index([complexityLevel])
  @@map("microservices")
}

enum MicroserviceStatus {
  OPEN        // Aberto para propostas
  ASSIGNED    // Atribuído a freelancer
  IN_PROGRESS // Em desenvolvimento
  COMPLETED   // Finalizado
  
  @@map("microservice_status")
}

// ======================
// MÓDULO DE PROPOSTAS
// ======================

model Proposal {
  id             String @id @default(uuid()) @db.Uuid
  microserviceId String @db.Uuid
  freelancerId   String @db.Uuid
  
  // Proposta
  proposedPrice    Decimal @db.Decimal(12,2)
  estimatedHours   Int
  deliveryDate     DateTime
  methodology      String  @db.Text
  coverLetter      String  @db.Text
  
  // Portfolio items específicos
  portfolioItems Json[] @db.JsonB // Array de { title, url, description }
  
  // Status e métricas
  status    ProposalStatus @default(SUBMITTED)
  aiScore   Decimal        @default(0) @db.Decimal(3,2) // Score da IA para a proposta
  
  // Timestamps
  submittedAt DateTime  @default(now())
  respondedAt DateTime?
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
  
  // Relacionamentos
  microservice Microservice      @relation(fields: [microserviceId], references: [id])
  freelancer   FreelancerProfile @relation(fields: [freelancerId], references: [id])
  contract     Contract?
  
  @@unique([microserviceId, freelancerId]) // Um freelancer só pode ter uma proposta ativa por microserviço
  @@index([freelancerId, status])
  @@index([status, submittedAt])
  @@map("proposals")
}

enum ProposalStatus {
  SUBMITTED    // Enviada
  UNDER_REVIEW // Em análise
  ACCEPTED     // Aceita
  REJECTED     // Rejeitada
  WITHDRAWN    // Retirada pelo freelancer
  
  @@map("proposal_status")
}

// ======================
// MÓDULO DE CONTRATOS
// ======================

model Contract {
  id             String @id @default(uuid()) @db.Uuid
  proposalId     String @unique @db.Uuid
  companyId      String @db.Uuid
  freelancerId   String @db.Uuid
  microserviceId String @db.Uuid
  
  // Valores
  contractValue Decimal @db.Decimal(12,2)
  
  // Datas
  startDate DateTime
  endDate   DateTime
  
  // Milestones
  milestones Json[] @db.JsonB // Array de { title, description, amount, dueDate, status }
  
  // Termos
  termsConditions String @db.Text
  
  // Status
  status ContractStatus @default(PENDING_SIGNATURE)
  
  // Assinaturas digitais
  companySignedAt    DateTime?
  freelancerSignedAt DateTime?
  signatureHash      String?   @db.VarChar(255) // Hash das assinaturas
  
  // Conclusão
  completedAt DateTime?
  
  // ASAAS integration
  asaasSubscriptionId String? @unique @db.VarChar(255) // Se for recorrente
  
  // Cronograma de pagamentos
  paymentSchedule Json[] @db.JsonB // Array de { amount, dueDate, status, description }
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  proposal   Proposal          @relation(fields: [proposalId], references: [id])
  company    CompanyProfile    @relation(fields: [companyId], references: [id])
  freelancer FreelancerProfile @relation("ContractFreelancer", fields: [freelancerId], references: [id])
  payments   Payment[]
  reviews    Review[]
  
  @@index([companyId, status])
  @@index([freelancerId, status])
  @@index([status, startDate])
  @@map("contracts")
}

enum ContractStatus {
  PENDING_SIGNATURE // Aguardando assinaturas
  ACTIVE           // Ativo
  COMPLETED        // Concluído
  TERMINATED       // Terminado antecipadamente
  DISPUTED         // Em disputa
  
  @@map("contract_status")
}

// ======================
// SISTEMA DE PAGAMENTOS (ASAAS)
// ======================

model AsaasCustomer {
  id       String @id @default(uuid()) @db.Uuid
  userId   String @unique @db.Uuid
  
  // Dados ASAAS
  asaasCustomerId String @unique @db.VarChar(255)
  customerType    AsaasCustomerType
  
  // Dados básicos
  name     String @db.VarChar(255)
  cpfCnpj  String @db.VarChar(18)
  email    String @db.VarChar(255)
  phone    String? @db.VarChar(20)
  
  // Endereço
  address Json? @db.JsonB
  
  // Status
  status            AsaasCustomerStatus @default(ACTIVE)
  createdAtAsaas    DateTime
  lastSyncAt        DateTime            @default(now())
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  user     User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  payments Payment[]
  
  @@index([asaasCustomerId])
  @@index([cpfCnpj])
  @@map("asaas_customers")
}

enum AsaasCustomerType {
  FISICA   // Pessoa física
  JURIDICA // Pessoa jurídica
  
  @@map("asaas_customer_type")
}

enum AsaasCustomerStatus {
  ACTIVE
  INACTIVE
  
  @@map("asaas_customer_status")
}

model Payment {
  id         String @id @default(uuid()) @db.Uuid
  contractId String @db.Uuid
  payerId    String @db.Uuid // Empresa (quem paga)
  payeeId    String @db.Uuid // Freelancer (quem recebe)
  
  // ASAAS Integration
  asaasPaymentId   String  @unique @db.VarChar(255)
  asaasCustomerId  String  @db.Uuid
  
  // Valores
  amount         Decimal @db.Decimal(12,2) // Valor total
  netValue       Decimal @db.Decimal(12,2) // Valor líquido após taxas
  platformFee    Decimal @db.Decimal(12,2) // Taxa da plataforma
  asaasFee       Decimal @db.Decimal(12,2) // Taxa do ASAAS
  
  // Detalhes
  currency               String        @default("BRL") @db.VarChar(3)
  paymentMethod          PaymentMethod
  status                 PaymentStatus
  description            String?       @db.Text
  externalReference      String?       @db.VarChar(255)
  
  // Parcelamento
  installmentCount  Int @default(1)
  installmentNumber Int @default(1)
  
  // Datas
  dueDate          DateTime
  paymentDate      DateTime?
  confirmationDate DateTime?
  
  // Escrow
  escrowReleasedAt DateTime?
  
  // Processamento
  processedAt        DateTime?
  webhookReceivedAt  DateTime?
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  contract      Contract      @relation(fields: [contractId], references: [id])
  payer         User          @relation("PaymentPayer", fields: [payerId], references: [id])
  payee         User          @relation("PaymentPayee", fields: [payeeId], references: [id])
  asaasCustomer AsaasCustomer @relation(fields: [asaasCustomerId], references: [id])
  refunds       PaymentRefund[]
  transfers     AsaasTransfer[]
  
  @@index([asaasPaymentId])
  @@index([contractId, status])
  @@index([payerId, status])
  @@index([status, dueDate])
  @@map("payments")
}

enum PaymentMethod {
  PIX
  BOLETO
  CREDIT_CARD
  DEBIT_CARD
  BANK_TRANSFER
  
  @@map("payment_method")
}

enum PaymentStatus {
  PENDING                         // Aguardando pagamento
  CONFIRMED                       // Pagamento confirmado
  RECEIVED                        // Pagamento recebido
  OVERDUE                         // Vencido
  REFUNDED                        // Estornado
  RECEIVED_IN_CASH               // Recebido em dinheiro
  REFUND_REQUESTED               // Estorno solicitado
  REFUND_IN_PROGRESS             // Estorno em andamento
  CHARGEBACK_REQUESTED           // Chargeback solicitado
  CHARGEBACK_DISPUTE             // Disputa de chargeback
  AWAITING_CHARGEBACK_REVERSAL   // Aguardando reversão
  
  @@map("payment_status")
}

model PaymentRefund {
  id        String @id @default(uuid()) @db.Uuid
  paymentId String @db.Uuid
  
  // ASAAS Integration
  asaasRefundId String @unique @db.VarChar(255)
  
  // Valores
  amount      Decimal @db.Decimal(12,2)
  description String? @db.Text
  
  // Status
  status PaymentRefundStatus
  
  // Datas
  requestedAt  DateTime @default(now())
  processedAt  DateTime?
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  payment Payment @relation(fields: [paymentId], references: [id])
  
  @@index([paymentId])
  @@map("payment_refunds")
}

enum PaymentRefundStatus {
  PENDING
  DONE
  CANCELLED
  
  @@map("payment_refund_status")
}

model AsaasTransfer {
  id           String @id @default(uuid()) @db.Uuid
  paymentId    String @db.Uuid
  freelancerId String @db.Uuid
  
  // ASAAS Integration
  asaasTransferId String @unique @db.VarChar(255)
  
  // Valores
  amount       Decimal @db.Decimal(12,2)
  netValue     Decimal @db.Decimal(12,2)
  transferFee  Decimal @db.Decimal(12,2)
  
  // Método
  transferMethod AsaasTransferMethod
  
  // Status
  status AsaasTransferStatus
  
  // Dados bancários
  bankAccount Json? @db.JsonB // Dados da conta destino
  pixKey      String? @db.VarChar(255) // Chave PIX criptografada
  
  // Datas
  scheduledDate DateTime
  effectiveDate DateTime?
  
  // Descrição e falha
  description   String? @db.Text
  failureReason String? @db.Text
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  payment    Payment           @relation(fields: [paymentId], references: [id])
  freelancer FreelancerProfile @relation(fields: [freelancerId], references: [id])
  
  @@index([freelancerId, status])
  @@index([scheduledDate, status])
  @@map("asaas_transfers")
}

enum AsaasTransferMethod {
  PIX
  TED
  DOC
  
  @@map("asaas_transfer_method")
}

enum AsaasTransferStatus {
  PENDING
  DONE
  CANCELLED
  FAILED
  
  @@map("asaas_transfer_status")
}

model AsaasWebhook {
  id      String @id @default(uuid()) @db.Uuid
  
  // ASAAS Event Data
  asaasEventId String @unique @db.VarChar(255)
  eventType    String @db.VarChar(100)
  objectType   String @db.VarChar(50)
  objectId     String @db.VarChar(255)
  
  // Payload
  payload Json @db.JsonB // Payload completo do webhook
  
  // Processing
  processed    Boolean   @default(false)
  processedAt  DateTime?
  errorMessage String?   @db.Text
  retryCount   Int       @default(0)
  
  // Timestamps
  receivedAt DateTime @default(now())
  createdAt  DateTime @default(now())
  
  @@index([processed, receivedAt])
  @@index([eventType])
  @@map("asaas_webhooks")
}

// ======================
// SISTEMA DE AVALIAÇÕES
// ======================

model Review {
  id         String @id @default(uuid()) @db.Uuid
  contractId String @db.Uuid
  reviewerId String @db.Uuid // Quem está avaliando
  
  // Avaliação
  rating      Decimal @db.Decimal(2,1) // 1.0 a 5.0
  title       String? @db.VarChar(255)
  comment     String? @db.Text
  
  // Tipo de avaliação
  type ReviewType
  
  // Categorias específicas (1-5)
  communicationRating Int?
  qualityRating       Int?
  timelinessRating    Int?
  professionalismRating Int?
  
  // Status
  isPublic  Boolean @default(true)
  isActive  Boolean @default(true)
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  contract   Contract @relation(fields: [contractId], references: [id])
  reviewer   User     @relation(fields: [reviewerId], references: [id])
  freelancer FreelancerProfile? @relation("ReviewFreelancer", fields: [freelancerId], references: [id])
  
  freelancerId String? @db.Uuid // Para indexação de reviews do freelancer
  
  @@unique([contractId, reviewerId]) // Uma review por usuário por contrato
  @@index([freelancerId, rating])
  @@index([rating, createdAt])
  @@map("reviews")
}

enum ReviewType {
  COMPANY_TO_FREELANCER
  FREELANCER_TO_COMPANY
  
  @@map("review_type")
}

// ======================
// SISTEMA DE COMUNICAÇÃO
// ======================

model Conversation {
  id           String @id @default(uuid()) @db.Uuid
  projectId    String? @db.Uuid // Conversa relacionada a um projeto
  contractId   String? @db.Uuid // Conversa relacionada a um contrato
  
  // Participantes
  participants String[] @db.Uuid[] // IDs dos usuários
  
  // Metadata
  title       String? @db.VarChar(255)
  isGroup     Boolean @default(false)
  isActive    Boolean @default(true)
  
  // Última atividade
  lastMessageAt DateTime @default(now())
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  messages Message[]
  
  @@index([participants])
  @@index([lastMessageAt])
  @@map("conversations")
}

model Message {
  id             String @id @default(uuid()) @db.Uuid
  conversationId String @db.Uuid
  senderId       String @db.Uuid
  recipientId    String? @db.Uuid // Para mensagens diretas
  
  // Conteúdo
  content     String @db.Text
  messageType MessageType @default(TEXT)
  attachments String[] // URLs de arquivos
  
  // Metadata
  isEdited   Boolean @default(false)
  editedAt   DateTime?
  
  // Leitura
  readBy     String[] @db.Uuid[] // IDs dos usuários que leram
  readAt     DateTime?
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  conversation Conversation @relation(fields: [conversationId], references: [id], onDelete: Cascade)
  sender       User         @relation("MessageSender", fields: [senderId], references: [id])
  recipient    User?        @relation("MessageReceiver", fields: [recipientId], references: [id])
  
  @@index([conversationId, createdAt])
  @@index([senderId])
  @@map("messages")
}

enum MessageType {
  TEXT
  FILE
  IMAGE
  SYSTEM // Mensagens do sistema
  
  @@map("message_type")
}

// ======================
// SISTEMA DE NOTIFICAÇÕES
// ======================

model Notification {
  id     String @id @default(uuid()) @db.Uuid
  userId String @db.Uuid
  
  // Conteúdo
  title   String @db.VarChar(255)
  message String @db.Text
  type    NotificationType
  
  // Metadata
  data Json? @db.JsonB // Dados específicos da notificação
  
  // Links
  actionUrl String? @db.VarChar(500) // URL para ação
  
  // Status
  isRead     Boolean   @default(false)
  readAt     DateTime?
  isArchived Boolean   @default(false)
  
  // Entrega
  channels   NotificationChannel[] // Canais de entrega
  sentAt     DateTime?
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  // Relacionamentos
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  @@index([userId, isRead])
  @@index([type, createdAt])
  @@map("notifications")
}

enum NotificationType {
  PROJECT_CREATED
  PROJECT_UPDATED
  PROPOSAL_RECEIVED
  PROPOSAL_ACCEPTED
  PROPOSAL_REJECTED
  PAYMENT_RECEIVED
  PAYMENT_OVERDUE
  CONTRACT_SIGNED
  CONTRACT_COMPLETED
  MESSAGE_RECEIVED
  REVIEW_RECEIVED
  SYSTEM_ANNOUNCEMENT
  
  @@map("notification_type")
}

enum NotificationChannel {
  IN_APP    // Notificação no app
  EMAIL     // E-mail
  PUSH      // Push notification
  SMS       // SMS (futuro)
  WEBHOOK   // Webhook (futuro)
  
  @@map("notification_channel")
}

// ======================
// SISTEMA DE AUDITORIA
// ======================

model AuditLog {
  id     String @id @default(uuid()) @db.Uuid
  userId String? @db.Uuid // Pode ser nulo para ações do sistema
  
  // Ação
  action       String @db.VarChar(100)
  resourceType String @db.VarChar(50)
  resourceId   String @db.Uuid
  
  // Dados
  oldValues Json? @db.JsonB // Valores anteriores
  newValues Json? @db.JsonB // Novos valores
  
  // Context
  ipAddress String? @db.Inet
  userAgent String? @db.Text
  sessionId String? @db.Uuid
  
  // Financeiro
  isFinancialOperation Boolean @default(false)
  amount               Decimal? @db.Decimal(12,2)
  asaasReference       String? @db.VarChar(255)
  
  // Timestamp
  timestamp DateTime @default(now())
  
  // Relacionamentos
  user User? @relation(fields: [userId], references: [id])
  
  @@index([userId, timestamp])
  @@index([resourceType, resourceId])
  @@index([isFinancialOperation, timestamp])
  @@map("audit_logs")
}

// ======================
// SISTEMA RBAC
// ======================

model Role {
  id          String @id @default(uuid()) @db.Uuid
  name        String @unique @db.VarChar(50)
  description String @db.Text
  level       Int    @default(1) // Nível hierárquico
  
  // Tipo
  isSystemRole Boolean @default(false) // Role do sistema
  
  // Permissões
  permissions         String[] // Array de permissões
  financialPermissions String[] // Permissões financeiras específicas
  
  // Timestamps
  createdAt DateTime @default(now())
  
  // Relacionamentos
  userRoles UserRole[]
  
  @@index([level])
  @@map("roles")
}

model UserRole {
  id      String @id @default(uuid()) @db.Uuid
  userId  String @db.Uuid
  roleId  String @db.Uuid
  
  // Concessão
  grantedBy String   @db.Uuid // Quem concedeu
  grantedAt DateTime @default(now())
  
  // Expiração
  expiresAt DateTime?
  isActive  Boolean   @default(true)
  
  // Contexto
  context Json? @db.JsonB // Contexto específico (empresa, projeto)
  
  // Relacionamentos
  user    User @relation(fields: [userId], references: [id], onDelete: Cascade)
  role    Role @relation(fields: [roleId], references: [id])
  
  @@unique([userId, roleId]) // Um usuário pode ter cada role apenas uma vez
  @@index([userId, isActive])
  @@map("user_roles")
}

// ======================
// CONFIGURAÇÕES SISTEMA
// ======================

model SystemConfig {
  id    String @id @default(uuid()) @db.Uuid
  key   String @unique @db.VarChar(100)
  value Json   @db.JsonB
  
  // Metadata
  description String?  @db.Text
  isSecret    Boolean  @default(false)
  environment String   @default("production") @db.VarChar(20)
  
  // Timestamps
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  @@index([environment])
  @@map("system_configs")
}
```

## 🔍 ÍNDICES E OTIMIZAÇÕES

### Índices Estratégicos
```sql
-- Índices de performance crítica
CREATE INDEX CONCURRENTLY idx_projects_search ON projects 
USING GIN (to_tsvector('portuguese', title || ' ' || description));

CREATE INDEX CONCURRENTLY idx_microservices_skills ON microservices 
USING GIN (required_skills);

CREATE INDEX CONCURRENTLY idx_freelancer_skills_search ON freelancer_skills (skill_id, proficiency)
WHERE proficiency IN ('ADVANCED', 'EXPERT');

-- Índices compostos para queries frequentes
CREATE INDEX CONCURRENTLY idx_payments_contract_status ON payments (contract_id, status, due_date);
CREATE INDEX CONCURRENTLY idx_proposals_freelancer_status ON proposals (freelancer_id, status, submitted_at DESC);
CREATE INDEX CONCURRENTLY idx_audit_logs_resource ON audit_logs (resource_type, resource_id, timestamp DESC);

-- Índices para relatórios financeiros
CREATE INDEX CONCURRENTLY idx_payments_financial_reports ON payments 
(status, payment_date, amount) 
WHERE status IN ('RECEIVED', 'CONFIRMED');

-- Índices parciais para dados ativos
CREATE INDEX CONCURRENTLY idx_users_active ON users (email, created_at) 
WHERE is_active = true;

CREATE INDEX CONCURRENTLY idx_projects_published ON projects (published_at DESC, budget_max) 
WHERE status = 'PUBLISHED';
```

### Particionamento
```sql
-- Particionamento de tabelas por data
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs 
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit_logs_2024_02 PARTITION OF audit_logs 
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Particionamento por hash para distribuição
CREATE TABLE messages_hash_0 PARTITION OF messages 
FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE messages_hash_1 PARTITION OF messages 
FOR VALUES WITH (MODULUS 4, REMAINDER 1);
```

### Row Level Security (RLS)
```sql
-- Habilitar RLS em tabelas sensíveis
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Políticas de segurança
CREATE POLICY company_projects_policy ON projects
FOR ALL TO application_role
USING (
  company_id = current_setting('app.current_company_id')::uuid
  OR current_setting('app.user_role') = 'ADMIN'
);

CREATE POLICY freelancer_proposals_policy ON proposals
FOR ALL TO application_role
USING (
  freelancer_id = current_setting('app.current_freelancer_id')::uuid
  OR EXISTS (
    SELECT 1 FROM microservices m 
    JOIN projects p ON m.project_id = p.id
    WHERE m.id = proposals.microservice_id 
    AND p.company_id = current_setting('app.current_company_id')::uuid
  )
);

CREATE POLICY payment_access_policy ON payments
FOR SELECT TO application_role
USING (
  payer_id = current_setting('app.current_user_id')::uuid
  OR payee_id = current_setting('app.current_user_id')::uuid
  OR current_setting('app.user_role') IN ('ADMIN', 'FINANCIAL_ADMIN')
);
```

## 🔐 SEGURANÇA E CRIPTOGRAFIA

### Criptografia de Dados Sensíveis
```sql
-- Extensão para criptografia
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Função para criptografar dados sensíveis
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT)
RETURNS TEXT AS $$
BEGIN
  RETURN pgp_sym_encrypt(data, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Função para descriptografar dados
CREATE OR REPLACE FUNCTION decrypt_sensitive_data(encrypted_data TEXT)
RETURNS TEXT AS $$
BEGIN
  RETURN pgp_sym_decrypt(encrypted_data, current_setting('app.encryption_key'));
EXCEPTION
  WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Triggers para criptografia automática
CREATE OR REPLACE FUNCTION encrypt_freelancer_bank_data()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.bank_details IS NOT NULL THEN
    NEW.bank_details = encrypt_sensitive_data(NEW.bank_details);
  END IF;
  
  IF NEW.pix_key IS NOT NULL THEN
    NEW.pix_key = encrypt_sensitive_data(NEW.pix_key);
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER encrypt_freelancer_data_trigger
BEFORE INSERT OR UPDATE ON freelancer_profiles
FOR EACH ROW EXECUTE FUNCTION encrypt_freelancer_bank_data();
```

### Auditoria Automática
```sql
-- Função genérica de auditoria
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO audit_logs (
    user_id,
    action,
    resource_type,
    resource_id,
    old_values,
    new_values,
    ip_address,
    session_id,
    timestamp
  ) VALUES (
    NULLIF(current_setting('app.current_user_id', true), '')::uuid,
    TG_OP,
    TG_TABLE_NAME,
    COALESCE(NEW.id, OLD.id),
    CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE NULL END,
    CASE WHEN TG_OP = 'INSERT' THEN to_jsonb(NEW)
         WHEN TG_OP = 'UPDATE' THEN to_jsonb(NEW)
         ELSE NULL END,
    NULLIF(current_setting('app.client_ip', true), '')::inet,
    NULLIF(current_setting('app.session_id', true), '')::uuid,
    NOW()
  );
  
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Aplicar auditoria em tabelas críticas
CREATE TRIGGER audit_projects_trigger
AFTER INSERT OR UPDATE OR DELETE ON projects
FOR EACH ROW EXECUTE FUNCTION audit_trigger();

CREATE TRIGGER audit_contracts_trigger
AFTER INSERT OR UPDATE OR DELETE ON contracts
FOR EACH ROW EXECUTE FUNCTION audit_trigger();

CREATE TRIGGER audit_payments_trigger
AFTER INSERT OR UPDATE OR DELETE ON payments
FOR EACH ROW EXECUTE FUNCTION audit_trigger();
```

## 📊 VIEWS E RELATÓRIOS

### Views Materializadas para Performance
```sql
-- View de estatísticas de freelancers
CREATE MATERIALIZED VIEW freelancer_stats AS
SELECT 
  fp.id,
  fp.user_id,
  fp.full_name,
  fp.rating,
  fp.completed_projects,
  COUNT(DISTINCT p.id) as active_proposals,
  COUNT(DISTINCT c.id) as active_contracts,
  COALESCE(AVG(r.rating), 0) as avg_rating,
  COUNT(DISTINCT r.id) as total_reviews,
  SUM(CASE WHEN py.status = 'RECEIVED' THEN py.net_value ELSE 0 END) as total_earnings
FROM freelancer_profiles fp
LEFT JOIN proposals p ON fp.id = p.freelancer_id AND p.status = 'SUBMITTED'
LEFT JOIN contracts c ON fp.id = c.freelancer_id AND c.status = 'ACTIVE'
LEFT JOIN reviews r ON fp.id = r.freelancer_id AND r.is_active = true
LEFT JOIN payments py ON fp.user_id = py.payee_id
GROUP BY fp.id, fp.user_id, fp.full_name, fp.rating, fp.completed_projects;

-- Index na view materializada
CREATE UNIQUE INDEX idx_freelancer_stats_id ON freelancer_stats (id);
CREATE INDEX idx_freelancer_stats_rating ON freelancer_stats (rating DESC);

-- Refresh automático da view
CREATE OR REPLACE FUNCTION refresh_freelancer_stats()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY freelancer_stats;
END;
$$ LANGUAGE plpgsql;

-- View de projetos com estatísticas
CREATE MATERIALIZED VIEW project_stats AS
SELECT 
  p.id,
  p.title,
  p.company_id,
  p.status,
  p.budget_min,
  p.budget_max,
  p.created_at,
  p.published_at,
  COUNT(DISTINCT m.id) as microservices_count,
  COUNT(DISTINCT pr.id) as proposals_count,
  COUNT(DISTINCT c.id) as contracts_count,
  COALESCE(AVG(pr.proposed_price), 0) as avg_proposal_price,
  COUNT(DISTINCT pr.freelancer_id) as unique_freelancers
FROM projects p
LEFT JOIN microservices m ON p.id = m.project_id
LEFT JOIN proposals pr ON m.id = pr.microservice_id
LEFT JOIN contracts c ON p.id = c.project_id
GROUP BY p.id, p.title, p.company_id, p.status, p.budget_min, p.budget_max, p.created_at, p.published_at;

CREATE UNIQUE INDEX idx_project_stats_id ON project_stats (id);
CREATE INDEX idx_project_stats_company ON project_stats (company_id, status);
```

### Views para Relatórios Financeiros
```sql
-- Relatório financeiro consolidado
CREATE VIEW financial_dashboard AS
SELECT 
  DATE_TRUNC('month', p.payment_date) as month,
  SUM(p.amount) as gross_revenue,
  SUM(p.platform_fee) as platform_revenue,
  SUM(p.net_value) as freelancer_payments,
  COUNT(DISTINCT p.id) as transactions_count,
  COUNT(DISTINCT p.payer_id) as active_companies,
  COUNT(DISTINCT p.payee_id) as active_freelancers,
  AVG(p.amount) as avg_transaction_value
FROM payments p
WHERE p.status = 'RECEIVED'
  AND p.payment_date >= DATE_TRUNC('year', CURRENT_DATE)
GROUP BY DATE_TRUNC('month', p.payment_date)
ORDER BY month;

-- Performance por freelancer
CREATE VIEW freelancer_performance AS
SELECT 
  fp.id as freelancer_id,
  fp.full_name,
  COUNT(DISTINCT c.id) as completed_contracts,
  SUM(py.net_value) as total_earnings,
  AVG(py.net_value) as avg_contract_value,
  AVG(EXTRACT(days FROM (c.completed_at - c.start_date))) as avg_completion_days,
  AVG(r.rating) as avg_rating,
  COUNT(DISTINCT r.id) as total_reviews
FROM freelancer_profiles fp
JOIN contracts c ON fp.id = c.freelancer_id AND c.status = 'COMPLETED'
JOIN payments py ON c.id = py.contract_id AND py.status = 'RECEIVED'
LEFT JOIN reviews r ON fp.id = r.freelancer_id AND r.is_active = true
GROUP BY fp.id, fp.full_name
HAVING COUNT(DISTINCT c.id) > 0
ORDER BY total_earnings DESC;
```

## 🔄 MIGRATIONS E SEEDS

### Migration Strategy
```typescript
// Migration para criar tabelas base
-- migrations/001_create_users_table.sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  type user_type DEFAULT 'FREELANCER',
  email_verified BOOLEAN DEFAULT FALSE,
  email_verified_at TIMESTAMP,
  email_verify_token VARCHAR(255) UNIQUE,
  two_factor_enabled BOOLEAN DEFAULT FALSE,
  two_factor_secret VARCHAR(32),
  is_active BOOLEAN DEFAULT TRUE,
  last_login_at TIMESTAMP,
  login_attempts INTEGER DEFAULT 0,
  locked_until TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Triggers para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- migrations/002_create_indexes.sql
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);
CREATE INDEX CONCURRENTLY idx_users_type_active ON users (type, is_active);
CREATE INDEX CONCURRENTLY idx_users_created_at ON users (created_at);
```

### Seed Data
```typescript
// seeds/001_initial_data.sql
-- Inserir skills básicas
INSERT INTO skills (id, name, slug, description, category, created_at) VALUES
  (gen_random_uuid(), 'JavaScript', 'javascript', 'Linguagem de programação JavaScript', 'Programming', NOW()),
  (gen_random_uuid(), 'TypeScript', 'typescript', 'TypeScript para desenvolvimento tipado', 'Programming', NOW()),
  (gen_random_uuid(), 'React', 'react', 'Biblioteca React para UI', 'Frontend', NOW()),
  (gen_random_uuid(), 'Node.js', 'nodejs', 'Runtime JavaScript para backend', 'Backend', NOW()),
  (gen_random_uuid(), 'PostgreSQL', 'postgresql', 'Banco de dados relacional', 'Database', NOW()),
  (gen_random_uuid(), 'UI/UX Design', 'ui-ux-design', 'Design de interface e experiência do usuário', 'Design', NOW());

-- Inserir configurações do sistema
INSERT INTO system_configs (id, key, value, description, environment, created_at) VALUES
  (gen_random_uuid(), 'platform_fee_percentage', '5.0', 'Percentual de taxa da plataforma', 'production', NOW()),
  (gen_random_uuid(), 'min_project_budget', '1000.0', 'Orçamento mínimo para projetos', 'production', NOW()),
  (gen_random_uuid(), 'max_proposals_per_microservice', '20', 'Máximo de propostas por microserviço', 'production', NOW());

-- Inserir roles do sistema
INSERT INTO roles (id, name, description, level, is_system_role, permissions, created_at) VALUES
  (gen_random_uuid(), 'SUPER_ADMIN', 'Administrador supremo da plataforma', 10, true, 
   ARRAY['*'], NOW()),
  (gen_random_uuid(), 'PLATFORM_ADMIN', 'Administrador da plataforma', 8, true,
   ARRAY['users:*', 'projects:*', 'reports:*'], NOW()),
  (gen_random_uuid(), 'FINANCIAL_ADMIN', 'Administrador financeiro', 7, true,
   ARRAY['payments:*', 'transfers:*', 'reports:financial'], NOW()),
  (gen_random_uuid(), 'COMPANY_USER', 'Usuário de empresa', 3, true,
   ARRAY['projects:crud', 'proposals:read', 'contracts:read'], NOW()),
  (gen_random_uuid(), 'FREELANCER', 'Freelancer da plataforma', 2, true,
   ARRAY['proposals:crud', 'contracts:read', 'profile:crud'], NOW());
```

## 📈 MONITORING E MAINTENANCE

### Monitoring Queries
```sql
-- Query para monitorar performance
SELECT 
  schemaname,
  tablename,
  attname,
  n_distinct,
  correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename IN ('users', 'projects', 'payments')
ORDER BY tablename, attname;

-- Monitorar tamanho das tabelas
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
  pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Queries mais lentas
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_time DESC
LIMIT 10;
```

### Maintenance Tasks
```sql
-- Limpeza automática de dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
  -- Limpar tokens de verificação expirados
  DELETE FROM users 
  WHERE email_verify_token IS NOT NULL 
    AND created_at < NOW() - INTERVAL '24 hours'
    AND email_verified = FALSE;
    
  -- Limpar sessões expiradas
  DELETE FROM user_sessions 
  WHERE expires_at < NOW() - INTERVAL '7 days';
  
  -- Limpar webhooks processados antigos
  DELETE FROM asaas_webhooks 
  WHERE processed = TRUE 
    AND received_at < NOW() - INTERVAL '30 days';
    
  -- Limpar logs de auditoria antigos (manter por 2 anos)
  DELETE FROM audit_logs 
  WHERE timestamp < NOW() - INTERVAL '2 years'
    AND is_financial_operation = FALSE;
    
  -- Arquivar notificações antigas
  UPDATE notifications 
  SET is_archived = TRUE 
  WHERE created_at < NOW() - INTERVAL '90 days'
    AND is_read = TRUE;
END;
$$ LANGUAGE plpgsql;

-- Agendar limpeza diária
SELECT cron.schedule('cleanup-old-data', '0 2 * * *', 'SELECT cleanup_old_data();');
```

## 🎯 PERFORMANCE TARGETS

### Métricas de Performance
- **Connection Pool**: Max 100 conexões simultâneas
- **Query Response Time**: < 100ms para 95% das queries
- **Index Usage**: > 95% das queries usando índices
- **Vacuum Performance**: VACUUM completo semanal
- **Replication Lag**: < 1 segundo

### Backup Strategy
- **Full Backup**: Diário às 02:00
- **WAL Archiving**: Contínuo
- **Point-in-time Recovery**: 30 dias
- **Cross-region Backup**: Semanal
- **Restore Testing**: Mensal

## 🔧 DOCKER E CONFIGURAÇÃO

### Docker Compose para Desenvolvimento
```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:17.5-alpine
    environment:
      POSTGRES_USER: demandei
      POSTGRES_PASSWORD: development
      POSTGRES_DB: demandei_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_statements
      -c pg_stat_statements.track=all
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c work_mem=4MB

  redis:
    image: redis:8.0-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb

  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@demandei.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "8080:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin

volumes:
  postgres_data:
  redis_data:
  pgadmin_data:
```

### Configuração PostgreSQL Otimizada
```ini
# postgresql.conf para produção
# Memory Configuration
shared_buffers = 2GB                    # 25% da RAM
effective_cache_size = 6GB              # 75% da RAM  
work_mem = 16MB                         # Para queries complexas
maintenance_work_mem = 512MB            # Para VACUUM, CREATE INDEX

# Checkpoint Configuration
checkpoint_completion_target = 0.9
wal_buffers = 16MB
max_wal_size = 4GB
min_wal_size = 1GB

# Connection Configuration
max_connections = 200
shared_preload_libraries = 'pg_stat_statements'

# Logging Configuration
log_destination = 'csvlog'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_statement = 'ddl'
log_min_duration_statement = 100
log_checkpoints = on
log_lock_waits = on

# Performance Monitoring
pg_stat_statements.track = all
pg_stat_statements.max = 10000
track_activity_query_size = 2048
```

Este schema completo fornece uma base sólida e escalável para a Demandei, com:

### ✅ **Características Principais**
- **Modelagem Robusta**: Relações bem definidas, integridade referencial
- **Segurança Avançada**: RLS, criptografia, auditoria completa
- **Performance Otimizada**: Índices estratégicos, particionamento, views materializadas
- **Integração ASAAS**: Schema específico para pagamentos brasileiros
- **Compliance**: LGPD, auditoria financeira, retenção de dados
- **Escalabilidade**: Preparado para crescimento, particionamento automático
- **Monitoring**: Queries de monitoramento, cleanup automático
- **Backup/Recovery**: Estratégia completa de backup e recuperação

### ✅ **Benefícios Técnicos**
- **ACID Compliance**: Transações seguras para operações críticas
- **Multi-tenant**: Isolamento de dados por empresa
- **Full-text Search**: Busca avançada em português
- **Temporal Data**: Histórico completo de mudanças
- **Performance**: < 100ms para 95% das queries
- **Segurança**: Criptografia AES-256, RLS, auditoria

Este banco de dados está pronto para suportar todos os requisitos da plataforma Demandei desde o MVP até uma solução enterprise completa.