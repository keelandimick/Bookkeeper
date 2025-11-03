import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
from database import Database
from categorizer import TransactionCategorizer
from utils import *
from helpers import *

# Page configuration
st.set_page_config(
    page_title="Bookkeeper - Financial Reconciliation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = Database()

if 'categorizer' not in st.session_state:
    st.session_state.categorizer = TransactionCategorizer(st.session_state.db)

if 'current_file_id' not in st.session_state:
    st.session_state.current_file_id = None

if 'transactions_df' not in st.session_state:
    st.session_state.transactions_df = pd.DataFrame()

if 'column_mapping' not in st.session_state:
    st.session_state.column_mapping = {}

if 'page_override' not in st.session_state:
    st.session_state.page_override = None

# Sidebar navigation
st.sidebar.title("📊 Bookkeeper")
st.sidebar.markdown("---")

# Show file status
if st.session_state.current_file_id:
    # Get file name for display
    current_file = st.session_state.db.get_file_by_id(st.session_state.current_file_id)
    if current_file:
        file_name = current_file[2]  # display_name
        st.sidebar.caption(f"📂 Viewing saved file: {file_name}")
else:
    if 'transactions_df' in st.session_state and not st.session_state.transactions_df.empty:
        st.sidebar.caption("📝 Working with unsaved file")

# Create navigation sections
transaction_pages = [
    "Upload & Map Files",
    "Categorize Transactions",
    "Review"
]

management_pages = [
    "Manage Chart of Accounts",
    "P&L Summary",
    "File Management",
    "Settings"
]

all_pages = transaction_pages + management_pages

# Handle page override if set
if st.session_state.page_override:
    st.session_state.selected_page = st.session_state.page_override
    st.session_state.page_override = None  # Clear override after use

# Initialize selected_page if not exists
if 'selected_page' not in st.session_state:
    st.session_state.selected_page = "Upload & Map Files"

# Custom CSS to style buttons like radio buttons
st.markdown("""
<style>
    .stButton > button {
        background-color: transparent;
        color: inherit;
        border: none;
        padding: 0.25rem 0.5rem;
        text-align: left !important;
        justify-content: flex-start !important;
        width: 100%;
        border-radius: 0.25rem;
        font-size: 1rem;
        font-weight: 400;
    }
    .stButton > button:hover {
        background-color: rgba(151, 166, 195, 0.15);
    }
    .stButton > button[kind="primary"] {
        background-color: rgba(255, 75, 75, 0.1);
        color: rgb(255, 75, 75);
    }
    /* Reduce spacing between buttons */
    .stButton {
        margin-bottom: -0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Create sidebar navigation with buttons
st.sidebar.subheader("Transaction Processing")
for page_name in transaction_pages:
    if st.sidebar.button(
        page_name, 
        key=f"nav_{page_name}",
        use_container_width=True,
        type="primary" if st.session_state.selected_page == page_name else "secondary"
    ):
        st.session_state.selected_page = page_name
        st.session_state.show_saved_message = False
        st.rerun()

st.sidebar.markdown("---")  # Divider line

st.sidebar.subheader("Management & Reports")  
for page_name in management_pages:
    if st.sidebar.button(
        page_name,
        key=f"nav_{page_name}", 
        use_container_width=True,
        type="primary" if st.session_state.selected_page == page_name else "secondary"
    ):
        st.session_state.selected_page = page_name
        st.session_state.show_saved_message = False
        st.rerun()

page = st.session_state.selected_page

# Main content area
if page == "Upload & Map Files":
    st.header("Upload & Map CSV Files")
    
    # Check if there's already a file being worked on
    if 'transactions_df' in st.session_state and not st.session_state.transactions_df.empty:
        if st.session_state.current_file_id:
            # Get the current file name
            current_file = st.session_state.db.get_file_by_id(st.session_state.current_file_id)
            if current_file:
                file_name = current_file[2]  # display_name
                st.warning(f"⚠️ Currently working with: {file_name}. Uploading a new file will replace this one and delete any unsaved changes.")
        else:
            st.warning("⚠️ You currently have unsaved work. Uploading a new file will replace it.")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV file", 
        type=['csv'],
        help="Upload your transaction data exported from Excel or Numbers"
    )
    
    if uploaded_file is not None:
        # Clear any existing work when new file is uploaded
        if ('transactions_df' in st.session_state and not st.session_state.transactions_df.empty) or st.session_state.current_file_id is not None:
            st.session_state.current_file_id = None
            st.session_state.transactions_df = pd.DataFrame()
            st.session_state.original_filename = None
            st.session_state.original_df = None
            st.session_state.unsaved_changes_count = 0
            if 'original_categories' in st.session_state:
                del st.session_state.original_categories
            st.rerun()
            
        # Read the file
        file_content = io.StringIO(uploaded_file.read().decode('utf-8'))
        df, error = parse_csv_data(file_content)
        
        if error:
            st.error(error)
        else:
            st.success(f"File uploaded successfully! Found {len(df)} rows and {len(df.columns)} columns.")
            
            # Check for duplicate file name
            duplicate_file = st.session_state.db.check_duplicate_file_name(uploaded_file.name)
            if duplicate_file:
                st.error(f"⚠️ A file with the name '{uploaded_file.name}' already exists as '{duplicate_file[1]}'. Please rename your file or delete the existing one from File Management.")
                st.stop()
            
            # Column mapping
            st.subheader("Column Mapping")
            st.info("Map your CSV columns to the required fields.")
            
            # Detect column types
            detected_types = detect_column_types(df)
            
            col_map_1, col_map_2, col_map_3, col_map_4 = st.columns(4)
            
            with col_map_1:
                date_col = create_column_mapping_ui(df, 'date', detected_types, "Date Column*")
            
            with col_map_2:
                desc_col = create_column_mapping_ui(df, 'description', detected_types, "Description Column*")
            
            with col_map_3:
                amount_col = create_column_mapping_ui(df, 'amount', detected_types, "Amount Column*")
            
            with col_map_4:
                category_col = create_column_mapping_ui(df, 'category', detected_types, "Category Column (Optional)")
            
            # Display preview after mapping
            st.subheader("Mapped Data Preview")
            
            # Show preview only if required columns are selected
            if date_col != 'None' and desc_col != 'None' and amount_col != 'None':
                preview_df = pd.DataFrame()
                preview_df['Date'] = df[date_col].head(10)
                preview_df['Amount'] = df[amount_col].apply(clean_amount).head(10)
                
                if category_col != 'None':
                    preview_df['Category'] = df[category_col].head(10)
                else:
                    preview_df['Category'] = ''
                    
                preview_df['Description'] = df[desc_col].head(10)
                
                # Format the preview nicely
                st.dataframe(
                    preview_df,
                    column_config={
                        'Date': st.column_config.TextColumn('Date'),
                        'Amount': st.column_config.NumberColumn('Amount', format="$%.2f"),
                        'Category': st.column_config.TextColumn('Category'),
                        'Description': st.column_config.TextColumn('Description')
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Select all required columns (Date, Description, Amount) to see the preview")
            
            # Process file button
            if st.button("Process File", type="primary"):
                if date_col != 'None' and desc_col != 'None' and amount_col != 'None':
                        # Check for duplicate dates before processing
                        dates_in_file = df[date_col].dropna().unique()
                        duplicate_files = st.session_state.db.check_duplicate_date_range(dates_in_file)
                        
                        if duplicate_files:
                            st.error("⚠️ Found existing file(s) with the same date range:")
                            for dup in duplicate_files:
                                st.error(f"   • {dup[2]} (saved as '{dup[1]}')")
                            st.error("Please check File Management to avoid duplicating data.")
                            st.stop()
                        
                        # Create standardized dataframe
                        processed_df = pd.DataFrame()
                        # Keep dates as strings for JSON serialization
                        processed_df['date'] = df[date_col].astype(str)
                        processed_df['description'] = df[desc_col]
                        processed_df['amount'] = df[amount_col].apply(clean_amount)
                        
                        # Handle category column
                        if category_col != 'None':
                            processed_df['category'] = df[category_col].fillna('')
                            # Learn from these categories
                            if not processed_df.empty:
                                # Add categories to Chart of Accounts if they don't exist
                                existing_categories = extract_categories_from_coa(st.session_state.db.get_chart_of_accounts())
                                new_categories = processed_df['category'].dropna().unique()
                                for cat in new_categories:
                                    if cat and cat not in existing_categories:
                                        st.session_state.db.add_category(cat)
                        else:
                            processed_df['category'] = ''
                        
                        # Save original data
                        for col in df.columns:
                            if col not in [date_col, desc_col, amount_col, category_col]:
                                processed_df[f'original_{col}'] = df[col]
                        
                        # Store in session
                        st.session_state.transactions_df = processed_df
                        st.session_state.original_filename = uploaded_file.name
                        st.session_state.original_df = df  # Keep original for later saving
                        
                        # Reset unsaved changes tracking
                        st.session_state.unsaved_changes_count = 0
                        if 'original_categories' in st.session_state:
                            del st.session_state.original_categories
                        
                        # Auto-save the file
                        st.session_state.current_file_id = auto_save_transactions(
                            st.session_state.db,
                            None,  # No existing file_id
                            uploaded_file.name,
                            df,
                            processed_df
                        )
                        
                        st.success("File processed and saved successfully! Redirecting to Categorize Transactions...")
                        # Set page override for navigation
                        st.session_state.page_override = "Categorize Transactions"
                        st.rerun()
                else:
                    st.error("Please map all required columns (Date, Description, Amount)")

elif page == "Manage Chart of Accounts":
    st.header("Chart of Accounts Management")
    
    # Get current chart of accounts
    coa = st.session_state.db.get_chart_of_accounts()
    
    st.info("✏️ Edit categories directly in the table below. You can add new rows, modify existing ones, or delete categories.")
    
    # Create editable dataframe
    if coa:
        coa_df = pd.DataFrame(coa, columns=['Category', 'Type'])
    else:
        # Start with empty dataframe if no categories exist
        coa_df = pd.DataFrame(columns=['Category', 'Type'])
    
    # Use data editor for full CRUD operations
    edited_coa = st.data_editor(
        coa_df,
        column_config={
            'Category': st.column_config.TextColumn(
                'Category Name',
                help='Name of the category',
                required=True
            ),
            'Type': st.column_config.SelectboxColumn(
                'Category Type',
                help='Select the category type',
                options=['Income', 'Expense', 'COGS', 'Other Income', 'Balance Sheet'],
                required=True,
                default='Expense'
            )
        },
        num_rows="dynamic",
        use_container_width=True
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("Save Changes", type="primary"):
            # First, clear all existing categories
            with st.session_state.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chart_of_accounts")
                conn.commit()
            
            # Then add all categories from the edited dataframe
            for _, row in edited_coa.iterrows():
                if row['Category']:  # Only add if category name is not empty
                    st.session_state.db.add_category(row['Category'], row['Type'])
            
            st.success("Chart of Accounts updated!")
            st.rerun()
    
    with col2:
        if not coa:
            if st.button("Initialize with Defaults"):
                default_categories = [
                    # Income
                    ('Sales Revenue', 'Income'),
                    ('Service Revenue', 'Income'),
                    ('Other Income', 'Income'),
                    # COGS
                    ('Cost of Goods Sold', 'COGS'),
                    ('Materials & Supplies', 'COGS'),
                    ('Direct Labor', 'COGS'),
                    ('Freight & Shipping', 'COGS'),
                    # Expenses
                    ('Rent', 'Expense'),
                    ('Utilities', 'Expense'),
                    ('Salaries & Wages', 'Expense'),
                    ('Office Supplies', 'Expense'),
                    ('Transportation', 'Expense'),
                    ('Insurance', 'Expense'),
                    ('Marketing', 'Expense'),
                    ('Professional Fees', 'Expense'),
                    ('Repairs & Maintenance', 'Expense'),
                    ('Meals & Entertainment', 'Expense'),
                    ('Other Expenses', 'Expense'),
                    # Balance Sheet
                    ('Equipment Purchase', 'Balance Sheet'),
                    ('Loan Payment', 'Balance Sheet'),
                    ('Owner Investment', 'Balance Sheet'),
                    ('Owner Draw', 'Balance Sheet')
                ]
                for cat_name, cat_type in default_categories:
                    st.session_state.db.add_category(cat_name, cat_type)
                st.success("Default categories added!")
                st.rerun()
    
    with col3:
        # Bulk import option
        with st.expander("Bulk Import from CSV"):
            st.info("Upload a CSV with 'Category' and 'Type' columns")
            
            # Add sample CSV download
            sample_csv = """Category,Type
Rent,Expense
Utilities,Expense
Office Supplies,Expense
Sales Revenue,Income
Service Revenue,Income
Cost of Goods Sold,COGS
Equipment Purchase,Balance Sheet
Owner Draw,Balance Sheet"""
            
            st.download_button(
                label="📥 Download Sample CSV",
                data=sample_csv,
                file_name="chart_of_accounts_sample.csv",
                mime="text/csv",
                help="Download a sample CSV file to see the required format"
            )
            
            coa_file = st.file_uploader("Chart of Accounts CSV", type=['csv'])
            if coa_file is not None:
                # Show preview of the file
                import_df = pd.read_csv(coa_file)
                st.write(f"Found {len(import_df)} rows in CSV")
                
                # Check if correct columns exist
                if 'Category' in import_df.columns or 'category' in import_df.columns:
                    # Show preview
                    st.dataframe(import_df.head(5))
                    
                    if st.button("Import Categories", type="primary", key="import_coa"):
                        categories = []
                        for _, row in import_df.iterrows():
                            cat_name = row.get('Category', row.get('category', ''))
                            cat_type = row.get('Type', row.get('type', 'Expense'))
                            if cat_name:
                                categories.append({'name': cat_name, 'type': cat_type})
                        
                        st.session_state.db.save_chart_of_accounts(categories)
                        st.success(f"Imported {len(categories)} categories")
                        st.rerun()
                else:
                    st.error("CSV must have a 'Category' column (and optionally a 'Type' column)")
    

elif page == "Categorize Transactions":
    if 'transactions_df' not in st.session_state or st.session_state.transactions_df.empty:
        st.header("Categorize Transactions")
        st.warning("Please upload a new file in 'Upload & Map Files' or open an existing file from 'File Management'")
    else:
        # Get file info
        if st.session_state.current_file_id:
            current_file = st.session_state.db.get_file_by_id(st.session_state.current_file_id)
            file_display_name = current_file[2] if current_file else "Unknown File"
        else:
            file_display_name = getattr(st.session_state, 'original_filename', 'Unsaved File')
        
        # Get uncategorized count
        uncategorized_count = len(st.session_state.transactions_df[get_uncategorized_mask(st.session_state.transactions_df)])
        
        # Header with file info
        st.header("Categorize Transactions")
        st.info(f"📄 Working with: **{file_display_name}**")
        
        # Count on the right
        col1, col2 = st.columns([3, 1])
        with col1:
            pass  # Empty column for spacing
        with col2:
            color = '#28a745' if uncategorized_count == 0 else '#dc3545'  # Green if 0, red if > 0
            st.markdown(f"<h2 style='text-align: right; color: {color};'>{uncategorized_count} Uncategorized</h2>", unsafe_allow_html=True)
        
        # Get chart of accounts
        coa = st.session_state.db.get_chart_of_accounts()
        categories = extract_categories_from_coa(coa) + ['Uncategorized']
        
        # Run auto-categorization
        if st.button("Auto-Categorize Transactions", type="primary"):
            # Count uncategorized transactions
            uncategorized_mask = get_uncategorized_mask(st.session_state.transactions_df)
            uncategorized_count = uncategorized_mask.sum()
            
            if uncategorized_count == 0:
                st.info("All transactions are already categorized!")
            else:
                # Simple progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(progress):
                    progress_bar.progress(progress)
                    done = int(progress * uncategorized_count)
                    status_text.text(f"Categorizing transactions... {done}/{uncategorized_count} complete")
                
                # Categorize transactions
                st.session_state.transactions_df = st.session_state.categorizer.categorize_transactions(
                    st.session_state.transactions_df,
                    progress_callback=update_progress
                )
                
                # Clean up and show success
                progress_bar.empty()
                status_text.empty()
                
                # Auto-save after categorization
                st.session_state.current_file_id = auto_save_transactions(
                    st.session_state.db,
                    st.session_state.current_file_id,
                    st.session_state.original_filename,
                    st.session_state.original_df,
                    st.session_state.transactions_df
                )
                
                st.success(f"Auto-categorization complete! Categorized {uncategorized_count} transactions.")
                # Rerun to update the uncategorized count in the header
                st.rerun()
        
        # Search All Transactions section
        st.subheader("🔍 Search All Transactions")
        
        search_term = st.text_input(
            "Search transactions", 
            placeholder="Search by description, category, amount, or date...",
            label_visibility="collapsed"
        )
        
        # Perform search automatically when there's a search term
        if search_term:
            # Gather all transactions from all sources
            all_search_transactions = pd.DataFrame()
            
            # 1. Get transactions from all saved files in database
            saved_files = st.session_state.db.get_files()
            for file_id, original_name, display_name, upload_date in saved_files:
                file_transactions = st.session_state.db.get_transactions(file_id)
                if not file_transactions.empty:
                    # Normalize date column name - database uses 'transaction_date', current file uses 'date'
                    if 'transaction_date' in file_transactions.columns and 'date' not in file_transactions.columns:
                        file_transactions['date'] = file_transactions['transaction_date']
                    # Add file source info
                    file_transactions['source_file'] = display_name
                    all_search_transactions = pd.concat([all_search_transactions, file_transactions], ignore_index=True)
    
            # 2. Add current working file transactions (if not already saved)
            if 'transactions_df' in st.session_state and not st.session_state.transactions_df.empty:
                current_trans = st.session_state.transactions_df.copy()
                # Check if current file is already in saved files
                if st.session_state.current_file_id:
                    # It's saved, so it's already included above
                    pass
                else:
                    # It's unsaved, add it with a special marker
                    current_trans['source_file'] = f"[Unsaved] {st.session_state.original_filename if 'original_filename' in st.session_state else 'Current File'}"
                    all_search_transactions = pd.concat([all_search_transactions, current_trans], ignore_index=True)
    
            if not all_search_transactions.empty:
                # Case-insensitive search across multiple columns
                search_term_lower = search_term.lower()
            
                # Initialize mask as all False
                search_mask = pd.Series([False] * len(all_search_transactions))
                
                # Search in description
                if 'description' in all_search_transactions.columns:
                    search_mask |= all_search_transactions['description'].str.lower().str.contains(
                        search_term_lower, na=False, regex=False
                    )
                
                # Search in category
                if 'category' in all_search_transactions.columns:
                    search_mask |= all_search_transactions['category'].str.lower().str.contains(
                        search_term_lower, na=False, regex=False
                    )
                
                # Search in amount (convert to string for comparison)
                if 'amount' in all_search_transactions.columns:
                    # Handle both exact amount and amount in description
                    amount_str = all_search_transactions['amount'].astype(str)
                    search_mask |= amount_str.str.contains(search_term, na=False)
                    
                    # Also check for formatted amounts (e.g., searching for "89.99" should find -89.99)
                    search_mask |= all_search_transactions['amount'].abs().astype(str).str.contains(
                        search_term.replace('$', '').replace(',', ''), na=False
                    )
                
                # Search in date columns
                date_col = get_date_column(all_search_transactions)
                if date_col and date_col in all_search_transactions.columns:
                    # Convert date to string for searching
                    search_mask |= all_search_transactions[date_col].astype(str).str.lower().str.contains(
                        search_term_lower, na=False, regex=False
                    )
                elif 'transaction_date' in all_search_transactions.columns:
                    search_mask |= all_search_transactions['transaction_date'].astype(str).str.lower().str.contains(
                        search_term_lower, na=False, regex=False
                    )
                
                # Apply the combined search mask
                search_results = all_search_transactions[search_mask].copy()
                
                if not search_results.empty:
                    # Display results count
                    st.info(f"Found {len(search_results)} transactions matching '{search_term}' across {search_results['source_file'].nunique()} file(s)")
                    
                    # Prepare display dataframe
                    date_col = get_date_column(search_results)
                    if date_col:
                        display_cols = [date_col, 'description', 'amount', 'category', 'source_file']
                    else:
                        # Handle case where date column might be different
                        if 'transaction_date' in search_results.columns:
                            display_cols = ['transaction_date', 'description', 'amount', 'category', 'source_file']
                        else:
                            display_cols = ['description', 'amount', 'category', 'source_file']
                    
                    # Sort by date (newest first) if date column exists
                    if date_col and date_col in display_cols:
                        search_results = search_results.sort_values(date_col, ascending=False)
                    
                    # Add index and file_id for tracking
                    search_results['row_idx'] = range(len(search_results))
                    
                    # Get categories for dropdown
                    coa = st.session_state.db.get_chart_of_accounts()
                    categories = ['Uncategorized'] + extract_categories_from_coa(coa)
                    
                    # Create editable dataframe
                    config = {
                        'description': st.column_config.TextColumn('Description', width="medium"),
                        'amount': st.column_config.NumberColumn('Amount', format="$%.2f"),
                        'category': st.column_config.SelectboxColumn(
                            'Category',
                            options=categories,
                            default='Uncategorized',
                            width="small"
                        ),
                        'source_file': st.column_config.TextColumn('File', width="small"),
                        'row_idx': None,
                        'id': None,
                        'file_id': None
                    }
                    
                    if date_col and date_col in display_cols:
                        config[date_col] = st.column_config.TextColumn('Date', width="small")
                    elif 'transaction_date' in display_cols:
                        config['transaction_date'] = st.column_config.TextColumn('Date', width="small")
                    
                    # Make the dataframe editable
                    edited_df = st.data_editor(
                        search_results[display_cols + ['row_idx', 'id', 'file_id']],
                        column_config=config,
                        use_container_width=True,
                        height=min(400, len(search_results) * 35 + 50),  # Dynamic height with max
                        hide_index=True,
                        disabled=[col for col in display_cols if col != 'category'],  # Only category is editable
                        key="categorize_search_editor"
                    )
                    
                    # Check for category changes and save automatically
                    for idx, row in edited_df.iterrows():
                        original_idx = row['row_idx']
                        new_category = row['category']
                        original_category = search_results.loc[search_results['row_idx'] == original_idx, 'category'].iloc[0]
                        
                        if new_category != original_category:
                            # Update the specific transaction directly in the database
                            file_id = row['file_id']
                            trans_id = row['id']
                            
                            # Get the file's transactions
                            file_transactions = st.session_state.db.get_transactions(file_id)
                            
                            # Update the category
                            file_transactions.loc[file_transactions['id'] == trans_id, 'category'] = new_category
                            
                            # Save back to database
                            st.session_state.db.save_transactions(file_id, file_transactions)
                            
                            # Update current file's display if it's the same file
                            if file_id == st.session_state.current_file_id and 'id' in st.session_state.transactions_df.columns:
                                mask = st.session_state.transactions_df['id'] == trans_id
                                if mask.any():
                                    st.session_state.transactions_df.loc[mask, 'category'] = new_category
                    
                    # Summary of search results
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Amount", f"${search_results['amount'].sum():,.2f}")
                    with col2:
                        income = search_results[search_results['amount'] > 0]['amount'].sum()
                        st.metric("Total Income", f"${income:,.2f}")
                    with col3:
                        expenses = abs(search_results[search_results['amount'] < 0]['amount'].sum())
                        st.metric("Total Expenses", f"${expenses:,.2f}")
                else:
                    st.warning(f"No transactions found matching '{search_term}'")
            else:
                st.warning("No transactions available to search")
        
        st.markdown("---")
        
        # Display transactions with unsaved changes counter
        if 'unsaved_changes_count' not in st.session_state:
            st.session_state.unsaved_changes_count = 0
            
        if st.session_state.unsaved_changes_count > 0:
            st.markdown(f"### Transaction Categorization <span style='font-size: 0.7em; color: #FF6B6B; font-weight: normal;'>({st.session_state.unsaved_changes_count} unsaved)</span>", unsafe_allow_html=True)
        else:
            st.subheader("Transaction Categorization")
        
        # All controls in one row
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        
        with col1:
            filter_category = st.selectbox("Filter by Category", ['All'] + categories)
        
        with col2:
            filter_amount = st.selectbox("Filter by Amount", ['All', 'Income (>0)', 'Expenses (<0)'])
        
        with col3:
            sort_column = st.selectbox("Sort by:", options=['Date', 'Description', 'Amount', 'Category'], key="sort_column")
        
        with col4:
            sort_order = st.radio("Order:", options=['Ascending', 'Descending'], horizontal=True, key="sort_order")
        
        with col5:
            filter_uncategorized = st.checkbox("Show only uncategorized", value=False)
        
        # Apply filters - keep track of original indices
        display_df = st.session_state.transactions_df.copy()
        # Store original index before filtering
        display_df['_original_index'] = display_df.index
        
        if filter_category != 'All':
            display_df = display_df[display_df['category'] == filter_category]
        if filter_uncategorized:
            display_df = display_df[get_uncategorized_mask(display_df)]
        if filter_amount == 'Income (>0)':
            display_df = display_df[display_df['amount'] > 0]
        elif filter_amount == 'Expenses (<0)':
            display_df = display_df[display_df['amount'] < 0]
        
        if not display_df.empty:
            # Add new category section
            with st.expander("➕ Add New Category", expanded=False):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    # Initialize session state for the input if not exists
                    if 'new_category_input_value' not in st.session_state:
                        st.session_state.new_category_input_value = ""
                    new_category = st.text_input("Category Name", value=st.session_state.new_category_input_value, key="new_category_input")
                with col2:
                    if 'new_category_type_value' not in st.session_state:
                        st.session_state.new_category_type_value = 1  # Default to "Expense"
                    category_type = st.selectbox("Type", ["Income", "Expense", "COGS", "Other Income", "Balance Sheet"], index=st.session_state.new_category_type_value, key="new_category_type")
                with col3:
                    if st.button("Add Category", type="secondary"):
                        if new_category and new_category not in categories:
                            st.session_state.db.add_category(new_category, category_type)
                            st.toast(f"✅ Added '{new_category}'", icon="✅")
                            # Clear the input fields
                            st.session_state.new_category_input_value = ""
                            st.session_state.new_category_type_value = 1  # Reset to "Expense"
                            st.rerun()
                        elif new_category in categories:
                            st.toast("Category already exists", icon="⚠️")
                        else:
                            st.toast("Please enter a category name", icon="⚠️")
            
            # Determine date column name
            date_col = get_date_column(display_df)
            
            # Apply sorting
            sort_col_map = {
                'Date': date_col,
                'Description': 'description', 
                'Amount': 'amount',
                'Category': 'category'
            }
            sort_ascending = sort_order == 'Ascending'
            display_df = display_df.sort_values(
                by=sort_col_map[sort_column],
                ascending=sort_ascending
            ).reset_index(drop=True)
            
            
            # Create editable view (excluding the _original_index column)
            # Use appropriate date column
            display_columns = [date_col, 'amount', 'category', 'description']
            
            # Store original categories to track changes
            # Reset original_categories when file changes or on first load
            if ('original_categories' not in st.session_state or 
                st.session_state.get('last_file_id') != st.session_state.current_file_id):
                st.session_state.original_categories = {}
                st.session_state.last_file_id = st.session_state.current_file_id
                # Populate with the current saved state from transactions_df
                for idx in st.session_state.transactions_df.index:
                    st.session_state.original_categories[idx] = st.session_state.transactions_df.loc[idx, 'category']
            
            edited_df = st.data_editor(
                display_df[display_columns],
                column_config={
                    date_col: st.column_config.TextColumn('Date'),
                    'amount': st.column_config.NumberColumn('Amount', format="$%.2f"),
                    'category': st.column_config.SelectboxColumn(
                        'Category',
                        options=categories,
                        default='Uncategorized'
                    ),
                    'description': st.column_config.TextColumn('Description')
                },
                use_container_width=True,
                num_rows="dynamic",
                key="transaction_editor"
            )
            
            # Track unsaved changes
            unsaved_count = 0
            for idx in edited_df.index:
                original_idx = display_df.loc[idx, '_original_index']
                new_cat = edited_df.loc[idx, 'category']
                original_cat = st.session_state.original_categories.get(original_idx, '')
                if new_cat != original_cat:
                    unsaved_count += 1
            
            st.session_state.unsaved_changes_count = unsaved_count
            
            # Show saved message if flag is set
            if st.session_state.get('show_saved_message', False):
                st.success("✅ Categories saved successfully!")
                st.session_state.show_saved_message = False
            
            # Add Save button
            if st.button("Save Changes", type="primary", key="save_categorization"):
                # Update categories in the session state
                for idx in edited_df.index:
                    original_idx = display_df.loc[idx, '_original_index']
                    new_cat = edited_df.loc[idx, 'category']
                    st.session_state.transactions_df.loc[original_idx, 'category'] = new_cat
                    # Update original categories tracker
                    st.session_state.original_categories[original_idx] = new_cat
                
                # Save to database if we have a file
                if st.session_state.current_file_id:
                    auto_save_transactions(
                        st.session_state.db,
                        st.session_state.current_file_id,
                        st.session_state.original_filename,
                        st.session_state.original_df,
                        st.session_state.transactions_df
                    )
                    st.session_state.show_saved_message = True
                else:
                    st.warning("⚠️ File not saved. Categories updated in memory only.")
                
                # Reset unsaved changes count
                st.session_state.unsaved_changes_count = 0
                st.rerun()
        
        # Research Transaction section (always visible)
        st.markdown("---")
        st.subheader("🔍 Research Transaction")
        
        if not display_df.empty:
            # Create transaction options for selectbox
            transaction_options = []
            for idx in display_df.index:  # Include all transactions
                desc = display_df.loc[idx, 'description']
                amount = display_df.loc[idx, 'amount']
                date_str = display_df.loc[idx, date_col] if date_col else ""
                category = display_df.loc[idx, 'category']
                transaction_options.append(f"{date_str} | {desc[:50]}... | ${amount:.2f} | {category}")
            
            col1, col2 = st.columns([5, 1])
            
            with col1:
                selected = st.selectbox(
                    "Select a transaction to analyze:",
                    options=["Choose a transaction..."] + transaction_options,
                    key="transaction_research"
                )
            
            with col2:
                if selected != "Choose a transaction...":
                    if st.button("✕ Clear", key="clear_research"):
                        st.session_state.transaction_research = "Choose a transaction..."
                        st.rerun()
            
            if selected != "Choose a transaction...":
                # Get the actual transaction index
                trans_idx = transaction_options.index(selected)
                row = display_df.iloc[trans_idx]
                
                # Get transaction details
                trans_desc = row['description']
                trans_amount = row['amount']
                trans_date = row[date_col] if date_col else "Unknown date"
                current_category = row['category']
                
                # Show AI analysis
                st.markdown("### 🤖 AI Analysis")
                
                with st.spinner("Analyzing transaction..."):
                    available_categories = [cat for cat in categories if cat != 'Uncategorized']
                    
                    # Clean the description by removing common unimportant words
                    cleaned_desc = trans_desc
                    for remove_word in ['PURCHASE AUTHORIZED ON', 'CARD', 'DEBIT', 'CREDIT', 'ON', 'AT']:
                        cleaned_desc = cleaned_desc.replace(remove_word, '')
                    # Remove card numbers (4+ digits)
                    import re
                    cleaned_desc = re.sub(r'\b\d{4,}\b', '', cleaned_desc)
                    cleaned_desc = ' '.join(cleaned_desc.split())  # Clean up extra spaces
                    
                    prompt = f"""Transaction: {trans_desc}
Amount: ${trans_amount:.2f}

Search for: "{cleaned_desc}"

Available categories: {', '.join(available_categories)}

CRITICAL: You MUST choose a category from the exact list above. Do NOT create new categories or modify spellings. Match letter-for-letter only.

Based on findings on web search, deduce what the user's transaction is all about with the goal of recommending the most correct category based on the user's chart of accounts.

Format your response EXACTLY like this:
1. What: 1-2 sentences about the vendor and how it relates to the user (mention location if present)
2. Category: **:green[Entertainment]** (replace Entertainment with your chosen category, keep the green formatting)
3. Why: Explain reasoning citing specific keywords from the description

The key insight: Transaction amount + location name/other keywords + one-time or recurring payment all informs category decision.

CRUCIAL: For transactions through ticketing platforms (Ludus, Ticketmaster, etc.), you are buying EVENT TICKETS, not the platform's software. Look for venue names/cities in the description - these indicate ticket purchases, not software subscriptions.

Keep total response under 100 words."""

                    try:
                        # Use Perplexity API for real-time web search
                        import requests
                        import os
                        
                        perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
                        
                        headers = {
                            'Authorization': f'Bearer {perplexity_api_key}',
                            'Content-Type': 'application/json'
                        }
                        
                        perplexity_payload = {
                            "model": "sonar",  # Basic search model with web access
                            "messages": [
                                {
                                    "role": "system", 
                                    "content": "You are a financial categorization assistant. Search the web to identify merchants. Be extremely concise."
                                },
                                {
                                    "role": "user", 
                                    "content": prompt
                                }
                            ],
                            "temperature": 0.2,
                            "max_tokens": 200
                        }
                        
                        response = requests.post(
                            'https://api.perplexity.ai/chat/completions',
                            headers=headers,
                            json=perplexity_payload
                        )
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            ai_response = response_data['choices'][0]['message']['content']
                            st.markdown(ai_response)
                        else:
                            st.error(f"Perplexity API error: {response.status_code} - {response.text}")
                                
                    except Exception as e:
                        st.error(f"Error analyzing transaction: {str(e)}")

elif page == "Review":
    st.header("Review Reconciliation")
    
    if 'transactions_df' not in st.session_state or st.session_state.transactions_df.empty:
        st.warning("Please upload a new file in 'Upload & Map Files' or open an existing file from 'File Management'")
    else:
        # Use transactions from session state
        transactions_df = st.session_state.transactions_df
        
        if transactions_df.empty:
            st.info("No transactions to review.")
        else:
            # Summary statistics
            col_stat_1, col_stat_2, col_stat_3, col_stat_4 = st.columns(4)
            with col_stat_1:
                st.metric("Total Transactions", len(transactions_df))
            with col_stat_2:
                st.metric("Categorized", len(transactions_df[transactions_df['category'].notna() & (transactions_df['category'] != '')]))
            with col_stat_3:
                st.metric("Total In", f"${transactions_df[transactions_df['amount'] > 0]['amount'].sum():,.2f}")
            with col_stat_4:
                st.metric("Total Out", f"${abs(transactions_df[transactions_df['amount'] < 0]['amount'].sum()):,.2f}")
            
            # Category breakdown
            st.subheader("Category Breakdown")
            category_summary = transactions_df.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
            category_summary.columns = ['Category', 'Total Amount', 'Count']
            
            # Display with proper column formatting (keeps numeric values for sorting)
            st.dataframe(
                category_summary, 
                column_config={
                    'Category': st.column_config.TextColumn('Category'),
                    'Total Amount': st.column_config.NumberColumn('Total Amount', format="$%.2f"),
                    'Count': st.column_config.NumberColumn('Count', format="%d")
                },
                use_container_width=True
            )
            
            # Rename section (only show if file is already saved)
            if st.session_state.current_file_id:
                st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    st.subheader("Rename Reconciliation")
                    
                    # Get current file name
                    current_file = st.session_state.db.get_file_by_id(st.session_state.current_file_id)
                    if current_file:
                        current_name = current_file[2]  # display_name
                        
                        rename_col1, rename_col2 = st.columns([2, 1])
                        
                        with rename_col1:
                            new_name = st.text_input(
                                "File name:", 
                                value=current_name,
                                help="Rename this reconciliation",
                                label_visibility="collapsed"
                            )
                        
                        with rename_col2:
                            if st.button("Rename", type="primary", use_container_width=True):
                                if new_name.strip() and new_name != current_name:
                                    st.session_state.db.update_file_name(st.session_state.current_file_id, new_name)
                                    st.success(f"✅ File renamed to '{new_name}'")
                                    st.rerun()
                                elif not new_name.strip():
                                    st.error("Please enter a name")

elif page == "P&L Summary":
    st.header("Profit & Loss Summary")
    
    # P&L Setup section
    with st.expander("P&L Report Settings", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Date range selector
            date_range = st.date_input(
                "Date Range",
                value=(datetime.now().replace(day=1), datetime.now()),
                format="MM/DD/YYYY"
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                st.warning("Please select both start and end dates")
                start_date = end_date = None
        
        with col2:
            # Starting cash input
            starting_cash = st.number_input(
                "Starting Cash",
                value=0.0,
                format="%.2f",
                help="Enter the cash balance at the beginning of the period"
            )
        
        with col3:
            # Generate button
            generate_report = st.button("Generate P&L", type="primary", use_container_width=True)
    
    if generate_report and start_date and end_date:
        try:
            # Load ALL transactions from ALL saved files
            saved_files = st.session_state.db.get_files()
            all_transactions = pd.DataFrame()
            files_with_transactions_in_range = set()
            
            if saved_files:
                file_options = {f[0]: f[2] for f in saved_files}  # id: display_name for info display
                for file_id, _, _, _ in saved_files:
                    file_transactions = st.session_state.db.get_transactions(file_id)
                    if not file_transactions.empty:
                        # Add file_id to each transaction for tracking
                        file_transactions['_file_id'] = file_id
                        all_transactions = pd.concat([all_transactions, file_transactions], ignore_index=True)
            
            if all_transactions.empty:
                st.info("No transactions found in the database.")
            else:
                # Filter by date range
                # Handle both 'date' and 'transaction_date' columns
                date_col = get_date_column(all_transactions)
                if date_col in all_transactions.columns:
                    # Convert to datetime
                    all_transactions[date_col] = pd.to_datetime(all_transactions[date_col], errors='coerce')
                    # Filter by date range
                    mask = (all_transactions[date_col] >= pd.Timestamp(start_date)) & \
                           (all_transactions[date_col] <= pd.Timestamp(end_date))
                    filtered_transactions = all_transactions[mask].copy()
                else:
                    filtered_transactions = all_transactions
                
                if filtered_transactions.empty:
                    st.warning("No transactions found in the selected date range.")
                else:
                    # Count unique files that have transactions in this date range
                    if '_file_id' in filtered_transactions.columns:
                        files_with_transactions_in_range = filtered_transactions['_file_id'].nunique()
                    else:
                        files_with_transactions_in_range = len(saved_files)
                    
                    # Normalize to 'date' column for consistency
                    if date_col == 'transaction_date' and 'date' not in filtered_transactions.columns:
                        filtered_transactions['date'] = filtered_transactions[date_col]
                    
                    # Get chart of accounts
                    coa = st.session_state.db.get_chart_of_accounts()
                    
                    # Generate P&L summary
                    pl_summary = generate_pl_summary(filtered_transactions, coa, starting_cash)
                    
                    # Show report info
                    st.info(f"""
                    P&L Report Generated:
                    - Date Range: {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}
                    - Total Transactions: {len(filtered_transactions)}
                    - Files Included: {files_with_transactions_in_range} saved file{'s' if files_with_transactions_in_range != 1 else ''}
                    """)
                
                    if not pl_summary.empty:
                        st.subheader("Monthly P&L Summary")
                    
                        # Add percentage column for gross profit and net income
                        pl_summary_with_pct = pl_summary.copy()
                        
                        # Find total income for percentage calculations
                        total_income_row = pl_summary_with_pct[pl_summary_with_pct['Category'] == 'Total Income']
                        if not total_income_row.empty and 'Total' in pl_summary_with_pct.columns:
                            total_income = total_income_row['Total'].iloc[0]
                        else:
                            total_income = 0
                        
                        # Add percentage column
                        percentages = []
                        for _, row in pl_summary_with_pct.iterrows():
                            if row['Category'] == 'Gross Profit' and total_income != 0:
                                pct = (row['Total'] / total_income) * 100
                                percentages.append(f"{pct:.1f}%")
                            elif row['Category'] == 'Net Income' and total_income != 0:
                                pct = (row['Total'] / total_income) * 100
                                percentages.append(f"{pct:.1f}%")
                            else:
                                percentages.append('')
                        
                        pl_summary_with_pct['%'] = percentages
                        
                        # Format the summary for display
                        formatted_summary = pl_summary_with_pct.copy()
                        for col in formatted_summary.columns:
                            if col not in ['Type', 'Category', '%']:
                                # Apply format_currency only to numeric values
                                formatted_summary[col] = formatted_summary[col].apply(
                                    lambda x: format_currency(x) if isinstance(x, (int, float)) else x
                                )
                        
                        # Styling for different row types
                        def style_pl_table(row):
                            styles = [''] * len(row)
                            
                            # Style summary rows
                            if row['Category'] in ['Total Income', 'Total COGS', 'Total Expenses', 'Total Other Income', 'Gross Profit', 'Net Income', 'Balance Sheet Items', 'Cash Flow', 'Starting Cash', 'Ending Cash']:
                                styles = ['font-weight: bold; background-color: #f0f2f5'] * len(row)
                                
                                # Extra emphasis for key metrics
                                if row['Category'] == 'Net Income':
                                    styles = ['font-weight: bold; background-color: #e8f4f8; color: #0066cc'] * len(row)
                                elif row['Category'] == 'Gross Profit':
                                    styles = ['font-weight: bold; background-color: #f0f8ff'] * len(row)
                                elif row['Category'] == 'Ending Cash':
                                    styles = ['font-weight: bold; background-color: #e8f8e8; color: #006600'] * len(row)
                            
                            return styles
                        
                        # Display with styling
                        styled_df = formatted_summary.style.apply(style_pl_table, axis=1)
                        
                        # Calculate optimal column widths based on content
                        def calculate_column_width(col_name, col_data):
                            # Get max length of values in column (including header)
                            max_len = len(str(col_name))
                            for val in col_data:
                                if pd.notna(val):
                                    max_len = max(max_len, len(str(val)))
                            
                            # Convert to approximate pixel width (roughly 7-8px per character)
                            # Add minimal padding
                            pixel_width = max(60, min(250, max_len * 7 + 10))
                            return pixel_width
                        
                        # Set column configuration for better display
                        column_config = {}
                        
                        # Configure each column with auto-calculated width
                        for col in formatted_summary.columns:
                            col_width = calculate_column_width(col, formatted_summary[col])
                            
                            if col == 'Type':
                                column_config[col] = st.column_config.TextColumn('Type', width=col_width)
                            elif col == 'Category':
                                # Category column usually needs more space
                                column_config[col] = st.column_config.TextColumn('Category', width=max(150, col_width))
                            elif col == '%':
                                # Percentage column can be narrower
                                column_config[col] = st.column_config.TextColumn('%', width=min(60, col_width))
                            elif col == 'Total':
                                column_config[col] = st.column_config.TextColumn('Total', width=col_width)
                            else:
                                # Month columns
                                column_config[col] = st.column_config.TextColumn(str(col), width=col_width)
                        
                        st.dataframe(
                            styled_df,
                            column_config=column_config,
                            use_container_width=True,
                            hide_index=True,
                            height=600  # Fixed height for better view
                        )
                
                        # Export option
                        st.markdown("---")
                        col_export_1, col_export_2, col_export_3 = st.columns([1, 2, 1])
                        with col_export_2:
                            # Format the data for CSV export with 2 decimal places
                            export_summary = pl_summary_with_pct.copy()
                            for col in export_summary.columns:
                                if col not in ['Type', 'Category', '%']:
                                    # Round numeric columns to 2 decimal places
                                    export_summary[col] = export_summary[col].apply(
                                        lambda x: round(x, 2) if isinstance(x, (int, float)) else x
                                    )
                            
                            csv_data = export_summary.to_csv(index=False, float_format='%.2f')
                            st.download_button(
                                label="📥 Download P&L Summary as CSV",
                                data=csv_data,
                                file_name=f"PL_Summary_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
        except Exception as e:
            st.error(f"Error generating P&L Summary: {str(e)}")
            st.error("Please check that all transactions have valid dates and categories.")
            import traceback
            st.text(traceback.format_exc())
    
    # Search All Transactions - Always visible
    st.markdown("---")
    st.subheader("Search All Transactions")
    
    # Search input
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_term = st.text_input("Search transactions by description, amount, category, or date", key="pl_search")
    
    # Get ALL transactions from ALL files for searching
    all_search_transactions = pd.DataFrame()
    saved_files = st.session_state.db.get_files()
    
    if saved_files:
        for file_id, _, display_name, _ in saved_files:
            file_transactions = st.session_state.db.get_transactions(file_id)
            if not file_transactions.empty:
                # Normalize date column
                if 'transaction_date' in file_transactions.columns and 'date' not in file_transactions.columns:
                    file_transactions['date'] = file_transactions['transaction_date']
                file_transactions['source_file'] = display_name
                file_transactions['file_id'] = file_id
                all_search_transactions = pd.concat([all_search_transactions, file_transactions], ignore_index=True)
        
        if not all_search_transactions.empty:
            # If search term is provided, filter; otherwise show all
            if search_term:
                # Create search mask
                search_term_lower = search_term.lower()
                search_mask = pd.Series([False] * len(all_search_transactions))
                
                # Search in description
                if 'description' in all_search_transactions.columns:
                    search_mask |= all_search_transactions['description'].astype(str).str.lower().str.contains(search_term_lower, na=False)
                
                # Search in category
                if 'category' in all_search_transactions.columns:
                    search_mask |= all_search_transactions['category'].astype(str).str.lower().str.contains(search_term_lower, na=False)
                
                # Search in amount
                if 'amount' in all_search_transactions.columns:
                    amount_str = all_search_transactions['amount'].astype(str)
                    search_mask |= amount_str.str.contains(search_term, na=False)
                    search_mask |= all_search_transactions['amount'].abs().astype(str).str.contains(
                        search_term.replace('$', '').replace(',', ''), na=False
                    )
                
                # Search in date
                date_col = get_date_column(all_search_transactions)
                if date_col and date_col in all_search_transactions.columns:
                    search_mask |= all_search_transactions[date_col].astype(str).str.lower().str.contains(search_term_lower, na=False)
                
                # Apply search mask
                search_results = all_search_transactions[search_mask].copy()
            else:
                # No search term, show all transactions
                search_results = all_search_transactions.copy()
            
            if not search_results.empty:
                if search_term:
                    st.info(f"Found {len(search_results)} transactions matching '{search_term}' across {search_results['source_file'].nunique()} file(s)")
                else:
                    st.info(f"Showing all {len(search_results)} transactions from {search_results['source_file'].nunique()} file(s)")
                
                # Add index for tracking
                search_results['row_idx'] = range(len(search_results))
                
                # Get categories for dropdown
                coa = st.session_state.db.get_chart_of_accounts()
                categories = ['Uncategorized'] + extract_categories_from_coa(coa)
                
                # Prepare display dataframe
                date_col = get_date_column(search_results)
                display_cols = [date_col, 'description', 'amount', 'category', 'source_file']
                
                # Sort by date
                if date_col:
                    search_results = search_results.sort_values(date_col, ascending=False)
                
                # Create editable dataframe
                edited_df = st.data_editor(
                    search_results[display_cols + ['row_idx', 'id', 'file_id']],
                    column_config={
                        date_col: st.column_config.TextColumn('Date', width="small"),
                        'description': st.column_config.TextColumn('Description', width="medium"),
                        'amount': st.column_config.NumberColumn('Amount', format="$%.2f"),
                        'category': st.column_config.SelectboxColumn(
                            'Category',
                            options=categories,
                            default='Uncategorized',
                            width="small"
                        ),
                        'source_file': st.column_config.TextColumn('File', width="small"),
                        'row_idx': None,
                        'id': None,
                        'file_id': None
                    },
                    use_container_width=True,
                    hide_index=True,
                    disabled=['date', 'description', 'amount', 'source_file'],
                    key="pl_search_editor"
                )
                
                # Check for category changes and save automatically
                for idx, row in edited_df.iterrows():
                    original_idx = row['row_idx']
                    new_category = row['category']
                    original_category = search_results.loc[search_results['row_idx'] == original_idx, 'category'].iloc[0]
                    
                    if new_category != original_category:
                        # Update the category in the database
                        file_id = row['file_id']
                        trans_id = row['id']
                        
                        # Load all transactions for this file
                        file_transactions = st.session_state.db.get_transactions(file_id)
                        # Update the specific transaction
                        file_transactions.loc[file_transactions['id'] == trans_id, 'category'] = new_category
                        # Save back to database
                        st.session_state.db.save_transactions(file_id, file_transactions)
                        st.toast(f"✅ Updated category to '{new_category}'")
                        st.rerun()
                
            else:
                if search_term:
                    st.warning(f"No transactions found matching '{search_term}'")
                else:
                    st.warning("No transactions found")
        else:
            st.info("No transactions found in the database.")

elif page == "File Management":
    st.header("File Management")
    
    # List all files
    files = st.session_state.db.get_files()
    
    if files:
        st.subheader("Uploaded Files")
        
        for file_id, original_name, display_name, upload_date in files:
            col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
            
            with col1:
                st.text(f"📄 {display_name}")
            
            with col2:
                st.text(f"Uploaded: {upload_date[:10]}")
            
            with col3:
                if st.button("Open", key=f"open_{file_id}"):
                    # Load file data and transactions
                    file_data = st.session_state.db.get_file_by_id(file_id)
                    transactions = st.session_state.db.get_transactions(file_id)
                    
                    if file_data and not transactions.empty:
                        # Load the original file data
                        st.session_state.original_df = pd.read_json(file_data[4])
                        st.session_state.original_filename = file_data[1]
                        
                        # Load the transactions and normalize date column
                        transactions_loaded = transactions.copy()
                        # Rename transaction_date to date for consistency
                        if 'transaction_date' in transactions_loaded.columns and 'date' not in transactions_loaded.columns:
                            transactions_loaded['date'] = transactions_loaded['transaction_date']
                        
                        st.session_state.transactions_df = transactions_loaded
                        st.session_state.current_file_id = file_id
                        
                        # Reset unsaved changes tracking
                        st.session_state.unsaved_changes_count = 0
                        if 'original_categories' in st.session_state:
                            del st.session_state.original_categories
                        
                        # Navigate to Categorize Transactions tab
                        st.session_state.selected_page = "Categorize Transactions"
                        st.success(f"Loaded file: {display_name}")
                        st.rerun()
            
            with col4:
                new_name = st.text_input("Rename", value=display_name, key=f"rename_{file_id}")
                if new_name != display_name:
                    if st.button("Save", key=f"save_{file_id}"):
                        st.session_state.db.update_file_name(file_id, new_name)
                        st.success("File renamed!")
                        st.rerun()
            
            with col5:
                # Use session state to track delete confirmation for each file
                confirm_key = f"delete_confirm_{file_id}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False
                
                if not st.session_state[confirm_key]:
                    if st.button("×", key=f"delete_{file_id}", help="Delete this file"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    # Show confirmation
                    if st.button("❌ Confirm", key=f"confirm_delete_{file_id}", type="primary"):
                        # Check if this is the currently loaded file
                        if st.session_state.current_file_id == file_id:
                            st.session_state.current_file_id = None
                            st.session_state.transactions_df = pd.DataFrame()
                            st.session_state.original_df = None
                            st.session_state.original_filename = None
                            st.session_state.unsaved_changes_count = 0
                            if 'original_categories' in st.session_state:
                                del st.session_state.original_categories
                        
                        # Delete the file
                        # Reinitialize database if method is missing (for hot reload)
                        if not hasattr(st.session_state.db, 'delete_file'):
                            from database import Database
                            st.session_state.db = Database()
                        
                        st.session_state.db.delete_file(file_id)
                        st.session_state[confirm_key] = False
                        st.success(f"Deleted file: {display_name}")
                        st.rerun()
                    
                    if st.button("Cancel", key=f"cancel_delete_{file_id}"):
                        st.session_state[confirm_key] = False
                        st.rerun()
        
        # Current file indicator
        if st.session_state.current_file_id:
            current_file = st.session_state.db.get_file_by_id(st.session_state.current_file_id)
            if current_file:
                file_name = current_file[2]  # display_name
                st.info(f"Currently working with file: {file_name}")
    else:
        st.info("No files uploaded yet. Go to 'Upload & Map Files' to get started.")

elif page == "Settings":
    st.header("Settings")
    
    tabs = st.tabs(["Database Management", "About"])
    
    with tabs[0]:
        st.subheader("Database Management")
        
        col_db_1, col_db_2 = st.columns(2)
        
        with col_db_1:
            if st.button("Export Database", type="secondary"):
                st.info("Export functionality coming soon!")
        
        with col_db_2:
            # Use session state to track if clear data was clicked
            if 'show_clear_confirm' not in st.session_state:
                st.session_state.show_clear_confirm = False
            
            if st.button("Clear All Data", type="secondary"):
                st.session_state.show_clear_confirm = True
            
            if st.session_state.show_clear_confirm:
                st.error("⚠️ This will permanently delete all data!")
                confirm_delete = st.checkbox("I understand this will delete all data", key="confirm_clear")
                
                if confirm_delete:
                    if st.button("Confirm Delete", type="primary"):
                        # Delete the actual database file
                        import os
                        if os.path.exists("bookkeeper.db"):
                            os.remove("bookkeeper.db")
                        
                        # Reset everything
                        st.session_state.db = Database()
                        st.session_state.categorizer = TransactionCategorizer(st.session_state.db)
                        st.session_state.current_file_id = None
                        st.session_state.transactions_df = pd.DataFrame()
                        st.session_state.show_clear_confirm = False
                        st.success("All data cleared!")
                        st.rerun()
                
                if st.button("Cancel"):
                    st.session_state.show_clear_confirm = False
                    st.rerun()
    
    with tabs[1]:
        st.subheader("About Bookkeeper")
        st.markdown("""
        **Bookkeeper** is a financial reconciliation tool that helps you:
        
        - 📊 Import transaction data from CSV files
        - 🏷️ Automatically categorize transactions using AI
        - 📝 Manage your Chart of Accounts
        - 💰 Generate P&L summaries
        - 💾 Save all data locally for privacy
        
        ### Features:
        - **AI-Powered Categorization**: Uses OpenAI GPT-3.5 to intelligently categorize transactions based on your historical data
        - **Real-Time Merchant Analysis**: Leverages Perplexity API to search the web and identify merchants for accurate categorization
        - **Local Storage**: All data stored locally using SQLite for complete privacy
        - **Export Options**: Export summaries and reports as CSV for further analysis
        
        ### How to Use:
        1. Start by uploading a CSV file with your transactions
        2. Map the columns to Date, Description, and Amount
        3. Set up your Chart of Accounts
        4. Let the AI categorize transactions automatically
        5. Review and adjust as needed
        6. Generate your P&L summary
        
        Version 1.0.0
        """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Bookkeeper v1.0.0")
st.sidebar.markdown("Built with Streamlit & SQLite")