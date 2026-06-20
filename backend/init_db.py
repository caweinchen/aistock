import mysql.connector
from mysql.connector import errorcode
import os
import urllib.parse

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('MYSQL_ROOT_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_ROOT_PORT', '3306')),
    'user': os.getenv('MYSQL_ROOT_USER', 'root'),
    'password': os.getenv('MYSQL_ROOT_PASSWORD', ''),
}

TARGET_DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USERNAME', 'aistock'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'at_stock'),
}

def create_database():
    try:
        # 连接到MySQL服务器（不指定数据库）
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {TARGET_DB_CONFIG['database']} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{TARGET_DB_CONFIG['database']}' created or already exists")

        # 创建用户（如果不存在）并授权
        try:
            cursor.execute(f"CREATE USER '{TARGET_DB_CONFIG['user']}'@'%' IDENTIFIED BY '{TARGET_DB_CONFIG['password']}'")
            print(f"User '{TARGET_DB_CONFIG['user']}' created")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_CANNOT_ADD_FOREIGN:
                print(f"User '{TARGET_DB_CONFIG['user']}' already exists")
            else:
                raise

        # 授权
        cursor.execute(f"GRANT ALL PRIVILEGES ON {TARGET_DB_CONFIG['database']}.* TO '{TARGET_DB_CONFIG['user']}'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        print(f"Privileges granted to user '{TARGET_DB_CONFIG['user']}'")

        cursor.close()
        conn.close()
        print("Database initialization completed successfully")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return False

    return True

if __name__ == "__main__":
    create_database()
