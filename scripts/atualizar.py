import os
import json
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

import requests


# ============================================================
# CONFIGURAÇÃO
# ============================================================

API_URL = "https://v3.football.api-sports.io"
API_KEY = os.environ["API_FOOTBALL_KEY"]
TIMEZONE_REFERENCIA = "America/Cuiaba"

# ID do Campeonato Brasileiro Sub-17 na API-Football.
LIGA_BRASILEIRO_U17_ID = 1128

HEADERS = {
    "x-apisports-key": API_KEY
}


# ============================================================
# COMPETIÇÕES BRASILEIRAS PERMITIDAS
# ============================================================

COMPETICOES_BRASIL = (
    "serie a",
    "serie b",
    "serie c",
    "serie d",
    "copa do brasil",
    "supercopa do brasil",
    "supercopa rei",
    "copa do nordeste",
    "copa verde",

    "paulista - a1",
    "paulista a1",
    "copa paulista",

    "carioca - 1",
    "carioca serie a",
    "copa rio",

    "mineiro - 1",
    "mineiro modulo i",

    "gaucho - 1",
    "gaucho 1",

    "paranaense - 1",
    "paranaense 1",

    "catarinense - 1",
    "catarinense 1",

    "baiano - 1",
    "baiano 1",

    "cearense - 1",
    "cearense 1",

    "goiano - 1",
    "goiano 1",

    "pernambucano - 1",
    "pernambucano 1",

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
# COMPETIÇÕES INTERNACIONAIS / ESTRANGEIRAS
# ============================================================

COMPETICOES_EXATAS_POR_PAIS = {
    "world": {
        "conmebol libertadores",
        "conmebol sudamericana",
        "conmebol recopa",
        "recopa sudamericana",
        "uefa champions league",
        "uefa europa league",
        "uefa europa conference league",
        "uefa conference league",
        "fifa club world cup",
        "club world cup",
        "fifa intercontinental cup",
        "intercontinental cup",
        "world cup",
        "fifa world cup",
        "copa america",
        "uefa euro",
        "euro championship",
        "world cup qualification",
        "world cup qualifiers",
        "uefa nations league",
    },

    "england": {
        "premier league",
        "fa cup",
        "league cup",
    },

    "spain": {
        "la liga",
        "copa del rey",
    },

    "italy": {
        "serie a",
        "coppa italia",
    },

    "germany": {
        "bundesliga",
        "dfb pokal",
    },

    "france": {
        "ligue 1",
        "coupe de france",
    },

    "portugal": {
        "primeira liga",
        "taca de portugal",
    },

    "saudi-arabia": {
        "pro league",
        "king's cup",
        "kings cup",
    },

    "usa": {
        "major league soccer",
    },

    "argentina": {
        "liga profesional argentina",
        "liga profesional de futbol",
    },
}


# ============================================================
# EXCEÇÃO DE BASE: BRASILEIRO SUB-17
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
# BLOQUEIOS
# ============================================================

BLOQUEADOS = (
    "u17", "u-17", "sub 17", "sub-17",
    "u18", "u-18", "sub 18", "sub-18",
    "u19", "u-19", "sub 19", "sub-19",
    "u20", "u-20", "sub 20", "sub-20",
    "u21", "u-21", "sub 21", "sub-21",
    "u23", "u-23", "sub 23", "sub-23",

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
# ALIASES PARA ACHAR O CLUBE PRINCIPAL DO SUB-17
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
        "atletico mineiro",
        "atletico-mg",
        "atletico mg",
    ),

    "athletico pr": (
        "athletico paranaense",
        "athletico-pr",
        "athletico pr",
    ),

    "bahia": (
        "bahia",
        "ec bahia",
    ),

    "botafogo": (
        "botafogo",
        "botafogo rj",
    ),

    "bragantino": (
        "rb bragantino",
        "red bull bragantino",
        "bragantino",
    ),

    "rb bragantino": (
        "rb bragantino",
        "red bull bragantino",
        "bragantino",
    ),

    "ceara": (
        "ceara",
        "ceara sc",
    ),

    "corinthians": (
        "corinthians",
    ),

    "coritiba": (
        "coritiba",
    ),

    "cruzeiro": (
        "cruzeiro",
    ),

    "cuiaba": (
        "cuiaba",
    ),

    "flamengo": (
        "flamengo",
    ),

    "fluminense": (
        "fluminense",
    ),

    "fortaleza": (
        "fortaleza",
        "fortaleza ec",
    ),

    "goias": (
        "goias",
    ),

    "gremio": (
        "gremio",
        "gremio fbpa",
    ),

    "internacional": (
        "internacional",
        "sc internacional",
    ),

    "juventude": (
        "juventude",
        "ec juventude",
    ),

    "palmeiras": (
        "palmeiras",
    ),

    "santos": (
        "santos",
        "santos fc",
    ),

    "sao paulo": (
        "sao paulo",
        "sao paulo fc",
    ),

    "sport": (
        "sport recife",
        "sport",
    ),

    "vasco": (
        "vasco da gama",
        "vasco",
    ),

    "vitoria": (
        "vitoria",
        "ec vitoria",
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
    "rb bragantino": "Bragantino",
    "ceara": "Ceará",
    "corinthians": "Corinthians",
    "coritiba": "Coritiba",
    "cruzeiro": "Cruzeiro",
    "cuiaba": "Cuiabá",
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "fortaleza": "Fortaleza",
    "goias": "Goiás",
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
# FUNÇÕES BÁSICAS
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
    texto = normalizar(texto)

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
            f"Erro retornado pela API-Football: {dados['errors']}"
        )

    return dados.get(
        "response",
        []
    )


def contem_algum(texto, termos):
    texto = normalizar(texto)

    return any(
        normalizar(termo) in texto
        for termo in termos
    )


# ============================================================
# FILTRO DAS COMPETIÇÕES
# ============================================================

def eh_brasileiro_u17(
    nome,
    pais,
    campeonato_id=None
):
    if campeonato_id == LIGA_BRASILEIRO_U17_ID:
        return True

    return (
        normalizar(pais) == "brazil"
        and contem_algum(
            nome,
            COMPETICOES_BASE_PERMITIDAS
        )
    )


def competicao_relevante(
    nome,
    pais,
    campeonato_id=None
):
    nome_n = normalizar(nome)
    pais_n = normalizar(pais)

    # Exceção permitida.
    if eh_brasileiro_u17(
        nome,
        pais,
        campeonato_id
    ):
        return True

    # Bloqueia demais categorias de base,
    # feminino e amistosos.
    if contem_algum(
        nome_n,
        BLOQUEADOS
    ):
        return False

    # Bloqueia divisões estaduais inferiores.
    if contem_algum(
        nome_n,
        DIVISOES_INFERIORES
    ):
        return False

    # Brasil.
    if pais_n == "brazil":
        return contem_algum(
            nome_n,
            COMPETICOES_BRASIL
        )

    # Internacional / estrangeiro.
    permitidas = (
        COMPETICOES_EXATAS_POR_PAIS.get(
            pais_n,
            set()
        )
    )

    return nome_n in permitidas


# ============================================================
# TRATAMENTO DOS CLUBES SUB-17
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
        "u17", "u-17",
        "u18", "u-18",
        "u19", "u-19",
        "u20", "u-20",
        "u21", "u-21",
        "u23", "u-23",

        "sub 17", "sub-17",
        "sub 18", "sub-18",
        "sub 19", "sub-19",
        "sub 20", "sub-20",
        "sub 21", "sub-21",
        "sub 23", "sub-23",

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
        "Buscando clubes brasileiros para corrigir "
        "nomes e escudos do Brasileiro Sub-17..."
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

        nome = team.get(
            "name",
            ""
        )

        if not nome:
            continue

        if team.get(
            "national",
            False
        ):
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

        clube = {
            "id": team.get("id"),
            "nome": nome,
            "logo": team.get("logo"),
        }

        indice.setdefault(
            chave,
            clube
        )

        # Exemplo:
        # Fortaleza EC -> Fortaleza
        # Santos FC -> Santos
        tokens = chave.split()

        if (
            len(tokens) > 1
            and tokens[-1] in {
                "fc",
                "ec",
                "sc",
                "ac"
            }
        ):
            chave_sem_sufixo = " ".join(
                tokens[:-1]
            )

            indice.setdefault(
                chave_sem_sufixo,
                clube
            )

    print(
        f"{len(indice)} nomes/aliases "
        f"de clubes indexados."
    )

    return indice


def montar_chaves_busca(nome_base):
    chave_base = chave_nome_clube(
        nome_base
    )

    chaves = [
        chave_base
    ]

    for alias in (
        ALIASES_CLUBE_PRINCIPAL.get(
            chave_base,
            ()
        )
    ):
        chave_alias = chave_nome_clube(
            alias
        )

        if (
            chave_alias
            and chave_alias not in chaves
        ):
            chaves.append(
                chave_alias
            )

    return chave_base, chaves


def pontuacao_nome(
    chave_time,
    chaves_procuradas
):
    melhor = 0.0

    for procurada in chaves_procuradas:
        if not procurada:
            continue

        if chave_time == procurada:
            return 1.0

        if (
            procurada in chave_time
            or chave_time in procurada
        ):
            melhor = max(
                melhor,
                0.92
            )

        similaridade = SequenceMatcher(
            None,
            chave_time,
            procurada
        ).ratio()

        melhor = max(
            melhor,
            similaridade
        )

    return melhor


def buscar_no_indice(
    nome_base,
    indice
):
    # CORREÇÃO DO ERRO QUE DEU NO GITHUB.
    _, chaves = montar_chaves_busca(
        nome_base
    )

    # Primeiro tenta correspondência exata.
    for chave in chaves:
        if chave in indice:
            return indice[
                chave
            ]

    # Depois tenta aproximação.
    melhor_clube = None
    melhor_score = 0.0

    for chave_time, clube in indice.items():
        score = pontuacao_nome(
            chave_time,
            chaves
        )

        if score > melhor_score:
            melhor_score = score
            melhor_clube = clube

    # Evita pegar escudo de clube errado.
    if melhor_score >= 0.78:
        return melhor_clube

    return None


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

    nome_exibicao = (
        NOMES_EXIBICAO_U17.get(
            chave_base,
            nome_base
        )
    )

    clube = buscar_no_indice(
        nome_base,
        indice
    )

    return clube, nome_exibicao


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
        "id": dados_time.get(
            "id"
        ),

        "nome": nome_original,

        "logo": logo_original,

        "vencedor": dados_time.get(
            "winner"
        ),

        "gols": goals.get(
            lado
        ),
    }

    # Jogo normal:
    # mantém exatamente o que veio da API.
    if not brasileiro_u17:
        return time_saida

    clube_principal, nome_exibicao = (
        resolver_clube_principal(
            nome_original,
            indice_principais
        )
    )

    # Remove U17 do nome mostrado no app.
    time_saida[
        "nome"
    ] = nome_exibicao

    # Mantém os dados originais
    # apenas para conferência/debug.
    time_saida[
        "nome_original_api"
    ] = nome_original

    time_saida[
        "logo_original_api"
    ] = logo_original

    # Se encontramos o clube principal,
    # usa o escudo dele.
    if (
        clube_principal
        and clube_principal.get(
            "logo"
        )
    ):
        time_saida[
            "logo"
        ] = clube_principal[
            "logo"
        ]

        time_saida[
            "clube_principal_id"
        ] = clube_principal.get(
            "id"
        )

        time_saida[
            "origem_logo"
        ] = "clube_principal"

    else:
        # Não envia a URL quebrada do U17.
        # O app pode usar seu placeholder local.
        time_saida[
            "logo"
        ] = None

        time_saida[
            "origem_logo"
        ] = "indisponivel"

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
# BUSCAR TODOS OS JOGOS DE HOJE
# ============================================================

