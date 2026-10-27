from datetime import datetime, timedelta


# Manages financial transactions stored in Supabase.
class FinanceTracker:
    def __init__(self, supabase_client, user_id):
        self.supabase = supabase_client
        self.user_id = user_id
        self.transactions = self.load_data()

    def load_data(self):
        response = (
            self.supabase
            .table("transactions")
            .select("id, date, type, amount, description")
            .eq("user_id", self.user_id)
            .order("date")
            .execute()
        )
        return response.data

    #Adding new transactions
    def add_transaction(self, amount, trans_type, description=''):
        transaction = {
            'user_id': self.user_id,
            'type': trans_type,
            'amount': float(amount),
            'description': description,
        }

        response = (
            self.supabase
            .table("transactions")
            .insert(transaction)
            .select("id, date, type, amount, description")
            .execute()
        )
        inserted_transaction = response.data[0]
        self.transactions.append(inserted_transaction)
        return inserted_transaction

    def delete_transaction(self, transaction_id):
        response = (
            self.supabase
            .table("transactions")
            .delete()
            .eq("id", transaction_id)
            .eq("user_id", self.user_id)
            .execute()
        )
        if response.data:
            self.transactions = [
                transaction for transaction in self.transactions
                if transaction['id'] != transaction_id
            ]
        return response.data

    #Current total balance
    def get_balance(self):
            # Start with balance of 0
            balance = 0
            
            # Loop through every transaction in our list
            # 't' is a temporary variable holding each transaction dictionary
            for t in self.transactions:
                # Check if this transaction is income
                if t['type'] == 'income':
                    # Add income to balance
                    balance += t['amount']
                else:  # Must be 'expense'
                    # Subtract expense from balance
                    balance -= t['amount']
            
            # Return the final calculated balance
            return balance

    def _parse_date(self, value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        raise ValueError(f"Invalid transaction date: {value}")

    #Calculate balance for each day using ML
    def get_daily_balances(self):
            # If no transactions exist, return empty lists
            if not self.transactions:
                return [], []
            
            # Sort transactions by date (earliest first)
            # lambda x: x['date'] means "sort by the 'date' field of each transaction"
            sorted_trans = sorted(self.transactions, key=lambda x: x['date'])
            
            # Get the date of the very first transaction
            # strptime() converts string '2025-01-11 14:30:00' to datetime object
            start_date = self._parse_date(sorted_trans[0]['date'])
            
            # Initialize empty lists to store our results
            dates = []  # Will hold date objects
            balances = []  # Will hold balance amounts
            
            # Start with balance of 0 and the first transaction's date
            current_balance = 0
            current_date = start_date.date()  # .date() extracts just the date (no time)
            
            # Process each transaction in chronological order
            for t in sorted_trans:
                # Get the date of this transaction
                trans_date = self._parse_date(t['date']).date()
                
                # Fill in all days BEFORE this transaction (days with no activity)
                # Example: If transaction on Jan 5 and we're on Jan 3, fill Jan 3 and 4
                while current_date < trans_date:
                    # Record the current date and balance
                    dates.append(current_date)
                    balances.append(current_balance)
                    
                    # Move to next day (timedelta(days=1) = 1 day)
                    current_date += timedelta(days=1)
                
                # Now apply this transaction to the balance
                if t['type'] == 'income':
                    current_balance += t['amount']  # Add income
                else:
                    current_balance -= t['amount']  # Subtract expense
            
            # Add the final day's balance (today)
            dates.append(current_date)
            balances.append(current_balance)
            
            # Return both lists as a tuple
            return dates, balances

    #Get summary information and stats
    def get_summary_stats(self):
            # Sum all amounts where type is 'income'
            # This is a "list comprehension" - compact way to filter and sum
            # It loops through transactions, picks only income ones, extracts amount, and sums
            total_income = sum(t['amount'] for t in self.transactions if t['type'] == 'income')
            
            # Same but for expenses
            total_expenses = sum(t['amount'] for t in self.transactions if t['type'] == 'expense')
            
            # Return all stats as a dictionary
            return {
                'total_income': total_income,
                'total_expenses': total_expenses,
                'balance': self.get_balance(),  # Call our balance calculation method
                'transaction_count': len(self.transactions)  # len() returns list length
            }