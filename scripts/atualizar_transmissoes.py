import json
import os
import re
import unicodedata

from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURACAO
# ============================================================

ARQUIVO_JSON = "data/jogos-hoje.json"

URL_DPF = (
    "https://doentesporfutebol.com.br/guiadejogos/"
)

URL_MANTOS = (
    "https://mantosdofutebol.com.br/"
    "guia-de-jogos-tv-hoje-ao-vivo/"
)


# Os dois sites usam horario de Brasilia.
TIMEZONE_FONTE = ZoneInfo(
    "America/Sao_Paulo"
)


# SEGURANCA MAXIMA:
# canal precisa aparecer nas DUAS fontes.
CONFIRMACOES_MINIMAS = 2


# Horario dos sites pode ter um pequeno ajuste.
TOLERANCIA_HORARIO_MINUTOS = 10


TIMEOUT = 25


HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),

    "Accept-Language":
        "pt-BR,pt;q=0.9,en;q=0.7",

    "Cache-Control":
        "no-cache",
}


# ============================================================
# ALIASES DE TIMES
# ============================================================

ALIASES_TIMES = {

    "atletico":
        "atletico mg",

    "atletico mg":
        "atletico mg",

    "atletico mineiro":
        "atletico mg",

    "clube atletico mineiro":
        "atletico mg",


    "red bull bragantino":
        "bragantino",

    "rb bragantino":
        "bragantino",

    "bragantino":
        "bragantino",


    "america mineiro":
        "america mg",

    "america mg":
        "america mg",


    "athletico paranaense":
        "athletico pr",

    "athletico pr":
        "athletico pr",


    "atletico goianiense":
        "atletico go",

    "atletico go":
        "atletico go",


    "sao paulo fc":
        "sao paulo",


    "gremio fbpa":
        "gremio",


    "sc internacional":
        "internacional",


    "ec juventude":
        "juventude",


    "ec bahia":
        "bahia",


    "ec vitoria":
        "vitoria",


    "sport recife":
        "sport",


    "vasco da gama":
        "vasco",


    "ceara sc":
        "ceara",


    "fortaleza ec":
        "fortaleza",


    "botafogo de sao paulo":
        "botafogo sp",

    "botafogo sp":
        "botafogo sp",


    "operario ferroviario":
        "operario",

    "operario pr":
        "operario",

    "operario":
        "operario",


    "nec nijmegen":
        "nijmegen",

    "nijmegen":
        "nijmegen",


    "lask linz":
        "lask",

    "lask":
        "lask",


    "slovan batislava":
        "slovan bratislava",

    "slovan bratislava":
        "slovan bratislava",


    "fc cincinnati":
        "cincinnati",


    "new england revolution":
        "new england revolution",

    "ne revolution":
        "new england revolution",


    "new york red bulls":
        "new york red bulls",

    "ny red bulls":
        "new york red bulls",


    "minnesota united":
        "minnesota",

    "minnesota":
        "minnesota",


    "los angeles galaxy":
        "la galaxy",

    "la galaxy":
        "la galaxy",


    "san jose earthquakes":
        "san jose earthquakes",

    "sj earthquakes":
        "san jose earthquakes",
}


# ============================================================
# ALIASES DE CANAIS
# ============================================================

ALIASES_CANAIS = {

    "espn4":
        "espn 4",

    "espn 4":
        "espn 4",

    "espn":
        "espn",

    "sportv":
        "sportv",

    "globo":
        "globo",

    "ge tv":
        "ge tv",

    "getv":
        "ge tv",

    "paramount+":
        "paramount+",

    "paramount plus":
        "paramount+",

    "disney+":
        "disney+",

    "disney plus":
        "disney+",

    "hbo max":
        "hbo max",

    "tnt":
        "tnt",

    "space":
        "space",

    "xsports":
        "xsports",

    "x sports":
        "xsports",

    "sportynet":
        "sportynet",

    "paulistao":
        "paulistao",

    "caze tv":
        "caze tv",

    "cazetv":
        "caze tv",

    "apple tv":
        "apple tv",

    "appletv":
        "apple tv",

    "onefootball":
        "onefootball",
}


EXIBICAO_CANAIS = {

    "espn":
        "ESPN",

    "espn 4":
        "ESPN 4",

    "sportv":
        "SporTV",

    "globo":
        "Globo",

    "ge tv":
        "GE TV",

    "paramount+":
        "Paramount+",

    "disney+":
        "Disney+",

    "hbo max":
        "HBO Max",

    "tnt":
        "TNT",

    "space":
        "Space",

    "xsports":
        "XSports",

    "sportynet":
        "SportyNet",

    "paulistao":
        "Paulistao",

    "caze tv":
        "CazeTV",

    "apple tv":
        "Apple TV",

    "onefootball":
        "OneFootball",
}


