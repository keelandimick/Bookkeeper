import pandas as pd
import openai
import json
import os
from dotenv import load_dotenv
from database import Database
from helpers import get_uncategorized_mask, create_category_type_map, extract_categories_from_coa

# Load environment variables
load_dotenv()

class TransactionCategorizer:
    def __init__(self, db: Database):
        self.db = db
        # Initialize OpenAI client
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please add it to your .env file.")
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def categorize_transactions(self, transactions_df, progress_callback=None):
        """Categorize all uncategorized transactions using AI"""
        # Get historical transactions for reference
        historical_transactions = self._get_historical_transactions()
        
        # Get chart of accounts with types
        chart_of_accounts = self.db.get_chart_of_accounts()
        categories = extract_categories_from_coa(chart_of_accounts)
        category_type_map = create_category_type_map(chart_of_accounts)
        
        # Find uncategorized transactions
        uncategorized_mask = get_uncategorized_mask(transactions_df)
        uncategorized_indices = transactions_df[uncategorized_mask].index.tolist()
        
        if not uncategorized_indices:
            return transactions_df
        
        # Process each transaction
        for i, idx in enumerate(uncategorized_indices):
            row = transactions_df.loc[idx]
            
            # Categorize this transaction
            result = self._categorize_single_transaction(
                row, historical_transactions, categories, category_type_map
            )
            
            # Update the dataframe
            transactions_df.at[idx, 'category'] = result['category']
            transactions_df.at[idx, 'confidence'] = result.get('confidence', 0.5)
            
            # Update progress if callback provided
            if progress_callback:
                progress = (i + 1) / len(uncategorized_indices)
                progress_callback(progress)
        
        return transactions_df
    
    def _get_historical_transactions(self):
        """Get all previously categorized transactions"""
        try:
            query = """
                SELECT description, amount, category, transaction_date as date 
                FROM transactions 
                WHERE category IS NOT NULL 
                AND category != '' 
                AND category != 'Uncategorized'
                ORDER BY transaction_date DESC
                LIMIT 500
            """
            conn = self.db.get_connection()
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error loading historical transactions: {e}")
            return pd.DataFrame()
    
    def _categorize_single_transaction(self, transaction, historical_df, categories, category_type_map):
        """Categorize a single transaction using AI"""
        description = str(transaction.get('description', ''))
        
        if not description:
            return {'category': 'Uncategorized', 'confidence': 0.0}
        
        try:
            # Find similar historical transactions
            similar_transactions = self._find_similar_transactions(description, historical_df)
            
            # Build categories with types
            categories_info = []
            for cat in categories:
                cat_type = category_type_map.get(cat, 'Unknown')
                categories_info.append(f"{cat} ({cat_type})")
            
            # Create prompt
            prompt = f"""You must find a matching historical transaction to categorize this one.

Current transaction: {description}

Similar historical transactions:
{similar_transactions}

STRICT RULE: Only categorize if you find a very similar transaction above. Otherwise return 'Uncategorized'.

Available categories: {', '.join(categories)}

Respond with JSON: {{"category": "category name", "confidence": 0.0-1.0}}"""

            # Call OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial categorization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            # Parse response
            content = response.choices[0].message.content
            # Handle both JSON and plain text responses
            if '{' in content:
                result = json.loads(content)
            else:
                # Fallback for non-JSON responses
                result = {'category': content.strip(), 'confidence': 0.5}
            
            # Validate category
            if result.get('category') not in categories:
                result['category'] = 'Uncategorized'
                result['confidence'] = 0.0
            
            return result
            
        except Exception as e:
            print(f"Error categorizing '{description}': {e}")
            return {'category': 'Uncategorized', 'confidence': 0.0}
    
    def _find_similar_transactions(self, description, historical_df):
        """Find similar transactions from history"""
        if historical_df.empty:
            return "No historical data available"
        
        # More strict word-based similarity
        desc_words = set(description.lower().split())
        # Remove common words that don't help with matching
        stop_words = {'the', 'and', 'or', 'for', 'to', 'from', 'of', 'in', 'on', 'at', 'by'}
        desc_words = desc_words - stop_words
        
        matches = []
        
        for _, row in historical_df.iterrows():
            hist_desc = str(row['description']).lower()
            hist_words = set(hist_desc.split()) - stop_words
            
            # Calculate overlap - need at least 3 meaningful words in common
            common = desc_words.intersection(hist_words)
            if len(common) >= 3 and len(desc_words) > 0:
                # Calculate similarity ratio
                similarity = len(common) / len(desc_words)
                if similarity >= 0.5:  # At least 50% of words match
                    matches.append((similarity, f"- {row['description']} → {row['category']}"))
        
        if not matches:
            return "No similar transactions found"
        
        # Sort by similarity and return top matches
        matches.sort(reverse=True, key=lambda x: x[0])
        return '\n'.join([match[1] for match in matches[:3]])  # Return top 3 matches
    
