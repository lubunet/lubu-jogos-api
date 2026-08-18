import os
import json
import requests
import unicodedata

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURAÇÃO
# ============================================================

API_URL = "https://v3.football.api-sports.io"
API_KEY = os.environ["API_FOOTBALL_KEY"]

TIMEZONE_REFERENCIA = "America/Cuiaba"

headers = {
    "x-apisports-key": API_KEY
}


# ============================================================
# COMPETIÇÕES RELEVANTES
# ============================================================

# Competições brasileiras que queremos aceitar.
COMPETICOES_BRASIL = (
    # Nacionais
    "serie a",
    "serie b",
    "serie c",
    "serie d",
    "copa do brasil",
    "supercopa do brasil",
    "supercopa rei",
    "copa do nordeste",
    "copa verde",

    # São Paulo
    "paulista - a1",
    "paulista a1",
    "copa paulista",

    # Rio
    "carioca - 1",
    "carioca serie a",
    "copa rio",

    # Minas
    "mineiro - 1",
    "mineiro modulo i",

    # RS
    "gaucho - 1",
    "gaucho 1",

    # Paraná
    "paranaense - 1",
    "paranaense 1",

    # Santa Catarina
    "catarinense - 1",
    "catarinense 1",

    # Bahia
    "baiano - 1",
    "baiano 1",

    # Ceará
    "cearense - 1",
    "cearense 1",

    # Goiás
    "goiano - 1",
    "goiano 1",

    # Pernambuco
    "pernambucano - 1",
    "pernambucano 1",

    # Outros estaduais
    "alagoano",
    "amazonense",
    "brasiliense",
    "capixaba",
    "maranhense",
    "mato-grossense",
    "paraense",
    "paraibano",
    "piauiense",
    "potiguar",
    "sergipano",
    "tocantinense",
    "acreano",
    "amapaense",
    "rondoniense",
    "roraimense",
)


# Competições internacionais / estrangeiras relevantes.
COMPETICOES_INTERNACIONAIS = (
    # CONMEBOL
    "conmebol libertadores",
    "conmebol sudamericana",
    "conmebol recopa",
    "recopa sudamericana",

    # UEFA
    "uefa champions league",
    "uefa europa league",
    "uefa europa conference league",
    "conference league",

    # Inglaterra
    "premier league",
    "fa cup",
    "league cup",

    # Espanha
    "la liga",
    "copa del rey",

    # Itália
    "serie a",
    "coppa italia",

    # Alemanha
    "bundesliga",
    "dfb pokal",

    # França
    "ligue 1",
    "coupe de france",

    # Portugal
    "primeira liga",

    # Arábia Saudita
    "pro league",

    # EUA
    "major league soccer",
    "mls",

    # Argentina
    "liga profesional argentina",
    "liga profesional de futbol",

    # Seleções / mundial
    "world cup",
    "fifa world cup",
    "club world cup",
    "fifa club world cup",
    "intercontinental cup",
    "copa america",
    "uefa euro",
    "euro championship",
    "world cup qualification",
    "world cup qualifiers",
    "uefa nations league",
)


# Sempre ignorar essas categorias.
BLOQUEADOS = (
    "u17",
    "u-17",
    "sub 17",
    "sub-17",

    "u18",
    "u-18",
    "sub 18",

    "u19",
    "u-19",

    "u20",
    "u-20",
    "sub 20",
    "sub-20",

    "u21",
    "u-21",

    "u23",
    "u-23",

    "youth",
    "junior",
    "juniors",

    "women",
    "woman",
    "feminino",
    "feminina",

    "reserve",
    "reserves",

    "friendly",
    "friendlies",
    "amistoso",
    "amistosos",
)


# Divisões estaduais que não queremos.
DIVISOES_INFERIORES = (
    "paulista a2",
    "paulista - a2",
    "paulista a3",
    "paulista - a3",
    "paulista a4",
    "paulista - a4",

    "carioca a2",
    "carioca - a2",

    "mineiro modulo ii",
    "mineiro modulo 2",

    "paranaense 2",
    "paranaense - 2",

    "catarinense 2",
    "catarinense - 2",

    "goiano 2",

    "pernambucano a2",

    "capixaba b",
)


# ============================================================
# FUNÇÕES
# ============================================================

