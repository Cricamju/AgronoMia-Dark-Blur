from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import re
from xhtml2pdf import pisa
import io
from flask import send_file
from flask_mail import Mail, Message
from sqlalchemy.sql import exists
from flask_login import login_required, current_user
from sqlalchemy import and_, not_, exists
from sqlalchemy.orm import aliased
import pandas as pd


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://dava:exoastro3@localhost/agronomia'
app.secret_key = 'clave_secreta_super_segura' 
db = SQLAlchemy(app)
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'moviitiz.tec@gmail.com')  # Usa valor por defecto si no hay .env
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'iryz gjiw olni ycgo')  # Usa valor por defecto si no hay .env
app.config['MAIL_DEFAULT_SENDER'] = 'moviitiz.tec@gmail.com'
mail = Mail(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tipo_usuario = db.Column(db.String(50), nullable=False) 
    direcciones = db.relationship('Direccion', backref='usuario', lazy=True)
    pedidos = db.relationship('Pedido', backref='usuario', lazy=True)
    contacto = db.relationship('Contacto', backref='usuario', lazy=True)
    pagos = db.relationship('Pago', backref='usuario', lazy=True)

class Administrador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  

class Productor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text, nullable=True) 
    ubicacion = db.Column(db.String(200), nullable=True)
    imagen = db.Column(db.String(200), nullable=True)
    publicado = db.Column(db.Boolean, default=False, nullable=False)

    productos = db.relationship('Producto', back_populates='productor')

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    productor_id = db.Column(db.Integer, db.ForeignKey('productor.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    tiempo_germinacion = db.Column(db.Integer)  # Nuevo campo para semillas
    epoca_siembra = db.Column(db.String(100))   # Nuevo campo para semillas
    cantidad_semillas = db.Column(db.Integer)   # Nuevo campo para semillas
    productor = db.relationship('Productor', back_populates='productos')  
    categoria = db.relationship('Categoria', back_populates='productos')


class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    productos = db.relationship('Producto', back_populates='categoria')


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', name="fk_pedido_usuario"), nullable=False)
    total = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    estado = db.Column(db.String(50), default="Pendiente")  
    



class Carrito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    producto = db.relationship('Producto')

class Contacto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    respuesta = db.Column(db.Text)

class Direccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)

class MetodoPago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)  

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', name="fk_pago_usuario"), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id', name="fk_pago_pedido"), nullable=False)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey('metodo_pago.id', name="fk_pago_metodo"), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    estado = db.Column(db.String(50), default="Completado")

def crear_admin():
    with app.app_context():  
        admin_existente = Administrador.query.filter_by(email="admin@agronomia.com").first()
        if not admin_existente:
            nuevo_admin = Administrador(nombre="Admin", email="admin@agronomia.com", password="securepassword")
            db.session.add(nuevo_admin)
            db.session.commit()

class PedidoItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    producto = db.relationship('Producto')
    pedido = db.relationship('Pedido', backref='items')


class Tarjeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    numero = db.Column(db.String(16), nullable=False)
    propietario = db.Column(db.String(100), nullable=False)
    fecha_expiracion = db.Column(db.String(5), nullable=False)


@app.route('/')
def inicio():
    cantidad_carrito = 0
    if 'usuario_id' in session and session.get('tipo_usuario') == 'Cliente':
        cantidad_carrito = db.session.query(db.func.sum(Carrito.cantidad)).filter_by(usuario_id=session['usuario_id']).scalar() or 0
    return render_template('inicio.html', cantidad_carrito=cantidad_carrito)


@app.route('/semillas')
def semillas():
    categoria_id = request.args.get('categoria_id')
    if categoria_id:
        productos = Producto.query.filter_by(categoria_id=categoria_id, activo=True).all()
    else:
        productos = Producto.query.filter_by(activo=True).all()
    
    categorias = Categoria.query.all()
    cantidad_carrito = 0
    if 'usuario_id' in session and session.get('tipo_usuario') == 'Cliente':
        cantidad_carrito = db.session.query(db.func.sum(Carrito.cantidad)).filter_by(usuario_id=session['usuario_id']).scalar() or 0
    
    return render_template('semillas.html', productos=productos, categorias=categorias, cantidad_carrito=cantidad_carrito)

@app.route('/productos')
def productos():
    productos = Producto.query.filter_by(activo=True).all()
    categorias = Categoria.query.all()
    cantidad_carrito = 0
    if 'usuario_id' in session and session.get('tipo_usuario') == 'Cliente':
        cantidad_carrito = db.session.query(db.func.sum(Carrito.cantidad)).filter_by(usuario_id=session['usuario_id']).scalar() or 0
    return render_template('productos.html', productos=productos, categorias=categorias, cantidad_carrito=cantidad_carrito)

@app.route('/contacto')
def contacto():
    cantidad_carrito = 0
    if 'usuario_id' in session and session.get('tipo_usuario') == 'Cliente':
        cantidad_carrito = db.session.query(db.func.sum(Carrito.cantidad)).filter_by(usuario_id=session['usuario_id']).scalar() or 0
    return render_template('contacto.html', cantidad_carrito=cantidad_carrito)


