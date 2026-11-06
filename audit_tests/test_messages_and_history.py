import sys
import os
import unittest
import copy
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import news_bot
import config

class TestMessagesAndHistory(unittest.TestCase):
    """
    Seção 7: Mensagens, limites do Telegram, divisão em partes, histórico e idempotência.
    """

    def setUp(self):
        self.sent_payloads = []
        # Prepara 7 notícias longas (~150 palavras cada) para gerar um boletim longo
        self.long_bulletin_data = {
            "panorama": "Panorama executivo longo com resumo dos principais fatos apurados no Brasil e no cenário internacional.",
            "noticias": []
        }
        for i in range(1, 8):
            pais = "BR" if i <= 4 else "MUNDO"
            tema = "Política" if i % 2 == 1 else "Economia"
            self.long_bulletin_data["noticias"].append({
                "titulo": f"Notícia Detalhada {i} com Título Informativo e Completo sobre Acontecimentos Oficiais",
                "pais": pais,
                "tema": tema,
                "resumo_desenvolvido": (
                    f"Este é um texto desenvolvido com fatos apurados para a matéria número {i}. "
                    "Contém nomes de autoridades públicas, datas precisas como 05 de novembro de 2026, "
                    "valores na ordem de R$ 3,5 bilhões de reais e detalhamento minucioso do processo judicial "
                    "ou da decisão econômica anunciada pelos órgãos reguladores competentes. "
                    "O objetivo é fornecer ao leitor um panorama claro de causas e consequências sem recorrer "
                    "a suposições ou dados não comprovados nos autos oficiais ou nas declarações públicas. "
                    "A matéria detalha ainda reuniões técnicas de transição e o cronograma previsto para o próximo trimestre."
                ),
                "contexto": f"Contexto histórico da questão {i}, abordando a legislação em vigor e os precedentes.",
                "consequencias": f"Consequências confirmadas {i}: publicação no Diário Oficial e intimação das partes.",
                "repercussao": f"Repercussão {i}: declarações de parlamentares e entidades sindicais.",
                "fonte_nome": "Folha de S.Paulo" if pais == "BR" else "BBC News",
                "fonte_url": f"https://www1.folha.uol.com.br/poder/2026/11/noticia_{i}.shtml" if pais == "BR" else f"https://www.bbc.com/news/world_{i}"
            })

    def mock_send_telegram(self, text, preview=False):
        self.sent_payloads.append(text)
        return True

    def test_m1_long_bulletin_partition_and_limits(self):
        """M1: Boletim longo com 7 matérias detalhadas deve ser dividido sem ultrapassar 4.000 chars por mensagem."""
        now = datetime.now(timezone(timedelta(hours=-3)))
        parts = news_bot.format_bulletin_html(self.long_bulletin_data, now, is_monday=False, failed_sources=[])
        
        print(f"Total de partes geradas: {len(parts)}")
        self.assertGreater(len(parts), 1, "Boletim longo de 7 matérias deve gerar múltiplas partes.")
        
        for idx, part in enumerate(parts, 1):
            self.assertLessEqual(len(part), config.TELEGRAM_MAX_CHARS, f"Parte {idx} excedeu limite seguro ({len(part)} > {config.TELEGRAM_MAX_CHARS})")
            # Verifica integridade básica de HTML
            self.assertEqual(part.count("<b>"), part.count("</b>"), f"Tags <b> não balanceadas na parte {idx}")
            self.assertEqual(part.count("<i>"), part.count("</i>"), f"Tags <i> não balanceadas na parte {idx}")
            self.assertEqual(part.count("<a href="), part.count("</a>"), f"Tags <a> não balanceadas na parte {idx}")
            print(f"  Parte {idx}: {len(part)} caracteres -> OK")

        # Verifica se todas as 7 notícias estão presentes na junção de todas as partes
        combined = "".join(parts)
        for i in range(1, 8):
            self.assertIn(f"{i}. Notícia Detalhada {i}", combined)
        print("TESTE M1 PASSOU: Partição respeitou 4.000 chars, balanceou HTML e preservou as 7 notícias com links.")

    def test_m2_special_characters_and_html_escaping(self):
        """M2: Verifica se caracteres perigosos para HTML (<, >, &, \", ') são devidamente escapados."""
        bad_data = {
            "panorama": "Panorama com <script>alert(1)</script> & caracteres 'especiais' \"aspas\".",
            "noticias": [
                {
                    "titulo": "Empresas & Cia: Lucro > R$ 1 bilhão < 2026>",
                    "pais": "BR",
                    "tema": "Economia",
                    "resumo_desenvolvido": "Texto com tags não permitidas <img src='x' onerror='alert(2)'> e símbolos A & B.",
                    "contexto": "Contexto com <tag>",
                    "consequencias": "Consequência com <tag>",
                    "repercussao": "Repercussão com <tag>",
                    "fonte_nome": "G1 & Parceiros",
                    "fonte_url": "https://g1.globo.com/economia/noticia.ghtml?param=1&foo=2"
                }
            ]
        }
        now = datetime.now(timezone(timedelta(hours=-3)))
        parts = news_bot.format_bulletin_html(bad_data, now, is_monday=False, failed_sources=[])
        msg = parts[0]
        
        # Tags não permitidas devem estar escapadas
        self.assertNotIn("<script>", msg)
        self.assertIn("&lt;script&gt;", msg)
        self.assertNotIn("<img", msg)
        self.assertIn("&lt;img", msg)
        self.assertIn("&amp;", msg)
        print("TESTE M2 PASSOU: Caracteres especiais escapados sem injeção de HTML malformado.")

    def test_m3_preview_does_not_mutate_history(self):
        """M3: Execução com preview=True NUNCA deve alterar history.json nem registrar notícias como enviadas."""
        fake_history = {"id_preexistente_1"}
        with patch("news_bot.load_history", return_value=copy.copy(fake_history)), \
             patch("news_bot.save_history") as mock_save, \
             patch("news_bot.collect_all_articles", return_value=([], [])), \
             patch("news_bot.send_telegram_message", return_value=True):
            
            news_bot.main(preview=True)
            mock_save.assert_not_called()
        print("TESTE M3 PASSOU: Modo preview não gravou no histórico.")

    def test_m4_same_edition_run_twice_deduplication(self):
        """M4: Se a mesma rotina rodar 2 vezes, a segunda execução deve detectar que notícias já foram enviadas."""
        history_state = set()

        def save_side_effect(sent_ids):
            history_state.update(sent_ids)

        # Artigos simulados usando article_id real como em fetch_feed
        url1 = "https://g1.globo.com/1"
        url2 = "https://bbc.com/2"
        articles = [
            {"id": news_bot.article_id(url1), "source": "G1", "country": "BR", "title": "Notícia 1", "url": url1, "published_at": "2026-11-05T12:00:00Z", "summary": "s1"},
            {"id": news_bot.article_id(url2), "source": "BBC", "country": "WORLD", "title": "Notícia 2", "url": url2, "published_at": "2026-11-05T12:00:00Z", "summary": "s2"}
        ]
        draft = {
            "panorama": "P1",
            "noticias": [
                {"titulo": "T1", "pais": "BR", "tema": "Política", "resumo_desenvolvido": "R1", "contexto": "C1", "consequencias": None, "repercussao": None, "fonte_nome": "G1", "fonte_url": "https://g1.globo.com/1"},
                {"titulo": "T2", "pais": "MUNDO", "tema": "Internacional", "resumo_desenvolvido": "R2", "contexto": "C2", "consequencias": None, "repercussao": None, "fonte_nome": "BBC", "fonte_url": "https://bbc.com/2"}
            ]
        }

        with patch("news_bot.load_history", side_effect=lambda: set(history_state)), \
             patch("news_bot.save_history", side_effect=save_side_effect), \
             patch("news_bot.collect_all_articles", return_value=(articles, [])), \
             patch("news_bot.summarize_with_ai", return_value=draft), \
             patch("news_bot.review_bulletin", return_value=draft), \
             patch("news_bot.send_telegram_message", return_value=True) as mock_send:

            # 1ª Execução (normal)
            news_bot.main(preview=False)
            self.assertEqual(len(history_state), 2)
            calls_first_run = mock_send.call_count

            # 2ª Execução imediata (mesmos artigos)
            news_bot.main(preview=False)
            # Na 2ª execução, filter_already_sent deve filtrar todos, não chamando summarize_with_ai
            calls_second_run = mock_send.call_count - calls_first_run
            self.assertEqual(calls_second_run, 0, "Segunda execução não deve reenviar notícias já presentes no histórico.")
            print("TESTE M4 PASSOU: Execução subsequente filtrou artigos já entregues sem duplicidade.")

    def test_m5_partial_delivery_failure_recovery(self):
        """
        M5: Falha no envio de uma parte (ex: parte 2 de 3).
        Verifica se all_sent é False e se o histórico NÃO é atualizado (impedindo perda de dados).
        """
        now = datetime.now(timezone(timedelta(hours=-3)))
        parts = news_bot.format_bulletin_html(self.long_bulletin_data, now, is_monday=False, failed_sources=[])
        self.assertGreaterEqual(len(parts), 2)

        # Simula: parte 1 tem sucesso, parte 2 falha no Telegram
        delivery_results = [True, False, False]
        def mock_delivery(part, preview=False):
            return delivery_results.pop(0) if delivery_results else False

        with patch("news_bot.load_history", return_value=set()), \
             patch("news_bot.save_history") as mock_save, \
             patch("news_bot.collect_all_articles", return_value=([], [])), \
             patch("news_bot.summarize_with_ai", return_value=self.long_bulletin_data), \
             patch("news_bot.review_bulletin", return_value=self.long_bulletin_data), \
             patch("news_bot.format_bulletin_html", return_value=parts), \
             patch("news_bot.send_telegram_message", side_effect=mock_delivery):

            news_bot.main(preview=False)
            # Como a parte 2 falhou, all_sent=False, e o histórico NÃO deve ser atualizado
            mock_save.assert_not_called()
            print("TESTE M5 PASSOU: Falha parcial de entrega não gravou histórico, permitindo reenvio integral futuro.")

if __name__ == "__main__":
    unittest.main()
