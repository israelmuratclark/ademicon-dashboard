#!/usr/bin/env python3
"""
fetch_avapro.py
Autentica no AVAPRO (crmapollo.com.br) e atualiza o data.json do dashboard Ademicon Vila Olímpia.

Endpoints usados:
  - Login:    POST https://crmapollo.com.br/ademicon-vila-olimpia/
  - Vendas:   GET  /app/controller/RelatoriosController.php?action=fetchTabelaVendas&...
  - Funil:    GET  /app/views/relatorios/relFunil.php?equipes=true
  - KPIs:     GET  /app/views/index.php?equipes=true
"""

import os
import json
import hashlib
import datetime
import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURAÇÃO
# ============================================================
AVAPRO_USERNAME = os.environ.get("AVAPRO_USERNAME", "")
AVAPRO_PASSWORD = os.environ.get("AVAPRO_PASSWORD", "")

# Login é feito via AJAX para LoginController.php (senha em MD5)
AVAPRO_LOGIN_URL = "https://crmapollo.com.br/app/controller/LoginController.php"
AVAPRO_BASE = "https://crmapollo.com.br/app"

# Device hash fixo — identificador da aplicação de automação
DEVICE_HASH = "ademicon-dashboard-sync-bot-v1"

# Equipe alvo: apenas MXMR1 (IDs 101 e 102 no AVAPRO)
EQUIPE_ALVO = "MXMR1"
EQUIPE_ID_USUARIOS = "101,102"  # value do select no relFunil/relVendas

DATA_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://crmapollo.com.br/ademicon-vila-olimpia/",
}


# ============================================================
# HELPERS
# ============================================================

def load_current_data():
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Aviso: não foi possível ler data.json existente: {e}")
        return {}


def save_data(data):
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"data.json salvo em {DATA_JSON_PATH}")


def get_inicio_semana():
    today = datetime.date.today()
    return today - datetime.timedelta(days=today.weekday())


def get_inicio_mes():
    return datetime.date.today().replace(day=1)


def get_fim_mes():
    today = datetime.date.today()
    # último dia do mês
    if today.month == 12:
        return today.replace(day=31)
    return (today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1))


def get_semana_iso():
    return datetime.date.today().isocalendar()[1]


def parse_valor_brl(texto):
    """Converte 'R$ 100.000,00' ou '100000.00' para float."""
    if not texto:
        return 0.0
    t = str(texto).replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(t)
    except (ValueError, TypeError):
        return 0.0


# ============================================================
# AUTENTICAÇÃO
# ============================================================

def login():
    """
    Autentica no AVAPRO via AJAX (LoginController.php).
    - Senha deve ser enviada como hash MD5 (comportamento do access.js)
    - Retorna sessão com cookies, ou None se falhar
    """
    if not AVAPRO_USERNAME or not AVAPRO_PASSWORD:
        print("AVISO: AVAPRO_USERNAME ou AVAPRO_PASSWORD não definidos.")
        return None

    session = requests.Session()
    session.headers.update(HEADERS)

    # Primeiro faz GET na página de login para obter o cookie PHPSESSID inicial
    try:
        session.get(
            "https://crmapollo.com.br/ademicon-vila-olimpia/",
            timeout=15,
        )
    except Exception:
        pass  # ignora erro no GET inicial

    # Hash MD5 da senha (igual ao que o access.js faz com $.md5())
    senha_md5 = hashlib.md5(AVAPRO_PASSWORD.encode("utf-8")).hexdigest()

    print(f"Autenticando como '{AVAPRO_USERNAME}' no LoginController.php...")
    try:
        resp = session.post(
            AVAPRO_LOGIN_URL,
            data={
                "action": "login",
                "usuario": AVAPRO_USERNAME,
                "senha": senha_md5,
                "device_hash": DEVICE_HASH,
            },
            timeout=30,
        )

        # Resposta esperada: {"return": true, "mensagem": "..."}
        try:
            result = resp.json()
        except Exception:
            print(f"Resposta não-JSON do login: {resp.text[:200]}")
            return None

        if result.get("return") is True:
            print(f"Login OK — {result.get('mensagem', 'Autenticado')}")
            return session
        else:
            print(f"Login FALHOU — {result.get('mensagem', 'Credenciais inválidas')}")
            return None

    except Exception as e:
        print(f"Erro ao autenticar: {e}")
        return None


