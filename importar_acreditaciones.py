import os
import pandas as pd
import mysql.connector
import uuid
from datetime import datetime

# --- Ruta del Excel en Documentos ---
file_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'datos.xlsx')

# --- Índices de las hojas que quieres importar: hoja 1, 2, y 4 (cero-indexed) ---
hojas_objetivo = [0, 1, 3]

# --- Conexión a la base de datos ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'maciaslogistic'
}

# --- Normaliza encabezados y limpia NaNs ---
def limpiar_df(df):
    df = df.where(pd.notnull(df), None)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    return df

# --- Clasifica tipo de persona basado en columnas PN y MPM ---
def clasificar_persona(pn, mpm):
    pn_flag = pn and str(pn).strip().upper() in ['X', 'SI', 'SÍ']
    mpm_flag = mpm and str(mpm).strip() != ''
    
    if pn_flag and mpm_flag:
        return "Persona natural / Mipyme"
    elif pn_flag:
        return "Persona natural"
    elif mpm_flag:
        return "Mipyme"
    else:
        return None

# --- Conexión a MySQL ---
conn = mysql.connector.connect(**db_config)
cur = conn.cursor(dictionary=True)

for hoja in hojas_objetivo:
    df = pd.read_excel(file_path, sheet_name=hoja, engine='openpyxl', dtype=str)
    df = limpiar_df(df)

    for idx, row in df.iterrows():
        t_persona = clasificar_persona(row.get('pn'), row.get('mpm'))

        datos = (
            row.get('estado'),                               # estado
            row.get('vin'),                                  # vin
            row.get('cliente_cuba'),                         # cuba
            row.get('cliente_usa'),                          # usa
            t_persona,                                       # t_persona
            row.get('mpm'),                                  # num_envio
            row.get('estado'),                               # estado_doc
            row.get('conf._accordia') or row.get('acreditacion'),  # acreditacion
            row.get('expediente'),                           # expediente
            row.get('ubicacion'),                            # ubicacion
            int(str(row.get('pagado', '')).strip().lower() in ['1', 'sí', 'si', 'x']),  # pagado
            row.get('referencia'),                           # referencia
            row.get('observaciones'),                        # observaciones
            str(uuid.uuid4()),                               # uuid
            datetime.now(),                                  # created_at
            datetime.now()                                   # updated_at
        )

        cur.execute("""
            INSERT INTO clientes (
              estado, vin, cuba, usa, t_persona,
              num_envio, estado_doc, acreditacion, expediente,
              ubicacion, pagado, referencia, observaciones,
              uuid, created_at, updated_at
            ) VALUES (
              %s, %s, %s, %s, %s,
              %s, %s, %s, %s,
              %s, %s, %s, %s,
              %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
              t_persona    = VALUES(t_persona),
              cuba         = VALUES(cuba),
              usa          = VALUES(usa),
              referencia   = VALUES(referencia),
              observaciones= VALUES(observaciones),
              updated_at   = VALUES(updated_at)
        """, datos)

        print(f"✅ Hoja {hoja+1} → Fila {idx+1} procesada")

# --- Finaliza ---
conn.commit()
cur.close()
conn.close()
print("🚀 Importación completa sin duplicados ni conflictos")