# ============================================================
# NORMALIZACAO
# ============================================================

def sem_acentos(texto):

    return unicodedata.normalize(
        "NFKD",
        str(texto or "")
    ).encode(
        "ascii",
        "ignore"
    ).decode(
        "ascii"
    )


def limpar_espacos(texto):

    return re.sub(
        r"\s+",
        " ",
        str(texto or "")
    ).strip()


def normalizar_texto(texto):

    texto = sem_acentos(
        texto
    ).lower()

    texto = texto.replace(
        "&",
        " e "
    )

    texto = re.sub(
        r"[^a-z0-9+]+",
        " ",
        texto
    )

    return limpar_espacos(
        texto
    )


def normalizar_time(nome):

    nome = normalizar_texto(
        nome
    )

    tokens = [

        token

        for token in nome.split()

        if token not in {
            "fc",
            "ec",
            "sc",
            "ac"
        }
    ]

    nome = " ".join(
        tokens
    )

    return ALIASES_TIMES.get(
        nome,
        nome
    )


def times_batem(a, b):

    a = normalizar_time(
        a
    )

    b = normalizar_time(
        b
    )

    if not a or not b:
        return False

    if a == b:
        return True

    # Apenas pequenas variacoes de escrita.
    return SequenceMatcher(
        None,
        a,
        b
    ).ratio() >= 0.92


# ============================================================
# COMPETICOES
# ============================================================

def normalizar_competicao(nome):

    nome = normalizar_texto(
        nome
    )

    regras = (

        (
            (
                "sudamericana",
                "sul americana"
            ),
            "sudamericana"
        ),

        (
            (
                "libertadores",
            ),
            "libertadores"
        ),

        (
            (
                "serie b",
                "brasileirao serie b",
                "brasileiro serie b"
            ),
            "serie b"
        ),

        (
            (
                "sub 17",
                "u17",
                "u 17"
            ),
            "brasileiro u17"
        ),

        (
            (
                "copa paulista",
            ),
            "copa paulista"
        ),

        (
            (
                "champions league",
            ),
            "champions league"
        ),

        (
            (
                "la liga",
                "laliga",
                "campeonato espanhol"
            ),
            "la liga"
        ),

        (
            (
                "major league soccer",
                "mls"
            ),
            "mls"
        ),

        (
            (
                "king s cup",
                "kings cup"
            ),
            "kings cup"
        ),
    )

    for termos, canonico in regras:

        if any(
            termo in nome
            for termo in termos
        ):

            return canonico

    return nome


def competicoes_batem(a, b):

    a = normalizar_competicao(
        a
    )

    b = normalizar_competicao(
        b
    )

    if not a or not b:
        return False

    if a == b:
        return True

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio() >= 0.88


# ============================================================
# CANAIS
# ============================================================

def normalizar_canal(canal):

    texto = limpar_espacos(
        canal
    )

    if not texto:
        return ""

    texto = sem_acentos(
        texto
    ).lower().strip()

    texto = texto.replace(
        "youtube.com/@",
        ""
    )

    texto = texto.replace(
        "youtube.com/",
        ""
    )

    texto = texto.replace(
        "www.",
        ""
    )

    simples = normalizar_texto(
        texto
    )

    perfis = {

        "tntsportsbr":
            "tnt",

        "getv":
            "ge tv",

        "cazetv":
            "caze tv",

        "paulistao":
            "paulistao",

        "sportynetbrasil":
            "sportynet",
    }

    if simples in perfis:

        return perfis[
            simples
        ]

    if texto in ALIASES_CANAIS:

        return ALIASES_CANAIS[
            texto
        ]

    if simples in ALIASES_CANAIS:

        return ALIASES_CANAIS[
            simples
        ]

    return simples


def nome_exibicao_canal(chave):

    if chave in EXIBICAO_CANAIS:

        return EXIBICAO_CANAIS[
            chave
        ]

    return " ".join(

        parte.upper()
        if len(parte) <= 4

        else
        parte.title()

        for parte in chave.split()
    )


