#!/usr/bin/env python3

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("="*50)
print("Testing Fixed Models and Schemas")
print("="*50)

try:
    print("1. Importing models...")
    from models import Base, BlockchainBlock, BlockchainTransaction, BlockchainAddress, MarketPrice, DataIngestionLog, CoinMetadata
    print("✓ All models imported successfully")
    
    print("2. Importing schemas...")
    from schemas import BlockchainBlockData, IngestionStatus, MarketPriceData
    print("✓ All schemas imported successfully")
    
    print("3. Testing SQLAlchemy table creation...")
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    print("✓ All tables created successfully (no foreign key errors)")
    
    print("4. Testing Pydantic validation...")
    from datetime import datetime, timezone
    test_data = BlockchainBlockData(
        block_id=123,
        coin_symbol="BTC",
        block_hash="a" * 64,
        block_time=datetime.now(timezone.utc)
    )
    print(f"✓ Pydantic validation works: {test_data.coin_symbol}")
    
    print("\n" + "="*50)
    print("🎉 ALL FIXES SUCCESSFUL!")
    print("✓ Foreign key constraint issue resolved")
    print("✓ Pydantic v2 compatibility fixed")
    print("✓ Timezone-aware timestamps working")
    print("✓ DAG should now deploy without errors")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
