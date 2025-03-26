"""
Ethereum blockchain client module.

This module provides integration with the Ethereum blockchain for secure,
immutable storage of insurance claims and transaction logs.
"""
import logging
from typing import Dict, Any, Optional
import json
import time

from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account
from eth_account.signers.local import LocalAccount

from config.config import ETHEREUM_PROVIDER_URL, ETHEREUM_PRIVATE_KEY, CONTRACT_ADDRESS

# Configure logger
logger = logging.getLogger(__name__)

class EthereumClient:
    """
    Ethereum blockchain client for insurance operations.
    
    This class handles interactions with the Ethereum blockchain for secure,
    immutable storage of insurance claims and transaction logs.
    """
    
    def __init__(self, provider_url: str = ETHEREUM_PROVIDER_URL,
                 private_key: str = ETHEREUM_PRIVATE_KEY,
                 contract_address: str = CONTRACT_ADDRESS):
        """
        Initialize the Ethereum client.
        
        Args:
            provider_url: URL of the Ethereum provider
            private_key: Private key for signing transactions
            contract_address: Address of the deployed insurance smart contract
        """
        self.provider_url = provider_url
        self.private_key = private_key
        self.contract_address = contract_address
        self.web3 = None
        self.account = None
        self.contract = None
        
        # Connect to Ethereum network
        self._connect()
        
    def _connect(self) -> bool:
        """
        Connect to the Ethereum network.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Connect to Ethereum provider
            self.web3 = Web3(Web3.HTTPProvider(self.provider_url))
            
            if not self.web3.is_connected():
                logger.error(f"Failed to connect to Ethereum provider at {self.provider_url}")
                return False
                
            # Set up account for transaction signing
            if self.private_key:
                self.account = Account.from_key(self.private_key)
                
            # Load smart contract
            if self.contract_address:
                self._load_contract()
                
            logger.info(f"Successfully connected to Ethereum network at {self.provider_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Ethereum network: {e}")
            return False
            
    def _load_contract(self) -> None:
        """Load the insurance smart contract."""
        try:
            # In a real implementation, we would load the contract ABI from a file
            # Here we're using a minimal ABI for demonstration purposes
            contract_abi = [
                {
                    "inputs": [
                        {"name": "claimId", "type": "string"},
                        {"name": "policyNumber", "type": "string"},
                        {"name": "claimData", "type": "string"}
                    ],
                    "name": "recordClaim",
                    "outputs": [{"name": "success", "type": "bool"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "claimId", "type": "string"}],
                    "name": "getClaim",
                    "outputs": [
                        {"name": "policyNumber", "type": "string"},
                        {"name": "claimData", "type": "string"},
                        {"name": "timestamp", "type": "uint256"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=contract_abi
            )
            
            logger.info(f"Loaded insurance smart contract at {self.contract_address}")
            
        except Exception as e:
            logger.error(f"Error loading insurance smart contract: {e}")
            self.contract = None
    
    def record_claim(self, claim_id: str, policy_number: str, 
                    claim_data: Dict[str, Any]) -> bool:
        """
        Record a claim on the blockchain.
        
        Args:
            claim_id: Unique identifier for the claim
            policy_number: Insurance policy number
            claim_data: Dictionary of claim information
            
        Returns:
            True if successful, False otherwise
        """
        if not self.web3 or not self.contract or not self.account:
            logger.error("Blockchain connection not properly initialized")
            return False
            
        try:
            # Convert claim data to JSON string
            claim_json = json.dumps(claim_data)
            
            # Prepare transaction
            txn = self.contract.functions.recordClaim(
                claim_id,
                policy_number,
                claim_json
            ).build_transaction({
                'from': self.account.address,
                'gas': 2000000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=self.private_key)
            txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash, timeout=120)
            
            if receipt.status == 1:
                logger.info(f"Successfully recorded claim {claim_id} on blockchain - txn hash: {txn_hash.hex()}")
                return True
            else:
                logger.error(f"Failed to record claim {claim_id} on blockchain - transaction reverted")
                return False
                
        except ContractLogicError as e:
            logger.error(f"Smart contract error recording claim {claim_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error recording claim {claim_id} on blockchain: {e}")
            return False
            
    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a claim from the blockchain.
        
        Args:
            claim_id: Unique identifier for the claim
            
        Returns:
            Dictionary of claim information or None if not found
        """
        if not self.web3 or not self.contract:
            logger.error("Blockchain connection not properly initialized")
            return None
            
        try:
            # Call contract function
            policy_number, claim_json, timestamp = self.contract.functions.getClaim(claim_id).call()
            
            # Parse claim data
            claim_data = json.loads(claim_json)
            
            # Add metadata
            result = {
                'claim_id': claim_id,
                'policy_number': policy_number,
                'timestamp': timestamp,
                'claim_data': claim_data
            }
            
            logger.info(f"Successfully retrieved claim {claim_id} from blockchain")
            return result
            
        except ContractLogicError as e:
            logger.error(f"Smart contract error retrieving claim {claim_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving claim {claim_id} from blockchain: {e}")
            return None 