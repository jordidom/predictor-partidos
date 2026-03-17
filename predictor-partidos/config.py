import os

MYSQL_CONFIG = {
    "host": os.getenv("MYSQLHOST", "localhost"),
    "port": int(os.getenv("MYSQLPORT", 3306)),
    "user": os.getenv("MYSQLUSER", "root"),
    "password": os.getenv("MYSQLPASSWORD", ""),
    "database": os.getenv("MYSQLDATABASE", "predictor_partidos")
}

SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esta_clave_por_una_mas_segura")