@app.route('/enviar_mensaje', methods=['POST'])
def enviar_mensaje():
    if 'usuario_id' not in session:
        return redirect(url_for('login')) 
    nombre = request.form['nombre']
    email = request.form['email']
    mensaje = request.form['mensaje']

    nuevo_mensaje = Contacto(usuario_id=session['usuario_id'], mensaje=mensaje)
    db.session.add(nuevo_mensaje)
    db.session.commit()

    flash("Tu mensaje fue enviado con éxito.", "success")
    return redirect(url_for('contacto'))



@app.route('/productores')
def productores():
    lista_productores = Productor.query.filter_by(publicado=True).all()
    return render_template('productores.html', productores=lista_productores)


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':  
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        tipo_usuario = "Cliente" 

        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{8,}$", password):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un carácter especial.", "error")
            return redirect(url_for('registro'))  

        if Usuario.query.filter_by(email=email).first():
            return render_template('registro.html', correo_duplicado=True, nombre=nombre, email=email)

        try:
            nuevo_usuario = Usuario(nombre=nombre, email=email, password=password, tipo_usuario=tipo_usuario)
            db.session.add(nuevo_usuario)
            db.session.commit()

            return render_template('registro.html', registro_exitoso=True)
        except Exception as e:
            db.session.rollback()
            return render_template('registro.html', registro_fallido=True)

    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email'].strip().lower() 
        password = request.form['password']


        admin = Administrador.query.filter_by(email=email, password=password).first()
        if admin:
            session['usuario_id'] = admin.id
            session['usuario_nombre'] = admin.nombre
            session['tipo_usuario'] = "Administrador"
            return redirect(url_for('panel_admin'))

        usuario = Usuario.query.filter_by(email=email, password=password).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['usuario_nombre'] = usuario.nombre
            session['tipo_usuario'] = usuario.tipo_usuario
            if usuario.tipo_usuario == "Cliente":
                return redirect(url_for('panel_cliente'))
            elif usuario.tipo_usuario == "Productor":
                productor = Productor.query.filter_by(email=usuario.email).first()
                if productor:
                    session['productor_id'] = productor.id
                    return redirect(url_for('panel_productor'))
                else:
                    flash("❌ No se encontró el productor asociado a este usuario.", "error")
                    return redirect(url_for('inicio'))
        
        error = "Correo o contraseña incorrectos"
    return render_template('login.html', error=error)
 

@app.route('/panel_cliente')
def panel_cliente():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    direccion = Direccion.query.filter_by(usuario_id=session['usuario_id']).first()
    cantidad_carrito = db.session.query(db.func.sum(Carrito.cantidad)).filter_by(usuario_id=session['usuario_id']).scalar() or 0
    tarjetas = Tarjeta.query.filter_by(usuario_id=session['usuario_id']).all()
    return render_template('panel_cliente.html', usuario=usuario, direccion=direccion, cantidad_carrito=cantidad_carrito, tarjetas=tarjetas)


@app.route('/perfil_cliente')
def perfil_cliente():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('perfil_cliente.html', usuario=usuario)


@app.route('/panel_productor')
def panel_productor():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Productor':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    productor_id = session.get('productor_id')

    
    total_pedidos = Pedido.query.join(PedidoItem).join(Producto).filter(Producto.productor_id == productor_id).distinct(Pedido.id).count()
    total_productos = db.session.query(db.func.sum(PedidoItem.cantidad)).join(Producto).filter(Producto.productor_id == productor_id).scalar() or 0
    total_ingresos = db.session.query(db.func.sum(PedidoItem.cantidad * Producto.precio)).join(Producto).filter(Producto.productor_id == productor_id).scalar() or 0

   
    from sqlalchemy import extract, func
    import calendar
    from datetime import datetime, timedelta

    hoy = datetime.today()
    ventas_labels = []
    ventas_data = []

    for i in range(5, -1, -1): 
        mes = (hoy.month - i - 1) % 12 + 1
        anio = hoy.year if hoy.month - i > 0 else hoy.year - 1
        nombre_mes = calendar.month_abbr[mes].capitalize()
        ventas_labels.append(f"{nombre_mes} {anio}")

        suma_mes = db.session.query(
            func.coalesce(func.sum(PedidoItem.cantidad * Producto.precio), 0)
        ).join(Producto).join(Pedido).filter(
            Producto.productor_id == productor_id,
            extract('month', Pedido.fecha) == mes,
            extract('year', Pedido.fecha) == anio
        ).scalar() or 0

        ventas_data.append(float(suma_mes))

    return render_template(
        'panel_productor.html',
        usuario=usuario,
        total_pedidos=total_pedidos,
        total_productos=total_productos,
        total_ingresos=total_ingresos,
        ventas_labels=ventas_labels,
        ventas_data=ventas_data
    )

