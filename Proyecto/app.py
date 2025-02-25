from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import re
import pandas as pd
from functools import wraps
import plotly.express as px
import random
import string
import requests
import mysql.connector

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'  # Cambia esto por una clave más segura

app.config['RECAPTCHA_PUBLIC_KEY'] = '6LdadNsqAAAAACnTh-BTdy8axpuLkim3g8cA2FAP'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6LdadNsqAAAAAM_ipF03OtweQJGpFx6QrSfpOzHD'

# Inicializa df_global como None
df_global = None

try:
    db = mysql.connector.connect(
        host="bqkgo4dahd8mzk8wmoiy-mysql.services.clever-cloud.com",
        user="uizayt0lnhyy6p0w",
        passwd="96jCK2wXfTJIul4efBRa",
        database="bqkgo4dahd8mzk8wmoiy"
    )
    print("Conexión a la base de datos exitosa.")
except db.Error as e:
    print(f"Error al conectar a la base de datos: {e}")

# Configuración de Flask-Mail para usar MailerSend
app.config['MAIL_SERVER'] = 'smtp.mailersend.net'  # Servidor SMTP de Gmail
app.config['MAIL_PORT'] = 587  # Puerto para TLS
app.config['MAIL_USE_TLS'] = True  # Usar TLS
app.config['MAIL_USE_SSL'] = False  # No usar SSL
app.config['MAIL_USERNAME'] = 'MS_cRZO7c@trial-yzkq340v2o0ld796.mlsender.net'  # Tu dirección de correo
app.config['MAIL_PASSWORD'] = 'mssp.ar2jyuR.3vz9dlejvoq4kj50.KEoK4Gu'  # Usa la contraseña de aplicación aquí
mail = Mail(app) 

def is_valid_email(email):
    # Validar que el email tenga un formato correcto
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_password(password):
    # Validar que la contraseña tenga entre 8 y 15 caracteres, una mayúscula, una minúscula, un número y un carácter especial
    return (8 <= len(password) <= 15 and  # Longitud entre 8 y 15 caracteres
            re.search(r"[A-Z]", password) and  # Al menos una letra mayúscula
            re.search(r"[a-z]", password) and  # Al menos una letra minúscula
            re.search(r"[0-9]", password) and  # Al menos un número
            re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))  # Al menos un carácter especial

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))  # Redirige a la página de login
        return f(*args, **kwargs)
    return decorated_function

