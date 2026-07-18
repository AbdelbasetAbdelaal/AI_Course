import sqlite3
import requests
import json
import os
from langchain_core.tools import tool
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine

DB_PATH = "chinook.db"

def get_engine_for_chinook_db():
    """Pull sql file, populate local database, and create engine."""
    if not os.path.exists(DB_PATH):
        url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        response = requests.get(url)
        response.raise_for_status()
        sql_script = response.text
        connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        connection.executescript(sql_script)
        connection.close()
        
    return create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False}
    )

# Initialize the database engine and utility
engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)

def execute_query(query: str, params: tuple = ()) -> list[dict]:
    """Helper to execute SQL queries and return results as a list of dicts."""
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        raw_conn.close()

@tool
def get_albums_by_artist(artist: str) -> str:
    """Retrieves albums by a given artist."""
    query = "SELECT Album.Title FROM Album JOIN Artist ON Album.ArtistId = Artist.ArtistId WHERE Artist.Name LIKE ?"
    try:
        results = execute_query(query, (f"%{artist}%",))
        if not results:
            return f"No albums found for artist: {artist}"
        return json.dumps([r['Title'] for r in results])
    except Exception as e:
        return f"Error: {e}"

@tool
def get_tracks_by_artist(artist: str) -> str:
    """Retrieves tracks (songs) by a given artist or similar artists."""
    query = "SELECT Track.Name as TrackName, Album.Title as AlbumTitle FROM Track JOIN Album ON Track.AlbumId = Album.AlbumId JOIN Artist ON Album.ArtistId = Artist.ArtistId WHERE Artist.Name LIKE ? LIMIT 50"
    try:
        results = execute_query(query, (f"%{artist}%",))
        if not results:
            return f"No tracks found for artist: {artist}"
        return json.dumps(results)
    except Exception as e:
        return f"Error: {e}"

@tool
def get_songs_by_genre(genre: str) -> str:
    """Fetches songs that match a specific genre."""
    query = "SELECT Track.Name, Artist.Name as ArtistName FROM Track JOIN Genre ON Track.GenreId = Genre.GenreId JOIN Album ON Track.AlbumId = Album.AlbumId JOIN Artist ON Album.ArtistId = Artist.ArtistId WHERE Genre.Name LIKE ? LIMIT 50"
    try:
        results = execute_query(query, (f"%{genre}%",))
        if not results:
            return f"No songs found for genre: {genre}"
        return json.dumps(results)
    except Exception as e:
        return f"Error: {e}"

@tool
def check_for_songs(song_title: str) -> str:
    """Checks if a song exists by its name and retrieves its details, including album, artist, composer, genre, duration, and price."""
    query = """
        SELECT 
            Track.Name as TrackName, 
            Artist.Name as ArtistName, 
            Album.Title as AlbumTitle, 
            Track.Composer, 
            Genre.Name as GenreName, 
            Track.Milliseconds, 
            Track.UnitPrice 
        FROM Track 
        JOIN Album ON Track.AlbumId = Album.AlbumId 
        JOIN Artist ON Album.ArtistId = Artist.ArtistId 
        LEFT JOIN Genre ON Track.GenreId = Genre.GenreId
        WHERE Track.Name LIKE ? 
        LIMIT 10
    """
    try:
        results = execute_query(query, (f"%{song_title}%",))
        if not results:
            return f"Song '{song_title}' not found in the catalog."
        return json.dumps(results)
    except Exception as e:
        return f"Error: {e}"


@tool
def get_invoices_by_customer_sorted_by_date(customer_id: str) -> str:
    """Retrieves all invoices for a customer, sorted by invoice date (most recent first)."""
    query = "SELECT * FROM Invoice WHERE CustomerId = ? ORDER BY InvoiceDate DESC"
    try:
        results = execute_query(query, (customer_id,))
        if not results:
            return f"No invoices found for customer ID: {customer_id}"
        return json.dumps(results, default=str)
    except Exception as e:
        return f"Error: {e}"

@tool
def get_invoices_sorted_by_unit_price(customer_id: str) -> str:
    """Retrieves all invoices for a customer, sorted by unit price (highest to lowest)."""
    query = "SELECT Invoice.InvoiceId, Invoice.InvoiceDate, InvoiceLine.UnitPrice, Track.Name as TrackName FROM Invoice JOIN InvoiceLine ON Invoice.InvoiceId = InvoiceLine.InvoiceId JOIN Track ON InvoiceLine.TrackId = Track.TrackId WHERE Invoice.CustomerId = ? ORDER BY InvoiceLine.UnitPrice DESC LIMIT 20"
    try:
        results = execute_query(query, (customer_id,))
        if not results:
            return f"No invoices found for customer ID: {customer_id}"
        return json.dumps(results, default=str)
    except Exception as e:
        return f"Error: {e}"

@tool
def get_employee_by_invoice_and_customer(invoice_id: str, customer_id: str) -> str:
    """Retrieves the employee information associated with a specific invoice and customer."""
    query = "SELECT Employee.* FROM Employee JOIN Customer ON Employee.EmployeeId = Customer.SupportRepId JOIN Invoice ON Customer.CustomerId = Invoice.CustomerId WHERE Invoice.InvoiceId = ? AND Customer.CustomerId = ?"
    try:
        results = execute_query(query, (invoice_id, customer_id))
        if not results:
            return f"No employee found for invoice ID: {invoice_id} and customer ID: {customer_id}"
        return json.dumps(results[0], default=str)
    except Exception as e:
        return f"Error: {e}"