# ============================================================
# BUSCA DE VENDAS (HTML — relVendas.php já renderiza a tabela)
# ============================================================

def fetch_vendas_html(session):
    """
    Faz GET no relatório de vendas filtrado pela equipe MXMR1.
    O servidor renderiza a tabela de vendas do mês atual com o filtro de usuários.
    Retorna HTML string.
    """
    # A página aceita POST com os filtros via form submit
    url = f"{AVAPRO_BASE}/views/relatorios/relVendas.php?equipes=true"
    print(f"Buscando vendas da equipe {EQUIPE_ALVO} (IDs: {EQUIPE_ID_USUARIOS})...")

    # Primeiro GET para obter o formulário com datas padrão
    try:
        r_get = session.get(url, timeout=30,
            headers={"Accept": "text/html,*/*", "X-Requested-With": ""})
        r_get.raise_for_status()
    except Exception as e:
        print(f"Erro no GET inicial de relVendas.php: {e}")
        return ""

    # Extrai as datas padrão do formulário
    from bs4 import BeautifulSoup as _BS
    soup = _BS(r_get.text, "lxml")
    data_inicio = get_inicio_mes().strftime("%d/%m/%Y")
    data_fim = get_fim_mes().strftime("%d/%m/%Y")

    # POST com filtro de equipe MXMR1 — campos: dataInicio, dataFim, id_usuario (formato ISO)
    data_inicio_iso = get_inicio_mes().isoformat()
    data_fim_iso = get_fim_mes().isoformat()
    try:
        resp = session.post(url, data={
            "dataInicio": data_inicio_iso,
            "dataFim": data_fim_iso,
            "id_usuario": EQUIPE_ID_USUARIOS,
            "pesquisar": "Pesquisar",
        }, timeout=30, headers={"Accept": "text/html,*/*", "X-Requested-With": "",
                                 "Referer": url,
                                 "Content-Type": "application/x-www-form-urlencoded"})
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Erro ao buscar relVendas.php (POST): {e}")
        return r_get.text


