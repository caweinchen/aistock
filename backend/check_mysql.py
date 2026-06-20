import mysql.connector
from mysql.connector import errorcode
import os

config = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USERNAME', 'aistock'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'at_stock'),
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print('Tables:', [t[0] for t in tables])
    
    # 获取每个表的行数
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f'{table[0]}: {count} rows')
    
    conn.close()
except mysql.connector.Error as err:
    print(f"Error: {err}")
