"""
Database initialization script for the Eonix insurance platform.
Creates database schema and loads initial data.
"""
import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
import random
import sys
import uuid
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.customer_db import CustomerDatabase
from blockchain.enhanced_client import EnhancedBlockchainClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_sample_customers(db: CustomerDatabase, count=10):
    """Generate sample customers for testing."""
    logger.info(f"Generating {count} sample customers...")
    
    first_names = ["John", "Emma", "Michael", "Sophia", "William", "Olivia", "James", "Ava", "Robert", "Isabella"]
    last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
    
    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"
        
        # Create a truly unique ID by adding an index
        unique_id = f"CUST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i+1}"
        
        customer_data = {
            'id': unique_id,  # Add explicit ID
            'name': f"{first_name} {last_name}",
            'email': email,
            'phone': f"(555) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
            'address': f"{random.randint(100, 999)} Main St, San Francisco, CA 9410{random.randint(1, 9)}",
            'policy_number': f"POL-{random.randint(10000, 99999)}",
            'policy_type': random.choice(["Full Coverage", "Liability", "Collision"]),
            'vehicle_info': json.dumps({
                'make': random.choice(["Toyota", "Honda", "Ford", "BMW", "Tesla"]),
                'model': random.choice(["Camry", "Civic", "F-150", "Model 3", "X5"]),
                'year': random.randint(2015, 2023),
                'vin': ''.join(random.choices("0123456789ABCDEFGHJKLMNPRSTUVWXYZ", k=17))
            })
        }
        
        customer_id = db.add_customer(customer_data)
        logger.info(f"Created customer: {customer_id}")

def generate_sample_claims(db: CustomerDatabase, blockchain: EnhancedBlockchainClient, count=5):
    """Generate sample claims for testing."""
    logger.info(f"Generating {count} sample claims...")
    
    # Generate a sample customer if none exist
    customer_id = "CUST-20250325112032"  # Use the first customer ID created
    
    for i in range(count):
        # Generate claim data
        claim_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        damage_type = random.choice(["Collision", "Theft", "Vandalism", "Weather", "Fire"])
        severity = random.choice(["Minor", "Moderate", "Severe"])
        amount = random.randint(500, 10000)
        
        # Generate blockchain ID
        blockchain_id = blockchain.generate_unique_claim_id(customer_id)
        
        # Prepare blockchain data
        blockchain_data = {
            'claim_date': claim_date,
            'damage_type': damage_type,
            'severity': severity,
            'amount': amount,
            'recorded_at': int(time.time())
        }
        
        # Record on blockchain
        tx_hash = blockchain.record_claim(
            blockchain_id,
            customer_id,
            "POL-12345",  # Sample policy number
            blockchain_data
        )
        
        # Create claim data
        claim_data = {
            'id': f"CL-{datetime.now().strftime('%Y%m%d')}-{i+1}",
            'customer_id': customer_id,
            'policy_number': "POL-12345",
            'claim_date': claim_date,
            'damage_type': damage_type,
            'severity': severity,
            'status': random.choice(["Submitted", "In Review", "Approved", "Completed"]),
            'amount': amount,
            'repair_time': f"{random.randint(1, 10)} days",
            'blockchain_id': blockchain_id,
            'blockchain_tx': tx_hash,
            'metadata': json.dumps({
                'damage_parts': random.sample(["Bumper", "Hood", "Door", "Fender", "Windshield"], 
                                             k=random.randint(1, 3)),
                'damage_description': f"{severity} {damage_type.lower()} requiring repair",
                'image_path': ''
            })
        }
        
        # Store in database
        claim_id = db.add_claim(claim_data)
        logger.info(f"Created claim: {claim_id}")

def main():
    """Initialize the database and load sample data."""
    try:
        # Create directories
        os.makedirs("data", exist_ok=True)
        os.makedirs("data/exports", exist_ok=True)
        
        # Initialize database
        db = CustomerDatabase()
        blockchain = EnhancedBlockchainClient()
        
        # Generate sample data
        generate_sample_customers(db)
        generate_sample_claims(db, blockchain)
        
        logger.info("Database initialization complete")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 