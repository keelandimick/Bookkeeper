import pandas as pd
from datetime import datetime
import json
import base64
from helpers import get_date_column

def parse_csv_data(file_content, encoding='utf-8'):
    try:
        # First, read with headers to check if first row looks like data
        df_with_headers = pd.read_csv(file_content, encoding=encoding)
        file_content.seek(0)  # Reset file pointer
        
        # Check if the column names look like actual data (dates, amounts, etc)
        first_row_might_be_data = False
        for col in df_with_headers.columns:
            col_str = str(col).strip()
            # Check if column name looks like a date
            if any(char in col_str for char in ['/', '-']) and any(char.isdigit() for char in col_str):
                first_row_might_be_data = True
                break
            # Check if column name looks like an amount
            if col_str.replace('$', '').replace(',', '').replace('.', '').replace('-', '').isdigit():
                first_row_might_be_data = True
                break
        
        # If first row looks like data, read without headers
        if first_row_might_be_data:
            file_content.seek(0)
            df = pd.read_csv(file_content, encoding=encoding, header=None)
            # Use first row values as column names for better UX in dropdowns
            # But ensure unique column names by adding index if duplicates
            first_row_values = df.iloc[0].astype(str).tolist()
            unique_columns = []
            seen = {}
            for i, val in enumerate(first_row_values):
                if val in seen:
                    seen[val] += 1
                    unique_columns.append(f"{val}_{seen[val]}")
                else:
                    seen[val] = 0
                    unique_columns.append(val)
            df.columns = unique_columns
        else:
            df = df_with_headers
            
        return df, None
    except UnicodeDecodeError:
        try:
            file_content.seek(0)
            df = pd.read_csv(file_content, encoding='latin-1')
            return df, None
        except Exception as e:
            return None, f"Error reading CSV: {str(e)}"
    except Exception as e:
        return None, f"Error parsing CSV: {str(e)}"

def detect_column_types(df):
    column_types = {}
    avg_lengths = {}
    
    # First pass: identify dates and amounts
    for col in df.columns:
        sample_values = df[col].dropna().head(10)
        
        # Check for date
        if is_date_column(sample_values):
            column_types[col] = 'date'
        # Check for amount/number
        elif is_amount_column(sample_values):
            column_types[col] = 'amount'
        else:
            # Calculate average character length for potential description columns
            avg_length = df[col].dropna().astype(str).apply(len).mean()
            avg_lengths[col] = avg_length
            column_types[col] = 'other'
    
    # Second pass: find the column with the longest average text (likely description)
    if avg_lengths:
        # Find column with maximum average length that isn't already classified
        desc_col = max(avg_lengths.items(), key=lambda x: x[1])[0]
        column_types[desc_col] = 'description'
    
    return column_types

def is_date_column(values):
    if len(values) == 0:
        return False
    
    date_formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', 
        '%Y/%m/%d', '%m-%d-%Y', '%d-%m-%Y'
    ]
    
    success_count = 0
    for val in values[:5]:
        for fmt in date_formats:
            try:
                datetime.strptime(str(val), fmt)
                success_count += 1
                break
            except:
                continue
    
    return success_count >= 3

def is_amount_column(values):
    if len(values) == 0:
        return False
    
    numeric_count = 0
    
    for val in values[:10]:  # Check first 10 values
        val_str = str(val).strip()
        
        # Skip empty values
        if not val_str or val_str.lower() in ['nan', 'none']:
            continue
        
        # REJECT if it has date separators (except negative sign at start)
        if '/' in val_str:
            return False  # Definitely not an amount if it has /
        
        if '-' in val_str and not val_str.startswith('-'):
            return False  # Has dash in middle = likely a date
            
        try:
            # Remove currency symbols and commas
            cleaned = val_str.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').replace(' ', '')
            
            # Must be a valid number
            float(cleaned)
            numeric_count += 1
        except:
            continue
    
    # Need at least 80% to be valid numbers
    return numeric_count >= len(values[:10]) * 0.8

def clean_amount(value):
    if pd.isna(value):
        return 0.0
    
    try:
        # Handle string amounts
        if isinstance(value, str):
            # Remove currency symbols and spaces
            cleaned = value.replace('$', '').replace(',', '').replace(' ', '')
            
            # Handle parentheses as negative
            if '(' in cleaned and ')' in cleaned:
                cleaned = '-' + cleaned.replace('(', '').replace(')', '')
            
            return float(cleaned)
        else:
            return float(value)
    except:
        return 0.0

