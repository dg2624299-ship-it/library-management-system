from data_structures import (Book, Transaction, BookHashTable, WaitlistQueue,
                             HistoryStack, RecommendationGraph)


class LibraryService:
    BUYBACK_RATE = 0.5

    def __init__(self, db):
        self.db = db
        self.books = BookHashTable()
        self.waitlists = {}
        self.history = HistoryStack()
        self.graph = RecommendationGraph()
        self._load_from_database()


    def _load_from_database(self):
        for book in self.db.get_all_books():
            self.books.put(book)
            self.graph.add_book(book.isbn, book.tag_set())
        for isbn, user_id in self.db.get_all_waitlist():
            self._queue_for(isbn).enqueue(user_id)


    def _queue_for(self, isbn):
        if isbn not in self.waitlists:
            self.waitlists[isbn] = WaitlistQueue()
        return self.waitlists[isbn]

    def _name(self, user_id):
        return self.db.get_user_name(user_id) or f"user #{user_id}"

    def _check(self, user_id, isbn):
        isbn = isbn.strip()
        book = self.books.get(isbn)
        if book is None:
            return None, f"No book found with ISBN {isbn}."
        if self.db.get_user_name(user_id) is None:
            return None, f"No user found with ID {user_id}."
        return book, None

    def _lend_copy(self, user_id, book, action="BORROW"):
        book.available_copies -= 1
        self.db.update_stock(book.isbn, book.total_copies, book.available_copies)
        self.db.insert_loan(user_id, book.isbn)
        self.db.log_transaction(user_id, book.isbn, action)

    def _take_back_copy(self, user_id, book, action):
        self.db.close_loan(user_id, book.isbn)
        book.available_copies += 1
        self.db.update_stock(book.isbn, book.total_copies, book.available_copies)
        self.db.log_transaction(user_id, book.isbn, action)

    def _serve_waitlist(self, book):
        messages = []
        queue = self._queue_for(book.isbn)
        while book.available_copies > 0 and not queue.is_empty():
            next_user = queue.dequeue()
            self.db.delete_waitlist(book.isbn, next_user)
            self._lend_copy(next_user, book, action="BORROW (from waitlist)")
            self.history.push(Transaction("BORROW", next_user, book.isbn))
            messages.append(f"Waitlist: '{book.title}' was automatically "
                            f"assigned to {self._name(next_user)}.")
        return messages


    def add_book(self, isbn, title, author, genre, tags, price, copies):
        isbn, title = isbn.strip(), title.strip()
        if not isbn or not title or not author.strip() or not genre.strip():
            return False, "ISBN, title, author and genre are required."
        if copies < 1 or price < 0:
            return False, "Copies must be at least 1 and price cannot be negative."
        if self.books.contains(isbn):
            return False, f"A book with ISBN {isbn} already exists."

        book = Book(isbn, title, author.strip(), genre.strip(),
                    [t.strip() for t in tags if t.strip()], price, copies, copies)
        self.db.insert_book(book)
        self.db.commit()
        self.books.put(book)
        self.graph.add_book(isbn, book.tag_set())
        return True, f"Added '{title}' with {copies} copies."

    def search_book(self, isbn):
        return self.books.get(isbn.strip())

    def search_by_keyword(self, text):
        return self.books.search_keyword(text)

    def list_books(self):
        return self.books.all_books()


    def register_user(self, name):
        name = name.strip()
        if not name:
            return None
        user_id = self.db.insert_user(name)
        self.db.commit()
        return user_id

    def list_users(self):
        return self.db.get_all_users()

    def my_loans(self, user_id):
        return self.db.get_active_loans(user_id)


    def preorder_book(self, user_id, isbn):
        book, error = self._check(user_id, isbn)
        if error:
            return False, error
        if book.available_copies > 0:
            return False, "This book is available right now - borrow or buy it instead."
        if self.db.has_active_loan(user_id, book.isbn):
            return False, "You already have this book borrowed."

        queue = self._queue_for(book.isbn)
        if queue.contains(user_id):
            return False, "You are already on the waitlist for this book."

        queue.enqueue(user_id)
        self.db.insert_waitlist(book.isbn, user_id)
        self.db.log_transaction(user_id, book.isbn, "PREORDER")
        self.db.commit()
        self.history.push(Transaction("PREORDER", user_id, book.isbn))
        return True, (f"{self._name(user_id)} joined the waitlist for '{book.title}'. "
                      f"Position in queue: {len(queue)}.")

    def view_waitlist(self, isbn):
        book = self.books.get(isbn.strip())
        if book is None:
            return None, []
        names = [self._name(u) for u in self._queue_for(book.isbn).to_list()]
        return book, names


    def borrow_book(self, user_id, isbn):
        book, error = self._check(user_id, isbn)
        if error:
            return False, error
        if self.db.has_active_loan(user_id, book.isbn):
            return False, "You have already borrowed this book."
        if book.available_copies == 0:
            waiting = len(self._queue_for(book.isbn))
            return False, (f"'{book.title}' is checked out ({waiting} waiting). "
                           f"Use pre-order to join the waitlist.")

        self._lend_copy(user_id, book)
        self.db.commit()
        self.history.push(Transaction("BORROW", user_id, book.isbn))
        return True, (f"{self._name(user_id)} borrowed '{book.title}'. "
                      f"Copies left: {book.available_copies}.")

    def buy_book(self, user_id, isbn):
        book, error = self._check(user_id, isbn)
        if error:
            return False, error
        if book.available_copies == 0:
            return False, f"'{book.title}' is out of stock. Use pre-order to join the waitlist."

        book.total_copies -= 1
        book.available_copies -= 1
        self.db.update_stock(book.isbn, book.total_copies, book.available_copies)
        self.db.log_transaction(user_id, book.isbn, "BUY", book.price)
        self.db.commit()
        self.history.push(Transaction("BUY", user_id, book.isbn))
        return True, (f"{self._name(user_id)} bought '{book.title}' for "
                      f"${book.price:.2f}. Copies left: {book.available_copies}.")


    def return_book(self, user_id, isbn):
        book, error = self._check(user_id, isbn)
        if error:
            return False, error
        if not self.db.has_active_loan(user_id, book.isbn):
            return False, "You have not borrowed this book."

        self._take_back_copy(user_id, book, "RETURN")
        notes = self._serve_waitlist(book)
        self.db.commit()
        return True, "\n".join([f"{self._name(user_id)} returned '{book.title}'."] + notes)

    def sell_book(self, user_id, isbn):
        book, error = self._check(user_id, isbn)
        if error:
            return False, error

        payout = round(book.price * self.BUYBACK_RATE, 2)
        book.total_copies += 1
        book.available_copies += 1
        self.db.update_stock(book.isbn, book.total_copies, book.available_copies)
        self.db.log_transaction(user_id, book.isbn, "SELL", payout)
        notes = self._serve_waitlist(book)
        self.db.commit()
        return True, "\n".join(
            [f"{self._name(user_id)} sold '{book.title}' back for ${payout:.2f}."] + notes)


    def get_history(self, count=10):
        lines = []
        for txn in self.history.recent(count):
            book = self.books.get(txn.isbn)
            lines.append(f"[{txn.time}] {txn.action:<8} {self._name(txn.user_id)} - {book.title}")
        return lines

    def undo_last_action(self):
        txn = self.history.pop()
        if txn is None:
            return False, "Nothing to undo - history is empty."

        book = self.books.get(txn.isbn)
        name = self._name(txn.user_id)

        if txn.action == "BORROW":
            if not self.db.has_active_loan(txn.user_id, txn.isbn):
                return False, f"{name} has already returned '{book.title}'; nothing to undo."
            self._take_back_copy(txn.user_id, book, "UNDO BORROW")
            notes = self._serve_waitlist(book)
            self.db.commit()
            return True, "\n".join([f"Undid borrow: {name} gave back '{book.title}'."] + notes)

        if txn.action == "BUY":
            book.total_copies += 1
            book.available_copies += 1
            self.db.update_stock(book.isbn, book.total_copies, book.available_copies)
            self.db.log_transaction(txn.user_id, book.isbn, "UNDO BUY", -book.price)
            notes = self._serve_waitlist(book)
            self.db.commit()
            return True, "\n".join([f"Undid purchase: '{book.title}' restocked, {name} refunded."] + notes)

        if txn.action == "PREORDER":
            if self._queue_for(book.isbn).remove(txn.user_id):
                self.db.delete_waitlist(book.isbn, txn.user_id)
                self.db.log_transaction(txn.user_id, book.isbn, "UNDO PREORDER")
                self.db.commit()
                return True, f"Undid pre-order: {name} left the waitlist for '{book.title}'."
            return False, f"{name} already received '{book.title}' from the waitlist; nothing to undo."

        return False, "Unknown action."

    def get_transaction_log(self, limit=10):
        return self.db.get_recent_transactions(limit)


    def show_recommendations(self, isbn, max_depth=2, limit=5):
        start = self.books.get(isbn.strip())
        if start is None:
            return None, []
        found = self.graph.recommend(start.isbn, max_depth)
        results = []
        for rec_isbn, depth in found[:limit]:
            shared = sorted(self.graph.shared_tags(start.isbn, rec_isbn))
            results.append((self.books.get(rec_isbn), depth, shared))
        return start, results
