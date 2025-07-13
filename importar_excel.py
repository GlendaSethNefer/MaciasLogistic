import os
import sys
import pandas as pd
import mysql.connector

def check_file(path):
    if not os.path.exists(path):
        print(f"Error: el archivo '{path}' no se encuentra.")
        sys.exit(1)

def connect_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='maciaslogistic'
    )

def to_tuples(df, cols):
    rows = []
    for vals in df[cols].itertuples(index=False, name=None):
        clean = tuple(None if pd.isna(v) else v for v in vals)
        rows.append(clean)
    return rows

def insert_proveedores(cursor, df):
    vals = to_tuples(df, ['id','nombre'])
    sql  = """
        INSERT INTO proveedores (id, nombre)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);
    """
    cursor.executemany(sql, vals)
    print(f"  ✓ proveedores: {len(vals)} filas")

def insert_autos(cursor, df):
    vals = to_tuples(df, ['vin','marca','modelo'])
    sql  = """
        INSERT INTO autos (vin, marca, modelo)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
          marca  = VALUES(marca),
          modelo = VALUES(modelo);
    """
    cursor.executemany(sql, vals)
    print(f"  ✓ autos:       {len(vals)} filas")

def insert_clientes(cursor, df):
    vals = to_tuples(df, ['nombre','vin'])
    sql  = """
        INSERT IGNORE INTO clientes (nombre, vin)
        VALUES (%s, %s);
    """
    cursor.executemany(sql, vals)
    print(f"  ✓ clientes:    {len(vals)} filas")

def main():
    # 1) Ruta al Excel en Documents
    home       = os.path.expanduser("~")
    default_xl = os.path.join(home, 'Documents', 'datos.xlsx')
    path       = sys.argv[1] if len(sys.argv)>1 else default_xl
    check_file(path)

    # 2) Leer hoja y sanear encabezados
    df = pd.read_excel(path,
                       sheet_name='ACREDITACIONES',
                       engine='openpyxl', dtype=str)
    df.columns = df.columns.str.strip()
    print("Total filas en ACREDITACIONES:", len(df))

    # 3) Preparar DataFrames

    # Proveedores: PN → id, MPM → nombre
    df_prov = (
        df[['PN','MPM']]
        .dropna(subset=['PN'])
        .rename(columns={'PN':'id','MPM':'nombre'})
        .drop_duplicates(subset=['id'])
    )

    # Autos (sin año): VIN, MARCA, MODELO
    df_autos = (
        df[['VIN','MARCA','MODELO']]
        .dropna(subset=['VIN'])
        .rename(columns={'VIN':'vin','MARCA':'marca','MODELO':'modelo'})
        .drop_duplicates(subset=['vin'])
    )

    # Clientes (CUBA + USA)
    df_cli = (
        pd.melt(df,
                id_vars=['VIN'],
                value_vars=['CLIENTE CUBA','CLIENTE USA'],
                var_name='origen',
                value_name='nombre')
        .dropna(subset=['nombre'])
        .rename(columns={'VIN':'vin'})
        [['nombre','vin']]
        .drop_duplicates()
    )

    # 4) Conectar e insertar
    conn = connect_db()
    cur  = conn.cursor()

    insert_proveedores(cur, df_prov)
    insert_autos(cur,      df_autos)
    insert_clientes(cur,   df_cli)

    conn.commit()
    cur.close()
    conn.close()
    print("Importación completada con éxito.")

if __name__ == '__main__':
    main()


