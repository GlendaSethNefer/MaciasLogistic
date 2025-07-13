from flask import Flask, render_template, request, redirect, url_for, flash, abort, get_flashed_messages
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'TU_CLAVE_SECRETA_ALEATORIA'
app.jinja_env.globals['now'] = datetime.utcnow

# Config DB
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'maciaslogistic'
}

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Roles y permisos
PERMISSIONS = {
    'admin':    ['create','edit','delete','view'],
    'vendedor': ['view','create']
}

@app.template_global()
def has_permission(perm: str) -> bool:
    rol = getattr(current_user, 'rol', None)
    return current_user.is_authenticated and rol and perm in PERMISSIONS.get(rol, [])

# Context processor
@app.context_processor
def inject_user():
    return {
        'current_user': current_user,
        'rol_actual': getattr(current_user, 'rol', None),
        'nombre_usuario': getattr(current_user, 'nombre', None)
    }

# User class
class User(UserMixin):
    def __init__(self, id, nombre, usuario, rol):
        self.id = id
        self.nombre = nombre
        self.usuario = usuario
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id,nombre,usuario,rol,contraseña FROM usuarios WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        return User(row['id'], row['nombre'], row['usuario'], row['rol'])
    return None

def permission_required(perm):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not has_permission(perm):
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ----------------------------------------
# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input  = request.form['usuario']
        password_input = request.form['password']
        conn = mysql.connector.connect(**db_config)
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, nombre, usuario, rol, contraseña
            FROM usuarios
            WHERE usuario = %s
        """, (usuario_input,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            flash('Usuario no registrado', 'error')
            return redirect(url_for('login'))
        if not check_password_hash(row['contraseña'], password_input):
            flash('Contraseña incorrecta', 'error')
            return redirect(url_for('login'))
        user = User(row['id'], row['nombre'], row['usuario'], row['rol'])
        login_user(user)
        flash('Sesión iniciada correctamente', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('inicio'))

    return render_template('vehiculos/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión','success')
    return redirect(url_for('login'))

# ----------------------------------------
# Página pública
@app.route('/')
def inicio():
    return render_template('vehiculos/inicio.html')

# ----------------------------------------
# PROVEEDORES
@app.route('/proveedores')
@login_required
def lista_proveedores():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM proveedores")
    proveedores = cur.fetchall()
    cur.close(); conn.close()
    return render_template('vehiculos/proveedores/lista_proveedores.html', proveedores=proveedores)

@app.route('/proveedores/registrar', methods=['GET','POST'])
@login_required
@permission_required('create')
def registrar_proveedor():
    if request.method == 'POST':
        datos = tuple(request.form[f] for f in [
          'nombre','titular','numero_cuenta','banco',
          'direccion','swift','numero_ruta'
        ])
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()
        cur.execute("""
          INSERT INTO proveedores
          (nombre,titular,numero_cuenta,banco,direccion,swift,numero_ruta)
          VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, datos)
        conn.commit(); cur.close(); conn.close()
        flash('Proveedor creado correctamente','success')
        return redirect(url_for('lista_proveedores'))
    return render_template('vehiculos/proveedores/registrar_proveedor.html')

@app.route('/proveedores/editar/<int:proveedor_id>', methods=['GET','POST'])
@login_required
@permission_required('edit')
def editar_proveedor(proveedor_id):
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    if request.method == 'POST':
        datos = tuple(request.form[f] for f in [
          'nombre','titular','numero_cuenta','banco',
          'direccion','swift','numero_ruta'
        ]) + (proveedor_id,)
        cur.execute("""
          UPDATE proveedores SET
            nombre=%s,titular=%s,numero_cuenta=%s,
            banco=%s,direccion=%s,swift=%s,numero_ruta=%s
          WHERE id=%s
        """, datos)
        conn.commit(); cur.close(); conn.close()
        flash('Proveedor modificado','success')
        return redirect(url_for('lista_proveedores'))

    cur.execute("SELECT * FROM proveedores WHERE id=%s", (proveedor_id,))
    proveedor = cur.fetchone()
    cur.close(); conn.close()
    if not proveedor: abort(404)
    return render_template('vehiculos/proveedores/editar_proveedor.html', proveedor=proveedor)

