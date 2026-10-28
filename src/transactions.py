from datetime import datetime


class TransactionQuery:
    """Filtering and sorting helpers for transaction collections."""

    @staticmethod
    def _parse_date(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.strip().replace('Z', '+00:00')
            if normalized:
                try:
                    return datetime.fromisoformat(normalized)
                except ValueError:
                    return None
        return None

    @classmethod
    def filter(cls, transactions, query='', transaction_type='all',
               date_from='', date_to='', min_amount='', max_amount=''):
        filtered = []
        search = query.strip().lower()

        start = cls._parse_date(date_from)
        end = cls._parse_date(date_to)
        if end:
            end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

        try:
            minimum = float(min_amount) if min_amount != '' else None
        except (TypeError, ValueError):
            minimum = None
        try:
            maximum = float(max_amount) if max_amount != '' else None
        except (TypeError, ValueError):
            maximum = None

        for transaction in transactions:
            description = str(transaction.get('description') or '').lower()
            transaction_type_value = str(transaction.get('type') or '').lower()

            if search and search not in description and search not in transaction_type_value:
                continue
            if transaction_type != 'all' and transaction_type_value != transaction_type:
                continue

            transaction_date = cls._parse_date(transaction.get('date'))
            if start and (transaction_date is None or transaction_date.date() < start.date()):
                continue
            if end and (transaction_date is None or transaction_date.date() > end.date()):
                continue

            try:
                amount = float(transaction.get('amount') or 0)
            except (TypeError, ValueError):
                amount = 0
            if minimum is not None and amount < minimum:
                continue
            if maximum is not None and amount > maximum:
                continue

            filtered.append(transaction)

        return filtered

    @classmethod
    def sort(cls, transactions, field='date', direction='desc'):
        reverse = direction == 'desc'

        def sort_value(transaction):
            if field == 'amount':
                try:
                    return float(transaction.get('amount') or 0)
                except (TypeError, ValueError):
                    return 0
            if field == 'type':
                return str(transaction.get('type') or '').lower()
            if field == 'description':
                return str(transaction.get('description') or '').lower()
            parsed_date = cls._parse_date(transaction.get('date'))
            if parsed_date is None:
                return float('-inf')
            if parsed_date.tzinfo is not None:
                return parsed_date.timestamp()
            return parsed_date.timestamp()

        return sorted(transactions, key=sort_value, reverse=reverse)
