import os, sys
import pandas as pd
import mysql.connector

def main():
    # 1) Cargar el Excel
    path = sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.expanduser("~"), "Documents", "datos.xlsx")
    if not os.path.exists(path):
        print("ERROR: no encontré el archivo:", path)
        sys.exit(1)

    df = pd.read_excel(path, sheet_name="ACREDITACIONES", engine="openpyxl", dtype=str)
    df.columns = df.columns.str.strip()
    print("Columnas en Excel:", df.columns.tolist())

    if "CLIENTE USA" not in df.columns:
        print("ERROR: no veo la columna 'CLIENTE USA' en tu Excel")
        sys.exit(1)

    # 2) Extraer valores únicos (limpios) de CLIENTE USA
    clientes_usa = df["CLIENTE USA"].dropna().astype(str).str.strip()
    clientes_usa = clientes_usa[clientes_usa != ""].unique().tolist()
    print(f"Valores únicos de CLIENTE USA en Excel: {len(clientes_usa)}")

    # 3) Conectar y ver qué proveedores ya están en la BD
    conn = mysql.connector.connect(host="localhost", user="root", password="", database="maciaslogistic")
    cur  = conn.cursor()
    cur.execute("SELECT nombre FROM proveedores;")
    existentes = {row[0] for row in cur.fetchall()}
    print(f"Proveedores ya en BD: {len(existentes)}")

    # 4) Determinar cuáles son nuevos
    nuevos = [n for n in clientes_usa if n not in existentes]
    print(f"Nuevos proveedores a insertar: {len(nuevos)} ->", nuevos[:10], "..." if len(nuevos)>10 else "")

    # 5) Hacer el INSERT de los nuevos
    if nuevos:
        sql = "INSERT INTO proveedores (nombre) VALUES (%s);"
        data = [(n,) for n in nuevos]
        cur.executemany(sql, data)
        conn.commit()
        print("✅ Inserción completada. Filas afectadas:", cur.rowcount)
    else:
        print("⚠️  No había nuevos proveedores; nada que insertar.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
