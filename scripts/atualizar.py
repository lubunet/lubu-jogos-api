import os
import json
import re
import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests


# ============================================================
# CONFIGURAÇÃO
# ============================================================

API_URL = "https://v3.football.api-sports.io"
API_KEY = os.environ["API_FOOTBALL_KEY"]
TIMEZONE_REFERENCIA = "America/Cuiaba"

HEADERS = {
    "x-apisports-key": API_KEY
}


# ============================================================
# COMPETIÇÕES RELEVANTES
# ============================================================

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

    # Rio Grande do Sul
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


# ============================================================
# COMPETIÇÕES DE BASE PERMITIDAS
# ============================================================

COMPETICOES_BASE_PERMITIDAS = (
    "brasileiro u17",
    "brasileiro u-17",
    "brasileiro sub 17",
    "brasileiro sub-17",
    "campeonato brasileiro u17",
    "campeonato brasileiro u-17",
    "campeonato brasileiro sub 17",
    "campeonato brasileiro sub-17",
)


# ============================================================
# COMPETIÇÕES INTERNACIONAIS
# ============================================================

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

    # Seleções / Mundial
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


# ============================================================
# CATEGORIAS BLOQUEADAS
# ============================================================

BLOQUEADOS = (
    "u17",
    "u-17",
    "sub 17",
    "sub-17",

    "u18",
    "u-18",
    "sub 18",
    "sub-18",

    "u19",
    "u-19",
    "sub 19",
    "sub-19",

    "u20",
    "u-20",
    "sub 20",
    "sub-20",

    "u21",
    "u-21",
    "sub 21",
    "sub-21",

    "u23",
    "u-23",
    "sub 23",
    "sub-23",

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


# ============================================================
# DIVISÕES ESTADUAIS INFERIORES
# ============================================================

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
# CORREÇÃO DOS CLUBES DO BRASILEIRO SUB-17
# ============================================================

ALIASES_CLUBE_PRINCIPAL = {

    "america mg": (
        "america mineiro",
        "america-mg",
        "america mg",
    ),

    "atletico go": (
        "atletico goianiense",
        "atletico-go",
        "atletico go",
    ),

    "atletico mg": (
        "atletico-mg",
        "atletico mineiro",
        "atletico mg",
    ),

    "athletico pr": (
        "athletico-pr",
        "athletico paranaense",
        "athletico pr",
    ),

    "bragantino": (
        "rb bragantino",
        "bragantino",
    ),

    "vasco": (
        "vasco da gama",
        "vasco",
    ),

    "vitoria": (
        "vitoria",
        "ec vitoria",
    ),

    "bahia": (
        "bahia",
        "ec bahia",
    ),

    "sport": (
        "sport recife",
        "sport",
    ),
}


NOMES_EXIBICAO_U17 = {

    "america mg": "América-MG",

    "atletico go": "Atlético-GO",

    "atletico mg": "Atlético-MG",

    "athletico pr": "Athletico-PR",

    "bahia": "Bahia",

    "botafogo": "Botafogo",

    "bragantino": "Bragantino",

    "ceara": "Ceará",

    "corinthians": "Corinthians",

    "cruzeiro": "Cruzeiro",

    "flamengo": "Flamengo",

    "fluminense": "Fluminense",

    "fortaleza": "Fortaleza",

    "gremio": "Grêmio",

    "internacional": "Internacional",

    "juventude": "Juventude",

    "palmeiras": "Palmeiras",

    "santos": "Santos",

    "sao paulo": "São Paulo",

    "sport": "Sport",

    "vasco": "Vasco",

    "vitoria": "Vitória",
}


# ============================================================
# FUNÇÕES
# ============================================================

def normalizar(texto):

    if not texto:
        return ""

    texto = unicodedata.normalize(
        "NFKD",
        str(texto)
    ).encode(
        "ASCII",
        "ignore"
    ).decode(
        "ASCII"
    )

    return texto.lower().strip()


def chave_nome_clube(texto):

    texto = normalizar(
        texto
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def chamar_api(endpoint, params=None):

    response = requests.get(
        f"{API_URL}/{endpoint}",
        headers=HEADERS,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    dados = response.json()

    if dados.get("errors"):

        raise Exception(
            f"Erro retornado pela API-Football: "
            f"{dados['errors']}"
        )

    return dados.get(
        "response",
        []
    )


def contem_algum(texto, termos):

    texto = normalizar(
        texto
    )

    return any(
        normalizar(termo) in texto
        for termo in termos
    )


def eh_brasileiro_u17(
    nome_campeonato,
    pais_campeonato
):

    return (
        normalizar(
            pais_campeonato
        ) == "brazil"

        and

        contem_algum(
            nome_campeonato,
            COMPETICOES_BASE_PERMITIDAS
        )
    )


def competicao_relevante(
    nome_campeonato,
    pais_campeonato
):

    nome = normalizar(
        nome_campeonato
    )

    pais = normalizar(
        pais_campeonato
    )


    # Brasileiro Sub-17 é uma exceção permitida.
    if eh_brasileiro_u17(
        nome_campeonato,
        pais_campeonato
    ):
        return True


    # Bloqueia outras bases, feminino, amistosos etc.
    if contem_algum(
        nome,
        BLOQUEADOS
    ):
        return False


    if contem_algum(
        nome,
        DIVISOES_INFERIORES
    ):
        return False


    if pais == "brazil":

        return contem_algum(
            nome,
            COMPETICOES_BRASIL
        )


    return contem_algum(
        nome,
        COMPETICOES_INTERNACIONAIS
    )


# ============================================================
# FUNÇÕES PARA CORRIGIR O SUB-17
# ============================================================

def limpar_sufixo_u17(nome):

    if not nome:
        return ""

    return re.sub(
        r"\s*(?:U[\s-]?17|SUB[\s-]?17)\s*$",
        "",
        str(nome),
        flags=re.IGNORECASE
    ).strip()


def eh_time_de_base_ou_reserva(nome):

    marcadores = (
        "u17",
        "u-17",

        "u18",
        "u-18",

        "u19",
        "u-19",

        "u20",
        "u-20",

        "u21",
        "u-21",

        "u23",
        "u-23",

        "sub 17",
        "sub-17",

        "sub 20",
        "sub-20",

        "youth",

        "junior",
        "juniors",

        "women",
        "woman",

        "feminino",
        "feminina",

        "reserve",
        "reserves",
    )

    return contem_algum(
        nome,
        marcadores
    )


def criar_indice_clubes_principais_brasil():

    print(
        "Brasileiro Sub-17 encontrado."
    )

    print(
        "Buscando clubes principais "
        "para corrigir nomes e escudos..."
    )


    resposta = chamar_api(
        "teams",
        {
            "country": "Brazil"
        }
    )


    indice = {}


    for item in resposta:

        team = item.get(
            "team",
            {}
        )


        if team.get(
            "national",
            False
        ):
            continue


        nome = team.get(
            "name",
            ""
        )


        if not nome:
            continue


        if eh_time_de_base_ou_reserva(
            nome
        ):
            continue


        chave = chave_nome_clube(
            nome
        )


        if not chave:
            continue


        indice.setdefault(
            chave,
            {
                "id":
                    team.get(
                        "id"
                    ),

                "nome":
                    nome,

                "logo":
                    team.get(
                        "logo"
                    )
            }
        )


    print(
        f"{len(indice)} clubes principais indexados."
    )


    return indice


def resolver_clube_principal(
    nome_u17,
    indice
):

    nome_base = limpar_sufixo_u17(
        nome_u17
    )


    chave_base = chave_nome_clube(
        nome_base
    )


    if not chave_base:

        return None, nome_base


    candidatos = [
        chave_base
    ]


    for alias in ALIASES_CLUBE_PRINCIPAL.get(
        chave_base,
        ()
    ):

        candidatos.append(
            chave_nome_clube(
                alias
            )
        )


    # --------------------------------------------------------
    # TENTATIVA EXATA
    # --------------------------------------------------------

    for candidato in candidatos:

        if candidato in indice:

            nome_exibicao = (
                NOMES_EXIBICAO_U17.get(
                    chave_base,
                    nome_base
                )
            )

            return (
                indice[candidato],
                nome_exibicao
            )


    # --------------------------------------------------------
    # TENTATIVA PARCIAL
    # --------------------------------------------------------

    possiveis = {}


    for chave_indice, clube in indice.items():

        for candidato in candidatos:

            if (
                candidato

                and

                (
                    candidato in chave_indice

                    or

                    chave_indice in candidato
                )
            ):

                clube_id = clube.get(
                    "id"
                )


                if clube_id is not None:

                    possiveis[
                        clube_id
                    ] = clube


                break


    if len(possiveis) == 1:

        clube = next(
            iter(
                possiveis.values()
            )
        )


        nome_exibicao = (
            NOMES_EXIBICAO_U17.get(
                chave_base,
                nome_base
            )
        )


        return (
            clube,
            nome_exibicao
        )


    # Não achou o profissional.
    # Pelo menos remove U17 do nome.

    nome_exibicao = (
        NOMES_EXIBICAO_U17.get(
            chave_base,
            nome_base
        )
    )


    return (
        None,
        nome_exibicao
    )


def preparar_time(
    dados_time,
    goals,
    lado,
    brasileiro_u17,
    indice_principais
):

    nome_original = dados_time.get(
        "name"
    )

    logo_original = dados_time.get(
        "logo"
    )


    time_saida = {

        "id":
            dados_time.get(
                "id"
            ),

        "nome":
            nome_original,

        "logo":
            logo_original,

        "vencedor":
            dados_time.get(
                "winner"
            ),

        "gols":
            goals.get(
                lado
            )
    }


    if not brasileiro_u17:

        return time_saida


    clube_principal, nome_exibicao = (
        resolver_clube_principal(
            nome_original,
            indice_principais
        )
    )


    # Remove o U17 do nome mostrado no app.
    time_saida[
        "nome"
    ] = nome_exibicao


    # Mantém original apenas para debug.
    time_saida[
        "nome_original_api"
    ] = nome_original


    time_saida[
        "logo_original_api"
    ] = logo_original


    if clube_principal:

        time_saida[
            "clube_principal_id"
        ] = clube_principal.get(
            "id"
        )


        if clube_principal.get(
            "logo"
        ):

            time_saida[
                "logo"
            ] = clube_principal[
                "logo"
            ]


    return time_saida


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
        "date":
            data_hoje,

        "timezone":
            TIMEZONE_REFERENCIA
    }
)


print(
    f"API retornou "
    f"{len(fixtures)} jogos no total."
)


# ============================================================
# VERIFICAR SE EXISTE BRASILEIRO SUB-17
# ============================================================

tem_brasileiro_u17 = any(

    eh_brasileiro_u17(

        item.get(
            "league",
            {}
        ).get(
            "name",
            ""
        ),

        item.get(
            "league",
            {}
        ).get(
            "country",
            ""
        )

    )

    for item in fixtures
)


indice_clubes_principais = {}


if tem_brasileiro_u17:

    indice_clubes_principais = (
        criar_indice_clubes_principais_brasil()
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


    # --------------------------------------------------------
    # FILTRO
    # --------------------------------------------------------

    if not competicao_relevante(
        nome_campeonato,
        pais_campeonato
    ):

        continue


    brasileiro_u17 = eh_brasileiro_u17(
        nome_campeonato,
        pais_campeonato
    )


    casa = preparar_time(

        teams.get(
            "home",
            {}
        ),

        goals,

        "home",

        brasileiro_u17,

        indice_clubes_principais
    )


    fora = preparar_time(

        teams.get(
            "away",
            {}
        ),

        goals,

        "away",

        brasileiro_u17,

        indice_clubes_principais
    )


    # --------------------------------------------------------
    # HORÁRIO
    # --------------------------------------------------------

    data_partida = datetime.fromisoformat(
        fixture[
            "date"
        ]
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


    # --------------------------------------------------------
    # JOGO
    # --------------------------------------------------------

    jogo = {

        "id":
            fixture.get(
                "id"
            ),


        # O app usa isso para o horário.
        "timestamp":
            fixture.get(
                "timestamp"
            ),


        "inicio_utc":
            inicio_utc,


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


        "casa":
            casa,


        "fora":
            fora,


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


        "transmissao":
            []
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
        )

        or

        0

)


# ============================================================
# LISTA DE CAMPEONATOS
# ============================================================

campeonatos = {}


for jogo in jogos:

    campeonato = jogo[
        "campeonato"
    ]


    campeonato_id = campeonato.get(
        "id"
    )


    if campeonato_id is None:

        continue


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
            )

            or

            "",


            campeonato.get(
                "nome"
            )

            or

            ""

        )

)


# ============================================================
# JSON FINAL
# ============================================================

saida = {

    "versao":
        6,


    "data":
        data_hoje,


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


# ============================================================
# SALVAR
# ============================================================

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


# ============================================================
# LOG
# ============================================================

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


if tem_brasileiro_u17:

    print(
        "Brasileiro Sub-17 corrigido: "
        "nomes sem U17 e escudos dos "
        "clubes principais quando encontrados."
    )


print(
    "JSON atualizado."
)
