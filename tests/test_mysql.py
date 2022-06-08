import os
import sys
import json
from multiprocessing import Process

import pytest
from mysql.connector import connect, DatabaseError

from common import (SSH, register_sconn, unregister_sconn, list_sconns,
    unregister_all_sconns, count_topic_message, topic, sconn
)

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from util import mysql_insert_fake

SETUP_PATH = '../mysql_jdbc/temp/setup.json'


@pytest.fixture(scope="session")
def setup():
    """인프라 설치 정보."""
    assert os.path.isfile(SETUP_PATH)
    with open(SETUP_PATH, 'rt') as f:
        return json.loads(f.read())


def exec_many(cursor, stmt):
    """멀티 라인 쿼리 실행

    주: 결과를 읽어와야 쿼리 실행이 됨

    """
    results = cursor.execute(stmt, multi=True)
    for res in results:
        print(res)


@pytest.fixture
def dbconcur(setup):
    db_addr = setup['mysql_public_ip']['value']
    db_user = setup['db_user']['value']
    db_passwd = setup['db_passwd']['value']
    conn = connect(host=db_addr, user=db_user, password=db_passwd, database="test")
    cursor = conn.cursor()
    yield conn, cursor
    conn.close()


@pytest.fixture
def table(dbconcur):
    """테스트용 테이블 초기화."""
    conn, cursor = dbconcur

    stmt = '''
DROP TABLE IF EXISTS person;
CREATE TABLE person (
    id  INT NOT NULL AUTO_INCREMENT,
    pid INT DEFAULT -1 NOT NULL,
    sid INT DEFAULT -1 NOT NULL,
    name VARCHAR(40),
    address VARCHAR(200),
    ip VARCHAR(20),
    birth DATE,
    company VARCHAR(40),
    phone VARCHAR(40),
    PRIMARY KEY(id)
)
    '''
    exec_many(cursor, stmt)
    yield
    cursor.execute('DROP TABLE IF EXISTS person;')
    conn.commit()


def test_sconn(setup):
    """카프카 JDBC Source 커넥트 테스트."""
    consumer_ip = setup['consumer_public_ip']['value']
    kafka_ip = setup['kafka_private_ip']['value']
    db_addr = setup['mysql_public_ip']['value']
    db_user = setup['db_user']['value']
    db_passwd = setup['db_passwd']['value']

    ssh = SSH(consumer_ip)

    # 기존 등록된 소스 커넥터 모두 제거
    unregister_all_sconns(ssh, kafka_ip)

    # 현재 등록된 커넥터
    ret = list_sconns(ssh, kafka_ip)
    assert ret == []

    # 커넥터 등록
    ret = register_sconn(ssh, kafka_ip, 'mysql', db_addr, 3306,
        db_user, db_passwd, "test", "person", "my-topic-")
    conn_name = ret['name']
    cfg = ret['config']
    assert cfg['name'].startswith('my-sconn')
    ret = list_sconns(ssh, kafka_ip)
    assert ret == [conn_name]

    # 커넥터 해제
    unregister_sconn(ssh, kafka_ip, conn_name)
    ret = list_sconns(ssh, kafka_ip)
    assert ret == []


def _insert_proc(setup):
    """가짜 데이터 인서트."""
    # DB 테이블에 100 x 100 행 insert
    mysql_insert_fake(setup, 100, 100)


def test_ct_basic(setup, sconn):
    """기본적인 Change Tracking 테스트."""
    consumer_ip = setup['consumer_public_ip']['value']
    kafka_ip = setup['kafka_private_ip']['value']
    ssh = SSH(consumer_ip)

    # DB 테이블에 100 x 100 행 insert
    p = Process(target=_insert_proc, args=(setup,))
    p.start()

    # 카프카 토픽 확인 (timeout 되기전에 다 받아야 함)
    cnt = count_topic_message(ssh, kafka_ip, 'my-topic-person')
    assert 10000 == cnt

    p.join()

    # # 추가 insert
    # mysql_insert_fake(setup, 100, 100)

    # cnt = count_topic_message(ssh, kafka_ip, 'my-topic-person')
    # assert 20000 == cnt