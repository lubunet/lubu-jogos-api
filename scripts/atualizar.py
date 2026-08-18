import os
import json
import requests
import unicodedata

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURAÇÕES
# ============================================================

API_URL = "https://v3.football.api-sports.io"
API_KEY = os.environ["API_FOOTBALL_KEY"]

TIMEZONE_REFERENCIA = "America/Cuiaba"

headers = {
    "x-apisports-key": API_KEY
}


# ============================================================
# COMPETIÇÕES QUE QUEREMOS
# ============================================================

COMPETICOES_PRINCIPAIS = {
    # Brasil - Nacional
    "serie a",
    "serie b",
    "serie c",
    "serie d",
    "copa do brasil",
    "supercopa do brasil",
    "copa do nordeste",
    "copa verde",

    # América do Sul
    "conmebol libertadores",
    "conmebol sudamericana",
    "conmebol recopa",
    "recopa sudamericana",

    # Mundial
    "fifa club world cup",
    "club world cup",
    "fifa intercontinental cup",
    "intercontinental cup",
}


# Principais estaduais
ESTADUAIS_PRINCIPAIS = (
    "paulista - a1",
    "paulista a1",

    "carioca - 1",
    "carioca serie a",

    "mineiro - 1",
    "mineiro modulo i",

    "gaucho - 1",
    "gaucho 1",

    "paranaense - 1",
    "paranaense 1",

    "baiano - 1",
    "baiano 1",

    "pernambucano - 1",
    "pernambucano 1",

    "cearense - 1",
    "cearense 1",

    "goiano - 1",
    "goiano 1",

    "catarinense - 1",
    "catarinense 1",

    "paraense",

    "amazonense",
)


# Qualquer competição com essas palavras é ignorada,
# mesmo se começar com um nome parecido com estadual.
PALAVRAS_BLOQUEADAS = (
    "u17",
    "u-17",
    "sub 17",
    "sub-17",

    "u20",
    "u-20",
    "sub 20",
    "sub-20",

    "u23",
    "u-23",
    "sub 23",
    "sub-23",

    "youth",
    "junior",
    "juniors",

    "women",
    "womens",
    "women's",
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
            f"Erro retornado pela API-Football: "
            f"{dados['errors']}"
        )

    return dados.get("response", [])


def competicao_relevante(nome):

    nome_normalizado = normalizar(nome)


    # Primeiro bloqueia base, feminino etc.
    for palavra in PALAVRAS_BLOQUEADAS:

        if normalizar(palavra) in nome_normalizado:
            return False


    # Competições nacionais/internacionais
    if nome_normalizado in COMPETICOES_PRINCIPAIS:
        return True


    # Principais estaduais
    for estadual in ESTADUAIS_PRINCIPAIS:

        if nome_normalizado.startswith(
            normalizar(estadual)
        ):
            return True


    return False


def categoria_competicao(nome):

    nome = normalizar(nome)


    internacionais = (
        "libertadores",
        "sudamericana",
        "recopa",
        "club world cup",
        "intercontinental"
    )

    for termo in internacionais:

        if termo in nome:
            return "internacional"


    nacionais = (
        "serie a",
        "serie b",
        "serie c",
        "serie d",
        "copa do brasil",
        "supercopa",
        "copa do nordeste",
        "copa verde"
    )

    if nome in nacionais:
        return "nacional"


    return "estadual"


# ============================================================
# HORÁRIO
# ============================================================

tz_referencia = ZoneInfo(
    TIMEZONE_REFERENCIA
)

agora = datetime.now(
    tz_referencia
)

data_referencia = agora.date()


# ============================================================
# BUSCAR CLUBES BRASILEIROS
# ============================================================

print(
    "Buscando clubes brasileiros..."
)

times = chamar_api(
    "teams",
    {
        "country": "Brazil"
    }
)


ids_times_brasileiros = set()


for item in times:

    time = item.get(
        "team",
        {}
    )

    # Ignora seleção brasileira
    if time.get("national", False):
        continue

    team_id = time.get("id")

    if team_id:
        ids_times_brasileiros.add(
            team_id
        )


print(
    f"{len(ids_times_brasileiros)} "
    f"clubes brasileiros encontrados."
)


# ============================================================
# BUSCAR ONTEM + HOJE + AMANHÃ
#
# Isso é proposital.
#
# Assim o LUBU consegue converter o timestamp para o timezone
# escolhido no próprio app e depois decidir quais jogos
# pertencem ao dia atual entre 00:00 e 23:59.
# ============================================================

datas_consulta = [
    data_referencia - timedelta(days=1),
    data_referencia,
    data_referencia + timedelta(days=1)
]


fixtures = []


for data_consulta in datas_consulta:

    data_str = data_consulta.isoformat()

    print(
        f"Buscando partidas de {data_str}..."
    )

    resposta = chamar_api(
        "fixtures",
        {
            "date": data_str,
            "timezone": TIMEZONE_REFERENCIA
        }
    )

    fixtures.extend(resposta)


print(
    f"{len(fixtures)} partidas recebidas "
    f"antes dos filtros."
)


# ============================================================
# FILTRAR PARTIDAS
# ============================================================

jogos = []

ids_adicionados = set()