fixtures = chamar_api(
    "fixtures",
    {
        "date": data_hoje,
        "timezone": TIMEZONE_REFERENCIA
    }
)

print(
    f"API retornou "
    f"{len(fixtures)} jogos no total."
)


# ============================================================
# VERIFICAR SE TEM BRASILEIRO SUB-17
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
        ),

        item.get(
            "league",
            {}
        ).get(
            "id"
        )
    )
    for item in fixtures
)


indice_clubes_principais = {}


# Só faz uma segunda chamada à API
# se existir Brasileiro Sub-17 no dia.
if tem_brasileiro_u17:
    indice_clubes_principais = (
        criar_indice_clubes_principais_brasil()
    )


# ============================================================
# FILTRAR E MONTAR OS JOGOS
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

    campeonato_id = league.get(
        "id"
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
        pais_campeonato,
        campeonato_id
    ):
        continue

    brasileiro_u17 = eh_brasileiro_u17(
        nome_campeonato,
        pais_campeonato,
        campeonato_id
    )

    # --------------------------------------------------------
    # TIMES
    # --------------------------------------------------------

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
    # JOGO FINAL
    # --------------------------------------------------------

    jogo = {
        "id": fixture.get(
            "id"
        ),

        # O APP DEVE USAR ESTE CAMPO
        # PARA AJUSTAR O HORÁRIO AO EPG.
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
                ),
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
                ),
        },

        "campeonato": {
            "id":
                campeonato_id,

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
                ),
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
                ),
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
                ),
        },

        "transmissao":
            [],
    }

    jogos.append(
        jogo
    )


# ============================================================
# ORDENAR PELO HORÁRIO
# ============================================================

jogos.sort(
    key=lambda jogo:
        jogo.get(
            "timestamp"
        ) or 0
)


# ============================================================
# LISTA DE CAMPEONATOS DO DIA
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
                0,
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
    key=lambda campeonato: (
        campeonato.get(
            "pais"
        ) or "",

        campeonato.get(
            "nome"
        ) or "",
    )
)


# ============================================================
# JSON FINAL
# ============================================================

saida = {
    "versao":
        8,

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
            "23:59",
    },

    "horario": {
        "campo_recomendado":
            "timestamp",

        "formato":
            "Unix timestamp",

        "observacao":
            "Converter usando o mesmo "
            "timezone/offset configurado "
            "para o EPG.",
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
        jogos,
}


# ============================================================
# SALVAR JSON
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
# LOG FINAL
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
        "Brasileiro Sub-17: "
        "nomes corrigidos e logos dos "
        "clubes principais ativados."
    )


print(
    "JSON atualizado com sucesso."
)
