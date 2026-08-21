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

# Canal so entra se for confirmado nas duas fontes.
CONFIRMACOES_MINIMAS = 2

# Aceita uma pequena diferenca de horario entre as fontes.
TOLERANCIA_HORARIO_MINUTOS = 15

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

    # Remove detalhes que normalmente aparecem so em uma das fontes.
    nome = re.sub(r"\([^)]*\)", " ", nome)
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

    regras = (
        (("sudamericana", "sul americana"), "sudamericana"),
        (("libertadores",), "libertadores"),
        (
            (
                "brasileirao serie b",
                "brasileiro serie b",
                "campeonato brasileiro serie b",
                "serie b",
            ),
            "serie b",
        ),
        (
            (
                "brasileiro sub 17",
                "brasileiro u17",
                "brasileiro u 17",
                "campeonato brasileiro sub 17",
                "campeonato brasileiro u17",
            ),
            "brasileiro u17",
        ),
        (("copa paulista",), "copa paulista"),
        (("champions league",), "champions league"),
        (("la liga", "laliga", "campeonato espanhol"), "la liga"),
        (("major league soccer", "mls"), "mls"),
        (("king s cup", "kings cup"), "kings cup"),

        (
            (
                "pro league",
                "saudi pro league",
                "liga saudita",
                "campeonato saudita",
            ),
            "saudi pro league",
        ),
    )

    for termos, canonico in regras:
        if any(termo in nome for termo in termos):
            return canonico

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


def dividir_canais(texto):
    texto = limpar_espacos(texto)

    texto = re.sub(
        r"^(?:📺\s*)?(?:canais?|transmiss[aã]o)\s*:\s*",
        "",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(r"^📺\s*", "", texto).strip()

    partes = re.split(
        r"\s*;\s*|\s*,\s*|\s+\be\b\s+",
        texto,
        flags=re.IGNORECASE,
    )

    resultado = []

    for parte in partes:
        canal = normalizar_canal(parte)

        if canal and canal not in resultado:
            resultado.append(canal)

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


def pagina_parece_ser_do_dia(linhas, data_json):
    try:
        data = datetime.strptime(data_json, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False

    # A data principal deve aparecer perto do inicio do conteudo.
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

    tokens = tokens_da_pagina(html)

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
    chaves_vistas = set()

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

            eh_linha_tv = (
                "📺" in token
                or re.match(
                    r"^(?:canais?|transmiss[aã]o)\s*:",
                    token,
                    flags=re.IGNORECASE,
                )
            )

            if not eh_linha_tv:
                continue

            # Pode ser:
            #   "📺 ESPN"
            # ou
            #   "📺"
            #   "ESPN"
            tentativa = dividir_canais(
                token
            )

            if not tentativa:
                proximos = []

                for seguinte in bloco[
                    i + 1:i + 4
                ]:
                    if token_parece_inicio_evento(
                        seguinte
                    ):
                        break

                    if separar_times(
                        seguinte
                    ):
                        break

                    if seguinte.strip() == "📺":
                        continue

                    proximos.append(
                        seguinte
                    )

                if proximos:
                    tentativa = dividir_canais(
                        " ".join(
                            proximos
                        )
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

        # Evita duplicatas caso o HTML contenha a mesma informacao
        # em versao desktop e mobile.
        chave = (
            evento["hora"],
            normalizar_time(
                evento["casa"]
            ),
            normalizar_time(
                evento["fora"]
            ),
            normalizar_competicao(
                evento["competicao"]
            ),
        )

        if chave in chaves_vistas:
            continue

        chaves_vistas.add(chave)
        eventos.append(evento)

    return eventos

def parse_mantos(html, data_json):
    linhas = linhas_da_pagina(html)

    if not pagina_parece_ser_do_dia(linhas, data_json):
        print("[Mantos] data da pagina nao foi confirmada.")
        return []

    eventos = []

    # Aceita 19h00, 19:00 e varios tipos de traco.
    padrao_evento = re.compile(
        r"^(\d{1,2})(?:h|:)(\d{2})\s*[–—-]\s*"
        r"(.+?)\s+[xX×]\s+"
        r"(.+?)\s*[–—-]\s*(.+)$",
        flags=re.IGNORECASE,
    )

    indices_eventos = []

    for indice, linha in enumerate(linhas):
        match = padrao_evento.match(linha)

        if not match:
            continue

        hora, minuto, casa, fora, competicao = match.groups()

        if int(hora) > 23 or int(minuto) > 59:
            continue

        indices_eventos.append(
            (
                indice,
                hora,
                minuto,
                limpar_espacos(casa),
                limpar_espacos(fora),
                limpar_espacos(competicao),
            )
        )

    for pos, evento in enumerate(indices_eventos):
        indice, hora, minuto, casa, fora, competicao = evento

        fim = (
            indices_eventos[pos + 1][0]
            if pos + 1 < len(indices_eventos)
            else min(len(linhas), indice + 10)
        )

        bloco = linhas[indice + 1:fim]

        canais = None

        for linha in bloco:
            if re.match(
                r"^(?:canais?|transmiss[aã]o)\s*:",
                linha,
                flags=re.IGNORECASE,
            ):
                tentativa = dividir_canais(linha)

                if tentativa:
                    canais = tentativa
                    break

        if canais:
            eventos.append({
                "hora": minutos_do_dia(hora, minuto),
                "casa": casa,
                "fora": fora,
                "competicao": competicao,
                "canais": canais,
            })

    return eventos


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

    for evento in eventos:
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
    Fallback usado SOMENTE quando as duas fontes estao saudaveis.

    Serve para casos em que uma fonte publicou horario incorreto,
    mas time da casa + visitante + competicao batem exatamente.

    Regras:
      - casa exata apos normalizacao/aliases;
      - visitante exato;
      - competicao exata;
      - precisa existir exatamente UM candidato na fonte.

    Nunca e usado sozinho para aceitar uma transmissao.
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

    for evento in eventos:

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
      - horario difere no maximo 5 minutos.

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
    ) > 5:
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
    Versao 4 - cobertura maxima com protecao contra falso positivo.

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
      - mantemos a regra rigorosa da v3:
        times + competicao + horario (max. 5 min) exatos.
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
    if (
        len(fontes) >= 2
        and
        len(encontrados) < 2
    ):

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

        if not evento_bate_estritamente(
            jogo,
            evento
        ):

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
    print("=== LUBU - Atualizacao de transmissoes v5 ===")

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

    # Se uma das duas fontes nao estiver valida, nao toca no JSON.
    if len(fontes) < CONFIRMACOES_MINIMAS:
        print(
            "[SEGURANCA] Menos de duas fontes validas. "
            "Nenhuma transmissao foi alterada."
        )
        return 0

    alterados = 0
    confirmados = 0
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
        confirmados += 1

        atual = jogo.get("transmissao", [])

        if atual != nova_transmissao:
            jogo["transmissao"] = nova_transmissao
            alterados += 1

        canais_log = ", ".join(
            item["canal"]
            for item in nova_transmissao
        )

        if status == "confirmado_fonte_unica":

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

            print(
                f"[OK] {nome_jogo(jogo)} -> {canais_log}"
            )

    print("")
    print("=== RESUMO ===")
    print(f"Confirmados nas duas fontes: {confirmados}")
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
