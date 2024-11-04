from flask import Flask, render_template, redirect, flash, request, g
import os
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'os.urandom(24)'  # Needed for flash messages
DB_FILE = os.path.join(os.path.dirname(__file__), 'homelist.db')

# Function to connect to the database
def connect_db():
    try:
        return sqlite3.connect(DB_FILE)
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None
# Execute a query with error handling
def execute_query(query, params=()):
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
    except sqlite3.Error as e:
        print(f"Database query error: {e}")
        return None

# Initialize the database
def init_db():
    conn = connect_db()
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
    cursor = conn.cursor()

    tables = [
        '''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS containers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location_id INTEGER,
            FOREIGN KEY (location_id) REFERENCES locations(id)
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location_id INTEGER,
            container_id INTEGER,
            type_id INTEGER,
            date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_removed DATETIME,
            FOREIGN KEY (location_id) REFERENCES locations(id),
            FOREIGN KEY (container_id) REFERENCES containers(id),
            FOREIGN KEY (type_id) REFERENCES types(id)
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS transaction_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
        '''
    ]

    for table_sql in tables:
        try:
            cursor.execute(table_sql)
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")

    conn.commit()
    conn.close()
    print("Database initialized.")

# Display all items
def display_items():
    cursor = execute_query('''
        SELECT items.id, items.name, locations.name AS location,
               containers.name AS container, types.name AS type,
               items.date_added, items.date_removed
        FROM items
        LEFT JOIN locations ON items.location_id = locations.id
        LEFT JOIN containers ON items.container_id = containers.id
        LEFT JOIN types ON items.type_id = types.id
    ''')
    return cursor.fetchall() if cursor else []

# Route for the home page
@app.route('/')
def index():
    items = display_items()
    return render_template('index.html', items=items)

# Route to initialize the database
@app.route('/init_db')
def initialize_db():
    init_db()
    flash('Database initialized!')
    return redirect('/')

# Route to add an item
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    if request.method == 'POST':
        try:
            # Extract form data
            item_name = request.form.get('name')
            location_id = request.form.get('location_id')
            container_id = request.form.get('container_id')
            item_type_id = request.form.get('item_type_id')

            # Extract dates from the form
            date_added = request.form.get('date_added') or datetime.now().strftime('%Y-%m-%d %H:%M')
            date_removed = request.form.get('date_removed') or None

            # Ensure all required fields are provided
            if not item_name or not location_id or not container_id or not item_type_id:
                flash('Please fill in all required fields.')
                return redirect('/add_item')

            # Insert the new item into the database
            item_id = create_item(item_name, item_type_id, location_id, container_id, date_added, date_removed)

            if item_id:
                flash('Item added successfully!')
                return redirect('/')
            else:
                flash('Error adding item.')
        except Exception as e:
            flash(f'Error: {e}')
            return redirect('/add_item')

    # Fetch options for dropdowns
    locations = conn.execute('SELECT id, name FROM locations').fetchall()
    containers = conn.execute('SELECT id, name FROM containers').fetchall()
    item_types = conn.execute('SELECT id, name FROM types').fetchall()
    conn.close()

    return render_template('add_item.html', locations=locations, containers=containers, item_types=item_types)

# Create an item
def create_item(name, type_id, location_id, container_id, date_added, date_removed):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO items (name, type_id, location_id, container_id, date_added, date_removed)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (name, type_id, location_id, container_id, date_added, date_removed)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error inserting item: {e}")
        return None
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)