def dividir_canais(texto):

    texto = limpar_espacos(
        texto
    )

    texto = re.sub(

        r"^(?:📺\s*)?"
        r"(?:canais?|transmissao)\s*:\s*",

        "",

        texto,

        flags=re.IGNORECASE
    )

    texto = re.sub(
        r"^📺\s*",
        "",
        texto
    ).strip()

    partes = re.split(

        r"\s*;\s*"
        r"|\s*,\s*"
        r"|\s+\be\b\s+",

        texto,

        flags=re.IGNORECASE
    )

    resultado = []

    for parte in partes:

        canal = normalizar_canal(
            parte
        )

        if (
            canal
            and canal not in resultado
        ):

            resultado.append(
                canal
            )

    return resultado


# ============================================================
# DOWNLOAD
# ============================================================

def baixar_html(url):

    try:

        resposta = requests.get(

            url,

            headers=HEADERS,

            timeout=TIMEOUT
        )

        if resposta.status_code != 200:
            return None

        tipo = resposta.headers.get(
            "Content-Type",
            ""
        ).lower()

        if "html" not in tipo:
            return None

        # Evita interpretar pagina vazia,
        # bloqueio ou resposta incompleta.
        if len(resposta.text) < 1500:
            return None

        return resposta.text

    except requests.RequestException:

        return None


# ============================================================
# VALIDAR DATA
# ============================================================

def pagina_parece_ser_do_dia(
    texto,
    data_json
):

    # Tolera pequenas mudancas como:
    # 19/08
    # 19 / 08
    # 19/0 8

    texto = re.sub(
        r"(?<=\d)\s+(?=\d)",
        "",
        texto
    )

    try:

        data = datetime.strptime(
            data_json,
            "%Y-%m-%d"
        )

    except (
        TypeError,
        ValueError
    ):

        return False


    # Formato 19/08/2026
    completos = re.findall(

        r"\b(\d{1,2})\s*/\s*"
        r"(\d{1,2})\s*/\s*"
        r"(\d{4})\b",

        texto
    )

    for dia, mes, ano in completos:

        if (
            int(dia) == data.day
            and
            int(mes) == data.month
            and
            int(ano) == data.year
        ):

            return True


    # Formato 19/08
    curtos = re.findall(

        r"\b(\d{1,2})\s*/\s*"
        r"(\d{1,2})\b",

        texto
    )

    for dia, mes in curtos:

        if (
            int(dia) == data.day
            and
            int(mes) == data.month
        ):

            return True

    return False


# ============================================================
# TEXTO DA PAGINA
# ============================================================

def linhas_da_pagina(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg"
        ]
    ):

        tag.decompose()

    linhas = []

    for linha in soup.get_text(
        "\n"
    ).splitlines():

        linha = limpar_espacos(
            linha
        )

        if linha:

            linhas.append(
                linha
            )

    return linhas


def separar_times(texto):

    partes = re.split(

        r"\s+[xX×]\s+",

        limpar_espacos(
            texto
        ),

        maxsplit=1
    )

    if len(partes) != 2:
        return None

    casa = limpar_espacos(
        partes[0]
    )

    fora = limpar_espacos(
        partes[1]
    )

    if not casa or not fora:
        return None

    return (
        casa,
        fora
    )


def minutos_do_dia(
    hora,
    minuto
):

    return (
        int(hora) * 60
        +
        int(minuto)
    )


# ============================================================
# PARSER DPF
# ============================================================

def parse_dpf(
    html,
    data_json
):

    linhas = linhas_da_pagina(
        html
    )

    if not pagina_parece_ser_do_dia(

        "\n".join(
            linhas
        ),

        data_json
    ):

        return []


    eventos = []


    padrao_horario = re.compile(

        r"^(?:🕗\s*)?"
        r"(\d{1,2}):(\d{2})\s+(.+)$"
    )


    for indice, linha in enumerate(
        linhas
    ):

        resultado = padrao_horario.match(
            linha
        )

        if not resultado:
            continue


        hora, minuto, competicao = (
            resultado.groups()
        )


        if (
            int(hora) > 23
            or
            int(minuto) > 59
        ):

            continue


        times = None
        canais = None


        proximas = linhas[
            indice + 1:
            indice + 7
        ]


        for posicao, proxima in enumerate(
            proximas
        ):

            if times is None:

                tentativa = separar_times(
                    proxima
                )

                if tentativa:

                    times = tentativa

                continue


            # So aceita transmissao quando a
            # linha esta identificada como tal.
            if (
                proxima.startswith("📺")
                or
                re.match(
                    r"^(?:canais?|transmissao)\s*:",
                    proxima,
                    flags=re.IGNORECASE
                )
            ):

                canais = dividir_canais(
                    proxima
                )


                # Caso o icone venha separado
                # do texto depois de uma mudanca
                # pequena no HTML.
                if (
                    not canais
                    and
                    posicao + 1
                    < len(proximas)
                ):

                    seguinte = proximas[
                        posicao + 1
                    ]

                    if (
                        not padrao_horario.match(
                            seguinte
                        )
                        and
                        separar_times(
                            seguinte
                        ) is None
                    ):

                        canais = dividir_canais(
                            seguinte
                        )

                break


        if (
            times
            and
            canais
        ):

            eventos.append({

                "hora":
                    minutos_do_dia(
                        hora,
                        minuto
                    ),

                "casa":
                    times[0],

                "fora":
                    times[1],

                "competicao":
                    limpar_espacos(
                        competicao
                    ),

                "canais":
                    canais,
            })


    return eventos


