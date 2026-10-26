import os
import sys

from data_structures import Book
from database import Database

DB_FILE = "library.db"


SAMPLE_BOOKS = [
    Book("9780141439518", "Pride and Prejudice", "Jane Austen", "Romance",
         ["classic", "love", "society"], 6.99, 2, 2),
    Book("9780743273565", "The Great Gatsby", "F. Scott Fitzgerald", "Classic",
         ["society", "tragedy"], 8.99, 1, 1),
    Book("9780061120084", "To Kill a Mockingbird", "Harper Lee", "Classic",
         ["justice", "society"], 9.49, 2, 2),
    Book("9780451524935", "1984", "George Orwell", "Dystopian",
         ["politics", "future", "classic"], 7.99, 1, 1),
    Book("9780060850524", "Brave New World", "Aldous Huxley", "Dystopian",
         ["future", "science"], 8.49, 2, 2),
    Book("9780547928227", "The Hobbit", "J.R.R. Tolkien", "Fantasy",
         ["adventure", "magic"], 10.99, 3, 3),
    Book("9780439708180", "Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "Fantasy",
         ["magic", "school", "adventure"], 11.99, 2, 2),
    Book("9780441172719", "Dune", "Frank Herbert", "Science Fiction",
         ["future", "politics", "adventure"], 12.99, 1, 1),
    Book("9780553380163", "A Brief History of Time", "Stephen Hawking", "Science",
         ["physics", "space"], 13.50, 2, 2),
    Book("9780345539434", "Cosmos", "Carl Sagan", "Science",
         ["space", "science fiction"], 14.00, 2, 2),
    Book("9780062315007", "The Alchemist", "Paulo Coelho", "Fiction",
         ["adventure", "philosophy"], 9.99, 2, 2),
    Book("9780307474278", "The Da Vinci Code", "Dan Brown", "Thriller",
         ["mystery", "adventure"], 8.99, 2, 2),
]

SAMPLE_USERS = ["Asha", "Ravi", "Meera", "John"]


def seed_database(db):
    for book in SAMPLE_BOOKS:
        db.insert_book(book)
    for name in SAMPLE_USERS:
        db.insert_user(name)
    db.commit()


if __name__ == "__main__":
    if "--reset" in sys.argv and os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("Old database deleted.")
    database = Database(DB_FILE)
    if database.count_books() == 0:
        seed_database(database)
        print(f"Database ready: {len(SAMPLE_BOOKS)} books, {len(SAMPLE_USERS)} users.")
    else:
        print("Database already has data. Use --reset to start over.")
    database.close()
