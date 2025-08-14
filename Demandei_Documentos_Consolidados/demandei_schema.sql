-- ============================================
-- DEMANDEI DATABASE SCHEMA FOR POSTGRESQL 17
-- ============================================
-- Complete database structure with ASAAS payment integration
-- Author: Demandei Platform
-- Version: 1.0.0
-- Last Updated: 2025-08-02
-- ============================================
-- IMPORTANT: This script uses PostgreSQL-specific features:
-- 1. CREATE EXTENSION (for uuid-ossp, pgcrypto, etc.)
-- 2. CREATE TYPE ... AS ENUM (for custom enum types)
-- 3. UUID data type and uuid_generate_v4() function
-- 4. JSONB data type
-- 5. Array types (UUID[], TEXT[])
-- 6. Row Level Security (RLS)
-- 7. Partitioned tables
-- 
-- This script MUST be run directly in PostgreSQL.
-- Generic SQL parsers will report syntax errors.
-- ============================================

-- ============================================
-- 1. DATABASE CONFIGURATION
-- ============================================

-- Drop database if exists (careful in production!)
-- DROP DATABASE IF EXISTS demandei;
-- CREATE DATABASE demandei
--     WITH 
--     OWNER = postgres
--     ENCODING = 'UTF8'
--     LC_COLLATE = 'en_US.UTF-8'
--     LC_CTYPE = 'en_US.UTF-8'
--     TABLESPACE = pg_default
--     CONNECTION LIMIT = -1;

-- Connect to database
-- \c demandei;

-- ============================================
-- 2. EXTENSIONS
-- ============================================
-- NOTE: CREATE EXTENSION is PostgreSQL-specific syntax.
-- If you're using a SQL parser that doesn't support it,
-- these extensions must be installed separately in PostgreSQL.

-- UUID generation (REQUIRED for uuid_generate_v4() function)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Trigram similarity for fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Full text search
CREATE EXTENSION IF NOT EXISTS unaccent;

-- JSONB indexing
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- ============================================
-- 3. CUSTOM TYPES (ENUMS)
-- ============================================

-- Drop existing types if they exist (careful in production!)
-- Uncomment these lines if running in PostgreSQL and types already exist
-- DROP TYPE IF EXISTS user_status CASCADE;
-- DROP TYPE IF EXISTS user_type CASCADE;
-- DROP TYPE IF EXISTS project_status CASCADE;
-- DROP TYPE IF EXISTS project_priority CASCADE;
-- DROP TYPE IF EXISTS proposal_status CASCADE;
-- DROP TYPE IF EXISTS contract_status CASCADE;
-- DROP TYPE IF EXISTS payment_status CASCADE;
-- DROP TYPE IF EXISTS payment_method CASCADE;
-- DROP TYPE IF EXISTS asaas_customer_type CASCADE;
-- DROP TYPE IF EXISTS asaas_transfer_status CASCADE;
-- DROP TYPE IF EXISTS asaas_webhook_status CASCADE;
-- DROP TYPE IF EXISTS work_preference CASCADE;
-- DROP TYPE IF EXISTS company_size CASCADE;
-- DROP TYPE IF EXISTS verification_status CASCADE;

-- User related enums
CREATE TYPE user_status AS ENUM (
    'active',
    'inactive',
    'suspended',
    'pending_verification',
    'deleted'
);

CREATE TYPE user_type AS ENUM (
    'company',
    'freelancer',
    'both',
    'admin'
);

-- Project related enums
CREATE TYPE project_status AS ENUM (
    'draft',
    'published',
    'in_progress',
    'completed',
    'cancelled',
    'disputed'
);

CREATE TYPE project_priority AS ENUM (
    'low',
    'medium',
    'high',
    'urgent'
);

-- Proposal related enums
CREATE TYPE proposal_status AS ENUM (
    'submitted',
    'under_review',
    'accepted',
    'rejected',
    'withdrawn'
);

-- Contract related enums
CREATE TYPE contract_status AS ENUM (
    'draft',
    'pending_signatures',
    'active',
    'completed',
    'terminated',
    'disputed'
);

-- Payment related enums
CREATE TYPE payment_status AS ENUM (
    'pending',
    'processing',
    'confirmed',
    'received',
    'failed',
    'refunded',
    'cancelled',
    'overdue',
    'chargeback'
);

CREATE TYPE payment_method AS ENUM (
    'pix',
    'boleto',
    'credit_card',
    'debit_card',
    'bank_transfer'
);

-- ASAAS specific enums
CREATE TYPE asaas_customer_type AS ENUM (
    'FISICA',
    'JURIDICA'
);

CREATE TYPE asaas_transfer_status AS ENUM (
    'pending',
    'done',
    'cancelled',
    'failed'
);

CREATE TYPE asaas_webhook_status AS ENUM (
    'received',
    'processing',
    'processed',
    'failed',
    'ignored'
);

-- Work preference enum
CREATE TYPE work_preference AS ENUM (
    'remote',
    'onsite',
    'hybrid'
);

-- Company size enum
CREATE TYPE company_size AS ENUM (
    'micro',
    'small',
    'medium',
    'large',
    'enterprise'
);

-- Verification status enum
CREATE TYPE verification_status AS ENUM (
    'unverified',
    'pending',
    'verified',
    'rejected'
);

-- ============================================
-- 4. SEQUENCES
-- ============================================

CREATE SEQUENCE IF NOT EXISTS contract_number_seq;
CREATE SEQUENCE IF NOT EXISTS incident_id_seq;
CREATE SEQUENCE IF NOT EXISTS lgpd_request_number_seq;

-- ============================================
-- 5. VALIDATION FUNCTIONS (needed before tables)
-- ============================================

-- Function to validate CPF
CREATE OR REPLACE FUNCTION validate_cpf(cpf TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    digits INTEGER[];
    sum1 INTEGER := 0;
    sum2 INTEGER := 0;
    i INTEGER;
BEGIN
    -- Remove non-numeric characters
    cpf := regexp_replace(cpf, '[^0-9]', '', 'g');
    
    -- Check length
    IF length(cpf) != 11 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if all digits are the same
    IF cpf ~ '^(.)\1{10}$' THEN
        RETURN FALSE;
    END IF;
    
    -- Convert to array of integers
    FOR i IN 1..11 LOOP
        digits[i] := substring(cpf, i, 1)::INTEGER;
    END LOOP;
    
    -- Calculate first check digit
    FOR i IN 1..9 LOOP
        sum1 := sum1 + digits[i] * (11 - i);
    END LOOP;
    
    sum1 := 11 - (sum1 % 11);
    IF sum1 >= 10 THEN
        sum1 := 0;
    END IF;
    
    IF sum1 != digits[10] THEN
        RETURN FALSE;
    END IF;
    
    -- Calculate second check digit
    FOR i IN 1..10 LOOP
        sum2 := sum2 + digits[i] * (12 - i);
    END LOOP;
    
    sum2 := 11 - (sum2 % 11);
    IF sum2 >= 10 THEN
        sum2 := 0;
    END IF;
    
    RETURN sum2 = digits[11];
END;
$$ language 'plpgsql';

-- Function to validate CNPJ
CREATE OR REPLACE FUNCTION validate_cnpj(cnpj TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    digits INTEGER[];
    sum1 INTEGER := 0;
    sum2 INTEGER := 0;
    i INTEGER;
    weights1 INTEGER[] := ARRAY[5,4,3,2,9,8,7,6,5,4,3,2];
    weights2 INTEGER[] := ARRAY[6,5,4,3,2,9,8,7,6,5,4,3,2];
BEGIN
    -- Remove non-numeric characters
    cnpj := regexp_replace(cnpj, '[^0-9]', '', 'g');
    
    -- Check length
    IF length(cnpj) != 14 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if all digits are the same
    IF cnpj ~ '^(.)\1{13}$' THEN
        RETURN FALSE;
    END IF;
    
    -- Convert to array of integers
    FOR i IN 1..14 LOOP
        digits[i] := substring(cnpj, i, 1)::INTEGER;
    END LOOP;
    
    -- Calculate first check digit
    FOR i IN 1..12 LOOP
        sum1 := sum1 + digits[i] * weights1[i];
    END LOOP;
    
    sum1 := 11 - (sum1 % 11);
    IF sum1 >= 10 THEN
        sum1 := 0;
    END IF;
    
    IF sum1 != digits[13] THEN
        RETURN FALSE;
    END IF;
    
    -- Calculate second check digit
    FOR i IN 1..13 LOOP
        sum2 := sum2 + digits[i] * weights2[i];
    END LOOP;
    
    sum2 := 11 - (sum2 % 11);
    IF sum2 >= 10 THEN
        sum2 := 0;
    END IF;
    
    RETURN sum2 = digits[14];
END;
$$ language 'plpgsql';

-- ============================================
-- 6. CORE TABLES
-- ============================================

-- ============================================
-- 6.1 AUTHENTICATION TABLES
-- ============================================

-- Users table (base authentication)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email_verified_at TIMESTAMP,
    email_verification_token VARCHAR(255),
    email_verification_expires_at TIMESTAMP,
    
    -- Two-factor authentication
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    
    -- Account status
    status user_status DEFAULT 'pending_verification' NOT NULL,
    user_type user_type NOT NULL,
    
    -- Login tracking
    last_login_at TIMESTAMP,
    last_login_ip INET,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    
    -- Password reset
    password_reset_token VARCHAR(255),
    password_reset_expires_at TIMESTAMP,
    
    -- ASAAS integration (FK will be added later)
    asaas_customer_id UUID,
    
    -- LGPD compliance
    lgpd_consent_date TIMESTAMP,
    data_retention_period_days INTEGER DEFAULT 1825, -- 5 years default
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- User sessions table
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_hash VARCHAR(255) UNIQUE,
    
    -- Session info
    ip_address INET,
    user_agent TEXT,
    device_id VARCHAR(255),
    
    -- Expiration
    expires_at TIMESTAMP NOT NULL,
    refresh_expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_reason VARCHAR(255),
    
    -- Activity tracking
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    requests_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================
-- 6.2 PROFILE TABLES
-- ============================================

-- Companies table
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Company information
    company_name VARCHAR(255) NOT NULL,
    trading_name VARCHAR(255),
    cnpj VARCHAR(14) UNIQUE NOT NULL,
    state_registration VARCHAR(50),
    municipal_registration VARCHAR(50),
    
    -- Business details
    business_area VARCHAR(100) NOT NULL,
    company_size company_size NOT NULL,
    founded_date DATE,
    description TEXT,
    
    -- Contact information
    phone VARCHAR(20) NOT NULL,
    website VARCHAR(255),
    linkedin_url VARCHAR(255),
    
    -- Address (JSONB for flexibility)
    address JSONB NOT NULL,
    /* Expected structure:
    {
        "street": "string",
        "number": "string",
        "complement": "string",
        "neighborhood": "string",
        "city": "string",
        "state": "string",
        "zip_code": "string",
        "country": "BR"
    }
    */
    
    -- Verification
    verification_status verification_status DEFAULT 'unverified' NOT NULL,
    verification_documents JSONB,
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id),
    
    -- Logo and branding
    logo_url VARCHAR(500),
    cover_image_url VARCHAR(500),
    brand_color VARCHAR(7), -- Hex color
    
    -- ASAAS account type
    asaas_account_type VARCHAR(20) DEFAULT 'PJ',
    
    -- Stats (denormalized for performance)
    total_projects INTEGER DEFAULT 0,
    active_projects INTEGER DEFAULT 0,
    completed_projects INTEGER DEFAULT 0,
    average_rating DECIMAL(3, 2),
    total_spent DECIMAL(15, 2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT companies_cnpj_format CHECK (cnpj ~ '^\d{14}$'),
    CONSTRAINT companies_cnpj_valid CHECK (validate_cnpj(cnpj)),
    CONSTRAINT companies_rating_range CHECK (average_rating IS NULL OR (average_rating >= 0 AND average_rating <= 5))
);

-- Freelancers table
CREATE TABLE freelancers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Personal information
    full_name VARCHAR(255) NOT NULL,
    cpf VARCHAR(11) UNIQUE NOT NULL,
    birth_date DATE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    
    -- Professional information
    professional_title VARCHAR(100) NOT NULL,
    bio TEXT,
    years_experience INTEGER DEFAULT 0,
    hourly_rate DECIMAL(10, 2),
    availability_hours_per_week INTEGER,
    work_preference work_preference DEFAULT 'remote',
    
    -- Location
    city VARCHAR(100),
    state VARCHAR(2),
    country VARCHAR(2) DEFAULT 'BR',
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',
    
    -- Professional links
    portfolio_url VARCHAR(255),
    github_url VARCHAR(255),
    linkedin_url VARCHAR(255),
    
    -- GitHub integration
    github_username VARCHAR(100) UNIQUE,
    github_verified BOOLEAN DEFAULT FALSE,
    
    -- Codero partnership
    codero_partner_id VARCHAR(100) UNIQUE,
    
    -- Banking information (encrypted)
    bank_details JSONB, -- Encrypted in application layer
    pix_key VARCHAR(255), -- Encrypted in application layer
    pix_key_type VARCHAR(20), -- cpf, cnpj, email, phone, random
    
    -- Verification
    verification_status verification_status DEFAULT 'unverified' NOT NULL,
    verification_documents JSONB,
    verified_at TIMESTAMP,
    
    -- Profile visibility
    is_available BOOLEAN DEFAULT TRUE,
    is_profile_public BOOLEAN DEFAULT TRUE,
    
    -- ASAAS account type
    asaas_account_type VARCHAR(20) DEFAULT 'PF',
    
    -- Stats (denormalized for performance)
    total_projects INTEGER DEFAULT 0,
    completed_projects INTEGER DEFAULT 0,
    success_rate DECIMAL(5, 2),
    average_rating DECIMAL(3, 2),
    total_earned DECIMAL(15, 2) DEFAULT 0,
    response_time_hours DECIMAL(5, 2),
    
    -- Gamification
    level INTEGER DEFAULT 1,
    experience_points INTEGER DEFAULT 0,
    achievement_badges JSONB DEFAULT '[]'::JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT freelancers_cpf_format CHECK (cpf ~ '^\d{11}$'),
    CONSTRAINT freelancers_cpf_valid CHECK (validate_cpf(cpf)),
    CONSTRAINT freelancers_age_minimum CHECK (birth_date <= CURRENT_DATE - INTERVAL '18 years'),
    CONSTRAINT freelancers_hourly_rate_positive CHECK (hourly_rate > 0),
    CONSTRAINT freelancers_availability_range CHECK (availability_hours_per_week >= 0 AND availability_hours_per_week <= 168),
    CONSTRAINT freelancers_rating_range CHECK (average_rating IS NULL OR (average_rating >= 0 AND average_rating <= 5))
);