# ============================================================
# PARSER MANTOS
# ============================================================

def parse_mantos(
    html,
    data_json
):

    linhas = linhas_da_pagina(
        html
    )


    if not pagina_parece_ser_do_dia(

        "\n".join(
            linhas
        ),

        data_json
    ):

        return []


    eventos = []


    padrao_evento = re.compile(

        r"^(\d{1,2})h(\d{2})"
        r"\s*[–—-]\s*"
        r"(.+?)\s+[xX×]\s+"
        r"(.+?)\s*[–—-]\s*"
        r"(.+)$",

        flags=re.IGNORECASE
    )


    for indice, linha in enumerate(
        linhas
    ):

        resultado = padrao_evento.match(
            linha
        )

        if not resultado:
            continue


        (
            hora,
            minuto,
            casa,
            fora,
            competicao

        ) = resultado.groups()


        if (
            int(hora) > 23
            or
            int(minuto) > 59
        ):

            continue


        canais = None


        for proxima in linhas[
            indice + 1:
            indice + 5
        ]:

            if re.match(

                r"^(?:canais?|transmissao)\s*:",

                proxima,

                flags=re.IGNORECASE
            ):

                canais = dividir_canais(
                    proxima
                )

                break


        if canais:

            eventos.append({

                "hora":
                    minutos_do_dia(
                        hora,
                        minuto
                    ),

                "casa":
                    limpar_espacos(
                        casa
                    ),

                "fora":
                    limpar_espacos(
                        fora
                    ),

                "competicao":
                    limpar_espacos(
                        competicao
                    ),

                "canais":
                    canais,
            })


    return eventos


# ============================================================
# HORARIO DO JSON -> BRASILIA
# ============================================================

def horario_brasilia_do_jogo(
    jogo
):

    timestamp = jogo.get(
        "timestamp"
    )

    if not isinstance(
        timestamp,
        (int, float)
    ):

        return None


    try:

        data = datetime.fromtimestamp(

            timestamp,

            tz=ZoneInfo(
                "UTC"
            )

        ).astimezone(
            TIMEZONE_FONTE
        )


        return (
            data.hour * 60
            +
            data.minute
        )

    except (
        OverflowError,
        OSError,
        ValueError
    ):

        return None


def diferenca_minutos(
    a,
    b
):

    diferenca = abs(
        a - b
    )

    return min(
        diferenca,
        1440 - diferenca
    )


# ============================================================
# LOCALIZAR MESMO JOGO
# ============================================================

def encontrar_evento(
    jogo,
    eventos
):

    casa = jogo.get(
        "casa",
        {}
    ).get(
        "nome",
        ""
    )


    fora = jogo.get(
        "fora",
        {}
    ).get(
        "nome",
        ""
    )


    competicao = jogo.get(
        "campeonato",
        {}
    ).get(
        "nome",
        ""
    )


    hora = horario_brasilia_do_jogo(
        jogo
    )


    if (
        not casa
        or
        not fora
        or
        not competicao
        or
        hora is None
    ):

        return None


    candidatos = []


    for evento in eventos:


        # HORARIO
        if diferenca_minutos(

            hora,

            evento[
                "hora"
            ]

        ) > TOLERANCIA_HORARIO_MINUTOS:

            continue


        # TIME DA CASA
        if not times_batem(

            casa,

            evento[
                "casa"
            ]
        ):

            continue


        # TIME VISITANTE
        if not times_batem(

            fora,

            evento[
                "fora"
            ]
        ):

            continue


        # COMPETICAO
        if not competicoes_batem(

            competicao,

            evento[
                "competicao"
            ]
        ):

            continue


        candidatos.append(
            evento
        )


    # Se encontrou mais de uma possibilidade,
    # nao adivinha.
    if len(candidatos) != 1:

        return None


    return candidatos[
        0
    ]