@app.route('/proveedores/borrar/<int:proveedor_id>', methods=['POST'])
@login_required
@permission_required('delete')
def borrar_proveedor(proveedor_id):
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("DELETE FROM proveedores WHERE id=%s", (proveedor_id,))
    conn.commit(); cur.close(); conn.close()
    flash('Proveedor eliminado','success')
    return redirect(url_for('lista_proveedores'))

# ----------------------------------------
# AUTOS
@app.route('/autos')
@login_required
def lista_autos():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT a.*, p.nombre AS proveedor
                   FROM autos a LEFT JOIN proveedores p
                   ON a.proveedor_id=p.id""")
    autos = cur.fetchall()
    cur.close(); conn.close()
    return render_template('vehiculos/autos/lista_autos.html', autos=autos)

@app.route('/autos/registrar', methods=['GET','POST'])
@login_required
@permission_required('create')
def registrar_auto():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id,nombre FROM proveedores"); proveedores = cur.fetchall()
    if request.method == 'POST':
        datos = (
          request.form['vin'],request.form['marca'],
          request.form['modelo'],request.form['año'],
          request.form['proveedor']
        )
        cur.execute("""
          INSERT INTO autos(vin,marca,modelo,año,proveedor_id)
          VALUES(%s,%s,%s,%s,%s)
        """, datos)
        conn.commit(); cur.close(); conn.close()
        flash('Auto guardado','success')
        return redirect(url_for('lista_autos'))
    cur.close(); conn.close()
    return render_template('vehiculos/autos/registrar_auto.html', proveedores=proveedores)

@app.route('/autos/editar/<int:auto_id>', methods=['GET','POST'])
@login_required
@permission_required('edit')
def editar_auto(auto_id):
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)

    if request.method == 'POST':
        datos = (
            request.form['vin'],
            request.form['marca'],
            request.form['modelo'],
            request.form['año'],
            request.form['proveedor'],
            auto_id
        )
        cur.execute("""
            UPDATE autos SET
              vin=%s, marca=%s, modelo=%s, año=%s, proveedor_id=%s
            WHERE id=%s
        """, datos + (auto_id,))
        conn.commit()
        cur.close(); conn.close()
        flash('Auto modificado correctamente', 'success')
        return redirect(url_for('lista_autos'))

    cur.execute("SELECT * FROM autos WHERE id=%s", (auto_id,))
    auto = cur.fetchone()
    cur.close(); conn.close()
    if not auto:
        abort(404)

    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id, nombre FROM proveedores")
    proveedores = cur.fetchall()
    cur.close(); conn.close()

    return render_template(
      'vehiculos/autos/editar_auto.html',
      auto=auto,
      proveedores=proveedores
    )

@app.route('/autos/borrar/<int:auto_id>', methods=['POST'])
@login_required
@permission_required('delete')
def borrar_auto(auto_id):
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("DELETE FROM autos WHERE id=%s", (auto_id,))
    conn.commit(); cur.close(); conn.close()
    flash('Auto eliminado','success')
    return redirect(url_for('lista_autos'))

# ----------------------------------------
# CLIENTES
@app.route('/clientes')
@login_required
def lista_clientes():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM clientes"); clientes = cur.fetchall()
    cur.close(); conn.close()
    return render_template('vehiculos/clientes/lista_clientes.html', clientes=clientes)

@app.route('/clientes/registrar', methods=['GET','POST'])
@login_required
@permission_required('create')
def registrar_cliente():
    if request.method == 'POST':
        datos = tuple(request.form[f] for f in [
          'cliente_cuba','cliente_usa','pn','mpm','estado',
          'conf_accordia','dr','estado_documentacion',
          'expediente','vin','marca','modelo'
        ])
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()
        placeholders = ','.join(['%s']*len(datos))
        sql = f"INSERT INTO clientes ({','.join([f for f,_ in []])}) VALUES ({placeholders})"
        # Ajusta el SQL con tus campos
        cur.execute(sql, datos)
        conn.commit(); cur.close(); conn.close()
        flash('Cliente creado','success')
        return redirect(url_for('lista_clientes'))
    return render_template('vehiculos/clientes/registrar_cliente.html')

@app.route('/clientes/editar/<int:cliente_id>', methods=['GET','POST'])
@login_required
@permission_required('edit')
def editar_cliente(cliente_id):
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    if request.method == 'POST':
        datos = (
          request.form['cliente_cuba'],request.form['cliente_usa'],
          request.form['pn'],request.form['mpm'],request.form['estado'],
          request.form['conf_accordia'],request.form['dr'],
          request.form['estado_documentacion'],request.form['expediente'],
          request.form['vin'],request.form['marca'],request.form['modelo'],
          cliente_id
        )
        cur.execute("""
          UPDATE clientes SET
            cliente_cuba=%s,cliente_usa=%s,pn=%s,mpm=%s,estado=%s,
            conf_accordia=%s,dr=%s,estado_documentacion=%s,
            expediente=%s,vin=%s,marca=%s,modelo=%s
          WHERE id=%s
        """, datos)
        conn.commit(); cur.close(); conn.close()
        flash('Cliente modificado','success')
        return redirect(url_for('lista_clientes'))

    cur.execute("SELECT * FROM clientes WHERE id=%s", (cliente_id,))
    cliente = cur.fetchone()
    cur.close(); conn.close()
    if not cliente: abort(404)
    return render_template('vehiculos/clientes/editar_cliente.html', cliente=cliente)

@app.route('/clientes/borrar/<int:cliente_id>', methods=['POST'])
@login_required
@permission_required('delete')
def borrar_cliente(cliente_id):
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("DELETE FROM autos WHERE id=%s", (cliente_id,))
    conn.commit(); cur.close(); conn.close()
    flash('cliente eliminado','success')
    return redirect(url_for('lista_clientes'))

# ----------------------------------------
# ÓRDENES
@app.route('/ordenes')
@login_required
def lista_ordenes():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT o.*,c.cliente_cuba,a.vin
                   FROM ordenes o
                   JOIN clientes c ON o.cliente_id=c.id
                   JOIN autos a ON o.auto_id=a.id""")
    ordenes = cur.fetchall()
    cur.close(); conn.close()
    return render_template('vehiculos/ordenes/lista_ordenes.html', ordenes=ordenes)

@app.route('/ordenes/registrar', methods=['GET','POST'])
@login_required
@permission_required('create')
def registrar_orden():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id,cliente_cuba FROM clientes"); clientes = cur.fetchall()
    cur.execute("SELECT id,vin,marca,modelo FROM autos");        autos     = cur.fetchall()
    cur.execute("SELECT id,nombre FROM usuarios");               usuarios  = cur.fetchall()
    if request.method == 'POST':
        datos = (
          request.form['cliente_id'],request.form['auto_id'],
          request.form['usuario_id'],request.form['estado'],
          request.form['total']
        )
        cur.execute("""
          INSERT INTO ordenes(cliente_id,auto_id,usuario_id,estado,total)
          VALUES(%s,%s,%s,%s,%s)
        """, datos)
        conn.commit(); cur.close(); conn.close()
        flash('Orden creada','success')
        return redirect(url_for('lista_ordenes'))
    cur.close(); conn.close()
    return render_template('vehiculos/ordenes/registrar_orden.html',
                           clientes=clientes, autos=autos, usuarios=usuarios)

if __name__ == '__main__':
    app.run(debug=True)
