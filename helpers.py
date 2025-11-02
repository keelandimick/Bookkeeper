"""Helper functions to reduce code duplication in the Bookkeeper app"""
import streamlit as st
import pandas as pd

def is_uncategorized(category):
    """Check if a category is considered uncategorized"""
    return pd.isna(category) or category == '' or category == 'Uncategorized'

def get_uncategorized_mask(df):
    """Get a boolean mask for uncategorized transactions"""
    return df['category'].apply(is_uncategorized)

def get_date_column(df):
    """Get the appropriate date column name from dataframe"""
    if 'date' in df.columns:
        return 'date'
    elif 'transaction_date' in df.columns:
        return 'transaction_date'
    return None

def create_column_mapping_ui(df, column_type, detected_types, label):
    """Create a selectbox for column mapping with auto-detection"""
    suggestions = []
    
    if column_type == 'date':
        suggestions = [col for col, typ in detected_types.items() if typ == 'date']
    elif column_type == 'description':
        suggestions = [col for col, typ in detected_types.items() if typ == 'description']
    elif column_type == 'amount':
        suggestions = [col for col, typ in detected_types.items() if typ == 'amount']
    elif column_type == 'category':
        suggestions = [col for col in df.columns if 'category' in col.lower() or 'cat' in col.lower()]
    
    options = ['None'] + list(df.columns)
    default_index = 0
    
    if suggestions:
        # Find the index of the first suggestion in the options list
        if suggestions[0] in options:
            default_index = options.index(suggestions[0])
    
    return st.selectbox(
        label,
        options=options,
        index=default_index,
        key=f"{column_type}_mapping"
    )

def extract_categories_from_coa(coa):
    """Extract category names from chart of accounts tuples"""
    return [cat[0] for cat in coa]

def create_category_type_map(coa):
    """Create a mapping of category names to types"""
    return {account[0]: account[1] for account in coa}

def auto_save_transactions(db, file_id, original_filename, original_df, transactions_df):
    """Auto-save transactions to database"""
    if file_id:
        # Update existing file
        db.save_transactions(file_id, transactions_df)
    else:
        # Create new saved file with original name
        file_data = original_df.to_json()
        new_file_id = db.save_file(
            original_filename, 
            original_filename,  # Keep original name as display name
            file_data
        )
        db.save_transactions(new_file_id, transactions_df)
        return new_file_id
    return file_id