-- ============================================
-- 6.3 PROJECT MANAGEMENT TABLES
-- ============================================

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Project information
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    requirements JSONB NOT NULL,
    
    -- Budget and timeline
    budget_min DECIMAL(15, 2) NOT NULL,
    budget_max DECIMAL(15, 2) NOT NULL,
    deadline DATE NOT NULL,
    estimated_duration_days INTEGER,
    
    -- Status and priority
    status project_status DEFAULT 'draft' NOT NULL,
    priority project_priority DEFAULT 'medium' NOT NULL,
    
    -- AI analysis
    complexity_score INTEGER CHECK (complexity_score >= 1 AND complexity_score <= 10),
    estimated_hours INTEGER,
    ai_decomposition_confidence DECIMAL(3, 2),
    
    -- Payment preferences
    payment_method_preference payment_method[],
    milestone_based_payment BOOLEAN DEFAULT FALSE,
    
    -- Visibility
    is_public BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    
    -- Files and attachments
    attachments JSONB DEFAULT '[]'::JSONB,
    
    -- Important dates
    published_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    
    -- Stats
    views_count INTEGER DEFAULT 0,
    proposals_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT projects_budget_range CHECK (budget_min > 0 AND budget_max >= budget_min),
    CONSTRAINT projects_deadline_future CHECK (deadline > created_at::DATE)
);

-- Microservices table (AI decomposition)
CREATE TABLE microservices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Microservice information
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    technical_requirements JSONB NOT NULL,
    
    -- Estimation
    estimated_hours INTEGER NOT NULL,
    complexity_level INTEGER NOT NULL CHECK (complexity_level >= 1 AND complexity_level <= 5),
    
    -- Dependencies and order
    dependencies UUID[], -- Array of microservice IDs
    execution_order INTEGER NOT NULL,
    is_milestone BOOLEAN DEFAULT FALSE,
    
    -- AI metadata
    ai_confidence DECIMAL(3, 2) NOT NULL,
    ai_reasoning TEXT,
    
    -- Required skills
    required_skills UUID[],
    
    -- Status tracking
    status project_status DEFAULT 'draft' NOT NULL,
    assigned_freelancer_id UUID REFERENCES freelancers(id),
    
    -- Progress tracking
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Skills table
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Project skills (many-to-many)
CREATE TABLE project_skills (
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT TRUE,
    importance_level INTEGER DEFAULT 3 CHECK (importance_level >= 1 AND importance_level <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (project_id, skill_id)
);

-- Microservice skills (many-to-many)
CREATE TABLE microservice_skills (
    microservice_id UUID NOT NULL REFERENCES microservices(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT TRUE,
    proficiency_level INTEGER DEFAULT 3 CHECK (proficiency_level >= 1 AND proficiency_level <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (microservice_id, skill_id)
);

-- Freelancer skills (many-to-many)
CREATE TABLE freelancer_skills (
    freelancer_id UUID NOT NULL REFERENCES freelancers(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_level INTEGER NOT NULL CHECK (proficiency_level >= 1 AND proficiency_level <= 5),
    years_experience DECIMAL(3, 1) DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (freelancer_id, skill_id)
);

-- ============================================
-- 6.4 PROPOSALS AND CONTRACTS
-- ============================================

-- Proposals table
CREATE TABLE proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    microservice_id UUID NOT NULL REFERENCES microservices(id) ON DELETE CASCADE,
    freelancer_id UUID NOT NULL REFERENCES freelancers(id) ON DELETE CASCADE,
    
    -- Proposal details
    proposed_value DECIMAL(15, 2) NOT NULL,
    estimated_hours INTEGER NOT NULL,
    hourly_rate DECIMAL(10, 2) NOT NULL,
    delivery_date DATE NOT NULL,
    
    -- Proposal content
    cover_letter TEXT NOT NULL,
    methodology TEXT,
    relevant_portfolio_items JSONB DEFAULT '[]'::JSONB,
    
    -- Status
    status proposal_status DEFAULT 'submitted' NOT NULL,
    
    -- AI scoring
    ai_match_score DECIMAL(3, 2),
    ai_score_reasoning JSONB,
    
    -- Review process
    reviewed_at TIMESTAMP,
    reviewed_by UUID REFERENCES users(id),
    review_notes TEXT,
    rejection_reason TEXT,
    
    -- Timestamps
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    withdrawn_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT proposals_unique_per_microservice UNIQUE (microservice_id, freelancer_id),
    CONSTRAINT proposals_value_positive CHECK (proposed_value > 0),
    CONSTRAINT proposals_hours_positive CHECK (estimated_hours > 0),
    CONSTRAINT proposals_hourly_rate_positive CHECK (hourly_rate > 0)
);

-- Contracts table
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposal_id UUID UNIQUE NOT NULL REFERENCES proposals(id),
    project_id UUID NOT NULL REFERENCES projects(id),
    microservice_id UUID NOT NULL REFERENCES microservices(id),
    company_id UUID NOT NULL REFERENCES companies(id),
    freelancer_id UUID NOT NULL REFERENCES freelancers(id),
    
    -- Contract details
    contract_number VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    
    -- Financial terms
    total_value DECIMAL(15, 2) NOT NULL,
    platform_fee_percentage DECIMAL(5, 2) DEFAULT 10.00,
    platform_fee_amount DECIMAL(15, 2) NOT NULL,
    freelancer_net_value DECIMAL(15, 2) NOT NULL,
    
    -- Timeline
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- Milestones
    milestones JSONB NOT NULL DEFAULT '[]'::JSONB,
    /* Expected structure:
    [{
        "id": "uuid",
        "title": "string",
        "description": "string",
        "value": "decimal",
        "due_date": "date",
        "status": "pending|completed|approved",
        "completed_at": "timestamp",
        "approved_at": "timestamp"
    }]
    */
    
    -- Terms and conditions
    terms_and_conditions TEXT NOT NULL,
    special_clauses TEXT,
    
    -- Payment schedule
    payment_schedule JSONB NOT NULL,
    payment_method payment_method NOT NULL,
    
    -- Status
    status contract_status DEFAULT 'draft' NOT NULL,
    
    -- Signatures
    company_signed_at TIMESTAMP,
    company_signed_by UUID REFERENCES users(id),
    company_signature_ip INET,
    
    freelancer_signed_at TIMESTAMP,
    freelancer_signature_ip INET,
    
    -- Completion
    completed_at TIMESTAMP,
    completion_notes TEXT,
    
    -- Termination
    terminated_at TIMESTAMP,
    terminated_by UUID REFERENCES users(id),
    termination_reason TEXT,
    
    -- Dispute
    disputed_at TIMESTAMP,
    dispute_reason TEXT,
    dispute_resolved_at TIMESTAMP,
    dispute_resolution TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT contracts_value_positive CHECK (total_value > 0),
    CONSTRAINT contracts_dates_valid CHECK (end_date >= start_date),
    CONSTRAINT contracts_signatures_complete CHECK (
        (status != 'active' AND status != 'completed') OR 
        (company_signed_at IS NOT NULL AND freelancer_signed_at IS NOT NULL)
    )
);

-- ============================================
-- 6.5 COMMUNICATION TABLES
-- ============================================

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    microservice_id UUID REFERENCES microservices(id) ON DELETE CASCADE,
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
    
    -- Conversation type
    conversation_type VARCHAR(50) NOT NULL, -- 'project', 'proposal', 'contract', 'support'
    subject VARCHAR(255),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP,
    archived_by UUID REFERENCES users(id),
    
    -- Stats
    messages_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Conversation participants
CREATE TABLE conversation_participants (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Participant status
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    left_at TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE,
    
    -- Read status
    last_read_at TIMESTAMP,
    unread_count INTEGER DEFAULT 0,
    
    -- Typing indicator
    is_typing BOOLEAN DEFAULT FALSE,
    started_typing_at TIMESTAMP,
    
    -- Notifications
    notifications_enabled BOOLEAN DEFAULT TRUE,
    muted_until TIMESTAMP,
    
    PRIMARY KEY (conversation_id, user_id)
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Message content
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text', -- 'text', 'file', 'system'
    
    -- Attachments
    attachments JSONB DEFAULT '[]'::JSONB,
    
    -- Reply reference
    reply_to_message_id UUID REFERENCES messages(id),
    
    -- Status
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by UUID REFERENCES users(id),
    
    -- Delivery status
    is_delivered BOOLEAN DEFAULT FALSE,
    delivered_at TIMESTAMP,
    
    -- Read receipts
    read_by JSONB DEFAULT '[]'::JSONB, -- Array of {user_id, read_at}
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT messages_content_not_empty CHECK (content != '' OR attachments != '[]'::JSONB)
);

-- Message attachments table
CREATE TABLE message_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- File information
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(100),
    file_size INTEGER NOT NULL, -- in bytes
    mime_type VARCHAR(100),
    
    -- Storage
    storage_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    
    -- Security
    is_malware_scanned BOOLEAN DEFAULT FALSE,
    scan_result VARCHAR(50),
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT message_attachments_size_limit CHECK (file_size <= 104857600) -- 100MB limit
);

-- ============================================
-- 6.6 REVIEW AND RATING TABLES
-- ============================================

-- Reviews table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID NOT NULL REFERENCES contracts(id),
    reviewer_id UUID NOT NULL REFERENCES users(id),
    reviewed_id UUID NOT NULL REFERENCES users(id),
    review_type VARCHAR(20) NOT NULL, -- 'company_to_freelancer' or 'freelancer_to_company'
    
    -- Ratings (1-5 stars)
    overall_rating INTEGER NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
    quality_rating INTEGER CHECK (quality_rating >= 1 AND quality_rating <= 5),
    communication_rating INTEGER CHECK (communication_rating >= 1 AND communication_rating <= 5),
    professionalism_rating INTEGER CHECK (professionalism_rating >= 1 AND professionalism_rating <= 5),
    deadline_rating INTEGER CHECK (deadline_rating >= 1 AND deadline_rating <= 5),
    
    -- Review content
    title VARCHAR(255),
    comment TEXT,
    
    -- Recommendation
    would_recommend BOOLEAN DEFAULT TRUE,
    would_work_again BOOLEAN DEFAULT TRUE,
    
    -- Response
    response_comment TEXT,
    response_at TIMESTAMP,
    
    -- Visibility
    is_public BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    
    -- Moderation
    is_flagged BOOLEAN DEFAULT FALSE,
    flagged_reason TEXT,
    moderated_at TIMESTAMP,
    moderated_by UUID REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT reviews_unique_per_contract_type UNIQUE (contract_id, reviewer_id, review_type),
    CONSTRAINT reviews_no_self_review CHECK (reviewer_id != reviewed_id)
);

