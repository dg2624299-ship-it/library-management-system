# Library Management System (Python + SQLite)

A command-line library system that combines a **SQLite database** with four classic **data structures** (hash table, queue, stack, graph). It is built to be easy to read and easy to explain in a viva.

- Language: Python 3
- Database: `sqlite3` (built in, no installation)
- Interface: command line (CLI)
- External packages: none

---

## 1. How to run

```bash
python main.py
```

On the first run the database `library.db` is created and filled with 12 sample books and 4 users, so the app works immediately.

To wipe everything and start again:

```bash
python setup_data.py --reset
```

---

## 2. Project structure

```
library_system/
├── main.py             Command-line menu (the only file that uses print/input)
├── library.py          Logic layer: all library operations
├── data_structures.py  Hash table, queue, stack and graph
├── database.py         All SQL statements
├── setup_data.py       Sample books and users
└── README.md           This file
```

### How the files connect

```
main.py  ->  library.py  ->  database.py          (permanent storage, SQLite)
                         ->  data_structures.py    (fast in-memory structures)
setup_data.py  ->  database.py                     (fills the empty database)
```

This is **separation of concerns**: the interface, the logic, the SQL and the data structures each live in their own file, so each can be explained (and changed) independently.

---

## 3. Menu options

| # | Option | Data structure involved |
|---|--------|-------------------------|
| 1 | Search book by ISBN | Hash table, O(1) |
| 2 | Search by title / author / genre | Hash table scan, O(n) |
| 3 | List all books | Hash table |
| 4 | Add a book | SQL + hash table + graph |
| 5 | Borrow a book | Stack (push) |
| 6 | Pre-order a book | Queue (enqueue) |
| 7 | Buy a book | Stack (push) |
| 8 | Return a book | Queue (dequeue, auto-assign) |
| 9 | Sell a book back to the library | Queue (dequeue, auto-assign) |
| 10 | Show recommendations | Graph + BFS |
| 11 | View a book's waitlist | Queue |
| 12 | History / Undo | Stack (pop) |
| 13 | My borrowed books | SQL |
| 14 | Transaction log | SQL |
| s | Switch user | - |

---

## 4. The four data structures

### 4.1 Hash table (`BookHashTable`)

- **What:** a dictionary mapping `ISBN -> Book`.
- **Why:** books are looked up by ISBN constantly (borrow, buy, return, recommend). A hash function turns the ISBN into a bucket position, so lookup, insert and delete are **O(1)** on average. Scanning a list would be O(n) every time.
- **Python note:** Python's `dict` is a hash table. Collisions are handled internally using open addressing.
- **Limitation:** it only helps when the exact key is known. Searching by part of a title or author must check every book, which is **O(n)**.

### 4.2 Queue (`WaitlistQueue`)

- **What:** one FIFO queue per book, holding the IDs of users waiting for it.
- **Why:** a waitlist must be fair. First In, First Out means the person who pre-ordered first gets the book first.
- **Implementation:** `collections.deque`. `popleft()` is O(1), whereas `list.pop(0)` is O(n) because every other element has to shift.
- **Behaviour:** when a copy comes back (return, sell-back, or undo), the program dequeues the person at the front and lends them the book automatically.
- **Invariant:** if a book's queue is not empty, its `available_copies` is 0. A returned copy goes straight to the next person instead of the shelf.

### 4.3 Stack (`HistoryStack`)

- **What:** a LIFO stack of `Transaction` records (borrow, buy, pre-order).
- **Why:** undo always reverses the **most recent** action first, then the one before it. That is Last In, First Out.
- **Implementation:** a Python list. `append()` is push and `pop()` is pop, both O(1).
- **Undo rules:**
  - Undo borrow: the book is given back (and the queue is served if someone is waiting).
  - Undo buy: the copy is restocked and the buyer is refunded.
  - Undo pre-order: the user leaves the queue.
  - Each undo first checks it is still possible (for example, a borrowed book may already have been returned).
- **Scope:** the stack only lives for the current session. The `transactions` table in SQL is the permanent history. Returns and sell-backs are not pushed on the stack, so they cannot be undone.

### 4.4 Graph (`RecommendationGraph`)

- **What:** an undirected graph stored as an **adjacency list** (`isbn -> set of neighbouring isbns`).
  - **Node** = a book
  - **Edge** = the two books share at least one genre or tag
- **Why a graph:** recommendations are about relationships between books, and a graph models relationships directly.
- **Why an adjacency list:** it uses O(V + E) memory. An adjacency matrix would need O(V^2), which is wasteful because most books are not connected to each other.
- **Why BFS and not DFS:** BFS visits all books 1 step away first, then 2 steps away. The most closely related books come out first. DFS would follow one chain deep and could return a distant book before a directly related one.
- **Depth:** depth 1 means the book shares a tag with your book. Depth 2 means it shares a tag with one of those books ("friend of a friend"). Within a depth level, books sharing more tags come first.

