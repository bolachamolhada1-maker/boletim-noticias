"""HTML com divisões balanceadas e rastreabilidade de artigos por parte."""
import html
import re
from datetime import datetime, timezone, timedelta

import config


class MessagePart(str):
    def __new__(cls, text, article_ids=()):
        obj = super().__new__(cls, text)
        obj.article_ids = tuple(sorted(set(article_ids)))
        return obj


def size(text):
    # Contagem conservadora: inclui markup e entidades, em unidades UTF-16.
    return len(text.encode("utf-16-le")) // 2


def split_html(block, limit):
    if size(block) <= limit:
        return [block]
    parts, stack, current = [], [], ""
    tokens = re.findall(r"<[^>]+>|(?:&(?:#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z]+);|[^<&\s])+|\s+|[<&]", block)
    # Texto extenso pode ser dividido sem perder caracteres ou quebrar entidades.
    # Tags e atributos continuam indivisíveis.
    expanded = []
    for token in tokens:
        if not token.startswith("<") and size(token) > limit // 2:
            expanded.extend(re.findall(r"&(?:#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z]+);|.", token, re.S))
        else:
            expanded.append(token)
    tokens = expanded

    def closing(tags):
        return "".join(f"</{name}>" for name, opening in reversed(tags))

    for token in tokens:
        next_stack = list(stack)
        if token.startswith("<") and token.endswith(">"):
            if token.startswith("</"):
                name = token[2:-1]
                if not next_stack or next_stack[-1][0] != name:
                    raise ValueError("HTML gerado não balanceado")
                next_stack.pop()
            else:
                name = token[1:-1].split()[0]
                if name not in ("b", "i", "a"):
                    raise ValueError("Tag não permitida")
                next_stack.append((name, token))
        if size(current + token + closing(next_stack)) > limit:
            if not current:
                raise ValueError("Token HTML maior que o limite")
            parts.append(current + closing(stack))
            current = "".join(opening for name, opening in stack)
            if size(current + token + closing(next_stack)) > limit:
                raise ValueError("Tag/link maior que o limite")
        current += token
        stack = next_stack
    if stack:
        raise ValueError("HTML gerado não encerrado")
    if current:
        parts.append(current)
    return parts


def format_bulletin_html(data, edition_date, is_monday, failed_sources):
    brt = timezone(timedelta(hours=-3))
    date = edition_date.astimezone(brt).strftime("%d/%m/%Y")
    header = f"📰 <b>Boletim de notícias — {date}</b>"
    if is_monday:
        header += "\n<i>Retrospectiva do fim de semana com atualizações da segunda-feira. Cobertura: últimas 72 horas.</i>"
    else:
        header += "\n<i>Cobertura: últimas 24 horas.</i>"
    blocks = [(header + "\n\n<b>Panorama:</b>\n" + html.escape(data["panorama"]), ())]
    for idx, n in enumerate(data["noticias"], 1):
        country = "Brasil" if n["pais"] == "BR" else "Internacional"
        text = f"\n\n<b>{idx}. {html.escape(n['titulo'])}</b>\n<i>{country} • {html.escape(n['tema'])}</i>\n"
        text += html.escape(n["resumo_desenvolvido"])
        for field, label in (("contexto", "Contexto"), ("consequencias", "Consequências e próximos passos"),
                             ("repercussao", "Repercussão"), ("limitacao", "Limitação da evidência"),
                             ("divergencias", "Divergências nas fontes")):
            if n.get(field):
                text += f"\n\n<b>{label}:</b> {html.escape(n[field])}"
        text += f'\n\n🔗 <a href="{html.escape(n["fonte_url"], quote=True)}">{html.escape(n["fonte_nome"])}</a>'
        blocks.append((text, (n.get("article_id", ""),)))
    footer = "\n\n─────────────────────"
    shortages = data.get("shortages", {})
    if any(shortages.values()):
        footer += ("\nMaterial comprovável insuficiente para completar as cotas: "
                   f"faltam {shortages.get('BR', 0)} do Brasil e {shortages.get('MUNDO', 0)} internacionais. "
                   "Janela temporal mantida.")
    if failed_sources:
        observations = [f"{o['url']}: {o['result']}" if isinstance(o, dict) else str(o) for o in failed_sources]
        footer += "\n<i>Observações por feed nesta coleta: " + html.escape("; ".join(observations)) + ".</i>"
    reviewed_at = data.get("approval", {}).get("reviewed_at")
    if reviewed_at:
        reviewed = datetime.fromisoformat(reviewed_at).astimezone(brt).strftime("%d/%m/%Y às %H:%M:%S")
        footer += f"\n<i>Revisão de fidelidade às evidências concluída em {reviewed} (Brasília).</i>"
    blocks.append((footer, ()))
    budget = config.TELEGRAM_MAX_CHARS - 80
    raw_parts, current, ids = [], "", set()
    for block, article_ids in blocks:
        for fragment in split_html(block, budget):
            if current and size(current + fragment) > budget:
                raw_parts.append(MessagePart(current, ids))
                current, ids = "", set()
            current += fragment
            ids.update(x for x in article_ids if x)
    if current:
        raw_parts.append(MessagePart(current, ids))
    total = len(raw_parts)
    return [MessagePart(f"<i>[Parte {i}/{total}]</i>\n" + str(p), p.article_ids)
            for i, p in enumerate(raw_parts, 1)]
