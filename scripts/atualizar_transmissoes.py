import json
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# CONFIGURACAO
# ============================================================

ARQUIVO_JSON = "data/jogos-hoje.json"

URL_DPF = "https://doentesporfutebol.com.br/guiadejogos/"
URL_MANTOS = (
    "https://mantosdofutebol.com.br/"
    "guia-de-jogos-tv-hoje-ao-vivo/"
)

TIMEZONE_FONTE = ZoneInfo("America/Sao_Paulo")

# A automacao pode continuar com UMA fonte valida.
# Com apenas uma fonte, o jogo so entra se o match for muito seguro.
FONTES_MINIMAS_PARA_EXECUTAR = 1

# Aceita uma pequena diferenca de horario entre as fontes.
TOLERANCIA_HORARIO_MINUTOS = 45

# Quando existe apenas uma fonte, o primeiro caminho continua exigindo
# horario muito proximo. Se o horario estiver errado na pagina, existe um
# segundo caminho mais conservador: casa + visitante + competicao precisam
# bater EXATAMENTE e formar uma identidade unica naquela fonte.
TOLERANCIA_FONTE_UNICA_MINUTOS = 20

TIMEOUT = 25

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.7,en;q=0.6",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}


# ============================================================
# ALIASES DE TIMES
# ============================================================

ALIASES_TIMES = {
    "atletico": "atletico mg",
    "atletico mg": "atletico mg",
    "atletico mineiro": "atletico mg",
    "clube atletico mineiro": "atletico mg",

    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "bragantino": "bragantino",

    "america mineiro": "america mg",
    "america mg": "america mg",

    "athletico paranaense": "athletico pr",
    "athletico pr": "athletico pr",

    "atletico goianiense": "atletico go",
    "atletico go": "atletico go",

    "sao paulo fc": "sao paulo",
    "gremio fbpa": "gremio",
    "sc internacional": "internacional",
    "ec juventude": "juventude",
    "ec bahia": "bahia",
    "ec vitoria": "vitoria",
    "sport recife": "sport",
    "vasco da gama": "vasco",
    "ceara sc": "ceara",
    "fortaleza ec": "fortaleza",

    "botafogo de sao paulo": "botafogo sp",
    "botafogo sp": "botafogo sp",

    "operario ferroviario": "operario",
    "operario pr": "operario",
    "operario": "operario",

    "nec nijmegen": "nijmegen",
    "nijmegen": "nijmegen",

    "lask linz": "lask",
    "lask": "lask",

    "slovan batislava": "slovan bratislava",
    "slovan bratislava": "slovan bratislava",

    "fc cincinnati": "cincinnati",
    "cincinnati": "cincinnati",

    "new england revolution": "new england revolution",
    "ne revolution": "new england revolution",

    "new york red bulls": "new york red bulls",
    "ny red bulls": "new york red bulls",

    "minnesota united": "minnesota",
    "minnesota": "minnesota",

    "los angeles galaxy": "la galaxy",
    "la galaxy": "la galaxy",

    "san jose earthquakes": "san jose earthquakes",
    "sj earthquakes": "san jose earthquakes",

    "sporting kansas city": "sporting kc",
    "sporting kc": "sporting kc",

    "cf montreal": "montreal",
    "montreal": "montreal",

    "dc united": "dc united",

    "los angeles fc": "los angeles fc",

    # Sul-Americana / Libertadores
    "atletico torque": "montevideo city torque",
    "montevideo city torque": "montevideo city torque",

    "independiente santa fe": "santa fe",
    "santa fe": "santa fe",

    # Saudi Pro League
    "al faisaly": "al faisaly",
    "al faysaly": "al faisaly",

    "al qadisiyah": "al qadsiah",
    "al qadsiah": "al qadsiah",

    "al riyadh": "al riyadh",
    "al nassr": "al nassr",

    "al ittihad": "al ittihad",
    "neom": "neom",

    "al hazm": "al hazm",
    "al diriyah": "al diriyah",

    # A API usa Taawon; o Mantos publica Taawoun.
    "al taawon": "al taawon",
    "al taawoun": "al taawon",

    # A API usa Deportes Tolima; os guias normalmente abreviam para Tolima.
    "deportes tolima": "tolima",
    "tolima": "tolima",

    # Variacoes extras
    "palmeiras sp": "palmeiras",
    "se palmeiras": "palmeiras",
    "cerro porteno": "cerro porteno",
    "cerro porteno fc": "cerro porteno",
    "independiente del valle": "independiente del valle",

    # Variacoes brasileiras importantes
    "america": "america mg",
    "america mg": "america mg",
    "america mineiro": "america mg",

    "athletic": "athletic",
    "athletic club": "athletic",

    # API-Football costuma usar Atletico Paranaense,
    # enquanto os guias usam Athletico / Athletico-PR.
    "atletico paranaense": "athletico pr",
    "athletico paranaense": "athletico pr",
    "athletico pr": "athletico pr",
    "athletico": "athletico pr",

    "botafogo rj": "botafogo",

    # Liga Saudita
    "al hazem": "al hazm",
}


# ============================================================
# CANAIS
# ============================================================

ALIASES_CANAIS = {
    "espn": "espn",
    "espn4": "espn 4",
    "espn 4": "espn 4",

    "sportv": "sportv",
    "sportv 2": "sportv 2",
    "sportv2": "sportv 2",
    "sportv 3": "sportv 3",
    "sportv3": "sportv 3",

    "globo": "globo",

    "ge tv": "ge tv",
    "getv": "ge tv",

    "paramount+": "paramount+",
    "paramount plus": "paramount+",
    "paramont+": "paramount+",
    "paramont plus": "paramount+",

    "disney+": "disney+",
    "disney plus": "disney+",

    "hbo max": "hbo max",
    "max": "hbo max",

    "tnt": "tnt",
    "space": "space",

    "xsports": "xsports",
    "x sports": "xsports",

    "sportynet": "sportynet",
    "sporty net": "sportynet",

    "paulistao": "paulistao",

    "caze tv": "caze tv",
    "cazetv": "caze tv",

    "apple tv": "apple tv",
    "appletv": "apple tv",

    "onefootball": "onefootball",
    "prime video": "prime video",
    "amazon prime video": "prime video",

    # Canais usados na cobertura da Liga Saudita
    "goat": "goat",
    "bandsports": "bandsports",
    "band sports": "bandsports",
    "esporte na band": "esporte na band",
    "sportv hd": "sportv",
    "sportv 2 hd": "sportv 2",
    "globo sp": "globo",
    "globo rj": "globo",

    "premiere": "premiere",
    "premiere clubes": "premiere",

    # typo encontrado no DPF
    "bansports": "bandsports",

    "dazn": "dazn",
    "dazb": "dazn",
    "tv brasil": "tv brasil",
    "globoplay": "globoplay",
    "rede globo": "globo",
    "band": "band",
    "rede bandeirantes": "band",
    "sbt": "sbt",
    "record": "record",
    "record tv": "record",
    "recordtv": "record",
    "nsports": "nsports",
    "n sports": "nsports",
    "fifa+": "fifa+",
    "fifa plus": "fifa+",
}