def parse_vendas_html(html):
    """
    Extrai tabela de vendas do HTML do relVendas.php.
    Colunas: #, Cliente, Celular, Valor, Grupo/Cota, Matricula, Contrato, Cadastro,
             Tipo, Opção de parcela, Adesão, Seguro?, Loja, Obs, Data fechamento,
             Consultor, Equipe, Login, Ações
    Retorna lista de dicts.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")

    # Localiza a tabela de vendas (tem coluna "Consultor")
    tabela = None
    for t in soup.find_all("table"):
        ths = [th.get_text(strip=True) for th in t.find_all("th")]
        if "Consultor" in ths and "Valor" in ths:
            tabela = t
            break

    if not tabela:
        print("Aviso: tabela de vendas não encontrada no HTML.")
        return []

    # Descobre índice de cada coluna
    headers = [th.get_text(strip=True) for th in tabela.find_all("th")]
    col = {h: i for i, h in enumerate(headers)}

    vendas = []
    for row in tabela.find_all("tr")[1:]:  # pula cabeçalho
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 5:
            continue
        try:
            int(cells[0])  # primeira coluna é o índice numérico
        except ValueError:
            continue  # linha de totais

        def get(colname, fallback=""):
            idx = col.get(colname)
            return cells[idx] if idx is not None and idx < len(cells) else fallback

        vendas.append({
            "cliente": get("Cliente"),
            "valor_str": get("Valor"),
            "tipo": get("Tipo"),
            "data_cadastro": get("Cadastro"),
            "data_fechamento": get("Data fechamento"),
            "consultor": get("Consultor"),
            "equipe": get("Equipe"),
            "grupo_cota": get("Grupo/Cota"),
        })

    print(f"Vendas encontradas na tabela HTML: {len(vendas)}")
    return vendas


# ============================================================
# BUSCA DO RELATÓRIO DE FUNIL (HTML)
# ============================================================

def fetch_funil_html(session):
    """
    Faz POST no relatório de funil filtrado pela equipe MXMR1.
    Retorna HTML string.
    """
    url = f"{AVAPRO_BASE}/views/relatorios/relFunil.php?equipes=true"
    print(f"Buscando funil da equipe {EQUIPE_ALVO}...")

    data_inicio_iso = get_inicio_mes().isoformat()
    data_fim_iso = get_fim_mes().isoformat()

    try:
        resp = session.post(url, data={
            "dataInicio": data_inicio_iso,
            "dataFim": data_fim_iso,
            "id_usuario": EQUIPE_ID_USUARIOS,
            "pesquisar": "Pesquisar",
        }, timeout=30, headers={"Accept": "text/html,*/*", "X-Requested-With": "",
                                 "Referer": url,
                                 "Content-Type": "application/x-www-form-urlencoded"})
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Erro ao buscar relatório de funil: {e}")
        return ""


def parse_funil_html(html):
    """
    Extrai métricas por consultor da tabela do relFunil.php.
    Colunas: #, Consultor, Leads, Ligações ef., Lig.Ag., Reuniões, Reun.Ag., Propostas, Cotas, Clientes, Imóveis, Veículos, Serviços, Total

    Retorna:
      - consultores: lista de dicts com métricas por consultor
      - leads_ativos: total de leads da equipe
      - totais: dict com somas
    """
    if not html:
        return [], 0, {}

    soup = BeautifulSoup(html, "lxml")

    # Encontra a tabela de consultores (contém coluna "Cotas")
    tabela = None
    for t in soup.find_all("table"):
        header_text = t.get_text()
        if "Cotas" in header_text and "Consultor" in header_text:
            tabela = t
            break

    if not tabela:
        print("Aviso: tabela de funil não encontrada no HTML.")
        return [], 0, {}

    consultores = []
    total_leads = 0
    totais = {}

    rows = tabela.find_all("tr")
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        # Linha de dados tem pelo menos 13 células e começa com número
        if len(cells) < 13:
            continue
        try:
            int(cells[0])  # primeira célula é o índice numérico
        except ValueError:
            # linha de totais ou cabeçalho
            if "Totais" in cells[0] or cells[0] == "":
                try:
                    totais = {
                        "leads": int(cells[2]) if len(cells) > 2 and cells[2].isdigit() else 0,
                        "cotas": int(cells[8]) if len(cells) > 8 and cells[8].isdigit() else 0,
                        "clientes": int(cells[9]) if len(cells) > 9 and cells[9].isdigit() else 0,
                        "vgv_imoveis": parse_valor_brl(cells[10]) if len(cells) > 10 else 0.0,
                        "vgv_veiculos": parse_valor_brl(cells[11]) if len(cells) > 11 else 0.0,
                        "vgv_servicos": parse_valor_brl(cells[12]) if len(cells) > 12 else 0.0,
                        "vgv_total": parse_valor_brl(cells[13]) if len(cells) > 13 else 0.0,
                    }
                except Exception:
                    pass
            continue

        nome = cells[1]
        leads = int(cells[2]) if cells[2].isdigit() else 0
        # Colunas (0-indexed): 0=#, 1=Consultor, 2=Leads, 3=Lig.ef., 4=Lig.Ag.,
        #   5=Reun.real., 6=Reun.Ag., 7=Propostas, 8=Cotas, 9=Clientes,
        #   10=Imóveis, 11=Veículos, 12=Serviços, 13=Total
        cotas = int(cells[8]) if len(cells) > 8 and cells[8].isdigit() else 0
        clientes = int(cells[9]) if len(cells) > 9 and cells[9].isdigit() else 0
        vgv_imoveis = parse_valor_brl(cells[10]) if len(cells) > 10 else 0.0
        vgv_veiculos = parse_valor_brl(cells[11]) if len(cells) > 11 else 0.0
        vgv_servicos = parse_valor_brl(cells[12]) if len(cells) > 12 else 0.0
        vgv_total = parse_valor_brl(cells[13]) if len(cells) > 13 else 0.0

        total_leads += leads
        consultores.append({
            "nome": nome,
            "leads_ativos": leads,
            "contratos_mes": cotas,
            "vgv_mes": vgv_total,
            "vgv_imoveis": vgv_imoveis,
            "vgv_veiculos": vgv_veiculos,
            "vgv_servicos": vgv_servicos,
            # VGV semana calculado depois a partir dos dados de vendas
            "vgv_semana": 0.0,
        })

    return consultores, total_leads, totais


# ============================================================
# PROCESSAMENTO DAS VENDAS JSON
# ============================================================

def processar_vendas(vendas_lista, consultores_funil):
    """
    Processa a lista de vendas parseadas do relVendas.php HTML.
    A página já filtra pelo mês atual por padrão.
    Retorna métricas calculadas.
    """
    inicio_semana = get_inicio_semana()
    inicio_mes = get_inicio_mes()

    vgv_semana = 0.0
    vgv_mes = 0.0
    contratos_semana = 0
    contratos_mes = 0
    vendas_recentes = []

    # Mapa consultor → vgv_semana (para enriquecer a lista do funil)
    vgv_semana_por_consultor = {}

    for venda in vendas_lista:
        valor = parse_valor_brl(venda.get("valor_str", ""))
        consultor = venda.get("consultor", "Desconhecido")
        tipo = venda.get("tipo", "Consórcio")

        # Data de fechamento — tenta "Data fechamento" primeiro, depois "Cadastro"
        data_raw = venda.get("data_fechamento") or venda.get("data_cadastro") or ""
        dt = None
        hora = "--:--"
        try:
            if data_raw:
                # Formato: "01/04/2026 17:30" ou "01/04/2026"
                partes = str(data_raw).strip().split(" ")
                data_parte = partes[0]
                hora = partes[1][:5] if len(partes) > 1 else "--:--"
                if "/" in data_parte:
                    d, m, a = data_parte.split("/")
                    dt = datetime.date(int(a), int(m), int(d))
                else:
                    dt = datetime.date.fromisoformat(data_parte[:10])
        except Exception:
            dt = None

        # Usar data de cadastro se não tiver data de fechamento
        if dt is None:
            try:
                data_cad = venda.get("data_cadastro", "")
                if data_cad:
                    partes = str(data_cad).strip().split(" ")
                    d, m, a = partes[0].split("/")
                    dt = datetime.date(int(a), int(m), int(d))
                    hora = partes[1][:5] if len(partes) > 1 else "--:--"
            except Exception:
                pass

        # A página já filtra pelo mês — toda venda aqui é do mês atual
        if valor > 0:
            vgv_mes += valor
            contratos_mes += 1

            # Verifica se é da semana atual
            if dt and dt >= inicio_semana:
                vgv_semana += valor
                contratos_semana += 1
                vgv_semana_por_consultor[consultor] = (
                    vgv_semana_por_consultor.get(consultor, 0.0) + valor
                )

            vendas_recentes.append({
                "consultor": consultor,
                "produto": tipo,
                "valor": valor,
                "hora": hora,
                "data": str(dt) if dt else "",
            })

    # Ordena por data mais recente e limita
    vendas_recentes.sort(key=lambda x: (x.get("data", ""), x.get("hora", "")), reverse=True)
    vendas_recentes = vendas_recentes[:10]

    # Enriquece consultores com vgv_semana
    for c in consultores_funil:
        c["vgv_semana"] = vgv_semana_por_consultor.get(c["nome"], 0.0)

    return {
        "vgv_semana": round(vgv_semana, 2),
        "vgv_mes": round(vgv_mes, 2),
        "contratos_semana": contratos_semana,
        "contratos_mes": contratos_mes,
        "vendas_recentes": vendas_recentes,
    }


# ============================================================
# FUNIL POR ESTÁGIO (estimativa a partir dos dados disponíveis)
# ============================================================

def calcular_funil_estagios(consultores, contratos_mes):
    """
    Monta os contadores do funil de vendas.
    - fechado: contratos fechados no mês
    - prospeccao/qualificado/proposta/negociacao: estimados a partir de leads e cotas
    """
    total_leads = sum(c.get("leads_ativos", 0) for c in consultores)
    total_cotas = sum(c.get("contratos_mes", 0) for c in consultores)
    total_propostas = sum(c.get("contratos_mes", 0) for c in consultores)  # mínimo

    # Estimativa conservadora das etapas intermediárias
    fechado = contratos_mes
    negociacao = max(0, total_leads // 5)
    proposta = max(0, total_leads // 4)
    qualificado = max(0, total_leads // 3)
    prospeccao = max(0, total_leads - qualificado - proposta - negociacao - fechado)

    return {
        "prospeccao": prospeccao,
        "qualificado": qualificado,
        "proposta": proposta,
        "negociacao": negociacao,
        "fechado": fechado,
    }


# ============================================================
# HISTÓRICO SEMANAL
# ============================================================

def atualizar_historico_semanal(current_data, vgv_semana):
    historico = current_data.get("resultados", {}).get("historico_semanal", [])
    semana_atual = get_semana_iso()

    entrada_encontrada = False
    for entrada in historico:
        if entrada.get("semana") == semana_atual:
            entrada["vgv"] = vgv_semana
            entrada_encontrada = True
            break

    if not entrada_encontrada:
        historico.append({
            "semana": semana_atual,
            "vgv": vgv_semana,
            "label": f"S{len(historico) + 1}",
        })

    return historico[-12:]


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("Iniciando sincronização AVAPRO → data.json")
    print(f"Timestamp: {datetime.datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    current_data = load_current_data()

    # ── 1. Login ──────────────────────────────────────────────
    session = login()
    if not session:
        print("Não foi possível autenticar. Atualizando apenas o timestamp.")
        current_data["ultima_atualizacao"] = datetime.datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        save_data(current_data)
        return

    # ── 2. Vendas (HTML) ──────────────────────────────────────
    vendas_html = fetch_vendas_html(session)
    vendas_lista = parse_vendas_html(vendas_html)

    # ── 3. Funil / Consultores (HTML) ─────────────────────────
    funil_html = fetch_funil_html(session)
    consultores, leads_ativos, totais_funil = parse_funil_html(funil_html)
    print(f"Consultores encontrados: {len(consultores)} | Leads: {leads_ativos}")

    # ── 4. Processamento ──────────────────────────────────────
    metricas = processar_vendas(vendas_lista, consultores)

    # Fallback: se vendas HTML não retornou dados mas funil tem totais
    if metricas["vgv_mes"] == 0 and totais_funil.get("vgv_total", 0) > 0:
        metricas["vgv_mes"] = totais_funil["vgv_total"]
        metricas["contratos_mes"] = totais_funil.get("cotas", 0)
        print("Aviso: usando totais do relFunil.php como fallback para VGV/contratos.")

    funil_estagios = calcular_funil_estagios(consultores, metricas["contratos_mes"])
    historico = atualizar_historico_semanal(current_data, metricas["vgv_semana"])

    # Ordena consultores por VGV mês
    consultores_sorted = sorted(
        consultores, key=lambda c: c["vgv_mes"], reverse=True
    )

    # ── 5. Monta novo data.json ───────────────────────────────
    novo_data = dict(current_data)
    novo_data["ultima_atualizacao"] = datetime.datetime.utcnow().strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    novo_data["resultados"] = {
        "vgv_semana_atual": metricas["vgv_semana"],
        "vgv_mes_atual": metricas["vgv_mes"],
        "contratos_semana": metricas["contratos_semana"],
        "contratos_mes": metricas["contratos_mes"],
        "leads_ativos": leads_ativos,
        "prospecoes_hoje": 0,  # não há endpoint dedicado — pode ser enriquecido depois
        "historico_semanal": historico,
    }
    novo_data["funil"] = funil_estagios
    novo_data["consultores"] = consultores_sorted
    novo_data["vendas_recentes"] = metricas["vendas_recentes"]
    # plano_90_dias e metas são preservados da leitura inicial

    save_data(novo_data)

    print("\nResumo:")
    print(f"  VGV Semana:  R$ {metricas['vgv_semana']:,.2f}")
    print(f"  VGV Mês:     R$ {metricas['vgv_mes']:,.2f}")
    print(f"  Contratos:   {metricas['contratos_mes']}")
    print(f"  Leads:       {leads_ativos}")
    print(f"  Consultores: {len(consultores_sorted)}")
    print("\nSincronização concluída com sucesso!")


if __name__ == "__main__":
    main()
