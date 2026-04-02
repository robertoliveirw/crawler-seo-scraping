# 📦 Guia de Instalação Completo

## Pré-requisitos

✅ **Python 3.9+** instalado
✅ **pip** (gerenciador de pacotes)
✅ **VS Code** (recomendado)
✅ **4GB+ RAM**

---

## Passo a Passo - Windows

### 1. Instalar Python

1. Acesse: https://www.python.org/downloads/
2. Baixe Python 3.11 ou superior
3. Durante instalação:
   - ✅ Marque "**Add Python to PATH**"
   - ✅ Marque "Install pip"
4. Clique em "Install Now"

**Verificar instalação:**
```cmd
python --version
pip --version
```

Deve mostrar algo como:
```
Python 3.11.x
pip 23.x.x
```

### 2. Criar Pasta do Projeto

1. Crie uma pasta no seu computador, ex: `C:\Desktop\seo-crawler`
2. Copie todos os arquivos do projeto para esta pasta:
   - crawler.py
   - config.yaml
   - requirements.txt
   - utils.py
   - extractors.py
   - exporters.py
   - README.md
   - QUICKSTART.md

### 3. Abrir no VS Code

1. Abra VS Code
2. File → Open Folder
3. Selecione a pasta `C:\Desktop\seo-crawler`

### 4. Abrir Terminal no VS Code

- Terminal → New Terminal (ou Ctrl + `)
- Deve abrir um terminal na parte inferior

### 5. Instalar Dependências

No terminal do VS Code, execute:

```bash
pip install -r requirements.txt
```

Isso vai instalar:
- requests (requisições HTTP)
- beautifulsoup4 (parsing HTML)
- pandas (manipulação de dados)
- openpyxl (Excel)
- PyYAML (configuração)
- tqdm (progress bar)
- colorama (cores)
- reppy (robots.txt)

**Aguarde alguns minutos...**

### 6. Testar Instalação

```bash
python test_install.py
```

Se tudo estiver OK, verá:
```
✅ Todas as dependências estão instaladas!
🎉 Crawler pronto para uso!
```

---

## Passo a Passo - Mac/Linux

### 1. Verificar Python

```bash
python3 --version
pip3 --version
```

### 2. Criar Pasta e Copiar Arquivos

```bash
mkdir ~/seo-crawler
cd ~/seo-crawler
# Copie todos os arquivos do projeto aqui
```

### 3. Instalar Dependências

```bash
pip3 install -r requirements.txt
```

### 4. Testar

```bash
python3 test_install.py
```

---

## Configuração Inicial

Abra `config.yaml` no VS Code e edite:

```yaml
# Mude para sua URL
start_url: "https://www.seusite.com.br"

# Ajuste limites conforme necessário
crawl:
  max_total_urls: 10000  # Comece com 10k para teste
```

---

## Primeiro Crawl (Teste)

### Configuração de Teste

Edite `config.yaml`:

```yaml
start_url: "https://www.seusite.com.br"

crawl:
  max_depth: 2
  max_total_urls: 100  # Apenas 100 URLs

rate_limiting:
  requests_per_second: 2.0
```

### Executar

```bash
python crawler.py
```

### Resultados

Arquivos serão criados em `output/`:
- `crawl_YYYYMMDD_HHMMSS.csv`
- `crawl_YYYYMMDD_HHMMSS.xlsx`

---

## Troubleshooting

### ❌ "python is not recognized"

**Solução:**
1. Reinstale Python marcando "Add to PATH"
2. Ou adicione manualmente ao PATH:
   - Painel de Controle → Sistema → Variáveis de Ambiente
   - Adicione: `C:\Users\SeuUsuario\AppData\Local\Programs\Python\Python311`

### ❌ "Permission denied"

**Windows:**
```bash
pip install --user -r requirements.txt
```

**Mac/Linux:**
```bash
pip3 install --user -r requirements.txt
```

### ❌ "ModuleNotFoundError: No module named 'X'"

```bash
pip install X
```

Ou reinstale tudo:
```bash
pip install -r requirements.txt --force-reinstall
```

### ❌ Crawler muito lento

Edite `config.yaml`:
```yaml
rate_limiting:
  requests_per_second: 5.0  # Aumente
  random_delay_range: [0.1, 0.3]  # Reduza
```

### ❌ Sendo bloqueado

Edite `config.yaml`:
```yaml
rate_limiting:
  requests_per_second: 0.5  # REDUZA muito
  random_delay_range: [3, 6]  # AUMENTE delays

# Simule um navegador real
user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
```

---

## Estrutura de Arquivos Final

```
seo-crawler/
├── crawler.py              # Motor principal
├── config.yaml             # Sua configuração
├── requirements.txt        # Dependências
├── utils.py               # Utilidades
├── extractors.py          # Extração de dados
├── exporters.py           # Export CSV/Excel
├── test_install.py        # Teste de instalação
├── README.md              # Documentação completa
├── QUICKSTART.md          # Início rápido
├── INSTALL.md             # Este arquivo
├── output/                # Resultados (gerado)
│   ├── *.csv
│   └── *.xlsx
└── logs/                  # Logs (gerado)
    └── *.log
```

---

## Próximos Passos

1. ✅ Python instalado
2. ✅ Dependências instaladas (`pip install -r requirements.txt`)
3. ✅ Teste passou (`python test_install.py`)
4. ✅ Config editado (`config.yaml`)
5. 🚀 **Rode o crawler:** `python crawler.py`

---

## Suporte

📧 Email: samuel@email.com
📱 Instagram: @seuperfil

Dúvidas? Consulte:
- README.md - Documentação completa
- QUICKSTART.md - Guia rápido

**Boa sorte com seu crawl!** 🕷️
