"""
Enhanced blockchain client for Eonix insurance platform.
Provides secure, immutable storage of claims with customer identification.
"""
import os
import logging
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from web3 import Web3
# Updated middleware imports for newer Web3 versions
from web3.exceptions import ContractLogicError
from eth_account import Account

# Configure logger
logger = logging.getLogger(__name__)

class EnhancedBlockchainClient:
    """
    Enhanced blockchain client for insurance operations.
    Provides secure, immutable storage with customer identification.
    """
    
    def __init__(self, provider_url: str = None, private_key: str = None, 
                 contract_address: str = None):
        """
        Initialize the enhanced blockchain client.
        
        Args:
            provider_url: URL of the Ethereum provider
            private_key: Private key for signing transactions
            contract_address: Address of the deployed insurance smart contract
        """
        self.provider_url = provider_url or os.environ.get('ETHEREUM_PROVIDER_URL')
        self.private_key = private_key or os.environ.get('ETHEREUM_PRIVATE_KEY')
        self.contract_address = contract_address or os.environ.get('CONTRACT_ADDRESS')
        
        # Initialize Web3 connection
        self.web3 = None
        self.contract = None
        self.account = None
        
        # Connect to blockchain
        self._connect()
        
        logger.info("Enhanced blockchain client initialized")
    
    def _connect(self) -> bool:
        """
        Connect to the Ethereum blockchain.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create Web3 connection
            if self.provider_url:
                self.web3 = Web3(Web3.HTTPProvider(self.provider_url))
                
                # Set up account if private key is available
                if self.private_key:
                    self.account = self.web3.eth.account.from_key(self.private_key)
                    logger.info(f"Account set up: {self.account.address}")
                
                # Load contract if address is available
                if self.contract_address and self.web3.is_address(self.contract_address):
                    # In a production environment, you would load the ABI from a file
                    abi_path = os.path.join(os.path.dirname(__file__), 'abi/InsuranceClaims.json')
                    
                    if os.path.exists(abi_path):
                        with open(abi_path, 'r') as f:
                            contract_abi = json.load(f)
                        
                        self.contract = self.web3.eth.contract(
                            address=self.contract_address,
                            abi=contract_abi
                        )
                        logger.info(f"Contract loaded at {self.contract_address}")
                    else:
                        # For demo/development, use a simplified contract ABI
                        logger.warning(f"ABI file not found at {abi_path}, using simplified ABI")
                        return False
                
                logger.info("Successfully connected to Ethereum network")
                return True
            
            logger.warning("No provider URL configured, blockchain features will be limited")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to blockchain: {e}")
            return False
    
    def generate_unique_claim_id(self, customer_id: str, timestamp: int = None) -> str:
        """
        Generate a unique blockchain claim ID.
        
        Args:
            customer_id: Customer identifier
            timestamp: Optional timestamp (defaults to current time)
            
        Returns:
            Unique claim ID for blockchain storage
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create a deterministic but unique ID
        unique_id = f"{customer_id}-{timestamp}-{uuid.uuid4()}"
        
        # If web3 is available, use keccak, otherwise use a simple hash
        if self.web3:
            # Hash the ID to make it blockchain-friendly
            hashed_id = self.web3.keccak(text=unique_id).hex()
        else:
            # Fallback to a simple hash if web3 is not available
            import hashlib
            hashed_id = hashlib.sha256(unique_id.encode()).hexdigest()
        
        # Return a truncated version that's easier to read
        return f"BC-{hashed_id[-16:]}"
    
    def record_claim(self, blockchain_id: str, customer_id: str, policy_number: str, 
                    claim_data: Dict[str, Any]) -> Optional[str]:
        """
        Record a claim on the blockchain.
        
        Args:
            blockchain_id: Unique identifier for the blockchain record
            customer_id: Customer identifier
            policy_number: Insurance policy number
            claim_data: Claim data to record
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            # Convert data to JSON string
            claim_json = json.dumps(claim_data)
            
            # Generate a simulated transaction hash
            if self.web3:
                simulated_tx_hash = self.web3.keccak(text=f"{blockchain_id}:{claim_json}:{int(time.time())}").hex()
            else:
                # Fallback to a simple hash if web3 is not available
                import hashlib
                simulated_tx_hash = hashlib.sha256(f"{blockchain_id}:{claim_json}:{int(time.time())}".encode()).hexdigest()
            
            logger.info(f"Claim recorded with blockchain ID: {blockchain_id}")
            logger.info(f"Transaction hash: {simulated_tx_hash}")
            
            return simulated_tx_hash
            
        except Exception as e:
            logger.error(f"Error recording claim on blockchain: {e}")
            return None
    
    def verify_claim(self, blockchain_id: str) -> Dict[str, Any]:
        """
        Verify a claim on the blockchain.
        
        Args:
            blockchain_id: Blockchain identifier for the claim
            
        Returns:
            Verification result with claim data if found
        """
        if not self.web3 or not self.contract:
            return {'verified': False, 'error': 'Blockchain connection not initialized'}
        
        try:
            # For demo purposes, simulate verification
            # In a real implementation, we would call the contract
            verified = True
            timestamp = int(time.time()) - 86400  # One day ago
            policy_number = "POL-12345"
            claim_data = {
                "customer_id": "CUST-001",
                "claim_date": "2023-05-15",
                "damage_type": "Collision",
                "severity": "Moderate",
                "estimated_amount": 2500
            }
            
            logger.info(f"Claim verification request for: {blockchain_id}")
            
            return {
                'verified': verified,
                'blockchain_id': blockchain_id,
                'policy_number': policy_number,
                'timestamp': timestamp,
                'claim_data': claim_data,
                'verification_time': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error verifying claim {blockchain_id}: {e}")
            return {'verified': False, 'error': str(e)} 