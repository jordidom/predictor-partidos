import mysql.connector
from werkzeug.security import generate_password_hash
from config import MYSQL_CONFIG

username = "admin"
password = "123admin123"

conn = mysql.connector.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

password_hash = generate_password_hash(password)

cursor.execute("""
    INSERT INTO users (username, password_hash, is_admin)
    VALUES (%s, %s, %s)
""", (username, password_hash, True))

conn.commit()
cursor.close()
conn.close()

print("Usuario admin creado correctamente.")