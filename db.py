from __future__ import annotations

from typing import Optional, Any, Dict, Tuple
import re
import streamlit as st
import pandas as pd

try:
    import mysql.connector as mysql
except Exception:
    mysql = None


def get_conn_params() -> Dict[str, Any]:
    secrets = getattr(st, "secrets", {}) or {}
    cfg = dict(st.session_state.get("_db_cfg", {}))

    if not cfg:
        try:
            from core.settings import DEFAULT_DB
            cfg = dict(DEFAULT_DB)
        except Exception:
            cfg = {}

    mysql_sec = secrets.get("mysql") if isinstance(secrets, dict) else None
    if isinstance(mysql_sec, dict):
        cfg.update(
            {
                "host": mysql_sec.get("host", cfg.get("host", "localhost")),
                "port": int(mysql_sec.get("port", cfg.get("port", 3306))),
                "user": mysql_sec.get("user", cfg.get("user", "")),
                "password": mysql_sec.get("password", cfg.get("password", "")),
                "database": mysql_sec.get("database", cfg.get("database", "")),
            }
        )

    if "port" in cfg:
        cfg["port"] = int(cfg["port"])

    return cfg
import json

def audit_log(action: str, entity: str, entity_key: str, before: dict | None, after: dict | None):
    actor_role = st.session_state.get("user_role", "user")
    actor_name = st.session_state.get("user_name") or None
    return execute(
        """
        INSERT INTO audit_log (Actor_Role, Actor_Name, Action, Entity, Entity_Key, Before_JSON, After_JSON)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            actor_role,
            actor_name,
            action,
            entity,
            entity_key,
            json.dumps(before) if before else None,
            json.dumps(after) if after else None,
        ),
    )


def get_connection():
    if mysql is None:
        raise RuntimeError("mysql-connector-python is not installed. Run: pip install mysql-connector-python")
    return mysql.connect(**get_conn_params())


def _close(conn) -> None:
    try:
        conn.close()
    except Exception:
        pass


def query_df(sql: str, params: Optional[Tuple[Any, ...]] = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return pd.DataFrame(rows)
    finally:
        _close(conn)


def execute(sql: str, params: Optional[Tuple[Any, ...]] = None) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        rc = cur.rowcount
        cur.close()
        return int(rc)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _close(conn)


def load_provinces() -> pd.DataFrame:
    df = query_df("SELECT Province_Code, Province_Name FROM provinces ORDER BY Province_Name")
    if df.empty:
        return pd.DataFrame(columns=["Province_Code", "Province_Name"])
    return df


def load_banks(active_only: bool = True) -> pd.DataFrame:
    if active_only:
        return query_df("SELECT Bank_ID, Bank_Name, Payment_Method FROM banks WHERE Is_Active=1 ORDER BY Bank_Name")
    return query_df("SELECT Bank_ID, Bank_Name, Payment_Method, Is_Active FROM banks ORDER BY Bank_Name")


def add_bank(bank_name: str, payment_method: str = "BANK_TRANSFER", is_active: int = 1) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO banks (Bank_Name, Payment_Method, Is_Active) VALUES (%s, %s, %s)",
            (bank_name.strip(), payment_method, int(is_active)),
        )
        new_id = cur.lastrowid
        conn.commit()
        cur.close()
        return int(new_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _close(conn)


def set_bank_active(bank_id: int, is_active: int) -> int:
    return execute("UPDATE banks SET Is_Active=%s WHERE Bank_ID=%s", (int(is_active), int(bank_id)))


def set_bank_payment_method(bank_id: int, payment_method: str) -> int:
    return execute("UPDATE banks SET Payment_Method=%s WHERE Bank_ID=%s", (payment_method, int(bank_id)))


def search_projects(q: str = "") -> pd.DataFrame:
    like = f"%{q.strip()}%" if q else "%"
    return query_df(
        """
        SELECT Project_ID, Project_Code, Project_Name, Phase_Number, Project_Type, Client_Name,
               Implementing_Partner, Start_Date, End_Date, Status, Notes, Project_Document_Link,
               Created_At, Updated_At
        FROM projects
        WHERE Project_Code LIKE %s
           OR Project_Name LIKE %s
           OR Client_Name LIKE %s
           OR Implementing_Partner LIKE %s
        ORDER BY Project_ID DESC
        LIMIT 200
        """,
        (like, like, like, like),
    )


def get_project_by_id(project_id: int) -> pd.DataFrame:
    return query_df(
        """
        SELECT Project_ID, Project_Code, Project_Name, Phase_Number, Project_Type, Client_Name,
               Implementing_Partner, Start_Date, End_Date, Status, Notes, Project_Document_Link,
               Created_At, Updated_At
        FROM projects
        WHERE Project_ID=%s
        LIMIT 1
        """,
        (int(project_id),),
    )


def add_project(data: dict) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO projects
              (Project_Code, Project_Name, Project_Type, Client_Name, Implementing_Partner,
               Start_Date, End_Date, Status, Notes, Project_Document_Link)
            VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                data["Project_Code"].strip(),
                data["Project_Name"].strip(),
                data["Project_Type"],
                (data.get("Client_Name") or None),
                (data.get("Implementing_Partner") or None),
                (data.get("Start_Date") or None),
                (data.get("End_Date") or None),
                data["Status"],
                (data.get("Notes") or None),
                (data.get("Project_Document_Link") or None),
            ),
        )
        new_id = cur.lastrowid
        conn.commit()
        cur.close()
        return int(new_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _close(conn)


def update_project(project_id: int, data: dict) -> int:
    return execute(
        """
        UPDATE projects
        SET Project_Code=%s,
            Project_Name=%s,
            Project_Type=%s,
            Client_Name=%s,
            Implementing_Partner=%s,
            Start_Date=%s,
            End_Date=%s,
            Status=%s,
            Notes=%s,
            Project_Document_Link=%s
        WHERE Project_ID=%s
        """,
        (
            data["Project_Code"].strip(),
            data["Project_Name"].strip(),
            data["Project_Type"],
            (data.get("Client_Name") or None),
            (data.get("Implementing_Partner") or None),
            (data.get("Start_Date") or None),
            (data.get("End_Date") or None),
            data["Status"],
            (data.get("Notes") or None),
            (data.get("Project_Document_Link") or None),
            int(project_id),
        ),
    )


def get_surveyor_by_code(code: str) -> pd.DataFrame:
    return query_df(
        "SELECT Surveyor_ID, Surveyor_Code, Surveyor_Name FROM surveyors WHERE Surveyor_Code=%s",
        (code.strip(),),
    )


def list_surveyor_accounts(surveyor_id: int) -> pd.DataFrame:
    return query_df(
        """
        SELECT sba.Bank_Account_ID,
               sba.Payment_Type,
               sba.Account_Number,
               sba.Mobile_Number,
               sba.Account_Title,
               sba.Is_Default,
               sba.Is_Active,
               sba.Created_At,
               b.Bank_Name,
               b.Payment_Method
        FROM surveyor_bank_accounts sba
        JOIN banks b ON b.Bank_ID = sba.Bank_ID
        WHERE sba.Surveyor_ID=%s
        ORDER BY sba.Is_Default DESC, sba.Bank_Account_ID DESC
        """,
        (int(surveyor_id),),
    )


def add_surveyor_account_tx(
    conn,
    surveyor_id: int,
    bank_id: int,
    payment_type: str,
    account_number: Optional[str],
    mobile_number: Optional[str],
    account_title: Optional[str],
    make_default: int,
    is_active: int = 1,
) -> int:
    cur = conn.cursor()
    try:
        if int(make_default) == 1:
            cur.execute("UPDATE surveyor_bank_accounts SET Is_Default=0 WHERE Surveyor_ID=%s", (int(surveyor_id),))
        cur.execute(
            """
            INSERT INTO surveyor_bank_accounts
              (Surveyor_ID, Bank_ID, Payment_Type, Account_Number, Mobile_Number, Account_Title, Is_Default, Is_Active)
            VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                int(surveyor_id),
                int(bank_id),
                payment_type,
                (account_number.strip() if account_number else None),
                (mobile_number.strip() if mobile_number else None),
                (account_title.strip() if account_title else None),
                int(make_default),
                int(is_active),
            ),
        )
        new_id = cur.lastrowid
        cur.close()
        return int(new_id)
    except Exception:
        try:
            cur.close()
        except Exception:
            pass
        raise