EXIBICAO_CANAIS = {
    "espn": "ESPN",
    "espn 4": "ESPN 4",
    "sportv": "SporTV",
    "sportv 2": "SporTV 2",
    "sportv 3": "SporTV 3",
    "globo": "Globo",
    "ge tv": "GE TV",
    "paramount+": "Paramount+",
    "disney+": "Disney+",
    "hbo max": "HBO Max",
    "tnt": "TNT",
    "space": "Space",
    "xsports": "XSports",
    "sportynet": "SportyNet",
    "paulistao": "Paulistão",
    "caze tv": "CazéTV",
    "apple tv": "Apple TV",
    "onefootball": "OneFootball",
    "prime video": "Prime Video",
    "goat": "GOAT",
    "bandsports": "BandSports",
    "esporte na band": "Esporte na Band",
    "premiere": "Premiere",
    "dazn": "DAZN",
    "tv brasil": "TV Brasil",
    "youtube": "YouTube",
    "globoplay": "Globoplay",
    "band": "Band",
    "sbt": "SBT",
    "record": "Record",
    "nsports": "NSports",
    "fifa+": "FIFA+",
}

PERFIS_YOUTUBE = {
    "tntsportsbr": "tnt",
    "getv": "ge tv",
    "cazetv": "caze tv",
    "paulistao": "paulistao",
    "sportynetbrasil": "sportynet",

    # GOAT
    "canalgoatbr": "goat",
    "maiscanalgoatbr": "goat",
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
    ).decode("ascii")


def limpar_espacos(texto):
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def normalizar_texto(texto):
    texto = sem_acentos(texto).lower()
    texto = texto.replace("&", " e ")
    texto = re.sub(r"[^a-z0-9+]+", " ", texto)
    return limpar_espacos(texto)


def normalizar_time(nome):
    nome = normalizar_texto(nome)

    # Remove sufixos pouco relevantes apenas quando sao palavras inteiras.
    tokens = [
        token
        for token in nome.split()
        if token not in {"fc", "ec", "sc", "ac"}
    ]
    nome = " ".join(tokens)

    return ALIASES_TIMES.get(nome, nome)


