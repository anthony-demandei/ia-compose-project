"""
Knowledge Sanitizer - Remove dados sensíveis e extrai apenas conhecimento técnico reutilizável.

Este módulo garante que apenas padrões técnicos e conhecimento generalizado
sejam armazenados na memória ZEP, protegendo dados privados dos clientes.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class DomainType(Enum):
    """Domínios de negócio genéricos."""

    ECOMMERCE = "ecommerce"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    LOGISTICS = "logistics"
    REAL_ESTATE = "real_estate"
    MARKETING = "marketing"
    GOVERNMENT = "government"
    MANUFACTURING = "manufacturing"
    GENERIC = "generic"


@dataclass
class SanitizedKnowledge:
    """Enhanced sanitized technical knowledge for ZEP storage - all terms standardized in English."""

    # Core project info (required fields first)
    domain: DomainType
    complexity_level: str  # "low", "medium", "high"

    # Technology & Infrastructure (required fields)
    tech_stack: List[str]
    libraries_frameworks: Dict[str, List[str]]  # categorized by purpose/language
    database_technologies: List[str]
    devops_tools: List[str]
    deployment_preferences: List[str]

    # Architecture & Patterns (required fields)
    architecture_patterns: List[str]
    design_patterns: List[str]
    business_patterns: List[str]

    # Integrations & APIs (required fields)
    payment_methods: List[str]  # comprehensive payment gateway knowledge
    api_integrations: Dict[str, List[str]]  # categorized API integrations
    integrations: List[str]  # legacy field, maintained for compatibility

    # Features & Requirements (required fields)
    common_features: List[str]
    security_patterns: List[str]
    performance_requirements: List[str]
    security_requirements: List[str]  # legacy field, maintained for compatibility

    # Optional fields (with defaults)
    estimated_timeline: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary for storage - all in English for universal understanding."""
        return {
            # Core project info
            "domain": self.domain.value,
            "complexity_level": self.complexity_level,
            "estimated_timeline": self.estimated_timeline,
            # Technology & Infrastructure
            "tech_stack": self.tech_stack,
            "libraries_frameworks": self.libraries_frameworks,
            "database_technologies": self.database_technologies,
            "devops_tools": self.devops_tools,
            "deployment_preferences": self.deployment_preferences,
            # Architecture & Patterns
            "architecture_patterns": self.architecture_patterns,
            "design_patterns": self.design_patterns,
            "business_patterns": self.business_patterns,
            # Integrations & APIs
            "payment_methods": self.payment_methods,
            "api_integrations": self.api_integrations,
            "integrations": self.integrations,
            # Features & Requirements
            "common_features": self.common_features,
            "security_patterns": self.security_patterns,
            "performance_requirements": self.performance_requirements,
            "security_requirements": self.security_requirements,
        }


