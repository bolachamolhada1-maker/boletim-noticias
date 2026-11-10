"""
config.py — Configurações centrais do boletim de notícias.
Edite aqui para alterar fontes, temas, horários e limites.

FONTES EXCLUSIVAMENTE AUTORIZADAS (conforme especificação editorial):
  1. BBC News Brasil
  2. Folha de S.Paulo
  3. O Estado de S. Paulo — Estadão
  4. Valor Econômico
  5. G1
  6. Poder360
  7. Nexo Jornal
  8. Agência Lupa e Aos Fatos
  9. Reuters
  10. Associated Press — AP
  11. Agence France-Presse — AFP
  12. BBC News
  13. The New York Times
  14. The Wall Street Journal e Financial Times
  15. The Economist e Deutsche Welle — DW
"""

# ---------------------------------------------------------------------------
# FONTES RSS CONFIGURADAS (resultados por endereço em docs/feed-checks.json)
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    # -----------------------------------------------------------------------
    # BRASIL — Folha de S.Paulo
    # -----------------------------------------------------------------------
    {
        "name": "Folha de S.Paulo — Poder",
        "url": "https://feeds.folha.uol.com.br/poder/rss091.xml",
        "topics": ["política"],
        "country": "BR",
    },
    {
        "name": "Folha de S.Paulo — Mercado",
        "url": "https://feeds.folha.uol.com.br/mercado/rss091.xml",
        "topics": ["economia"],
        "country": "BR",
    },
    {
        "name": "Folha de S.Paulo — Cotidiano",
        "url": "https://feeds.folha.uol.com.br/cotidiano/rss091.xml",
        "topics": ["segurança", "política"],
        "country": "BR",
    },
    # -----------------------------------------------------------------------
    # BRASIL — G1
    # -----------------------------------------------------------------------
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
        "name": "G1 — Brasil e Cidades",
        "url": "https://g1.globo.com/rss/g1/",
        "topics": ["segurança", "política"],
        "country": "BR",
    },
    {
        "name": "G1 — Tecnologia",
        "url": "https://pox.globo.com/rss/g1/tecnologia/",
        "topics": ["tecnologia"],
        "country": "BR",
    },
    # -----------------------------------------------------------------------
    # BRASIL — Poder360
    # -----------------------------------------------------------------------
    {
        "name": "Poder360",
        "url": "https://www.poder360.com.br/feed/",
        "topics": ["política", "economia"],
        "country": "BR",
    },
    # -----------------------------------------------------------------------
    # BRASIL — Agência Lupa
    # -----------------------------------------------------------------------
    {
        "name": "Agência Lupa",
        "url": "https://www.agencialupa.org/feed/",
        "topics": ["política", "segurança"],
        "country": "BR",
    },
    # -----------------------------------------------------------------------
    # INTERNACIONAL em português — BBC News Brasil, DW e Folha Mundo
    # -----------------------------------------------------------------------
    {
        "name": "BBC News Brasil",
        "url": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "topics": ["política", "economia", "segurança", "tecnologia"],
        "country": "WORLD",
    },
    {
        "name": "Deutsche Welle — Brasil",
        "url": "https://rss.dw.com/rdf/rss-br-br",
        "topics": ["política", "economia", "segurança", "tecnologia"],
        "country": "WORLD",
    },
    {
        "name": "Folha de S.Paulo — Mundo",
        "url": "https://feeds.folha.uol.com.br/mundo/rss091.xml",
        "topics": ["política", "economia"],
        "country": "WORLD",
    },
    # -----------------------------------------------------------------------
    # INTERNACIONAL em inglês (traduzido pela IA fielmente para pt-BR)
    # -----------------------------------------------------------------------
    {
        "name": "BBC News — World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "topics": ["política", "economia", "segurança"],
        "country": "WORLD",
    },
    {
        "name": "The New York Times — World",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "topics": ["política", "economia", "segurança"],
        "country": "WORLD",
    },
    {
        "name": "The Economist — International",
        "url": "https://www.economist.com/international/rss.xml",
        "topics": ["política", "economia"],
        "country": "WORLD",
    },
    {
        "name": "The Economist — Finance and Economics",
        "url": "https://www.economist.com/finance-and-economics/rss.xml",
        "topics": ["economia"],
        "country": "WORLD",
    },
    # Verificados em 05/11/2026. A disponibilidade do feed não implica corpo aberto.
    {
        "name": "Nexo Jornal",
        "url": "https://www.nexojornal.com.br/rss.xml",
        "topics": ["política", "economia", "segurança", "tecnologia"],
        "country": "MISTO",
    },
    {
        "name": "The Wall Street Journal — World",
        "url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
        "topics": ["política", "economia", "segurança", "tecnologia"],
        "country": "MISTO",
    },
    {
        "name": "Financial Times — World",
        "url": "https://www.ft.com/rss/world",
        "topics": ["política", "economia", "tecnologia"],
        "country": "MISTO",
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
MAX_NEWS_TOTAL = 7           # Total de notícias no boletim (4 BR + 3 MUNDO)
MAX_NEWS_BRAZIL = 4          # Notícias do Brasil
MAX_NEWS_WORLD = 3           # Notícias internacionais (3 acontecimentos distintos)

# Período de busca em horas (dias úteis normais)
LOOKBACK_HOURS_WEEKDAY = 24

# Período de busca na segunda-feira (cobre o fim de semana inteiro)
LOOKBACK_HOURS_MONDAY = 72

# Máximo de artigos enviados à IA para seleção (controla custo e tempo)
MAX_ARTICLES_FOR_AI = 35

# Limite de caracteres por artigo enviado à IA (evita tokens excessivos)
MAX_ARTICLE_CHARS = 6000

# Limites explícitos de coleta e revisão (sem ampliar a janela editorial).
MAX_RESPONSE_BYTES = 1_000_000
MAX_REDIRECTS = 3
NETWORK_BUDGET_SECONDS = 15
MAX_CONTENT_FETCHES = 14
CONTENT_BUDGET_SECONDS = 90
MAX_REVIEW_ATTEMPTS = 3
MAX_REPLACEMENT_ROUNDS = 2
GEMINI_TIMEOUT_SECONDS = 60

# ---------------------------------------------------------------------------
# TELEGRAM
# ---------------------------------------------------------------------------
# Limite do Telegram por mensagem (4096 caracteres)
TELEGRAM_MAX_CHARS = 4000   # Margem de segurança de 96 chars
TELEGRAM_PART_DELAY_SECONDS = 2  # Preserva o intervalo entre partes da rotina anterior

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
GEMINI_MODEL = "gemini-3.1-flash-lite"
DELIVERY_STATE_FILE = "delivery_state.json"
DELIVERY_MAX_EDITIONS = 30
