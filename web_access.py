"""Leitura pública limitada. Valida destinos antes de cada redirecionamento."""

import ipaddress
import json
import re
import socket
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import requests

import config


EDITORIAL_ROOTS = {
    "bbc.com": "BBC News", "bbc.co.uk": "BBC News",
    "folha.uol.com.br": "Folha de S.Paulo", "folha.com.br": "Folha de S.Paulo",
    "estadao.com.br": "Estadão", "valor.globo.com": "Valor Econômico",
    "valor.com.br": "Valor Econômico", "g1.globo.com": "G1",
    "poder360.com.br": "Poder360", "nexojornal.com.br": "Nexo Jornal",
    "agencialupa.org": "Agência Lupa", "lupa.news": "Agência Lupa",
    "aosfatos.org": "Aos Fatos", "reuters.com": "Reuters", "apnews.com": "Associated Press — AP",
    "afp.com": "Agence France-Presse — AFP", "nytimes.com": "The New York Times",
    "wsj.com": "The Wall Street Journal", "ft.com": "Financial Times",
    "economist.com": "The Economist", "dw.com": "Deutsche Welle — DW",
}
TRANSPORT_HOSTS = {"feeds.bbci.co.uk", "feeds.folha.uol.com.br", "rss.nytimes.com",
                   "rss.dw.com", "pox.globo.com", "feeds.a.dj.com", "feeds.content.dowjones.io"}


def editorial_source(url):
    try:
        p = urlparse(url)
        host = p.hostname or ""
        if (p.scheme not in ("http", "https") or p.username or p.password or
                p.port not in (None, 80, 443) or host in TRANSPORT_HOSTS or host.startswith(("feeds.", "rss.", "redir."))):
            return None
        for root, name in EDITORIAL_ROOTS.items():
            if host == root or host.endswith("." + root):
                if root.startswith("bbc") and "/portuguese" in p.path:
                    return "BBC News Brasil"
                return name
        return None
    except (ValueError, TypeError):
        return None


def is_public_url(url):
    try:
        p = urlparse(url)
        if (p.scheme not in ("https", "http") or not p.hostname or p.username or p.password or
                p.port not in (None, 80, 443)):
            return False
        addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
    except (OSError, ValueError, TypeError):
        return False


class FetchError(RuntimeError):
    pass


def bounded_get(url, *, feed=False, max_bytes=None):
    """Sem cookies/autenticação, sem proxy do ambiente, sem redirecionamento automático.

    A validação DNS não é pinagem do socket. Não afirmamos proteção absoluta
    contra DNS rebinding de um domínio autorizado comprometido.
    """
    max_bytes = max_bytes or config.MAX_RESPONSE_BYTES
    started = time.monotonic()
    current = url
    with requests.Session() as session:
        session.trust_env = False
        for hop in range(config.MAX_REDIRECTS + 1):
            if time.monotonic() - started >= config.NETWORK_BUDGET_SECONDS:
                raise FetchError("orçamento de tempo excedido")
            if urlparse(current).scheme != "https":
                raise FetchError("transporte sem HTTPS não permitido")
            host = urlparse(current).hostname
            permitted = editorial_source(current) or (feed and host in TRANSPORT_HOSTS)
            if not permitted or not is_public_url(current):
                raise FetchError("destino não autorizado, não público ou DNS não resolvido")
            remaining = config.NETWORK_BUDGET_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                raise FetchError("orçamento de tempo excedido")
            with session.get(current, timeout=(min(4, remaining), min(8, remaining)), allow_redirects=False, stream=True,
                             headers={"User-Agent": "NewsBulletin/2.0", "Accept": "application/rss+xml, application/xml, text/html"}) as response:
                if time.monotonic() - started >= config.NETWORK_BUDGET_SECONDS:
                    raise FetchError("orçamento de tempo excedido")
                if response.status_code in (301, 302, 303, 307, 308):
                    if hop == config.MAX_REDIRECTS or not response.headers.get("Location"):
                        raise FetchError("limite de redirecionamentos")
                    current = urljoin(current, response.headers["Location"])
                    continue
                if response.status_code != 200:
                    raise FetchError(f"HTTP {response.status_code}")
                data = bytearray()
                # Um byte impede que um bloco grande retenha um fluxo lento
                # sem devolver controle para conferir o prazo. DNS e leituras
                # bloqueantes ainda dependem dos limites do sistema/requests.
                for chunk in response.iter_content(1):
                    if time.monotonic() - started >= config.NETWORK_BUDGET_SECONDS:
                        raise FetchError("orçamento de tempo excedido")
                    data.extend(chunk)
                    if len(data) > max_bytes:
                        raise FetchError("limite de bytes excedido")
                if time.monotonic() - started >= config.NETWORK_BUDGET_SECONDS:
                    raise FetchError("orçamento de tempo excedido")
                return bytes(data), current, response.headers.get("Content-Type", "")
    raise FetchError("redirecionamento inválido")


class PublicArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.article_depth = 0
        self.skip = 0
        self.paragraph = False
        self.parts = []
        self.json_blocks = []
        self.json_data = None
        self.canonical_urls = []
        self.article_records = []
        self.article_stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonical_urls.append(attrs.get("href", ""))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.json_data = []
        if tag in ("script", "style", "nav", "aside", "footer", "header"):
            self.skip += 1
        if tag == "article":
            self.article_depth += 1
            record = dict(attrs=attrs, parts=[], visible=[])
            self.article_records.append(record)
            self.article_stack.append(record)
        if tag == "p" and self.article_depth and not self.skip:
            self.paragraph = True

    def handle_endtag(self, tag):
        if tag == "script" and self.json_data is not None:
            self.json_blocks.append("".join(self.json_data))
            self.json_data = None
        if tag in ("script", "style", "nav", "aside", "footer", "header"):
            self.skip = max(0, self.skip - 1)
        if tag == "article":
            self.article_depth = max(0, self.article_depth - 1)
            if self.article_stack:
                self.article_stack.pop()
        if tag == "p":
            self.paragraph = False

    def handle_data(self, data):
        if self.json_data is not None:
            self.json_data.append(data)
        if self.paragraph and not self.skip:
            self.parts.append(data)
            if self.article_stack:
                self.article_stack[-1]["parts"].append(data)
        if self.article_stack and not self.skip:
            self.article_stack[-1]["visible"].append(data)


def _identity_url(value, base):
    """Compara identidades sem rede; preserva caminho/query semânticos."""
    if not isinstance(value, str) or not value.strip():
        return None
    if any(ord(c) < 32 or c == "\\" for c in value):
        return None
    try:
        parsed = urlparse(urljoin(base or "", value.strip()))
        if (parsed.scheme not in ("http", "https") or not parsed.hostname or
                parsed.username or parsed.password or parsed.port not in (None, 80, 443)):
            return None
        host = parsed.hostname.lower().encode("idna").decode("ascii")
        if parsed.port and (parsed.scheme, parsed.port) not in (("http", 80), ("https", 443)):
            host += f":{parsed.port}"
        query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                 if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid")]
        return urlunparse((parsed.scheme.lower(), host, parsed.path or "/", parsed.params,
                           urlencode(sorted(query)), ""))
    except (TypeError, ValueError, UnicodeError):
        return None


