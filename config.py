"""
config.py — Configurações centrais do boletim de notícias.
Edite aqui para alterar fontes, temas, horários e limites.
"""

# ---------------------------------------------------------------------------
# FONTES RSS VERIFICADAS
# Cada entrada: (nome_exibição, url_feed, categorias_cobertas, país)
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    # Brasil — Política e geral
    {
        "name": "Agência Brasil — Política",
        "url": "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml",
        "topics": ["política"],
        "country": "BR",
    },
    {
        "name": "Agência Brasil — Economia",
        "url": "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",
        "topics": ["economia"],
        "country": "BR",
    },
    {
        "name": "Agência Brasil — Geral",
        "url": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
        "topics": ["política", "economia", "segurança", "tecnologia"],
        "country": "BR",
    },
    {
        "name": "G1 — Política",
        "url": "https://g1.globo.com/rss/g1/politica/",
        "topics": ["política"],
        "country": "BR",
    },
    {
        "name": "G1 — Economia",
        "url": "https://g1.globo.com/rss/g1/economia/",
        "topics": ["economia"],
        "country": "BR",
    },
    {
        "name": "G1 — Brasil (segurança pública)",
        "url": "https://g1.globo.com/rss/g1/brasil/",
        "topics": ["segurança"],
        "country": "BR",
    },
    {
        "name": "G1 — Tecnologia",
        "url": "http://pox.globo.com/rss/g1/tecnologia/",
        "topics": ["tecnologia"],
        "country": "BR",
    },
    {
        "name": "Poder360",
        "url": "https://www.poder360.com.br/feed/",
        "topics": ["política", "economia"],
        "country": "BR",
    },
    {
        "name": "TecMundo",
        "url": "https://rss.tecmundo.com.br/feed",
        "topics": ["tecnologia"],
        "country": "BR",
    },
    # Internacional em português
    {
        "name": "BBC News Brasil",
        "url": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "topics": ["política", "economia", "segurança", "tecnologia"],
        "country": "WORLD",
    },
    {
        "name": "Agência Brasil — Internacional",
        "url": "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml",
        "topics": ["política", "economia"],
        "country": "WORLD",
    },
]

# ---------------------------------------------------------------------------
# CURADORIA DE CONTEÚDO
# ---------------------------------------------------------------------------

# Temas aceitos (a IA também filtra, mas este filtro é uma pré-seleção rápida)
ACCEPTED_TOPICS = ["política", "economia", "segurança", "tecnologia"]

# Palavras-chave para excluir automaticamente sem enviar à IA
# (reduz custos e ruído)
EXCLUDE_KEYWORDS = [
    "futebol", "campeonato", "gol", "jogador", "atleta", "esporte",
    "celebridade", "famoso", "famosa", "novela", "série", "filme",
    "moda", "beleza", "receita", "culinária", "horóscopo",
    "BBB", "Big Brother", "reality show",
]

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES DO BOLETIM
# ---------------------------------------------------------------------------
MAX_NEWS_TOTAL = 6           # Total de notícias no boletim
MAX_NEWS_BRAZIL = 4          # Máximo de notícias do Brasil
MAX_NEWS_WORLD = 2           # Máximo de notícias internacionais

# Período de busca em horas (dias úteis normais)
LOOKBACK_HOURS_WEEKDAY = 24

# Período de busca na segunda-feira (cobre o fim de semana inteiro)
LOOKBACK_HOURS_MONDAY = 72

# Máximo de artigos enviados à IA para seleção (controla custo e tempo)
MAX_ARTICLES_FOR_AI = 30

# Limite de caracteres por artigo enviado à IA (evita tokens excessivos)
MAX_ARTICLE_CHARS = 1500

# ---------------------------------------------------------------------------
# TELEGRAM
# ---------------------------------------------------------------------------
# Limite do Telegram por mensagem (4096 caracteres)
TELEGRAM_MAX_CHARS = 4000   # Margem de segurança de 96 chars

# ---------------------------------------------------------------------------
# RETENTATIVAS
# ---------------------------------------------------------------------------
MAX_RETRIES = 3              # Tentativas máximas em caso de falha
RETRY_DELAY_SECONDS = 10     # Segundos entre tentativas (aumenta a cada retry)

# ---------------------------------------------------------------------------
# HISTÓRICO
# ---------------------------------------------------------------------------
HISTORY_FILE = "history.json"
HISTORY_MAX_ENTRIES = 500    # Máximo de URLs armazenadas (evita crescimento infinito)
