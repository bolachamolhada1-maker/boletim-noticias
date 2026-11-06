import requests
import datetime
import json
import feedparser

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*"
}

probes = [
    # 1. Estadão
    ("Estadão", "https://www.estadao.com.br/rss/ultimas.xml"),
    ("Estadão", "https://www.estadao.com.br/feed/"),
    ("Estadão", "https://politica.estadao.com.br/rss"),
    # 2. Valor Econômico
    ("Valor Econômico", "https://valor.globo.com/rss/"),
    ("Valor Econômico", "https://valor.globo.com/rss/brasil/"),
    ("Valor Econômico", "https://valor.globo.com/feed/"),
    # 3. Nexo Jornal
    ("Nexo Jornal", "https://www.nexojornal.com.br/feed/"),
    ("Nexo Jornal", "https://www.nexojornal.com.br/rss.xml"),
    # 4. AFP
    ("AFP", "https://www.afp.com/pt/noticias/rss"),
    ("AFP", "https://www.afp.com/feed"),
    # 5. Reuters
    ("Reuters", "https://feeds.reuters.com/reuters/topNews"),
    ("Reuters", "https://www.reutersagency.com/feed/"),
    ("Reuters", "https://www.reuters.com/rssFeed/worldNews"),
    # 6. AP News
    ("AP News", "https://apnews.com/feed"),
    ("AP News", "https://apnews.com/rss"),
    ("AP News", "https://apnews.com/hub/ap-top-news?outputType=xml"),
    # 7. The Wall Street Journal
    ("Wall Street Journal", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("Wall Street Journal", "https://feeds.wsj.com/wsj/xml/rss/3_7085.xml"),
    # 8. Financial Times
    ("Financial Times", "https://www.ft.com/world?format=rss"),
    ("Financial Times", "https://www.ft.com/rss/home/us"),
    # 9. Aos Fatos
    ("Aos Fatos", "https://www.aosfatos.org/noticias/feed/"),
    ("Aos Fatos", "https://www.aosfatos.org/feed/"),
    ("Aos Fatos", "https://www.aosfatos.org/rss/"),
]

now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(f"Sondagem de feeds iniciada em {now_iso}...\n")

results = []

for outlet, url in probes:
    try:
        resp = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        status = resp.status_code
        final_url = resp.url
        content_type = resp.headers.get("Content-Type", "")
        
        parsed = feedparser.parse(resp.content)
        entries_count = len(parsed.entries)
        is_valid_rss = (status == 200) and (entries_count > 0) and not parsed.get("bozo", False)
        
        if status == 404:
            limitacao = "URL não localizada / Feed inexistente (HTTP 404)"
        elif status == 403:
            limitacao = "Acesso bloqueado / Paywall / Cloudflare (HTTP 403)"
        elif status == 401:
            limitacao = "Autenticação requerida (HTTP 401)"
        elif status == 200 and entries_count == 0:
            limitacao = "HTTP 200 retornado mas resposta não é XML/RSS válido (HTML comum ou vazio)"
        elif status == 200 and entries_count > 0:
            limitacao = f"Feed funcional detectado ({entries_count} itens)"
        else:
            limitacao = f"Status HTTP inesperado: {status}"

        print(f"[{outlet}] {url}")
        print(f"  -> Status: {status} | Final: {final_url} | Tipo: {content_type}")
        print(f"  -> Entradas RSS: {entries_count} | Diagnóstico: {limitacao}\n")
        
        results.append({
            "veiculo": outlet,
            "url_testada": url,
            "status_http": status,
            "url_final": final_url,
            "content_type": content_type,
            "entradas_rss": entries_count,
            "diagnostico": limitacao,
            "data_teste": now_iso
        })
    except requests.exceptions.Timeout:
        print(f"[{outlet}] {url} -> TIMEOUT (>8s)\n")
        results.append({
            "veiculo": outlet,
            "url_testada": url,
            "status_http": "TIMEOUT",
            "diagnostico": "Timeout na conexão (>8s)",
            "data_teste": now_iso
        })
    except Exception as e:
        print(f"[{outlet}] {url} -> ERRO: {e}\n")
        results.append({
            "veiculo": outlet,
            "url_testada": url,
            "status_http": "ERRO",
            "diagnostico": str(e),
            "data_teste": now_iso
        })

with open(r"audit_tests\probe_results.json", "w", encoding="utf-8") as f:
    json.dump({"probes": results}, f, indent=2, ensure_ascii=False)
