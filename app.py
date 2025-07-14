from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, abort, get_flashed_messages
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
import json

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

#---------------------------------------------
# Sincronizacion en la base de datos
#exportacion
@app.route('/sync/export/clientes', methods=['GET'])
@login_required
def export_clientes():
    since = request.args.get('since')
    if not since:
        return jsonify({ 'error': 'se requiere parámetro since' }), 400

    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
      SELECT * FROM clientes
      WHERE updated_at >= %s
    """, (since,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)

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

@app.route('/proveedores/registrar', methods=['GET', 'POST'])
@login_required
@permission_required('create')
def registrar_proveedor():
    if request.method == 'POST':
        data = (
            request.form['nombre'],
            request.form['oferta'],
            request.form['millas'],
            request.form['precio_vehiculo'],
            request.form['precio_oferta'],
            request.form['gama'],
            request.form['impuesto'],
            request.form['acreditacion'],
            request.form['observaciones']
        )
        conn = mysql.connector.connect(**db_config)
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO proveedores
              (nombre, oferta, millas, precio_vehiculo,
               precio_oferta, gama, impuesto,
               acreditacion, observaciones)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, data)
        conn.commit()
        cur.close()
        conn.close()
        flash('Proveedor creado correctamente', 'success')
        return redirect(url_for('lista_proveedores'))

    return render_template('vehiculos/proveedores/registrar_proveedor.html')

@app.route('/proveedores/editar/<int:proveedor_id>', methods=['GET', 'POST'])
@login_required
@permission_required('edit')
def editar_proveedor(proveedor_id):
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)

    if request.method == 'POST':
        data = (
            request.form['nombre'],
            request.form['oferta'],
            request.form['millas'],
            request.form['precio_vehiculo'],
            request.form['precio_oferta'],
            request.form['gama'],
            request.form['impuesto'],
            request.form['acreditacion'],
            request.form['observaciones'],
            proveedor_id
        )
        cur.execute("""
            UPDATE proveedores SET
              nombre=%s,
              oferta=%s,
              millas=%s,
              precio_vehiculo=%s,
              precio_oferta=%s,
              gama=%s,
              impuesto=%s,
              acreditacion=%s,
              observaciones=%s
            WHERE id=%s
        """, data)
        conn.commit()
        cur.close()
        conn.close()
        flash('Proveedor modificado correctamente', 'success')
        return redirect(url_for('lista_proveedores'))

    # GET → obtener datos existentes
    cur.execute("SELECT * FROM proveedores WHERE id=%s", (proveedor_id,))
    proveedor = cur.fetchone()
    cur.close()
    conn.close()

    if not proveedor:
        abort(404)

    return render_template(
        'vehiculos/proveedores/editar_proveedor.html',
        proveedor=proveedor
    )


@app.route('/proveedores/borrar/<int:proveedor_id>', methods=['POST'])
@login_required
@permission_required('delete')
def borrar_proveedor(proveedor_id):
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("DELETE FROM proveedores WHERE id=%s", (proveedor_id,))
    conn.commit(); cur.close(); conn.close()
    flash('Importación eliminada','success')
    return redirect(url_for('lista_proveedores'))

# ----------------------------------------
# AUTOS
@app.route('/autos')
@login_required
def lista_autos():
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM autos")
    autos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
        'vehiculos/autos/lista_autos.html',
        autos=autos
    )

# Registrar Auto
@app.route('/autos/registrar', methods=['GET', 'POST'])
@login_required
@permission_required('create')
def registrar_auto():
    if request.method == 'POST':
        datos = (
            request.form['nombre_cliente'],
            request.form['dr'],
            request.form['vin'],
            request.form['marca'],
            request.form['modelo'],
            request.form['año'],
            request.form['millas'],
            request.form['licencia'],
            request.form['importadora'],
            request.form['ent_puerto'],
            request.form['tit_enviado'],
            request.form['bill_of_sale'],
            request.form['sed'],
            request.form['estado'],
            request.form['accordia'],
            request.form['fecha_salida'],
            request.form['observaciones']
        )
        sql = """
          INSERT INTO autos
            (nombre_cliente, dr, vin, marca, modelo, año,
             millas, licencia, importadora, ent_puerto,
             tit_enviado, bill_of_sale, sed, estado,
             accordia, fecha_salida, observaciones)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        conn = mysql.connector.connect(**db_config)
        cur  = conn.cursor()
        cur.execute(sql, datos)
        conn.commit()
        cur.close()
        conn.close()

        flash('Auto registrado correctamente', 'success')
        return redirect(url_for('lista_autos'))

    return render_template('vehiculos/autos/registrar_auto.html')

