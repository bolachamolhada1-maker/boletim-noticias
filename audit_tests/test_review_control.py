import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import news_bot

class TestReviewControl(unittest.TestCase):
    """
    Grupo A: Testes do controle de envio no código news_bot.py.
    Simula respostas estruturadas do revisor para verificar se o sistema respeita
    aprovação, rejeição, correções e falhas técnicas.
    """

    def setUp(self):
        self.draft_data = {
            "panorama": "Panorama inicial do dia.",
            "noticias": [
                {
                    "titulo": "Notícia Aprovada 1",
                    "pais": "BR",
                    "tema": "Política",
                    "resumo_desenvolvido": "Resumo da notícia 1...",
                    "contexto": "Contexto da notícia 1...",
                    "consequencias": "Consequência 1",
                    "repercussao": "Repercussão 1",
                    "fonte_nome": "Folha de S.Paulo",
                    "fonte_url": "https://www1.folha.uol.com.br/poder/noticia1.shtml"
                },
                {
                    "titulo": "Notícia Que Será Rejeitada",
                    "pais": "BR",
                    "tema": "Economia",
                    "resumo_desenvolvido": "Resumo da notícia 2...",
                    "contexto": "Contexto da notícia 2...",
                    "consequencias": "Consequência 2",
                    "repercussao": "Repercussão 2",
                    "fonte_nome": "G1",
                    "fonte_url": "https://g1.globo.com/economia/noticia2.ghtml"
                },
                {
                    "titulo": "Notícia Que Precisa De Correção",
                    "pais": "MUNDO",
                    "tema": "Internacional",
                    "resumo_desenvolvido": "Texto incorreto original...",
                    "contexto": "Contexto 3...",
                    "consequencias": "Consequência 3",
                    "repercussao": "Repercussão 3",
                    "fonte_nome": "BBC News Brasil",
                    "fonte_url": "https://www.bbc.com/portuguese/noticia3"
                }
            ]
        }
        self.source_articles = [
            {"id": "id1", "source": "Folha de S.Paulo", "country": "BR", "title": "Notícia 1", "url": "https://www1.folha.uol.com.br/poder/noticia1.shtml", "published_at": "2026-11-05T12:00:00Z", "summary": "Fonte 1"},
            {"id": "id2", "source": "G1", "country": "BR", "title": "Notícia 2", "url": "https://g1.globo.com/economia/noticia2.ghtml", "published_at": "2026-11-05T12:00:00Z", "summary": "Fonte 2"},
            {"id": "id3", "source": "BBC News Brasil", "country": "WORLD", "title": "Notícia 3", "url": "https://www.bbc.com/portuguese/noticia3", "published_at": "2026-11-05T12:00:00Z", "summary": "Fonte 3"},
        ]

    @patch("google.generativeai.GenerativeModel")
    def test_a1_all_approved(self, mock_gen_model):
        """A1: Quando o revisor aprova todas as notícias, todas devem seguir para o envio."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "panorama_ok": true,
            "panorama_observacao": null,
            "revisoes": [
                {"titulo": "Notícia Aprovada 1", "status": "aprovada", "motivo": null, "correcao": null},
                {"titulo": "Notícia Que Será Rejeitada", "status": "aprovada", "motivo": null, "correcao": null},
                {"titulo": "Notícia Que Precisa De Correção", "status": "aprovada", "motivo": null, "correcao": null}
            ]
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_instance

        reviewed = news_bot.review_bulletin(self.draft_data, self.source_articles)
        self.assertIsNotNone(reviewed)
        self.assertEqual(len(reviewed["noticias"]), 3)
        self.assertEqual(reviewed["noticias"][0]["titulo"], "Notícia Aprovada 1")
        print("TESTE A1 PASSOU: 3 notícias aprovadas preservadas integralmente.")

    @patch("google.generativeai.GenerativeModel")
    def test_a2_item_rejected_is_excluded(self, mock_gen_model):
        """A2: Notícia com status 'rejeitada' deve ser excluída e nota adicionada ao panorama."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "panorama_ok": true,
            "panorama_observacao": null,
            "revisoes": [
                {"titulo": "Notícia Aprovada 1", "status": "aprovada", "motivo": null, "correcao": null},
                {"titulo": "Notícia Que Será Rejeitada", "status": "rejeitada", "motivo": "Fato não consta na fonte", "correcao": null},
                {"titulo": "Notícia Que Precisa De Correção", "status": "aprovada", "motivo": null, "correcao": null}
            ]
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_instance

        reviewed = news_bot.review_bulletin(self.draft_data, self.source_articles)
        self.assertIsNotNone(reviewed)
        self.assertEqual(len(reviewed["noticias"]), 2)
        titulos = [n["titulo"] for n in reviewed["noticias"]]
        self.assertNotIn("Notícia Que Será Rejeitada", titulos)
        self.assertIn("1 matéria(s) descartada(s)", reviewed["panorama"])
        print("TESTE A2 PASSOU: Notícia rejeitada foi excluída e nota inserida no panorama.")

    @patch("google.generativeai.GenerativeModel")
    def test_a3_correction_applied(self, mock_gen_model):
        """A3: Notícia com status 'precisa_correcao' e texto de correção tem resumo_desenvolvido atualizado."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "panorama_ok": true,
            "panorama_observacao": null,
            "revisoes": [
                {"titulo": "Notícia Aprovada 1", "status": "aprovada", "motivo": null, "correcao": null},
                {"titulo": "Notícia Que Será Rejeitada", "status": "aprovada", "motivo": null, "correcao": null},
                {"titulo": "Notícia Que Precisa De Correção", "status": "precisa_correcao", "motivo": "Dado numérico ajustado", "correcao": "Texto revisado e corrigido pelo auditor com sucesso."}
            ]
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_instance

        reviewed = news_bot.review_bulletin(self.draft_data, self.source_articles)
        self.assertIsNotNone(reviewed)
        self.assertEqual(len(reviewed["noticias"]), 3)
        item3 = [n for n in reviewed["noticias"] if n["titulo"] == "Notícia Que Precisa De Correção"][0]
        self.assertEqual(item3["resumo_desenvolvido"], "Texto revisado e corrigido pelo auditor com sucesso.")
        print("TESTE A3 PASSOU: Resumo corrigido substituiu o texto com erro.")

    @patch("google.generativeai.GenerativeModel")
    def test_a4_all_rejected(self, mock_gen_model):
        """A4: Quando todas as notícias são rejeitadas, a lista 'noticias' fica vazia."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "panorama_ok": true,
            "panorama_observacao": null,
            "revisoes": [
                {"titulo": "Notícia Aprovada 1", "status": "rejeitada", "motivo": "sem suporte", "correcao": null},
                {"titulo": "Notícia Que Será Rejeitada", "status": "rejeitada", "motivo": "sem suporte", "correcao": null},
                {"titulo": "Notícia Que Precisa De Correção", "status": "rejeitada", "motivo": "sem suporte", "correcao": null}
            ]
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_instance

        reviewed = news_bot.review_bulletin(self.draft_data, self.source_articles)
        self.assertIsNotNone(reviewed)
        self.assertEqual(len(reviewed["noticias"]), 0)
        print("TESTE A4 PASSOU: Todas as notícias rejeitadas resultaram em lista vazia.")

    @patch("google.generativeai.GenerativeModel")
    def test_a5_technical_failure_blocks_bulletin(self, mock_gen_model):
        """A5: Falha técnica na chamada do modelo (exceção em todos os modelos) retorna None."""
        mock_instance = MagicMock()
        mock_instance.generate_content.side_effect = Exception("Erro 503 Service Unavailable")
        mock_gen_model.return_value = mock_instance

        reviewed = news_bot.review_bulletin(self.draft_data, self.source_articles)
        self.assertIsNone(reviewed)
        print("TESTE A5 PASSOU: Falha do revisor retornou None (bloqueando envio).")

if __name__ == "__main__":
    unittest.main()