def generate_pl_summary(transactions_df, chart_of_accounts, starting_cash=0):
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Work with a copy to avoid modifying the original
    df = transactions_df.copy()
    
    # Check for date column - could be 'date' or 'transaction_date'
    date_col = get_date_column(df)
    
    if date_col:
        # Convert to datetime, coerce errors to NaT
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        # Filter out rows with invalid dates
        df = df[df[date_col].notna()]
        if df.empty:
            return pd.DataFrame()
        df['month'] = df[date_col].dt.to_period('M')
    else:
        # No date column - can't create monthly summary
        return pd.DataFrame()
    
    # Create a mapping of category to type
    from helpers import create_category_type_map
    category_type_map = create_category_type_map(chart_of_accounts)
    
    # Group by category and month
    summary = df.groupby(['category', 'month'])['amount'].sum().reset_index()
    
    # Pivot to get categories as rows and months as columns
    pl_summary = summary.pivot(index='category', columns='month', values='amount').fillna(0)
    
    # Convert Period columns to string format for display
    pl_summary.columns = [str(col) if col != 'Total' else col for col in pl_summary.columns]
    
    # Add totals
    pl_summary['Total'] = pl_summary.sum(axis=1)
    
    # Sort by category type
    income_categories = []
    cogs_categories = []
    expense_categories = []
    other_income_categories = []
    balance_sheet_categories = []
    
    for category in pl_summary.index:
        cat_type = category_type_map.get(category, 'Expense')
        if cat_type == 'Income':
            income_categories.append(category)
        elif cat_type == 'COGS':
            cogs_categories.append(category)
        elif cat_type == 'Other Income':
            other_income_categories.append(category)
        elif cat_type == 'Balance Sheet':
            balance_sheet_categories.append(category)
        else:  # Expense or unknown
            expense_categories.append(category)
    
    # Create empty list to build the final P&L in order
    final_rows = []
    
    # Reset index to make category a regular column
    pl_summary = pl_summary.reset_index()
    # The index name could be 'category' or 'index' depending on how it was created
    if 'category' in pl_summary.columns:
        pl_summary = pl_summary.rename(columns={'category': 'Category'})
    elif 'index' in pl_summary.columns:
        pl_summary = pl_summary.rename(columns={'index': 'Category'})
    
    # Add category type as the first column
    pl_summary.insert(0, 'Type', '')
    
    # Get numeric columns for calculations
    numeric_cols = [col for col in pl_summary.columns if col not in ['Type', 'Category']]
    
    # Process Income categories
    if income_categories:
        for category in income_categories:
            row = pl_summary[pl_summary['Category'] == category].copy()
            if not row.empty:
                row['Type'] = 'Income'
                final_rows.append(row)
        
        # Add Total Income row
        income_total = pl_summary[pl_summary['Category'].isin(income_categories)][numeric_cols].sum()
        total_row = pd.DataFrame([['', 'Total Income'] + income_total.tolist()], columns=pl_summary.columns)
        final_rows.append(total_row)
    
    # Process COGS categories
    if cogs_categories:
        for category in cogs_categories:
            row = pl_summary[pl_summary['Category'] == category].copy()
            if not row.empty:
                row['Type'] = 'COGS'
                final_rows.append(row)
        
        # Add Total COGS row
        cogs_total = pl_summary[pl_summary['Category'].isin(cogs_categories)][numeric_cols].sum()
        total_row = pd.DataFrame([['', 'Total COGS'] + cogs_total.tolist()], columns=pl_summary.columns)
        final_rows.append(total_row)
        
        # Add Gross Profit row
        if income_categories:
            income_total = pl_summary[pl_summary['Category'].isin(income_categories)][numeric_cols].sum()
            # COGS is already negative, so we add it to income
            gross_profit = income_total + cogs_total
            gp_row = pd.DataFrame([['', 'Gross Profit'] + gross_profit.tolist()], columns=pl_summary.columns)
            final_rows.append(gp_row)
    
    # Process Expense categories
    if expense_categories:
        for category in expense_categories:
            row = pl_summary[pl_summary['Category'] == category].copy()
            if not row.empty:
                row['Type'] = 'Expense'
                final_rows.append(row)
        
        # Add Total Expenses row
        expense_total = pl_summary[pl_summary['Category'].isin(expense_categories)][numeric_cols].sum()
        total_row = pd.DataFrame([['', 'Total Expenses'] + expense_total.tolist()], columns=pl_summary.columns)
        final_rows.append(total_row)
    
    # Process Other Income categories
    if other_income_categories:
        for category in other_income_categories:
            row = pl_summary[pl_summary['Category'] == category].copy()
            if not row.empty:
                row['Type'] = 'Other Income'
                final_rows.append(row)
        
        # Add Total Other Income row
        other_income_total = pl_summary[pl_summary['Category'].isin(other_income_categories)][numeric_cols].sum()
        total_row = pd.DataFrame([['', 'Total Other Income'] + other_income_total.tolist()], columns=pl_summary.columns)
        final_rows.append(total_row)
    
    # Add Net Income row
    income_total = pl_summary[pl_summary['Category'].isin(income_categories)][numeric_cols].sum() if income_categories else pd.Series(0, index=numeric_cols)
    cogs_total = pl_summary[pl_summary['Category'].isin(cogs_categories)][numeric_cols].sum() if cogs_categories else pd.Series(0, index=numeric_cols)
    expense_total = pl_summary[pl_summary['Category'].isin(expense_categories)][numeric_cols].sum() if expense_categories else pd.Series(0, index=numeric_cols)
    other_income_total = pl_summary[pl_summary['Category'].isin(other_income_categories)][numeric_cols].sum() if other_income_categories else pd.Series(0, index=numeric_cols)
    # COGS and Expenses are already negative, Other Income is positive, so we add them all together
    net_income = income_total + cogs_total + expense_total + other_income_total
    ni_row = pd.DataFrame([['', 'Net Income'] + net_income.tolist()], columns=pl_summary.columns)
    final_rows.append(ni_row)
    
    # Process Balance Sheet categories
    if balance_sheet_categories:
        for category in balance_sheet_categories:
            row = pl_summary[pl_summary['Category'] == category].copy()
            if not row.empty:
                row['Type'] = 'Balance Sheet'
                final_rows.append(row)
        
        # Add Balance Sheet Total row
        balance_total = pl_summary[pl_summary['Category'].isin(balance_sheet_categories)][numeric_cols].sum()
        total_row = pd.DataFrame([['', 'Balance Sheet Items'] + balance_total.tolist()], columns=pl_summary.columns)
        final_rows.append(total_row)
    
    # Add Cash Flow section
    # First calculate net income and balance sheet values for each period
    net_income_values = []
    balance_sheet_values = []
    cash_flow_values = []
    
    for col in numeric_cols:
        if col != 'Total':
            # Find the net income value for this period
            net_income_val = 0
            balance_sheet_val = 0
            for row_data in final_rows:
                if not row_data.empty and len(row_data) > 0:
                    if row_data.iloc[0]['Category'] == 'Net Income':
                        net_income_val = row_data[col].iloc[0] if col in row_data.columns else 0
                    elif row_data.iloc[0]['Category'] == 'Balance Sheet Items':
                        balance_sheet_val = row_data[col].iloc[0] if col in row_data.columns else 0
            net_income_values.append(net_income_val)
            balance_sheet_values.append(balance_sheet_val)
            # Cash flow is net income plus balance sheet items
            cash_flow_values.append(net_income_val + balance_sheet_val)
    
    # Add total column for cash flow
    total_cash_flow = sum(cash_flow_values)
    cash_flow_values.append(total_cash_flow)
    
    # Add Cash Flow row (Net Income + Balance Sheet Items)
    cash_flow_row = pd.DataFrame([['', 'Cash Flow'] + cash_flow_values], columns=pl_summary.columns)
    final_rows.append(cash_flow_row)
    
    # Calculate starting and ending cash for each period
    starting_cash_values = []
    ending_cash_values = []
    running_cash = starting_cash
    
    for i in range(len(net_income_values)):
        # Starting cash for this period
        starting_cash_values.append(running_cash)
        # Ending cash = starting cash + cash flow
        running_cash += net_income_values[i] + balance_sheet_values[i]
        ending_cash_values.append(running_cash)
    
    # For the Total column, show the initial starting cash and final ending cash
    starting_cash_values.append(starting_cash)  # Original starting cash for Total
    ending_cash_values.append(running_cash)  # Final ending cash for Total
    
    # Starting Cash row
    starting_cash_row = pd.DataFrame([['', 'Starting Cash'] + starting_cash_values], columns=pl_summary.columns)
    final_rows.append(starting_cash_row)
    
    # Ending Cash row
    ending_cash_row = pd.DataFrame([['', 'Ending Cash'] + ending_cash_values], columns=pl_summary.columns)
    final_rows.append(ending_cash_row)
    
    # Combine all rows
    pl_summary = pd.concat(final_rows, ignore_index=True)
    
    return pl_summary

def export_to_csv(dataframe, filename):
    csv = dataframe.to_csv(index=True)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download {filename}</a>'
    return href

def format_currency(amount):
    if amount >= 0:
        return f"${amount:,.2f}"
    else:
        return f"(${abs(amount):,.2f})"