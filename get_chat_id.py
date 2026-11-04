"""
get_chat_id.py — Script auxiliar de configuração.

Execute este script UMA VEZ depois de enviar qualquer mensagem
para o seu bot @jornaltom_bot no Telegram.

Ele mostrará o seu Chat ID, que você deve:
1. Copiar
2. Colar no arquivo .env no campo TELEGRAM_CHAT_ID=
3. Adicionar como segredo no GitHub (ver README.md)

Uso:
  python get_chat_id.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("ERRO: TELEGRAM_BOT_TOKEN não encontrado no arquivo .env")
    exit(1)

print("Buscando atualizações do bot...")
resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=10)
data = resp.json()

if not data.get("ok"):
    print(f"Erro na API do Telegram: {data}")
    exit(1)

results = data.get("result", [])

if not results:
    print(
        "\n❌ Nenhuma mensagem encontrada.\n"
        "Por favor:\n"
        "  1. Abra o Telegram\n"
        "  2. Busque por @jornaltom_bot\n"
        "  3. Clique em 'Iniciar' ou envie qualquer mensagem\n"
        "  4. Execute este script novamente\n"
    )
    exit(1)

print("\n✅ Mensagens encontradas! Seus dados:\n")
seen = set()
for update in results:
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        continue
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "")
    chat_name = chat.get("first_name") or chat.get("title") or chat.get("username") or "Desconhecido"

    if chat_id not in seen:
        seen.add(chat_id)
        print(f"  Chat: {chat_name} ({chat_type})")
        print(f"  Chat ID: {chat_id}")
        print()

print("👉 Copie o 'Chat ID' acima e cole no arquivo .env:")
print("   TELEGRAM_CHAT_ID=<número_aqui>")
print()
print("Depois adicione também como segredo 'TELEGRAM_CHAT_ID' no GitHub.")
