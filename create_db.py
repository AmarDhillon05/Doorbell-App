import mysql.connector
import os

camdb = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd = os.environ.get("PSWD"),
    database = 'camdb'
)
cursor = camdb.cursor()

cursor.execute('DROP TABLE users')
cursor.execute('DROP TABLE cams')
cursor.execute('DROP TABLE people')
cursor.execute('CREATE TABLE users (pwd VARCHAR(255), cams TEXT);')
cursor.execute('CREATE TABLE cams (ip VARCHAR(255), name VARCHAR(60));')
cursor.execute('CREATE TABLE people (camname VARCHAR(60), personname VARCHAR(20), path VARCHAR(20));')
#Image Array will be the flattened version
for x in cursor:
    print(x)
