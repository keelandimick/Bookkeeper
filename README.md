# Bookkeeper - Financial Reconciliation Tool

A standalone web application for reconciling personal or business finances by automatically categorizing transactions based on historical patterns.

## Features

- **CSV File Upload**: Import transaction data from Excel or Apple Numbers exports
- **Smart Column Mapping**: Auto-detect and save column mappings for different account formats
- **AI-Powered Categorization**: Automatically categorize transactions using OpenAI GPT-3.5
- **Transaction Research**: Analyze individual transactions with web search via Perplexity API
- **Chart of Accounts Management**: Maintain and update your categories dynamically
- **Transaction Review**: Edit and refine categorizations with an intuitive interface
- **P&L Summary**: Generate monthly Profit & Loss statements with:
  - Gross profit and net income percentages
  - Cash flow analysis
  - Starting/ending cash tracking
  - Auto-sized columns for better readability
- **Search All Transactions**: Search across all files in your database
- **Local Storage**: All data stored securely on your local machine using SQLite
- **File Management**: Rename files, re-open previous reconciliations with auto-navigation

## Installation

1. Clone this repository or download the source code
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the Bookkeeper app:
```bash
streamlit run bookkeeper.py
```

The application will open in your default web browser at `http://localhost:8501`

## How to Use

### 1. Upload & Map Files
- Upload your CSV file exported from Excel/Numbers
- Map columns to Date, Description, and Amount
- Save the mapping for future use with similar files

### 2. Manage Chart of Accounts
- Add categories manually or bulk import from CSV
- Categories are automatically updated when you add new ones during reconciliation
- Initialize with default categories if starting fresh

### 3. Categorize Transactions
- Click "Auto-Categorize" to let AI categorize your transactions
- Review and adjust categories as needed
- The system learns from your adjustments for better future predictions

### 4. Review & Edit
- View category breakdowns and statistics
- Make quick edits to individual transactions
- See total income and expenses at a glance

### 5. Generate P&L Summary
- View monthly Profit & Loss statements
- Export summaries as CSV files
- Analyze trends with visual charts

### 6. File Management
- Rename uploaded files for better organization
- Re-open previous files to continue working
- Track when files were uploaded

## File Format Requirements

Your CSV files should contain at minimum:
- A date column (various formats supported)
- A description column (transaction descriptions/memos)
- An amount column (positive for income, negative for expenses)

## Data Storage

All data is stored locally in `bookkeeper.db` (SQLite database) including:
- Uploaded files and metadata
- Column mappings
- Chart of accounts
- Transaction categorizations
- Categorization rules learned from your patterns

## Tips for Best Results

1. **Consistent Descriptions**: The more consistent your transaction descriptions, the better the auto-categorization
2. **Review Regularly**: Review and correct categorizations to improve AI accuracy
3. **Save Column Mappings**: Save mappings for each account type to streamline future uploads
4. **Build Rules**: The system learns from your categorizations and builds rules automatically

## Privacy

All data is stored locally on your machine. No data is sent to external servers.

## Deployment

### Deploy to Streamlit Community Cloud

1. Fork this repository to your GitHub account
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Click "New app" and connect your GitHub account
4. Select your forked repository
5. Set the main file path to `bookkeeper.py`
6. Add your API keys in the Secrets section:
   ```toml
   OPENAI_API_KEY = "your-openai-key"
   PERPLEXITY_API_KEY = "your-perplexity-key"
   ```
7. Click "Deploy"

### Local Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/keelandimick/bookkeeper.git
   cd bookkeeper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your-openai-key
   PERPLEXITY_API_KEY=your-perplexity-key
   ```

4. Run the app:
   ```bash
   streamlit run bookkeeper.py
   ```

## For Developers

See `DEVELOPMENT_GUIDE.md` for:
- Code quality standards
- Architecture details
- Contributing guidelines
- Working with Claude AI

## Technical Details

Built with:
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **SQLite**: Local database storage
- **Scikit-learn**: Machine learning for categorization
- **Python 3.8+**: Core programming language