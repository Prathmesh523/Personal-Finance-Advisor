#!/usr/bin/env python3
"""
Infrastructure Startup Script
Run this in Terminal 1 and keep it running
"""
import subprocess
import time
import sys

def run_command(description, command, check=True):
    """Execute command with status"""
    print(f"\n{'='*60}")
    print(f"⚙️  {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True)
    
    if check and result.returncode != 0:
        print(f"❌ {description} - FAILED")
        return False
    
    print(f"✅ {description} - COMPLETE")
    return True

def main():
    # Check for reset flag
    reset_mode = '--reset' in sys.argv or '-r' in sys.argv
    
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║         INFRASTRUCTURE SETUP - TERMINAL 1            ║
    ║      Docker + Database + RabbitMQ Consumer           ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    if reset_mode:
        print("⚠️  RESET MODE: Will drop all tables and recreate schema\n")
    else:
        print("ℹ️  NORMAL MODE: Using existing schema\n")
        print("💡 To reset schema, run: python3 start_infra.py --reset\n")
    
    print("🏗️  PHASE 1: DOCKER INFRASTRUCTURE")
    
    # Step 1: Clean slate
    run_command("Stopping existing containers", "docker-compose down -v", check=False)
    
    # Step 2: Start services
    if not run_command("Starting RabbitMQ + PostgreSQL", "docker-compose up -d --force-recreate"):
        print("\n❌ Docker failed to start. Check docker-compose.yml")
        sys.exit(1)
    
    print("\n⏳ Waiting 5 seconds for services to be ready...")
    for i in range(5, 0, -1):
        print(f"   {i}...", end='\r')
        time.sleep(1)
    print("   ✅ Services ready!          ")
    
    # Step 3: Database setup
    print("\n💾 PHASE 2: DATABASE SETUP")
    
    if reset_mode:
        # Reset schema (drop + recreate)
        if not run_command("Resetting database schema", "python3 reset_schema.py"):
            print("\n❌ Schema reset failed")
            sys.exit(1)
    else:
        # Check if tables exist, if not create them
        print("Checking if schema exists...")
        result = subprocess.run(
            "python3 -c \"from app.database.connection import get_db_connection; conn = get_db_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN (\\\"bank_transactions\\\", \\\"splitwise_transactions\\\")'); count = cur.fetchone()[0]; cur.close(); conn.close(); exit(0 if count == 2 else 1)\"",
            shell=True,
            capture_output=True
        )
        
        if result.returncode != 0:
            print("Schema not found, creating...")
            if not run_command("Creating database schema", "python3 reset_schema.py"):
                print("\n❌ Schema creation failed")
                sys.exit(1)
        else:
            print("✅ Schema exists, skipping creation")
    
    # Step 4: Start consumer
    print("\n🔄 PHASE 3: RABBITMQ CONSUMER")
    print("="*60)
    print("⚙️  Starting RabbitMQ Consumer (will run continuously)")
    print("="*60)
    print("\n💡 INSTRUCTIONS:")
    print("   1. Keep this terminal running")
    print("   2. Open a NEW terminal (Terminal 2)")
    print("   3. Run: python3 run_analysis.py")
    print("   4. Watch messages appear below")
    print("   5. After analysis completes, press Ctrl+C here to stop\n")
    print("="*60)
    print("🚀 CONSUMER STARTING NOW...")
    print("="*60 + "\n")
    
    try:
        # Run consumer (will block until Ctrl+C)
        subprocess.run("python3 -m app.etl.consumers.data_processor", shell=True)
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 CONSUMER STOPPED")
        print("="*60)
        print("\n💡 To restart:")
        print("   Normal mode: python3 start_infra.py")
        print("   Reset mode:  python3 start_infra.py --reset")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted")
        sys.exit(1)