@app.route('/panel_admin')
def panel_admin():
    q = request.args.get('q', '').strip()
    filtro = request.args.get('filtro', '')

    total_usuarios = Usuario.query.count()
    pedidos_activos = Pedido.query.filter(Pedido.estado != 'Entregado').count()
    total_productos = Producto.query.count()
    mensajes_pendientes = Contacto.query.filter(Contacto.respuesta == None).count()

    resultados = []
    if q:
        if filtro == "usuarios":
            resultados = Usuario.query.filter(
                (Usuario.nombre.ilike(f"%{q}%")) | (Usuario.email.ilike(f"%{q}%"))
            ).all()
        elif filtro == "pedidos":
            resultados = Pedido.query.join(Usuario).filter(
                (Pedido.id == q) |
                (Usuario.nombre.ilike(f"%{q}%")) |
                (Pedido.estado.ilike(f"%{q}%"))
            ).all()
        elif filtro == "productos":
            resultados = Producto.query.filter(
                (Producto.nombre.ilike(f"%{q}%")) |
                (Producto.descripcion.ilike(f"%{q}%"))
            ).all()
        else:
            usuarios = Usuario.query.filter(
                (Usuario.nombre.ilike(f"%{q}%")) | (Usuario.email.ilike(f"%{q}%"))
            ).all()
            pedidos = Pedido.query.join(Usuario).filter(
                (Pedido.id == q) |
                (Usuario.nombre.ilike(f"%{q}%")) |
                (Pedido.estado.ilike(f"%{q}%"))
            ).all()
            productos = Producto.query.filter(
                (Producto.nombre.ilike(f"%{q}%")) |
                (Producto.descripcion.ilike(f"%{q}%"))
            ).all()
            resultados = usuarios + pedidos + productos

    return render_template(
        'panel_admin.html',
        total_usuarios=total_usuarios,
        pedidos_activos=pedidos_activos,
        total_productos=total_productos,
        mensajes_pendientes=mensajes_pendientes,
        resultados=resultados,
        q=q,
        filtro=filtro
    )

@app.route('/exportar_reporte')
def exportar_reporte():
    tipo = request.args.get('tipo')
    if not tipo:
        return "<h2 style='color:#c62828;text-align:center;margin-top:40px;'>Debes especificar el tipo de reporte (usuarios, pedidos o productos).</h2>", 400

    output = io.BytesIO()

    if tipo == 'usuarios':
        usuarios = Usuario.query.all()
        data = [{
            'ID': u.id,
            'Nombre': u.nombre,
            'Email': u.email,
            'Tipo de usuario': u.tipo_usuario
        } for u in usuarios]
        df = pd.DataFrame(data)
        filename = "usuarios.xlsx"

    elif tipo == 'pedidos':
        pedidos = Pedido.query.all()
        data = [{
            'ID': p.id,
            'Usuario': p.usuario_id,
            'Total': p.total,
            'Estado': p.estado,
            'Fecha': p.fecha.strftime('%d/%m/%Y %H:%M')
        } for p in pedidos]
        df = pd.DataFrame(data)
        filename = "pedidos.xlsx"

    elif tipo == 'productos':
        productos = Producto.query.all()
        data = [{
            'ID': prod.id,
            'Nombre': prod.nombre,
            'Descripción': prod.descripcion,
            'Precio': prod.precio,
            'Productor': prod.productor_id,
            'Categoría': prod.categoria_id,
            'Activo': prod.activo
        } for prod in productos]
        df = pd.DataFrame(data)
        filename = "productos.xlsx"

    else:
        return "<h2 style='color:#c62828;text-align:center;margin-top:40px;'>Tipo de reporte no válido.</h2>", 400

    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('inicio'))


@app.route('/carrito')
def carrito():
    if 'usuario_id' not in session:
        flash("⚠️ Debes iniciar sesión para ver tu carrito.", "error")
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    carrito_items = Carrito.query.filter_by(usuario_id=usuario_id).all()
    productos_en_carrito = []
    total = 0

    for item in carrito_items:
        producto = Producto.query.get(item.producto_id)
        if producto:
            producto.cantidad = item.cantidad  
            productos_en_carrito.append(producto)
            total += producto.precio * item.cantidad

    return render_template('carrito.html', productos=productos_en_carrito, total=total)


def calcular_total_carrito(usuario_id):
    carrito_items = Carrito.query.filter_by(usuario_id=usuario_id).all()
    if not carrito_items:
        return 0  
    total = sum(item.producto.precio * item.cantidad for item in carrito_items)
    return total

