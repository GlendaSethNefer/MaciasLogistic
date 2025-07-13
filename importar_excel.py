import os
import sys
import pandas as pd
import mysql.connector

def check_file(path):
    if not os.path.exists(path):
        print(f"Error: archivo no encontrado: '{path}'")
        sys.exit(1)

def connect_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='maciaslogistic'
    )

def get_table_columns(cursor, table):
    cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
    return [row[0] for row in cursor.fetchall()]

def to_tuples(df, cols):
    """
    Convierte el df en lista de tuplas para executemany, 
    cambiando NaN a None.
    """
    rows = []
    for vals in df[cols].itertuples(index=False, name=None):
        clean = tuple(None if pd.isna(v) else v for v in vals)
        rows.append(clean)
    return rows

def insert_proveedores(cur, df):
    vals = to_tuples(df, ['id','nombre'])
    sql  = """
        INSERT INTO proveedores (id, nombre)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            nombre = VALUES(nombre);
    """
    print(f"  ✓ proveedores: {len(vals)} filas")
    cur.executemany(sql, vals)

def insert_autos(cur, df):
    vals = to_tuples(df, ['vin','marca','modelo'])
    sql  = """
        INSERT INTO autos (vin, marca, modelo)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            marca  = VALUES(marca),
            modelo = VALUES(modelo);
    """
    print(f"  ✓ autos:       {len(vals)} filas")
    cur.executemany(sql, vals)

def insert_clientes(cur, df, table_cols):
    """
    Aquí asumimos que tu tabla `clientes` tiene columnas:
      - vin                (clave única)
      - cliente_cuba       (para datos de CLIENTE CUBA)
      - cliente_usa        (para datos de CLIENTE USA)
    """
    # Renombrar las columnas del df para que encajen
    df2 = df.rename(columns={
        'CLIENTE CUBA': 'cliente_cuba',
        'CLIENTE USA':  'cliente_usa'
    })[['VIN','cliente_cuba','cliente_usa']]

    # Quitar filas donde VIN sea nulo
    df2 = df2.dropna(subset=['VIN']).drop_duplicates(subset=['VIN'])

    # Asegurarnos que sólo usamos campos que existen en la tabla
    existing = set(table_cols)
    insert_cols = [c for c in ['vin','cliente_cuba','cliente_usa'] if c in existing]
    if 'VIN' in df2.columns:
        df2 = df2.rename(columns={'VIN':'vin'})
    vals = to_tuples(df2, insert_cols)

    cols_sql = ", ".join(f"`{c}`" for c in insert_cols)
    placeholders = ", ".join("%s" for _ in insert_cols)
    updates = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in insert_cols if c != 'vin')

    sql = (
        f"INSERT INTO clientes ({cols_sql})\n"
        f"VALUES ({placeholders})\n"
        f"ON DUPLICATE KEY UPDATE {updates};"
    )

    print(f"  ✓ clientes:    {len(vals)} filas (columnas: {insert_cols})")
    cur.executemany(sql, vals)

def main():
    # 1) Ruta a Documents/datos.xlsx
    home       = os.path.expanduser("~")
    default_xl = os.path.join(home, 'Documents', 'datos.xlsx')
    path       = sys.argv[1] if len(sys.argv) > 1 else default_xl
    check_file(path)

    # 2) Leer hoja y sanear encabezados
    df = pd.read_excel(path,
                       sheet_name='ACREDITACIONES',
                       engine='openpyxl', dtype=str)
    df.columns = df.columns.str.strip()
    print("Total filas en ACREDITACIONES:", len(df))

    # 3a) Proveedores: PN → id, MPM → nombre
    df_prov = (
        df[['PN','MPM']]
        .dropna(subset=['PN'])
        .rename(columns={'PN':'id','MPM':'nombre'})
        .drop_duplicates(subset=['id'])
    )

    # 3b) Autos: VIN, MARCA, MODELO
    df_autos = (
        df[['VIN','MARCA','MODELO']]
        .dropna(subset=['VIN'])
        .rename(columns={'VIN':'vin','MARCA':'marca','MODELO':'modelo'})
        .drop_duplicates(subset=['vin'])
    )

    # 3c) Clientes: mantenemos ambas columnas en un solo df
    df_cli = df[['VIN','CLIENTE CUBA','CLIENTE USA']]

    # 4) Conectar e insertar
    conn = connect_db()
    cur  = conn.cursor()

    # 1) Tras leer df = pd.read_excel(...)
    # 2) Extraer CLIENTE USA como proveedores
    df_prov_usa = (
        df[['CLIENTE USA']]
        .dropna(subset=['CLIENTE USA'])      # quita filas vacías
        .rename(columns={'CLIENTE USA':'nombre'})
        .drop_duplicates(subset=['nombre'])  # valores únicos
    )
    # 3) Volcar a tu tabla proveedores (supone id AUTO_INCREMENT)
    vals = [(n,) for n in df_prov_usa['nombre']]
    sql  = "INSERT IGNORE INTO proveedores (nombre) VALUES (%s);"
    cur.executemany(sql, vals)
    print(f"Proveedores USA insertados: {len(vals)}")

    insert_proveedores(cur, df_prov)
    insert_autos(cur,      df_autos)

    # Obtener columnas reales de clientes
    cols_cli = get_table_columns(cur, 'clientes')
    insert_clientes(cur, df_cli, cols_cli)

    conn.commit()
    cur.close()
    conn.close()
    print("Importación completada con éxito.")

if __name__ == '__main__':
    main()