def send_verification_code(email):
    print(f"Enviando código a: {email}")
    code = ''.join(random.choices(string.digits, k=6))
    session['verification_code'] = code
    print(f"Código de verificación generado: {code}")

    msg = Message('Código de Verificación', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'Tu código de verificación es: {code}'

    try:
        mail.send(msg)
        print("Correo enviado con éxito.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

@app.route('/')
def home():
    return render_template('login.html')  # Redirige a la página de login

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validar el correo electrónico
        if not is_valid_email(username):
            return render_template('login.html', error_message='El nombre de usuario debe ser un correo electrónico válido.')

        try:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM usuario WHERE usuarioNombre=%s", (username,))
            user = cursor.fetchone()

            if user:
                print(f"Usuario encontrado: {username}")
                failed_attempts = user[3]  # Suponiendo que el contador de intentos fallidos está en la columna 4
                lock_time = user[4]  # Suponiendo que el tiempo de bloqueo está en la columna 5

                # Verificar si la cuenta está bloqueada
                if failed_attempts >= 3:
                    if lock_time and datetime.now() < lock_time + timedelta(seconds=30):  # 30 segundos de bloqueo
                        print(f"Cuenta bloqueada para el usuario: {username}")
                        return render_template('login.html', error_message='Tu cuenta está bloqueada. Intenta de nuevo más tarde.')
                    else:
                        # Reiniciar el contador de intentos fallidos y el tiempo de bloqueo
                        cursor.execute("UPDATE usuario SET failed_attempts = 0, lock_time = NULL WHERE usuarioNombre=%s", (username,))
                        db.commit()

                if check_password_hash(user[2], password):  # Verificar la contraseña hasheada
                    session['user'] = username
                    # Reiniciar contador de intentos fallidos en la base de datos
                    cursor.execute("UPDATE usuario SET failed_attempts = 0, lock_time = NULL WHERE usuarioNombre=%s", (username,))
                    db.commit()
                    session.pop('verification_code', None)  # Limpiar el código de verificación
                    send_verification_code(username)  # Enviar el código de verificación
                    return redirect(url_for('verify_code'))  # Redirige a la página de verificación
                else:
                    print(f"Contraseña incorrecta para el usuario: {username}")
            else:
                print(f"Usuario no encontrado: {username}")

            # Incrementar el contador de intentos fallidos en la base de datos
            cursor.execute("UPDATE usuario SET failed_attempts = failed_attempts + 1 WHERE usuarioNombre=%s", (username,))
            db.commit()

            # Verificar el nuevo número de intentos fallidos
            cursor.execute("SELECT failed_attempts FROM usuario WHERE usuarioNombre=%s", (username,))
            failed_attempts = cursor.fetchone()[0]

            print(f"Intento fallido #{failed_attempts} para el usuario: {username}")

            if failed_attempts >= 3:
                # Guardar el tiempo de bloqueo
                cursor.execute("UPDATE usuario SET lock_time = %s WHERE usuarioNombre=%s", (datetime.now(), username))
                db.commit()
                print(f"Cuenta bloqueada para el usuario: {username} debido a múltiples intentos fallidos.")
                return render_template('login.html', error_message='Tu cuenta ha sido bloqueada por 30 segundos debido a múltiples intentos fallidos.')

            return render_template('login.html', error_message='Credenciales incorrectas.')

        except Exception as e:
            print(f"Error al procesar la solicitud: {e}")
            return render_template('login.html', error_message='Ocurrió un error al procesar la solicitud. Por favor, inténtalo de nuevo más tarde.')

    return render_template('login.html')



@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        entered_code = request.form['code']
        if entered_code == session.get('verification_code'):
            return redirect(url_for('home_page'))  # Redirige a la página de inicio
        else:
            # Si el código es incorrecto, renderiza la plantilla con un mensaje de error
            error_message = "Código incorrecto. Intenta de nuevo."
            return render_template('verify_code.html', error_message=error_message)

    return render_template('verify_code.html')

@app.route('/home')
@login_required
def home_page():
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirige a login si no está autenticado
    return render_template('home.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    global df_global
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirige a login si no está autenticado

    error_message = None  # Inicializa el mensaje de error

    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            try:
                # Leer el archivo Excel
                df_global = pd.read_excel(file)

                # Convertir la columna 'Fecha aduana' a datetime
                if 'Fecha aduana' in df_global.columns:
                    df_global['Fecha aduana'] = pd.to_datetime(df_global['Fecha aduana'], errors='coerce')
            except Exception as e:
                error_message = "Error al procesar el archivo. Asegúrate de que sea un archivo Excel válido."
                print(f"Error: {e}")

    # Paginación
    page = request.args.get('page', 1, type=int)  # Obtener el número de página
    per_page = 25  # Número de filas por página

    if df_global is not None and not df_global.empty:  # Verifica que df_global no sea None y no esté vacío
        total = len(df_global)  # Total de filas
        start = (page - 1) * per_page
        end = start + per_page
        paginated_df = df_global.iloc[start:end]  # Obtener las filas para la página actual

        # Convertir el DataFrame a HTML
        table = paginated_df.to_html(classes='data', header="true", index=False)
        return render_template('upload.html', table=table, page=page, total_pages=(total // per_page) + 1, error_message=error_message)

    return render_template('upload.html', table=None, page=1, total_pages=1, error_message=error_message)
@app.route('/filter', methods=['POST'])
@login_required
def filter_data():
    global df_global
    if df_global is None or df_global.empty:
        return redirect(url_for('upload_file'))  # Redirige si no hay datos

    error_message = None  # Inicializa el mensaje de error

    # Obtener los valores de los filtros y eliminar espacios en blanco
    cod_paquete = request.form.get('cod_paquete', '').strip()
    cod_manifiesto = request.form.get('cod_manifiesto', '').strip()
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    # Filtrar el DataFrame
    filtered_df = df_global.copy()  # Hacer una copia del DataFrame original

    # Asegurarse de que CodManifiesto sea tratado como string
    filtered_df['CodManifiesto'] = filtered_df['CodManifiesto'].astype(str)

    if cod_paquete:
        filtered_df = filtered_df[filtered_df['CodPaquete'].str.contains(cod_paquete, na=False)]
    if cod_manifiesto:
        filtered_df = filtered_df[filtered_df['CodManifiesto'].str.contains(cod_manifiesto, na=False)]
    
    # Filtrar por rango de fechas
    if fecha_inicio:
        filtered_df = filtered_df[filtered_df['Fecha aduana'] >= pd.to_datetime(fecha_inicio)]
    if fecha_fin:
        fecha_fin_adjusted = pd.to_datetime(fecha_fin) + pd.Timedelta(days=1)
        filtered_df = filtered_df[filtered_df['Fecha aduana'] < fecha_fin_adjusted]

    # Almacenar el DataFrame filtrado en la sesión
    session['filtered_data'] = filtered_df.to_json()  # Convertir a JSON para almacenar en la sesión

    # Convertir el DataFrame filtrado a HTML
    table = filtered_df.to_html(classes='data', header="true", index=False)

    # Paginación
    page = request.args.get('page', 1, type=int)  # Obtener el número de página
    per_page = 25  # Número de filas por página
    total = len(filtered_df)  # Total de filas filtradas

    if total > 0:
        start = (page - 1) * per_page
        end = start + per_page
        paginated_df = filtered_df.iloc[start:end]  # Obtener las filas para la página actual

        # Convertir el DataFrame paginado a HTML
        table = paginated_df.to_html(classes='data', header="true", index=False)
        return render_template('upload.html', table=table, page=page, total_pages=(total // per_page) + 1, error_message=error_message)

    # Si no hay resultados, renderiza la plantilla sin datos
    return render_template('upload.html', table=None, page=1, total_pages=1, error_message=error_message)

@app.route('/reset', methods=['POST'])
@login_required
def reset_data():
    global df_global
    if df_global is None or df_global.empty:
        return redirect(url_for('upload_file'))  # Redirige si no hay datos

    # Limpiar los datos filtrados de la sesión
    session.pop('filtered_data', None)

    # Reiniciar a la primera página
    page = 1
    per_page = 25  # Número de filas por página
    total = len(df_global)  # Total de filas

    # Obtener las filas para la página actual
    start = (page - 1) * per_page
    end = start + per_page
    paginated_df = df_global.iloc[start:end]  # Obtener las filas para la página actual

    # Convertir el DataFrame paginado a HTML
    table = paginated_df.to_html(classes='data', header="true", index=False)

    # Calcular el total de páginas
    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('upload.html', table=table, page=page, total_pages=total_pages)

@app.route('/logout')
def logout():
    session.pop('user', None)  # Elimina el usuario de la sesión
    return redirect(url_for('login'))  # Redirige a la página de login

# Ruta para agregar un nuevo usuario
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Validar el correo electrónico
        if not is_valid_email(username):
            return render_template('add_user.html', error="El nombre de usuario debe ser un correo electrónico válido.")
        
        # Validar la contraseña
        if not is_valid_password(password):
            return render_template('add_user.html', error="Contraseña inválida.")
        
        cursor = db.cursor()
        
        # Verificar si el nombre de usuario ya existe
        cursor.execute("SELECT * FROM usuario WHERE usuarioNombre=%s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            return render_template('add_user.html', error="El nombre de usuario ya existe. Por favor, elige otro.")  # Mensaje de error
        else:
            # Si el nombre de usuario no existe, se puede crear el nuevo usuario
            hashed_password = generate_password_hash(password)  # Hashear la contraseña
            cursor.execute("INSERT INTO usuario (usuarioNombre, usuarioContra) VALUES (%s, %s)", (username, hashed_password))
            db.commit()  # Asegúrate de guardar los cambios
            return redirect(url_for('users'))  # Redirige a la lista de usuarios

    return render_template('add_user.html')

# Ruta para listar usuarios
@app.route('/users')
@login_required
def users():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuario")
    users = cursor.fetchall()
    return render_template('users.html', users=users)

# Ruta para agregar un nuevo empleado
@app.route('/add_employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    cursor = db.cursor()
    
    # Obtener la lista de usuarios que no están asociados a un empleado
    cursor.execute("""
        SELECT u.usuarioId, u.usuarioNombre FROM usuario u
        LEFT JOIN empleado e ON u.usuarioId = e.usuarioId
        WHERE e.usuarioId IS NULL
    """)
    users = cursor.fetchall()

    if request.method == 'POST':
        employee_name = request.form['nombre']
        employee_lastname = request.form['apellido']
        role = request.form['rol']
        usuarioId = request.form['usuarioId']

        # Verificar si ya existe un empleado con el mismo nombre y apellido
        cursor.execute("SELECT * FROM empleado WHERE nombre=%s AND apellido=%s", (employee_name, employee_lastname))
        existing_employee = cursor.fetchone()

        if existing_employee:
            return render_template('add_employee.html', error="Ya existe un empleado con ese nombre y apellido. Por favor, verifica los datos.", users=users)  # Mensaje de error
        else:
            # Si no existe, se puede crear el nuevo empleado
            cursor.execute("INSERT INTO empleado (nombre, apellido, rol, usuarioId) VALUES (%s, %s, %s, %s)", 
                        (employee_name, employee_lastname, role, usuarioId))
            db.commit()  # Asegúrate de guardar los cambios
            return redirect(url_for('employees'))  # Redirige a la lista de empleados

    return render_template('add_employee.html', users=users)
    
@app.route('/employees')
@login_required
def employees():
    cursor = db.cursor()
    # Realizar un JOIN para obtener el nombre de usuario asociado a cada empleado
    cursor.execute("""
        SELECT e.empleadoId, e.nombre, e.apellido, e.rol, u.usuarioNombre 
        FROM empleado e
        JOIN usuario u ON e.usuarioId = u.usuarioId
    """)
    employees = cursor.fetchall()
    return render_template('employees.html', employees=employees)

# Ruta para eliminar un usuario
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    cursor = db.cursor()
    
    # Eliminar el usuario de la base de datos
    cursor.execute("DELETE FROM usuario WHERE usuarioId = %s", (user_id,))
    db.commit()  # Asegúrate de guardar los cambios
    
    return redirect(url_for('users'))  # Redirige a la lista de usuarios

# Ruta para eliminar un empleado
@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    cursor = db.cursor()
    
    # Eliminar el empleado de la base de datos
    cursor.execute("DELETE FROM empleado WHERE empleadoId = %s", (employee_id,))
    db.commit()  # Asegúrate de guardar los cambios
    
    return redirect(url_for('employees'))  # Redirige a la lista de empleados

@app.route('/generate_report', methods=['POST'])
@login_required
def generate_report():
    global df_global
    if df_global is None or df_global.empty:
        return redirect(url_for('upload_file'))  # Redirige si no hay datos

    # Cargar los datos filtrados desde la sesión
    filtered_data_json = session.get('filtered_data')

    if filtered_data_json is not None:
        # Si hay datos filtrados, convertir el JSON de vuelta a un DataFrame
        filtered_df = pd.read_json(filtered_data_json)
    else:
        # Si no hay datos filtrados, usar el DataFrame original
        filtered_df = df_global

    # Gráfico 1: Gráfico circular de "Estado actual savar"
    estado_counts = filtered_df['Estado actual savar'].value_counts()
    fig1 = px.pie(estado_counts, values=estado_counts.values, names=estado_counts.index, title="Distribución de Estados Actuales")

    # Gráfico 2: Gráfico de barras de "Estado aduana"
    estado_aduana_counts = filtered_df['Estado aduana'].value_counts()
    fig2 = px.bar(estado_aduana_counts, x=estado_aduana_counts.index, y=estado_aduana_counts.values, title="Estados de Aduana")

    # Gráfico 3: Gráfico de líneas de "Fecha aduana" (por día)
    filtered_df['Fecha aduana'] = pd.to_datetime(filtered_df['Fecha aduana'])
    fecha_counts = filtered_df.groupby(filtered_df['Fecha aduana'].dt.date).size()
    fig3 = px.line(fecha_counts, x=fecha_counts.index, y=fecha_counts.values, title="Paquetes por Fecha")

    # Gráfico 4: Gráfico de dispersión de "RUC" vs "Celular"
    fig4 = px.scatter(filtered_df, x='RUC', y='Celular', title="Relación entre RUC y Celular")

    # Convertir las figuras a HTML
    graph1 = fig1.to_html(full_html=False)
    graph2 = fig2.to_html(full_html=False)
    graph3 = fig3.to_html(full_html=False)
    graph4 = fig4.to_html(full_html=False)

    # Renderizar la plantilla con los gráficos
    return render_template('report.html', graph1=graph1, graph2=graph2, graph3=graph3, graph4=graph4)

if __name__ == '__main__':
    app.run(debug=True)