def similaridade_time(a, b):
    a = normalizar_time(a)
    b = normalizar_time(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    return SequenceMatcher(None, a, b).ratio()


def times_batem(a, b):
    return similaridade_time(a, b) >= 0.92


# ============================================================
# COMPETICOES
# ============================================================

def normalizar_competicao(nome):
    nome = normalizar_texto(nome)

    # Erro recorrente encontrado no DPF: "Camponato".
    nome = re.sub(
        r"\bcamponato\b",
        "campeonato",
        nome,
    )

    # Remove detalhes de fase sem mudar a competicao.
    nome = re.sub(
        r"\b("
        r"oitavas de final|oitavas|quartas de final|quartas|"
        r"semifinal|semi final|final|"
        r"ida|volta|qualificacao|qualificatoria|"
        r"of|qf|sf"
        r")\b",
        " ",
        nome
    )

    nome = limpar_espacos(nome)

    # IMPORTANTE:
    # competicoes especificas primeiro.
    # Assim "Brasileirao Serie B" nunca vira Serie A por engano.

    if "serie b" in nome:
        return "serie b"

    if "serie c" in nome:
        return "serie c"

    if "serie d" in nome:
        return "serie d"

    if (
        "serie a" in nome
        or nome == "brasileirao"
        or nome == "campeonato brasileiro"
    ):
        return "serie a"

    if "libertadores" in nome:
        return "libertadores"

    if (
        "sudamericana" in nome
        or "sul americana" in nome
    ):
        return "sudamericana"

    if "copa do brasil" in nome:
        return "copa do brasil"

    if (
        "brasileiro sub 17" in nome
        or "brasileiro u17" in nome
        or "brasileiro u 17" in nome
        or "campeonato brasileiro sub 17" in nome
    ):
        return "brasileiro u17"

    if "copa paulista" in nome:
        return "copa paulista"

    if (
        "pro league" in nome
        or "saudi pro league" in nome
        or "saudi arabia pro league" in nome
        or "liga saudita" in nome
        or "campeonato saudita" in nome
    ):
        return "saudi pro league"

    if "champions league" in nome:
        return "champions league"

    if (
        "la liga" in nome
        or "laliga" in nome
        or "campeonato espanhol" in nome
    ):
        return "la liga"

    if (
        "premier league" in nome
        or "campeonato ingles" in nome
    ):
        return "premier league"

    if (
        "major league soccer" in nome
        or nome == "mls"
    ):
        return "mls"

    if (
        "king s cup" in nome
        or "kings cup" in nome
    ):
        return "kings cup"

    return nome


def competicoes_batem(a, b):
    a = normalizar_competicao(a)
    b = normalizar_competicao(b)

    if not a or not b:
        return False

    if a == b:
        return True

    # Comparacao por tokens para aguentar pequenas mudancas de descricao.
    ta = set(a.split())
    tb = set(b.split())

    if ta and tb:
        inter = len(ta & tb)
        base = min(len(ta), len(tb))

        if base > 0 and inter / base >= 0.75:
            return True

    return SequenceMatcher(None, a, b).ratio() >= 0.84


# ============================================================
# CANAIS
# ============================================================

def normalizar_canal(canal):
    original = limpar_espacos(canal)
    if not original:
        return ""

    texto = sem_acentos(original).lower().strip()

    # URLs/perfis do YouTube.
    match = re.search(
        r"(?:youtube\.com/)?@([a-z0-9_.-]+)",
        texto,
        flags=re.IGNORECASE,
    )

    if match:
        perfil = normalizar_texto(match.group(1))
        if perfil in PERFIS_YOUTUBE:
            return PERFIS_YOUTUBE[perfil]

    texto = texto.replace("www.", "")
    simples = normalizar_texto(texto)

    if texto in ALIASES_CANAIS:
        return ALIASES_CANAIS[texto]

    if simples in ALIASES_CANAIS:
        return ALIASES_CANAIS[simples]

    # Evita gravar lixo muito comprido como se fosse canal.
    if len(simples) > 50:
        return ""

    return simples


def nome_exibicao_canal(chave):
    if chave in EXIBICAO_CANAIS:
        return EXIBICAO_CANAIS[chave]

    return " ".join(
        parte.upper() if len(parte) <= 4 else parte.title()
        for parte in chave.split()
    )


PADRAO_MARCADOR_CANAIS = re.compile(
    r"^(?:📺\s*)?"
    r"(?:canais?|transmiss[aã]o|onde assistir(?:\s+ao vivo)?)\s*:\s*",
    flags=re.IGNORECASE,
)


TERMOS_RUIDO_CANAIS = (
    "horario de brasilia",
    "onde assistir futebol",
    "jogos de hoje",
    "jogos de amanha",
    "jogos de ontem",
    "mais jogos",
    "veja tambem",
    "confira os jogos",
    "clique aqui",
    "saiba mais",
    "assista aqui",
    "segunda feira",
    "terca feira",
    "quarta feira",
    "quinta feira",
    "sexta feira",
    "sabado",
    "domingo",
)


def eh_marcador_canais(texto):
    texto = limpar_espacos(texto)

    return (
        texto.startswith("📺")
        or PADRAO_MARCADOR_CANAIS.match(texto) is not None
    )


def canais_conhecidos_no_texto(texto):
    """
    Encontra mais de um canal mesmo quando o HTML separa os nomes em
    tags, mas o texto visivel chega sem virgula ou ponto e virgula.

    Exemplo recebido do HTML:
        "ESPN Disney+"

    A busca usa limites de palavra e resolve sobreposicoes preferindo
    o alias mais comprido ("SporTV 2" antes de "SporTV").
    """

    texto_n = normalizar_texto(texto)

    if not texto_n:
        return []

    ocorrencias = []

    for alias, chave in ALIASES_CANAIS.items():
        alias_n = normalizar_texto(alias)

        if not alias_n:
            continue

        padrao = re.compile(
            rf"(?<![a-z0-9]){re.escape(alias_n)}(?![a-z0-9])"
        )

        for match in padrao.finditer(texto_n):
            ocorrencias.append(
                (
                    match.start(),
                    match.end(),
                    chave,
                )
            )

    ocorrencias.sort(
        key=lambda item: (
            item[0],
            -(item[1] - item[0]),
        )
    )

    escolhidas = []
    fim_anterior = -1

    for inicio, fim, chave in ocorrencias:
        if inicio < fim_anterior:
            continue

        escolhidas.append(
            (
                inicio,
                chave,
            )
        )
        fim_anterior = fim

    resultado = []

    for _, chave in escolhidas:
        if chave not in resultado:
            resultado.append(chave)

    return resultado


def canal_desconhecido_parece_valido(original, chave):
    """
    Canais novos continuam permitidos quando aparecem dentro de um bloco
    explicitamente marcado como transmissao. Textos de navegacao, datas e
    cabecalhos nunca sao aceitos como nome de canal.
    """

    original = limpar_espacos(original)
    chave = normalizar_texto(chave)

    if not original or not chave:
        return False

    if len(chave) > 50 or len(chave.split()) > 6:
        return False

    if re.search(
        r"\b(?:[0-3]?\d)[/.-](?:[01]?\d)(?:[/.-]\d{2,4})?\b",
        original,
    ):
        return False

    if re.search(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", original):
        return False

    if any(
        termo in chave
        for termo in TERMOS_RUIDO_CANAIS
    ):
        return False

    if re.search(r"\s+[xX×]\s+", original):
        return False

    return True


def dividir_canais(texto):
    texto = limpar_espacos(texto)

    texto = PADRAO_MARCADOR_CANAIS.sub("", texto)

    texto = re.sub(r"^📺\s*", "", texto).strip()

    partes = re.split(
        r"\s*;\s*|\s*,\s*|\s*\|\s*|\s*•\s*|"
        r"\s+/\s+|\s+\be\b\s+",
        texto,
        flags=re.IGNORECASE,
    )

    resultado = []

    for parte in partes:
        conhecidos = canais_conhecidos_no_texto(parte)

        if conhecidos:
            for canal in conhecidos:
                if canal not in resultado:
                    resultado.append(canal)

            continue

        canal = normalizar_canal(parte)

        if (
            canal
            and canal_desconhecido_parece_valido(
                parte,
                canal,
            )
            and canal not in resultado
        ):
            resultado.append(canal)

    return resultado


def extrair_canais_de_bloco(
    bloco,
    indice_marcador,
    limite_tokens=6,
):
    """
    Le o marcador de TV e tambem os tokens imediatamente seguintes.

    Isso cobre tanto:
        "📺 ESPN; Disney+"

    quanto HTML fragmentado:
        "📺"
        "ESPN"
        "Disney+"
    """

    resultado = []
    fim = min(
        len(bloco),
        indice_marcador + limite_tokens,
    )

    for indice in range(indice_marcador, fim):
        token = limpar_espacos(bloco[indice])

        if not token:
            continue

        if indice > indice_marcador:
            if eh_marcador_canais(token):
                break

            if token_parece_inicio_evento(token):
                break

            if separar_times(token):
                break

            if data_mencionada_na_linha(token) is not None:
                break

        canais = dividir_canais(token)

        if canais:
            for canal in canais:
                if canal not in resultado:
                    resultado.append(canal)

            continue

        if resultado:
            break

    return resultado


# ============================================================
# DOWNLOAD
# ============================================================

def criar_sessao():
    sessao = requests.Session()

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )

    sessao.mount(
        "https://",
        HTTPAdapter(max_retries=retry)
    )

    return sessao


def baixar_html(sessao, nome_fonte, url):
    headers = dict(HEADERS_BASE)

    parsed = urlparse(url)
    headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

    try:
        resposta = sessao.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as erro:
        print(
            f"[{nome_fonte}] download: FALHOU "
            f"({erro.__class__.__name__})"
        )
        return None

    tamanho = len(resposta.text or "")
    tipo = resposta.headers.get("Content-Type", "").lower()

    print(
        f"[{nome_fonte}] HTTP {resposta.status_code} "
        f"- {tamanho} caracteres"
    )

    if resposta.status_code != 200:
        return None

    texto = resposta.text or ""

    # Alguns servidores enviam Content-Type impreciso.
    # Aceitamos se o corpo claramente parecer HTML.
    parece_html = (
        "html" in tipo
        or "<html" in texto.lower()
        or "<!doctype" in texto.lower()
    )

    if not parece_html or tamanho < 1000:
        return None

    return texto


# ============================================================
# TEXTO E DATA DA PAGINA
# ============================================================

def linhas_da_pagina(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    linhas = []

    for linha in soup.get_text("\n").splitlines():
        linha = limpar_espacos(
            linha.replace("\xa0", " ")
        )

        if linha:
            linhas.append(linha)

    return linhas


MESES_PORTUGUES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def data_mencionada_na_linha(
    texto,
    ano_referencia=None,
):
    """Extrai uma data explicita de uma linha curta de cabecalho."""

    texto = limpar_espacos(texto)

    if not texto or len(texto) > 100:
        return None

    if ano_referencia is None:
        ano_referencia = datetime.now().year

    match = re.search(
        r"(?<!\d)([0-3]?\d)[/.-]([01]?\d)"
        r"(?:[/.-](\d{2,4}))?(?!\d)",
        texto,
    )

    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        ano_texto = match.group(3)

        if ano_texto:
            ano = int(ano_texto)
            if ano < 100:
                ano += 2000
        else:
            ano = int(ano_referencia)

        try:
            return datetime(
                ano,
                mes,
                dia,
            ).date()
        except ValueError:
            return None

    texto_n = normalizar_texto(texto)

    match = re.search(
        r"\b([0-3]?\d)\s+de\s+([a-z]+)"
        r"(?:\s+de\s+(\d{4}))?\b",
        texto_n,
    )

    if not match:
        return None

    mes = MESES_PORTUGUES.get(
        match.group(2)
    )

    if mes is None:
        return None

    dia = int(match.group(1))
    ano = int(
        match.group(3)
        or ano_referencia
    )

    try:
        return datetime(
            ano,
            mes,
            dia,
        ).date()
    except ValueError:
        return None


def recortar_itens_da_data(
    itens,
    data_json,
):
    """
    Isola apenas o trecho da data do JSON quando uma fonte publica varios
    dias na mesma pagina. Se nao houver marcadores de data confiaveis, o
    conteudo original e mantido e as demais validacoes continuam valendo.
    """

    try:
        data_alvo = datetime.strptime(
            data_json,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        return []

    marcadores = []

    for indice, item in enumerate(itens):
        data_item = data_mencionada_na_linha(
            item,
            data_alvo.year,
        )

        if data_item is not None:
            marcadores.append(
                (
                    indice,
                    data_item,
                )
            )

    inicios = [
        indice
        for indice, data_item in marcadores
        if data_item == data_alvo
    ]

    if not inicios:
        return list(itens)

    inicio = inicios[0] + 1
    fim = len(itens)

    for indice, data_item in marcadores:
        if indice < inicio:
            continue

        if data_item != data_alvo:
            fim = indice
            break

    return list(
        itens[inicio:fim]
    )


def pagina_parece_ser_do_dia(linhas, data_json):
    try:
        data = datetime.strptime(data_json, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False

    # A data principal deve aparecer perto do inicio do conteudo.
    for linha in linhas[:160]:
        data_linha = data_mencionada_na_linha(
            linha,
            data.year,
        )

        if data_linha == data.date():
            return True

    cabecalho = " ".join(linhas[:120])
    cabecalho_compacto = re.sub(r"\s+", "", cabecalho)

    data_curta = f"{data.day:02d}/{data.month:02d}"
    data_curta_sem_zero = f"{data.day}/{data.month}"
    data_completa = f"{data.day:02d}/{data.month:02d}/{data.year}"

    return (
        data_completa in cabecalho_compacto
        or data_curta in cabecalho_compacto
        or data_curta_sem_zero in cabecalho_compacto
    )


# ============================================================
# FUNCOES DE PARSER
# ============================================================

def separar_times(texto):
    partes = re.split(
        r"\s+[xX×]\s+",
        limpar_espacos(texto),
        maxsplit=1,
    )

    if len(partes) != 2:
        return None

    casa = limpar_espacos(partes[0])
    fora = limpar_espacos(partes[1])

    if not casa or not fora:
        return None

    # Protecao contra capturar linhas enormes que nao sao partidas.
    if len(casa) > 80 or len(fora) > 80:
        return None

    return casa, fora


def minutos_do_dia(hora, minuto):
    return int(hora) * 60 + int(minuto)


def tokens_da_pagina(html):
    """
    Retorna os textos visiveis preservando melhor os blocos do HTML.

    O DPF pode separar no HTML:
        🕗
        19:00
        Copa Sul-Americana
        Atletico x Red Bull Bragantino
        📺
        ESPN

    ou pode juntar alguns desses itens na mesma tag.

    Por isso nao dependemos de classe CSS nem de uma estrutura HTML exata.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    tokens = []

    for item in soup.stripped_strings:
        for pedaco in str(item).splitlines():
            pedaco = limpar_espacos(
                pedaco.replace("\xa0", " ")
            )

            if pedaco:
                tokens.append(pedaco)

    return tokens


def token_tem_horario(token):
    return re.search(
        r"\b([01]?\d|2[0-3]):([0-5]\d)\b",
        token
    ) is not None


def token_parece_inicio_evento(token):
    """
    O DPF normalmente usa o relogio antes de cada jogo.
    Tambem aceitamos um token que contenha horario + texto, caso
    o emoji seja removido ou separado por alguma mudanca pequena.
    """
    token = limpar_espacos(token)

    if "🕗" in token:
        return True

    return bool(
        re.match(
            r"^([01]?\d|2[0-3]):([0-5]\d)\b",
            token
        )
    )


def extrair_horario_e_competicao(bloco):
    """
    Procura o horario e tenta obter o campeonato sem depender
    de o horario e a competicao estarem na mesma tag.
    """
    hora = None
    minuto = None
    indice_horario = None
    competicao_na_mesma_linha = ""

    for i, token in enumerate(bloco):
        resultado = re.search(
            r"\b([01]?\d|2[0-3]):([0-5]\d)\b",
            token
        )

        if not resultado:
            continue

        hora = resultado.group(1)
        minuto = resultado.group(2)
        indice_horario = i

        resto = limpar_espacos(
            token[resultado.end():]
        )

        resto = re.sub(
            r"^[\s\-–—:|]+",
            "",
            resto
        ).strip()

        if resto:
            competicao_na_mesma_linha = resto

        break

    if hora is None:
        return None

    return {
        "hora": hora,
        "minuto": minuto,
        "indice_horario": indice_horario,
        "competicao_mesma_linha": competicao_na_mesma_linha,
    }


def chave_evento_fonte(evento):
    return (
        evento.get("hora"),
        normalizar_time(
            evento.get("casa", "")
        ),
        normalizar_time(
            evento.get("fora", "")
        ),
        normalizar_competicao(
            evento.get("competicao", "")
        ),
    )


def consolidar_eventos(eventos):
    """
    Une copias identicas do mesmo evento publicadas no HTML desktop/mobile.

    Antes, o DPF descartava a segunda copia e podia perder canais; no Mantos,
    duas copias iguais podiam ser tratadas como candidatos ambiguos. Agora os
    canais sao unidos somente quando horario, times e competicao coincidem.
    """

    consolidados = {}

    for evento in eventos:
        chave = chave_evento_fonte(evento)

        if (
            chave[0] is None
            or not chave[1]
            or not chave[2]
            or not chave[3]
        ):
            continue

        if chave not in consolidados:
            copia = dict(evento)
            copia["canais"] = list(
                dict.fromkeys(
                    evento.get(
                        "canais",
                        [],
                    )
                )
            )
            consolidados[chave] = copia
            continue

        destino = consolidados[chave]

        for canal in evento.get(
            "canais",
            [],
        ):
            if canal not in destino["canais"]:
                destino["canais"].append(canal)

    return list(
        consolidados.values()
    )


def parse_dpf(html, data_json):
    """
    Parser tolerante do Doentes por Futebol.

    Nao depende de classes CSS.
    Aceita tanto HTML em que os dados estejam juntos quanto HTML
    em que icone, horario, campeonato, jogo e canal estejam em tags
    separadas.

    Se nao for possivel identificar com seguranca:
        simplesmente nao retorna aquele evento.
    """
    linhas = linhas_da_pagina(html)

    if not pagina_parece_ser_do_dia(linhas, data_json):
        print("[DPF] data da pagina nao foi confirmada.")
        return []

    tokens = recortar_itens_da_data(
        tokens_da_pagina(html),
        data_json,
    )

    # Localiza todos os possiveis inicios de evento.
    inicios = []

    for i, token in enumerate(tokens):
        if token_parece_inicio_evento(token):
            # Se o token for apenas o emoji, o horario deve aparecer
            # logo depois. Isso evita interpretar icones soltos.
            if token.strip() == "🕗":
                janela = tokens[i + 1:i + 4]

                if not any(
                    token_tem_horario(item)
                    for item in janela
                ):
                    continue

            inicios.append(i)

    eventos = []

    for posicao, inicio_bloco in enumerate(inicios):
        fim_bloco = (
            inicios[posicao + 1]
            if posicao + 1 < len(inicios)
            else min(
                len(tokens),
                inicio_bloco + 18
            )
        )

        bloco = tokens[
            inicio_bloco:fim_bloco
        ]

        dados_horario = extrair_horario_e_competicao(
            bloco
        )

        if not dados_horario:
            continue

        hora = dados_horario["hora"]
        minuto = dados_horario["minuto"]
        indice_horario = dados_horario["indice_horario"]

        # --------------------------------------------------------
        # LOCALIZAR A LINHA DOS TIMES
        # --------------------------------------------------------

        indice_times = None
        times = None

        for i in range(
            indice_horario,
            len(bloco)
        ):
            tentativa = separar_times(
                bloco[i]
            )

            if tentativa:
                indice_times = i
                times = tentativa
                break

        if not times:
            continue

        # --------------------------------------------------------
        # COMPETICAO
        # --------------------------------------------------------

        competicao = dados_horario[
            "competicao_mesma_linha"
        ]

        if not competicao:
            candidatos_competicao = []

            for token in bloco[
                indice_horario + 1:
                indice_times
            ]:
                token_limpo = limpar_espacos(
                    token.replace("🕗", "")
                )

                if (
                    token_limpo
                    and not token_tem_horario(
                        token_limpo
                    )
                    and "📺" not in token_limpo
                ):
                    candidatos_competicao.append(
                        token_limpo
                    )

            # Em geral existe exatamente um token entre horario e jogo.
            # Se houver mais, juntamos apenas os pequenos fragmentos
            # imediatamente anteriores ao nome dos times.
            if candidatos_competicao:
                competicao = limpar_espacos(
                    " ".join(
                        candidatos_competicao[-3:]
                    )
                )

        if not competicao:
            continue

        # --------------------------------------------------------
        # CANAIS
        # --------------------------------------------------------

        canais = None

        for i in range(
            indice_times + 1,
            len(bloco)
        ):
            token = bloco[i]

            eh_linha_tv = eh_marcador_canais(
                token
            )

            if not eh_linha_tv:
                continue

            tentativa = extrair_canais_de_bloco(
                bloco,
                i,
            )

            if tentativa:
                canais = tentativa
                break

        if not canais:
            continue

        evento = {
            "hora": minutos_do_dia(
                hora,
                minuto
            ),
            "casa": times[0],
            "fora": times[1],
            "competicao": competicao,
            "canais": canais,
        }

        eventos.append(evento)

    return consolidar_eventos(
        eventos
    )

def parse_mantos(html, data_json):
    linhas = linhas_da_pagina(html)

    if not pagina_parece_ser_do_dia(linhas, data_json):
        print("[Mantos] data da pagina nao foi confirmada.")
        return []

    eventos = []

    # Aceita 19h00, 19:00 e varios tipos de traco.
    # Separador entre campos:
    # - en dash/em dash podem vir sem espaco;
    # - hifen ASCII so vale como separador se houver espacos.
    #
    # Isso evita o bug que cortava:
    #   Athletico-PR
    #   Al-Hazem
    #   Atletico-MG
    separador = r"(?:\s*[–—]\s*|\s+-\s+)"

    padrao_evento = re.compile(
        rf"^(\d{{1,2}})(?:h|:)(\d{{2}}){separador}"
        rf"(.+?)\s+[xX×]\s+"
        rf"(.+?){separador}(.+?)$",
        flags=re.IGNORECASE,
    )

    padrao_inicio_horario = re.compile(
        r"^(\d{1,2})(?:h|:)(\d{2})\b",
        flags=re.IGNORECASE,
    )

    indices_eventos = []
    indice = 0

    while indice < len(linhas):
        linha = linhas[indice]

        if not padrao_inicio_horario.match(linha):
            indice += 1
            continue

        match = None
        fim_cabecalho = indice

        # O WordPress pode quebrar horario, times e competicao em tags
        # separadas. Juntamos uma janela pequena e paramos assim que o
        # cabecalho completo for reconhecido.
        for fim_tentativa in range(
            indice,
            min(len(linhas), indice + 6),
        ):
            if (
                fim_tentativa > indice
                and eh_marcador_canais(
                    linhas[fim_tentativa]
                )
            ):
                break

            if (
                fim_tentativa > indice
                and padrao_inicio_horario.match(
                    linhas[fim_tentativa]
                )
            ):
                break

            candidato = limpar_espacos(
                " ".join(
                    linhas[
                        indice:fim_tentativa + 1
                    ]
                )
            )

            tentativa = padrao_evento.match(
                candidato
            )

            if tentativa:
                match = tentativa
                fim_cabecalho = fim_tentativa
                break

        if not match:
            indice += 1
            continue

        hora, minuto, casa, fora, competicao = match.groups()

        if int(hora) > 23 or int(minuto) > 59:
            indice += 1
            continue

        indices_eventos.append(
            {
                "inicio": indice,
                "fim_cabecalho": fim_cabecalho,
                "hora": hora,
                "minuto": minuto,
                "casa": limpar_espacos(casa),
                "fora": limpar_espacos(fora),
                "competicao": limpar_espacos(competicao),
            }
        )

        indice = fim_cabecalho + 1

    for posicao, evento in enumerate(indices_eventos):
        fim = (
            indices_eventos[posicao + 1]["inicio"]
            if posicao + 1 < len(indices_eventos)
            else min(
                len(linhas),
                evento["fim_cabecalho"] + 12,
            )
        )

        bloco = linhas[
            evento["fim_cabecalho"] + 1:fim
        ]

        canais = None

        for indice_bloco, linha in enumerate(bloco):
            if not eh_marcador_canais(linha):
                continue

            tentativa = extrair_canais_de_bloco(
                bloco,
                indice_bloco,
            )

            if tentativa:
                canais = tentativa
                break

        if canais:
            eventos.append(
                {
                    "hora": minutos_do_dia(
                        evento["hora"],
                        evento["minuto"],
                    ),
                    "casa": evento["casa"],
                    "fora": evento["fora"],
                    "competicao": evento["competicao"],
                    "canais": canais,
                }
            )

    return consolidar_eventos(
        eventos
    )


# ============================================================
# HORARIO DO JSON -> BRASILIA
# ============================================================

def horario_brasilia_do_jogo(jogo):
    timestamp = jogo.get("timestamp")

    if not isinstance(timestamp, (int, float)):
        return None

    try:
        data = datetime.fromtimestamp(
            timestamp,
            tz=ZoneInfo("UTC"),
        ).astimezone(TIMEZONE_FONTE)

        return data.hour * 60 + data.minute

    except (OverflowError, OSError, ValueError):
        return None


def diferenca_minutos(a, b):
    diferenca = abs(a - b)
    return min(diferenca, 1440 - diferenca)


# ============================================================
# MATCH DE JOGOS
# ============================================================

def encontrar_evento(jogo, eventos):
    casa = jogo.get("casa", {}).get("nome", "")
    fora = jogo.get("fora", {}).get("nome", "")
    competicao = jogo.get("campeonato", {}).get("nome", "")
    hora = horario_brasilia_do_jogo(jogo)

    if not casa or not fora or not competicao or hora is None:
        return None

    candidatos = []

    for evento in consolidar_eventos(
        eventos
    ):
        if diferenca_minutos(hora, evento["hora"]) > TOLERANCIA_HORARIO_MINUTOS:
            continue

        if not times_batem(casa, evento["casa"]):
            continue

        if not times_batem(fora, evento["fora"]):
            continue

        if not competicoes_batem(competicao, evento["competicao"]):
            continue

        score = (
            similaridade_time(casa, evento["casa"])
            + similaridade_time(fora, evento["fora"])
        )

        candidatos.append((score, evento))

    # Se houver mais de um candidato, so aceita se o melhor
    # estiver claramente acima do segundo.
    if not candidatos:
        return None

    candidatos.sort(key=lambda item: item[0], reverse=True)

    if len(candidatos) > 1:
        diferenca_score = candidatos[0][0] - candidatos[1][0]

        if diferenca_score < 0.08:
            return None

    return candidatos[0][1]


# ============================================================
# MATCH EXATO SEM HORARIO
# ============================================================

def encontrar_evento_exato_sem_horario(
    jogo,
    eventos
):
    """
    Fallback de identidade usado quando uma fonte publicou horario errado.

    Serve para casos em que uma fonte publicou horario incorreto,
    mas time da casa + visitante + competicao batem exatamente.

    Regras:
      - casa exata apos normalizacao/aliases;
      - visitante exato;
      - competicao exata;
      - precisa existir exatamente UM candidato na fonte.

    Com fonte unica, so e aceito depois de confirmar que o candidato e unico.
    """

    casa = normalizar_time(
        jogo.get(
            "casa",
            {}
        ).get(
            "nome",
            ""
        )
    )

    fora = normalizar_time(
        jogo.get(
            "fora",
            {}
        ).get(
            "nome",
            ""
        )
    )

    competicao = normalizar_competicao(
        jogo.get(
            "campeonato",
            {}
        ).get(
            "nome",
            ""
        )
    )

    if not casa or not fora or not competicao:
        return None

    candidatos = []

    for evento in consolidar_eventos(
        eventos
    ):

        if normalizar_time(
            evento.get(
                "casa",
                ""
            )
        ) != casa:
            continue

        if normalizar_time(
            evento.get(
                "fora",
                ""
            )
        ) != fora:
            continue

        if normalizar_competicao(
            evento.get(
                "competicao",
                ""
            )
        ) != competicao:
            continue

        candidatos.append(
            evento
        )

    if len(candidatos) != 1:
        return None

    return candidatos[0]


# ============================================================
# CONFIRMACAO ENTRE AS DUAS FONTES
# ============================================================

def evento_bate_estritamente(jogo, evento):
    """
    Fallback seguro para quando apenas UMA das duas fontes lista o jogo.

    So aceitamos fonte unica quando:
      - time da casa bate exatamente apos aliases/normalizacao;
      - visitante bate exatamente apos aliases/normalizacao;
      - competicao bate exatamente apos normalizacao;
      - horario difere no maximo 20 minutos.

    Isso permite aproveitar uma transmissao real que exista apenas
    no DPF ou apenas no Mantos sem aceitar correspondencias vagas.
    """

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
        or not fora
        or not competicao
        or hora is None
    ):
        return False

    if diferenca_minutos(
        hora,
        evento.get(
            "hora",
            -9999
        )
    ) > TOLERANCIA_FONTE_UNICA_MINUTOS:
        return False

    if normalizar_time(
        casa
    ) != normalizar_time(
        evento.get(
            "casa",
            ""
        )
    ):
        return False

    if normalizar_time(
        fora
    ) != normalizar_time(
        evento.get(
            "fora",
            ""
        )
    ):
        return False

    if normalizar_competicao(
        competicao
    ) != normalizar_competicao(
        evento.get(
            "competicao",
            ""
        )
    ):
        return False

    canais = evento.get(
        "canais"
    )

    if not isinstance(
        canais,
        list
    ) or not canais:
        return False

    return True


def evento_bate_com_variacao_segura(jogo, evento):
    """
    Aceita uma pequena grafia diferente em apenas UM dos times.

    Esta regra existe para casos como Taawon/Taawoun. Para evitar falso
    positivo, exige simultaneamente:
      - horario dentro da tolerancia estrita de fonte unica;
      - competicao exatamente igual apos normalizacao;
      - um dos times exatamente igual;
      - o outro time com similaridade minima de 92%;
      - lista de canais valida.

    O candidato ja passou pela verificacao de ambiguidade de
    encontrar_evento antes de chegar aqui.
    """

    casa = jogo.get(
        "casa",
        {},
    ).get(
        "nome",
        "",
    )

    fora = jogo.get(
        "fora",
        {},
    ).get(
        "nome",
        "",
    )

    competicao = jogo.get(
        "campeonato",
        {},
    ).get(
        "nome",
        "",
    )

    hora = horario_brasilia_do_jogo(
        jogo
    )

    if (
        not casa
        or not fora
        or not competicao
        or hora is None
    ):
        return False

    if diferenca_minutos(
        hora,
        evento.get(
            "hora",
            -9999,
        ),
    ) > TOLERANCIA_FONTE_UNICA_MINUTOS:
        return False

    if normalizar_competicao(
        competicao
    ) != normalizar_competicao(
        evento.get(
            "competicao",
            "",
        )
    ):
        return False

    similaridade_casa = similaridade_time(
        casa,
        evento.get(
            "casa",
            "",
        ),
    )

    similaridade_fora = similaridade_time(
        fora,
        evento.get(
            "fora",
            "",
        ),
    )

    if min(
        similaridade_casa,
        similaridade_fora,
    ) < 0.92:
        return False

    if max(
        similaridade_casa,
        similaridade_fora,
    ) < 1.0:
        return False

    canais = evento.get(
        "canais"
    )

    return (
        isinstance(
            canais,
            list,
        )
        and bool(canais)
    )


def montar_transmissao(
    canais,
    fonte
):
    resultado = []

    for canal in sorted(
        set(
            canais
        )
    ):

        if not canal:
            continue

        resultado.append(
            {
                "canal":
                    nome_exibicao_canal(
                        canal
                    ),

                "fonte":
                    fonte,
            }
        )

    return resultado


def confirmar_transmissao(jogo, fontes):
    """
    Versao 9 - parser resiliente, aliases robustos e protecao contra falso positivo.

    REGRA A - jogo encontrado nas DUAS fontes:
      - usamos a UNIAO dos canais.
      - se um canal aparece nas duas, fonte = "DPF + Mantos".
      - se aparece so em uma, guardamos a fonte correspondente.

    REGRA B - horario diverge em uma fonte:
      - tentamos casar por times + competicao EXATOS.
      - isso so vale quando as DUAS fontes reconhecem o mesmo jogo.
      - se os horarios divergem, exigimos pelo menos UM canal em comum
        antes de aceitar a uniao.

    REGRA C - apenas UMA fonte possui o jogo:
      - primeiro exigimos times + competicao exatos e horario proximo;
      - se a fonte errou o horario, aceitamos somente uma identidade unica
        de casa + visitante + competicao, todos exatos apos normalizacao.
    """

    encontrados = {}

    # Match normal com horario.
    for nome_fonte, eventos in fontes.items():

        evento = encontrar_evento(
            jogo,
            eventos
        )

        if evento:

            encontrados[
                nome_fonte
            ] = evento


    # Fallback exato sem horario.
    if len(encontrados) < len(fontes):

        for nome_fonte, eventos in fontes.items():

            if nome_fonte in encontrados:
                continue

            evento = encontrar_evento_exato_sem_horario(
                jogo,
                eventos
            )

            if evento:

                encontrados[
                    nome_fonte
                ] = evento


    if not encontrados:

        return {
            "status":
                "insuficiente",

            "transmissao":
                None,

            "fontes":
                encontrados,
        }


    # Apenas uma fonte -> regra estrita com horario.
    if len(
        encontrados
    ) == 1:

        nome_fonte, evento = next(
            iter(
                encontrados.items()
            )
        )

        fonte_unica_segura = evento_bate_estritamente(
            jogo,
            evento
        )

        if not fonte_unica_segura:
            fonte_unica_segura = evento_bate_com_variacao_segura(
                jogo,
                evento,
            )

        if not fonte_unica_segura:

            # A pagina pode publicar o horario errado. Para nao perder um
            # canal correto, aceitamos sem horario apenas quando existe UM
            # unico evento com casa + visitante + competicao exatos.
            evento_exato = encontrar_evento_exato_sem_horario(
                jogo,
                fontes.get(
                    nome_fonte,
                    [],
                ),
            )

            if evento_exato is not None:
                evento = evento_exato
                encontrados[nome_fonte] = evento

                fonte_unica_segura = True

        if not fonte_unica_segura:

            return {
                "status":
                    "insuficiente",

                "transmissao":
                    None,

                "fontes":
                    encontrados,
            }

        transmissao = montar_transmissao(
            evento.get(
                "canais",
                []
            ),
            nome_fonte
        )

        if not transmissao:

            return {
                "status":
                    "insuficiente",

                "transmissao":
                    None,

                "fontes":
                    encontrados,
            }

        return {
            "status":
                "confirmado_fonte_unica",

            "transmissao":
                transmissao,

            "fontes":
                encontrados,
        }


    # Duas fontes.
    canais_por_fonte = {}

    for nome_fonte, evento in encontrados.items():

        canais_por_fonte[
            nome_fonte
        ] = set(
            evento.get(
                "canais",
                []
            )
        )


    nomes_fontes = list(
        canais_por_fonte.keys()
    )

    primeira = canais_por_fonte[
        nomes_fontes[0]
    ]

    segunda = canais_por_fonte[
        nomes_fontes[1]
    ]

    comuns = (
        primeira
        &
        segunda
    )


    # Verifica se alguma fonte divergiu bastante do horario do JSON.
    horario_json = horario_brasilia_do_jogo(
        jogo
    )

    horarios_divergentes = False

    if horario_json is not None:

        for evento in encontrados.values():

            if diferenca_minutos(
                horario_json,
                evento.get(
                    "hora",
                    horario_json
                )
            ) > TOLERANCIA_HORARIO_MINUTOS:

                horarios_divergentes = True
                break


    # Se houve divergencia forte de horario, so aceita se as fontes
    # concordarem em pelo menos um canal.
    if (
        horarios_divergentes
        and
        not comuns
    ):

        return {
            "status":
                "conflito",

            "transmissao":
                [],

            "fontes":
                encontrados,
        }


    # Uniao dos canais.
    todos_canais = sorted(
        set().union(
            *canais_por_fonte.values()
        )
    )

    transmissao = []

    for canal in todos_canais:

        fontes_canal = [

            nome_fonte

            for nome_fonte, canais
            in canais_por_fonte.items()

            if canal in canais
        ]


        if len(
            fontes_canal
        ) >= 2:

            fonte_canal = "DPF + Mantos"

        else:

            fonte_canal = fontes_canal[
                0
            ]


        transmissao.append(
            {
                "canal":
                    nome_exibicao_canal(
                        canal
                    ),

                "fonte":
                    fonte_canal,
            }
        )


    if not transmissao:

        return {
            "status":
                "conflito",

            "transmissao":
                [],

            "fontes":
                encontrados,
        }


    return {
        "status":
            "confirmado",

        "transmissao":
            transmissao,

        "fontes":
            encontrados,
    }


# ============================================================
# LOG
# ============================================================

def nome_jogo(jogo):
    casa = jogo.get("casa", {}).get("nome", "?")
    fora = jogo.get("fora", {}).get("nome", "?")
    return f"{casa} x {fora}"


# ============================================================
# SALVAR
# ============================================================

def salvar_atomico(dados):
    temporario = ARQUIVO_JSON + ".tmp"

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
                indent=2,
            )
            arquivo.write("\n")

        os.replace(
            temporario,
            ARQUIVO_JSON
        )

        return True

    except OSError:
        try:
            if os.path.exists(temporario):
                os.remove(temporario)
        except OSError:
            pass

        return False


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=== LUBU - Atualizacao de transmissoes v9 ===")

    try:
        with open(
            ARQUIVO_JSON,
            "r",
            encoding="utf-8",
        ) as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        print("[JSON] Nao foi possivel ler o arquivo. Nada alterado.")
        return 0

    data_json = dados.get("data")
    jogos = dados.get("jogos")

    if not data_json or not isinstance(jogos, list):
        print("[JSON] Estrutura inesperada. Nada alterado.")
        return 0

    print(f"[JSON] Data: {data_json}")
    print(f"[JSON] Jogos: {len(jogos)}")

    sessao = criar_sessao()
    fontes = {}

    html_dpf = baixar_html(
        sessao,
        "DPF",
        URL_DPF,
    )

    if html_dpf:
        try:
            eventos_dpf = parse_dpf(
                html_dpf,
                data_json,
            )
        except Exception as erro:
            print(
                "[DPF] parser: FALHOU "
                f"({erro.__class__.__name__})"
            )
            eventos_dpf = []

        print(f"[DPF] eventos validos: {len(eventos_dpf)}")

        if eventos_dpf:
            fontes["DPF"] = eventos_dpf

    html_mantos = baixar_html(
        sessao,
        "Mantos",
        URL_MANTOS,
    )

    if html_mantos:
        try:
            eventos_mantos = parse_mantos(
                html_mantos,
                data_json,
            )
        except Exception as erro:
            print(
                "[Mantos] parser: FALHOU "
                f"({erro.__class__.__name__})"
            )
            eventos_mantos = []

        print(f"[Mantos] eventos validos: {len(eventos_mantos)}")

        if eventos_mantos:
            fontes["Mantos"] = eventos_mantos

    # Se nenhuma fonte estiver valida, nao toca no JSON.
    if len(fontes) < FONTES_MINIMAS_PARA_EXECUTAR:
        print(
            "[SEGURANCA] Nenhuma fonte valida. "
            "Nenhuma transmissao foi alterada."
        )
        return 0

    if len(fontes) == 1:
        print(
            "[AVISO] Apenas uma fonte valida nesta execucao. "
            "Sera usado somente o match estrito."
        )

    alterados = 0
    confirmados_duas_fontes = 0
    confirmados_fonte_unica = 0
    conflitos = 0
    insuficientes = 0
    limpos_por_conflito = 0

    for jogo in jogos:
        resultado = confirmar_transmissao(
            jogo,
            fontes,
        )

        status = resultado["status"]

        if status == "insuficiente":
            insuficientes += 1

            print(
                f"[SEM-MATCH] {nome_jogo(jogo)} "
                f"| {jogo.get('campeonato', {}).get('nome', '?')} "
                f"| Brasilia={horario_brasilia_do_jogo(jogo)}min"
            )

            continue

        if status == "conflito":
            conflitos += 1

            # As duas fontes encontraram o MESMO jogo de forma segura,
            # mas nao concordaram em nenhum canal.
            # Nesse caso, removemos uma transmissao antiga para nao
            # exibir um canal que deixou de estar confirmado.
            atual = jogo.get("transmissao", [])

            if atual:
                jogo["transmissao"] = []
                alterados += 1
                limpos_por_conflito += 1

                print(
                    f"[CONFLITO] {nome_jogo(jogo)} "
                    "- transmissao antiga removida."
                )

            continue

        nova_transmissao = resultado["transmissao"]

        atual = jogo.get("transmissao", [])

        if atual != nova_transmissao:
            jogo["transmissao"] = nova_transmissao
            alterados += 1

        canais_log = ", ".join(
            item["canal"]
            for item in nova_transmissao
        )

        if status == "confirmado_fonte_unica":

            confirmados_fonte_unica += 1

            fonte_log = nova_transmissao[
                0
            ].get(
                "fonte",
                "fonte unica"
            )

            print(
                f"[OK-FONTE-UNICA] {nome_jogo(jogo)} "
                f"-> {canais_log} ({fonte_log})"
            )

        else:

            confirmados_duas_fontes += 1

            print(
                f"[OK] {nome_jogo(jogo)} -> {canais_log}"
            )

    print("")
    print("=== RESUMO ===")
    print(
        "Confirmados nas duas fontes: "
        f"{confirmados_duas_fontes}"
    )
    print(
        "Confirmados por fonte unica: "
        f"{confirmados_fonte_unica}"
    )
    print(f"Conflitos entre fontes: {conflitos}")
    print(f"Sem confirmacao dupla: {insuficientes}")
    print(f"Campos alterados: {alterados}")

    if limpos_por_conflito:
        print(
            "Transmissoes antigas removidas por conflito: "
            f"{limpos_por_conflito}"
        )

    if alterados == 0:
        print("Nenhuma mudanca no JSON.")
        return 0

    if not salvar_atomico(dados):
        print(
            "[JSON] Falha ao salvar. "
            "Arquivo original mantido."
        )
        return 0

    print("JSON atualizado com seguranca.")
    return 0


# ============================================================
# PROTECAO FINAL
# ============================================================

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as erro:
        # O app nunca recebe erro nem JSON parcial.
        # O log do GitHub mostra apenas o tipo geral para diagnostico.
        print(
            "[SEGURANCA] Execucao interrompida sem alterar o JSON "
            f"({erro.__class__.__name__})."
        )
        raise SystemExit(0)
