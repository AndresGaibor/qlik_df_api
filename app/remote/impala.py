from __future__ import annotations

import logging
import re
from collections.abc import Generator
from contextlib import contextmanager

from impala.dbapi import connect
from impala.error import HiveServer2Error, ProgrammingError

from remote_server.config import RemoteSettings

logger = logging.getLogger(__name__)


def _validar_identificador(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Identificador invalido: {value}")
    return value


@contextmanager
def conexion_impala(settings: RemoteSettings) -> Generator:
    connection = None
    try:
        connection = connect(
            host=settings.impala_host,
            port=settings.impala_port,
            auth_mechanism=settings.impala_auth_mechanism,
            timeout=settings.impala_timeout,
        )
        logger.info("Conectado a Impala en %s:%s", settings.impala_host, settings.impala_port)
        yield connection
    except HiveServer2Error as error:
        logger.error("Error de Impala: %s", error)
        raise
    except ProgrammingError as error:
        logger.error("Error de consulta: %s", error)
        raise
    finally:
        if connection:
            connection.close()


def listar_databases(settings: RemoteSettings) -> list[str]:
    with conexion_impala(settings) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute("SHOW DATABASES")
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()


def listar_tablas(settings: RemoteSettings, database: str) -> list[str]:
    database = _validar_identificador(database)
    with conexion_impala(settings) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(f"SHOW TABLES IN `{database}`")
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()


def listar_columnas(
    settings: RemoteSettings, database: str, table: str
) -> list[dict[str, str]]:
    database = _validar_identificador(database)
    table = _validar_identificador(table)
    with conexion_impala(settings) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(f"DESCRIBE `{database}`.`{table}`")
            columnas = []
            for row in cursor.fetchall():
                col_name = row[0]
                col_type = row[1]
                if col_name and col_type:
                    columnas.append({"name": col_name, "type": col_type})
            return columnas
        finally:
            cursor.close()
