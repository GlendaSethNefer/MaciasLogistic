from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from models import db, User, Role

# ----------------------------------------------------------------
# 1) Vista base que comprueba sesión y rol 'admin'
# ----------------------------------------------------------------
class SecuredModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.has_role('admin')

    def inaccessible_callback(self, name, **kwargs):
        # redirige a login
        return self.render('login.html')

class MyAdminIndex(AdminIndexView):
    @expose('/')
    def index(self):
        if not (current_user.is_authenticated and current_user.has_role('admin')):
            return self.render('login.html')
        return super().index()

# ----------------------------------------------------------------
# 2) Inicialización del panel
# ----------------------------------------------------------------
def init_app(app):
    admin = Admin(
        app,
        name='AutoGest Admin',
        index_view=MyAdminIndex(),
        template_mode='bootstrap4'
    )
    # Añadimos los modelos
    admin.add_view(SecuredModelView(User, db.session,      category='Usuarios'))
    admin.add_view(SecuredModelView(Role, db.session,      category='Usuarios'))
    # Si quisieras ver/edit Proveedores, Autos, Clientes, órdenes:
    # from models import Proveedor, Auto, Cliente, Orden
    # admin.add_view(SecuredModelView(Proveedor, db.session, category='Datos'))
    # admin.add_view(SecuredModelView(Auto, db.session,      category='Datos'))
    # admin.add_view(SecuredModelView(Cliente, db.session,   category='Datos'))
    # admin.add_view(SecuredModelView(Orden, db.session,     category='Datos'))