def normalizar(texto):

    if not texto:
        return ""

    texto = unicodedata.normalize(
        "NFKD",
        texto
    ).encode(
        "ASCII",
        "ignore"
    ).decode(
        "ASCII"
    )

    return texto.lower().strip()


def chamar_api(endpoint, params=None):

    url = f"{API_URL}/{endpoint}"

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    dados = response.json()

    if dados.get("errors"):
        raise Exception(
            f"Erro retornado pela API-Football: {dados['errors']}"
        )

    return dados.get("response", [])


def contem_algum(texto, termos):

    texto = normalizar(texto)

    for termo in termos:

        if normalizar(termo) in texto:
            return True

    return False


def competicao_relevante(nome, pais):

    nome_normalizado = normalizar(nome)
    pais_normalizado = normalizar(pais)


    # -----------------------------------------
    # BLOQUEIOS GERAIS
    # -----------------------------------------

    if contem_algum(
        nome_normalizado,
        BLOQUEADOS
    ):
        return False


    if contem_algum(
        nome_normalizado,
        DIVISOES_INFERIORES
    ):
        return False


    # -----------------------------------------
    # BRASIL
    # -----------------------------------------

    if pais_normalizado == "brazil":

        return contem_algum(
            nome_normalizado,
            COMPETICOES_BRASIL
        )


    # -----------------------------------------
    # INTERNACIONAL
    # -----------------------------------------

    return contem_algum(
        nome_normalizado,
        COMPETICOES_INTERNACIONAIS
    )


# ============================================================
# DATA DE HOJE
# ============================================================

tz_referencia = ZoneInfo(
    TIMEZONE_REFERENCIA
)

agora = datetime.now(
    tz_referencia
)

data_hoje = agora.strftime(
    "%Y-%m-%d"
)


print(
    f"Buscando jogos de {data_hoje}..."
)


# ============================================================
# CONSULTAR TODOS OS JOGOS DE HOJE
# ============================================================

fixtures = chamar_api(
    "fixtures",
    {
        "date": data_hoje,
        "timezone": TIMEZONE_REFERENCIA
    }
)


print(
    f"API retornou {len(fixtures)} jogos no total."
)


# ============================================================
# FILTRAR E MONTAR JOGOS
# ============================================================

jogos = []


for item in fixtures:

    fixture = item.get(
        "fixture",
        {}
    )

    league = item.get(
        "league",
        {}
    )

    teams = item.get(
        "teams",
        {}
    )

    goals = item.get(
        "goals",
        {}
    )

    score = item.get(
        "score",
        {}
    )


    nome_campeonato = league.get(
        "name",
        ""
    )

    pais_campeonato = league.get(
        "country",
        ""
    )


    # ========================================================
    # FILTRO PRINCIPAL
    # ========================================================

    if not competicao_relevante(
        nome_campeonato,
        pais_campeonato
    ):

        continue


    casa = teams.get(
        "home",
        {}
    )

    fora = teams.get(
        "away",
        {}
    )


    # ========================================================
    # HORÁRIO
    # ========================================================

    data_partida = datetime.fromisoformat(
        fixture["date"]
    )


    data_utc = data_partida.astimezone(
        timezone.utc
    )


    data_referencia = data_partida.astimezone(
        tz_referencia
    )


    inicio_utc = (
        data_utc
        .isoformat()
        .replace(
            "+00:00",
            "Z"
        )
    )


    # ========================================================
    # JOGO
    # ========================================================

    jogo = {

        "id": fixture.get(
            "id"
        ),


        # CAMPO QUE O APP DEVE USAR
        # PARA CALCULAR O HORÁRIO.
        "timestamp": fixture.get(
            "timestamp"
        ),


        "inicio_utc": inicio_utc,


        "horario_referencia": {

            "timezone":
                TIMEZONE_REFERENCIA,

            "data":
                data_referencia.strftime(
                    "%Y-%m-%d"
                ),

            "horario":
                data_referencia.strftime(
                    "%H:%M"
                )
        },


        "status": {

            "codigo":
                fixture.get(
                    "status",
                    {}
                ).get(
                    "short"
                ),

            "descricao":
                fixture.get(
                    "status",
                    {}
                ).get(
                    "long"
                ),

            "minuto":
                fixture.get(
                    "status",
                    {}
                ).get(
                    "elapsed"
                )
        },


        "campeonato": {

            "id":
                league.get(
                    "id"
                ),

            "nome":
                nome_campeonato,

            "pais":
                pais_campeonato,

            "logo":
                league.get(
                    "logo"
                ),

            "bandeira":
                league.get(
                    "flag"
                ),

            "temporada":
                league.get(
                    "season"
                ),

            "rodada":
                league.get(
                    "round"
                )
        },


        "casa": {

            "id":
                casa.get(
                    "id"
                ),

            "nome":
                casa.get(
                    "name"
                ),

            "logo":
                casa.get(
                    "logo"
                ),

            "vencedor":
                casa.get(
                    "winner"
                ),

            "gols":
                goals.get(
                    "home"
                )
        },


        "fora": {

            "id":
                fora.get(
                    "id"
                ),

            "nome":
                fora.get(
                    "name"
                ),

            "logo":
                fora.get(
                    "logo"
                ),

            "vencedor":
                fora.get(
                    "winner"
                ),

            "gols":
                goals.get(
                    "away"
                )
        },


        "placar": {

            "intervalo":
                score.get(
                    "halftime"
                ),

            "final":
                score.get(
                    "fulltime"
                ),

            "prorrogacao":
                score.get(
                    "extratime"
                ),

            "penaltis":
                score.get(
                    "penalty"
                )
        },


        "estadio": {

            "id":
                fixture.get(
                    "venue",
                    {}
                ).get(
                    "id"
                ),

            "nome":
                fixture.get(
                    "venue",
                    {}
                ).get(
                    "name"
                ),

            "cidade":
                fixture.get(
                    "venue",
                    {}
                ).get(
                    "city"
                )
        },


        "transmissao": []
    }


    jogos.append(
        jogo
    )


