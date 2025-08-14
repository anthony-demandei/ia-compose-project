#!/usr/bin/env python3
"""
Test AI documentation generation directly
"""

import asyncio
import json
import sys
sys.path.append('.')

from app.services.document_generator import DocumentGeneratorService

async def test_ai_generation():
    """Test AI generation with a simple project."""
    
    print("🧪 TESTE DIRETO DA GERAÇÃO AI")
    print("=" * 40)
    
    # Prepare test data
    session_data = {
        "project_description": """
        Sistema de e-commerce completo para venda de produtos online incluindo:
        - Catálogo de produtos com busca e filtros
        - Carrinho de compras e checkout
        - Múltiplos métodos de pagamento (PIX, cartão, boleto)
        - Sistema de avaliações e reviews
        - Painel administrativo para gestão
        - Integração com correios para frete
        - Sistema de cupons de desconto
        - Notificações por email
        - API REST para integrações
        Orçamento: R$ 150.000. Prazo: 6 meses.
        """,
        "answers": [
            {"question_code": "Q001", "selected_choices": ["responsive_web", "mobile_apps"]},
            {"question_code": "Q002", "selected_choices": ["payment_gateway", "shipping_api"]},
            {"question_code": "Q003", "selected_choices": ["lgpd", "pci_dss"]},
            {"question_code": "Q004", "selected_choices": ["correios", "payment_providers"]},
            {"question_code": "Q005", "selected_choices": ["b2c"]},
            {"question_code": "Q006", "selected_choices": ["high_performance"]}
        ],
        "project_classification": {
            "type": "e-commerce",
            "complexity": "moderate",
            "key_technologies": ["web", "mobile", "payments"],
            "confidence": 0.9
        }
    }
    
    # Initialize service
    doc_generator = DocumentGeneratorService()
    
    try:
        # Generate documentation
        print("\n📄 Gerando documentação com AI...")
        stacks = await doc_generator.generate_documents(
            session_data=session_data,
            include_implementation=True
        )
        
        # Analyze results
        print("\n📊 RESULTADOS:")
        print("-" * 40)
        
        total_chars = 0
        for stack in stacks:
            content_size = len(stack.content)
            total_chars += content_size
            
            print(f"\n✅ {stack.stack_type.upper()}:")
            print(f"   Título: {stack.title}")
            print(f"   Tecnologias: {', '.join(stack.technologies[:5])}")
            print(f"   Esforço: {stack.estimated_effort}")
            print(f"   Tamanho: {content_size:,} caracteres")
            
            # Show first 200 chars of content
            print(f"   Preview: {stack.content[:200]}...")
        
        print(f"\n📈 TOTAL: {total_chars:,} caracteres gerados")
        
        # Save to file for inspection
        output = {
            "total_chars": total_chars,
            "stacks": [
                {
                    "type": s.stack_type,
                    "size": len(s.content),
                    "technologies": s.technologies,
                    "effort": s.estimated_effort,
                    "content_preview": s.content[:500]
                }
                for s in stacks
            ]
        }
        
        with open("ai_generation_test_result.json", "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print("\n✅ Resultado salvo em: ai_generation_test_result.json")
        
        # Determine success
        if total_chars > 1000:
            print(f"\n🎉 SUCESSO! AI gerou {total_chars:,} caracteres de documentação contextualizada")
        else:
            print(f"\n⚠️ FALLBACK DETECTADO: Apenas {total_chars} caracteres (templates padrão)")
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_generation())