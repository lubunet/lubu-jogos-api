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
}

PERFIS_YOUTUBE = {
    "tntsportsbr": "tnt",
    "getv": "ge tv",
    "cazetv": "caze tv",
    "paulistao": "paulistao",
    "sportynetbrasil": "sportynet",
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


def parse_dpf(html, data_json):
    linhas = linhas_da_pagina(html)

    if not pagina_parece_ser_do_dia(linhas, data_json):
        print("[DPF] data da pagina nao foi confirmada.")
        return []

    eventos = []

    padrao_horario = re.compile(
        r"^(?:🕗\s*)?(\d{1,2}):(\d{2})\s+(.+)$"
    )

    indices_eventos = []

    for indice, linha in enumerate(linhas):
        match = padrao_horario.match(linha)

        if not match:
            continue

        hora, minuto, competicao = match.groups()

        if int(hora) > 23 or int(minuto) > 59:
            continue

        indices_eventos.append(
            (indice, hora, minuto, competicao)
        )

    for pos, (indice, hora, minuto, competicao) in enumerate(indices_eventos):
        fim = (
            indices_eventos[pos + 1][0]
            if pos + 1 < len(indices_eventos)
            else min(len(linhas), indice + 12)
        )

        bloco = linhas[indice + 1:fim]

        times = None
        canais = None

        for linha in bloco:
            if times is None:
                tentativa = separar_times(linha)

                if tentativa:
                    times = tentativa
                    continue

            if (
                linha.startswith("📺")
                or re.match(
                    r"^(?:canais?|transmiss[aã]o)\s*:",
                    linha,
                    flags=re.IGNORECASE,
                )
            ):
                tentativa_canais = dividir_canais(linha)

                if tentativa_canais:
                    canais = tentativa_canais
                    break

        if times and canais:
            eventos.append({
                "hora": minutos_do_dia(hora, minuto),
                "casa": times[0],
                "fora": times[1],
                "competicao": limpar_espacos(competicao),
                "canais": canais,
            })

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
# CONFIRMACAO ENTRE AS DUAS FONTES
# ============================================================

def confirmar_transmissao(jogo, fontes):
    encontrados = {}

    for nome_fonte, eventos in fontes.items():
        evento = encontrar_evento(jogo, eventos)

        if evento:
            encontrados[nome_fonte] = evento

    if len(encontrados) < CONFIRMACOES_MINIMAS:
        return {
            "status": "insuficiente",
            "transmissao": None,
            "fontes": encontrados,
        }

    votos = Counter()

    for evento in encontrados.values():
        for canal in set(evento["canais"]):
            votos[canal] += 1

    canais_confirmados = sorted(
        canal
        for canal, quantidade in votos.items()
        if quantidade >= CONFIRMACOES_MINIMAS
    )

    if not canais_confirmados:
        return {
            "status": "conflito",
            "transmissao": [],
            "fontes": encontrados,
        }

    transmissao = [
        {
            "canal": nome_exibicao_canal(canal),
            "fonte": "DPF + Mantos",
        }
        for canal in canais_confirmados
    ]

    return {
        "status": "confirmado",
        "transmissao": transmissao,
        "fontes": encontrados,
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
    print("=== LUBU - Atualizacao de transmissoes ===")

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
