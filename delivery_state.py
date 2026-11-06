"""Histórico compatível e outbox durável por edição/parte.

Antes de POST, `sending` precisa estar confirmado no armazenamento durável.
Sem confirmação posterior, a parte fica incerta e exige reconciliação humana.
"""

import copy
import json
import os
import re
import subprocess
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import config
from editorial import digest


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def telegram_destination_matches(destination, chat_id, username=None):
    """Destino congelado pode ser ID ou @username; recibo guarda o ID real."""
    if not isinstance(destination, str) or not destination:
        return False
    if destination.startswith("@"):
        return (isinstance(username, str) and
                re.fullmatch(r"[A-Za-z0-9_]{5,32}", destination[1:]) is not None and
                re.fullmatch(r"-?[0-9]+", str(chat_id)) is not None and
                username.casefold() == destination[1:].casefold())
    return str(chat_id) == destination


def valid_date(value):
    if not isinstance(value, str):
        raise ValueError("Data inválida no estado")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Data sem fuso no estado")
    return dt


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Estado ilegível/corrompido: {Path(path).name}; restaure antes de enviar") from exc


def history_data():
    if not Path(config.HISTORY_FILE).exists():
        return dict(sent_ids=[], sent_at={})
    data = read_json(config.HISTORY_FILE)
    if (not isinstance(data, dict) or not isinstance(data.get("sent_ids"), list) or
            any(not isinstance(x, str) or not x for x in data["sent_ids"]) or
            len(set(data["sent_ids"])) != len(data["sent_ids"])):
        raise ValueError("Esquema de histórico inválido")
    dates = data.get("sent_at")
    if dates is None:
        # IDs legados não têm horário individual; não inventar cronologia entre eles.
        old_date = data.get("updated_at", "1970-01-01T00:00:00+00:00")
        valid_date(old_date)
        dates = {ident: old_date for ident in data["sent_ids"]}
    if not isinstance(dates, dict) or set(dates) != set(data["sent_ids"]):
        raise ValueError("Datas do histórico incompatíveis com IDs")
    for date in dates.values():
        valid_date(date)
    return dict(sent_ids=data["sent_ids"], sent_at=dates)


def load_history():
    return set(history_data()["sent_ids"])


def save_history(sent_ids):
    if not isinstance(sent_ids, set) or any(not isinstance(x, str) or not x for x in sent_ids):
        raise ValueError("IDs de histórico inválidos")
    old = history_data()
    now = utcnow()
    dates = {ident: old["sent_at"].get(ident, now) for ident in sent_ids}
    ordered = sorted(dates, key=lambda ident: (-valid_date(dates[ident]).timestamp(), ident))
    kept = ordered[:config.HISTORY_MAX_ENTRIES]
    atomic_json(config.HISTORY_FILE, dict(schema_version=2, sent_ids=kept,
        sent_at={ident: dates[ident] for ident in kept}, total_sent=len(kept), updated_at=now))