# ============================================================
# CONFIRMAR CANAIS NAS DUAS FONTES
# ============================================================

def transmissoes_confirmadas(
    jogo,
    fontes
):

    encontrados = []


    for eventos in fontes.values():

        evento = encontrar_evento(
            jogo,
            eventos
        )

        if evento:

            encontrados.append(
                evento
            )


    if len(
        encontrados
    ) < CONFIRMACOES_MINIMAS:

        return None


    votos = Counter()


    for evento in encontrados:

        # Cada site conta apenas uma vez.
        for canal in set(
            evento[
                "canais"
            ]
        ):

            votos[
                canal
            ] += 1


    canais_confirmados = sorted(

        canal

        for canal, quantidade
        in votos.items()

        if quantidade
        >=
        CONFIRMACOES_MINIMAS
    )


    if not canais_confirmados:

        return None


    return [

        {
            "canal":
                nome_exibicao_canal(
                    canal
                ),

            "fonte":
                "DPF + Mantos"
        }

        for canal
        in canais_confirmados
    ]


# ============================================================
# PRINCIPAL
# ============================================================

def main():

    # --------------------------------------------------------
    # ABRIR JSON
    # --------------------------------------------------------

    try:

        with open(

            ARQUIVO_JSON,

            "r",

            encoding="utf-8"

        ) as arquivo:

            dados = json.load(
                arquivo
            )

    except (
        OSError,
        json.JSONDecodeError
    ):

        return 0


    data_json = dados.get(
        "data"
    )

    jogos = dados.get(
        "jogos"
    )


    if (
        not data_json
        or
        not isinstance(
            jogos,
            list
        )
    ):

        return 0


    # --------------------------------------------------------
    # FONTES
    # --------------------------------------------------------

    fontes = {}


    html_dpf = baixar_html(
        URL_DPF
    )


    if html_dpf:

        eventos_dpf = parse_dpf(

            html_dpf,

            data_json
        )


        if eventos_dpf:

            fontes[
                "DPF"
            ] = eventos_dpf


    html_mantos = baixar_html(
        URL_MANTOS
    )


    if html_mantos:

        eventos_mantos = parse_mantos(

            html_mantos,

            data_json
        )


        if eventos_mantos:

            fontes[
                "Mantos"
            ] = eventos_mantos


    # --------------------------------------------------------
    # SE UMA DAS FONTES FALHOU:
    # NAO ALTERA ABSOLUTAMENTE NADA
    # --------------------------------------------------------

    if len(
        fontes
    ) < CONFIRMACOES_MINIMAS:

        print(
            "Nenhuma transmissao atualizada."
        )

        return 0


    # --------------------------------------------------------
    # COMPARAR JOGOS
    # --------------------------------------------------------

    alterados = 0


    for jogo in jogos:

        nova_transmissao = (
            transmissoes_confirmadas(

                jogo,

                fontes
            )
        )


        # Nao encontrou confirmacao segura.
        # Mantem exatamente como estava.
        if not nova_transmissao:

            continue


        transmissao_atual = jogo.get(
            "transmissao",
            []
        )


        if (
            transmissao_atual
            !=
            nova_transmissao
        ):

            jogo[
                "transmissao"
            ] = nova_transmissao

            alterados += 1


    # --------------------------------------------------------
    # NADA MUDOU
    # --------------------------------------------------------

    if alterados == 0:

        print(
            "Nenhuma transmissao atualizada."
        )

        return 0


    # --------------------------------------------------------
    # SALVAR DE FORMA ATOMICA
    # --------------------------------------------------------

    temporario = (
        ARQUIVO_JSON
        +
        ".tmp"
    )


    try:

        with open(

            temporario,

            "w",

            encoding="utf-8"

        ) as arquivo:

            json.dump(

                dados,

                arquivo,

                ensure_ascii=False,

                indent=2
            )

            arquivo.write(
                "\n"
            )


        os.replace(

            temporario,

            ARQUIVO_JSON
        )


    except OSError:

        try:

            if os.path.exists(
                temporario
            ):

                os.remove(
                    temporario
                )

        except OSError:

            pass


        return 0


    print(

        f"Transmissoes atualizadas "
        f"em {alterados} jogo(s)."
    )


    return 0


# ============================================================
# NUNCA QUEBRAR POR CAUSA DAS FONTES EXTERNAS
# ============================================================

if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except Exception:

        # Sem traceback.
        # Sem JSON quebrado.
        # Sem erro para o aplicativo.

        print(
            "Nenhuma transmissao atualizada."
        )

        raise SystemExit(
            0
        )
