"""
Script de teste de instalação
Verifica se todas as dependências estão instaladas corretamente
"""

import sys

print("🧪 Testando instalação do SEO Crawler...\n")

# Lista de bibliotecas necessárias
required_packages = {
    'requests': 'Requisições HTTP',
    'beautifulsoup4': 'Parsing HTML',
    'lxml': 'Parser XML/HTML',
    'pandas': 'Manipulação de dados',
    'openpyxl': 'Export para Excel',
    'pyyaml': 'Configuração YAML',
    'tqdm': 'Progress bar',
    'colorama': 'Cores no terminal',
    'reppy': 'Parser de robots.txt'
}

errors = []
success = []

for package, description in required_packages.items():
    try:
        __import__(package)
        success.append(f"✅ {package:20} - {description}")
    except ImportError as e:
        errors.append(f"❌ {package:20} - {description}")

print("Resultados:\n")
for msg in success:
    print(msg)

if errors:
    print("\n⚠️  Pacotes faltando:\n")
    for msg in errors:
        print(msg)
    print("\nInstale com: pip install -r requirements.txt")
    sys.exit(1)
else:
    print("\n✅ Todas as dependências estão instaladas!")
    print("\n🎉 Crawler pronto para uso!")
    print("\nPróximos passos:")
    print("  1. Configure config.yaml com sua URL")
    print("  2. Execute: python crawler.py")
    sys.exit(0)
