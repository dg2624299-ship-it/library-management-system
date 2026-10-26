from database import Database
from library import LibraryService
from setup_data import seed_database, DB_FILE


def ask_int(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("  Please enter a number.")


def ask_float(prompt):
    while True:
        try:
            return float(input(prompt).strip())
        except ValueError:
            print("  Please enter a valid price.")


def print_book(book):
    print(f"  ISBN: {book.isbn} | {book.title} by {book.author}")
    print(f"        Genre: {book.genre} | Tags: {', '.join(book.tags) or '-'} | "
          f"Price: ${book.price:.2f} | Available: {book.available_copies}/{book.total_copies}")


def print_result(result):
    ok, message = result
    print(("  [OK] " if ok else "  [!]  ") + message)


def search_by_isbn(library, user_id):
    book = library.search_book(input("ISBN: "))
    print_book(book) if book else print("  No book with that ISBN.")


def search_by_keyword(library, user_id):
    results = library.search_by_keyword(input("Title / author / genre: "))
    if not results:
        print("  No matches.")
    for book in results:
        print_book(book)


def list_books(library, user_id):
    for book in library.list_books():
        print_book(book)


def add_book(library, user_id):
    isbn = input("ISBN: ")
    title = input("Title: ")
    author = input("Author: ")
    genre = input("Genre: ")
    tags = input("Tags (comma separated, optional): ").split(",")
    price = ask_float("Price: ")
    copies = ask_int("Number of copies: ")
    print_result(library.add_book(isbn, title, author, genre, tags, price, copies))


def borrow_book(library, user_id):
    print_result(library.borrow_book(user_id, input("ISBN to borrow: ")))


def preorder_book(library, user_id):
    print_result(library.preorder_book(user_id, input("ISBN to pre-order: ")))


def buy_book(library, user_id):
    print_result(library.buy_book(user_id, input("ISBN to buy: ")))


def return_book(library, user_id):
    print_result(library.return_book(user_id, input("ISBN to return: ")))


def sell_book(library, user_id):
    print_result(library.sell_book(user_id, input("ISBN of the book you are selling back: ")))


def show_recommendations(library, user_id):
    start, results = library.show_recommendations(input("ISBN of a book you liked: "))
    if start is None:
        print("  No book with that ISBN.")
        return
    print(f"  Because you liked '{start.title}':")
    if not results:
        print("  No related books found.")
    for book, depth, shared in results:
        reason = f"shares: {', '.join(shared)}" if shared else "linked through a related book"
        label = "direct match" if depth == 1 else "2 steps away"
        print(f"   - {book.title} by {book.author}  ({label}; {reason})")


def view_waitlist(library, user_id):
    book, names = library.view_waitlist(input("ISBN: "))
    if book is None:
        print("  No book with that ISBN.")
    elif not names:
        print(f"  Nobody is waiting for '{book.title}'.")
    else:
        print(f"  Waitlist for '{book.title}' (front of queue first):")
        for position, name in enumerate(names, start=1):
            print(f"   {position}. {name}")


def history_and_undo(library, user_id):
    lines = library.get_history()
    print("  Session history (newest first):" if lines else "  No history yet this session.")
    for line in lines:
        print("   " + line)
    if lines and input("  Undo the most recent action? (y/n): ").strip().lower() == "y":
        print_result(library.undo_last_action())


def my_loans(library, user_id):
    loans = library.my_loans(user_id)
    if not loans:
        print("  You have no borrowed books.")
    for title, isbn, borrowed_at in loans:
        print(f"   - {title} (ISBN {isbn}), borrowed {borrowed_at}")


def transaction_log(library, user_id):
    for when, action, name, title, amount in library.get_transaction_log():
        money = f" ${amount:.2f}" if amount else ""
        print(f"   [{when}] {action:<22} {name} - {title}{money}")


def choose_user(library):
    while True:
        print("\nWho is using the library?")
        for user_id, name in library.list_users():
            print(f"  {user_id}. {name}")
        choice = input("Enter user ID, or 'n' to register a new user: ").strip().lower()
        if choice == "n":
            new_id = library.register_user(input("Your name: "))
            if new_id:
                print(f"  Registered! Your user ID is {new_id}.")
                return new_id
        elif choice.isdigit() and library.db.get_user_name(int(choice)):
            return int(choice)
        print("  Invalid choice, try again.")


MENU = [
    ("Search book by ISBN  (hash table, O(1))", search_by_isbn),
    ("Search by title/author/genre (O(n))",      search_by_keyword),
    ("List all books",                           list_books),
    ("Add a book",                               add_book),
    ("Borrow a book  (pushes onto stack)",       borrow_book),
    ("Pre-order a book  (joins queue)",          preorder_book),
    ("Buy a book  (pushes onto stack)",          buy_book),
    ("Return a book  (serves queue)",            return_book),
    ("Sell a book back  (serves queue)",         sell_book),
    ("Show recommendations  (graph + BFS)",      show_recommendations),
    ("View a book's waitlist",                   view_waitlist),
    ("History / Undo  (stack)",                  history_and_undo),
    ("My borrowed books",                        my_loans),
    ("Transaction log (from SQL)",               transaction_log),
]


def main():
    db = Database(DB_FILE)
    if db.count_books() == 0:
        seed_database(db)
        print("First run: sample books and users loaded.")
    library = LibraryService(db)

    print("=" * 50)
    print("   LIBRARY MANAGEMENT SYSTEM")
    print("=" * 50)
    user_id = choose_user(library)

    while True:
        print(f"\n--- Menu (logged in as {library.db.get_user_name(user_id)}) ---")
        for number, (label, _) in enumerate(MENU, start=1):
            print(f"{number:>2}. {label}")
        print(" s. Switch user")
        print(" 0. Exit")

        choice = input("Choose: ").strip().lower()
        if choice == "0":
            print("Goodbye!")
            break
        if choice == "s":
            user_id = choose_user(library)
        elif choice.isdigit() and 1 <= int(choice) <= len(MENU):
            print()
            MENU[int(choice) - 1][1](library, user_id)
        else:
            print("Invalid option.")

    db.close()


if __name__ == "__main__":
    main()