-- ============================================
-- 6.7 NOTIFICATION TABLES
-- ============================================

-- Notifications table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification details
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Related entities
    related_entity_type VARCHAR(50),
    related_entity_id UUID,
    
    -- Action URL
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Priority
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    
    -- Delivery
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    push_sent BOOLEAN DEFAULT FALSE,
    push_sent_at TIMESTAMP,
    
    -- Expiration
    expires_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================
-- 6.8 PAYMENT INTEGRATION TABLES (ASAAS)
-- ============================================

-- ASAAS Customers table
CREATE TABLE asaas_customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- ASAAS integration
    asaas_customer_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Customer information
    customer_type asaas_customer_type NOT NULL,
    name VARCHAR(255) NOT NULL,
    cpf_cnpj VARCHAR(14) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    mobile_phone VARCHAR(20),
    
    -- Address
    address JSONB NOT NULL,
    
    -- ASAAS status
    status VARCHAR(50) DEFAULT 'ACTIVE',
    
    -- Sync information
    created_at_asaas TIMESTAMP NOT NULL,
    updated_at_asaas TIMESTAMP,
    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(50) DEFAULT 'synced',
    sync_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID NOT NULL REFERENCES contracts(id),
    payer_id UUID NOT NULL REFERENCES users(id),
    payee_id UUID NOT NULL REFERENCES users(id),
    
    -- ASAAS integration
    asaas_payment_id VARCHAR(255) UNIQUE NOT NULL,
    asaas_customer_id VARCHAR(255) NOT NULL,
    
    -- Payment details
    amount DECIMAL(15, 2) NOT NULL,
    net_value DECIMAL(15, 2),
    currency VARCHAR(3) DEFAULT 'BRL',
    description TEXT NOT NULL,
    external_reference VARCHAR(255),
    
    -- Payment method
    payment_method payment_method NOT NULL,
    
    -- Status
    status payment_status DEFAULT 'pending' NOT NULL,
    
    -- Dates
    due_date DATE NOT NULL,
    payment_date TIMESTAMP,
    confirmation_date TIMESTAMP,
    credit_date DATE,
    estimated_credit_date DATE,
    
    -- Installments (for credit card)
    installment_count INTEGER DEFAULT 1,
    installment_number INTEGER,
    installment_value DECIMAL(15, 2),
    
    -- Fees
    platform_fee_percentage DECIMAL(5, 2),
    platform_fee_amount DECIMAL(15, 2),
    asaas_fee DECIMAL(15, 2),
    
    -- Escrow
    escrow_held BOOLEAN DEFAULT TRUE,
    escrow_released_at TIMESTAMP,
    escrow_released_by UUID REFERENCES users(id),
    escrow_milestone_id UUID,
    
    -- Split payment
    split_payment_config JSONB,
    
    -- Bank slip specific (boleto)
    bank_slip_url VARCHAR(500),
    bank_slip_barcode VARCHAR(100),
    bank_slip_nosso_numero VARCHAR(50),
    
    -- PIX specific
    pix_qr_code_url VARCHAR(500),
    pix_qr_code TEXT,
    pix_key VARCHAR(255),
    
    -- Refund
    refund_requested_at TIMESTAMP,
    refund_processed_at TIMESTAMP,
    refund_amount DECIMAL(15, 2),
    refund_reason TEXT,
    
    -- Chargeback
    chargeback_status VARCHAR(50),
    chargeback_reason TEXT,
    chargeback_requested_at TIMESTAMP,
    chargeback_deadline DATE,
    
    -- ASAAS webhook
    last_webhook_at TIMESTAMP,
    webhook_attempts INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT payments_amount_positive CHECK (amount > 0),
    CONSTRAINT payments_installments_valid CHECK (installment_count >= 1 AND installment_number <= installment_count)
);

-- Payment methods table
CREATE TABLE payment_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Method details
    type payment_method NOT NULL,
    provider VARCHAR(50) DEFAULT 'ASAAS',
    asaas_payment_method_id VARCHAR(255),
    
    -- Default method
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Method specific data
    metadata JSONB NOT NULL,
    /* Expected structures:
    PIX: {"key": "string", "key_type": "cpf|cnpj|email|phone|random"}
    BANK: {"bank_code": "string", "agency": "string", "account": "string", "account_type": "checking|savings"}
    CARD: {"brand": "string", "last_digits": "string", "holder_name": "string", "expiry_month": "number", "expiry_year": "number"}
    */
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP
);

-- Create unique index to ensure only one default payment method per user
CREATE UNIQUE INDEX payment_methods_one_default_per_user 
ON payment_methods (user_id) 
WHERE is_default = TRUE;

-- ASAAS Webhooks table
CREATE TABLE asaas_webhooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Webhook identification
    asaas_event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    
    -- Related object
    object_type VARCHAR(50) NOT NULL, -- 'payment', 'subscription', 'transfer'
    object_id VARCHAR(255) NOT NULL,
    
    -- Payload
    payload JSONB NOT NULL,
    headers JSONB,
    
    -- Processing
    status asaas_webhook_status DEFAULT 'received' NOT NULL,
    processed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP,
    
    -- Timestamps
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Indexing for deduplication
    CONSTRAINT asaas_webhooks_unique_event UNIQUE (asaas_event_id, event_type)
);

-- ASAAS Transfers table
CREATE TABLE asaas_transfers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id UUID NOT NULL REFERENCES payments(id),
    freelancer_id UUID NOT NULL REFERENCES freelancers(id),
    
    -- ASAAS integration
    asaas_transfer_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Transfer details
    amount DECIMAL(15, 2) NOT NULL,
    net_value DECIMAL(15, 2) NOT NULL,
    transfer_fee DECIMAL(15, 2) DEFAULT 0,
    
    -- Transfer method
    transfer_method VARCHAR(20) NOT NULL, -- 'PIX', 'TED', 'DOC'
    
    -- Bank account or PIX
    bank_account JSONB,
    pix_key VARCHAR(255),
    pix_key_type VARCHAR(20),
    
    -- Status
    status asaas_transfer_status DEFAULT 'pending' NOT NULL,
    
    -- Dates
    scheduled_date DATE NOT NULL,
    effective_date DATE,
    
    -- Description
    description TEXT,
    
    -- Failure handling
    failure_reason TEXT,
    failed_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT asaas_transfers_amount_positive CHECK (amount > 0)
);

