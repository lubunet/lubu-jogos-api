import os
import json
import requests

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
# FUNÇÃO PARA CHAMAR A API
# ============================================================

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


# ============================================================
# DATA DE HOJE
# ============================================================

tz_referencia = ZoneInfo(TIMEZONE_REFERENCIA)

agora = datetime.now(tz_referencia)

data_hoje = agora.strftime("%Y-%m-%d")


print(
    f"Buscando todos os jogos de {data_hoje}..."
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
    f"{len(fixtures)} jogos encontrados."
)


# ============================================================
# MONTAR JOGOS
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


    casa = teams.get(
        "home",
        {}
    )

    fora = teams.get(
        "away",
        {}
    )


    # --------------------------------------------------------
    # HORÁRIO
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # MONTAR O OBJETO DO JOGO
    # --------------------------------------------------------

    jogo = {

        "id": fixture.get("id"),


        # CAMPO PRINCIPAL PARA HORÁRIO.
        #
        # O app deve converter isso usando
        # o mesmo timezone/offset usado pelo EPG.
        "timestamp": fixture.get(
            "timestamp"
        ),


        "inicio_utc": inicio_utc,


        # Somente referência/debug.
        "horario_referencia": {

            "timezone": TIMEZONE_REFERENCIA,

            "data": data_referencia.strftime(
                "%Y-%m-%d"
            ),

            "horario": data_referencia.strftime(
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


        # ----------------------------------------------------
        # CAMPEONATO
        #
        # É ISSO QUE O LUBU VAI USAR PARA SEPARAR:
        #
        # Serie B
        # Copa Paulista
        # Libertadores
        # Premier League
        # etc.
        # ----------------------------------------------------

        "campeonato": {

            "id": league.get(
                "id"
            ),

            "nome": league.get(
                "name"
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


        # ----------------------------------------------------
        # TIME DA CASA
        # ----------------------------------------------------

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
            )
        },


        # ----------------------------------------------------
        # TIME VISITANTE
        # ----------------------------------------------------

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
            )
        },


        # ----------------------------------------------------
        # PLACAR
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # ESTÁDIO
        # ----------------------------------------------------

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


        # Futuramente preencheremos
        # com canais de transmissão.
        "transmissao": []

    }


    jogos.append(
        jogo
    )


# ============================================================
# ORDENAR PELO HORÁRIO
# ============================================================

jogos.sort(
    key=lambda jogo:
        jogo.get("timestamp") or 0
)


# ============================================================
# CRIAR LISTA DE CAMPEONATOS DISPONÍVEIS HOJE
# ============================================================

campeonatos = {}


for jogo in jogos:

    campeonato = jogo["campeonato"]

    campeonato_id = campeonato.get(
        "id"
    )

    if campeonato_id is None:
        continue


    if campeonato_id not in campeonatos:

        campeonatos[campeonato_id] = {

            "id": campeonato_id,

            "nome": campeonato.get(
                "nome"
            ),

            "pais": campeonato.get(
                "pais"
            ),

            "logo": campeonato.get(
                "logo"
            ),

            "bandeira": campeonato.get(
                "bandeira"
            ),

            "quantidade_jogos": 0
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
            campeonato.get("pais") or "",
            campeonato.get("nome") or ""
        )
)


# ============================================================
# GERAR JSON
# ============================================================

saida = {

    "versao": 3,

    "data": data_hoje,

    "gerado_em": agora.isoformat(),

    "timezone_referencia": TIMEZONE_REFERENCIA,


    "periodo": {

        "inicio": "00:00",

        "fim": "23:59"
    },


    "horario": {

        "campo_recomendado": "timestamp",

        "formato": "Unix timestamp",

        "observacao":
            "O aplicativo deve converter o timestamp "
            "usando o mesmo timezone ou ajuste utilizado "
            "pelo EPG."
    },


    "quantidade_campeonatos": len(
        lista_campeonatos
    ),

    "quantidade_jogos": len(
        jogos
    ),


    # Lista resumida para facilitar a criação
    # das categorias no aplicativo.
    "campeonatos": lista_campeonatos,


    # Lista completa de partidas.
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
    f"{len(jogos)} jogos salvos."
)

print(
    f"{len(lista_campeonatos)} campeonatos encontrados."
)

print(
    "Arquivo data/jogos-hoje.json atualizado."
)
