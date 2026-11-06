import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import news_bot

step_file = r'C:\Users\gabriel\.gemini\antigravity\brain\c2a0a49a-dc22-40fe-a3e6-7b1f7177b77d\.system_generated\steps\433\output.txt'
with open(step_file, 'r', encoding='utf-8') as f:
    text = f.read()

print("=" * 80)
print("RELATÓRIO DE ANÁLISE DA PRÉVIA REAL (PASSO 433)")
print("=" * 80)

# Check start and end times
start_m = re.search(r'START_TIME:\s*(\S+)', text)
end_m = re.search(r'END_TIME:\s*(\S+)', text)
print(f"Início UTC: {start_m.group(1) if start_m else 'N/A'}")
print(f"Fim UTC:    {end_m.group(1) if end_m else 'N/A'}")

# Extract parts
parts = re.findall(r'PRÉVIA GERADA \(modo preview ativado — não enviada\):\s*=+\n(.*?)\n=+', text, re.DOTALL)
print(f"Total de partes de mensagem geradas: {len(parts)}")

full_bulletin_text = "\n\n".join(parts)
print("\n" + "=" * 40 + " BOLETIM COMPLETO GERADO " + "=" * 40)
print(full_bulletin_text)
print("=" * 105 + "\n")

# Re-collect articles from feeds to match with URLs
articles, _ = news_bot.collect_all_articles(24)
articles_by_url = {news_bot.normalize_url(a['url']): a for a in articles}

# Find each news item block
item_pattern = re.compile(
    r'(🏛️|📈|🛡️|💻|🌐)\s*(🇧🇷|🌐)\s*<b>(\d+)\.\s*(.*?)</b>\s*<i>\((.*?)\)</i>\n(.*?)(?=\n\n(?:🏛️|📈|🛡️|💻|🌐)|─────────────────────|\Z)',
    re.DOTALL
)

items = item_pattern.findall(full_bulletin_text)
print(f"Total de notícias extraídas: {len(items)}\n")

for emoji, country_icon, num, title, theme, body in items:
    # clean HTML
    clean_body = re.sub(r'<[^>]+>', ' ', body)
    clean_body = re.sub(r'\s+', ' ', clean_body).strip()
    words = clean_body.split()
    title_words = title.split()
    total_words = len(title_words) + len(words)

    # Find URL
    url_match = re.search(r'href=["\']([^"\']+)["\']', body)
    url = url_match.group(1) if url_match else "URL NÃO ENCONTRADA"
    norm_url = news_bot.normalize_url(url)
    source_article = articles_by_url.get(norm_url)

    country_code = "BR" if "🇧🇷" in country_icon else "MUNDO"

    print(f"--- NOTÍCIA {num} ---")
    print(f"Título:               {title}")
    print(f"País:                 {country_code} ({country_icon})")
    print(f"Categoria/Tema:       {theme}")
    print(f"Palavras no Título:   {len(title_words)}")
    print(f"Palavras no Corpo:    {len(words)}")
    print(f"Total de Palavras:    {total_words} (faixa esperada: 100-160)")
    print(f"URL:                  {url}")
    
    if source_article:
        src_name = source_article['source']
        summary = source_article['summary']
        summary_len = len(summary.split())
        print(f"Fonte original:       {src_name}")
        print(f"Tamanho resumo RSS:   {summary_len} palavras ({len(summary)} caracteres)")
        if len(summary) < 100:
            material_type = "apenas título ou resumo ultracurto"
        elif summary_len < 60:
            material_type = "trecho / lead parcial"
        else:
            material_type = "trecho extenso / matéria substancial"
        print(f"Tipo de material:     {material_type}")
        print(f"Texto da fonte (RSS):\n  \"{summary[:300]}...\"" if len(summary) > 300 else f"Texto da fonte (RSS):\n  \"{summary}\"")
    else:
        print(f"Fonte original:       NÃO LOCALIZADA NO MAPA DE ARTIGOS COLETADOS!")

    print("\n")
