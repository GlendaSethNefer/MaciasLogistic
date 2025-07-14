from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()  # si no lo tenías definido, créalo aquí

# Tabla intermedia user_roles
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'),    primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'),    primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __str__(self):
        return self.name

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    active        = db.Column(db.Boolean, default=True, nullable=False)

    roles = db.relationship('Role', secondary=user_roles, backref='users')

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    def has_role(self, role_name):
        return any(r.name == role_name for r in self.roles)

class Orden(db.Model):
    __tablename__ = 'ordenes'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    vin = db.Column(db.String(17), nullable=False)
    expediente_id = db.Column(db.Integer, db.ForeignKey('expedientes.id'))  # opcional
    estado = db.Column(db.String(50))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    procesados = db.Column(db.Integer, default=0)
    observaciones = db.Column(db.Text)

    usuario = db.relationship('Usuario', backref='ordenes')
    cliente = db.relationship('Cliente', backref='ordenes')
