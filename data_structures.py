from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    genre: str
    tags: list
    price: float
    total_copies: int
    available_copies: int

    @classmethod
    def from_row(cls, row):
        tags = [t for t in row["tags"].split(",") if t]
        return cls(row["isbn"], row["title"], row["author"], row["genre"],
                   tags, row["price"], row["total_copies"], row["available_copies"])

    def tags_as_text(self):
        return ",".join(self.tags)

    def tag_set(self):
        return {self.genre.lower()} | {t.strip().lower() for t in self.tags}


@dataclass
class Transaction:
    action: str
    user_id: int
    isbn: str
    time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


class BookHashTable:

    def __init__(self):
        self._table = {}

    def put(self, book):
        self._table[book.isbn] = book

    def get(self, isbn):
        return self._table.get(isbn)

    def contains(self, isbn):
        return isbn in self._table

    def all_books(self):
        return sorted(self._table.values(), key=lambda b: b.title)

    def search_keyword(self, text):
        text = text.lower().strip()
        return [b for b in self.all_books()
                if text in b.title.lower()
                or text in b.author.lower()
                or text in b.genre.lower()]

    def __len__(self):
        return len(self._table)


class WaitlistQueue:

    def __init__(self):
        self._items = deque()

    def enqueue(self, user_id):
        self._items.append(user_id)

    def dequeue(self):
        return self._items.popleft() if self._items else None

    def peek(self):
        return self._items[0] if self._items else None

    def contains(self, user_id):
        return user_id in self._items

    def remove(self, user_id):
        if user_id in self._items:
            self._items.remove(user_id)
            return True
        return False

    def to_list(self):
        return list(self._items)

    def is_empty(self):
        return len(self._items) == 0

    def __len__(self):
        return len(self._items)


class HistoryStack:

    def __init__(self):
        self._items = []

    def push(self, transaction):
        self._items.append(transaction)

    def pop(self):
        return self._items.pop() if self._items else None

    def peek(self):
        return self._items[-1] if self._items else None

    def recent(self, count=10):
        return list(reversed(self._items))[:count]

    def is_empty(self):
        return len(self._items) == 0

    def __len__(self):
        return len(self._items)


class RecommendationGraph:

    def __init__(self):
        self._edges = {}
        self._tags = {}

    def add_book(self, isbn, tags):
        self._edges.setdefault(isbn, set())
        for other_isbn, other_tags in self._tags.items():
            if tags & other_tags:
                self._edges[isbn].add(other_isbn)
                self._edges[other_isbn].add(isbn)
        self._tags[isbn] = tags

    def shared_tags(self, isbn_a, isbn_b):
        return self._tags.get(isbn_a, set()) & self._tags.get(isbn_b, set())

    def recommend(self, start_isbn, max_depth=2):
        if start_isbn not in self._edges:
            return []

        visited = {start_isbn}
        bfs_queue = deque([(start_isbn, 0)])
        results = []

        while bfs_queue:
            current, depth = bfs_queue.popleft()
            if depth == max_depth:
                continue


            neighbours = sorted(
                self._edges[current],
                key=lambda n: (-len(self._tags[current] & self._tags[n]), n))

            for neighbour in neighbours:
                if neighbour not in visited:
                    visited.add(neighbour)
                    results.append((neighbour, depth + 1))
                    bfs_queue.append((neighbour, depth + 1))
        return results
