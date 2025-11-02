#!/usr/bin/env python3
"""
Code quality checker for Bookkeeper project
Run this before committing to catch common issues
"""
import ast
import os
import re
from pathlib import Path
from collections import defaultdict

class CodeQualityChecker:
    def __init__(self):
        self.issues = []
        self.python_files = ['bookkeeper.py', 'database.py', 'categorizer.py', 'utils.py', 'helpers.py']
        
    def check_unused_imports(self, filename):
        """Check for unused imports in a file"""
        with open(filename, 'r') as f:
            content = f.read()
            
        try:
            tree = ast.parse(content)
        except SyntaxError:
            self.issues.append(f"❌ {filename}: Syntax error - skipping import check")
            return
            
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    if alias.name == '*':
                        imports.append('*')
                    else:
                        imports.append(alias.name)
        
        # Check usage
        for imp in imports:
            if imp == '*':
                continue
            # Simple check - look for the import name in the code
            if content.count(imp) == 1:  # Only appears in import line
                self.issues.append(f"⚠️  {filename}: Possibly unused import '{imp}'")
                
    def check_duplicate_patterns(self):
        """Check for common duplicate patterns"""
        patterns = {
            'uncategorized_check': [
                r"category.*==.*''.*\|.*category.*==.*'Uncategorized'",
                r"category.*\.isna\(\).*\|.*category.*==.*''",
            ],
            'date_column_check': [
                r"'date'.*in.*columns.*else.*'transaction_date'",
                r"if.*'date'.*in.*\.columns",
            ],
            'category_extraction': [
                r"\[cat\[0\].*for.*cat.*in.*get_chart_of_accounts",
            ]
        }
        
        for pattern_name, pattern_list in patterns.items():
            occurrences = defaultdict(list)
            for filename in self.python_files:
                if os.path.exists(filename):
                    with open(filename, 'r') as f:
                        content = f.read()
                        for i, line in enumerate(content.split('\n'), 1):
                            for pattern in pattern_list:
                                if re.search(pattern, line):
                                    occurrences[filename].append(i)
                                    
            if len(occurrences) > 1:
                locations = []
                for file, lines in occurrences.items():
                    locations.append(f"{file}:{','.join(map(str, lines))}")
                self.issues.append(f"⚠️  Duplicate pattern '{pattern_name}' found in: {', '.join(locations)}")
                
    def check_empty_functions(self):
        """Check for empty or pass-only functions"""
        for filename in self.python_files:
            if not os.path.exists(filename):
                continue
                
            with open(filename, 'r') as f:
                content = f.read()
                
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
                
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) == 1:
                        if isinstance(node.body[0], ast.Pass):
                            self.issues.append(f"⚠️  {filename}: Empty function '{node.name}' with only pass statement")
                        elif (isinstance(node.body[0], ast.Expr) and 
                              isinstance(node.body[0].value, ast.Constant) and
                              isinstance(node.body[0].value.value, str)):
                            # Function with only a docstring
                            pass
                            
    def check_database_usage(self):
        """Check for references to removed database tables"""
        removed_tables = ['column_mappings', 'reconciliations']
        removed_methods = ['save_column_mapping', 'get_column_mappings', 'get_column_mapping', 'save_reconciliation']
        
        for filename in self.python_files:
            if not os.path.exists(filename):
                continue
                
            with open(filename, 'r') as f:
                content = f.read()
                
            for table in removed_tables:
                if table in content:
                    self.issues.append(f"❌ {filename}: Reference to removed table '{table}'")
                    
            for method in removed_methods:
                if method in content:
                    self.issues.append(f"❌ {filename}: Reference to removed method '{method}'")
                    
    def run_checks(self):
        """Run all quality checks"""
        print("🔍 Running code quality checks...\n")
        
        # Check each file exists
        for filename in self.python_files:
            if not os.path.exists(filename):
                print(f"Skipping {filename} (not found)")
                continue
                
            self.check_unused_imports(filename)
            
        self.check_duplicate_patterns()
        self.check_empty_functions()
        self.check_database_usage()
        
        # Report results
        if self.issues:
            print("Found the following potential issues:\n")
            for issue in self.issues:
                print(issue)
            print(f"\n📊 Total issues found: {len(self.issues)}")
            print("\n💡 Tip: Review DEVELOPMENT_GUIDE.md for best practices")
            return 1
        else:
            print("✅ No code quality issues found!")
            return 0

if __name__ == "__main__":
    checker = CodeQualityChecker()
    exit(checker.run_checks())