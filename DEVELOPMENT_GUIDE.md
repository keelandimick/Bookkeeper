# Bookkeeper Development Guide

## Table of Contents
1. [Project Architecture](#project-architecture)
2. [Working with Claude AI](#working-with-claude-ai)
3. [Code Quality Standards](#code-quality-standards)
4. [Database Schema](#database-schema)
5. [Development Workflow](#development-workflow)

## Project Architecture

**Bookkeeper** is a financial reconciliation tool built with:
- **Frontend**: Streamlit web interface
- **Backend**: Python with SQLite database  
- **AI**: 
  - OpenAI GPT-3.5 for intelligent transaction categorization
  - Perplexity API for real-time web search and merchant identification

### Key Components
- `bookkeeper.py` - Main Streamlit UI application
- `database.py` - Database operations and schema management
- `categorizer.py` - AI-powered transaction categorization
- `utils.py` - Data processing and P&L generation utilities
- `helpers.py` - Shared UI helpers and common patterns

## Working with Claude AI

### Starting a New Session

**IMPORTANT**: At the start of each session with Claude, use this prompt:

```
Please read DEVELOPMENT_GUIDE.md first, then I'll tell you what I'd like changed.
```

After Claude confirms reading this file, provide your specific request.

### Key Instructions for Claude

1. **Always check `helpers.py`** before adding new functions
2. **Follow existing patterns** documented in this guide
3. **Never duplicate code** - use existing helpers
4. **Remove dead code** when making changes
5. **Run `check_code_quality.py`** after modifications

### Files Claude Must Always Review

Before making any changes, Claude should check these files:

1. **`helpers.py`** - Contains these reusable functions to prevent duplication:
   - `is_uncategorized(category)` - Check if a category is uncategorized
   - `get_uncategorized_mask(df)` - Get boolean mask for uncategorized transactions
   - `get_date_column(df)` - Detect whether to use 'date' or 'transaction_date' column
   - `create_column_mapping_ui()` - Create consistent column mapping UI
   - `extract_categories_from_coa(coa)` - Extract category names from chart of accounts
   - `create_category_type_map(coa)` - Create category to type mapping

2. **`check_code_quality.py`** - Run this after changes to check for:
   - Unused imports
   - Duplicate patterns
   - Empty functions
   - References to removed database tables/methods

### Example Session Starters

#### For New Features
```
Working on Bookkeeper app. Read DEVELOPMENT_GUIDE.md first.
Adding [feature]. Check helpers.py for existing functionality.
Ensure no code duplication.
```

#### For Bug Fixes  
```
Bookkeeper bug fix. Read DEVELOPMENT_GUIDE.md.
Fix [issue] using existing helpers where possible.
Remove any dead code encountered.
```

#### For Refactoring
```
Bookkeeper refactoring. Read DEVELOPMENT_GUIDE.md.
Consolidate [duplicate code] into helpers.py.
Ensure patterns are consistent.
```

## Code Quality Standards

This guide documents best practices for maintaining clean, efficient code in the Bookkeeper application.

### 1. Avoiding Code Duplication

#### Use Helper Functions
- **Location**: `helpers.py` contains reusable utility functions
- **Common Patterns to Centralize**:
  - Uncategorized transaction checks → use `is_uncategorized()` or `get_uncategorized_mask()`
  - Date column detection → use `get_date_column()`
  - Category extraction → use `extract_categories_from_coa()`
  - Category type mapping → use `create_category_type_map()`

#### Database Operations
- Avoid repeating the connection pattern:
  ```python
  with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(...)
      conn.commit()
  ```
- Consider creating wrapper methods for common operations

### 2. Dead Code Prevention

#### Before Adding New Code
- Check if similar functionality already exists
- Search for existing implementations using grep/search tools
- Review `helpers.py` for reusable functions

#### Regular Cleanup Checklist
- [ ] Remove unused imports
- [ ] Delete unused functions/methods
- [ ] Remove empty "compatibility" methods
- [ ] Clean up unused database tables/columns
- [ ] Remove commented-out code blocks

### 3. Code Review Checklist

When making changes, check for:

#### Imports
- [ ] All imports are used
- [ ] No duplicate import statements
- [ ] Imports are organized (standard library, third-party, local)

#### Functions/Methods
- [ ] No duplicate functionality
- [ ] All defined functions are called somewhere
- [ ] No empty placeholder methods

#### Database Schema
- [ ] All tables are actively used
- [ ] All columns have a purpose
- [ ] No duplicate data storage

#### UI Patterns
- [ ] Column mapping UI uses `create_column_mapping_ui()`
- [ ] Category filtering uses helper functions
- [ ] Date column handling uses `get_date_column()`

### 4. Common Anti-Patterns to Avoid

#### ❌ Don't Repeat Yourself (DRY)
```python
# Bad: Repeated logic
if df['category'] == '' or df['category'] == 'Uncategorized' or df['category'].isna():
    # ...

# Good: Use helper
if is_uncategorized(df['category']):
    # ...
```

#### ❌ Multiple Ways to Check Same Thing
```python
# Bad: Different checks in different places
date_col = 'date' if 'date' in df.columns else 'transaction_date'  # Location A
if 'transaction_date' in df.columns:  # Location B
    date_col = 'transaction_date'

# Good: Consistent helper
date_col = get_date_column(df)
```

#### ❌ Unused Compatibility Code
```python
# Bad: Empty methods "for compatibility"
def old_method(self):
    pass  # Kept for compatibility

# Good: Remove completely or document deprecation timeline
```

### 5. Maintenance Schedule

#### Weekly
- Run unused import checker
- Review any new functions for duplication

#### Monthly
- Full code audit for dead code
- Review database schema usage
- Check for parallel implementations

#### Before Major Features
- Clean up related code areas first
- Document any new patterns in `helpers.py`

### 6. Tools for Code Quality

#### Static Analysis
```bash
# Check for unused imports
python -m pyflakes *.py

# Find duplicate code patterns
# Consider using tools like:
# - pylint --disable=all --enable=duplicate-code
# - vulture (finds dead code)
```

#### Manual Checks
```bash
# Find potentially unused functions
rg "def \w+" -A 1 | grep -v "test"

# Find similar patterns
rg "get_chart_of_accounts\(\)" | wc -l
```

### 7. Adding New Features

Before adding new functionality:
1. Check if it already exists in some form
2. Look for similar patterns in the codebase
3. Consider if it belongs in `helpers.py`
4. Update this guide if introducing new patterns

### 8. Database Changes

When modifying the database:
1. Remove unused tables/columns in the same PR
2. Update all related access code
3. Don't leave "placeholder" columns for future use

---

## Automated Quality Checks

To enable automatic pre-commit checks:
```bash
git config core.hooksPath .githooks
```

Manual quality check:
```bash
python3 check_code_quality.py
```

## Quick Reference

### Files and Their Purpose
- `bookkeeper.py` - Main Streamlit UI
- `database.py` - Database operations only
- `categorizer.py` - AI categorization logic
- `utils.py` - Data processing utilities
- `helpers.py` - UI and common pattern helpers

### When to Add to helpers.py
Add a function to helpers when:
- It's used in 2+ places
- It standardizes a check/operation
- It reduces code duplication
- It makes code more readable

### Red Flags 🚩
- Copy-pasting code blocks
- "Temporary" workarounds
- Empty methods/functions
- Imports without usage
- Complex conditions repeated in multiple places

## Database Schema

### Active Tables
- `files` - Stores uploaded file metadata and original data
- `transactions` - Individual transaction records with categories
- `chart_of_accounts` - Category definitions with types (Income/Expense/COGS/Balance Sheet)
- `categorization_rules` - Learned patterns for auto-categorization

### Removed Tables (Do Not Use)
- `column_mappings` - Deprecated, was for saving CSV mappings
- `reconciliations` - Deprecated, not used in current workflow

## Development Workflow

### Setup
1. Clone the repository: `git clone https://github.com/keelandimick/bookkeeper.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set OpenAI API key in `.env` file
4. Set Perplexity API key in `.env` file
5. Enable git hooks: `git config core.hooksPath .githooks`

#### API Keys Configuration
Create a `.env` file in the project root with:
```
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
```

### Before Committing
1. Run `python3 check_code_quality.py`
2. Fix any duplicate patterns found
3. Remove unused imports
4. Ensure all new functions are documented

### Testing
- Manual testing through Streamlit UI
- Verify categorization with test CSV files
- Check P&L calculations match expected results

### Common Tasks

#### Adding a New UI Component
1. Check if similar component exists in helpers.py
2. Use existing patterns (e.g., `create_column_mapping_ui`)
3. Add to helpers.py if reusable

#### Modifying Database Schema
1. Update schema in `database.py`
2. Remove any deprecated tables/columns
3. Update all access code
4. Test migration with existing databases

#### Improving Categorization
1. Modifications go in `categorizer.py`
2. Use existing helper functions
3. Test with various transaction types
4. Ensure respects user's chart of accounts

## AI Transaction Analysis Feature

### Overview
The AI Analysis feature uses Perplexity API to provide real-time web search capabilities for identifying merchants and suggesting appropriate categories for transactions.

### How It Works
1. **Research Transaction Button**: In the Categorize Transactions tab, users can click "Research Transaction" to analyze individual transactions
2. **Web Search**: The system uses Perplexity's "sonar" model to search the web for merchant information
3. **Smart Analysis**: AI provides:
   - What the merchant is and their business type
   - Suggested category from the user's Chart of Accounts
   - Reasoning based on transaction description and amount

### Implementation Details
- **Location**: `bookkeeper.py` lines 579-620
- **API Model**: Perplexity "sonar" for web-enabled search
- **Description Cleaning**: Removes common payment processor words and card numbers
- **Category Matching**: Enforces selection from existing Chart of Accounts only

### Best Practices
1. Keep prompts concise (under 100 words response)
2. Clean transaction descriptions before searching
3. Always match to existing categories exactly
4. Handle special cases (e.g., ticketing platforms vs software subscriptions)

## Future Features & TODO List

1. **Implement Export Database Functionality**
   - Export complete database backup as ZIP file
   - Include all files, transactions, chart of accounts, and categorization rules
   - Add restore/import functionality

2. **Create Dashboard**
   - Design a comprehensive financial dashboard
   - Include visual charts and graphs
   - Show key metrics and trends
   - Add customizable widgets

3. **Implement Multi-Account Support**
   
   **Phase 1: Add Multi-Account Support (No Auth)**
   - Add account_id column to existing tables (files, chart_of_accounts, categorization_rules)
   - Create accounts table with id, account_name, account_type, created_at
   - Create default account for existing data
   - Update all database queries to filter by account_id
   - Add account switcher dropdown in UI sidebar
   - Estimated time: 2-3 hours
   
   **Phase 2: Add User Authentication**
   - Create users table (id, email, password_hash, created_at)
   - Link accounts to users (add user_id to accounts table)
   - Implement authentication using streamlit-authenticator or OAuth
   - Add login/logout functionality
   - Handle session management
   - Estimated time: 1-2 hours
   
   **Phase 3: Deployment Setup**
   - Set up GitHub repository
   - Configure for Streamlit Community Cloud deployment
   - Add environment variables for API keys
   - Set up secrets management
   - Test multi-user functionality
   - Estimated time: 1-2 hours

### Future Enhancements
- API integration with banks/financial institutions
- Scheduled reports and email notifications
- Mobile-responsive design improvements
- Bulk transaction editing
- Custom report templates
- Data visualization enhancements