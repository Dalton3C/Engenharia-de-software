import os
from datetime import datetime, timedelta, timezone
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, send_file)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

from models import db, User, Entidade, Investimento, RelatorioConfig
from utils import formatar_moeda, gerar_relatorio_txt, gerar_relatorio_pdf

# ── Configuração ────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'troca-isto-por-uma-chave-segura')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///investimentos.db'
app.config['UPLOAD_FOLDER'] = 'relatorios'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para aceder a esta página.'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_utils():
    return dict(formatar_moeda=formatar_moeda, now=datetime.now)


# ══════════════════════════════════════════════════════════════
#  AUTENTICAÇÃO
# ══════════════════════════════════════════════════════════════

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        regiao = request.form.get('regiao', 'PT')

        if not username or not email or not password:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Utilizador ou email já existe.', 'danger')
            return redirect(url_for('register'))

        user = User(
            username=username, email=email,
            password_hash=generate_password_hash(password),
            regiao=regiao
        )
        db.session.add(user)
        db.session.commit()
        flash('Conta criada com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Credenciais inválidas.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('login'))


# ══════════════════════════════════════════════════════════════
#  PERFIL (NOVO!)
# ══════════════════════════════════════════════════════════════

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        acao = request.form.get('acao', '')

        if acao == 'editar_dados':
            novo_username = request.form.get('username', '').strip()
            novo_email = request.form.get('email', '').strip()
            nova_regiao = request.form.get('regiao', 'PT')

            if not novo_username or not novo_email:
                flash('Utilizador e email são obrigatórios.', 'danger')
            else:
                # Verificar se username/email já existem (noutro user)
                existe = User.query.filter(
                    User.id != current_user.id,
                    (User.username == novo_username) | (User.email == novo_email)
                ).first()
                if existe:
                    flash('Utilizador ou email já está em uso.', 'danger')
                else:
                    current_user.username = novo_username
                    current_user.email = novo_email
                    current_user.regiao = nova_regiao
                    db.session.commit()
                    flash('Dados atualizados com sucesso!', 'success')

        elif acao == 'mudar_senha':
            senha_atual = request.form.get('senha_atual', '')
            nova_senha = request.form.get('nova_senha', '')
            confirmar = request.form.get('confirmar_senha', '')

            if not check_password_hash(current_user.password_hash, senha_atual):
                flash('Palavra-passe atual incorreta.', 'danger')
            elif len(nova_senha) < 4:
                flash('A nova palavra-passe deve ter pelo menos 4 caracteres.', 'danger')
            elif nova_senha != confirmar:
                flash('As palavras-passe não coincidem.', 'danger')
            else:
                current_user.password_hash = generate_password_hash(nova_senha)
                db.session.commit()
                flash('Palavra-passe alterada com sucesso!', 'success')

        return redirect(url_for('perfil'))

    return render_template('perfil.html')


# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════

@app.route('/')
@login_required
def dashboard():
    recentes = (Investimento.query
                .filter_by(user_id=current_user.id)
                .order_by(Investimento.data.desc())
                .limit(5).all())
    return render_template('dashboard.html', recentes=recentes)


# ══════════════════════════════════════════════════════════════
#  ENTIDADES
# ══════════════════════════════════════════════════════════════

@app.route('/entidades', methods=['GET', 'POST'])
@login_required
def entidades():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        tipo = request.form.get('tipo', 'Empresa').strip()
        contacto = request.form.get('contacto', '').strip()
        if nome:
            db.session.add(Entidade(
                nome=nome, tipo=tipo, contacto=contacto,
                user_id=current_user.id
            ))
            db.session.commit()
            flash('Entidade adicionada.', 'success')
        return redirect(url_for('entidades'))

    pesquisa = request.args.get('q', '').strip()
    query = Entidade.query.filter_by(user_id=current_user.id)
    if pesquisa:
        query = query.filter(Entidade.nome.ilike(f'%{pesquisa}%'))
    return render_template('entidades.html',
                           entidades=query.order_by(Entidade.nome).all(),
                           pesquisa=pesquisa)


@app.route('/entidades/<int:eid>/delete', methods=['POST'])
@login_required
def delete_entidade(eid):
    ent = db.session.get(Entidade, eid)
    if ent and ent.user_id == current_user.id:
        db.session.delete(ent)
        db.session.commit()
        flash('Entidade removida.', 'info')
    return redirect(url_for('entidades'))


# ══════════════════════════════════════════════════════════════
#  INVESTIMENTOS
# ══════════════════════════════════════════════════════════════

@app.route('/investimentos', methods=['GET', 'POST'])
@login_required
def investimentos():
    if request.method == 'POST':
        entidade_id = request.form.get('entidade_id', type=int)
        valor = request.form.get('valor', type=float)
        descricao = request.form.get('descricao', '').strip()
        data_str = request.form.get('data', '')

        if not entidade_id or not valor or valor <= 0:
            flash('Preencha a entidade e um valor válido.', 'danger')
            return redirect(url_for('investimentos'))

        try:
            data = datetime.strptime(data_str, '%Y-%m-%d') if data_str else datetime.now(timezone.utc)
        except ValueError:
            data = datetime.now(timezone.utc)

        db.session.add(Investimento(
            valor=valor, data=data, descricao=descricao,
            entidade_id=entidade_id, user_id=current_user.id
        ))
        db.session.commit()
        flash('Investimento registado.', 'success')
        return redirect(url_for('investimentos'))

    lista = (Investimento.query
             .filter_by(user_id=current_user.id)
             .order_by(Investimento.data.desc()).all())
    entidades = Entidade.query.filter_by(user_id=current_user.id).all()
    return render_template('investimentos.html',
                           investimentos=lista, entidades=entidades)


@app.route('/investimentos/exportar')
@login_required
def exportar_investimentos():
    invs = (Investimento.query
            .filter_by(user_id=current_user.id)
            .order_by(Investimento.data.desc()).all())
    caminho = os.path.join(app.config['UPLOAD_FOLDER'], f'investimentos_{current_user.id}.txt')
    gerar_relatorio_txt(current_user, invs, caminho)
    return send_file(caminho, as_attachment=True, download_name='investimentos.txt')


# ══════════════════════════════════════════════════════════════
#  RELATÓRIOS
# ══════════════════════════════════════════════════════════════

@app.route('/relatorios', methods=['GET', 'POST'])
@login_required
def relatorios():
    config = RelatorioConfig.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        intervalo = request.form.get('intervalo_dias', 30, type=int)
        formato = request.form.get('formato', 'pdf')
        if not config:
            config = RelatorioConfig(user_id=current_user.id)
            db.session.add(config)
        config.intervalo_dias = max(1, intervalo)
        config.formato = formato
        config.ativo = True
        db.session.commit()
        flash(f'Relatório configurado: a cada {intervalo} dias em .{formato}', 'success')
        return redirect(url_for('relatorios'))
    return render_template('relatorios.html', config=config)


@app.route('/relatorios/gerar')
@login_required
def gerar_relatorio():
    config = RelatorioConfig.query.filter_by(user_id=current_user.id).first()
    if not config:
        flash('Configure o relatório primeiro.', 'warning')
        return redirect(url_for('relatorios'))

    data_inicio = datetime.now(timezone.utc) - timedelta(days=config.intervalo_dias)
    invs = (Investimento.query
            .filter_by(user_id=current_user.id)
            .filter(Investimento.data >= data_inicio)
            .order_by(Investimento.data).all())

    nome = f'relatorio_{current_user.id}_{datetime.now():%Y%m%d}'
    if config.formato == 'pdf':
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], f'{nome}.pdf')
        gerar_relatorio_pdf(current_user, invs, caminho)
    else:
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], f'{nome}.txt')
        gerar_relatorio_txt(current_user, invs, caminho)

    return send_file(caminho, as_attachment=True, download_name=os.path.basename(caminho))


# ── Agendador ───────────────────────────────────────────────
def tarefa_relatorios_automaticos():
    with app.app_context():
        for cfg in RelatorioConfig.query.filter_by(ativo=True).all():
            user = db.session.get(User, cfg.user_id)
            if not user:
                continue
            data_inicio = datetime.now(timezone.utc) - timedelta(days=cfg.intervalo_dias)
            invs = (Investimento.query
                    .filter_by(user_id=user.id)
                    .filter(Investimento.data >= data_inicio).all())
            nome = f'relatorio_auto_{user.id}_{datetime.now():%Y%m%d}'
            if cfg.formato == 'pdf':
                caminho = os.path.join(app.config['UPLOAD_FOLDER'], f'{nome}.pdf')
                gerar_relatorio_pdf(user, invs, caminho)
            else:
                caminho = os.path.join(app.config['UPLOAD_FOLDER'], f'{nome}.txt')
                gerar_relatorio_txt(user, invs, caminho)
            print(f"[AUTO] Relatório gerado para {user.username}: {caminho}")


scheduler = BackgroundScheduler()
scheduler.add_job(tarefa_relatorios_automaticos, 'interval', days=1)  # ✅ Corrigido


# ══════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    scheduler.start()
    app.run(debug=True, port=5000)