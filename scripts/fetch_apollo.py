#!/usr/bin/env python3
"""
fetch_apollo.py
Busca dados do Apollo CRM e atualiza o data.json do dashboard Ademicon Vila Olimpia.
"""

import os
import json
import datetime
import requests

# ============================================================
# CONFIGURACAO
# ============================================================
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")
DATA_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")

APOLLO_BASE = "https://api.apollo.io/v1"

HEADERS = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "X-Api-Key": APOLLO_API_KEY,
}

# Mapeamento de stages do Apollo para etapas do funil
STAGE_MAP = {
    "new": "prospeccao",
    "incoming": "prospeccao",
    "open": "prospeccao",
    "qualified": "qualificado",
    "working": "qualificado",
    "proposal sent": "proposta",
    "proposal_sent": "proposta",
    "demo scheduled": "proposta",
    "demo_scheduled": "proposta",
    "negotiation": "negociacao",
    "closed won": "fechado",
    "closed_won": "fechado",
    "won": "fechado",
}

# ============================================================
# HELPERS
# ============================================================

def load_current_data():
    """Carrega o data.json existente."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Aviso: nao foi possivel ler data.json existente: {e}")
        return {}


def save_data(data):
    """Salva o data.json atualizado."""
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"data.json salvo com sucesso em {DATA_JSON_PATH}")


def get_semana_atual():
    """Retorna o numero da semana ISO atual."""
    return datetime.date.today().isocalendar()[1]


def get_inicio_semana():
    """Retorna a data de inicio da semana atual (segunda-feira)."""
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())
    return start


def get_inicio_mes():
    """Retorna a data de inicio do mes atual."""
    today = datetime.date.today()
    return today.replace(day=1)


def parse_valor(deal):
    """Extrai o valor monetario de um deal do Apollo."""
    amount = deal.get("amount") or deal.get("value") or 0
    try:
        return float(amount)
    except (TypeError, ValueError):
        return 0.0


def get_stage_funil(deal):
    """Mapeia o stage do Apollo para uma etapa do funil interno."""
    stage_raw = (deal.get("stage") or deal.get("status") or "").lower().strip()
    return STAGE_MAP.get(stage_raw, "prospeccao")


def safe_post(url, payload, label=""):
    """Faz POST na Apollo API com tratamento de erros."""
    try:
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP em {label}: {e} - {resp.text[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexao em {label}: {e}")
    except Exception as e:
        print(f"Erro inesperado em {label}: {e}")
    return None


# ============================================================
# BUSCA DE OPORTUNIDADES (DEALS)
# ============================================================

def fetch_all_opportunities():
    """Busca todas as oportunidades abertas e fechadas no mes atual."""
    deals = []
    page = 1
    per_page = 200

    print("Buscando oportunidades no Apollo...")

    while True:
        payload = {
            "page": page,
            "per_page": per_page,
        }
        result = safe_post(f"{APOLLO_BASE}/opportunities/search", payload, "opportunities/search")

        if not result:
            break

        batch = result.get("opportunities") or result.get("deals") or []
        if not batch:
            break

        deals.extend(batch)
        print(f"  Pagina {page}: {len(batch)} deals encontrados (total: {len(deals)})")

        pagination = result.get("pagination") or {}
        total_pages = pagination.get("total_pages") or 1
        if page >= total_pages or len(batch) < per_page:
            break
        page += 1

    print(f"Total de oportunidades buscadas: {len(deals)}")
    return deals


# ============================================================
# BUSCA DE CONTATOS/LEADS
# ============================================================

def fetch_contacts():
    """Busca contatos ativos no CRM."""
    contacts = []
    page = 1
    per_page = 200

    print("Buscando contatos no Apollo...")

    while True:
        payload = {
            "page": page,
            "per_page": per_page,
        }
        result = safe_post(f"{APOLLO_BASE}/contacts/search", payload, "contacts/search")

        if not result:
            break

        batch = result.get("contacts") or []
        if not batch:
            break

        contacts.extend(batch)
        pagination = result.get("pagination") or {}
        total_pages = pagination.get("total_pages") or 1
        if page >= total_pages or len(batch) < per_page:
            break
        page += 1

    print(f"Total de contatos: {len(contacts)}")
    return contacts


# ============================================================
# PROCESSAMENTO
# ============================================================

def processar_deals(deals, current_data):
    """Calcula metricas a partir dos deals."""
    inicio_semana = get_inicio_semana()
    inicio_mes = get_inicio_mes()

    vgv_semana = 0.0
    vgv_mes = 0.0
    contratos_semana = 0
    contratos_mes = 0

    funil = {"prospeccao": 0, "qualificado": 0, "proposta": 0, "negociacao": 0, "fechado": 0}

    consultores_dict = {}
    vendas_recentes = []

    for deal in deals:
        valor = parse_valor(deal)
        etapa = get_stage_funil(deal)
        funil[etapa] = funil.get(etapa, 0) + 1

        # Data de fechamento ou criacao
        closed_date_raw = deal.get("closed_date") or deal.get("close_date") or deal.get("created_at") or ""
        try:
            if "T" in str(closed_date_raw):
                dt = datetime.date.fromisoformat(str(closed_date_raw)[:10])
            elif closed_date_raw:
                dt = datetime.date.fromisoformat(str(closed_date_raw)[:10])
            else:
                dt = None
        except Exception:
            dt = None

        # Nome do responsavel
        owner = deal.get("owner") or deal.get("owner_name") or ""
        if isinstance(owner, dict):
            owner = owner.get("name") or owner.get("email") or "Desconhecido"

        if not owner:
            owner = "Desconhecido"

        # Inicializa consultor
        if owner not in consultores_dict:
            consultores_dict[owner] = {
                "nome": owner,
                "vgv_semana": 0.0,
                "vgv_mes": 0.0,
                "contratos_mes": 0,
                "leads_ativos": 0,
                "prospecoes": 0,
            }

        # Prospecao (todos os leads do consultor)
        consultores_dict[owner]["leads_ativos"] += 1
        consultores_dict[owner]["prospecoes"] += 1

        # Contabiliza fechados
        if etapa == "fechado" and valor > 0:
            if dt and dt >= inicio_mes:
                vgv_mes += valor
                contratos_mes += 1
                consultores_dict[owner]["vgv_mes"] += valor
                consultores_dict[owner]["contratos_mes"] += 1

                if dt >= inicio_semana:
                    vgv_semana += valor
                    contratos_semana += 1
                    consultores_dict[owner]["vgv_semana"] += valor

                # Venda recente para o ticker
                hora_raw = deal.get("closed_date") or deal.get("created_at") or ""
                hora = ""
                try:
                    if "T" in str(hora_raw):
                        hora = str(hora_raw)[11:16]
                except Exception:
                    hora = "--:--"

                vendas_recentes.append({
                    "consultor": owner,
                    "produto": deal.get("name") or "Consorcio",
                    "valor": valor,
                    "hora": hora,
                    "data": str(dt) if dt else "",
                })

    # Ordena vendas recentes (mais recentes primeiro, max 10)
    vendas_recentes.sort(key=lambda x: x.get("data", ""), reverse=True)
    vendas_recentes = vendas_recentes[:10]

    # Monta lista de consultores ordenada por VGV mes
    consultores_list = sorted(
        consultores_dict.values(),
        key=lambda c: c["vgv_mes"],
        reverse=True
    )

    return {
        "vgv_semana": round(vgv_semana, 2),
        "vgv_mes": round(vgv_mes, 2),
        "contratos_semana": contratos_semana,
        "contratos_mes": contratos_mes,
        "funil": funil,
        "consultores": consultores_list,
        "vendas_recentes": vendas_recentes,
    }


def processar_contatos(contacts, metricas):
    """Enriquece metricas com dados de contatos."""
    total_leads = len(contacts)
    metricas["leads_ativos"] = total_leads

    # Conta prospecoes de hoje
    hoje = datetime.date.today().isoformat()
    prospecoes_hoje = 0
    for c in contacts:
        created = c.get("created_at") or ""
        if str(created)[:10] == hoje:
            prospecoes_hoje += 1

    metricas["prospecoes_hoje"] = prospecoes_hoje
    return metricas


def calcular_historico_semanal(current_data, metricas):
    """Preserva e atualiza o historico semanal."""
    historico = current_data.get("resultados", {}).get("historico_semanal", [])

    semana_atual = get_semana_atual()
    vgv_semana = metricas["vgv_semana"]

    # Atualiza ou adiciona a entrada da semana atual
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

    # Mantém apenas as últimas 12 semanas
    historico = historico[-12:]
    return historico


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("Iniciando sincronizacao Apollo CRM -> data.json")
    print(f"Timestamp: {datetime.datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    current_data = load_current_data()

    if not APOLLO_API_KEY:
        print("AVISO: APOLLO_API_KEY nao encontrada. Apenas o timestamp sera atualizado.")
        current_data["ultima_atualizacao"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        save_data(current_data)
        print("data.json atualizado com novo timestamp (sem dados do Apollo).")
        return

    # Busca dados
    deals = fetch_all_opportunities()
    contacts = fetch_contacts()

    # Processa
    metricas = processar_deals(deals, current_data)
    metricas = processar_contatos(contacts, metricas)
    historico = calcular_historico_semanal(current_data, metricas)

    # Monta novo data.json preservando plano_90_dias e configuracoes
    novo_data = dict(current_data)  # copia os campos existentes (inclui plano_90_dias)
    novo_data["ultima_atualizacao"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    # Atualiza resultados
    novo_data["resultados"] = {
        "vgv_semana_atual": metricas["vgv_semana"],
        "vgv_mes_atual": metricas["vgv_mes"],
        "contratos_semana": metricas["contratos_semana"],
        "contratos_mes": metricas["contratos_mes"],
        "leads_ativos": metricas["leads_ativos"],
        "prospecoes_hoje": metricas["prospecoes_hoje"],
        "historico_semanal": historico,
    }

    # Atualiza funil, consultores e vendas
    novo_data["funil"] = metricas["funil"]
    novo_data["consultores"] = metricas["consultores"]
    novo_data["vendas_recentes"] = metricas["vendas_recentes"]

    # plano_90_dias e metas sao preservados da leitura inicial (nao sobrescritos)

    save_data(novo_data)

    print("\nResumo:")
    print(f"  VGV Semana: R$ {metricas['vgv_semana']:,.2f}")
    print(f"  VGV Mes:    R$ {metricas['vgv_mes']:,.2f}")
    print(f"  Contratos:  {metricas['contratos_mes']}")
    print(f"  Leads:      {metricas['leads_ativos']}")
    print(f"  Consultores ativos: {len(metricas['consultores'])}")
    print("\nSincronizacao concluida com sucesso!")


if __name__ == "__main__":
    main()
