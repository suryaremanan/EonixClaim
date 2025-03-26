"""
Customer database manager for Eonix insurance platform.
Stores and manages customer data with CSV import/export capabilities.
"""
import os
import logging
import json
import csv
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

class CustomerDatabase:
    """
    Customer database manager.
    Handles storage, retrieval, and export of customer data.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the customer database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), '../data/customers.db')
        self.conn = None
        
        # Initialize database
        self._initialize_db()
        
        logger.info("Customer database initialized")
    
    def _initialize_db(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        try:
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create customers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    policy_number TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT
                )
            ''')
            
            # Create claims table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT,
                    policy_number TEXT,
                    claim_date TEXT,
                    damage_type TEXT,
                    severity TEXT,
                    estimated_amount REAL,
                    status TEXT,
                    blockchain_id TEXT,
                    blockchain_tx TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
            
            # Create appointments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT,
                    customer_id TEXT,
                    service_station_id TEXT,
                    appointment_date TEXT,
                    appointment_time TEXT,
                    status TEXT,
                    confirmation_code TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT,
                    FOREIGN KEY (claim_id) REFERENCES claims (id),
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            if self.conn:
                self.conn.close()
                self.conn = None
    
    def _ensure_connection(self) -> bool:
        """
        Ensure database connection is active.
        
        Returns:
            True if connection is active, False otherwise
        """
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
                return True
            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                return False
        return True
    
    def add_customer(self, customer_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new customer to the database.
        
        Args:
            customer_data: Dictionary containing customer information
            
        Returns:
            Customer ID if successful, None otherwise
        """
        if not self._ensure_connection():
            return None
        
        try:
            cursor = self.conn.cursor()
            
            # Generate customer ID if not provided
            customer_id = customer_data.get('id') or f"CUST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Prepare metadata
            metadata = customer_data.get('metadata', {})
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)
            
            # Insert customer data
            cursor.execute('''
                INSERT INTO customers (
                    id, name, email, phone, address, policy_number, 
                    created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id,
                customer_data.get('name', ''),
                customer_data.get('email', ''),
                customer_data.get('phone', ''),
                customer_data.get('address', ''),
                customer_data.get('policy_number', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                metadata
            ))
            
            self.conn.commit()
            logger.info(f"Added customer {customer_id} to database")
            
            return customer_id
            
        except Exception as e:
            logger.error(f"Error adding customer to database: {e}")
            return None
    
    def add_claim(self, claim_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new claim to the database.
        
        Args:
            claim_data: Dictionary containing claim information
            
        Returns:
            Claim ID if successful, None otherwise
        """
        if not self._ensure_connection():
            return None
        
        try:
            cursor = self.conn.cursor()
            
            # Generate claim ID if not provided
            claim_id = claim_data.get('id') or f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Prepare metadata
            metadata = claim_data.get('metadata', {})
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)
            
            # Insert claim data
            cursor.execute('''
                INSERT INTO claims (
                    id, customer_id, policy_number, claim_date, damage_type, 
                    severity, estimated_amount, status, blockchain_id, blockchain_tx,
                    created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                claim_id,
                claim_data.get('customer_id', ''),
                claim_data.get('policy_number', ''),
                claim_data.get('claim_date', datetime.now().isoformat()),
                claim_data.get('damage_type', ''),
                claim_data.get('severity', ''),
                claim_data.get('estimated_amount', 0.0),
                claim_data.get('status', 'Pending'),
                claim_data.get('blockchain_id', ''),
                claim_data.get('blockchain_tx', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                metadata
            ))
            
            self.conn.commit()
            logger.info(f"Added claim {claim_id} to database")
            
            return claim_id
            
        except Exception as e:
            logger.error(f"Error adding claim to database: {e}")
            return None
    
    def add_appointment(self, appointment_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new appointment to the database.
        
        Args:
            appointment_data: Dictionary containing appointment information
            
        Returns:
            Appointment ID if successful, None otherwise
        """
        if not self._ensure_connection():
            return None
        
        try:
            cursor = self.conn.cursor()
            
            # Generate appointment ID if not provided
            appointment_id = appointment_data.get('id') or f"APT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Prepare metadata
            metadata = appointment_data.get('metadata', {})
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)
            
            # Insert appointment data
            cursor.execute('''
                INSERT INTO appointments (
                    id, claim_id, customer_id, service_station_id, 
                    appointment_date, appointment_time, status, confirmation_code,
                    created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                appointment_id,
                appointment_data.get('claim_id', ''),
                appointment_data.get('customer_id', ''),
                appointment_data.get('service_station_id', ''),
                appointment_data.get('appointment_date', ''),
                appointment_data.get('appointment_time', ''),
                appointment_data.get('status', 'Scheduled'),
                appointment_data.get('confirmation_code', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                metadata
            ))
            
            self.conn.commit()
            logger.info(f"Added appointment {appointment_id} to database")
            
            return appointment_id
            
        except Exception as e:
            logger.error(f"Error adding appointment to database: {e}")
            return None
    
    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get customer information by ID.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer data dictionary or None if not found
        """
        if not self._ensure_connection():
            return None
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                SELECT id, name, email, phone, address, policy_number, 
                       created_at, updated_at, metadata
                FROM customers
                WHERE id = ?
            ''', (customer_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Parse metadata
            metadata = row[8]
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
            
            return {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'address': row[4],
                'policy_number': row[5],
                'created_at': row[6],
                'updated_at': row[7],
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error retrieving customer {customer_id}: {e}")
            return None
    
    def get_customer_claims(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        Get all claims for a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            List of claim data dictionaries
        """
        if not self._ensure_connection():
            return []
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                SELECT id, customer_id, policy_number, claim_date, damage_type, 
                       severity, estimated_amount, status, blockchain_id, blockchain_tx,
                       created_at, updated_at, metadata
                FROM claims
                WHERE customer_id = ?
                ORDER BY created_at DESC
            ''', (customer_id,))
            
            claims = []
            
            for row in cursor.fetchall():
                # Parse metadata
                metadata = row[12]
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
                
                claims.append({
                    'id': row[0],
                    'customer_id': row[1],
                    'policy_number': row[2],
                    'claim_date': row[3],
                    'damage_type': row[4],
                    'severity': row[5],
                    'estimated_amount': row[6],
                    'status': row[7],
                    'blockchain_id': row[8],
                    'blockchain_tx': row[9],
                    'created_at': row[10],
                    'updated_at': row[11],
                    'metadata': metadata
                })
            
            return claims
            
        except Exception as e:
            logger.error(f"Error retrieving claims for customer {customer_id}: {e}")
            return []
    
    def export_all_data_csv(self, output_dir: str = None) -> Optional[str]:
        """
        Export all customer and claim data to CSV files.
        
        Args:
            output_dir: Directory to save CSV files
            
        Returns:
            Path to the output directory if successful, None otherwise
        """
        if not self._ensure_connection():
            return None
        
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(__file__), '../exports')
        
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Timestamp for filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export customers
            customers_path = os.path.join(output_dir, f'customers_{timestamp}.csv')
            with open(customers_path, 'w', newline='') as csvfile:
                cursor = self.conn.cursor()
                cursor.execute('SELECT * FROM customers')
                
                # Get column names
                column_names = [description[0] for description in cursor.description]
                
                # Create CSV writer
                writer = csv.writer(csvfile)
                writer.writerow(column_names)
                
                # Write data rows
                for row in cursor.fetchall():
                    writer.writerow(row)
            
            # Export claims
            claims_path = os.path.join(output_dir, f'claims_{timestamp}.csv')
            with open(claims_path, 'w', newline='') as csvfile:
                cursor = self.conn.cursor()
                cursor.execute('SELECT * FROM claims')
                
                # Get column names
                column_names = [description[0] for description in cursor.description]
                
                # Create CSV writer
                writer = csv.writer(csvfile)
                writer.writerow(column_names)
                
                # Write data rows
                for row in cursor.fetchall():
                    writer.writerow(row)
            
            # Export appointments
            appointments_path = os.path.join(output_dir, f'appointments_{timestamp}.csv')
            with open(appointments_path, 'w', newline='') as csvfile:
                cursor = self.conn.cursor()
                cursor.execute('SELECT * FROM appointments')
                
                # Get column names
                column_names = [description[0] for description in cursor.description]
                
                # Create CSV writer
                writer = csv.writer(csvfile)
                writer.writerow(column_names)
                
                # Write data rows
                for row in cursor.fetchall():
                    writer.writerow(row)
            
            logger.info(f"Exported all data to CSV files in {output_dir}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Error exporting data to CSV: {e}")
            return None
    
    def search_customers(self, search_term: str = None) -> List[Dict[str, Any]]:
        """
        Search for customers in the database.
        
        Args:
            search_term: Optional search term to filter customers
            
        Returns:
            List of matching customer records
        """
        try:
            cursor = self.conn.cursor()
            
            if search_term:
                # Search by name, email, or policy number
                query = """
                SELECT * FROM customers 
                WHERE name LIKE ? OR email LIKE ? OR policy_number LIKE ?
                """
                search_pattern = f"%{search_term}%"
                cursor.execute(query, (search_pattern, search_pattern, search_pattern))
            else:
                # Return all customers if no search term provided
                cursor.execute("SELECT * FROM customers")
            
            # Convert to dictionary format
            columns = [col[0] for col in cursor.description]
            customers = []
            
            for row in cursor.fetchall():
                customer = dict(zip(columns, row))
                customers.append(customer)
            
            return customers
            
        except Exception as e:
            logger.error(f"Error searching customers: {e}")
            return []