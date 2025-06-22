#!/usr/bin/env python3
"""
Quick test script to verify SQLAlchemy models work correctly
and the database can be initialized without errors.
"""

import sys
import os
from datetime import datetime, timezone

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_models():
    """Test that models can be imported and created without errors."""
    print("Testing SQLAlchemy models...")
    
    try:
        from models import Base, BlockchainBlock, BlockchainTransaction, BlockchainAddress, MarketPrice, DataIngestionLog, CoinMetadata
        print("✓ Models imported successfully")
        
        # Test that we can create the declarative base
        print(f"✓ Base metadata tables: {len(Base.metadata.tables)}")
        
        # Test model creation (in memory)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Use in-memory SQLite for testing
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        print("✓ Tables created in memory database")
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test creating a sample record
        test_block = BlockchainBlock(
            block_id=1,
            coin_symbol="BTC",
            block_hash="test_hash_123",
            block_time=datetime.now(timezone.utc),
            transaction_count=10
        )
        
        session.add(test_block)
        session.commit()
        print("✓ Sample block record created and committed")
        
        # Test querying
        retrieved = session.query(BlockchainBlock).filter_by(block_id=1).first()
        if retrieved:
            print(f"✓ Sample block retrieved: {retrieved}")
        else:
            print("✗ Failed to retrieve sample block")
            return False
            
        session.close()
        print("✓ Session closed successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_settings():
    """Test that settings can be loaded."""
    print("\nTesting settings...")
    
    try:
        from core.settings import settings, get_active_coins, get_coin_symbol_mapping
        print("✓ Settings imported successfully")
        
        print(f"✓ Database URL: {settings.database.url[:30]}...")
        print(f"✓ Environment: {settings.environment}")
        print(f"✓ Default coins: {settings.ingestion.default_coins}")
        
        active_coins = get_active_coins()
        print(f"✓ Active coins: {[coin['symbol'] for coin in active_coins]}")
        
        coin_mapping = get_coin_symbol_mapping()
        print(f"✓ CoinGecko mapping: {list(coin_mapping.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_service():
    """Test that database service works."""
    print("\nTesting database service...")
    
    try:
        # Fix relative import issue
        import sys
        sys.path.append('/home/mieszek/dev/business-intelligence/src')
        
        from database import DatabaseService
        print("✓ DatabaseService imported successfully")
        
        # Test with in-memory database
        db = DatabaseService("sqlite:///:memory:")
        print("✓ DatabaseService created")
        
        db.create_tables()
        print("✓ Tables created via DatabaseService")
        
        # Test session context manager
        with db.get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT 1 as test")).fetchone()
            print(f"✓ Session test query result: {result}")
        
        print("✓ DatabaseService session context manager works")
        return True
        
    except Exception as e:
        print(f"✗ DatabaseService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("SQLAlchemy Models and Settings Test")
    print("="*60)
    
    tests = [
        ("Models", test_models),
        ("Settings", test_settings),
        ("Database Service", test_database_service),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        success = test_func()
        results.append((test_name, success))
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    all_passed = True
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:<20}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! The SQLAlchemy models are working correctly.")
        print("   The DAG should now work without the AttributeError.")
    else:
        print("\n❌ Some tests failed. Please fix the issues before running the DAG.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