@app.route('/pago', methods=['GET', 'POST'])
def pago():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    tarjetas = Tarjeta.query.filter_by(usuario_id=usuario_id).all()
    carrito_items = Carrito.query.filter_by(usuario_id=usuario_id).all()
    productos = []
    total = 0

    for item in carrito_items:
        producto = Producto.query.get(item.producto_id)
        if producto:
            producto.cantidad = item.cantidad
            productos.append(producto)
            total += producto.precio * item.cantidad

    if request.method == 'POST':
        tarjeta_id = request.form.get('tarjeta_guardada')
        if tarjeta_id:
        
            tarjeta = Tarjeta.query.get(int(tarjeta_id))
            nombre = request.form['nombre']
            correo = request.form['correo']
            direccion = request.form['direccion']
            numero_tarjeta = tarjeta.numero
            propietario = tarjeta.propietario
            fecha_expiracion = tarjeta.fecha_expiracion
            
        else:
            
            nombre = request.form['nombre']
            correo = request.form['correo']
            direccion = request.form['direccion']
            numero_tarjeta = request.form['numero_tarjeta']
            propietario = request.form['propietario']
            fecha_expiracion = request.form['fecha_expiracion']
            cvv = request.form['cvv']

            
            tarjeta_existente = Tarjeta.query.filter_by(
                usuario_id=usuario_id,
                numero=numero_tarjeta
            ).first()
            if not tarjeta_existente:
                nueva_tarjeta = Tarjeta(
                    usuario_id=usuario_id,
                    numero=numero_tarjeta,
                    propietario=propietario,
                    fecha_expiracion=fecha_expiracion
                )
                db.session.add(nueva_tarjeta)
                db.session.commit()

        
        nuevo_pedido = Pedido(usuario_id=usuario_id, total=total, estado="Pendiente")
        db.session.add(nuevo_pedido)
        db.session.commit()

        
        for item in carrito_items:
            pedido_item = PedidoItem(
                pedido_id=nuevo_pedido.id,
                producto_id=item.producto_id,
                cantidad=item.cantidad
            )
            db.session.add(pedido_item)
        db.session.commit()

       
        Carrito.query.filter_by(usuario_id=usuario_id).delete()
        db.session.commit()

       
        try:
            productos_detalle = ""
            for producto in productos:
                productos_detalle += f"- {producto.nombre} x{producto.cantidad} = ${producto.precio * producto.cantidad:.2f}\n"

            msg = Message(
                'Confirmación de compra - AgronoMia',
                sender='xhencho.taallegas@gmail.com',
                recipients=[correo]
            )
            msg.body = (
                f"Hola {nombre},\n\n"
                f"Tu pago se realizó con éxito. Tu pedido será enviado a:\n{direccion}\n\n"
                f"Detalle de tu compra:\n"
                f"{productos_detalle}\n"
                f"Total pagado: ${total:.2f}\n\n"
                f"¡Gracias por comprar en AgronoMia!"
            )
            mail.send(msg)
        except Exception as e:
            print("No se pudo enviar el correo:", e)

        return render_template('pago.html', nombre=nombre, productos=productos, total=total)

    return render_template('metodos_pago.html', tarjetas=tarjetas, productos=productos, total=total)


@app.route('/historial_pedidos')
def historial_pedidos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    pedidos = Pedido.query.filter_by(usuario_id=session['usuario_id']).order_by(Pedido.fecha.desc()).all()


    return render_template('historial_pedidos.html', pedidos=pedidos)


@app.route('/guardar_perfil', methods=['POST'])
def guardar_perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    usuario = Usuario.query.get(usuario_id)

    usuario.nombre = request.form['nombre']
    usuario.email = request.form['email']

    if request.form['password'].strip():
        usuario.password = request.form['password']

    direccion_existente = Direccion.query.filter_by(usuario_id=usuario_id).first()
    if direccion_existente:
        direccion_existente.direccion = request.form['direccion']
    else:
        nueva_direccion = Direccion(usuario_id=usuario_id, direccion=request.form['direccion'])
        db.session.add(nueva_direccion)

    db.session.commit()

    flash("✔ Cambios guardados correctamente.", "success") 

    return redirect(url_for('perfil_cliente'))


@app.route('/registrar_productor', methods=['POST'])
def registrar_productor():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nombre = request.form['nombre']
    email = request.form['email']
    descripcion = request.form['descripcion']
    ubicacion = request.form['ubicacion']

    imagen = request.files.get('imagen')
    imagen_nombre = None
    if imagen and imagen.filename:
        imagen_nombre = secure_filename(imagen.filename)
        imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], imagen_nombre))

  
    productor = Productor.query.filter_by(email=email).first()
    if productor:
        productor.nombre = nombre
        productor.descripcion = descripcion
        productor.ubicacion = ubicacion
        productor.publicado = True  
        if imagen_nombre:
            productor.imagen = imagen_nombre
        db.session.commit()
        flash("✔ Perfil actualizado correctamente.", "success")
    else:
        nuevo_productor = Productor(
            nombre=nombre,
            email=email,
            descripcion=descripcion,
            ubicacion=ubicacion,
            imagen=imagen_nombre if imagen_nombre else "default.png",
            publicado=True  
        )
        db.session.add(nuevo_productor)
        db.session.commit()
        flash("✔ Perfil creado correctamente.", "success")

    return redirect(url_for('panel_productor'))

@app.route('/pedidos_productor')
def pedidos_productor():
    pedidos = Pedido.query.filter_by(estado="Pendiente").all()
    for pedido in pedidos:
        pedido.cliente_nombre = pedido.usuario.nombre if hasattr(pedido, 'usuario') else 'Cliente'
        pedido.productos_resumen = ', '.join([f"{item.producto.nombre} (x{item.cantidad})" for item in pedido.items])
        
        direccion = Direccion.query.filter_by(usuario_id=pedido.usuario_id).first()
        pedido.direccion_entrega = direccion.direccion if direccion else "No registrada"
    return render_template('pedidos_productor.html', pedidos=pedidos)



def obtener_cantidad_carrito(usuario_id):
    cantidad = db.session.query(db.func.sum(Carrito.cantidad)).filter_by(usuario_id=usuario_id).scalar()
    return cantidad or 0