def extract_public_body(content, requested_url=None):
    parser = PublicArticleParser()
    parser.feed(content)

    def walk(node, seen=None):
        pending = [node]
        seen = set() if seen is None else seen
        while pending:
            current = pending.pop()
            if not isinstance(current, (list, dict)) or id(current) in seen:
                continue
            seen.add(id(current))
            if isinstance(current, list):
                pending.extend(reversed(current))
            elif isinstance(current, dict):
                yield current
                pending.extend(reversed(list(current.values())))

    nodes = []
    for block in parser.json_blocks:
        try:
            nodes.extend(walk(json.loads(block)))
        except RecursionError:
            return "", "metadados excedem a profundidade suportada"
        except (ValueError, TypeError):
            continue

    def identities(value):
        result, pending = [], [value]
        while pending:
            current = pending.pop()
            if isinstance(current, str):
                result.append(current)
            elif isinstance(current, list):
                pending.extend(current)
            elif isinstance(current, dict):
                pending.extend((current.get("url"), current.get("@id")))
        return result

    requested = _identity_url(requested_url, requested_url)
    if requested_url is not None and requested is None:
        return "", "identidade solicitada inválida"
    targets = {requested} if requested else set()
    canonical = {_identity_url(url, requested) for url in parser.canonical_urls} - {None}
    if len(canonical) > 1:
        return "", "canonical ambíguo; corpo não utilizado"
    # Canonical é alias declarado pela página; aceitar apenas na mesma origem.
    for url in canonical:
        if requested and urlparse(url).netloc == urlparse(requested).netloc and urlparse(url).path != "/":
            targets.add(url)

    articles = [n for n in nodes if isinstance(n.get("articleBody"), str) or
                any(str(t).rsplit("/", 1)[-1].endswith("Article") for t in
                    (n.get("@type") if isinstance(n.get("@type"), list) else [n.get("@type", "")]))]
    selected = []
    for node in articles:
        strong = identities(node.get("url")) + identities(node.get("mainEntityOfPage"))
        values = strong or identities(node.get("@id"))
        ids = {_identity_url(v, requested) for v in values} - {None}
        if requested and ids and ids <= targets:
            selected.append(node)
        elif not requested and len(articles) == 1:
            selected.append(node)  # compatibilidade do extrator isolado sem URL

    # Compartilhar a visita evita custo quadrático entre entidades selecionadas
    # aninhadas. Entidades relacionadas fora de hasPart continuam independentes.
    checked = set()
    restrictions = list(selected)
    for node in selected:
        restrictions.extend(walk(node.get("hasPart", []), checked))
    for part in restrictions:
        value = part.get("isAccessibleForFree")
        if value is False or (isinstance(value, str) and value.lower() == "false"):
            return "", "restrição declarada na matéria solicitada; corpo não utilizado"
    bodies = {n["articleBody"].strip() for n in selected
              if isinstance(n.get("articleBody"), str) and n["articleBody"].strip()}
    if len(bodies) > 1:
        return "", "entidades da matéria ambíguas; corpo não utilizado"
    if articles and not selected:
        return "", "entidade da matéria solicitada não identificada"

    dom = []
    for record in parser.article_records:
        attrs = record["attrs"]
        record_ids = {_identity_url(attrs[k], requested) for k in ("itemid", "about", "data-url") if attrs.get(k)} - {None}
        if (record_ids and record_ids <= targets) or (not record_ids and len(parser.article_records) == 1 and
                (not requested or bool(canonical & targets) or bool(selected))):
            dom.append(record)
    for record in dom:
        attrs = record["attrs"]
        visible = " ".join(record["visible"])
        if (attrs.get("data-access") in ("restricted", "subscriber") or attrs.get("data-paywall") == "true" or
                re.search(r"\b(assine para (ler|continuar)|subscribe to (read|continue))\b", visible, re.I)):
            return "", "restrição de acesso visível na matéria solicitada"
    if bodies:
        text = next(iter(bodies))
    elif len(dom) == 1:
        text = " ".join(dom[0]["parts"])
    else:
        return "", "corpo não identificado ou ambíguo"
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
    return text[:config.MAX_ARTICLE_CHARS], "corpo público extraído" if text else "corpo não identificado"


def enrich_candidates(articles):
    """Somente candidatos já selecionados; uma tentativa por artigo, teto global."""
    result = []
    started = time.monotonic()
    fetched = 0
    for raw in articles:
        a = dict(raw)
        a.setdefault("body", "")
        if (not a["body"] and len(a.get("summary", "").split()) < 160 and
                fetched < config.MAX_CONTENT_FETCHES and
                time.monotonic() - started < config.CONTENT_BUDGET_SECONDS):
            fetched += 1
            try:
                content, final_url, mime = bounded_get(a["url"])
                if "html" not in mime.lower():
                    raise FetchError("tipo de conteúdo não HTML")
                # Redirecionamento para login/home/outra matéria não muda a referência.
                from news_bot import normalize_url
                if normalize_url(final_url) != normalize_url(a["url"]):
                    raise FetchError("destino diferente; corpo não associado automaticamente")
                a["body"], a["content_access"] = extract_public_body(
                    content.decode("utf-8", errors="replace"), requested_url=a["url"])
            except (FetchError, requests.RequestException, ValueError) as exc:
                # Não registrar URLs de credenciais nem exceções de requests completas.
                a["content_access"] = str(exc) if isinstance(exc, FetchError) else type(exc).__name__
        a["evidence_level"] = "body" if a["body"] else "excerpt" if a.get("summary") else "title"
        result.append(a)
    return result