-- ASAAS Subscriptions table (for recurring payments)
CREATE TABLE asaas_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts(id),
    customer_id UUID NOT NULL REFERENCES asaas_customers(id),
    
    -- ASAAS integration
    asaas_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Subscription details
    description TEXT NOT NULL,
    billing_type payment_method NOT NULL,
    value DECIMAL(15, 2) NOT NULL,
    cycle VARCHAR(20) NOT NULL, -- 'WEEKLY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'SEMIANNUALLY', 'YEARLY'
    
    -- Dates
    next_due_date DATE NOT NULL,
    end_date DATE,
    
    -- Status
    status VARCHAR(50) NOT NULL, -- 'ACTIVE', 'INACTIVE', 'EXPIRED'
    
    -- Discount
    discount_value DECIMAL(15, 2),
    discount_duration_months INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    cancelled_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT asaas_subscriptions_value_positive CHECK (value > 0)
);

-- ASAAS Settings table
CREATE TABLE asaas_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    environment VARCHAR(20) NOT NULL DEFAULT 'production', -- 'sandbox', 'production'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ASAAS Fees table
CREATE TABLE asaas_fees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_method payment_method NOT NULL,
    fee_type VARCHAR(20) NOT NULL, -- 'PERCENTAGE', 'FIXED'
    fee_value DECIMAL(10, 4) NOT NULL,
    min_value DECIMAL(15, 2),
    max_value DECIMAL(15, 2),
    is_active BOOLEAN DEFAULT TRUE,
    effective_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================
-- 6.9 RBAC (ROLE-BASED ACCESS CONTROL) TABLES
-- ============================================

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Hierarchy
    level INTEGER NOT NULL DEFAULT 1,
    parent_role_id UUID REFERENCES roles(id),
    
    -- System role flag
    is_system_role BOOLEAN DEFAULT FALSE,
    
    -- Permissions array (denormalized for performance)
    permissions TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- Financial permissions
    financial_permissions TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- Limits
    max_projects INTEGER,
    max_users INTEGER,
    max_monthly_transactions DECIMAL(15, 2),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Permission structure
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    
    -- Conditions
    conditions JSONB,
    
    -- Categories
    category VARCHAR(50) NOT NULL,
    is_financial BOOLEAN DEFAULT FALSE,
    
    -- Risk level
    risk_level VARCHAR(20) DEFAULT 'low', -- 'low', 'medium', 'high', 'critical'
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Unique permission per resource-action
    CONSTRAINT permissions_unique_resource_action UNIQUE (resource, action)
);

-- Role permissions (many-to-many)
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    
    -- Grant details
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Conditions override
    conditions_override JSONB,
    
    -- Expiration
    expires_at TIMESTAMP,
    
    PRIMARY KEY (role_id, permission_id)
);

-- User roles (many-to-many with context)
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id),
    
    -- Context (e.g., specific company or project)
    context_type VARCHAR(50), -- 'global', 'company', 'project'
    context_id UUID, -- ID of the company or project
    
    -- Grant details
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reason TEXT,
    
    -- Expiration
    expires_at TIMESTAMP,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP,
    revoked_by UUID REFERENCES users(id),
    revoke_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT user_roles_unique_per_context UNIQUE (user_id, role_id, context_type, context_id)
);

-- ============================================
-- 6.10 AUDIT AND LOGGING TABLES
-- ============================================

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID DEFAULT uuid_generate_v4(),
    
    -- Actor information
    user_id UUID REFERENCES users(id),
    user_email VARCHAR(255),
    user_type VARCHAR(50),
    
    -- Action details
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    resource_name VARCHAR(255),
    
    -- Changes
    old_values JSONB,
    new_values JSONB,
    
    -- Request information
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    
    -- Financial operation flag
    is_financial_operation BOOLEAN DEFAULT FALSE,
    amount DECIMAL(15, 2),
    currency VARCHAR(3),
    
    -- ASAAS reference
    asaas_reference VARCHAR(255),
    
    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Primary key must include partition column
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create partitions for audit_logs (example for 2025)
CREATE TABLE audit_logs_2025_q1 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE audit_logs_2025_q2 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

CREATE TABLE audit_logs_2025_q3 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

CREATE TABLE audit_logs_2025_q4 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

-- Activity logs table (less critical activities)
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Activity details
    activity_type VARCHAR(100) NOT NULL,
    description TEXT,
    metadata JSONB,
    
    -- Performance metrics
    duration_ms INTEGER,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================
-- 6.11 ADDITIONAL TABLES
-- ============================================

-- Badges table
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    icon_url VARCHAR(500),
    category VARCHAR(50) NOT NULL, -- 'achievement', 'milestone', 'skill', 'special'
    criteria JSONB NOT NULL, -- Criteria for earning the badge
    points_value INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Freelancer badges (many-to-many)
CREATE TABLE freelancer_badges (
    freelancer_id UUID NOT NULL REFERENCES freelancers(id) ON DELETE CASCADE,
    badge_id UUID NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    earned_reason TEXT,
    PRIMARY KEY (freelancer_id, badge_id)
);

-- Disputes table
CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID NOT NULL REFERENCES contracts(id),
    project_id UUID NOT NULL REFERENCES projects(id),
    complainant_id UUID NOT NULL REFERENCES users(id),
    respondent_id UUID NOT NULL REFERENCES users(id),
    
    -- Dispute details
    dispute_type VARCHAR(50) NOT NULL, -- 'payment', 'quality', 'deadline', 'communication', 'other'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'open' NOT NULL, -- 'open', 'investigating', 'awaiting_response', 'resolved', 'escalated'
    priority VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    
    -- Evidence
    evidence JSONB DEFAULT '[]'::JSONB,
    
    -- Resolution
    resolution_type VARCHAR(50), -- 'mutual_agreement', 'platform_decision', 'refund', 'cancelled'
    resolution_details TEXT,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP,
    
    -- Financial impact
    disputed_amount DECIMAL(15, 2),
    refund_amount DECIMAL(15, 2),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    responded_at TIMESTAMP,
    escalated_at TIMESTAMP
);

-- Escrow accounts table
CREATE TABLE escrow_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID UNIQUE NOT NULL REFERENCES contracts(id),
    payment_id UUID REFERENCES payments(id),
    
    -- Amounts
    total_amount DECIMAL(15, 2) NOT NULL,
    held_amount DECIMAL(15, 2) NOT NULL DEFAULT 0,
    released_amount DECIMAL(15, 2) NOT NULL DEFAULT 0,
    refunded_amount DECIMAL(15, 2) NOT NULL DEFAULT 0,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active' NOT NULL, -- 'active', 'partially_released', 'fully_released', 'disputed', 'refunded'
    
    -- Milestones
    milestones JSONB DEFAULT '[]'::JSONB,
    
    -- Release conditions
    auto_release_date DATE,
    release_approved_by UUID REFERENCES users(id),
    release_approved_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT escrow_amounts_check CHECK (
        held_amount >= 0 AND 
        released_amount >= 0 AND 
        refunded_amount >= 0 AND
        (held_amount + released_amount + refunded_amount) <= total_amount
    )
);

-- LGPD Compliance table
CREATE TABLE lgpd_compliance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Data type and purpose
    data_type VARCHAR(100) NOT NULL, -- 'personal_info', 'financial_data', 'usage_data', 'communications'
    purpose TEXT NOT NULL,
    
    -- Legal basis
    legal_basis VARCHAR(50) NOT NULL, -- 'consent', 'contract', 'legal_obligation', 'vital_interests', 'public_task', 'legitimate_interests'
    legal_basis_details TEXT,
    
    -- Consent
    consent_given BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMP,
    consent_withdrawal_date TIMESTAMP,
    
    -- Retention
    retention_period_days INTEGER NOT NULL,
    deletion_date DATE,
    
    -- Processing
    processing_activities TEXT[],
    third_party_sharing JSONB,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Data breach log table
CREATE TABLE data_breach_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Incident details
    incident_date TIMESTAMP NOT NULL,
    discovered_date TIMESTAMP NOT NULL,
    reported_date TIMESTAMP,
    
    -- Severity and scope
    severity VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    breach_type VARCHAR(100) NOT NULL,
    affected_data_types TEXT[],
    affected_users_count INTEGER,
    affected_user_ids UUID[],
    
    -- Description
    description TEXT NOT NULL,
    cause TEXT,
    
    -- Actions taken
    immediate_actions TEXT,
    remediation_actions TEXT,
    preventive_measures TEXT,
    
    -- Notifications
    users_notified BOOLEAN DEFAULT FALSE,
    users_notified_date TIMESTAMP,
    anpd_notified BOOLEAN DEFAULT FALSE,
    anpd_notified_date TIMESTAMP,
    anpd_protocol_number VARCHAR(100),
    
    -- Investigation
    investigation_status VARCHAR(50) DEFAULT 'open', -- 'open', 'investigating', 'closed'
    investigation_findings TEXT,
    root_cause_analysis TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at TIMESTAMP
);

-- LGPD requests table
CREATE TABLE lgpd_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    request_number VARCHAR(50) UNIQUE NOT NULL,
    
    -- Request details
    request_type VARCHAR(50) NOT NULL, -- 'access', 'rectification', 'deletion', 'portability', 'opposition', 'restriction'
    description TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending' NOT NULL, -- 'pending', 'in_progress', 'completed', 'rejected'
    rejection_reason TEXT,
    
    -- Processing
    assigned_to UUID REFERENCES users(id),
    processed_by UUID REFERENCES users(id),
    
    -- Response
    response_data JSONB,
    response_format VARCHAR(50), -- 'json', 'csv', 'pdf'
    
    -- Deadlines (LGPD requires response within 15 days)
    deadline_date DATE NOT NULL,
    completed_date DATE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- GitHub integrations table
CREATE TABLE github_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    
    -- GitHub OAuth
    github_user_id VARCHAR(100) UNIQUE NOT NULL,
    github_username VARCHAR(100) UNIQUE NOT NULL,
    github_email VARCHAR(255),
    access_token TEXT, -- Encrypted
    refresh_token TEXT, -- Encrypted
    token_expires_at TIMESTAMP,
    
    -- Profile data
    github_profile_data JSONB,
    repositories_count INTEGER,
    followers_count INTEGER,
    
    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    
    -- Stats
    total_commits INTEGER DEFAULT 0,
    total_pull_requests INTEGER DEFAULT 0,
    languages JSONB,
    
    -- Sync
    last_sync_at TIMESTAMP,
    sync_status VARCHAR(50) DEFAULT 'pending',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Codero partnerships table