# ------------------------------------------------
# Editar Auto
@app.route('/autos/editar/<int:auto_id>', methods=['GET', 'POST'])
@login_required
@permission_required('edit')
def editar_auto(auto_id):
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)

    if request.method == 'POST':
        datos = (
            request.form['nombre_cliente'],
            request.form['dr'],
            request.form['vin'],
            request.form['marca'],
            request.form['modelo'],
            request.form['año'],
            request.form['millas'],
            request.form['licencia'],
            request.form['importadora'],
            request.form['ent_puerto'],
            request.form['tit_enviado'],
            request.form['bill_of_sale'],
            request.form['sed'],
            request.form['estado'],
            request.form['accordia'],
            request.form['fecha_salida'],
            request.form['observaciones'],
            auto_id
        )
        sql = """
          UPDATE autos SET
            nombre_cliente=%s,
            dr=%s,
            vin=%s,
            marca=%s,
            modelo=%s,
            año=%s,
            millas=%s,
            licencia=%s,
            importadora=%s,
            ent_puerto=%s,
            tit_enviado=%s,
            bill_of_sale=%s,
            sed=%s,
            estado=%s,
            accordia=%s,
            fecha_salida=%s,
            observaciones=%s
          WHERE id=%s
        """
        cur.execute(sql, datos)
        conn.commit()
        cur.close()
        conn.close()

        flash('Auto modificado correctamente', 'success')
        return redirect(url_for('lista_autos'))

    # GET → cargar datos existentes
    cur.execute("SELECT * FROM autos WHERE id=%s", (auto_id,))
    auto = cur.fetchone()
    cur.close()
    conn.close()

    if not auto:
        abort(404)

    return render_template(
        'vehiculos/autos/editar_auto.html',
        auto=auto
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
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM clientes")
    clientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('vehiculos/clientes/lista_clientes.html', clientes=clientes)


@app.route('/clientes/registrar', methods=['GET', 'POST'])
@login_required
@permission_required('create')
def registrar_cliente():
    if request.method == 'POST':
        datos = (
            new_uuid, 
            request.form['cuba'],
            request.form['usa'],
            request.form['t_persona'],
            request.form['num_envio'],
            request.form['estado_doc'],
            request.form['acreditacion'],
            request.form['expediente'],
            request.form['vin'],
            request.form['ubicacion'],
            int(request.form.get('pagado', 0)),
            request.form['referencia'],
            request.form['observaciones']
        )
        sql = """
          INSERT INTO clientes
            (uuid, cuba, usa, t_persona, num_envio,
             estado_doc, acreditacion, expediente,
             vin, ubicacion, pagado,
             referencia, observaciones)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        conn = mysql.connector.connect(**db_config)
        cur  = conn.cursor()
        cur.execute(sql, datos)
        conn.commit()
        cur.close()
        conn.close()
        flash('Cliente registrado correctamente', 'success')
        return redirect(url_for('lista_clientes'))

    return render_template('vehiculos/clientes/registrar_cliente.html')


@app.route('/clientes/editar/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
@permission_required('edit')
def editar_cliente(cliente_id):
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)

    if request.method == 'POST':
        datos = (
            request.form['cuba'],
            request.form['usa'],
            request.form['t_persona'],
            request.form['num_envio'],
            request.form['estado_doc'],
            request.form['acreditacion'],
            request.form['expediente'],
            request.form['vin'],
            request.form['ubicacion'],
            int(request.form.get('pagado', 0)),
            request.form['referencia'],
            request.form['observaciones'],
            cliente_id
        )
        sql = """
          UPDATE clientes SET
            cuba=%s, usa=%s, t_persona=%s, num_envio=%s,
            estado_doc=%s, acreditacion=%s, expediente=%s,
            vin=%s, ubicacion=%s, pagado=%s,
            referencia=%s, observaciones=%s
          WHERE id=%s
        """
        cur.execute(sql, datos)
        conn.commit()
        cur.close()
        conn.close()
        flash('Cliente modificado correctamente', 'success')
        return redirect(url_for('lista_clientes'))

    # GET → carga datos existentes
    cur.execute("SELECT * FROM clientes WHERE id=%s", (cliente_id,))
    cliente = cur.fetchone()
    cur.close()
    conn.close()
    if not cliente:
        abort(404)

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
#RUTAS PARA ÓRDENES
# -------------------------------

@app.route('/ordenes')
@login_required
def lista_ordenes():
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)
    # Traemos los campos que quieres mostrar, haciendo JOIN con usuarios y clientes
    cur.execute("""
      SELECT
        o.id,
        c.cuba    AS cliente_cuba,
        o.vin,
        u.nombre AS nombre_usuario,
        o.fecha,
        o.estado,
        o.procesados AS total
      FROM ordenes o
      JOIN usuarios u  ON o.usuario_id  = u.id
      JOIN clientes c ON o.cliente_id  = c.id
      ORDER BY o.fecha DESC
    """)
    ordenes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('vehiculos/ordenes/lista_ordenes.html', ordenes=ordenes)


@app.route('/ordenes/registrar', methods=['GET', 'POST'])
@login_required
@permission_required('create')
def registrar_orden():
    if request.method == 'POST':
        datos = (
            current_user.id,
            request.form['cliente_id'],
            request.form['vin'],
            request.form.get('expediente_id') or None,
            request.form['estado'],
            int(request.form.get('procesados', 0)),
            request.form.get('observaciones'),
            datetime.utcnow()
        )
        sql = """
          INSERT INTO ordenes
            (usuario_id, cliente_id, vin, expediente_id,
             estado, procesados, observaciones, fecha)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """
        conn = mysql.connector.connect(**db_config)
        cur  = conn.cursor()
        cur.execute(sql, datos)
        conn.commit()
        cur.close()
        conn.close()
        flash('Orden registrada correctamente', 'success')
        return redirect(url_for('lista_ordenes'))

    # Si es GET, necesitamos lista de clientes para el select
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id, cuba FROM clientes ORDER BY cuba")
    clientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
      'vehiculos/ordenes/registrar_orden.html',
      clientes=clientes
    )


@app.route('/ordenes/editar/<int:orden_id>', methods=['GET', 'POST'])
@login_required
@permission_required('edit')
def editar_orden(orden_id):
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor(dictionary=True)

    if request.method == 'POST':
        datos = (
            request.form['cliente_id'],
            request.form['vin'],
            request.form.get('expediente_id') or None,
            request.form['estado'],
            int(request.form.get('procesados', 0)),
            request.form.get('observaciones'),
            orden_id
        )
        sql = """
          UPDATE ordenes SET
            cliente_id=%s, vin=%s, expediente_id=%s,
            estado=%s, procesados=%s, observaciones=%s
          WHERE id=%s
        """
        cur.execute(sql, datos)
        conn.commit()
        cur.close()
        conn.close()
        flash('Orden modificada correctamente', 'success')
        return redirect(url_for('lista_ordenes'))

    # GET → cargo datos existentes
    cur.execute("SELECT * FROM ordenes WHERE id=%s", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        cur.close()
        conn.close()
        abort(404)

    # también necesito clientes para el select
    cur.execute("SELECT id, cuba FROM clientes ORDER BY cuba")
    clientes = cur.fetchall()

    cur.close()
    conn.close()
    return render_template(
      'vehiculos/ordenes/editar_orden.html',
      orden=orden,
      clientes=clientes
    )


@app.route('/ordenes/borrar/<int:orden_id>', methods=['POST'])
@login_required
@permission_required('delete')
def borrar_orden(orden_id):
    conn = mysql.connector.connect(**db_config)
    cur  = conn.cursor()
    cur.execute("DELETE FROM ordenes WHERE id=%s", (orden_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Orden eliminada', 'success')
    return redirect(url_for('lista_ordenes'))



if __name__ == '__main__':
    app.run(debug=True)
