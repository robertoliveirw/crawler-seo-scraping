# 🚀 Guia Rápido de Início

## Setup em 5 Minutos

### 1️⃣ Verificar Python

```bash
python --version
```

Se não tiver Python instalado:
- Download: https://www.python.org/downloads/
- Se aparcer a opção, marque "Add Python to PATH" durante instalação

### 2️⃣ Criar Pasta do Projeto

```bash
# Crie uma pasta
mkdir seo-crawler
cd seo-crawler

# Copie todos os arquivos do projeto para esta pasta
```

### 3️⃣ Instalar Dependências

```bash
# Instalar bibliotecas Python
pip install -r requirements.txt
```

**Se der erro de permissão no Windows:**
```bash
pip install --user -r requirements.txt
```

### 4️⃣ Configurar**
1. Abra `config.yaml` no VS Code ou no seu editor de código preferido
2. Mude `start_url` para seu site
3. Ajuste `url_pattern_limits` com seus padrões

### 5️⃣ Rodar!

```bash
python crawler.py
```

## 🎯 Teste Rápido (Crawl Pequeno)

Para testar se está funcionando, edite `config.yaml`:

```yaml
start_url: "https://www.seusite.com.br"

crawl:
  max_depth: 2
  max_total_urls: 100  # Apenas 100 URLs para teste

rate_limiting:
  requests_per_second: 2.0
```

Execute:
```bash
python crawler.py
```

Deve terminar em poucos minutos e criar arquivos em `output/`.

## 📊 Ver Resultados

Abra os arquivos na pasta `output/`:

```
output/
├── crawl_20240401_143022.csv      # CSV para análise
└── crawl_20240401_143022.xlsx     # Excel com abas
```

O Excel tem 3 abas:
1. **Crawl Data**: Todos os dados
2. **Summary**: Estatísticas gerais
3. **Issues**: Problemas encontrados

## ⚠️ Problemas Comuns

### Erro: "ModuleNotFoundError"

```bash
pip install -r requirements.txt
```

### Erro: "Permission denied"

```bash
# Windows: rode como Administrador
# Ou use:
pip install --user -r requirements.txt
```

### Crawler muito lento

Edite `config.yaml`:
```yaml
rate_limiting:
  requests_per_second: 3.0  # Aumente este valor
  random_delay_range: [0.2, 0.5]  # Reduza delays
```

### Sendo bloqueado pelo site

Edite `config.yaml`:
```yaml
rate_limiting:
  requests_per_second: 0.5  # REDUZA este valor
  random_delay_range: [2, 4]  # AUMENTE delays

# Mude user-agent
user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

## 🎓 Próximos Passos

1. ✅ Rode o teste com 100 URLs
2. ✅ Verifique se os dados estão corretos no Excel
3. ✅ Ajuste padrões de URL no `config.yaml`
4. ✅ Aumente para 1000-5000 URLs
5. ✅ Analise resultados
6. ✅ Crawl completo com 50k+ URLs

## 💡 Dicas

**Para crawls grandes:**
- Rode à noite ou em horário de baixo tráfego
- Use `max_depth: 5-6` para cobrir todo o site
- Configure limites por padrão adequados
- Mantenha `requests_per_second` baixo (1-2)

**Para análise rápida:**
- Use `max_depth: 2-3`
- Limite total de URLs em 5000-10000
- Foque em padrões específicos com `include_patterns`

## 📞 Ajuda

Problemas? Verifique:
1. `logs/` - Logs detalhados do crawl
2. README.md - Documentação completa

---

**Pronto para começar!** 🚀