CREATE TABLE codero_partnerships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    freelancer_id UUID UNIQUE NOT NULL REFERENCES freelancers(id),
    
    -- Codero partner info
    codero_partner_id VARCHAR(100) UNIQUE NOT NULL,
    partnership_tier VARCHAR(50), -- 'bronze', 'silver', 'gold', 'platinum'
    
    -- Benefits
    discount_percentage DECIMAL(5, 2),
    special_benefits JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- 'pending', 'active', 'suspended', 'terminated'
    activated_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Performance
    projects_completed_via_codero INTEGER DEFAULT 0,
    total_revenue_via_codero DECIMAL(15, 2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- AI requests log table
CREATE TABLE ai_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    
    -- Request details
    request_type VARCHAR(100) NOT NULL, -- 'project_optimization', 'freelancer_matching', 'skill_analysis', 'cost_estimation'
    request_payload JSONB NOT NULL,
    
    -- AI model info
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    
    -- Response
    response_data JSONB,
    confidence_score DECIMAL(3, 2),
    processing_time_ms INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    
    -- Usage tracking
    tokens_used INTEGER,
    cost_estimate DECIMAL(10, 4),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);

-- User points table (gamification)
CREATE TABLE user_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Points
    total_points INTEGER DEFAULT 0,
    available_points INTEGER DEFAULT 0,
    spent_points INTEGER DEFAULT 0,
    
    -- Level system
    current_level INTEGER DEFAULT 1,
    points_to_next_level INTEGER,
    
    -- Categories
    points_breakdown JSONB DEFAULT '{}'::JSONB,
    
    -- Streaks
    current_streak_days INTEGER DEFAULT 0,
    longest_streak_days INTEGER DEFAULT 0,
    last_activity_date DATE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT user_points_unique UNIQUE (user_id),
    CONSTRAINT points_non_negative CHECK (
        total_points >= 0 AND 
        available_points >= 0 AND 
        spent_points >= 0
    )
);

-- Achievements table
CREATE TABLE achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    
    -- Requirements
    criteria JSONB NOT NULL,
    points_reward INTEGER DEFAULT 0,
    
    -- Display
    icon_url VARCHAR(500),
    badge_color VARCHAR(7),
    is_secret BOOLEAN DEFAULT FALSE,
    
    -- Rarity
    rarity VARCHAR(20) DEFAULT 'common', -- 'common', 'uncommon', 'rare', 'epic', 'legendary'
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Stats
    times_earned INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- User achievements (many-to-many)
CREATE TABLE user_achievements (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id UUID NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    
    -- Earning details
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    progress JSONB,
    
    -- Display
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER,
    
    PRIMARY KEY (user_id, achievement_id)
);

-- Leaderboards table
CREATE TABLE leaderboards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    
    -- Configuration
    period_type VARCHAR(20) NOT NULL, -- 'all_time', 'yearly', 'monthly', 'weekly', 'daily'
    metric_type VARCHAR(50) NOT NULL, -- 'points', 'projects', 'earnings', 'rating'
    user_type VARCHAR(20), -- 'freelancer', 'company', 'all'
    
    -- Filters
    skill_filter UUID REFERENCES skills(id),
    category_filter VARCHAR(100),
    
    -- Display
    is_public BOOLEAN DEFAULT TRUE,
    max_entries INTEGER DEFAULT 100,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Leaderboard entries
CREATE TABLE leaderboard_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    leaderboard_id UUID NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Ranking
    rank INTEGER NOT NULL,
    score DECIMAL(15, 2) NOT NULL,
    previous_rank INTEGER,
    
    -- Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT leaderboard_entries_unique UNIQUE (leaderboard_id, user_id, period_start)
);

-- Meetings table
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id),
    contract_id UUID REFERENCES contracts(id),
    
    -- Meeting details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    agenda TEXT,
    
    -- Scheduling
    scheduled_start TIMESTAMP NOT NULL,
    scheduled_end TIMESTAMP NOT NULL,
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',
    
    -- Location/Platform
    meeting_type VARCHAR(50) NOT NULL, -- 'online', 'in_person', 'phone'
    location TEXT,
    meeting_url VARCHAR(500),
    meeting_platform VARCHAR(50), -- 'zoom', 'meet', 'teams', 'discord'
    
    -- Organizer
    organized_by UUID NOT NULL REFERENCES users(id),
    
    -- Status
    status VARCHAR(50) DEFAULT 'scheduled', -- 'scheduled', 'in_progress', 'completed', 'cancelled'
    
    -- Recording
    is_recorded BOOLEAN DEFAULT FALSE,
    recording_url VARCHAR(500),
    
    -- Notes
    meeting_notes TEXT,
    action_items JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    cancelled_at TIMESTAMP
);

-- Meeting participants
CREATE TABLE meeting_participants (
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Participation
    role VARCHAR(50) DEFAULT 'participant', -- 'organizer', 'presenter', 'participant'
    is_required BOOLEAN DEFAULT TRUE,
    
    -- Response
    response_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'accepted', 'declined', 'tentative'
    responded_at TIMESTAMP,
    
    -- Attendance
    attended BOOLEAN,
    join_time TIMESTAMP,
    leave_time TIMESTAMP,
    
    -- Notes
    notes TEXT,
    
    PRIMARY KEY (meeting_id, user_id)
);

-- System configuration table
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    
    -- Metadata
    value_type VARCHAR(50) NOT NULL, -- 'string', 'number', 'boolean', 'json'
    category VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Validation
    validation_rules JSONB,
    default_value TEXT,
    
    -- Security
    is_sensitive BOOLEAN DEFAULT FALSE,
    encrypted BOOLEAN DEFAULT FALSE,
    
    -- Audit
    last_modified_by UUID REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Feature flags table
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flag_key VARCHAR(100) UNIQUE NOT NULL,
    
    -- Flag details
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Status
    is_enabled BOOLEAN DEFAULT FALSE,
    
    -- Rollout configuration
    rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
    
    -- Targeting
    target_users UUID[],
    target_companies UUID[],
    target_rules JSONB,
    
    -- Metadata
    tags TEXT[],
    
    -- Audit
    created_by UUID REFERENCES users(id),
    last_modified_by UUID REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    enabled_at TIMESTAMP,
    disabled_at TIMESTAMP
);

-- User analytics table
CREATE TABLE user_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Session data
    session_id UUID,
    session_start TIMESTAMP,
    session_end TIMESTAMP,
    session_duration_seconds INTEGER,
    
    -- Activity metrics
    page_views INTEGER DEFAULT 0,
    actions_performed JSONB DEFAULT '[]'::JSONB,
    features_used JSONB DEFAULT '[]'::JSONB,
    
    -- Device and location
    device_type VARCHAR(50),
    browser VARCHAR(100),
    os VARCHAR(100),
    ip_address INET,
    country VARCHAR(2),
    city VARCHAR(100),
    
    -- Engagement metrics
    bounce_rate DECIMAL(5, 2),
    engagement_score DECIMAL(5, 2),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT user_analytics_duration_positive CHECK (session_duration_seconds >= 0)
);

-- Project analytics table
CREATE TABLE project_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    
    -- View metrics
    total_views INTEGER DEFAULT 0,
    unique_views INTEGER DEFAULT 0,
    avg_time_on_page_seconds INTEGER,
    
    -- Engagement metrics
    proposals_submitted INTEGER DEFAULT 0,
    proposals_conversion_rate DECIMAL(5, 2),
    messages_sent INTEGER DEFAULT 0,
    
    -- Performance metrics
    time_to_first_proposal_hours DECIMAL(10, 2),
    time_to_hire_hours DECIMAL(10, 2),
    completion_rate DECIMAL(5, 2),
    
    -- Source tracking
    traffic_sources JSONB DEFAULT '{}'::JSONB,
    referral_sources JSONB DEFAULT '{}'::JSONB,
    
    -- Daily snapshots
    daily_metrics JSONB DEFAULT '[]'::JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================
-- 7. ALTER TABLES - ADD FOREIGN KEYS
-- ============================================

-- Add foreign key from users to asaas_customers after asaas_customers table is created
ALTER TABLE users 
ADD CONSTRAINT fk_users_asaas_customers 
FOREIGN KEY (asaas_customer_id) 
REFERENCES asaas_customers(id);

-- ============================================
-- 8. INDEXES FOR PERFORMANCE
-- ============================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_last_login ON users(last_login_at DESC) WHERE last_login_at IS NOT NULL;

-- User sessions indexes
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_token ON user_sessions(token_hash);

-- Companies indexes
CREATE INDEX idx_companies_user_id ON companies(user_id);
CREATE INDEX idx_companies_cnpj ON companies(cnpj);
CREATE INDEX idx_companies_verification_status ON companies(verification_status);
CREATE INDEX idx_companies_business_area ON companies(business_area);

-- Freelancers indexes
CREATE INDEX idx_freelancers_user_id ON freelancers(user_id);
CREATE INDEX idx_freelancers_cpf ON freelancers(cpf);
CREATE INDEX idx_freelancers_verification_status ON freelancers(verification_status);
CREATE INDEX idx_freelancers_is_available ON freelancers(is_available) WHERE is_available = TRUE;
CREATE INDEX idx_freelancers_hourly_rate ON freelancers(hourly_rate);
CREATE INDEX idx_freelancers_rating ON freelancers(average_rating DESC) WHERE average_rating IS NOT NULL;