def set_default_account_tx(conn, surveyor_id: int, bank_account_id: int) -> int:
    cur = conn.cursor()
    try:
        cur.execute("UPDATE surveyor_bank_accounts SET Is_Default=0 WHERE Surveyor_ID=%s", (int(surveyor_id),))
        cur.execute(
            "UPDATE surveyor_bank_accounts SET Is_Default=1 WHERE Bank_Account_ID=%s AND Surveyor_ID=%s",
            (int(bank_account_id), int(surveyor_id)),
        )
        rc = cur.rowcount
        cur.close()
        return int(rc)
    except Exception:
        try:
            cur.close()
        except Exception:
            pass
        raise


def _client_to_code(client_name: str) -> str:
    s = (client_name or "").strip().upper()
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return (s or "CLIENT")[:20]


def _project_to_key(project_name: str) -> str:
    s = (project_name or "").strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s[:150]


def generate_project_code_tx(conn, client_name: str, project_name: str, start_date) -> Tuple[str, int]:
    if start_date is None:
        raise ValueError("Start_Date is required")
    year = int(start_date.year)
    client_code = _client_to_code(client_name)
    project_key = _project_to_key(project_name)

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT IGNORE INTO project_phase_sequences (Client_Code, Project_Key, Start_Year, Last_Phase)
            VALUES (%s,%s,%s,0)
            """,
            (client_code, project_key, year),
        )
        cur.execute(
            """
            SELECT Last_Phase
            FROM project_phase_sequences
            WHERE Client_Code=%s AND Project_Key=%s AND Start_Year=%s
            FOR UPDATE
            """,
            (client_code, project_key, year),
        )
        row = cur.fetchone()
        last_phase = int(row[0]) if row else 0
        phase = last_phase + 1
        cur.execute(
            """
            UPDATE project_phase_sequences
            SET Last_Phase=%s
            WHERE Client_Code=%s AND Project_Key=%s AND Start_Year=%s
            """,
            (int(phase), client_code, project_key, year),
        )
        code = f"PPC-{client_code}-{year}-PH-{phase:02d}"
        return code, int(phase)
    finally:
        try:
            cur.close()
        except Exception:
            pass


def add_project_auto(data: dict) -> int:
    conn = get_connection()
    try:
        conn.start_transaction()
        code, phase = generate_project_code_tx(
            conn,
            client_name=data.get("Client_Name") or "",
            project_name=data.get("Project_Name") or "",
            start_date=data.get("Start_Date"),
        )
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO projects
              (Project_Code, Project_Name, Phase_Number, Project_Type, Client_Name, Implementing_Partner,
               Start_Date, End_Date, Status, Notes, Project_Document_Link)
            VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                code,
                data["Project_Name"].strip(),
                int(phase),
                data["Project_Type"],
                (data.get("Client_Name") or None),
                (data.get("Implementing_Partner") or None),
                (data.get("Start_Date") or None),
                (data.get("End_Date") or None),
                data["Status"],
                (data.get("Notes") or None),
                (data.get("Project_Document_Link") or None),
            ),
        )
        new_id = cur.lastrowid
        cur.close()
        conn.commit()
        return int(new_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _close(conn)


def get_next_surveyor_code(perm_prov_code: str, conn=None) -> str:
    from core.settings import SURVEYOR_CODE_PREFIX

    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()

    try:
        if owns_conn:
            conn.start_transaction()

        cur = conn.cursor()
        cur.execute(
            "INSERT IGNORE INTO province_sequences (Province_Code, Last_Number) VALUES (%s, 0)",
            (perm_prov_code,),
        )
        cur.execute(
            "SELECT Last_Number FROM province_sequences WHERE Province_Code=%s FOR UPDATE",
            (perm_prov_code,),
        )
        row = cur.fetchone()
        last = int(row[0]) if row else 0
        nxt = last + 1
        cur.execute(
            "UPDATE province_sequences SET Last_Number=%s WHERE Province_Code=%s",
            (int(nxt), perm_prov_code),
        )
        code = f"{SURVEYOR_CODE_PREFIX}-{perm_prov_code}-{nxt:03d}"
        cur.close()

        if owns_conn:
            conn.commit()

        return code
    except Exception:
        if owns_conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if owns_conn:
            _close(conn)
