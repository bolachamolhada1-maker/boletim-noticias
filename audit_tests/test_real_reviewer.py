import sys
import os
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import news_bot

load_dotenv()

def run_real_reviewer_tests():
    print("=" * 80)
    print("GRUPO B: TESTES DA CAPACIDADE EDITORIAL DO REVISOR REAL COM IA")
    print("=" * 80)

    # 1. Artigos-fonte de referência controlados
    source_articles = [
        {
            "id": "src_master",
            "source": "Folha de S.Paulo — Mercado",
            "country": "BR",
            "title": "Governo do DF acusa Master de gestão fraudulenta, se diz vítima e pede transferência de R$ 2 bi bloqueados",
            "url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master-de-gestao-fraudulenta.shtml",
            "published_at": "2026-11-05T18:43:00Z",
            "summary": "O governo do Distrito Federal pediu ao STF (Supremo Tribunal Federal) que R$ 2,2 bilhões bloqueados no âmbito de investigações do Banco Master sejam transferidos ao BRB (Banco de Brasília). Para isso, o DF se diz vítima do esquema de gestão fraudulenta."
        },
        {
            "id": "src_midterms",
            "source": "BBC News — World",
            "country": "WORLD",
            "title": "US midterm election results alter congressional balance",
            "url": "https://www.bbc.com/news/world-us-canada-67890",
            "published_at": "2026-11-05T14:00:00Z",
            "summary": "The US midterm elections have reshaped the congressional balance of power. President Joe Biden faces divided government, while Donald Trump suffered notable setbacks among his endorsed candidates across key swing states."
        }
    ]

    # Casos de teste
    test_cases = [
        {
            "id": "B0_CONTROLE",
            "name": "Controle (Fiel à fonte, sem adulteração)",
            "adulteracao": "Nenhuma (reprodução fiel dos fatos).",
            "item": {
                "titulo": "Governo do DF acusa Banco Master de gestão fraudulenta e pede R$ 2,2 bi ao STF",
                "pais": "BR",
                "tema": "Economia",
                "resumo_desenvolvido": "O governo do Distrito Federal ingressou com um pedido perante o Supremo Tribunal Federal (STF) para que R$ 2,2 bilhões atualmente bloqueados em investigações relativas ao Banco Master sejam redirecionados ao BRB (Banco de Brasília). A administração distrital sustenta ter sido lesada pelo esquema de gestão fraudulenta na instituição financeira.",
                "contexto": "O caso envolve a recuperação de ativos de entes públicos sob apuração de fraudes no sistema bancário.",
                "consequencias": "O STF analisará se defere a transferência dos valores para o banco distrital.",
                "repercussao": "O governo do DF declarou-se vítima no procedimento judicial.",
                "fonte_nome": "Folha de S.Paulo — Mercado",
                "fonte_url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master-de-gestao-fraudulenta.shtml"
            }
        },
        {
            "id": "B1_NUMERO_INCORRETO",
            "name": "1. Valor numérico incorreto (R$ 2,2 bi -> R$ 500 milhões)",
            "adulteracao": "Valor alterado de R$ 2,2 bilhões para R$ 500 milhões.",
            "item": {
                "titulo": "Governo do DF acusa Banco Master e pede transferência de R$ 500 milhões ao STF",
                "pais": "BR",
                "tema": "Economia",
                "resumo_desenvolvido": "O governo do Distrito Federal solicitou ao STF a liberação e transferência de R$ 500 milhões bloqueados em apurações de gestão fraudulenta contra o Banco Master para os cofres do BRB.",
                "contexto": "Disputa pela recuperação de valores bloqueados.",
                "consequencias": "Decisão do STF sobre os R$ 500 milhões.",
                "repercussao": None,
                "fonte_nome": "Folha de S.Paulo — Mercado",
                "fonte_url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master-de-gestao-fraudulenta.shtml"
            }
        },
        {
            "id": "B2_NOME_TROCADO",
            "name": "2. Nome/órgão trocado (DF -> Governo de São Paulo / STF -> STJ)",
            "adulteracao": "Governo do DF trocado por Governo de São Paulo; STF trocado por STJ.",
            "item": {
                "titulo": "Governo de São Paulo pede ao STJ transferência de R$ 2,2 bi bloqueados do Banco Master",
                "pais": "BR",
                "tema": "Economia",
                "resumo_desenvolvido": "O governo do estado de São Paulo ingressou no Superior Tribunal de Justiça (STJ) requerendo que R$ 2,2 bilhões de investigações do Banco Master sejam repassados ao banco estadual.",
                "contexto": "Tentativa do governo paulista de recuperar ativos financeiros.",
                "consequencias": "Análise pelo STJ.",
                "repercussao": None,
                "fonte_nome": "Folha de S.Paulo — Mercado",
                "fonte_url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master-de-gestao-fraudulenta.shtml"
            }
        },
        {
            "id": "B3_FATO_INEXISTENTE",
            "name": "3. Afirmação inexistente (renúncia do governador e prisão da diretoria)",
            "adulteracao": "Acrescentada renúncia do governador e prisão preventiva de diretores, dados totalmente ausentes na fonte.",
            "item": {
                "titulo": "Governador do DF renuncia após STF determinar prisão de diretores do Banco Master",
                "pais": "BR",
                "tema": "Economia",
                "resumo_desenvolvido": "Em desdobramento bombástico, o governador do Distrito Federal anunciou sua renúncia imediata após o STF decretar a prisão de toda a diretoria do Banco Master e transferir R$ 2,2 bilhões.",
                "contexto": "Crise política institucional no Distrito Federal.",
                "consequencias": "Novas eleições no DF.",
                "repercussao": None,
                "fonte_nome": "Folha de S.Paulo — Mercado",
                "fonte_url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master-de-gestao-fraudulenta.shtml"
            }
        },
        {
            "id": "B4_PREVISAO_VIRANDO_FATO",
            "name": "4. Previsão transformada em fato consumado (recursos já foram transferidos)",
            "adulteracao": "O pedido em análise no STF foi descrito como já deferido e os R$ 2,2 bi já depositados na conta do BRB ontem à noite.",
            "item": {
                "titulo": "STF transfere R$ 2,2 bilhões do Banco Master para o BRB a pedido do DF",
                "pais": "BR",
                "tema": "Economia",
                "resumo_desenvolvido": "O Supremo Tribunal Federal já transferiu em definitivo R$ 2,2 bilhões anteriormente retidos do Banco Master para a conta do BRB. O dinheiro caiu ontem e encerrou a disputa com o governo do DF.",
                "contexto": "Recursos transferidos com sucesso pelo Judiciário.",
                "consequencias": "O BRB já incorporou o valor ao seu balanço.",
                "repercussao": None,
                "fonte_nome": "Folha de S.Paulo — Mercado",
                "fonte_url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master-de-gestao-fraudulenta.shtml"
            }
        },
        {
            "id": "B5_TITULO_CONTRADIZ_CORPO",
            "name": "5. Título contradiz o corpo (Título: DF elogia Master vs Corpo: DF acusa Master de fraude)",
            "adulteracao": "Título afirma que o DF defendeu e elogiou a lisura do Master, mas o corpo afirma que o DF o acusou de fraude.",
            "item": {
                "titulo": "Governo do DF atesta idoneidade do Banco Master e nega qualquer irregularidade financeira",
                "pais": "BR",
                "tema": "Economia",
                "resumo_desenvolvido": "O governo do Distrito Federal denunciou o Banco Master ao STF por gestão fraudulenta, afirmando ser vítima de um grande golpe e solicitando a transferência de R$ 2,2 bilhões bloqueados.",
                "contexto": "Processo de apuração de fraude.",
                "consequencias": "Investigação no STF.",
                "repercussao": None,
                "fonte_nome": "Folha de S.Paulo — Mercado",
                "fonte_url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master-de-gestao-fraudulenta.shtml"
            }
        },
        {
            "id": "B6_TRADUCAO_DISTORCIDA",
            "name": "6. Tradução distorcida ('setbacks' -> vitória esmagadora histórica de Trump)",
            "adulteracao": "'Donald Trump suffered notable setbacks' traduzido como 'Donald Trump obteve vitória esmagadora e histórica'.",
            "item": {
                "titulo": "Eleições de meio de mandato consolidam vitória esmagadora de Trump e seus aliados nos EUA",
                "pais": "MUNDO",
                "tema": "Internacional",
                "resumo_desenvolvido": "As eleições legislativas nos Estados Unidos redefiniram o equilíbrio de poder em Washington. O presidente Joe Biden agora enfrenta um governo dividido, enquanto Donald Trump obteve uma vitória histórica e esmagadora, com triunfos de todos os seus candidatos apadrinhados em estados decisivos.",
                "contexto": "Avanço da oposição republicana sob a liderança de Trump.",
                "consequencias": "Fortalecimento total da agenda trumpista no Congresso.",
                "repercussao": None,
                "fonte_nome": "BBC News — World",
                "fonte_url": "https://www.bbc.com/news/world-us-canada-67890"
            }
        }
    ]

    results = []

    for tc in test_cases:
        print(f"\nSubmetendo teste: {tc['name']}...")
        draft = {
            "panorama": "Panorama de teste.",
            "noticias": [tc["item"]]
        }

        reviewed = news_bot.review_bulletin(draft, source_articles)

        if reviewed is None:
            res_status = "ERRO_TECNICO"
            dest = "BLOQUEADO"
            motivo = "Falha técnica na API"
        else:
            noticias_finais = reviewed.get("noticias", [])
            if len(noticias_finais) == 0:
                res_status = "REJEITADA"
                dest = "DESCARTADO"
                motivo = "Item excluído pelo revisor"
            else:
                final_item = noticias_finais[0]
                if final_item.get("resumo_desenvolvido") != tc["item"]["resumo_desenvolvido"]:
                    res_status = "CORRIGIDA"
                    dest = "ENVIADO_COM_CORRECAO"
                    motivo = "Texto foi retificado pelo auditor"
                else:
                    res_status = "APROVADA"
                    dest = "ENVIADO_ORIGINAL"
                    motivo = "Revisor aprovou sem alterações"

        print(f"  Resultado: Status={res_status} | Destino={dest}")
        results.append({
            "id": tc["id"],
            "name": tc["name"],
            "adulteracao": tc["adulteracao"],
            "status_revisor": res_status,
            "destino": dest,
            "motivo": motivo,
            "sucesso": (dest != "ENVIADO_ORIGINAL") if tc["id"] != "B0_CONTROLE" else (dest == "ENVIADO_ORIGINAL")
        })

    # Teste de divergência entre fontes
    print("\n--- TESTE B7: DUAS FONTES AUTORIZADAS DIVERGENTES SOBRE O MESMO FATO ---")
    divergent_sources = [
        {
            "id": "src_folha",
            "source": "Folha de S.Paulo — Mercado",
            "country": "BR",
            "title": "Governo do DF pede transferência de R$ 2,2 bilhões bloqueados do Banco Master",
            "url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master.shtml",
            "published_at": "2026-11-05T18:43:00Z",
            "summary": "O governo do Distrito Federal pediu ao STF a transferência de R$ 2,2 bilhões bloqueados nas contas do Banco Master."
        },
        {
            "id": "src_g1",
            "source": "G1 — Economia",
            "country": "BR",
            "title": "DF afirma que quantia retida no caso Master foi de R$ 1,5 bilhão",
            "url": "https://g1.globo.com/economia/noticia/2026/11/05/df-diz-que-bloqueio-master-foi-1-bi-e-meio.ghtml",
            "published_at": "2026-11-05T18:50:00Z",
            "summary": "Em nota oficial divergente, o governo do Distrito Federal declarou ao G1 que o montante total sob bloqueio é de R$ 1,5 bilhão, e não R$ 2,2 bilhões como citado por outras autoridades."
        }
    ]

    draft_divergent = {
        "panorama": "Divergência de valores entre fontes.",
        "noticias": [
            {
                "titulo": "Governo do DF pede transferência de R$ 2,2 bilhões bloqueados do Banco Master",
                "pais": "BR",
                "tema": "Economia",
                "resumo_desenvolvido": "O governo do Distrito Federal solicitou ao STF que os R$ 2,2 bilhões bloqueados do Banco Master sejam transferidos ao BRB, valor contestado em comunicado paralelo que mencionou R$ 1,5 bilhão.",
                "contexto": "Disputa sobre o valor exato sob custódia judicial.",
                "consequencias": "STF precisará apurar o saldo real.",
                "repercussao": None,
                "fonte_nome": "Folha de S.Paulo — Mercado",
                "fonte_url": "https://www1.folha.uol.com.br/mercado/2026/11/governo-do-df-acusa-master.shtml"
            }
        ]
    }

    reviewed_div = news_bot.review_bulletin(draft_divergent, divergent_sources)
    print("Resultado do teste de divergência:")
    if reviewed_div and reviewed_div.get("noticias"):
        print("  Revisor aceitou notícia baseada na Folha com menção à divergência.")
    else:
        print("  Revisor rejeitou ou descartou item divergente.")

    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO DOS TESTES DO REVISOR REAL:")
    print("=" * 80)
    for r in results:
        status_pass = "PASSOU" if r["sucesso"] else "FALHOU"
        print(f"[{status_pass}] {r['id']}: {r['name']}")
        print(f"    Adulteração: {r['adulteracao']}")
        print(f"    Status Revisor: {r['status_revisor']} -> Destino: {r['destino']}")

    # Salva relatório em json para inclusão nas evidências
    with open(r"audit_tests\real_reviewer_results.json", "w", encoding="utf-8") as f:
        json.dump({"cases": results}, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    run_real_reviewer_tests()
