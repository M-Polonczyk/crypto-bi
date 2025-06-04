from datetime import datetime, timedelta

def get_yesterday_date_str(format="%Y-%m-%d"):
    """Returns yesterday's date as a string."""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime(format)

def get_date_str_for_coingecko(date_obj=None):
    """Returns date as dd-mm-yyyy string for CoinGecko."""
    if date_obj is None:
        date_obj = datetime.now() - timedelta(days=1)
    return date_obj.strftime("%d-%m-%Y")

if __name__ == '__main__':
    print(f"Yesterday (YYYY-MM-DD): {get_yesterday_date_str()}")
    print(f"Yesterday for CoinGecko (DD-MM-YYYY): {get_date_str_for_coingecko()}")