from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    regiao = db.Column(db.String(10), default='PT')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relacionamentos com cascade (apagar tudo ao remover o user)
    entidades = db.relationship('Entidade', backref='user', lazy=True, cascade='all, delete-orphan')
    investimentos = db.relationship('Investimento', backref='user', lazy=True, cascade='all, delete-orphan')
    relatorios = db.relationship('RelatorioConfig', backref='user', lazy=True, cascade='all, delete-orphan')

    @property
    def total_investido(self):
        return sum(inv.valor for inv in self.investimentos)

    @property
    def num_entidades(self):
        return len(self.entidades)

    @property
    def num_investimentos(self):
        return len(self.investimentos)


class Entidade(db.Model):
    __tablename__ = 'entidades'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(50), default='Empresa')
    contacto = db.Column(db.String(120), default='')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


class Investimento(db.Model):
    __tablename__ = 'investimentos'
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    descricao = db.Column(db.Text, default='')
    entidade_id = db.Column(db.Integer, db.ForeignKey('entidades.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entidade = db.relationship('Entidade')


class RelatorioConfig(db.Model):
    __tablename__ = 'relatorio_configs'
    id = db.Column(db.Integer, primary_key=True)
    intervalo_dias = db.Column(db.Integer, default=30)
    formato = db.Column(db.String(5), default='pdf')
    ativo = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)