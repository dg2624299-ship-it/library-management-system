import sqlite3
from datetime import datetime

from data_structures import Book


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, db_path="library.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()


    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                isbn             TEXT PRIMARY KEY,
                title            TEXT NOT NULL,
                author           TEXT NOT NULL,
                genre            TEXT NOT NULL,
                tags             TEXT NOT NULL DEFAULT '',
                price            REAL NOT NULL,
                total_copies     INTEGER NOT NULL,
                available_copies INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS loans (
                loan_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(user_id),
                isbn        TEXT    NOT NULL REFERENCES books(isbn),
                borrowed_at TEXT    NOT NULL,
                returned_at TEXT
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                entry_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn      TEXT    NOT NULL REFERENCES books(isbn),
                user_id   INTEGER NOT NULL REFERENCES users(user_id),
                joined_at TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                txn_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL REFERENCES users(user_id),
                isbn      TEXT    NOT NULL REFERENCES books(isbn),
                action    TEXT    NOT NULL,
                amount    REAL    NOT NULL DEFAULT 0,
                timestamp TEXT    NOT NULL
            );
        """)
        self.conn.commit()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


    def insert_book(self, book):
        self.conn.execute(
            "INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (book.isbn, book.title, book.author, book.genre, book.tags_as_text(),
             book.price, book.total_copies, book.available_copies))

    def get_all_books(self):
        rows = self.conn.execute("SELECT * FROM books").fetchall()
        return [Book.from_row(row) for row in rows]

    def count_books(self):
        return self.conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    def update_stock(self, isbn, total_copies, available_copies):
        self.conn.execute(
            "UPDATE books SET total_copies = ?, available_copies = ? WHERE isbn = ?",
            (total_copies, available_copies, isbn))


    def insert_user(self, name):
        cursor = self.conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
        return cursor.lastrowid

    def get_user_name(self, user_id):
        row = self.conn.execute(
            "SELECT name FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row["name"] if row else None

    def get_all_users(self):
        rows = self.conn.execute("SELECT user_id, name FROM users ORDER BY user_id")
        return [(r["user_id"], r["name"]) for r in rows]


    def insert_loan(self, user_id, isbn):
        self.conn.execute(
            "INSERT INTO loans (user_id, isbn, borrowed_at) VALUES (?, ?, ?)",
            (user_id, isbn, _now()))

    def close_loan(self, user_id, isbn):
        cursor = self.conn.execute(
            "UPDATE loans SET returned_at = ? "
            "WHERE user_id = ? AND isbn = ? AND returned_at IS NULL",
            (_now(), user_id, isbn))
        return cursor.rowcount > 0

    def has_active_loan(self, user_id, isbn):
        row = self.conn.execute(
            "SELECT 1 FROM loans WHERE user_id = ? AND isbn = ? AND returned_at IS NULL",
            (user_id, isbn)).fetchone()
        return row is not None

    def get_active_loans(self, user_id):
        rows = self.conn.execute(
            "SELECT b.title, b.isbn, l.borrowed_at FROM loans l "
            "JOIN books b ON b.isbn = l.isbn "
            "WHERE l.user_id = ? AND l.returned_at IS NULL", (user_id,))
        return [(r["title"], r["isbn"], r["borrowed_at"]) for r in rows]


    def insert_waitlist(self, isbn, user_id):
        self.conn.execute(
            "INSERT INTO waitlist (isbn, user_id, joined_at) VALUES (?, ?, ?)",
            (isbn, user_id, _now()))

    def delete_waitlist(self, isbn, user_id):
        self.conn.execute(
            "DELETE FROM waitlist WHERE isbn = ? AND user_id = ?", (isbn, user_id))

    def get_all_waitlist(self):
        rows = self.conn.execute(
            "SELECT isbn, user_id FROM waitlist ORDER BY entry_id").fetchall()
        return [(r["isbn"], r["user_id"]) for r in rows]


    def log_transaction(self, user_id, isbn, action, amount=0.0):
        self.conn.execute(
            "INSERT INTO transactions (user_id, isbn, action, amount, timestamp) "
            "VALUES (?, ?, ?, ?, ?)", (user_id, isbn, action, amount, _now()))

    def get_recent_transactions(self, limit=10):
        rows = self.conn.execute(
            "SELECT t.timestamp, t.action, u.name, b.title, t.amount "
            "FROM transactions t "
            "JOIN users u ON u.user_id = t.user_id "
            "JOIN books b ON b.isbn = t.isbn "
            "ORDER BY t.txn_id DESC LIMIT ?", (limit,))
        return [(r["timestamp"], r["action"], r["name"], r["title"], r["amount"])
                for r in rows]