# ============================================================
# ORDENAR
# ============================================================

jogos.sort(
    key=lambda jogo:
        jogo.get(
            "timestamp"
        ) or 0
)


# ============================================================
# GERAR LISTA DE CAMPEONATOS
# ============================================================

campeonatos = {}


for jogo in jogos:

    campeonato = jogo[
        "campeonato"
    ]

    campeonato_id = campeonato.get(
        "id"
    )


    if campeonato_id not in campeonatos:

        campeonatos[
            campeonato_id
        ] = {

            "id":
                campeonato_id,

            "nome":
                campeonato.get(
                    "nome"
                ),

            "pais":
                campeonato.get(
                    "pais"
                ),

            "logo":
                campeonato.get(
                    "logo"
                ),

            "bandeira":
                campeonato.get(
                    "bandeira"
                ),

            "quantidade_jogos":
                0
        }


    campeonatos[
        campeonato_id
    ][
        "quantidade_jogos"
    ] += 1


lista_campeonatos = list(
    campeonatos.values()
)


lista_campeonatos.sort(
    key=lambda campeonato:
        (
            campeonato.get(
                "pais"
            ) or "",

            campeonato.get(
                "nome"
            ) or ""
        )
)


# ============================================================
# JSON FINAL
# ============================================================

saida = {

    "versao": 4,

    "data": data_hoje,

    "gerado_em":
        agora.isoformat(),

    "timezone_referencia":
        TIMEZONE_REFERENCIA,


    "periodo": {

        "inicio":
            "00:00",

        "fim":
            "23:59"
    },


    "horario": {

        "campo_recomendado":
            "timestamp",

        "formato":
            "Unix timestamp",

        "observacao":
            "Converter usando o mesmo "
            "timezone/offset configurado "
            "para o EPG."
    },


    "quantidade_campeonatos":
        len(
            lista_campeonatos
        ),

    "quantidade_jogos":
        len(
            jogos
        ),


    "campeonatos":
        lista_campeonatos,


    "jogos":
        jogos
}


os.makedirs(
    "data",
    exist_ok=True
)


with open(
    "data/jogos-hoje.json",
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        saida,
        arquivo,
        ensure_ascii=False,
        indent=2
    )


print()

print(
    f"{len(fixtures)} jogos recebidos da API."
)

print(
    f"{len(jogos)} jogos relevantes mantidos."
)

print(
    f"{len(lista_campeonatos)} campeonatos."
)

print(
    "JSON atualizado."
)