-- Projects indexes
CREATE INDEX idx_projects_company_id ON projects(company_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_slug ON projects(slug);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX idx_projects_published_at ON projects(published_at DESC) WHERE published_at IS NOT NULL;
CREATE INDEX idx_projects_budget_range ON projects(budget_min, budget_max);
CREATE INDEX idx_projects_deadline ON projects(deadline);

-- Full-text search indexes
CREATE INDEX idx_projects_search ON projects USING gin(
    to_tsvector('portuguese', title || ' ' || description)
);

-- Microservices indexes
CREATE INDEX idx_microservices_project_id ON microservices(project_id);
CREATE INDEX idx_microservices_status ON microservices(status);
CREATE INDEX idx_microservices_assigned_freelancer ON microservices(assigned_freelancer_id) WHERE assigned_freelancer_id IS NOT NULL;

-- Skills indexes
CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_skills_slug ON skills(slug);
CREATE INDEX idx_skills_category ON skills(category);

-- Proposals indexes
CREATE INDEX idx_proposals_microservice_id ON proposals(microservice_id);
CREATE INDEX idx_proposals_freelancer_id ON proposals(freelancer_id);
CREATE INDEX idx_proposals_status ON proposals(status);
CREATE INDEX idx_proposals_ai_score ON proposals(ai_match_score DESC) WHERE ai_match_score IS NOT NULL;
CREATE INDEX idx_proposals_submitted_at ON proposals(submitted_at DESC);

-- Contracts indexes
CREATE INDEX idx_contracts_company_id ON contracts(company_id);
CREATE INDEX idx_contracts_freelancer_id ON contracts(freelancer_id);
CREATE INDEX idx_contracts_project_id ON contracts(project_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_contract_number ON contracts(contract_number);

-- Messages indexes
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);

-- Notifications indexes
CREATE INDEX idx_notifications_user_id ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

-- Payments indexes
CREATE INDEX idx_payments_contract_id ON payments(contract_id);
CREATE INDEX idx_payments_payer_id ON payments(payer_id);
CREATE INDEX idx_payments_payee_id ON payments(payee_id);
CREATE INDEX idx_payments_asaas_payment_id ON payments(asaas_payment_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_due_date ON payments(due_date);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
CREATE INDEX idx_payments_pending ON payments(status, due_date) WHERE status = 'pending';

-- ASAAS specific indexes
CREATE INDEX idx_asaas_customers_user_id ON asaas_customers(user_id);
CREATE INDEX idx_asaas_customers_asaas_id ON asaas_customers(asaas_customer_id);
CREATE INDEX idx_asaas_customers_cpf_cnpj ON asaas_customers(cpf_cnpj);

CREATE INDEX idx_asaas_webhooks_event_id ON asaas_webhooks(asaas_event_id);
CREATE INDEX idx_asaas_webhooks_object ON asaas_webhooks(object_type, object_id);
CREATE INDEX idx_asaas_webhooks_status ON asaas_webhooks(status, received_at) WHERE status != 'processed';

CREATE INDEX idx_asaas_transfers_payment_id ON asaas_transfers(payment_id);
CREATE INDEX idx_asaas_transfers_freelancer_id ON asaas_transfers(freelancer_id);
CREATE INDEX idx_asaas_transfers_status ON asaas_transfers(status);

-- RBAC indexes
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_context ON user_roles(context_type, context_id) WHERE context_id IS NOT NULL;
CREATE INDEX idx_user_roles_active ON user_roles(user_id, is_active) WHERE is_active = TRUE;

-- Audit logs indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_financial ON audit_logs(is_financial_operation, created_at DESC) WHERE is_financial_operation = TRUE;

-- Disputes indexes
CREATE INDEX idx_disputes_contract_id ON disputes(contract_id);
CREATE INDEX idx_disputes_project_id ON disputes(project_id);
CREATE INDEX idx_disputes_complainant_id ON disputes(complainant_id);
CREATE INDEX idx_disputes_respondent_id ON disputes(respondent_id);
CREATE INDEX idx_disputes_status ON disputes(status);
CREATE INDEX idx_disputes_created_at ON disputes(created_at DESC);

-- Escrow accounts indexes
CREATE INDEX idx_escrow_accounts_contract_id ON escrow_accounts(contract_id);
CREATE INDEX idx_escrow_accounts_payment_id ON escrow_accounts(payment_id);
CREATE INDEX idx_escrow_accounts_status ON escrow_accounts(status);

-- LGPD compliance indexes
CREATE INDEX idx_lgpd_compliance_user_id ON lgpd_compliance(user_id);
CREATE INDEX idx_lgpd_compliance_data_type ON lgpd_compliance(data_type);
CREATE INDEX idx_lgpd_compliance_legal_basis ON lgpd_compliance(legal_basis);
CREATE INDEX idx_lgpd_compliance_active ON lgpd_compliance(is_active) WHERE is_active = TRUE;

-- Data breach log indexes
CREATE INDEX idx_data_breach_log_incident_id ON data_breach_log(incident_id);
CREATE INDEX idx_data_breach_log_severity ON data_breach_log(severity);
CREATE INDEX idx_data_breach_log_discovered_date ON data_breach_log(discovered_date DESC);

-- LGPD requests indexes
CREATE INDEX idx_lgpd_requests_user_id ON lgpd_requests(user_id);
CREATE INDEX idx_lgpd_requests_request_number ON lgpd_requests(request_number);
CREATE INDEX idx_lgpd_requests_status ON lgpd_requests(status);
CREATE INDEX idx_lgpd_requests_deadline ON lgpd_requests(deadline_date);

-- GitHub integrations indexes
CREATE INDEX idx_github_integrations_user_id ON github_integrations(user_id);
CREATE INDEX idx_github_integrations_github_username ON github_integrations(github_username);
CREATE INDEX idx_github_integrations_verified ON github_integrations(is_verified) WHERE is_verified = TRUE;

-- Codero partnerships indexes
CREATE INDEX idx_codero_partnerships_freelancer_id ON codero_partnerships(freelancer_id);
CREATE INDEX idx_codero_partnerships_partner_id ON codero_partnerships(codero_partner_id);
CREATE INDEX idx_codero_partnerships_status ON codero_partnerships(status);

-- AI requests indexes
CREATE INDEX idx_ai_requests_user_id ON ai_requests(user_id);
CREATE INDEX idx_ai_requests_type ON ai_requests(request_type);
CREATE INDEX idx_ai_requests_status ON ai_requests(status);
CREATE INDEX idx_ai_requests_created_at ON ai_requests(created_at DESC);

-- User points indexes
CREATE INDEX idx_user_points_user_id ON user_points(user_id);
CREATE INDEX idx_user_points_level ON user_points(current_level);
CREATE INDEX idx_user_points_total ON user_points(total_points DESC);

-- Achievements indexes
CREATE INDEX idx_achievements_name ON achievements(name);
CREATE INDEX idx_achievements_category ON achievements(category);
CREATE INDEX idx_achievements_rarity ON achievements(rarity);

-- User achievements indexes
CREATE INDEX idx_user_achievements_user_id ON user_achievements(user_id);
CREATE INDEX idx_user_achievements_earned_at ON user_achievements(earned_at DESC);

-- Leaderboards indexes
CREATE INDEX idx_leaderboards_name ON leaderboards(name);
CREATE INDEX idx_leaderboards_period_metric ON leaderboards(period_type, metric_type);

-- Leaderboard entries indexes
CREATE INDEX idx_leaderboard_entries_leaderboard_id ON leaderboard_entries(leaderboard_id);
CREATE INDEX idx_leaderboard_entries_user_id ON leaderboard_entries(user_id);
CREATE INDEX idx_leaderboard_entries_rank ON leaderboard_entries(rank);
CREATE INDEX idx_leaderboard_entries_period ON leaderboard_entries(period_start, period_end);

-- Meetings indexes
CREATE INDEX idx_meetings_project_id ON meetings(project_id);
CREATE INDEX idx_meetings_contract_id ON meetings(contract_id);
CREATE INDEX idx_meetings_organized_by ON meetings(organized_by);
CREATE INDEX idx_meetings_scheduled ON meetings(scheduled_start, scheduled_end);
CREATE INDEX idx_meetings_status ON meetings(status);

-- Meeting participants indexes
CREATE INDEX idx_meeting_participants_meeting_id ON meeting_participants(meeting_id);
CREATE INDEX idx_meeting_participants_user_id ON meeting_participants(user_id);
CREATE INDEX idx_meeting_participants_response ON meeting_participants(response_status);

-- System config indexes
CREATE INDEX idx_system_config_key ON system_config(config_key);
CREATE INDEX idx_system_config_category ON system_config(category);

-- Feature flags indexes
CREATE INDEX idx_feature_flags_key ON feature_flags(flag_key);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(is_enabled) WHERE is_enabled = TRUE;

-- Message attachments indexes
CREATE INDEX idx_message_attachments_message_id ON message_attachments(message_id);
CREATE INDEX idx_message_attachments_uploaded_at ON message_attachments(uploaded_at DESC);

-- User analytics indexes
CREATE INDEX idx_user_analytics_user_id ON user_analytics(user_id);
CREATE INDEX idx_user_analytics_session_id ON user_analytics(session_id);
CREATE INDEX idx_user_analytics_created_at ON user_analytics(created_at DESC);

-- Project analytics indexes
CREATE INDEX idx_project_analytics_project_id ON project_analytics(project_id);
CREATE INDEX idx_project_analytics_updated_at ON project_analytics(updated_at DESC);

-- ============================================
-- 9. TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to all relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_freelancers_updated_at BEFORE UPDATE ON freelancers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_microservices_updated_at BEFORE UPDATE ON microservices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_proposals_updated_at BEFORE UPDATE ON proposals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at BEFORE UPDATE ON contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_skills_updated_at BEFORE UPDATE ON skills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_freelancer_skills_updated_at BEFORE UPDATE ON freelancer_skills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_methods_updated_at BEFORE UPDATE ON payment_methods
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asaas_customers_updated_at BEFORE UPDATE ON asaas_customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asaas_transfers_updated_at BEFORE UPDATE ON asaas_transfers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asaas_subscriptions_updated_at BEFORE UPDATE ON asaas_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asaas_settings_updated_at BEFORE UPDATE ON asaas_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asaas_fees_updated_at BEFORE UPDATE ON asaas_fees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_badges_updated_at BEFORE UPDATE ON badges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at BEFORE UPDATE ON permissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_roles_updated_at BEFORE UPDATE ON user_roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_disputes_updated_at BEFORE UPDATE ON disputes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_escrow_accounts_updated_at BEFORE UPDATE ON escrow_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lgpd_compliance_updated_at BEFORE UPDATE ON lgpd_compliance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_data_breach_log_updated_at BEFORE UPDATE ON data_breach_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lgpd_requests_updated_at BEFORE UPDATE ON lgpd_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_github_integrations_updated_at BEFORE UPDATE ON github_integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_codero_partnerships_updated_at BEFORE UPDATE ON codero_partnerships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_points_updated_at BEFORE UPDATE ON user_points
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_achievements_updated_at BEFORE UPDATE ON achievements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leaderboards_updated_at BEFORE UPDATE ON leaderboards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meetings_updated_at BEFORE UPDATE ON meetings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feature_flags_updated_at BEFORE UPDATE ON feature_flags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_project_analytics_updated_at BEFORE UPDATE ON project_analytics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate slug from title
CREATE OR REPLACE FUNCTION generate_slug()
RETURNS TRIGGER AS $$
DECLARE
    base_slug TEXT;
    final_slug TEXT;
    counter INTEGER := 0;
BEGIN
    -- Generate base slug from title
    base_slug := regexp_replace(
        lower(unaccent(NEW.title)),
        '[^a-z0-9]+', '-', 'g'
    );
    base_slug := trim(both '-' from base_slug);
    
    -- Check for uniqueness and add counter if needed
    final_slug := base_slug;
    WHILE EXISTS (
        SELECT 1 FROM projects 
        WHERE slug = final_slug AND id != COALESCE(NEW.id, uuid_nil())
    ) LOOP
        counter := counter + 1;
        final_slug := base_slug || '-' || counter;
    END LOOP;
    
    NEW.slug := final_slug;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply slug generation trigger
CREATE TRIGGER generate_project_slug BEFORE INSERT OR UPDATE OF title ON projects
    FOR EACH ROW EXECUTE FUNCTION generate_slug();

-- Function to update project stats
CREATE OR REPLACE FUNCTION update_project_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'proposals' THEN
        -- Update proposals count
        UPDATE projects 
        SET proposals_count = (
            SELECT COUNT(*) 
            FROM proposals p
            JOIN microservices m ON p.microservice_id = m.id
            WHERE m.project_id = (
                SELECT project_id 
                FROM microservices 
                WHERE id = NEW.microservice_id
            )
        )
        WHERE id = (
            SELECT project_id 
            FROM microservices 
            WHERE id = NEW.microservice_id
        );
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply stats trigger
CREATE TRIGGER update_project_stats_on_proposal
    AFTER INSERT OR DELETE ON proposals
    FOR EACH ROW EXECUTE FUNCTION update_project_stats();

-- Function to update company stats
CREATE OR REPLACE FUNCTION update_company_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Update project counts
    UPDATE companies
    SET 
        total_projects = (
            SELECT COUNT(*) FROM projects WHERE company_id = NEW.company_id
        ),
        active_projects = (
            SELECT COUNT(*) FROM projects 
            WHERE company_id = NEW.company_id AND status = 'in_progress'
        ),
        completed_projects = (
            SELECT COUNT(*) FROM projects 
            WHERE company_id = NEW.company_id AND status = 'completed'
        )
    WHERE id = NEW.company_id;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply company stats trigger
CREATE TRIGGER update_company_stats_on_project
    AFTER INSERT OR UPDATE OF status OR DELETE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_company_stats();

-- Function to calculate platform fees
CREATE OR REPLACE FUNCTION calculate_platform_fee(
    amount DECIMAL(15, 2),
    fee_percentage DECIMAL(5, 2) DEFAULT 10.00
)
RETURNS TABLE (
    platform_fee DECIMAL(15, 2),
    net_amount DECIMAL(15, 2)
) AS $$
BEGIN
    platform_fee := ROUND(amount * fee_percentage / 100, 2);
    net_amount := amount - platform_fee;
    RETURN NEXT;
END;
$$ language 'plpgsql';

-- ============================================
-- 10. ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE freelancers ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY users_own_data ON users
    FOR ALL USING (id = current_setting('app.current_user_id')::UUID);

-- Companies can see their own profile
CREATE POLICY companies_own_profile ON companies
    FOR ALL USING (user_id = current_setting('app.current_user_id')::UUID);

-- Freelancers can see their own profile
CREATE POLICY freelancers_own_profile ON freelancers
    FOR ALL USING (user_id = current_setting('app.current_user_id')::UUID);

-- Public projects are visible to all, own projects always visible
CREATE POLICY projects_visibility ON projects
    FOR SELECT USING (
        is_public = TRUE OR 
        company_id IN (
            SELECT id FROM companies WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Companies can manage their own projects
CREATE POLICY projects_company_manage ON projects
    FOR ALL USING (
        company_id IN (
            SELECT id FROM companies WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Freelancers can see their proposals
CREATE POLICY proposals_freelancer_view ON proposals
    FOR ALL USING (
        freelancer_id IN (
            SELECT id FROM freelancers WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Companies can see proposals for their projects
CREATE POLICY proposals_company_view ON proposals
    FOR SELECT USING (
        microservice_id IN (
            SELECT m.id FROM microservices m
            JOIN projects p ON m.project_id = p.id
            JOIN companies c ON p.company_id = c.id
            WHERE c.user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Contracts visible to both parties
CREATE POLICY contracts_parties_access ON contracts
    FOR ALL USING (
        company_id IN (
            SELECT id FROM companies WHERE user_id = current_setting('app.current_user_id')::UUID
        ) OR
        freelancer_id IN (
            SELECT id FROM freelancers WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Messages visible to conversation participants
CREATE POLICY messages_participants_only ON messages
    FOR ALL USING (
        conversation_id IN (
            SELECT conversation_id FROM conversation_participants
            WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Payments visible to payer and payee
CREATE POLICY payments_parties_access ON payments
    FOR ALL USING (
        payer_id = current_setting('app.current_user_id')::UUID OR
        payee_id = current_setting('app.current_user_id')::UUID
    );

-- ============================================
-- 11. VIEWS FOR COMMON QUERIES
-- ============================================

-- Active projects view
CREATE VIEW active_projects AS
SELECT 
    p.*,
    c.company_name,
    c.logo_url as company_logo,
    c.verification_status as company_verification,
    COUNT(DISTINCT m.id) as microservices_count,
    COUNT(DISTINCT pr.id) as actual_proposals_count,
    MIN(pr.proposed_value) as min_proposal_value,
    MAX(pr.proposed_value) as max_proposal_value
FROM projects p
JOIN companies c ON p.company_id = c.id
LEFT JOIN microservices m ON m.project_id = p.id
LEFT JOIN proposals pr ON pr.microservice_id = m.id
WHERE p.status = 'published'
    AND p.deadline > CURRENT_DATE
GROUP BY p.id, c.company_name, c.logo_url, c.verification_status;

-- User profiles view
CREATE VIEW user_profiles AS
SELECT 
    u.id,
    u.email,
    u.user_type,
    u.status,
    u.created_at,
    u.last_login_at,
    c.company_name,
    c.cnpj,
    c.verification_status as company_verification,
    f.full_name,
    f.cpf,
    f.professional_title,
    f.hourly_rate,
    f.average_rating,
    f.level as freelancer_level
FROM users u
LEFT JOIN companies c ON c.user_id = u.id
LEFT JOIN freelancers f ON f.user_id = u.id;

-- Payment summary view
CREATE VIEW payment_summary AS
SELECT 
    p.id,
    p.asaas_payment_id,
    p.amount,
    p.status,
    p.payment_method,
    p.due_date,
    p.payment_date,
    c.title as contract_title,
    payer.email as payer_email,
    payee.email as payee_email,
    comp.company_name,
    free.full_name as freelancer_name
FROM payments p
JOIN contracts c ON p.contract_id = c.id
JOIN users payer ON p.payer_id = payer.id
JOIN users payee ON p.payee_id = payee.id
LEFT JOIN companies comp ON c.company_id = comp.id
LEFT JOIN freelancers free ON c.freelancer_id = free.id;

-- ============================================
-- 12. FUNCTIONS FOR COMMON OPERATIONS
-- ============================================

-- Function to get user's active role
CREATE OR REPLACE FUNCTION get_user_active_role(
    p_user_id UUID,
    p_context_type VARCHAR DEFAULT 'global',
    p_context_id UUID DEFAULT NULL
)
RETURNS TABLE (
    role_id UUID,
    role_name VARCHAR,
    permissions TEXT[],
    financial_permissions TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id,
        r.name,
        r.permissions,
        r.financial_permissions
    FROM user_roles ur
    JOIN roles r ON ur.role_id = r.id
    WHERE ur.user_id = p_user_id
        AND ur.is_active = TRUE
        AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
        AND ur.context_type = p_context_type
        AND (p_context_id IS NULL OR ur.context_id = p_context_id)
    ORDER BY r.level DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to check user permission
CREATE OR REPLACE FUNCTION check_user_permission(
    p_user_id UUID,
    p_resource VARCHAR,
    p_action VARCHAR,
    p_context_type VARCHAR DEFAULT 'global',
    p_context_id UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_permissions TEXT[];
    v_permission TEXT;
BEGIN
    -- Get user's permissions
    SELECT permissions INTO v_permissions
    FROM get_user_active_role(p_user_id, p_context_type, p_context_id);
    
    -- Check for wildcard permission
    IF '*' = ANY(v_permissions) THEN
        RETURN TRUE;
    END IF;
    
    -- Check for resource wildcard
    v_permission := p_resource || '.*';
    IF v_permission = ANY(v_permissions) THEN
        RETURN TRUE;
    END IF;
    
    -- Check for specific permission
    v_permission := p_resource || '.' || p_action;
    IF v_permission = ANY(v_permissions) THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to create contract from accepted proposal
CREATE OR REPLACE FUNCTION create_contract_from_proposal(
    p_proposal_id UUID,
    p_terms_and_conditions TEXT,
    p_payment_schedule JSONB
)
RETURNS UUID AS $$
DECLARE
    v_contract_id UUID;
    v_proposal proposals%ROWTYPE;
    v_microservice microservices%ROWTYPE;
    v_project projects%ROWTYPE;
    v_contract_number VARCHAR(50);
    v_platform_fee DECIMAL(15, 2);
    v_net_value DECIMAL(15, 2);
BEGIN
    -- Get proposal details
    SELECT * INTO v_proposal FROM proposals WHERE id = p_proposal_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Proposal not found';
    END IF;
    
    -- Get microservice details
    SELECT * INTO v_microservice FROM microservices WHERE id = v_proposal.microservice_id;
    
    -- Get project details
    SELECT * INTO v_project FROM projects WHERE id = v_microservice.project_id;
    
    -- Generate contract number
    v_contract_number := 'CTR-' || TO_CHAR(CURRENT_DATE, 'YYYYMM') || '-' || 
                        LPAD(NEXTVAL('contract_number_seq')::TEXT, 6, '0');
    
    -- Calculate fees
    SELECT platform_fee, net_amount INTO v_platform_fee, v_net_value
    FROM calculate_platform_fee(v_proposal.proposed_value);
    
    -- Create contract
    INSERT INTO contracts (
        proposal_id,
        project_id,
        microservice_id,
        company_id,
        freelancer_id,
        contract_number,
        title,
        total_value,
        platform_fee_percentage,
        platform_fee_amount,
        freelancer_net_value,
        start_date,
        end_date,
        terms_and_conditions,
        payment_schedule,
        payment_method,
        status
    ) VALUES (
        p_proposal_id,
        v_project.id,
        v_microservice.id,
        v_project.company_id,
        v_proposal.freelancer_id,
        v_contract_number,
        v_microservice.title,
        v_proposal.proposed_value,
        10.00, -- Default platform fee percentage
        v_platform_fee,
        v_net_value,
        CURRENT_DATE,
        v_proposal.delivery_date,
        p_terms_and_conditions,
        p_payment_schedule,
        v_project.payment_method_preference[1], -- Use first preferred method
        'pending_signatures'
    ) RETURNING id INTO v_contract_id;
    
    -- Update proposal status
    UPDATE proposals 
    SET status = 'accepted'
    WHERE id = p_proposal_id;
    
    -- Update microservice status
    UPDATE microservices
    SET status = 'in_progress',
        assigned_freelancer_id = v_proposal.freelancer_id
    WHERE id = v_proposal.microservice_id;
    
    RETURN v_contract_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 13. INITIAL DATA
-- ============================================

-- Insert ASAAS default settings
INSERT INTO asaas_settings (setting_key, setting_value, environment) VALUES
('api_key', 'YOUR_API_KEY_HERE', 'production'),
('webhook_url', 'https://yourdomain.com/webhooks/asaas', 'production'),
('default_payment_methods', '["pix", "boleto", "credit_card"]', 'production'),
('platform_fee_percentage', '10.00', 'production'),
('transfer_schedule', '{"type": "daily", "hour": 18}', 'production'),
('notification_settings', '{"email": true, "webhook": true}', 'production');

-- Insert ASAAS default fees
INSERT INTO asaas_fees (payment_method, fee_type, fee_value, effective_date) VALUES
('pix', 'PERCENTAGE', 0.99, CURRENT_DATE),
('boleto', 'FIXED', 2.50, CURRENT_DATE),
('credit_card', 'PERCENTAGE', 2.99, CURRENT_DATE),
('debit_card', 'PERCENTAGE', 2.49, CURRENT_DATE),
('bank_transfer', 'FIXED', 5.00, CURRENT_DATE);

-- Insert default roles
INSERT INTO roles (name, display_name, description, level, is_system_role, permissions, financial_permissions) VALUES
('super_admin', 'Super Administrator', 'Full system access', 10, TRUE, 
 ARRAY['*'], ARRAY['*']),

('platform_admin', 'Platform Administrator', 'Platform management without critical settings', 9, TRUE,
 ARRAY['users.*', 'projects.*', 'contracts.*', 'reviews.*', 'reports.*'],
 ARRAY['payments.read', 'payments.process', 'transfers.read', 'reports.*']),

('financial_admin', 'Financial Administrator', 'Financial operations management', 8, TRUE,
 ARRAY['payments.*', 'transfers.*', 'reports.financial', 'users.read'],
 ARRAY['*']),

('company_admin', 'Company Administrator', 'Full company account management', 5, TRUE,
 ARRAY['company.update', 'projects.*', 'contracts.*', 'users.invite', 'payments.create'],
 ARRAY['payments.create', 'payments.read', 'methods.manage']),

('company_user', 'Company User', 'Basic company user', 4, TRUE,
 ARRAY['projects.read', 'projects.create', 'contracts.read', 'messages.*'],
 ARRAY['payments.read']),

('freelancer_premium', 'Premium Freelancer', 'Freelancer with premium features', 3, TRUE,
 ARRAY['proposals.*', 'contracts.read', 'messages.*', 'analytics.advanced'],
 ARRAY['payments.read', 'transfers.read', 'receivables.anticipate']),

('freelancer', 'Freelancer', 'Basic freelancer', 2, TRUE,
 ARRAY['proposals.create', 'proposals.read', 'contracts.read', 'messages.*'],
 ARRAY['payments.read', 'transfers.read']);

-- Insert default skills
INSERT INTO skills (name, slug, category, description) VALUES
('JavaScript', 'javascript', 'Programming', 'JavaScript programming language'),
('Python', 'python', 'Programming', 'Python programming language'),
('React', 'react', 'Framework', 'React JavaScript library'),
('Node.js', 'nodejs', 'Runtime', 'Node.js JavaScript runtime'),
('PostgreSQL', 'postgresql', 'Database', 'PostgreSQL relational database'),
('Docker', 'docker', 'DevOps', 'Docker containerization'),
('AWS', 'aws', 'Cloud', 'Amazon Web Services'),
('UI/UX Design', 'ui-ux-design', 'Design', 'User Interface and Experience Design'),
('Mobile Development', 'mobile-development', 'Development', 'iOS and Android development'),
('Machine Learning', 'machine-learning', 'AI/ML', 'Machine Learning and AI');

-- Insert default badges
INSERT INTO badges (name, display_name, description, category, criteria, points_value) VALUES
('first_project', 'First Project', 'Completed your first project', 'milestone', 
 '{"type": "project_count", "value": 1, "operator": "gte"}', 10),
('five_star_freelancer', '5 Star Freelancer', 'Maintained 5-star average rating', 'achievement',
 '{"type": "average_rating", "value": 5, "operator": "eq", "min_projects": 5}', 50),
('quick_responder', 'Quick Responder', 'Average response time under 1 hour', 'achievement',
 '{"type": "response_time_hours", "value": 1, "operator": "lte"}', 20),
('top_earner', 'Top Earner', 'Earned over R$ 10,000', 'milestone',
 '{"type": "total_earned", "value": 10000, "operator": "gte"}', 100),
('verified_professional', 'Verified Professional', 'Completed profile verification', 'special',
 '{"type": "verification_status", "value": "verified", "operator": "eq"}', 30);

-- ============================================
-- 14. COMMENTS FOR DOCUMENTATION
-- ============================================

-- Table comments
COMMENT ON TABLE users IS 'Base authentication table for all platform users';
COMMENT ON TABLE companies IS 'Company profiles with business information and verification';
COMMENT ON TABLE freelancers IS 'Freelancer profiles with professional information and skills';
COMMENT ON TABLE projects IS 'Projects posted by companies seeking freelancers';
COMMENT ON TABLE microservices IS 'AI-decomposed project tasks that can be assigned to freelancers';
COMMENT ON TABLE proposals IS 'Freelancer proposals for microservices with pricing and timeline';
COMMENT ON TABLE contracts IS 'Formalized agreements between companies and freelancers';
COMMENT ON TABLE payments IS 'Payment records integrated with ASAAS payment gateway';
COMMENT ON TABLE asaas_customers IS 'Customer records synchronized with ASAAS payment system';
COMMENT ON TABLE asaas_webhooks IS 'Webhook events received from ASAAS for payment updates';
COMMENT ON TABLE asaas_settings IS 'Configuration settings for ASAAS integration';
COMMENT ON TABLE asaas_fees IS 'Fee structure for different payment methods in ASAAS';
COMMENT ON TABLE badges IS 'Achievement badges for gamification system';
COMMENT ON TABLE freelancer_badges IS 'Badges earned by freelancers';
COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all system actions';
COMMENT ON TABLE disputes IS 'Complete dispute management system for contracts and projects';
COMMENT ON TABLE escrow_accounts IS 'Detailed escrow account management for secure payments';
COMMENT ON TABLE lgpd_compliance IS 'LGPD compliance tracking for user data processing';
COMMENT ON TABLE data_breach_log IS 'Security breach incident tracking as required by LGPD';
COMMENT ON TABLE lgpd_requests IS 'User data requests under LGPD rights';
COMMENT ON TABLE github_integrations IS 'GitHub OAuth integration for developer profiles';
COMMENT ON TABLE codero_partnerships IS 'Partnership tracking with Codero platform';
COMMENT ON TABLE ai_requests IS 'AI service request logging and analytics';
COMMENT ON TABLE user_points IS 'Gamification points system for user engagement';
COMMENT ON TABLE achievements IS 'Achievement definitions for gamification';
COMMENT ON TABLE user_achievements IS 'User achievement tracking';
COMMENT ON TABLE leaderboards IS 'Competitive leaderboard configurations';
COMMENT ON TABLE leaderboard_entries IS 'Leaderboard rankings and scores';
COMMENT ON TABLE meetings IS 'Meeting scheduling and management';
COMMENT ON TABLE meeting_participants IS 'Meeting participant tracking';
COMMENT ON TABLE system_config IS 'System-wide configuration settings';
COMMENT ON TABLE feature_flags IS 'Feature toggle system for gradual rollouts';

-- Column comments
COMMENT ON COLUMN users.two_factor_secret IS 'TOTP secret for 2FA authentication (encrypted)';
COMMENT ON COLUMN users.asaas_customer_id IS 'Reference to ASAAS customer record';
COMMENT ON COLUMN users.lgpd_consent_date IS 'Date when user provided LGPD consent';
COMMENT ON COLUMN users.data_retention_period_days IS 'Data retention period in days for LGPD compliance';
COMMENT ON COLUMN companies.cnpj IS 'Brazilian company registration number (14 digits)';
COMMENT ON COLUMN companies.asaas_account_type IS 'ASAAS account type for companies (PJ)';
COMMENT ON COLUMN freelancers.cpf IS 'Brazilian individual taxpayer registry (11 digits)';
COMMENT ON COLUMN freelancers.bank_details IS 'Encrypted banking information for payments';
COMMENT ON COLUMN freelancers.pix_key IS 'Encrypted PIX key for instant payments';
COMMENT ON COLUMN freelancers.asaas_account_type IS 'ASAAS account type (PF for individual, MEI for micro-entrepreneur)';
COMMENT ON COLUMN freelancers.github_username IS 'GitHub username for integration';
COMMENT ON COLUMN freelancers.github_verified IS 'Whether GitHub account is verified';
COMMENT ON COLUMN freelancers.codero_partner_id IS 'Codero partnership identifier';
COMMENT ON COLUMN projects.ai_decomposition_confidence IS 'AI confidence score for project decomposition (0-1)';
COMMENT ON COLUMN payments.escrow_held IS 'Whether payment is held in escrow until work completion';
COMMENT ON COLUMN payments.escrow_milestone_id IS 'Reference to specific escrow milestone';
COMMENT ON COLUMN payments.split_payment_config IS 'Configuration for split payments between multiple parties';
COMMENT ON COLUMN asaas_customers.asaas_customer_id IS 'Unique customer ID in ASAAS payment system';
COMMENT ON COLUMN asaas_customers.customer_type IS 'FISICA for individuals, JURIDICA for companies';

-- ============================================
-- END OF DEMANDEI DATABASE SCHEMA
-- ============================================