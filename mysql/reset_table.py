import time
import sys
import json
from pathlib import Path

from mysql.connector import connect, DatabaseError


with open(snakemake.input[0], 'rt') as f:
    tfout = json.loads(f.read())

SERVER = tfout['mysql_public_ip']['value']
USER = tfout['db_user']['value']
PASSWD = tfout['db_passwd']['value']
DATABASE = 'test'

print(f"Connect MySQL at {SERVER}")
retry = 10
while True:
    try:
        conn = connect(host=SERVER, user=USER, password=PASSWD, db=DATABASE)
    except DatabaseError as e:
        retry -= 1
        if "Can't connect to MySQL server" in str(e) and retry > 0:
            time.sleep(2)
            print("Wait for MySQL connection.")
        else:
            raise e
    else:
        break

cursor = conn.cursor()
print("Done")

# 테이블 생성
sql = '''
DROP TABLE IF EXISTS person;
CREATE TABLE person (
    id  INT NOT NULL AUTO_INCREMENT,
    pid INT NOT NULL,
    sid INT NOT NULL,
    name VARCHAR(40),
    address VARCHAR(200),
    ip VARCHAR(20),
    birth DATE,
    company VARCHAR(40),
    phone VARCHAR(40),
    PRIMARY KEY(id)
)
'''
cursor.execute(sql)
conn.close()

Path(snakemake.output[0]).touch()