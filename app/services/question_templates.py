"""
Standardized Question Templates and Options.
Provides contextual multiple choice options by domain and mandatory coverage areas.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class OptionTemplate:
    """Template for a standardized question option."""
    id: str
    text: str
    description: str = ""


class QuestionTemplates:
    """Centralized repository of standardized question templates by domain."""
    
    # Mandatory Coverage Areas - Must be addressed in every project
    MANDATORY_COVERAGE = {
        "devices": {
            "question": "Em quais dispositivos o sistema deve funcionar?",
            "why_it_matters": "Define a estratégia de desenvolvimento (responsivo, nativo, híbrido) e impacta custos e cronograma significativamente.",
            "options": [
                OptionTemplate("desktop_only", "Apenas Desktop/Web", "Foco em computadores e notebooks"),
                OptionTemplate("mobile_priority", "Mobile-first", "Prioridade para smartphones e tablets"),
                OptionTemplate("responsive_web", "Web Responsivo", "Site que adapta a qualquer tela"),
                OptionTemplate("native_apps", "Apps Nativos", "Aplicativos específicos iOS/Android"),
                OptionTemplate("hybrid_apps", "Apps Híbridos", "Uma base para múltiplas plataformas"),
                OptionTemplate("all_platforms", "Multiplataforma Completa", "Web + iOS + Android + Desktop")
            ]
        },
        
        "peripherals": {
            "question": "Quais periféricos e integrações externas são necessários?",
            "why_it_matters": "Periféricos específicos podem exigir drivers especiais, APIs dedicadas e testes específicos, afetando arquitetura e custos.",
            "options": [
                OptionTemplate("printers", "Impressoras", "Impressão de relatórios, etiquetas, documentos"),
                OptionTemplate("scanners", "Scanners/Câmeras", "Digitalização de documentos, QR codes"),
                OptionTemplate("card_readers", "Leitores de Cartão", "Pagamentos, controle de acesso"),
                OptionTemplate("barcode", "Código de Barras", "Leitura/impressão de códigos"),
                OptionTemplate("certificates", "Certificados Digitais", "A1, A3, assinatura digital"),
                OptionTemplate("biometrics", "Biometria", "Impressão digital, reconhecimento facial"),
                OptionTemplate("pos_terminal", "Terminal POS", "Equipamentos de ponto de venda"),
                OptionTemplate("none", "Nenhum Periférico", "Sistema apenas software")
            ]
        },
        
        "fiscal_compliance": {
            "question": "Que obrigações fiscais e regulamentárias o sistema deve atender?",
            "why_it_matters": "Compliance fiscal é obrigatório no Brasil e requer integrações específicas com Receita Federal, podendo representar 20-30% do desenvolvimento.",
            "options": [
                OptionTemplate("nfe", "NFe (Nota Fiscal Eletrônica)", "Venda de produtos"),
                OptionTemplate("nfse", "NFSe (Nota Fiscal de Serviço)", "Prestação de serviços"),
                OptionTemplate("nfce", "NFCe (Cupom Fiscal Eletrônico)", "Varejo/PDV"),
                OptionTemplate("sped", "SPED", "Sistema Público de Escrituração Digital"),
                OptionTemplate("sat", "SAT", "Sistema Autenticador e Transmissor"),
                OptionTemplate("mfe", "MFe", "Mobile Fiscal Eletrônico"),
                OptionTemplate("lgpd", "LGPD", "Lei Geral de Proteção de Dados"),
                OptionTemplate("cfm", "CFM", "Conselho Federal de Medicina"),
                OptionTemplate("bacen", "Bacen", "Banco Central do Brasil"),
                OptionTemplate("none_fiscal", "Sem Obrigações Fiscais", "Sistema interno sem emissão fiscal")
            ]
        },
        
        "integrations": {
            "question": "Com quais sistemas externos o projeto precisa se integrar?",
            "why_it_matters": "Integrações definem a complexidade da arquitetura e podem ser o maior desafio técnico, exigindo APIs, autenticação e sincronização de dados.",
            "options": [
                OptionTemplate("erp_legacy", "ERP Legado", "Sistemas antigos da empresa"),
                OptionTemplate("crm_existing", "CRM Existente", "Salesforce, HubSpot, Pipedrive"),
                OptionTemplate("payment_gateways", "Gateways de Pagamento", "PagSeguro, Mercado Pago, Stripe"),
                OptionTemplate("banks_apis", "APIs Bancárias", "Open Banking, PIX, TEDs"),
                OptionTemplate("government", "Sistemas Governamentais", "Receita, INSS, eSocial"),
                OptionTemplate("delivery", "Sistemas de Entrega", "Correios, transportadoras"),
                OptionTemplate("social_auth", "Autenticação Social", "Google, Facebook, Microsoft"),
                OptionTemplate("none_integration", "Sem Integrações", "Sistema independente")
            ]
        }
    }
    
    # Performance/SLA Mandatory Question - Always included
    PERFORMANCE_SLA = {
        "question": "Quais são as metas de performance e SLA para o sistema?",
        "why_it_matters": "Define a arquitetura de infraestrutura, estratégias de cache, monitoramento e investimento em alta disponibilidade necessários.",
        "options": [
            OptionTemplate("basic_sla", "SLA Básico", "99% uptime, resposta < 3s"),
            OptionTemplate("standard_sla", "SLA Padrão", "99.5% uptime, resposta < 1s"),
            OptionTemplate("high_sla", "SLA Alto", "99.9% uptime, resposta < 500ms"),
            OptionTemplate("enterprise_sla", "SLA Enterprise", "99.95% uptime, resposta < 100ms"),
            OptionTemplate("realtime_sla", "Tempo Real Crítico", "99.99% uptime, resposta < 50ms"),
            OptionTemplate("custom_sla", "SLA Customizado", "Definir metas específicas")
        ]
    }
    
    # Domain-specific Templates
    DOMAIN_TEMPLATES = {
        "financial": {
            "business_model": {
                "question": "Qual o modelo de negócio financeiro principal?",
                "why_it_matters": "O modelo de negócio determina a arquitetura de segurança, compliance e regulamentações específicas necessárias.",
                "options": [
                    OptionTemplate("bank", "Banco Digital", "Conta corrente, poupança, cartões"),
                    OptionTemplate("fintech", "Fintech de Pagamentos", "PIX, carteira digital, transferências"),
                    OptionTemplate("investment", "Plataforma de Investimentos", "Corretora, fundos, ações"),
                    OptionTemplate("lending", "Empréstimos/Crédito", "Análise de risco, scoring"),
                    OptionTemplate("insurance", "Seguros", "Apólices, sinistros, cobertura"),
                    OptionTemplate("accounting", "Contabilidade", "Gestão contábil para empresas")
                ]
            },
            "transaction_volume": {
                "question": "Qual o volume de transações esperado por dia?",
                "why_it_matters": "Volume de transações define a infraestrutura necessária, estratégias de cache e arquitetura de alta disponibilidade.",
                "options": [
                    OptionTemplate("low", "Até 1.000 transações/dia", "Pequeno porte"),
                    OptionTemplate("medium", "1.000 a 10.000 transações/dia", "Médio porte"),
                    OptionTemplate("high", "10.000 a 100.000 transações/dia", "Grande porte"),
                    OptionTemplate("enterprise", "Mais de 100.000 transações/dia", "Enterprise/Bancário")
                ]
            }
        },
        
        "healthcare": {
            "facility_type": {
                "question": "Que tipo de estabelecimento de saúde é o foco?",
                "why_it_matters": "Cada tipo tem regulamentações específicas (CFM, ANVISA), fluxos diferentes e necessidades de integração distintas.",
                "options": [
                    OptionTemplate("clinic", "Clínica Especializada", "Consultórios médicos especializados"),
                    OptionTemplate("hospital", "Hospital", "Internações, cirurgias, emergência"),
                    OptionTemplate("lab", "Laboratório", "Exames, análises clínicas"),
                    OptionTemplate("pharmacy", "Farmácia", "Dispensação, controle de medicamentos"),
                    OptionTemplate("telemedicine", "Telemedicina", "Consultas remotas, laudos à distância"),
                    OptionTemplate("dental", "Odontologia", "Consultórios e clínicas dentárias")
                ]
            },
            "patient_data": {
                "question": "Quais dados de pacientes o sistema deve gerenciar?",
                "why_it_matters": "Dados médicos têm regulamentações rígidas (LGPD, CFM), exigem criptografia específica e auditoria completa.",
                "options": [
                    OptionTemplate("basic_data", "Dados Básicos", "Nome, CPF, contato, convênio"),
                    OptionTemplate("medical_records", "Prontuários Completos", "Histórico médico, exames, prescrições"),
                    OptionTemplate("exam_images", "Imagens Médicas", "Raio-X, ultrassom, ressonância"),
                    OptionTemplate("lab_results", "Resultados de Exames", "Laboratório, análises clínicas"),
                    OptionTemplate("prescriptions", "Prescrições Digitais", "Medicamentos, posologia"),
                    OptionTemplate("appointments", "Agendamentos", "Consultas, procedimentos, horários")
                ]
            }
        },
        
        "ecommerce": {
            "business_model": {
                "question": "Qual o modelo de e-commerce?",
                "why_it_matters": "O modelo define a complexidade dos fluxos de pagamento, logística e relacionamento com fornecedores/clientes.",
                "options": [
                    OptionTemplate("b2c", "B2C (Loja Virtual)", "Venda direta ao consumidor"),
                    OptionTemplate("b2b", "B2B (Atacado/Distribuição)", "Venda para outras empresas"),
                    OptionTemplate("marketplace", "Marketplace", "Múltiplos vendedores na plataforma"),
                    OptionTemplate("subscription", "Subscription", "Assinaturas recorrentes"),
                    OptionTemplate("dropshipping", "Dropshipping", "Sem estoque próprio"),
                    OptionTemplate("hybrid", "Modelo Híbrido", "Combinação de modelos")
                ]
            },
            "product_type": {
                "question": "Que tipos de produtos serão vendidos?",
                "why_it_matters": "Produtos diferentes têm regulamentações específicas, necessidades de estoque e logística distintas.",
                "options": [
                    OptionTemplate("physical", "Produtos Físicos", "Itens que precisam ser enviados"),
                    OptionTemplate("digital", "Produtos Digitais", "Downloads, softwares, cursos"),
                    OptionTemplate("services", "Serviços", "Agendamentos, consultorias"),
                    OptionTemplate("mixed", "Produtos Mistos", "Físicos + digitais + serviços"),
                    OptionTemplate("prescription", "Medicamentos", "Farmácia (regulamentação ANVISA)"),
                    OptionTemplate("food", "Alimentos", "Delivery, regulamentação sanitária")
                ]
            }
        },
        
        "education": {
            "learning_type": {
                "question": "Qual o tipo de ensino/aprendizagem?",
                "why_it_matters": "Cada modalidade tem necessidades técnicas diferentes: ao vivo precisa streaming, gravado precisa storage, presencial precisa QR codes.",
                "options": [
                    OptionTemplate("online_live", "Aulas Ao Vivo Online", "Streaming, webinars, transmissão"),
                    OptionTemplate("online_recorded", "Conteúdo Gravado", "Vídeos, PDFs, exercícios"),
                    OptionTemplate("blended", "Ensino Híbrido", "Presencial + online"),
                    OptionTemplate("corporate", "Treinamento Corporativo", "Capacitação de funcionários"),
                    OptionTemplate("academic", "Ensino Acadêmico", "Escolas, universidades"),
                    OptionTemplate("certification", "Certificação", "Cursos com diploma/certificado")
                ]
            },
            "user_capacity": {
                "question": "Quantos usuários simultâneos o sistema deve suportar?",
                "why_it_matters": "Usuários simultâneos definem a infraestrutura de streaming, CDN e capacidade de processamento necessária.",
                "options": [
                    OptionTemplate("small", "Até 100 usuários", "Cursos pequenos, workshops"),
                    OptionTemplate("medium", "100 a 1.000 usuários", "Empresa média, escola"),
                    OptionTemplate("large", "1.000 a 10.000 usuários", "Universidade, curso popular"),
                    OptionTemplate("massive", "Mais de 10.000 usuários", "MOOC, plataforma nacional")
                ]
            }
        },
        
        "marketplace": {
            "service_categories": {
                "question": "Quais categorias de serviços serão oferecidas na plataforma?",
                "why_it_matters": "Define o escopo de mercado, estrutura de dados, sistema de busca e filtros necessários para cada categoria.",
                "options": [
                    OptionTemplate("tech", "Desenvolvimento e TI", "Programação, apps, sistemas"),
                    OptionTemplate("design", "Design e Criatividade", "Logotipos, sites, artes visuais"),
                    OptionTemplate("marketing", "Marketing Digital", "SEO, redes sociais, campanhas"),
                    OptionTemplate("writing", "Redação e Conteúdo", "Artigos, copywriting, tradução"),
                    OptionTemplate("business", "Consultoria Empresarial", "Estratégia, finanças, RH"),
                    OptionTemplate("education", "Educação e Treinamento", "Cursos, mentoria, coaching"),
                    OptionTemplate("all_categories", "Todas as Categorias", "Marketplace abrangente")
                ]
            },
            "payment_model": {
                "question": "Como funcionará o sistema de pagamentos e proteção?",
                "why_it_matters": "Define a arquitetura financeira, integração com gateways, sistema de escrow e proteção contra fraudes.",
                "options": [
                    OptionTemplate("escrow_auto", "Escrow Automático", "Retenção até entrega aprovada"),
                    OptionTemplate("milestone_based", "Pagamento por Marcos", "Liberação progressiva por etapas"),
                    OptionTemplate("direct_payment", "Pagamento Direto", "Cliente paga diretamente ao freelancer"),
                    OptionTemplate("subscription", "Modelo Assinatura", "Taxa mensal/anual para acesso"),
                    OptionTemplate("commission_only", "Só Comissão", "Taxa apenas sobre transações"),
                    OptionTemplate("hybrid_model", "Modelo Híbrido", "Combinação de modelos")
                ]
            },
            "matching_system": {
                "question": "Como será feito o matching entre clientes e freelancers?",
                "why_it_matters": "Define o algoritmo de recomendação, sistema de busca, filtros e experiência do usuário na descoberta de talentos.",
                "options": [
                    OptionTemplate("manual_search", "Busca Manual", "Cliente busca e escolhe freelancers"),
                    OptionTemplate("auto_matching", "Matching Automático", "IA sugere freelancers compatíveis"),
                    OptionTemplate("bidding_system", "Sistema de Lances", "Freelancers fazem propostas"),
                    OptionTemplate("curated_matches", "Matches Curados", "Equipe interna faz pré-seleção"),
                    OptionTemplate("hybrid_matching", "Sistema Híbrido", "Combinação de métodos"),
                    OptionTemplate("category_specific", "Por Categoria", "Método varia por tipo de serviço")
                ]
            }
        }
    }
    
    @classmethod
    def get_mandatory_questions(cls) -> List[Dict[str, Any]]:
        """Get all mandatory coverage questions that must be included in every project."""
        questions = []
        
        for coverage_area, config in cls.MANDATORY_COVERAGE.items():
            question = {
                "category": "technical",
                "text": config["question"],
                "why_it_matters": config["why_it_matters"],
                "required": True,
                "allow_multiple": True,
                "choices": [
                    {
                        "id": opt.id,
                        "text": opt.text,
                        "description": opt.description
                    }
                    for opt in config["options"]
                ]
            }
            questions.append(question)
        
        return questions
    
    @classmethod
    def get_domain_questions(cls, domain: str, max_questions: int = 3) -> List[Dict[str, Any]]:
        """Get domain-specific questions for a given industry/domain."""
        if domain not in cls.DOMAIN_TEMPLATES:
            return []
        
        questions = []
        domain_config = cls.DOMAIN_TEMPLATES[domain]
        
        # Limit to max_questions
        question_keys = list(domain_config.keys())[:max_questions]
        
        for question_key in question_keys:
            config = domain_config[question_key]
            question = {
                "category": "business",
                "text": config["question"],
                "why_it_matters": config["why_it_matters"],
                "required": True,
                "allow_multiple": False,
                "choices": [
                    {
                        "id": opt.id,
                        "text": opt.text,
                        "description": opt.description
                    }
                    for opt in config["options"]
                ]
            }
            questions.append(question)
        
        return questions
    
    @classmethod
    def detect_domain(cls, project_description: str) -> str:
        """Detect the most likely domain based on project description keywords."""
        description_lower = project_description.lower()
        
        # Domain detection keywords
        domain_keywords = {
            "financial": ["bancário", "banco", "fintech", "pagamento", "pix", "cartão", "empréstimo", "financeiro", "investimento", "corretora", "trading"],
            "healthcare": ["médico", "hospitalar", "clínica", "saúde", "paciente", "prontuário", "telemedicina", "exame"],
            "ecommerce": ["e-commerce", "loja", "vendas", "produto", "carrinho", "delivery", "varejo"],
            "education": ["educação", "ensino", "curso", "aula", "aprendizagem", "treinamento", "e-learning"],
            "marketplace": ["marketplace", "freelancer", "freelancers", "plataforma", "serviços", "matching", "gig economy", "talents", "profissionais"]
        }
        
        # Count keyword matches for each domain
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            domain_scores[domain] = score
        
        # Return domain with highest score, or None if no clear match
        if max(domain_scores.values()) > 0:
            return max(domain_scores.items(), key=lambda x: x[1])[0]
        
        return "general"
    
    @classmethod
    def get_performance_question(cls) -> Dict[str, Any]:
        """Get mandatory performance/SLA question."""
        return {
            "category": "operational",
            "text": cls.PERFORMANCE_SLA["question"],
            "why_it_matters": cls.PERFORMANCE_SLA["why_it_matters"],
            "required": True,
            "allow_multiple": False,
            "choices": [
                {
                    "id": opt.id,
                    "text": opt.text,
                    "description": opt.description
                }
                for opt in cls.PERFORMANCE_SLA["options"]
            ]
        }
    
    @classmethod
    def get_contextual_questions(cls, project_description: str, total_questions: int = 8) -> List[Dict[str, Any]]:
        """
        CORREÇÃO CIRÚRGICA: Get a complete set of contextual questions with HARD QUOTAS.
        
        NEW STRATEGY (Based on diagnostics):
        - 4 mandatory coverage questions (devices, peripherals, fiscal, integrations) - TECHNICAL
        - 1 mandatory performance/SLA question - OPERATIONAL  
        - 2-3 domain-specific questions - BUSINESS
        - Fill remaining to ensure 30% minimum per category
        
        HARD QUOTAS: min 30% business / 30% technical / 30% operational
        """
        questions = []
        
        # Step 1: Always include mandatory coverage (4 technical questions)
        mandatory = cls.get_mandatory_questions()
        questions.extend(mandatory)
        
        # Step 2: Always include performance/SLA (1 operational question)
        performance_q = cls.get_performance_question()
        questions.append(performance_q)
        
        # Step 3: Add domain-specific questions (business questions)
        domain = cls.detect_domain(project_description)
        if domain != "general":
            domain_questions = cls.get_domain_questions(domain, max_questions=3)
            questions.extend(domain_questions)
        
        # Step 4: Ensure category quotas (30% minimum each)
        questions = cls._enforce_category_quotas(questions, total_questions)
        
        # Step 5: Add question codes
        for i, question in enumerate(questions):
            question["code"] = f"Q{i+1:03d}"
        
        return questions[:total_questions]
    
    @classmethod
    def _enforce_category_quotas(cls, questions: List[Dict[str, Any]], target_total: int) -> List[Dict[str, Any]]:
        """
        HARD QUOTA ENFORCEMENT: Ensure minimum 30% per category.
        
        Args:
            questions: Current list of questions
            target_total: Target number of questions
        
        Returns:
            Questions list adjusted to meet quotas
        """
        # Count current distribution
        category_counts = {"business": 0, "technical": 0, "operational": 0}
        for q in questions:
            cat = q.get("category", "unknown")
            if cat in category_counts:
                category_counts[cat] += 1
        
        # Calculate minimum needed per category (30% of target)
        min_per_category = max(1, int(target_total * 0.3))
        
        # Add questions to meet minimums
        for category, current_count in category_counts.items():
            needed = min_per_category - current_count
            
            if needed > 0:
                # Generate additional questions for this category
                additional_questions = cls._generate_additional_questions(category, needed)
                questions.extend(additional_questions)
        
        return questions
    
    @classmethod 
    def _generate_additional_questions(cls, category: str, count: int) -> List[Dict[str, Any]]:
        """Generate additional questions to meet category quotas."""
        additional = []
        
        if category == "operational":
            # Additional operational questions
            ops_questions = [
                {
                    "category": "operational",
                    "text": "Como será feita a operação diária e monitoramento do sistema?",
                    "why_it_matters": "Define processos operacionais, dashboards de monitoramento e procedures de manutenção necessários.",
                    "required": True,
                    "allow_multiple": True,
                    "choices": [
                        {"id": "auto_monitoring", "text": "Monitoramento Automático", "description": "Alertas e dashboards automatizados"},
                        {"id": "manual_ops", "text": "Operação Manual", "description": "Equipe dedicada para monitoramento"},
                        {"id": "hybrid_ops", "text": "Operação Híbrida", "description": "Automação + supervisão humana"},
                        {"id": "outsourced_ops", "text": "Operação Terceirizada", "description": "Empresa especializada em operação"},
                        {"id": "self_service", "text": "Self-Service", "description": "Usuários resolvem problemas sozinhos"}
                    ]
                },
                {
                    "category": "operational", 
                    "text": "Qual será a estratégia de backup e disaster recovery?",
                    "why_it_matters": "Define RTO/RPO, infraestrutura de backup e procedures de contingência para garantir continuidade do negócio.",
                    "required": True,
                    "allow_multiple": False,
                    "choices": [
                        {"id": "basic_backup", "text": "Backup Básico", "description": "Backup diário, RTO 24h"},
                        {"id": "standard_dr", "text": "DR Padrão", "description": "Backup contínuo, RTO 4h"},
                        {"id": "advanced_dr", "text": "DR Avançado", "description": "Hot standby, RTO 1h"},
                        {"id": "enterprise_dr", "text": "DR Enterprise", "description": "Multi-region, RTO 15min"},
                        {"id": "custom_dr", "text": "DR Customizado", "description": "Estratégia específica do projeto"}
                    ]
                }
            ]
            additional.extend(ops_questions[:count])
            
        elif category == "business":
            # Additional business questions  
            biz_questions = [
                {
                    "category": "business",
                    "text": "Qual é o modelo de monetização principal do projeto?",
                    "why_it_matters": "Define arquitetura de cobrança, integrações de pagamento e métricas de sucesso do negócio.",
                    "required": True,
                    "allow_multiple": False,
                    "choices": [
                        {"id": "subscription", "text": "Assinatura Mensal/Anual", "description": "Receita recorrente"},
                        {"id": "freemium", "text": "Freemium", "description": "Básico grátis + premium pago"},
                        {"id": "transaction_fee", "text": "Taxa por Transação", "description": "Comissão sobre vendas"},
                        {"id": "advertising", "text": "Publicidade", "description": "Revenue de anúncios"},
                        {"id": "one_time", "text": "Pagamento Único", "description": "Compra única do software"},
                        {"id": "custom_model", "text": "Modelo Customizado", "description": "Combinação ou modelo específico"}
                    ]
                }
            ]
            additional.extend(biz_questions[:count])
            
        elif category == "technical":
            # Additional technical questions
            tech_questions = [
                {
                    "category": "technical",
                    "text": "Qual será a estratégia de escalabilidade e arquitetura?",
                    "why_it_matters": "Define se a arquitetura suportará crescimento futuro e quais tecnologias usar para alta disponibilidade.",
                    "required": True,
                    "allow_multiple": False,
                    "choices": [
                        {"id": "monolith", "text": "Arquitetura Monolítica", "description": "Aplicação única, deploy simples"},
                        {"id": "microservices", "text": "Microserviços", "description": "Serviços independentes, alta escalabilidade"},
                        {"id": "serverless", "text": "Serverless", "description": "Functions as a Service, escala automática"},
                        {"id": "containers", "text": "Containers", "description": "Docker/Kubernetes, orquestração"},
                        {"id": "hybrid_arch", "text": "Arquitetura Híbrida", "description": "Combinação de estratégias"}
                    ]
                }
            ]
            additional.extend(tech_questions[:count])
        
        return additional