@app.route('/pedidos_cliente')
def pedidos_cliente():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    pedidos = Pedido.query.filter_by(usuario_id=session['usuario_id']).order_by(Pedido.fecha.desc()).all()
    cantidad_carrito = obtener_cantidad_carrito(session['usuario_id'])
    return render_template('pedidos_cliente.html', pedidos=pedidos, cantidad_carrito=cantidad_carrito)


@app.route('/gestion_usuarios')
def gestion_usuarios():
    usuarios = Usuario.query.all()  
    return render_template('gestion_usuarios.html', usuarios=usuarios)

@app.route('/eliminar_usuario/<int:user_id>', methods=['POST'])
def eliminar_usuario(user_id):
    usuario = Usuario.query.get(user_id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
    return redirect(url_for('gestion_usuarios'))

@app.route('/editar_usuario/<int:user_id>', methods=['POST'])
def editar_usuario(user_id):
    usuario = Usuario.query.get_or_404(user_id)
    usuario.nombre = request.form['nombre']
    usuario.email = request.form['email']
    usuario.password = request.form['password']
    usuario.tipo_usuario = request.form['tipo_usuario']
    db.session.commit()
    flash("Usuario actualizado correctamente.", "success")
    return redirect(url_for('gestion_usuarios'))

@app.route('/admin_pedidos')
def admin_pedidos():
    pedidos = Pedido.query.all()  
    return render_template('admin_pedidos.html', pedidos=pedidos)

@app.route('/admin_productos')
def admin_productos():
    productos = Producto.query.all() 
    return render_template('admin_productos.html', productos=productos)



@app.route('/admin_productos_productor')
def admin_productos_productor():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Productor':
        return redirect(url_for('login'))
    productor_id = session.get('productor_id')
    if not productor_id:
        flash("No se encontró el productor asociado a este usuario.", "error")
        return redirect(url_for('inicio'))
    
   
    productos = Producto.query.filter_by(productor_id=productor_id, activo=True).all()

   
    productos_eliminables = (
        Producto.query
        .filter_by(productor_id=productor_id, activo=True)
        .filter(
            exists().where(
                (PedidoItem.producto_id == Producto.id) &
                (PedidoItem.pedido_id == Pedido.id) &
                (Pedido.estado != 'Entregado')
            )
        )
        .all()
    )

    categorias = Categoria.query.all()
    return render_template(
        'admin_productos_productor.html',
        productos=productos,
        productos_eliminables=productos_eliminables,
        categorias=categorias
    )

@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Productor':
        return redirect(url_for('login'))

    productor_id = session.get('productor_id')
    if not productor_id:
        flash("No se encontró el productor asociado a este usuario.", "error")
        return redirect(url_for('admin_productos_productor'))

    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    precio = float(request.form['precio'])
    categoria_id = int(request.form['categoria_id'])
    imagen = request.files['imagen']

    filename = None
    if imagen and allowed_file(imagen.filename):
        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    nuevo_producto = Producto(
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        categoria_id=categoria_id,
        imagen=filename,
        productor_id=productor_id  
    )
    db.session.add(nuevo_producto)
    db.session.commit()
    flash("Producto agregado correctamente", "success") 
    return redirect(url_for('admin_productos_productor'))




@app.route('/editar_producto/<int:producto_id>', methods=['GET', 'POST'])
def editar_producto(producto_id):
    producto = Producto.query.get(producto_id)

    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.precio = float(request.form['precio'])
        db.session.commit()
        return redirect(url_for('admin_productos_productor'))

    return render_template('editar_producto.html', producto=producto)

@app.route('/eliminar_carrito/<int:producto_id>', methods=['POST'])
def eliminar_carrito(producto_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    item = Carrito.query.filter_by(usuario_id=usuario_id, producto_id=producto_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("❌ Producto eliminado del carrito.", "info")
    else:
        flash("⚠️ El producto no estaba en el carrito.", "warning")

    return redirect(url_for('carrito'))

@app.route('/agregar_carrito/<int:producto_id>', methods=['POST'])
def agregar_carrito(producto_id):
    if 'usuario_id' not in session:
        flash("⚠️ Debes iniciar sesión para agregar productos al carrito.", "error")
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    producto = Producto.query.get(producto_id)

    if producto:
      
        item_en_carrito = Carrito.query.filter_by(usuario_id=usuario_id, producto_id=producto_id).first()

        if item_en_carrito:
            item_en_carrito.cantidad += 1 
        else:
            nuevo_item = Carrito(usuario_id=usuario_id, producto_id=producto_id, cantidad=1)
            db.session.add(nuevo_item)  

        try:
            db.session.commit()
            flash('✅ Producto agregado al carrito', 'success')
        except Exception as e:
            db.session.rollback()  
            flash(f"❌ Error al agregar producto al carrito: {str(e)}", "error")

    return redirect(url_for('productos'))


@app.route('/metodos_pago', methods=['GET', 'POST'])
def metodos_pago():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    tarjetas = Tarjeta.query.filter_by(usuario_id=usuario_id).all()
 
    tarjetas_json = [
        {
            "id": t.id,
            "numero": t.numero,
            "propietario": t.propietario,
            "fecha_expiracion": t.fecha_expiracion
        }
        for t in tarjetas
    ]
    return render_template('metodos_pago.html', tarjetas=tarjetas, tarjetas_json=tarjetas_json)


@app.route('/detalle_pedido/<int:pedido_id>')
def detalle_pedido(pedido_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    pedido = Pedido.query.get_or_404(pedido_id)
    cantidad_carrito = obtener_cantidad_carrito(session['usuario_id'])
    return render_template('detalle_pedido.html', pedido=pedido, cantidad_carrito=cantidad_carrito)

@app.route('/quitar_carrito/<int:producto_id>', methods=['POST'])
def quitar_carrito(producto_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario_id = session['usuario_id']
    item = Carrito.query.filter_by(usuario_id=usuario_id, producto_id=producto_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash('❌ Se eliminó el producto exitosamente', 'success')
    else:
        flash("⚠️ El producto no estaba en el carrito.", "warning")

    return redirect(url_for('carrito'))


@app.route('/marcar_entregado/<int:pedido_id>')
def marcar_entregado(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.estado = "Entregado"
    db.session.commit()
    return redirect(url_for('pedidos_productor'))



@app.route('/eliminar_producto/<int:producto_id>', methods=['POST'])
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    PedidoItem.query.filter_by(producto_id=producto_id).delete()
   
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado correctamente.', 'success')
    return redirect(url_for('admin_productos_productor'))


@app.route('/actualizar_producto/<int:producto_id>', methods=['GET', 'POST'])
def actualizar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    categorias = Categoria.query.all()
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.descripcion = request.form['descripcion']
        producto.precio = float(request.form['precio'])
        producto.categoria_id = int(request.form['categoria_id'])
        imagen = request.files['imagen']
        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            producto.imagen = filename
        db.session.commit()
        flash("Producto actualizado correctamente.", "success")
        return redirect(url_for('admin_productos_productor'))
    return render_template('actualizar_producto.html', producto=producto, categorias=categorias)



@app.route('/descargar_factura_pdf')
def descargar_factura_pdf():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    
    pedido = Pedido.query.filter_by(usuario_id=usuario_id).order_by(Pedido.fecha.desc()).first()
    if not pedido:
        flash("No hay pedido para generar factura.", "error")
        return redirect(url_for('pago'))

   
    items = PedidoItem.query.filter_by(pedido_id=pedido.id).all()
    productos = []
    for item in items:
        producto = Producto.query.get(item.producto_id)
        if producto:
            productos.append({
                'nombre': producto.nombre,
                'cantidad': item.cantidad,
                'precio': producto.precio,
                'subtotal': producto.precio * item.cantidad
            })

    total = pedido.total
    metodo_pago = Pago.query.filter_by(pedido_id=pedido.id).first()
    if metodo_pago:
       metodo = MetodoPago.query.get(metodo_pago.metodo_pago_id)
       metodo_pago_nombre = metodo.nombre if metodo else "No especificado"
    else:
      metodo_pago_nombre = "No especificado"

  
    html = render_template('factura_pdf.html', pedido=pedido, productos=productos, total=total, metodo_pago=metodo_pago_nombre)

  
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)
    if pisa_status.err:
        flash("Error al generar el PDF.", "error")
        return redirect(url_for('pago'))

    result.seek(0)
    return send_file(result, mimetype='application/pdf', as_attachment=True, download_name='factura_AgronoMia.pdf')


@app.route('/agregar_usuario', methods=['GET', 'POST'])
def agregar_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        tipo_usuario = request.form['tipo_usuario']
        nuevo_usuario = Usuario(nombre=nombre, email=email, password=password, tipo_usuario=tipo_usuario)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash("Usuario agregado correctamente.", "success")
        return redirect(url_for('gestion_usuarios'))
    return render_template('agregar_usuario.html')

@app.route('/eliminar_pedido/<int:pedido_id>', methods=['POST'])
def eliminar_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    
    PedidoItem.query.filter_by(pedido_id=pedido.id).delete()
    db.session.delete(pedido)
    db.session.commit()
    flash("Pedido eliminado correctamente.", "success")
    return redirect(url_for('admin_pedidos'))



@app.route('/agregar_producto_admin', methods=['GET', 'POST'])
def agregar_producto_admin():
    productores = Productor.query.all()
    categorias = Categoria.query.all()
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        imagen = request.files['imagen']
        productor_id = int(request.form['productor_id'])
        categoria_id = int(request.form['categoria_id'])
        filename = None
        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        nuevo_producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            imagen=filename,
            productor_id=productor_id,
            categoria_id=categoria_id
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        flash("Producto agregado correctamente.", "success")
        return redirect(url_for('admin_productos'))
    return render_template('agregar_producto_admin.html', productores=productores, categorias=categorias)


@app.route('/actualizar_producto_admin/<int:producto_id>', methods=['GET', 'POST'])
def actualizar_producto_admin(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.descripcion = request.form['descripcion']
        producto.precio = float(request.form['precio'])
        imagen = request.files['imagen']
        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            producto.imagen = filename
        db.session.commit()
        flash("Producto actualizado correctamente.", "success")
        return redirect(url_for('admin_productos'))
    return render_template('actualizar_producto_admin.html', producto=producto)


@app.route('/eliminar_producto_admin/<int:producto_id>', methods=['POST'])
def eliminar_producto_admin(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    PedidoItem.query.filter_by(producto_id=producto_id).delete()
   
    db.session.delete(producto)
    db.session.commit()
    flash("Producto eliminado permanentemente.", "success")
    return redirect(url_for('admin_productos'))

@app.route('/descargar_ticket_transferencia')
def descargar_ticket_transferencia():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    
    pedido = Pedido.query.filter_by(usuario_id=usuario_id).order_by(Pedido.fecha.desc()).first()
    if not pedido:
        flash("No hay pedido para generar ticket.", "error")
        return redirect(url_for('pago'))

   
    items = PedidoItem.query.filter_by(pedido_id=pedido.id).all()
    productos = []
    for item in items:
        producto = Producto.query.get(item.producto_id)
        if producto:
            productos.append({
                'nombre': producto.nombre,
                'cantidad': item.cantidad,
                'precio': producto.precio,
                'subtotal': producto.precio * item.cantidad
            })

    total = pedido.total

    datos = session.get('ticket_transferencia')
    if not datos:
        flash("Datos de transferencia no encontrados.", "error")
        return redirect(url_for('pago'))

    html = render_template('ticket_transferencia.html',
        pedido=pedido,
        numero_tarjeta=datos['numero_tarjeta'],
        propietario=datos['propietario'],
        productos=productos,
        total=total
    )
    result = io.BytesIO()
    pisa.CreatePDF(html, dest=result)
    result.seek(0)
    return send_file(result, mimetype='application/pdf', as_attachment=True, download_name='ticket_transferencia.pdf')




@app.route('/eliminar_tarjeta/<int:tarjeta_id>', methods=['POST'])
def eliminar_tarjeta(tarjeta_id):
    tarjeta = Tarjeta.query.get_or_404(tarjeta_id)
    if tarjeta.usuario_id == session['usuario_id']:
        db.session.delete(tarjeta)
        db.session.commit()
        flash("✔ Tarjeta eliminada correctamente.", "success")
    return redirect(url_for('panel_cliente'))

@app.route('/agregar_tarjeta', methods=['GET', 'POST'])
def agregar_tarjeta():
    if request.method == 'POST':
        numero = request.form['numero_tarjeta']
        propietario = request.form['propietario']
        fecha_expiracion = request.form['fecha_expiracion']
        try:
            nueva_tarjeta = Tarjeta(
                usuario_id=session['usuario_id'],
                numero=numero,
                propietario=propietario,
                fecha_expiracion=fecha_expiracion
            )
            db.session.add(nueva_tarjeta)
            db.session.commit()
            flash("✔ Tarjeta agregada exitosamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash("✖ Ocurrió un error al agregar la tarjeta.", "error")
        return redirect(url_for('agregar_tarjeta'))
    return render_template('agregar_tarjeta.html')


@app.route('/desactivar_producto/<int:producto_id>', methods=['POST'])
def desactivar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    producto.activo = False
    db.session.commit()
    flash('Producto desactivado correctamente.', 'success')
    return redirect(url_for('admin_productos_productor'))

@app.route('/desactivar_producto_admin/<int:producto_id>', methods=['POST'])
def desactivar_producto_admin(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    producto.activo = False
    db.session.commit()
    flash('Producto desactivado correctamente.', 'success')
    return redirect(url_for('admin_productos'))


@app.route('/admin_mensajes')
def admin_mensajes():
    mensajes = Contacto.query.order_by(Contacto.id.desc()).all()
    return render_template('admin_mensajes.html', mensajes=mensajes)

@app.route('/eliminar_mensaje/<int:mensaje_id>', methods=['POST'])
def eliminar_mensaje(mensaje_id):
    mensaje = Contacto.query.get_or_404(mensaje_id)
    db.session.delete(mensaje)
    db.session.commit()
    flash('Mensaje eliminado correctamente.', 'success')
    return redirect(url_for('admin_mensajes'))


@app.route('/responder_mensaje/<int:mensaje_id>', methods=['POST'])
def responder_mensaje(mensaje_id):
    mensaje = Contacto.query.get_or_404(mensaje_id)
    respuesta = request.form.get('respuesta')
    if respuesta:
        mensaje.respuesta = respuesta
        db.session.commit()
        flash('Respuesta enviada correctamente.', 'success')
    else:
        flash('La respuesta no puede estar vacía.', 'danger')
    return redirect(url_for('admin_mensajes'))



@app.route('/bandeja_mensajes_productor')
def bandeja_mensajes_productor():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Productor':
        return redirect(url_for('login'))
    mensajes = Contacto.query.filter_by(usuario_id=session['usuario_id']).order_by(Contacto.fecha.desc()).all()
    return render_template('bandeja_mensajes_productor.html', mensajes=mensajes)


@app.route('/enviar_mensaje_productor', methods=['GET', 'POST'])
def enviar_mensaje_productor():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Productor':
        return redirect(url_for('login'))
    if request.method == 'POST':
        mensaje = request.form.get('mensaje')
        if mensaje:
            nuevo_mensaje = Contacto(usuario_id=session['usuario_id'], mensaje=mensaje)
            db.session.add(nuevo_mensaje)
            db.session.commit()
            flash('Mensaje enviado correctamente.', 'success')
            return redirect(url_for('bandeja_mensajes_productor'))
        else:
            flash('El mensaje no puede estar vacío.', 'danger')
    return render_template('enviar_mensaje_productor.html')


@app.route('/bandeja_mensajes_cliente')
def bandeja_mensajes_cliente():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Cliente':
        return redirect(url_for('login'))
    mensajes = Contacto.query.filter_by(usuario_id=session['usuario_id']).order_by(Contacto.fecha.desc()).all()
    return render_template('bandeja_mensajes_cliente.html', mensajes=mensajes)

@app.route('/registro_admin', methods=['GET', 'POST'])
def registro_admin():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email'].strip().lower()  
        password = request.form['password']


        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{8,}$", password):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un carácter especial.", "error")
            return redirect(url_for('registro_admin'))

        if Usuario.query.filter_by(email=email).first():
            return render_template('registro_admin.html', correo_duplicado=True, nombre=nombre, email=email)

        try:
            nuevo_usuario = Usuario(nombre=nombre, email=email, password=password, tipo_usuario="Productor")
            db.session.add(nuevo_usuario)
            db.session.commit()
 
            nuevo_productor = Productor(nombre=nombre, email=email)
            db.session.add(nuevo_productor)
            db.session.commit()
            return render_template('registro_admin.html', registro_exitoso=True)
        except Exception as e:
            db.session.rollback()
            return render_template('registro_admin.html', registro_fallido=True)

    return render_template('registro_admin.html')

@app.route('/registro_productores', methods=['GET', 'POST'])
def registro_productores():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email'].strip().lower()  
        password = request.form['password']

        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{8,}$", password):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un carácter especial.", "error")
            return redirect(url_for('registro_productores'))

        if Usuario.query.filter_by(email=email).first():
            return render_template('registro_productores.html', correo_duplicado=True, nombre=nombre, email=email)

        try:
            nuevo_usuario = Usuario(nombre=nombre, email=email, password=password, tipo_usuario="Productor")
            db.session.add(nuevo_usuario)
            db.session.commit()
 
            nuevo_productor = Productor(nombre=nombre, email=email)
            db.session.add(nuevo_productor)
            db.session.commit()
            return render_template('registro_productores.html', registro_exitoso=True)
        except Exception as e:
            db.session.rollback()
            return render_template('registro_productores.html', registro_fallido=True)

    return render_template('registro_productores.html')


@app.route('/perfil_productor')
def perfil_productor():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Productor':
        return redirect(url_for('login'))
    
    productor_id = session.get('productor_id')
    productor = Productor.query.get_or_404(productor_id)
    
    return render_template('perfil_productor.html', productor=productor)

@app.route('/actualizar_perfil_productor', methods=['POST'])
def actualizar_perfil_productor():
    if 'usuario_id' not in session or session.get('tipo_usuario') != 'Productor':
        return redirect(url_for('login'))
    
    productor_id = session.get('productor_id')
    productor = Productor.query.get_or_404(productor_id)
    
    # Actualizar datos
    productor.nombre = request.form['nombre']
    productor.email = request.form['email']
    productor.ubicacion = request.form['ubicacion']
    productor.descripcion = request.form['descripcion']
    
    # Manejar imagen
    imagen = request.files.get('imagen')
    if imagen and imagen.filename:
        if allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            productor.imagen = filename
    
    db.session.commit()
    flash("Perfil actualizado correctamente", "success")
    return redirect(url_for('perfil_productor'))


@app.route('/gestionar_productores')
def gestionar_productores():
    productores = Productor.query.all()
    return render_template('gestionar_productores.html', productores=productores)


@app.route('/eliminar_productor/<int:productor_id>', methods=['POST'])
def eliminar_productor(productor_id):
    productor = Productor.query.get_or_404(productor_id)
    db.session.delete(productor)
    db.session.commit()
    flash("Productor eliminado correctamente.", "success")
    return redirect(url_for('gestionar_productores'))

@app.route('/editar_productor/<int:productor_id>', methods=['POST'])
def editar_productor(productor_id):
    productor = Productor.query.get_or_404(productor_id)
    productor.nombre = request.form['nombre']
    productor.email = request.form['email']
    productor.ubicacion = request.form.get('ubicacion', '')
    productor.descripcion = request.form.get('descripcion', '')
    db.session.commit()
    flash("Productor actualizado correctamente.", "success")
    return redirect(url_for('gestionar_productores'))

@app.route('/actualizar_estado_pedido/<int:pedido_id>', methods=['POST'])
def actualizar_estado_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    nuevo_estado = request.form.get('estado')
    if nuevo_estado:
        pedido.estado = nuevo_estado
        db.session.commit()
        flash("Estado del pedido actualizado correctamente.", "success")
    else:
        flash("No se recibió un estado válido.", "error")
    return redirect(url_for('admin_pedidos'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        crear_admin()  
        print("✅ Tablas creadas y administrador registrado 🚀")

    
    app.run(debug=True)