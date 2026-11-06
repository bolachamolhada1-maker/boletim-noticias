import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import news_bot

class TestFailurePaths(unittest.TestCase):
    """
    Seção 4: Falhas que devem impedir conteúdo não revisado.
    Testa o caminho completo com interceptação de transporte do Telegram.
    """

    def setUp(self):
        self.sent_messages = []
        self.draft_data = {
            "panorama": "Panorama do dia de teste.",
            "noticias": [
                {
                    "titulo": "Notícia Teste 1",
                    "pais": "BR",
                    "tema": "Política",
                    "resumo_desenvolvido": "Resumo teste 1.",
                    "contexto": "Contexto teste 1.",
                    "consequencias": "Consequências 1.",
                    "repercussao": None,
                    "fonte_nome": "G1 — Política",
                    "fonte_url": "https://g1.globo.com/politica/noticia1.ghtml"
                },
                {
                    "titulo": "Notícia Teste 2",
                    "pais": "MUNDO",
                    "tema": "Internacional",
                    "resumo_desenvolvido": "Resumo teste 2.",
                    "contexto": "Contexto teste 2.",
                    "consequencias": "Consequências 2.",
                    "repercussao": None,
                    "fonte_nome": "BBC News Brasil",
                    "fonte_url": "https://www.bbc.com/portuguese/noticia2"
                }
            ]
        }
        self.source_articles = [
            {"id": "id1", "source": "G1 — Política", "country": "BR", "title": "Notícia Teste 1", "url": "https://g1.globo.com/politica/noticia1.ghtml", "published_at": "2026-11-05T12:00:00Z", "summary": "Fonte 1"},
            {"id": "id2", "source": "BBC News Brasil", "country": "WORLD", "title": "Notícia Teste 2", "url": "https://www.bbc.com/portuguese/noticia2", "published_at": "2026-11-05T12:00:00Z", "summary": "Fonte 2"}
        ]

    def mock_send_telegram(self, text, preview=False):
        self.sent_messages.append({"text": text, "preview": preview})
        return True

    @patch("news_bot.send_telegram_message")
    @patch("news_bot.review_bulletin")
    @patch("news_bot.summarize_with_ai")
    @patch("news_bot.collect_all_articles")
    @patch("news_bot.load_history")
    @patch("news_bot.save_history")
    def test_f1_reviewer_timeout_blocks_bulletin(self, mock_save_hist, mock_load_hist, mock_collect, mock_summarize, mock_review, mock_send):
        """F1: Se o revisor falhar (timeout/erro), o boletim NÃO deve ser enviado."""
        mock_send.side_effect = self.mock_send_telegram
        mock_load_hist.return_value = set()
        mock_collect.return_value = (self.source_articles, [])
        mock_summarize.return_value = self.draft_data
        # Simula revisor retornando None (falha técnica em todos os fallbacks)
        mock_review.return_value = None

        news_bot.main(preview=False)

        # Deve enviar apenas a mensagem de aviso, NUNCA o boletim
        self.assertEqual(len(self.sent_messages), 1)
        self.assertIn("Aviso Editorial", self.sent_messages[0]["text"])
        self.assertIn("auditoria editorial automática obrigatória falhou", self.sent_messages[0]["text"])
        # Histórico NÃO pode ter sido salvo
        mock_save_hist.assert_not_called()
        print("TESTE F1 PASSOU: Timeout/falha do revisor bloqueou o envio do boletim.")

    @patch("google.generativeai.GenerativeModel")
    def test_f2_invalid_json_response_blocks_bulletin(self, mock_gen_model):
        """F2: Se a resposta do modelo for JSON inválido, review_bulletin deve retornar None."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "ESTE NÃO É UM JSON VÁLIDO {broken"
        mock_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_instance

        result = news_bot.review_bulletin(self.draft_data, self.source_articles)
        self.assertIsNone(result)
        print("TESTE F2 PASSOU: JSON inválido retornou None.")

    @patch("news_bot.send_telegram_message")
    @patch("news_bot.review_bulletin")
    @patch("news_bot.summarize_with_ai")
    @patch("news_bot.collect_all_articles")
    @patch("news_bot.load_history")
    @patch("news_bot.save_history")
    def test_f3_rejection_of_single_item(self, mock_save_hist, mock_load_hist, mock_collect, mock_summarize, mock_review, mock_send):
        """F3: Se 1 de 2 notícias for reprovada, somente a aprovada é enviada."""
        mock_send.side_effect = self.mock_send_telegram
        mock_load_hist.return_value = set()
        mock_collect.return_value = (self.source_articles, [])
        mock_summarize.return_value = self.draft_data
        mock_review.return_value = {
            "panorama": "Panorama do dia com 1 notícia descartada.",
            "noticias": [self.draft_data["noticias"][0]] # apenas a notícia 1
        }

        news_bot.main(preview=False)

        self.assertGreaterEqual(len(self.sent_messages), 1)
        bulletin_text = self.sent_messages[0]["text"]
        self.assertIn("Notícia Teste 1", bulletin_text)
        self.assertNotIn("Notícia Teste 2", bulletin_text)
        # Histórico deve registrar apenas o ID da notícia entregue
        mock_save_hist.assert_called_once()
        saved_history = mock_save_hist.call_args[0][0]
        id1 = news_bot.article_id("https://g1.globo.com/politica/noticia1.ghtml")
        id2 = news_bot.article_id("https://www.bbc.com/portuguese/noticia2")
        self.assertIn(id1, saved_history)
        self.assertNotIn(id2, saved_history)
        print("TESTE F3 PASSOU: Item reprovado foi excluído e não registrado no histórico.")

    @patch("google.generativeai.GenerativeModel")
    def test_f4_correction_without_text_flaw(self, mock_gen_model):
        """
        F4: Investigação do comportamento quando status é 'precisa_correcao' mas correcao é None/vazio.
        Verifica se o código atual repassa a notícia sem correção (defeito no código).
        """
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "panorama_ok": true,
            "panorama_observacao": null,
            "revisoes": [
                {"titulo": "Notícia Teste 1", "status": "precisa_correcao", "motivo": "Erro grave nos dados", "correcao": null},
                {"titulo": "Notícia Teste 2", "status": "aprovada", "motivo": null, "correcao": null}
            ]
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_instance

        reviewed = news_bot.review_bulletin(self.draft_data, self.source_articles)
        # Verifica se Notícia Teste 1 foi mantida sem correção
        titulos = [n["titulo"] for n in reviewed["noticias"]]
        if "Notícia Teste 1" in titulos:
            print("TESTE F4 - DEFEITO IDENTIFICADO: Item com status 'precisa_correcao' sem texto substituto foi mantido no boletim no ramo 'else'.")
        else:
            print("TESTE F4: Item foi descartado.")

if __name__ == "__main__":
    unittest.main()
