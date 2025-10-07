import pyodbc
from azure.identity import DefaultAzureCredential

# === Configuration ===
sql_endpoint = "your-lakehouse.sql.azuresynapse.net"
database = "YourLakehouseName"
sql_query = "SELECT TOP 10 * FROM YourTable"

# === Get Azure AD Access Token ===
credential = DefaultAzureCredential()

# === Connect to Fabric Lakehouse via ODBC ===
conn_str = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{sql_endpoint},1433;"
    f"Database={database};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
    f"Authentication=ActiveDirectoryAccessToken"
)

# === Run SQL Query ===
with pyodbc.connect(conn_str, attrs_before={1256: credential.get_token("https://sql.azuresynapse.net/.default").token}) as conn:
    cursor = conn.cursor()
    cursor.execute(sql_query)

    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()

    for row in rows:
        row_dict = dict(zip(columns, row))
        print(row_dict)
