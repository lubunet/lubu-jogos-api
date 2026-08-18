import os
import json
import requests

from datetime import datetime
from zoneinfo import ZoneInfo


API_URL = "https://v3.football.api-sports.io"
API_KEY = os.environ["API_FOOTBALL_KEY"]

TIMEZONE = "America/Cuiaba"

headers = {
    "x-apisports-key": API_KEY
}


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


# ------------------------------------------------
# DATA ATUAL NO HORÁRIO DE CUIABÁ
# ------------------------------------------------

timezone_cuiaba = ZoneInfo(TIMEZONE)

agora = datetime.now(timezone_cuiaba)

data_hoje = agora.strftime("%Y-%m-%d")


print(f"Buscando jogos de {data_hoje}")


# ------------------------------------------------
# BUSCAR TODOS OS CLUBES BRASILEIROS
# ------------------------------------------------

print("Buscando clubes brasileiros...")

times = chamar_api(
    "teams",
    {
        "country": "Brazil"
    }
)


ids_times_brasileiros = set()


for item in times:

    time = item.get("team", {})

    # Ignora seleções nacionais.
    # Mantém apenas clubes.
    if not time.get("national", False):

        team_id = time.get("id")

        if team_id:
            ids_times_brasileiros.add(team_id)


print(
    f"{len(ids_times_brasileiros)} clubes brasileiros encontrados."
)


# ------------------------------------------------
# BUSCAR TODOS OS JOGOS DO DIA
# ------------------------------------------------

print("Buscando jogos do dia...")

fixtures = chamar_api(
    "fixtures",
    {
        "date": data_hoje,
        "timezone": TIMEZONE
    }
)


print(
    f"{len(fixtures)} jogos encontrados no mundo."
)


# ------------------------------------------------
# FILTRAR APENAS JOGOS COM CLUBES BRASILEIROS
# ------------------------------------------------

jogos = []


for item in fixtures:

    fixture = item.get("fixture", {})
    league = item.get("league", {})
    teams = item.get("teams", {})
    goals = item.get("goals", {})
    score = item.get("score", {})

    casa = teams.get("home", {})
    fora = teams.get("away", {})

    casa_id = casa.get("id")
    fora_id = fora.get("id")


    # Se nenhum dos dois clubes for brasileiro,
    # ignora a partida.
    if (
        casa_id not in ids_times_brasileiros
        and
        fora_id not in ids_times_brasileiros
    ):
        continue


    data_partida = datetime.fromisoformat(
        fixture["date"]
    ).astimezone(timezone_cuiaba)


    jogo = {

        "id": fixture.get("id"),

        "data": data_partida.strftime("%Y-%m-%d"),

        "horario": data_partida.strftime("%H:%M"),

        "timestamp": fixture.get("timestamp"),


        "status": {
            "codigo": fixture.get("status", {}).get("short"),
            "descricao": fixture.get("status", {}).get("long"),
            "minuto": fixture.get("status", {}).get("elapsed")
        },


        "campeonato": {
            "id": league.get("id"),
            "nome": league.get("name"),
            "pais": league.get("country"),
            "logo": league.get("logo"),
            "bandeira": league.get("flag"),
            "temporada": league.get("season"),
            "rodada": league.get("round")
        },


        "casa": {
            "id": casa.get("id"),
            "nome": casa.get("name"),
            "logo": casa.get("logo"),
            "vencedor": casa.get("winner"),
            "gols": goals.get("home")
        },


        "fora": {
            "id": fora.get("id"),
            "nome": fora.get("name"),
            "logo": fora.get("logo"),
            "vencedor": fora.get("winner"),
            "gols": goals.get("away")
        },


        "placar": {
            "intervalo": score.get("halftime"),
            "final": score.get("fulltime"),
            "prorrogacao": score.get("extratime"),
            "penaltis": score.get("penalty")
        },


        "estadio": {
            "id": fixture.get("venue", {}).get("id"),
            "nome": fixture.get("venue", {}).get("name"),
            "cidade": fixture.get("venue", {}).get("city")
        },


        # Vamos preencher isso posteriormente
        # com os canais de transmissão.
        "transmissao": []

    }

    jogos.append(jogo)


# ------------------------------------------------
# ORDENAR PELO HORÁRIO
# ------------------------------------------------

jogos.sort(
    key=lambda jogo: jogo.get("timestamp") or 0
)


# ------------------------------------------------
# GERAR JSON
# ------------------------------------------------

saida = {

    "data": data_hoje,

    "timezone": TIMEZONE,

    "periodo": {
        "inicio": "00:00",
        "fim": "23:59"
    },

    "atualizado_em": agora.isoformat(),

    "quantidade": len(jogos),

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


print(
    f"{len(jogos)} jogos com clubes brasileiros encontrados."
)

print(
    "Arquivo data/jogos-hoje.json criado."
)
