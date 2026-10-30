import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ── Formatação de moeda por região ──────────────────────────
MOEDAS = {
    'PT': {'simbolo': '€', 'posicao': 'sufixo', 'decimal': ',', 'milhar': '.', 'nome': 'Euro'},
    'BR': {'simbolo': 'R$', 'posicao': 'prefixo', 'decimal': ',', 'milhar': '.', 'nome': 'Real'},
    'US': {'simbolo': '$', 'posicao': 'prefixo', 'decimal': '.', 'milhar': ',', 'nome': 'Dólar'},
    'AO': {'simbolo': 'Kz', 'posicao': 'sufixo', 'decimal': ',', 'milhar': '.', 'nome': 'Kwanza'},
    'MZ': {'simbolo': 'MT', 'posicao': 'sufixo', 'decimal': ',', 'milhar': '.', 'nome': 'Metical'},
}

def formatar_moeda(valor, regiao: str = 'PT') -> str:
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        valor = 0.0
    cfg = MOEDAS.get(regiao, MOEDAS['PT'])
    inteiro, dec = f"{valor:.2f}".split('.')
    # Formatar número
    inteiro, dec = f"{valor:.2f}".split('.')
    inteiro_fmt = ''
    for i, d in enumerate(reversed(inteiro)):
        if i > 0 and i % 3 == 0:
            inteiro_fmt = cfg['milhar'] + inteiro_fmt
        inteiro_fmt = d + inteiro_fmt
    numero = f"{inteiro_fmt}{cfg['decimal']}{dec}"
    if cfg['posicao'] == 'prefixo':
        return f"{cfg['simbolo']} {numero}"
    return f"{numero} {cfg['simbolo']}"


# ── Geração de Relatório TXT ────────────────────────────────
def gerar_relatorio_txt(user, investimentos, caminho):
    cfg_moeda = MOEDAS.get(user.regiao, MOEDAS['PT'])
    total = sum(inv.valor for inv in investimentos)
    linhas = [
        "=" * 55,
        f"  RELATÓRIO DE INVESTIMENTOS",
        f"  Utilizador: {user.username}",
        f"  Região: {user.regiao} ({cfg_moeda['nome']})",
        f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "=" * 55,
        "",
        f"{'Data':<14} {'Entidade':<20} {'Valor':>15}",
        "-" * 55,
    ]
    for inv in investimentos:
        data_str = inv.data.strftime('%d/%m/%Y')
        valor_str = formatar_moeda(inv.valor, user.regiao)
        linhas.append(f"{data_str:<14} {inv.entidade.nome:<20} {valor_str:>15}")
    linhas += [
        "-" * 55,
        f"{'TOTAL':<35} {formatar_moeda(total, user.regiao):>15}",
        "=" * 55,
    ]
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas))
    return caminho


# ── Geração de Relatório PDF ────────────────────────────────
def gerar_relatorio_pdf(user, investimentos, caminho):
    c = canvas.Canvas(caminho, pagesize=A4)
    w, h = A4
    cfg_moeda = MOEDAS.get(user.regiao, MOEDAS['PT'])
    total = sum(inv.valor for inv in investimentos)
    y = h - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "Relatório de Investimentos")
    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Utilizador: {user.username}  |  Região: {user.regiao}")
    y -= 18
    c.drawString(50, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 30

    # Cabeçalho da tabela
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Data")
    c.drawString(180, y, "Entidade")
    c.drawString(420, y, "Valor")
    y -= 8
    c.line(50, y, 550, y)
    y -= 18

    # Linhas
    c.setFont("Helvetica", 10)
    for inv in investimentos:
        if y < 60:
            c.showPage()
            y = h - 50
        c.drawString(50, y, inv.data.strftime('%d/%m/%Y'))
        c.drawString(180, y, inv.entidade.nome[:25])
        c.drawRightString(550, y, formatar_moeda(inv.valor, user.regiao))
        y -= 16

    # Total
    y -= 10
    c.line(50, y, 550, y)
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "TOTAL")
    c.drawRightString(550, y, formatar_moeda(total, user.regiao))

    c.save()
    return caminho