---

## 5. Database design (SQLite)

| Table | Purpose |
|-------|---------|
| `books` | Catalogue, price, total copies, available copies |
| `users` | Library members |
| `loans` | Who borrowed which book; `returned_at` is NULL while still borrowed |
| `waitlist` | Saved copy of the queues so they survive a restart (`entry_id` order = queue order) |
| `transactions` | Permanent audit log of every action |

### SQL versus memory

- **SQLite** is permanent storage and survives closing the program.
- **The dictionary, queues and graph** are a fast working copy, rebuilt from SQL every time the program starts.
- Every change is written to **both**, with SQL first, so they never disagree.

### Good practices to mention

- **Parameterised queries** (`?` placeholders) are used everywhere. This prevents SQL injection.
- **One commit per operation.** Borrowing involves three writes (update stock, insert loan, log transaction). They are saved together or not at all. This is **atomicity** from ACID.
- **Foreign keys** are enabled, so a loan cannot refer to a book or user that does not exist.

---

## 6. What each function does

| Function | What happens |
|----------|--------------|
| `add_book()` | Validates, inserts into SQL, then adds to the hash table and the graph |
| `search_book()` | Exact ISBN lookup in the hash table, O(1) |
| `search_by_keyword()` | Scans title, author and genre, O(n) |
| `borrow_book()` | Checks availability, lends a copy, updates SQL, pushes onto the stack |
| `buy_book()` | Permanently removes one copy, logs the sale, pushes onto the stack |
| `preorder_book()` | If the book is unavailable, enqueues the user and saves to the waitlist table |
| `return_book()` | Closes the loan, restores the copy, then serves the front of the queue |
| `sell_book()` | The user sells a copy back to the library (50% of the price). Stock increases and the queue is served |
| `undo_last_action()` | Pops the stack and reverses that action |
| `show_recommendations()` | BFS from the chosen book, nearest books first |

**Note on `sell_book()`:** it is implemented as a buy-back, meaning the user sells a copy to the library. The library gains a copy and anyone waiting is served immediately.

---

## 7. Viva cheat sheet

### Time complexities

| Structure | Used for | Operation | Time |
|-----------|----------|-----------|------|
| Hash table (dict) | Find a book by ISBN | get / put / delete | O(1) average |
| | | keyword search | O(n) |
| Queue (deque) | Pre-order waitlist | enqueue | O(1) |
| | | dequeue | O(1) |
| | | remove from middle (undo) | O(n) |
| Stack (list) | History and undo | push | O(1) |
| | | pop | O(1) |
| Graph (adjacency list) | Recommendations | add a book | O(V) |
| | | BFS recommend | O(V + E) |

### One-line answers

- **Why a hash table?** It jumps straight to a book through hash(ISBN). A list would need O(n).
- **Why a queue?** Fairness: first to pre-order is first served. A deque is used because `list.pop(0)` is O(n).
- **Why a stack?** Undo reverses the latest action first, which is LIFO.
- **Why a graph?** Books are related to each other. Nodes are books and edges are shared tags.
- **Why BFS?** It returns the closest (most related) books first.
- **Why keep both SQL and memory?** SQL is permanent. Memory is fast. Memory is rebuilt from SQL at startup.
- **Why does the queue also live in SQL?** So waitlists are not lost when the program closes.

### Other points examiners like

- Parameterised queries prevent SQL injection.
- One `commit()` per operation gives atomicity.
- Invariant: a non-empty queue implies `available_copies == 0`.
- The stack is per session; the `transactions` table is the permanent history.
- Each layer has one job (interface, logic, SQL, data structures, sample data).

---

## 8. Two-minute demo script

The book **1984** has only one copy, so it demonstrates the queue straight away.

1. Log in as **Asha** and borrow *1984* (option 5). This pushes onto the stack.
2. Switch to **Ravi** (`s`). Try to borrow *1984*: it is refused. Pre-order it (option 6). This enqueues him.
3. Switch to **Meera** and pre-order *1984* too. View the waitlist (option 11): Ravi, then Meera.
4. Switch back to **Asha** and return *1984* (option 8). It is automatically assigned to **Ravi** (dequeue, FIFO).
5. Run option 10 with *1984* to see BFS recommendations.
6. Run option 12 to see the history stack, then undo the last action.

---

## 9. Sample data

12 books across Romance, Classic, Dystopian, Fantasy, Science Fiction, Science, Fiction and Thriller, plus 4 users: Asha (1), Ravi (2), Meera (3), John (4). ISBNs are sample values for demonstration.
