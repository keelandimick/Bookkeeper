import sqlite3
import json
import pandas as pd

class Database:
    def __init__(self, db_path="bookkeeper.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        # Enable foreign key enforcement
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_data TEXT NOT NULL
                )
            """)
            
            # Chart of accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chart_of_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT UNIQUE NOT NULL,
                    category_type TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    transaction_date TEXT,
                    description TEXT,
                    amount REAL,
                    category TEXT,
                    original_data TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id)
                )
            """)
            
            # Categorization rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorization_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    category TEXT NOT NULL,
                    rule_type TEXT DEFAULT 'contains',
                    confidence REAL DEFAULT 1.0,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
        # Clean up any orphaned transactions
        orphaned = self.clean_orphaned_transactions()
        if orphaned > 0:
            print(f"Cleaned up {orphaned} orphaned transactions")
    
    def save_file(self, original_name, display_name, file_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files (original_name, display_name, file_data)
                VALUES (?, ?, ?)
            """, (original_name, display_name, file_data))
            conn.commit()
            return cursor.lastrowid
    
    def update_file_name(self, file_id, new_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE files SET display_name = ? WHERE id = ?
            """, (new_name, file_id))
            conn.commit()
    
    def delete_file(self, file_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Delete transactions first (due to foreign key)
            cursor.execute("DELETE FROM transactions WHERE file_id = ?", (file_id,))
            # Then delete the file
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
    
    def get_files(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, original_name, display_name, upload_date 
                FROM files ORDER BY upload_date DESC
            """)
            return cursor.fetchall()
    
    def get_file_by_id(self, file_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            return cursor.fetchone()
    
    def save_chart_of_accounts(self, categories):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for category in categories:
                # Remove all types of apostrophes from category name and use title case for consistency
                category_clean = category['name'].replace("'", "").replace("'", "").replace("'", "").replace("`", "")
                category_clean = category_clean.strip().title()  # Convert to title case
                cursor.execute("""
                    INSERT OR IGNORE INTO chart_of_accounts (category_name, category_type)
                    VALUES (?, ?)
                """, (category_clean, category.get('type', 'Expense')))
            conn.commit()
    
    def get_chart_of_accounts(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category_name, category_type 
                FROM chart_of_accounts 
                ORDER BY category_name
            """)
            return cursor.fetchall()
    
    def add_category(self, category_name, category_type='Expense'):
        # Remove all types of apostrophes from category name and use title case for consistency
        category_clean = category_name.replace("'", "").replace("'", "").replace("'", "").replace("`", "")
        category_clean = category_clean.strip().title()  # Convert to title case
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO chart_of_accounts (category_name, category_type)
                VALUES (?, ?)
            """, (category_clean, category_type))
            conn.commit()
    
    def save_transactions(self, file_id, transactions_df):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE file_id = ?", (file_id,))
            
            for _, row in transactions_df.iterrows():
                # Handle both 'date' and 'transaction_date' column names
                date_value = row.get('date', row.get('transaction_date', ''))
                # Remove apostrophes from category
                category = row.get('category', '')
                category_clean = category.replace("'", "").replace("'", "").replace("'", "").replace("`", "")
                cursor.execute("""
                    INSERT INTO transactions 
                    (file_id, transaction_date, description, amount, category, original_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    date_value,
                    row.get('description', ''),
                    row.get('amount', 0),
                    category_clean,
                    json.dumps(row.to_dict())
                ))
            conn.commit()
    
    def get_transactions(self, file_id):
        with self.get_connection() as conn:
            df = pd.read_sql_query("""
                SELECT * FROM transactions WHERE file_id = ?
            """, conn, params=(file_id,))
            return df
    
    def save_categorization_rule(self, pattern, category, rule_type='contains', confidence=1.0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO categorization_rules 
                (pattern, category, rule_type, confidence)
                VALUES (?, ?, ?, ?)
            """, (pattern, category, rule_type, confidence))
            conn.commit()
    
    def get_categorization_rules(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pattern, category, rule_type, confidence 
                FROM categorization_rules 
                ORDER BY confidence DESC
            """)
            return cursor.fetchall()
    
    def check_duplicate_file_name(self, original_name):
        """Check if a file with the same original name already exists (case-insensitive)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, display_name FROM files WHERE LOWER(original_name) = LOWER(?)
            """, (original_name,))
            return cursor.fetchone()
    
    def check_duplicate_date_range(self, dates):
        """Check if any existing file has transactions with the same dates"""
        # Handle numpy arrays and pandas series
        if dates is None or (hasattr(dates, '__len__') and len(dates) == 0):
            return None
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Get unique dates as strings for comparison
            unique_dates = list(set(str(d) for d in dates))
            date_placeholders = ','.join(['?' for _ in unique_dates])
            
            cursor.execute(f"""
                SELECT DISTINCT f.id, f.display_name, f.original_name
                FROM files f
                JOIN transactions t ON f.id = t.file_id
                WHERE DATE(t.transaction_date) IN ({date_placeholders})
                GROUP BY f.id
                HAVING COUNT(DISTINCT DATE(t.transaction_date)) = ?
            """, unique_dates + [len(unique_dates)])
            
            return cursor.fetchall()
    
    def clean_orphaned_transactions(self):
        """Remove transactions that don't have a corresponding file"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Find and delete orphaned transactions
            cursor.execute("""
                DELETE FROM transactions 
                WHERE file_id NOT IN (SELECT id FROM files)
            """)
            orphaned_count = cursor.rowcount
            conn.commit()
            return orphaned_count
    
