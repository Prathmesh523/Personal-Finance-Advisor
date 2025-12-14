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
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║         INFRASTRUCTURE SETUP - TERMINAL 1            ║
    ║      Docker + Database + Kafka Consumer              ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    print("\n🏗️  PHASE 1: DOCKER INFRASTRUCTURE")
    
    # Step 1: Clean slate
    run_command("Stopping existing containers", "docker-compose down", check=False)
    
    # Step 2: Start services
    if not run_command("Starting Kafka + PostgreSQL", "docker-compose up -d"):
        print("\n❌ Docker failed to start. Check docker-compose.yml")
        sys.exit(1)
    
    print("\n⏳ Waiting 3 seconds for services to be ready...")
    for i in range(3, 0, -1):
        print(f"   {i}...", end='\r')
        time.sleep(1)
    print("   ✅ Services ready!          ")
    
    # Step 3: Initialize database
    print("\n💾 PHASE 2: DATABASE SETUP")
    if not run_command("Creating database schema", "python init_db.py"):
        print("\n❌ Database initialization failed")
        sys.exit(1)
    
    # Step 4: Start consumer
    print("\n🔄 PHASE 3: KAFKA CONSUMER")
    print("="*60)
    print("⚙️  Starting Kafka Consumer (will run continuously)")
    print("="*60)
    print("\n💡 INSTRUCTIONS:")
    print("   1. Keep this terminal running")
    print("   2. Open a NEW terminal (Terminal 2)")
    print("   3. Run: python run_analysis.py")
    print("   4. Watch messages appear below")
    print("   5. After analysis completes, press Ctrl+C here to stop\n")
    print("="*60)
    print("🚀 CONSUMER STARTING NOW...")
    print("="*60 + "\n")
    
    try:
        # Run consumer (will block until Ctrl+C)
        subprocess.run("python -m app.etl.consumers.data_processor", shell=True)
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 CONSUMER STOPPED")
        print("="*60)
        print("\n💡 To restart everything, run: python start_infrastructure.py")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted")
        sys.exit(1)