class KnowledgeSanitizer:
    """
    Sanitiza dados de projetos, extraindo apenas conhecimento técnico reutilizável.
    Remove todas as informações sensíveis e específicas dos clientes.
    """

    def __init__(self):
        """Inicializa o sanitizador com padrões e vocabulários técnicos."""

        # === COMPREHENSIVE LIBRARIES & FRAMEWORKS BY CATEGORY ===
        self.libraries_frameworks = {
            # Frontend Frameworks & Libraries
            "frontend": [
                # Core Frameworks
                "react",
                "vue",
                "angular",
                "svelte",
                "solid-js",
                "preact",
                "next.js",
                "nuxt.js",
                "sveltekit",
                "gatsby",
                "remix",
                # UI Component Libraries
                "material-ui",
                "ant-design",
                "chakra-ui",
                "mantine",
                "semantic-ui",
                "bootstrap",
                "tailwind",
                "bulma",
                "foundation",
                "primer",
                "react-bootstrap",
                "vue-bootstrap",
                "ng-bootstrap",
                # State Management
                "redux",
                "mobx",
                "zustand",
                "recoil",
                "jotai",
                "valtio",
                "vuex",
                "pinia",
                "ngrx",
                "akita",
                "elf",
                # Styling Solutions
                "styled-components",
                "emotion",
                "stitches",
                "vanilla-extract",
                "css-modules",
                "sass",
                "less",
                "stylus",
                "postcss",
            ],
            # Backend Frameworks & Libraries
            "backend": [
                # Node.js
                "express",
                "fastify",
                "koa",
                "nestjs",
                "hapi",
                "restify",
                "socket.io",
                "ws",
                "graphql",
                "apollo-server",
                # Python
                "django",
                "flask",
                "fastapi",
                "tornado",
                "pyramid",
                "bottle",
                "celery",
                "rq",
                "dramatiq",
                "uvicorn",
                "gunicorn",
                # Java
                "spring",
                "spring-boot",
                "quarkus",
                "micronaut",
                "vertx",
                "hibernate",
                "mybatis",
                "jooq",
                # C#/.NET
                "asp.net",
                "asp.net-core",
                "entity-framework",
                "dapper",
                "hangfire",
                "mediatr",
                "automapper",
                # PHP
                "laravel",
                "symfony",
                "codeigniter",
                "cakephp",
                "phalcon",
                "doctrine",
                "eloquent",
                "propel",
                # Go
                "gin",
                "echo",
                "fiber",
                "chi",
                "mux",
                "gorm",
                "beego",
                # Rust
                "actix-web",
                "rocket",
                "warp",
                "axum",
                "tide",
                "diesel",
            ],
            # Mobile Development
            "mobile": [
                # Cross-platform
                "react-native",
                "flutter",
                "ionic",
                "cordova",
                "capacitor",
                "xamarin",
                "maui",
                "unity",
                "expo",
                # Native iOS
                "swift",
                "objective-c",
                "swiftui",
                "uikit",
                "core-data",
                "alamofire",
                "snapkit",
                "realm-swift",
                # Native Android
                "kotlin",
                "java",
                "jetpack-compose",
                "android-sdk",
                "retrofit",
                "room",
                "dagger",
                "koin",
            ],
            # Database Libraries & ORMs
            "database": [
                # SQL Databases
                "postgresql",
                "mysql",
                "sqlite",
                "mssql",
                "oracle",
                # NoSQL Databases
                "mongodb",
                "redis",
                "cassandra",
                "couchdb",
                "neo4j",
                # ORMs & Query Builders
                "prisma",
                "typeorm",
                "sequelize",
                "knex",
                "mongoose",
                "sqlalchemy",
                "django-orm",
                "hibernate",
                "entity-framework",
                "eloquent",
                "active-record",
                "gorm",
                "diesel",
            ],
            # Testing Frameworks
            "testing": [
                # Unit Testing
                "jest",
                "vitest",
                "mocha",
                "jasmine",
                "qunit",
                "pytest",
                "unittest",
                "nose2",
                "junit",
                "testng",
                "nunit",
                "xunit",
                "phpunit",
                "go-test",
                # Integration & E2E Testing
                "cypress",
                "playwright",
                "selenium",
                "puppeteer",
                "webdriver",
                "testcafe",
                "codeceptjs",
                # API Testing
                "supertest",
                "postman",
                "insomnia",
                "rest-assured",
            ],
            # DevOps & Infrastructure
            "devops": [
                # Containerization
                "docker",
                "podman",
                "containerd",
                "buildah",
                # Orchestration
                "kubernetes",
                "docker-compose",
                "docker-swarm",
                "nomad",
                # Infrastructure as Code
                "terraform",
                "pulumi",
                "ansible",
                "chef",
                "puppet",
                "cloudformation",
                "arm-templates",
                "helm",
                # CI/CD
                "jenkins",
                "github-actions",
                "gitlab-ci",
                "circleci",
                "travis-ci",
                "azure-devops",
                "bamboo",
                "teamcity",
                # Monitoring & Logging
                "prometheus",
                "grafana",
                "elk-stack",
                "datadog",
                "new-relic",
                "sentry",
                "jaeger",
                "zipkin",
            ],
        }

        # === DATABASE TECHNOLOGIES (Detailed) ===
        self.database_technologies = {
            # Relational Databases
            "postgresql",
            "mysql",
            "mariadb",
            "sqlite",
            "mssql",
            "oracle",
            "db2",
            "cockroachdb",
            "yugabytedb",
            # NoSQL Document Databases
            "mongodb",
            "couchdb",
            "amazon-documentdb",
            "azure-cosmosdb",
            # Key-Value Stores
            "redis",
            "memcached",
            "amazon-dynamodb",
            "riak",
            # Column Family
            "cassandra",
            "hbase",
            "amazon-keyspaces",
            # Graph Databases
            "neo4j",
            "arangodb",
            "amazon-neptune",
            "dgraph",
            # Time Series
            "influxdb",
            "timescaledb",
            "prometheus-tsdb",
            # Search Engines
            "elasticsearch",
            "solr",
            "amazon-opensearch",
            "algolia",
            # Cloud Databases
            "firebase-firestore",
            "supabase",
            "planetscale",
            "neon",
            "railway-db",
            "aiven",
            "mongodb-atlas",
        }

        # === DEVOPS & INFRASTRUCTURE TOOLS ===
        self.devops_tools = {
            # Container Technologies
            "docker",
            "podman",
            "buildah",
            "kaniko",
            "img",
            # Container Orchestration
            "kubernetes",
            "docker-swarm",
            "nomad",
            "mesos",
            "rancher",
            "openshift",
            "eks",
            "gke",
            "aks",
            # Infrastructure as Code
            "terraform",
            "pulumi",
            "ansible",
            "chef",
            "puppet",
            "saltstack",
            "cloudformation",
            "arm-templates",
            # CI/CD Platforms
            "jenkins",
            "github-actions",
            "gitlab-ci",
            "circleci",
            "travis-ci",
            "azure-devops",
            "bamboo",
            "teamcity",
            "drone",
            "tekton",
            "argo-cd",
            "flux",
            # Monitoring & Observability
            "prometheus",
            "grafana",
            "jaeger",
            "zipkin",
            "datadog",
            "new-relic",
            "dynatrace",
            "splunk",
            "elk-stack",
            "fluentd",
            "telegraf",
            "collectd",
            # Service Mesh
            "istio",
            "linkerd",
            "consul-connect",
            "envoy",
            # Package Managers & Registries
            "helm",
            "kustomize",
            "docker-registry",
            "harbor",
            "nexus",
            "artifactory",
            "npm",
            "yarn",
            "pip",
            "maven",
        }

        # === SECURITY PATTERNS & STANDARDS ===
        self.security_patterns = {
            # Authentication Patterns
            "oauth2",
            "openid-connect",
            "saml",
            "jwt",
            "session-based",
            "token-based",
            "api-key",
            "basic-auth",
            "digest-auth",
            # Authorization Patterns
            "rbac",
            "abac",
            "acl",
            "pbac",
            "resource-based",
            "role-based",
            "permission-based",
            "claim-based",
            # Encryption & Cryptography
            "aes",
            "rsa",
            "ecc",
            "tls",
            "ssl",
            "https",
            "hashing",
            "bcrypt",
            "scrypt",
            "argon2",
            "pbkdf2",
            "hmac",
            # Security Standards & Compliance
            "gdpr",
            "hipaa",
            "pci-dss",
            "sox",
            "iso-27001",
            "nist",
            "owasp",
            "cis",
            "fido2",
            "webauthn",
            # Security Patterns
            "zero-trust",
            "defense-in-depth",
            "least-privilege",
            "fail-secure",
            "secure-by-default",
            "input-validation",
            "output-encoding",
            "csrf-protection",
            "xss-protection",
            # API Security
            "rate-limiting",
            "throttling",
            "api-gateway",
            "cors",
            "content-security-policy",
            "hsts",
            "certificate-pinning",
        }

        # Legacy technologies field (maintained for compatibility)
        self.technologies = {
            # Frontend
            "react",
            "vue",
            "angular",
            "svelte",
            "next.js",
            "nuxt.js",
            "typescript",
            "javascript",
            "html",
            "css",
            "tailwind",
            "bootstrap",
            "material-ui",
            "ant-design",
            # Backend
            "node.js",
            "python",
            "java",
            "c#",
            "php",
            "go",
            "rust",
            "django",
            "flask",
            "fastapi",
            "express",
            "nestjs",
            "spring",
            "laravel",
            "asp.net",
            # Database
            "postgresql",
            "mysql",
            "mongodb",
            "redis",
            "sqlite",
            "cassandra",
            "dynamodb",
            "firebase",
            "supabase",
            # Cloud & Infrastructure
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "terraform",
            "nginx",
            "apache",
            "cloudflare",
            # Mobile
            "react-native",
            "flutter",
            "ionic",
            "swift",
            "kotlin",
            "xamarin",
        }

        # === COMPREHENSIVE DESIGN PATTERNS ===
        self.design_patterns = {
            # Creational Patterns
            "factory",
            "abstract-factory",
            "builder",
            "prototype",
            "singleton",
            "object-pool",
            "lazy-initialization",
            "dependency-injection",
            # Structural Patterns
            "adapter",
            "bridge",
            "composite",
            "decorator",
            "facade",
            "flyweight",
            "proxy",
            "module",
            "mixin",
            "private-class-data",
            # Behavioral Patterns
            "chain-of-responsibility",
            "command",
            "interpreter",
            "iterator",
            "mediator",
            "memento",
            "observer",
            "state",
            "strategy",
            "template-method",
            "visitor",
            "null-object",
            "blackboard",
            "specification",
            # Concurrency Patterns
            "active-object",
            "monitor",
            "reactor",
            "thread-pool",
            "producer-consumer",
            "readers-writer",
            "scheduler",
            # Architectural Patterns
            "mvc",
            "mvp",
            "mvvm",
            "model-view-presenter",
            "model-view-adapter",
            # Enterprise Patterns
            "repository",
            "unit-of-work",
            "data-mapper",
            "active-record",
            "service-layer",
            "domain-service",
            "application-service",
            "value-object",
            "entity",
            "aggregate",
            "factory-pattern",
        }

        # === COMPREHENSIVE ARCHITECTURE PATTERNS ===
        self.architecture_patterns = {
            # Monolithic Patterns
            "monolith",
            "modular-monolith",
            "layered-architecture",
            # Distributed Patterns
            "microservices",
            "service-mesh",
            "api-gateway",
            "bff",
            "strangler-fig",
            "anti-corruption-layer",
            # Event-Driven Patterns
            "event-driven",
            "event-sourcing",
            "cqrs",
            "saga",
            "event-streaming",
            "pub-sub",
            "message-queue",
            # Cloud Patterns
            "serverless",
            "faas",
            "cloud-native",
            "twelve-factor",
            "circuit-breaker",
            "bulkhead",
            "retry",
            "timeout",
            "rate-limiting",
            "load-balancer",
            "auto-scaling",
            # Data Patterns
            "database-per-service",
            "shared-database",
            "data-lake",
            "lambda-architecture",
            "kappa-architecture",
            "polyglot-persistence",
            # Frontend Patterns
            "jamstack",
            "spa",
            "ssr",
            "ssg",
            "mpa",
            "micro-frontends",
            "progressive-web-app",
            "headless-architecture",
            # Domain-Driven Design
            "clean-architecture",
            "hexagonal",
            "onion-architecture",
            "domain-driven-design",
            "bounded-context",
            "ubiquitous-language",
        }

        # === BUSINESS LOGIC PATTERNS BY DOMAIN ===
        self.business_patterns = {
            # E-commerce Patterns
            "shopping-cart",
            "checkout-process",
            "payment-gateway",
            "inventory-management",
            "order-fulfillment",
            "product-catalog",
            "pricing-engine",
            "discount-system",
            "loyalty-program",
            "recommendation-engine",
            "search-faceting",
            "wishlist",
            # Fintech Patterns
            "double-entry-bookkeeping",
            "transaction-processing",
            "fraud-detection",
            "kyc-verification",
            "aml-compliance",
            "risk-assessment",
            "payment-orchestration",
            "wallet-system",
            "loan-origination",
            "trading-engine",
            "settlement-system",
            "regulatory-reporting",
            # Healthcare Patterns
            "patient-management",
            "appointment-scheduling",
            "medical-records",
            "billing-system",
            "insurance-claims",
            "prescription-management",
            "telemedicine",
            "hipaa-compliance",
            "hl7-integration",
            # SaaS Patterns
            "multi-tenancy",
            "tenant-isolation",
            "subscription-billing",
            "usage-metering",
            "feature-flagging",
            "a-b-testing",
            "onboarding-flow",
            "trial-management",
            "churn-prevention",
            # Enterprise Patterns
            "workflow-engine",
            "approval-process",
            "document-management",
            "reporting-system",
            "analytics-dashboard",
            "audit-trail",
            "role-based-access",
            "single-sign-on",
            "data-synchronization",
        }

        # Features comuns
        self.common_features = {
            "authentication",
            "authorization",
            "user-management",
            "payment-integration",
            "notification-system",
            "search",
            "reporting",
            "analytics",
            "dashboard",
            "admin-panel",
            "file-upload",
            "real-time-updates",
            "chat",
            "messaging",
            "inventory-management",
            "order-management",
            "cms",
            "e-commerce",
            "booking-system",
            "calendar",
            "scheduling",
            "geolocation",
            "maps-integration",
            "social-login",
            "multi-tenancy",
            "internationalization",
            "audit-log",
        }

        # === COMPREHENSIVE PAYMENT METHODS & FINANCIAL APIS ===
        self.payment_methods = {
            # Global Payment Processors
            "stripe",
            "paypal",
            "square",
            "braintree",
            "adyen",
            "worldpay",
            "authorize-net",
            "2checkout",
            "razorpay",
            "payu",
            # Regional Payment Gateways
            "mercadopago",
            "pagseguro",
            "cielo",
            "rede",
            "getnet",
            "stone",  # Brazil
            "alipay",
            "wechat-pay",
            "unionpay",  # China
            "sofort",
            "giropay",
            "ideal",
            "bancontact",  # Europe
            "paytm",
            "phonepe",
            "gpay-india",  # India
            # Digital Wallets
            "apple-pay",
            "google-pay",
            "samsung-pay",
            "paypal-wallet",
            "amazon-pay",
            "shop-pay",
            "klarna",
            "afterpay",
            # Cryptocurrency Payments
            "coinbase",
            "bitpay",
            "crypto-com",
            "binance-pay",
            "metamask",
            "wallet-connect",
            "web3-payments",
            # Buy Now Pay Later (BNPL)
            "klarna",
            "affirm",
            "sezzle",
            "quadpay",
            "zip",
            "laybuy",
            # Banking & Open Banking
            "plaid",
            "yodlee",
            "tink",
            "truelayer",
            "belvo",
            "pix",
            "ted",
            "doc",
            "boleto",  # Brazil banking
            "sepa",
            "ach",
            "wire-transfer",
            "direct-debit",
            # Business & B2B Payments
            "bill-com",
            "melio",
            "corpay",
            "payoneer",
            "wise-business",
            "tipalti",
            "nium",
            "flywire",
        }

        # === COMPREHENSIVE API INTEGRATIONS BY CATEGORY ===
        self.api_integrations = {
            # Communication APIs
            "communication": [
                "sendgrid",
                "mailgun",
                "aws-ses",
                "mailchimp",
                "constant-contact",
                "twilio",
                "vonage",
                "messagebird",
                "sinch",
                "bandwidth",
                "telegram-bot",
                "whatsapp-business",
                "slack-api",
                "discord-bot",
                "firebase-messaging",
                "onesignal",
                "pusher",
                "socket-io",
            ],
            # Social Media APIs
            "social": [
                "facebook-graph",
                "instagram-basic",
                "twitter-api",
                "linkedin-api",
                "youtube-api",
                "tiktok-api",
                "snapchat-api",
                "pinterest-api",
                "reddit-api",
                "discord-api",
                "telegram-api",
                "whatsapp-api",
            ],
            # Cloud Services APIs
            "cloud": [
                "aws-sdk",
                "azure-sdk",
                "gcp-sdk",
                "cloudflare-api",
                "s3",
                "cloudfront",
                "lambda",
                "ec2",
                "rds",
                "azure-functions",
                "azure-blob",
                "cosmosdb",
                "google-cloud-storage",
                "bigquery",
                "cloud-functions",
            ],
            # Business & CRM APIs
            "business": [
                "salesforce-api",
                "hubspot-api",
                "pipedrive-api",
                "zoho-crm",
                "monday-com",
                "asana-api",
                "trello-api",
                "notion-api",
                "quickbooks-api",
                "xero-api",
                "sage-api",
                "netsuite-api",
                "shopify-api",
                "woocommerce-api",
                "magento-api",
            ],
            # Analytics & Monitoring APIs
            "analytics": [
                "google-analytics",
                "mixpanel",
                "amplitude",
                "segment",
                "hotjar",
                "fullstory",
                "logrocket",
                "sentry",
                "datadog",
                "new-relic",
                "splunk",
                "elastic-apm",
                "prometheus",
                "grafana-api",
                "pagerduty-api",
            ],
            # Maps & Location APIs
            "location": [
                "google-maps",
                "mapbox",
                "here-maps",
                "openstreetmap",
                "foursquare-api",
                "yelp-api",
                "geocoding-api",
                "weather-api",
                "timezone-api",
            ],
            # Logistics & Shipping APIs
            "logistics": [
                "ups-api",
                "fedex-api",
                "dhl-api",
                "usps-api",
                "correios-api",
                "shipstation",
                "easypost",
                "shippo",
                "uber-api",
                "lyft-api",
                "door-dash-api",
            ],
            # Authentication & Identity APIs
            "identity": [
                "auth0",
                "okta",
                "firebase-auth",
                "cognito",
                "keycloak",
                "ping-identity",
                "onelogin",
                "google-oauth",
                "facebook-login",
                "github-oauth",
                "linkedin-oauth",
                "microsoft-oauth",
            ],
            # Document & File APIs
            "documents": [
                "docusign-api",
                "adobe-sign",
                "pandadoc-api",
                "google-drive-api",
                "dropbox-api",
                "box-api",
                "onedrive-api",
                "aws-s3-api",
                "cloudinary-api",
            ],
            # AI & ML APIs
            "ai_ml": [
                "openai-api",
                "anthropic-api",
                "huggingface-api",
                "google-ai",
                "azure-cognitive",
                "aws-ai-services",
                "tensorflow-serving",
                "pytorch-serve",
                "mlflow-api",
            ],
        }

        # Legacy integrations field (maintained for compatibility)
        self.integrations = {
            "stripe",
            "paypal",
            "mercadopago",
            "pagseguro",
            "correios",
            "fedex",
            "dhl",
            "ups",
            "sendgrid",
            "mailgun",
            "aws-ses",
            "twilio",
            "google-analytics",
            "mixpanel",
            "hotjar",
            "slack",
            "discord",
            "whatsapp",
            "telegram",
            "salesforce",
            "hubspot",
            "pipedrive",
            "zendesk",
            "intercom",
            "freshdesk",
        }

        # Palavras que indicam dados sensíveis (devem ser removidas)
        self.sensitive_indicators = {
            # Nomes e identificadores
            "ltda",
            "s.a.",
            "me",
            "eireli",
            "company",
            "corp",
            "inc",
            # Localizações específicas
            "rua",
            "avenida",
            "av.",
            "street",
            "road",
            "bairro",
            # Dados pessoais
            "nome",
            "email",
            "telefone",
            "cpf",
            "cnpj",
            "rg",
            # Valores específicos
            "r$",
            "$",
            "euro",
            "reais",
            "milhão",
            "million",
            # Nomes próprios (padrões comuns)
            "hospital",
            "clínica",
            "escola",
            "universidade",
            "banco",
            "empresa",
            "cliente",
            "customer",
        }

        # === COMPREHENSIVE PORTUGUESE → ENGLISH MAPPING ===
        # All terms stored in ZEP will be in English for universal understanding
        self.portuguese_to_english_mapping = {
            # Payment & Financial Terms
            "pagamentos": "payment-integration",
            "pagamento": "payment-integration",
            "gateway de pagamento": "payment-gateway",
            "cartão": "credit-card",
            "cartão de crédito": "credit-card",
            "cartão de débito": "debit-card",
            "pix": "pix",
            "boleto": "boleto",
            "transferência": "bank-transfer",
            "transação": "transaction",
            "financeiro": "financial",
            "faturamento": "billing-system",
            "cobrança": "billing",
            "subscription": "subscription-billing",
            "assinatura": "subscription-billing",
            # E-commerce Terms
            "e-commerce": "ecommerce",
            "loja online": "ecommerce",
            "carrinho": "shopping-cart",
            "checkout": "checkout-process",
            "estoque": "inventory-management",
            "produto": "product-catalog",
            "pedido": "order-management",
            "pedidos": "order-management",
            "marketplace": "marketplace",
            "catálogo": "product-catalog",
            # Authentication & Security
            "autenticação": "authentication",
            "autorização": "authorization",
            "login": "authentication",
            "usuários": "user-management",
            "usuarios": "user-management",
            "gestão de usuários": "user-management",
            "permissões": "authorization",
            "segurança": "security-patterns",
            "criptografia": "encryption",
            # Technical Infrastructure
            "banco de dados": "database",
            "servidor": "server",
            "nuvem": "cloud",
            "hospedagem": "hosting",
            "deploy": "deployment",
            "implantação": "deployment",
            "monitoramento": "monitoring",
            "logs": "logging",
            "backup": "backup",
            "cache": "caching",
            # Frontend Terms
            "interface": "user-interface",
            "tela": "screen",
            "página": "page",
            "site": "website",
            "aplicativo": "application",
            "app": "application",
            "mobile": "mobile",
            "responsivo": "responsive-design",
            "design": "ui-design",
            # Backend Terms
            "api": "api",
            "serviço": "service",
            "microserviços": "microservices",
            "microsserviços": "microservices",
            "integração": "integration",
            "webhook": "webhook",
            "jobs": "background-jobs",
            "filas": "message-queue",
            "processamento": "data-processing",
            # Business Logic
            "relatórios": "reporting-system",
            "dashboard": "analytics-dashboard",
            "painel": "dashboard",
            "notificações": "notification-system",
            "email": "email-system",
            "sms": "sms-integration",
            "chat": "chat-system",
            "mensagens": "messaging",
            "upload": "file-upload",
            "download": "file-download",
            # Healthcare Specific
            "saúde": "healthcare",
            "médico": "medical",
            "hospital": "hospital-management",
            "paciente": "patient-management",
            "consulta": "appointment-scheduling",
            "prontuário": "medical-records",
            "exame": "medical-examination",
            "telemedicina": "telemedicine",
            # Education Specific
            "educação": "education",
            "escola": "school-management",
            "aluno": "student-management",
            "professor": "teacher-management",
            "curso": "course-management",
            "lms": "learning-management-system",
            # Real Estate Specific
            "imóvel": "real-estate",
            "propriedade": "property-management",
            "aluguel": "rental-system",
            "locação": "rental-system",
            "corretor": "broker-system",
            # Logistics Specific
            "logística": "logistics",
            "entrega": "delivery-system",
            "transporte": "transportation",
            "rastreamento": "tracking-system",
            # "estoque": "inventory-management",  # Duplicate removed
            "armazém": "warehouse-management",
            # Technology Stack Terms
            "frontend": "frontend",
            "backend": "backend",
            "full-stack": "full-stack",
            "react": "react",
            "node": "nodejs",
            "python": "python",
            "java": "java",
            "javascript": "javascript",
            "typescript": "typescript",
            "php": "php",
            "go": "golang",
            "rust": "rust",
            "flutter": "flutter",
            # Architecture Terms
            "arquitetura": "architecture-patterns",
            "padrão": "design-patterns",
            "padrões": "design-patterns",
            "estrutura": "architecture",
            "organização": "project-structure",
            "modular": "modular-architecture",
            # Performance & Scalability
            "performance": "performance-optimization",
            "otimização": "optimization",
            "escalabilidade": "scalability",
            "alta disponibilidade": "high-availability",
            "load balancer": "load-balancing",
            "cdn": "content-delivery-network",
            # DevOps Terms
            "docker": "docker",
            "kubernetes": "kubernetes",
            "ci/cd": "continuous-integration",
            "integração contínua": "continuous-integration",
            "deploy contínuo": "continuous-deployment",
            "terraform": "terraform",
            "ansible": "ansible",
            # Time & Project Management
            "urgente": "urgent",
            "rápido": "quick-delivery",
            "prazo": "timeline",
            "cronograma": "project-schedule",
            # "entrega": "delivery",  # Duplicate removed
            "milestone": "milestone",
            "mvp": "minimum-viable-product",
        }

        # Mapeamento de domínios por palavras-chave
        self.domain_keywords = {
            DomainType.ECOMMERCE: [
                "e-commerce",
                "loja",
                "venda",
                "produto",
                "carrinho",
                "checkout",
                "pagamento",
                "estoque",
                "marketplace",
            ],
            DomainType.FINTECH: [
                "financeiro",
                "banco",
                "pagamento",
                "cartão",
                "pix",
                "transferência",
                "investimento",
                "empréstimo",
                "crédito",
            ],
            DomainType.HEALTHCARE: [
                "saúde",
                "médico",
                "hospital",
                "clínica",
                "paciente",
                "prontuário",
                "exame",
                "consulta",
                "telemedicina",
                "leitos",
                "enfermaria",
                "uti",
                "cirurgia",
                "emergência",
                "sistema hospitalar",
                "gestão hospitalar",
                "healthcare",
            ],
            DomainType.EDUCATION: [
                "educação",
                "escola",
                "universidade",
                "curso",
                "aluno",
                "professor",
                "lms",
                "e-learning",
                "ead",
            ],
            DomainType.LOGISTICS: [
                "logística",
                "entrega",
                "transporte",
                "estoque",
                "armazém",
                "distribuição",
                "rastreamento",
            ],
            DomainType.REAL_ESTATE: [
                "imóvel",
                "apartamento",
                "casa",
                "aluguel",
                "venda",
                "corretor",
                "imobiliária",
                "propriedade",
            ],
        }

    def sanitize_project_description(self, description: str) -> Optional[SanitizedKnowledge]:
        """
        Sanitiza descrição do projeto, extraindo apenas conhecimento técnico.

        Args:
            description: Descrição original do projeto

        Returns:
            Conhecimento sanitizado ou None se não houver informação técnica suficiente
        """
        if not description or len(description.strip()) < 10:
            return None

        try:
            # Converter para lowercase para análise
            clean_text = description.lower()

            # Remover dados potencialmente sensíveis
            sanitized_text = self._remove_sensitive_data(clean_text)

            # Extrair componentes técnicos
            domain = self._extract_domain(sanitized_text)
            tech_stack = self._extract_technologies(sanitized_text)
            architecture = self._extract_architecture_patterns(sanitized_text)
            features = self._extract_features(sanitized_text)
            integrations = self._extract_integrations(sanitized_text)
            complexity = self._assess_complexity(sanitized_text, tech_stack, features)
            deployment = self._extract_deployment_preferences(sanitized_text)
            security = self._extract_security_requirements(sanitized_text)
            performance = self._extract_performance_requirements(sanitized_text)
            timeline = self._extract_timeline_patterns(sanitized_text)

            # Só retornar se houver informação técnica mínima
            if not tech_stack and not features and not integrations:
                logger.debug("Insufficient technical information to create sanitized knowledge")
                return None

            # Extract enhanced categories using new comprehensive vocabularies
            payment_methods = self._extract_payment_methods(sanitized_text)
            api_integrations = self._extract_api_integrations(sanitized_text)
            design_patterns = self._extract_design_patterns(sanitized_text)
            libraries_frameworks = self._extract_libraries_frameworks(sanitized_text)
            database_technologies = self._extract_database_technologies(sanitized_text)
            devops_tools = self._extract_devops_tools(sanitized_text)
            security_patterns = self._extract_security_patterns(sanitized_text)
            business_patterns = self._extract_business_patterns(sanitized_text)

            sanitized_knowledge = SanitizedKnowledge(
                # Core project info (required fields first)
                domain=domain,
                complexity_level=complexity,
                # Technology & Infrastructure (required fields)
                tech_stack=tech_stack,
                libraries_frameworks=libraries_frameworks,
                database_technologies=database_technologies,
                devops_tools=devops_tools,
                deployment_preferences=deployment,
                # Architecture & Patterns (required fields)
                architecture_patterns=architecture,
                design_patterns=design_patterns,
                business_patterns=business_patterns,
                # Integrations & APIs (required fields)
                payment_methods=payment_methods,
                api_integrations=api_integrations,
                integrations=integrations,  # legacy field
                # Features & Requirements (required fields)
                common_features=features,
                security_patterns=security_patterns,
                performance_requirements=performance,
                security_requirements=security,  # legacy field
                # Optional fields
                estimated_timeline=timeline,
            )

            logger.info(
                f"Successfully sanitized project knowledge: {domain.value} domain, {len(tech_stack)} technologies"
            )
            return sanitized_knowledge

        except Exception as e:
            logger.error(f"Error sanitizing project description: {str(e)}")
            return None

    def sanitize_wizard_answers(self, answers: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Sanitiza respostas do wizard, extraindo apenas padrões técnicos.

        Args:
            answers: Respostas brutas do wizard

        Returns:
            Padrões técnicos extraídos das respostas
        """
        sanitized_patterns = {
            "technologies": [],
            "features": [],
            "integrations": [],
            "architecture": [],
            "deployment": [],
        }

        try:
            for question_id, answer in answers.items():
                if not answer:
                    continue

                # Converter resposta para texto analisável
                answer_text = self._normalize_answer_to_text(answer)
                clean_answer = answer_text.lower()

                # Extrair padrões técnicos da resposta
                sanitized_patterns["technologies"].extend(self._extract_technologies(clean_answer))
                sanitized_patterns["features"].extend(self._extract_features(clean_answer))
                sanitized_patterns["integrations"].extend(self._extract_integrations(clean_answer))
                sanitized_patterns["architecture"].extend(
                    self._extract_architecture_patterns(clean_answer)
                )
                sanitized_patterns["deployment"].extend(
                    self._extract_deployment_preferences(clean_answer)
                )

            # Remover duplicatas
            for key in sanitized_patterns:
                sanitized_patterns[key] = list(set(sanitized_patterns[key]))

            logger.info(f"Sanitized {len(answers)} wizard answers into technical patterns")
            return sanitized_patterns

        except Exception as e:
            logger.error(f"Error sanitizing wizard answers: {str(e)}")
            return sanitized_patterns

    def sanitize_project_scope(self, scope_text: str) -> Optional[Dict[str, List[str]]]:
        """
        Sanitiza escopo do projeto, extraindo apenas insights arquiteturais.

        Args:
            scope_text: Texto completo do escopo

        Returns:
            Insights arquiteturais sanitizados
        """
        if not scope_text or len(scope_text.strip()) < 50:
            return None

        try:
            clean_scope = scope_text.lower()

            # Remover dados específicos do cliente
            sanitized_scope = self._remove_sensitive_data(clean_scope)

            # Extrair padrões técnicos
            tech_choices = self._extract_technologies(sanitized_scope)
            arch_patterns = self._extract_architecture_patterns(sanitized_scope)
            integrations = self._extract_integrations(sanitized_scope)

            # Identificar decisões arquiteturais (deployment, cloud, etc.)
            deployment_keywords = [
                "aws",
                "docker",
                "kubernetes",
                "azure",
                "gcp",
                "heroku",
                "vercel",
            ]
            arch_decisions = [kw for kw in deployment_keywords if kw in sanitized_scope]
            arch_decisions.extend(arch_patterns)

            insights = {
                "technology_choices": tech_choices,
                "architectural_decisions": list(set(arch_decisions)),
                "integration_patterns": integrations,
                "security_measures": self._extract_security_requirements(sanitized_scope),
                "scalability_approaches": self._extract_performance_requirements(sanitized_scope),
            }

            # Filtrar insights vazios
            filtered_insights = {k: v for k, v in insights.items() if v}

            if not filtered_insights:
                return None

            logger.info(
                f"Extracted {len(filtered_insights)} types of architectural insights from scope"
            )
            return filtered_insights

        except Exception as e:
            logger.error(f"Error sanitizing project scope: {str(e)}")
            return None

    def _remove_sensitive_data(self, text: str) -> str:
        """Remove dados potencialmente sensíveis do texto."""
        sanitized = text

        # Remover padrões PII
        from app.utils.pii_safe_logging import PIISafeLogger

        pii_logger = PIISafeLogger("sanitizer")
        sanitized = pii_logger._mask_pii_patterns(sanitized)

        # Remover palavras indicadoras de dados sensíveis
        for indicator in self.sensitive_indicators:
            # Usar regex para remover palavras completas
            pattern = r"\b" + re.escape(indicator) + r"\b"
            sanitized = re.sub(pattern, "[REMOVED]", sanitized, flags=re.IGNORECASE)

        # Remover números específicos que podem ser valores, IDs, etc.
        sanitized = re.sub(r"\b\d{4,}\b", "[NUMBER]", sanitized)

        return sanitized

    def _extract_domain(self, text: str) -> DomainType:
        """Extrai domínio de negócio baseado em palavras-chave."""
        domain_scores = {}
        text_lower = text.lower()

        for domain_type, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                domain_scores[domain_type] = score

        if not domain_scores:
            return DomainType.GENERIC

        # Retornar domínio com maior pontuação
        return max(domain_scores, key=domain_scores.get)

    def _extract_technologies(self, text: str) -> List[str]:
        """Extrai tecnologias mencionadas no texto."""
        found_tech = []
        for tech in self.technologies:
            if tech in text:
                found_tech.append(tech)
        return found_tech

    def _extract_architecture_patterns(self, text: str) -> List[str]:
        """Extrai padrões de arquitetura mencionados."""
        found_patterns = []
        for pattern in self.architecture_patterns:
            if pattern in text or pattern.replace("-", " ") in text:
                found_patterns.append(pattern)
        return found_patterns

    def _extract_features(self, text: str) -> List[str]:
        """Extract common features mentioned in text, always returning English terms."""
        found_features = []
        text_lower = text.lower()

        # Direct feature matching
        for feature in self.common_features:
            feature_variations = [feature, feature.replace("-", " "), feature.replace("-", "_")]

            # Check direct English matches
            for variation in feature_variations:
                if variation in text_lower:
                    found_features.append(feature)
                    break

        # Use comprehensive Portuguese → English mapping for features
        for portuguese_term, english_term in self.portuguese_to_english_mapping.items():
            if portuguese_term in text_lower and english_term in self.common_features:
                if english_term not in found_features:
                    found_features.append(english_term)

        return list(set(found_features))  # Remove duplicates

    def _extract_integrations(self, text: str) -> List[str]:
        """Extrai integrações mencionadas."""
        found_integrations = []
        for integration in self.integrations:
            if integration in text:
                found_integrations.append(integration)
        return found_integrations

    def _assess_complexity(self, text: str, tech_stack: List[str], features: List[str]) -> str:
        """Avalia complexidade baseada em indicadores técnicos."""
        complexity_score = 0

        # Tecnologias aumentam complexidade
        complexity_score += len(tech_stack) * 0.5

        # Features aumentam complexidade
        complexity_score += len(features) * 0.3

        # Palavras indicadoras de alta complexidade
        high_complexity_words = [
            "microserviços",
            "microservices",
            "distributed",
            "real-time",
            "alta disponibilidade",
            "scalable",
            "machine learning",
            "ai",
            "blockchain",
            "big data",
            "analytics",
            "complex",
        ]

        for word in high_complexity_words:
            if word in text:
                complexity_score += 2

        # Classificar complexidade
        if complexity_score >= 8:
            return "high"
        elif complexity_score >= 4:
            return "medium"
        else:
            return "low"

    def _extract_deployment_preferences(self, text: str) -> List[str]:
        """Extrai preferências de deploy."""
        deployment_options = [
            "cloud",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "serverless",
            "on-premise",
            "hybrid",
            "saas",
            "paas",
        ]

        found_deployment = []
        for option in deployment_options:
            if option in text:
                found_deployment.append(option)

        return found_deployment

    def _extract_security_requirements(self, text: str) -> List[str]:
        """Extrai requisitos de segurança."""
        security_keywords = [
            "lgpd",
            "gdpr",
            "hipaa",
            "pci-dss",
            "ssl",
            "https",
            "authentication",
            "authorization",
            "encryption",
            "two-factor",
            "oauth",
            "jwt",
            "security",
            "compliance",
        ]

        found_security = []
        for keyword in security_keywords:
            if keyword in text:
                found_security.append(keyword)

        return found_security

    def _extract_performance_requirements(self, text: str) -> List[str]:
        """Extrai requisitos de performance."""
        performance_keywords = [
            "performance",
            "scalability",
            "load-balancing",
            "caching",
            "cdn",
            "optimization",
            "high-availability",
            "clustering",
            "auto-scaling",
            "monitoring",
        ]

        found_performance = []
        for keyword in performance_keywords:
            if keyword in text:
                found_performance.append(keyword)

        return found_performance

    def _extract_timeline_patterns(self, text: str) -> Optional[str]:
        """Extrai padrões de cronograma (sem valores específicos)."""
        if any(word in text for word in ["urgente", "urgent", "asap", "rápido"]):
            return "urgent"
        elif any(word in text for word in ["longo prazo", "long-term", "futuro"]):
            return "long-term"
        elif any(word in text for word in ["médio prazo", "medium-term"]):
            return "medium-term"
        else:
            return None

    # === NEW COMPREHENSIVE EXTRACTION METHODS ===

    def _extract_payment_methods(self, text: str) -> List[str]:
        """Extract payment methods and financial APIs from text, always in English."""
        found_payments = []
        text_lower = text.lower()

        # Direct matching from comprehensive payment methods
        for payment_method in self.payment_methods:
            if payment_method in text_lower:
                found_payments.append(payment_method)

        # Portuguese to English mapping for payments
        for portuguese_term, english_term in self.portuguese_to_english_mapping.items():
            if portuguese_term in text_lower and english_term.endswith(
                ("-integration", "-gateway", "-payment", "pix", "boleto")
            ):
                if english_term not in found_payments:
                    found_payments.append(english_term)

        return list(set(found_payments))

    def _extract_api_integrations(self, text: str) -> Dict[str, List[str]]:
        """Extract categorized API integrations from text."""
        found_integrations = {}
        text_lower = text.lower()

        # Search through all API categories
        for category, apis in self.api_integrations.items():
            found_apis = []
            for api in apis:
                if api in text_lower or api.replace("-", " ") in text_lower:
                    found_apis.append(api)

            if found_apis:
                found_integrations[category] = found_apis

        return found_integrations

    def _extract_design_patterns(self, text: str) -> List[str]:
        """Extract design patterns from text, always in English."""
        found_patterns = []
        text_lower = text.lower()

        for pattern in self.design_patterns:
            # Check direct matches and common variations
            if pattern in text_lower or pattern.replace("-", " ") in text_lower:
                found_patterns.append(pattern)

        # Check Portuguese mappings
        for portuguese_term, english_term in self.portuguese_to_english_mapping.items():
            if portuguese_term in text_lower and "pattern" in english_term:
                if english_term not in found_patterns:
                    found_patterns.append(english_term)

        return list(set(found_patterns))

    def _extract_libraries_frameworks(self, text: str) -> Dict[str, List[str]]:
        """Extract categorized libraries and frameworks from text."""
        found_libs = {}
        text_lower = text.lower()

        for category, libs in self.libraries_frameworks.items():
            found_category_libs = []
            for lib in libs:
                # Handle different naming patterns
                if (
                    lib in text_lower
                    or lib.replace("-", " ") in text_lower
                    or lib.replace(".", "") in text_lower
                ):
                    found_category_libs.append(lib)

            if found_category_libs:
                found_libs[category] = found_category_libs

        return found_libs

    def _extract_database_technologies(self, text: str) -> List[str]:
        """Extract database technologies from text."""
        found_dbs = []
        text_lower = text.lower()

        for db_tech in self.database_technologies:
            if db_tech in text_lower or db_tech.replace("-", " ") in text_lower:
                found_dbs.append(db_tech)

        # Portuguese mapping for database terms
        db_mappings = {
            "banco de dados": "database",
            "mysql": "mysql",
            "postgres": "postgresql",
            "mongo": "mongodb",
            "redis": "redis",
        }

        for pt_term, en_term in db_mappings.items():
            if (
                pt_term in text_lower
                and en_term not in found_dbs
                and en_term in self.database_technologies
            ):
                found_dbs.append(en_term)

        return list(set(found_dbs))

    def _extract_devops_tools(self, text: str) -> List[str]:
        """Extract DevOps and infrastructure tools from text."""
        found_tools = []
        text_lower = text.lower()

        for tool in self.devops_tools:
            if tool in text_lower or tool.replace("-", " ") in text_lower:
                found_tools.append(tool)

        return list(set(found_tools))

    def _extract_security_patterns(self, text: str) -> List[str]:
        """Extract security patterns and standards from text."""
        found_security = []
        text_lower = text.lower()

        for security_pattern in self.security_patterns:
            if security_pattern in text_lower or security_pattern.replace("-", " ") in text_lower:
                found_security.append(security_pattern)

        # Portuguese security mappings
        security_mappings = {
            "autenticação": "authentication",
            "autorização": "authorization",
            "criptografia": "encryption",
            "segurança": "security-patterns",
            "ssl": "ssl",
            "https": "https",
            "oauth": "oauth2",
        }

        for pt_term, en_term in security_mappings.items():
            if (
                pt_term in text_lower
                and en_term not in found_security
                and en_term in self.security_patterns
            ):
                found_security.append(en_term)

        return list(set(found_security))

    def _extract_business_patterns(self, text: str) -> List[str]:
        """Extract domain-specific business patterns from text."""
        found_patterns = []
        text_lower = text.lower()

        for pattern in self.business_patterns:
            if pattern in text_lower or pattern.replace("-", " ") in text_lower:
                found_patterns.append(pattern)

        # Portuguese business pattern mappings
        business_mappings = {
            "carrinho": "shopping-cart",
            "checkout": "checkout-process",
            "estoque": "inventory-management",
            "pedidos": "order-management",
            "pagamentos": "payment-gateway",
            "usuários": "user-management",
            "relatórios": "reporting-system",
            "dashboard": "analytics-dashboard",
            "notificações": "notification-system",
        }

        for pt_term, en_term in business_mappings.items():
            if (
                pt_term in text_lower
                and en_term not in found_patterns
                and en_term in self.business_patterns
            ):
                found_patterns.append(en_term)

        return list(set(found_patterns))

    def _translate_to_english(self, text: str) -> str:
        """Translate Portuguese technical terms to English using comprehensive mapping."""
        translated_text = text.lower()

        # Apply Portuguese to English mappings
        for pt_term, en_term in self.portuguese_to_english_mapping.items():
            translated_text = translated_text.replace(pt_term, en_term)

        return translated_text

    def _normalize_answer_to_text(self, answer: Any) -> str:
        """Normaliza resposta para texto analisável."""
        if isinstance(answer, str):
            return answer
        elif isinstance(answer, list):
            return " ".join(str(item) for item in answer)
        elif isinstance(answer, dict):
            return " ".join(str(value) for value in answer.values())
        else:
            return str(answer)


# Função de conveniência
def create_knowledge_sanitizer() -> KnowledgeSanitizer:
    """Cria uma instância do sanitizador de conhecimento."""
    return KnowledgeSanitizer()