@contextmanager
def execution_lock(path=".delivery.lock"):
    """Trava liberada pelo SO mesmo em crash. Workflow serializa runners distintos."""
    with open(path, "a+b") as handle:
        handle.seek(0)
        if handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Outra execução já está usando este estado") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def git_checkpoint():
    """Sem force/rebase/merge automático: conflito de estado bloqueia próximos POSTs."""
    if os.getenv("BOT_PERSIST_GIT") != "1":
        if os.getenv("GITHUB_ACTIONS") == "true":
            raise RuntimeError("Runner sem persistência Git habilitada")
        return

    def git(*args):
        result = subprocess.run(["git", *args], capture_output=True, text=True, timeout=45,
                                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        if result.returncode:
            raise RuntimeError("Checkpoint Git falhou em " + args[0])
        return result.stdout.strip()

    branch = os.getenv("BOT_STATE_BRANCH", "main")
    if git("branch", "--show-current") != branch:
        raise RuntimeError("Checkout diferente da branch de estado")
    paths = [str(Path(p).as_posix()) for p in (config.HISTORY_FILE, config.DELIVERY_STATE_FILE)
             if Path(p).exists()]
    staged = git("diff", "--cached", "--name-only").splitlines()
    if set(staged) - set(paths):
        raise RuntimeError("Checkpoint recusou alterações staged fora do estado")
    if paths:
        git("add", "--", *paths)
        if git("diff", "--cached", "--name-only"):
            git("-c", "user.name=github-actions[bot]", "-c",
                "user.email=github-actions[bot]@users.noreply.github.com", "commit", "-m",
                "chore(state): checkpoint de entrega [skip ci]", "--", *paths)
    # Mesmo sem novo diff, um commit anterior pode ter falhado no push.
    git("push", "origin", f"HEAD:refs/heads/{branch}")
    local = git("rev-parse", "HEAD")
    remote = git("ls-remote", "origin", f"refs/heads/{branch}").split()
    if not remote or remote[0] != local:
        raise RuntimeError("Checkpoint remoto não confirmou o commit local")


class DeliveryStore:
    def __init__(self, path=None):
        self.path = Path(path or config.DELIVERY_STATE_FILE)
        self.data = read_json(self.path) if self.path.exists() else dict(schema_version=1, editions=[])
        self.validate()

    def validate(self):
        data = self.data
        if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("editions"), list):
            raise ValueError("Esquema de entregas inválido")
        seen = set()
        try:
            for edition in data["editions"]:
                ident = edition["id"]
                if not isinstance(ident, str) or ident in seen:
                    raise ValueError("Edição duplicada/inválida")
                seen.add(ident)
                if not edition["parts"] or not isinstance(edition["destination"], str):
                    raise ValueError("Edição sem partes/destinatário")
                valid_date(edition["created_at"])
                frozen = dict(key=edition["key"], destination=edition["destination"],
                              editorial=edition["editorial"],
                              parts=[dict(text=p["text"], article_ids=p["article_ids"]) for p in edition["parts"]])
                if digest(frozen) != edition["manifest_hash"]:
                    raise ValueError("Conteúdo congelado adulterado")
                for idx, part in enumerate(edition["parts"]):
                    if (part["id"] != f"{ident}:{idx+1}" or not isinstance(part["text"], str) or
                            not isinstance(part["article_ids"], list) or
                            any(not isinstance(x, str) for x in part["article_ids"]) or
                            part["status"] not in ("pending", "sending", "sent", "uncertain")):
                        raise ValueError("Parte inválida")
                    if part["status"] == "sent":
                        if (type(part.get("message_id")) is not int or part["message_id"] <= 0 or
                                not telegram_destination_matches(edition["destination"], part.get("chat_id"),
                                                                 part.get("chat_username"))):
                            raise ValueError("Confirmação Telegram inválida")
                        valid_date(part["sent_at"])
                statuses = [p["status"] for p in edition["parts"]]
                if edition["status"] not in ("pending", "partial", "complete") or (edition["status"] == "complete" and any(s != "sent" for s in statuses)):
                    raise ValueError("Situação da edição incompatível")
        except (KeyError, TypeError) as exc:
            raise ValueError("Estado de entregas incompleto") from exc

    def checkpoint(self):
        self.validate()
        atomic_json(self.path, self.data)
        git_checkpoint()

    def unfinished(self):
        return next((e for e in self.data["editions"] if e["status"] != "complete"), None)

    def for_key(self, key):
        return next((e for e in self.data["editions"] if e["key"] == key), None)

    def create(self, key, parts, destination, editorial):
        if self.unfinished() or self.for_key(key):
            raise ValueError("Edição existente deve ser retomada")
        frozen = dict(key=key, parts=copy.deepcopy(parts), destination=str(destination),
                      editorial=copy.deepcopy(editorial))
        ident = digest(dict(key=key, destination=str(destination)))[:24]
        edition = dict(id=ident, key=key, destination=str(destination), created_at=utcnow(),
                       status="pending", editorial=frozen["editorial"], manifest_hash=digest(frozen),
                       parts=[dict(**part, id=f"{ident}:{i+1}", status="pending") for i, part in enumerate(parts)])
        complete = [e for e in self.data["editions"] if e["status"] == "complete"]
        complete = sorted(complete, key=lambda e: (e["created_at"], e["id"]))[-max(0, config.DELIVERY_MAX_EDITIONS-1):]
        self.data["editions"] = complete + [edition]
        self.checkpoint()
        return edition

    def record_confirmed_articles(self, edition):
        required = {}
        for part in edition["parts"]:
            for ident in part["article_ids"]:
                required.setdefault(ident, []).append(part["status"] == "sent")
        delivered = {ident for ident, confirmations in required.items() if all(confirmations)}
        if delivered:
            save_history(load_history() | delivered)

    def deliver(self, edition, sender):
        self.validate()
        load_history()  # corrupção bloqueia também retomadas antes do primeiro POST
        # Após reinício, `sending` não prova que o Telegram não recebeu.
        for part in edition["parts"]:
            if part["status"] == "sending":
                part["status"] = "uncertain"
                part["error"] = "interrompido sem confirmação persistida"
        if any(p["status"] == "uncertain" for p in edition["parts"]):
            edition["status"] = "partial"
            self.checkpoint()
            return "partial"
        self.record_confirmed_articles(edition)
        for part in edition["parts"]:
            if part["status"] == "sent":
                continue
            part["status"] = "sending"
            part["attempted_at"] = utcnow()
            edition["status"] = "partial"
            self.checkpoint()  # confirmação REMOTA necessária antes do POST
            result = sender(part["text"])
            if not isinstance(result, dict) or result.get("status") not in ("sent", "pending", "uncertain"):
                result = dict(status="uncertain", error="resultado de transporte inválido")
            if result["status"] == "sent":
                if (type(result.get("message_id")) is not int or result["message_id"] <= 0 or
                        not telegram_destination_matches(edition["destination"], result.get("chat_id"),
                                                         result.get("chat_username"))):
                    result = dict(status="uncertain", error="confirmação incompatível")
                else:
                    part.update(status="sent", message_id=result["message_id"],
                                chat_id=str(result["chat_id"]), sent_at=utcnow())
                    if result.get("chat_username") is not None:
                        part["chat_username"] = result["chat_username"]
            if result["status"] != "sent":
                part.update(status=result["status"], error=result.get("error", "falha"))
            self.record_confirmed_articles(edition)
            if all(p["status"] == "sent" for p in edition["parts"]):
                edition["status"] = "complete"
            self.checkpoint()
            if result["status"] != "sent":
                return "partial"
            if any(p["status"] == "pending" for p in edition["parts"]):
                time.sleep(config.TELEGRAM_PART_DELAY_SECONDS)
        edition["status"] = "complete"
        self.checkpoint()
        return "complete"


if __name__ == "__main__":
    # Usado no step always() do Actions; falhas de push continuam sendo erros.
    git_checkpoint()
