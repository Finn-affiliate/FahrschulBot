import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = "fahrschule.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS theorie_freigaben (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schueler_id INTEGER NOT NULL,
                fahrlehrer_id INTEGER NOT NULL,
                passwort TEXT NOT NULL UNIQUE,
                erstellt_am TEXT NOT NULL,
                genutzt INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS theorie_pruefungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schueler_id INTEGER NOT NULL,
                fahrlehrer_id INTEGER NOT NULL,
                punktzahl INTEGER NOT NULL,
                bestanden INTEGER NOT NULL,
                datum TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS praktische_pruefungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schueler_id INTEGER NOT NULL,
                fahrlehrer_id INTEGER NOT NULL,
                kategorie TEXT NOT NULL,
                vorname TEXT NOT NULL,
                nachname TEXT NOT NULL,
                geburtsdatum TEXT NOT NULL,
                telefon TEXT NOT NULL,
                psn TEXT NOT NULL,
                bestanden INTEGER,
                bemerkung TEXT,
                unterschrift TEXT,
                datum TEXT,
                gestartet_am TEXT NOT NULL,
                abgeschlossen INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS fahrlehrer_statistik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fahrlehrer_id INTEGER NOT NULL,
                fahrlehrer_name TEXT NOT NULL,
                woche_start TEXT NOT NULL,
                theorie_freischaltungen INTEGER DEFAULT 0,
                praktisch_a INTEGER DEFAULT 0,
                praktisch_b INTEGER DEFAULT 0,
                praktisch_c INTEGER DEFAULT 0,
                praktisch_d INTEGER DEFAULT 0,
                praktisch_e INTEGER DEFAULT 0,
                praktisch_f INTEGER DEFAULT 0,
                bestanden INTEGER DEFAULT 0,
                nicht_bestanden INTEGER DEFAULT 0,
                UNIQUE(fahrlehrer_id, woche_start)
            );
        """)
    logger.info("Datenbank initialisiert.")


# --- Theorie Freigaben ---

def create_freigabe(schueler_id: int, fahrlehrer_id: int, passwort: str, datum: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO theorie_freigaben (schueler_id, fahrlehrer_id, passwort, erstellt_am) VALUES (?, ?, ?, ?)",
            (schueler_id, fahrlehrer_id, passwort, datum)
        )


def get_freigabe_by_passwort(passwort: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM theorie_freigaben WHERE passwort = ? AND genutzt = 0",
            (passwort,)
        ).fetchone()
        return dict(row) if row else None


def mark_freigabe_genutzt(passwort: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE theorie_freigaben SET genutzt = 1 WHERE passwort = ?",
            (passwort,)
        )


# --- Theorie Prüfungen ---

def save_theorie_pruefung(schueler_id: int, fahrlehrer_id: int, punktzahl: int, bestanden: bool, datum: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO theorie_pruefungen (schueler_id, fahrlehrer_id, punktzahl, bestanden, datum) VALUES (?, ?, ?, ?, ?)",
            (schueler_id, fahrlehrer_id, punktzahl, int(bestanden), datum)
        )


# --- Praktische Prüfungen ---

def start_praktische_pruefung(
    schueler_id: int, fahrlehrer_id: int, kategorie: str,
    vorname: str, nachname: str, geburtsdatum: str,
    telefon: str, psn: str, gestartet_am: str
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO praktische_pruefungen
               (schueler_id, fahrlehrer_id, kategorie, vorname, nachname, geburtsdatum,
                telefon, psn, gestartet_am)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (schueler_id, fahrlehrer_id, kategorie, vorname, nachname,
             geburtsdatum, telefon, psn, gestartet_am)
        )
        return cur.lastrowid


def finish_praktische_pruefung(
    pruefung_id: int, bestanden: bool, unterschrift: str, bemerkung: str, datum: str
):
    with get_conn() as conn:
        conn.execute(
            """UPDATE praktische_pruefungen
               SET bestanden=?, unterschrift=?, bemerkung=?, datum=?, abgeschlossen=1
               WHERE id=?""",
            (int(bestanden), unterschrift, bemerkung, datum, pruefung_id)
        )


def get_laufende_pruefungen(fahrlehrer_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM praktische_pruefungen WHERE fahrlehrer_id=? AND abgeschlossen=0",
            (fahrlehrer_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_pruefung_by_id(pruefung_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM praktische_pruefungen WHERE id=?",
            (pruefung_id,)
        ).fetchone()
        return dict(row) if row else None


def get_laufende_pruefung_by_schueler(schueler_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM praktische_pruefungen WHERE schueler_id=? AND abgeschlossen=0",
            (schueler_id,)
        ).fetchone()
        return dict(row) if row else None


# --- Statistik ---

def get_current_week_start() -> str:
    from datetime import datetime, timedelta
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")


def ensure_fahrlehrer_stat(fahrlehrer_id: int, fahrlehrer_name: str, woche_start: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO fahrlehrer_statistik
               (fahrlehrer_id, fahrlehrer_name, woche_start)
               VALUES (?, ?, ?)""",
            (fahrlehrer_id, fahrlehrer_name, woche_start)
        )


def increment_theorie_freischaltung(fahrlehrer_id: int, fahrlehrer_name: str):
    woche = get_current_week_start()
    ensure_fahrlehrer_stat(fahrlehrer_id, fahrlehrer_name, woche)
    with get_conn() as conn:
        conn.execute(
            """UPDATE fahrlehrer_statistik
               SET theorie_freischaltungen = theorie_freischaltungen + 1
               WHERE fahrlehrer_id=? AND woche_start=?""",
            (fahrlehrer_id, woche)
        )


def increment_praktisch(fahrlehrer_id: int, fahrlehrer_name: str, kategorie: str, bestanden: bool):
    woche = get_current_week_start()
    ensure_fahrlehrer_stat(fahrlehrer_id, fahrlehrer_name, woche)
    kat = kategorie.upper()
    col_map = {"A": "praktisch_a", "B": "praktisch_b", "C": "praktisch_c",
               "D": "praktisch_d", "E": "praktisch_e", "F": "praktisch_f"}
    kat_col = col_map.get(kat, "praktisch_b")
    result_col = "bestanden" if bestanden else "nicht_bestanden"
    with get_conn() as conn:
        conn.execute(
            f"""UPDATE fahrlehrer_statistik
               SET {kat_col} = {kat_col} + 1, {result_col} = {result_col} + 1
               WHERE fahrlehrer_id=? AND woche_start=?""",
            (fahrlehrer_id, woche)
        )


def get_fahrlehrer_stats_week(fahrlehrer_id: int, woche_start: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM fahrlehrer_statistik WHERE fahrlehrer_id=? AND woche_start=?",
            (fahrlehrer_id, woche_start)
        ).fetchone()
        return dict(row) if row else None


def get_all_fahrlehrer_stats_week(woche_start: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM fahrlehrer_statistik WHERE woche_start=?",
            (woche_start,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_gesamtstatistik():
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                SUM(theorie_freischaltungen) as theorie,
                SUM(praktisch_a) as a,
                SUM(praktisch_b) as b,
                SUM(praktisch_c) as c,
                SUM(praktisch_d) as d,
                SUM(praktisch_e) as e,
                SUM(praktisch_f) as f,
                SUM(bestanden) as bestanden,
                SUM(nicht_bestanden) as nicht_bestanden
            FROM fahrlehrer_statistik
        """).fetchone()
        return dict(row) if row else {}


def get_all_fahrlehrer_ids():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT fahrlehrer_id, fahrlehrer_name FROM fahrlehrer_statistik"
        ).fetchall()
        return [dict(r) for r in rows]
