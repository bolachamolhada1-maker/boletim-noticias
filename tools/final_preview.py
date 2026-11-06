"""One bounded real preview, isolated from Telegram and production writes."""
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import news_bot as bot
import config
from editorial import TEXT_FIELDS, bind_item

class StopPreview(BaseException):
    pass

def hashes():
    return {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None
            for p in ('history.json', 'delivery_state.json')}

def main():
    report = dict(started_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                  model=config.GEMINI_MODEL, calls=[], errors=[], production_before=hashes(), parts=[], BR=0, MUNDO=0)
    start = time.monotonic()
    original_collect, original_build = bot.collect_all_articles, bot.build_reviewed_bulletin
    def collect(*args, **kwargs):
        articles, observations = original_collect(*args, **kwargs)
        report['collected'] = len(articles)
        report['feed_observations'] = observations
        return articles, observations
    def call(instruction, payload, review=False):
        if len(report['calls']) >= 8:
            report['errors'].append(dict(kind='budget', message='Eight real AI calls reached'))
            raise StopPreview()
        stage = ('review' if review else 'generation' if 'eligible_ids' in payload else 'panorama' if 'noticias' in payload else 'confirmation')
        record = dict(number=len(report['calls'])+1, stage=stage, model=config.GEMINI_MODEL)
        report['calls'].append(record)
        tick = time.monotonic()
        try:
            bot.genai.configure(api_key=bot.GEMINI_API_KEY)
            response = bot.genai.GenerativeModel(config.GEMINI_MODEL, system_instruction=instruction).generate_content(
                json.dumps(payload, ensure_ascii=False),
                generation_config=bot.genai.types.GenerationConfig(temperature=0.1 if review else 0.2, max_output_tokens=8500, response_mime_type='application/json'),
                request_options={'timeout': config.GEMINI_TIMEOUT_SECONDS, 'retry': None})
            record['http'] = 'service response received'
        except Exception as exc:
            code = getattr(exc, 'code', None)
            report['errors'].append(dict(kind='external', type=type(exc).__name__, code=str(code)))
            raise StopPreview()
        finally:
            record['seconds'] = round(time.monotonic()-tick, 3)
        try:
            result = json.loads(response.text)
            if not isinstance(result, dict):
                raise ValueError('JSON is not object')
        except Exception as exc:
            report['errors'].append(dict(kind='local_parsing', type=type(exc).__name__))
            raise StopPreview()
        record['parsing'] = 'valid JSON object'
        if stage == 'generation':
            sources = payload['catalogo']
            record['vacancies'] = payload['vagas']
            record['excluded_ids'] = payload['excluded_ids']
            record['eligible_count'] = len(payload['eligible_ids'])
            record['proposals'] = []
            for n in result.get('noticias', []):
                if not isinstance(n, dict):
                    record['proposals'].append(dict(valid=False, reason='not object'))
                    continue
                evidence = ' '.join(a.get('body') or a.get('summary') or '' for a in sources if a['id'] in n.get('evidence_ids', []))
                words = sum(len(str(n.get(k) or '').split()) for k in TEXT_FIELDS)
                budget = min(180, max(60, int(len(evidence.split())*1.7)))
                record['proposals'].append(dict(id=n.get('article_id'), country=n.get('pais'), valid=bind_item(n, sources) is not None,
                    words=words, budget=budget, over_word_budget=words > budget))
        if review:
            record['verdicts'] = [{k: r.get(k) for k in ('article_id','version','status','motivo','duplicada_de','fonte_suspeita')} for r in result.get('revisoes', []) if isinstance(r,dict)]
            record['panorama_ok'] = result.get('panorama_ok')
        return result
    def build(candidates, monday):
        report['candidates'] = [{k:a.get(k) for k in ('id','country','evidence_level','content_access')} for a in candidates]
        result = original_build(candidates, monday)
        if result:
            for country in ('BR','MUNDO'):
                report[country] = sum(n['pais']==country for n in result['noticias'])
            report['shortages'] = result.get('shortages')
        else:
            report['errors'].append(dict(kind='local_validation', message='Editorial pipeline did not approve a bulletin'))
        return result
    def send(text, preview=False):
        if not preview:
            raise StopPreview('Telegram blocked')
        report['parts'].append(text)
        return dict(status='preview')
    original_print = print
    def capture_print(value='', *args, **kwargs):
        if isinstance(value, str) and value.startswith('<i>[Parte '):
            report['parts'].append(value)
        original_print(value, *args, **kwargs)
    def blocked(*a, **kw):
        raise StopPreview('Production mutation blocked')
    try:
        with patch('builtins.print',side_effect=capture_print), patch.object(bot,'collect_all_articles',side_effect=collect), patch.object(bot,'build_reviewed_bulletin',side_effect=build), patch.object(bot,'call_gemini_json',side_effect=call), patch.object(bot,'send_telegram_message',side_effect=send), patch('requests.post',side_effect=blocked), patch('subprocess.run',side_effect=blocked), patch('delivery_state.atomic_json',side_effect=blocked), patch('delivery_state.git_checkpoint',side_effect=blocked), patch.object(bot,'save_history',side_effect=blocked):
            report['exit_code'] = bot.main(preview=True)
    except StopPreview:
        report['exit_code'] = 4
    finally:
        report['duration_seconds'] = round(time.monotonic()-start,3)
        report['production_after'] = hashes()
        report['production_unchanged'] = report['production_before']==report['production_after']
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        (ROOT/'docs/final-preview-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if report['parts']:
            (ROOT/'docs/final-preview.html').write_text('<meta charset="utf-8"><pre>'+ '\n\n'.join(report['parts'])+'</pre>',encoding='utf-8')
        print(json.dumps({k:report[k] for k in ('exit_code','duration_seconds','BR','MUNDO','errors','production_unchanged')}))
    return report['exit_code']

if __name__=='__main__':
    sys.exit(main())
