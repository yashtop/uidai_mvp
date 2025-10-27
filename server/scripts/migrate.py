# server/scripts/migrate_schema.py - CREATE THIS FILE

from sqlalchemy import create_engine, text, inspect
from src.config import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def get_existing_columns(engine, table_name):
    """Get list of existing columns in a table"""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return None
    
    columns = inspector.get_columns(table_name)
    return [col['name'] for col in columns]

def migrate_test_results(engine):
    """Migrate test_results table to new schema"""
    
    existing_cols = get_existing_columns(engine, 'test_results')
    
    if existing_cols is None:
        print("✅ test_results table doesn't exist, will be created fresh")
        return
    
    print(f"📋 Existing columns: {existing_cols}")
    
    with engine.begin() as conn:
        # Add missing columns
        migrations = []
        
        if 'nodeid' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN nodeid VARCHAR(500)")
            print("  + Adding nodeid column")
        
        if 'test_name' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN test_name VARCHAR(255)")
            print("  + Adding test_name column")
        
        if 'test_file' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN test_file VARCHAR(255)")
            print("  + Adding test_file column")
        
        if 'outcome' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN outcome VARCHAR(50)")
            print("  + Adding outcome column")
        
        if 'duration' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN duration FLOAT")
            print("  + Adding duration column")
        
        if 'error_message' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN error_message TEXT")
            print("  + Adding error_message column")
        
        if 'error_traceback' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN error_traceback TEXT")
            print("  + Adding error_traceback column")
        
        if 'line_number' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN line_number INTEGER")
            print("  + Adding line_number column")
        
        if 'was_healed' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN was_healed BOOLEAN DEFAULT FALSE")
            print("  + Adding was_healed column")
        
        if 'healing_attempt' not in existing_cols:
            migrations.append("ALTER TABLE test_results ADD COLUMN healing_attempt INTEGER")
            print("  + Adding healing_attempt column")
        
        # Execute migrations
        if migrations:
            print(f"\n🔧 Executing {len(migrations)} migrations...")
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                    print(f"  ✅ {sql[:50]}...")
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            print("✅ test_results table migrated")
        else:
            print("✅ test_results table already up to date")

def migrate_test_runs(engine):
    """Migrate test_runs table to new schema"""
    
    existing_cols = get_existing_columns(engine, 'test_runs')
    
    if existing_cols is None:
        print("✅ test_runs table doesn't exist, will be created fresh")
        return
    
    print(f"📋 Existing columns: {existing_cols}")
    
    with engine.begin() as conn:
        migrations = []
        
        # Add missing columns to test_runs
        if 'test_creation_mode' not in existing_cols:
            migrations.append("ALTER TABLE test_runs ADD COLUMN test_creation_mode VARCHAR(50) DEFAULT 'ai'")
            print("  + Adding test_creation_mode column")
        
        if 'healing_result' not in existing_cols:
            migrations.append("ALTER TABLE test_runs ADD COLUMN healing_result JSON")
            print("  + Adding healing_result column")
        
        if 'discovery_data' not in existing_cols:
            migrations.append("ALTER TABLE test_runs ADD COLUMN discovery_data JSON")
            print("  + Adding discovery_data column")
        
        if 'generated_tests' not in existing_cols:
            migrations.append("ALTER TABLE test_runs ADD COLUMN generated_tests JSON")
            print("  + Adding generated_tests column")
        
        if 'scenarios' not in existing_cols:
            migrations.append("ALTER TABLE test_runs ADD COLUMN scenarios JSON")
            print("  + Adding scenarios column")
        
        # Execute migrations
        if migrations:
            print(f"\n🔧 Executing {len(migrations)} migrations...")
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                    print(f"  ✅ {sql[:50]}...")
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            print("✅ test_runs table migrated")
        else:
            print("✅ test_runs table already up to date")

def migrate_database():
    """Run all migrations"""
    engine = create_engine(DATABASE_URL)
    
    print("🔍 Checking database schema...\n")
    
    # Migrate test_results
    print("📊 Migrating test_results table...")
    migrate_test_results(engine)
    
    print("\n📊 Migrating test_runs table...")
    migrate_test_runs(engine)
    
    # Create missing tables
    print("\n🔨 Creating any missing tables...")
    from src.database.models import Base
    Base.metadata.create_all(engine)
    
    print("\n✅ Database migration complete!")
    
    # Show final schema
    print("\n📋 Final tables:")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """))
        for row in result:
            print(f"  - {row[0]}")

if __name__ == "__main__":
    migrate_database()