for item in fixtures:

    fixture = item.get(
        "fixture",
        {}
    )

    fixture_id = fixture.get("id")


    # Evita partidas duplicadas
    if fixture_id in ids_adicionados:
        continue


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


    casa = teams.get(
        "home",
        {}
    )

    fora = teams.get(
        "away",
        {}
    )


    casa_id = casa.get("id")
    fora_id = fora.get("id")


    # --------------------------------------------------------
    # PRECISA TER PELO MENOS UM CLUBE BRASILEIRO
    # --------------------------------------------------------

    if (
        casa_id not in ids_times_brasileiros
        and
        fora_id not in ids_times_brasileiros
    ):
        continue


    # --------------------------------------------------------
    # FILTRO DE COMPETIÇÃO
    # --------------------------------------------------------

    nome_campeonato = league.get(
        "name",
        ""
    )


    if not competicao_relevante(
        nome_campeonato
    ):

        print(
            f"Ignorado: "
            f"{nome_campeonato} - "
            f"{casa.get('name')} x "
            f"{fora.get('name')}"
        )

        continue


    # --------------------------------------------------------
    # HORÁRIO
    # --------------------------------------------------------

    data_partida = datetime.fromisoformat(
        fixture["date"]
    )


    data_utc = data_partida.astimezone(
        timezone.utc
    )


    data_cuiaba = data_partida.astimezone(
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
    # MONTAR JOGO
    # --------------------------------------------------------

    jogo = {

        "id": fixture_id,


        # ESTE É O CAMPO PRINCIPAL DE HORÁRIO
        #
        # O LUBU deve converter este timestamp
        # usando o MESMO timezone/offset do EPG.
        "timestamp": fixture.get(
            "timestamp"
        ),


        # Horário universal.
        "inicio_utc": inicio_utc,


        # Apenas para conferência/debug.
        # NÃO deve ser a referência principal no app.
        "horario_referencia": {

            "timezone": TIMEZONE_REFERENCIA,

            "data": data_cuiaba.strftime(
                "%Y-%m-%d"
            ),

            "horario": data_cuiaba.strftime(
                "%H:%M"
            )
        },


        "status": {

            "codigo": fixture.get(
                "status",
                {}
            ).get(
                "short"
            ),

            "descricao": fixture.get(
                "status",
                {}
            ).get(
                "long"
            ),

            "minuto": fixture.get(
                "status",
                {}
            ).get(
                "elapsed"
            )
        },


        "campeonato": {

            "id": league.get("id"),

            "nome": nome_campeonato,

            "categoria": categoria_competicao(
                nome_campeonato
            ),

            "pais": league.get(
                "country"
            ),

            "logo": league.get(
                "logo"
            ),

            "bandeira": league.get(
                "flag"
            ),

            "temporada": league.get(
                "season"
            ),

            "rodada": league.get(
                "round"
            )
        },


        "casa": {

            "id": casa.get(
                "id"
            ),

            "nome": casa.get(
                "name"
            ),

            "logo": casa.get(
                "logo"
            ),

            "vencedor": casa.get(
                "winner"
            ),

            "gols": goals.get(
                "home"
            ),

            "brasileiro":
                casa_id
                in
                ids_times_brasileiros
        },


        "fora": {

            "id": fora.get(
                "id"
            ),

            "nome": fora.get(
                "name"
            ),

            "logo": fora.get(
                "logo"
            ),

            "vencedor": fora.get(
                "winner"
            ),

            "gols": goals.get(
                "away"
            ),

            "brasileiro":
                fora_id
                in
                ids_times_brasileiros
        },


        "placar": {

            "intervalo": score.get(
                "halftime"
            ),

            "final": score.get(
                "fulltime"
            ),

            "prorrogacao": score.get(
                "extratime"
            ),

            "penaltis": score.get(
                "penalty"
            )
        },


        "estadio": {

            "id": fixture.get(
                "venue",
                {}
            ).get(
                "id"
            ),

            "nome": fixture.get(
                "venue",
                {}
            ).get(
                "name"
            ),

            "cidade": fixture.get(
                "venue",
                {}
            ).get(
                "city"
            )
        },


        # Preencheremos depois
        # usando a fonte de canais.
        "transmissao": []

    }


    jogos.append(
        jogo
    )

    ids_adicionados.add(
        fixture_id
    )


# ============================================================
# ORDENAR
# ============================================================

jogos.sort(
    key=lambda jogo:
        jogo.get(
            "timestamp"
        )
        or 0
)


# ============================================================
# GERAR JSON
# ============================================================

saida = {

    "versao": 2,

    "gerado_em": agora.isoformat(),

    "timezone_referencia": TIMEZONE_REFERENCIA,


    "horario": {

        "campo_recomendado": "timestamp",

        "formato": "Unix timestamp",

        "observacao":
            "O aplicativo deve converter o timestamp "
            "usando o mesmo timezone ou ajuste do EPG."
    },


    "janela_consultada": {

        "inicio":
            datas_consulta[0].isoformat(),

        "fim":
            datas_consulta[-1].isoformat()
    },


    "quantidade": len(
        jogos
    ),


    "jogos": jogos

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
    f"{len(jogos)} partidas relevantes "
    f"com clubes brasileiros."
)

print(
    "Arquivo data/jogos-hoje.json atualizado."
)
