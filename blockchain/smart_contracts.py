"""
Smart contracts for the InsurTech platform.

This module contains Solidity smart contracts for the InsurTech platform and
utilities for deploying and interacting with them.
"""
import logging
import json
from typing import Dict, Any, Optional, Tuple
import time

from web3 import Web3
from eth_account import Account
from solcx import compile_standard, install_solc

from blockchain.ethereum_client import EthereumClient
from config.config import ETHEREUM_PRIVATE_KEY

# Configure logger
logger = logging.getLogger(__name__)

class SmartContractManager:
    """
    Manage insurance smart contracts.
    
    This class provides utilities for compiling, deploying, and interacting
    with insurance smart contracts on the Ethereum blockchain.
    """
    
    def __init__(self, ethereum_client: Optional[EthereumClient] = None):
        """
        Initialize the smart contract manager.
        
        Args:
            ethereum_client: Optional EthereumClient instance
        """
        self.ethereum_client = ethereum_client or EthereumClient()
        logger.info("Initialized SmartContractManager")
        
    def compile_contract(self, source_path: str) -> Dict[str, Any]:
        """
        Compile a Solidity smart contract.
        
        Args:
            source_path: Path to the Solidity source file
            
        Returns:
            Dictionary of compiled contract data
        """
        try:
            # Ensure solc is installed
            install_solc('0.8.0')
            
            # Read the Solidity source code
            with open(source_path, 'r') as file:
                source_code = file.read()
                
            # Compile the contract
            compiled_sol = compile_standard(
                {
                    "language": "Solidity",
                    "sources": {
                        "Insurance.sol": {
                            "content": source_code
                        }
                    },
                    "settings": {
                        "outputSelection": {
                            "*": {
                                "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                            }
                        }
                    }
                },
                solc_version="0.8.0"
            )
            
            logger.info(f"Successfully compiled contract from {source_path}")
            return compiled_sol
            
        except Exception as e:
            logger.error(f"Error compiling contract: {e}")
            raise
    
    def deploy_contract(self, compiled_contract: Dict[str, Any], 
                       contract_name: str) -> Optional[str]:
        """
        Deploy a compiled smart contract to the blockchain.
        
        Args:
            compiled_contract: Compiled contract data
            contract_name: Name of the contract to deploy
            
        Returns:
            Address of the deployed contract or None if deployment failed
        """
        if not self.ethereum_client.web3:
            logger.error("Web3 connection not initialized")
            return None
            
        try:
            # Get contract bytecode and ABI
            bytecode = compiled_contract["contracts"]["Insurance.sol"][contract_name]["evm"]["bytecode"]["object"]
            abi = json.loads(compiled_contract["contracts"]["Insurance.sol"][contract_name]["metadata"])["output"]["abi"]
            
            # Create contract instance
            contract = self.ethereum_client.web3.eth.contract(abi=abi, bytecode=bytecode)
            
            # Prepare deployment transaction
            txn = contract.constructor().build_transaction({
                'from': self.ethereum_client.account.address,
                'gas': 3000000,
                'gasPrice': self.ethereum_client.web3.eth.gas_price,
                'nonce': self.ethereum_client.web3.eth.get_transaction_count(self.ethereum_client.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.ethereum_client.web3.eth.account.sign_transaction(txn, private_key=ETHEREUM_PRIVATE_KEY)
            txn_hash = self.ethereum_client.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            receipt = self.ethereum_client.web3.eth.wait_for_transaction_receipt(txn_hash, timeout=300)
            
            if receipt.status == 1:
                contract_address = receipt.contractAddress
                logger.info(f"Successfully deployed contract {contract_name} at {contract_address}")
                return contract_address
            else:
                logger.error(f"Failed to deploy contract {contract_name} - transaction reverted")
                return None
                
        except Exception as e:
            logger.error(f"Error deploying contract {contract_name}: {e}")
            return None
            
    def get_insurance_contract_source(self) -> str:
        """
        Get the Solidity source code for the insurance contract.
        
        Returns:
            Solidity source code as a string
        """
        # This would typically be loaded from a file, but for simplicity, 
        # we include it directly here
        return """
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        
        contract InsuranceClaims {
            struct Claim {
                string policyNumber;
                string claimData;
                uint256 timestamp;
                bool exists;
            }
            
            mapping(string => Claim) private claims;
            string[] private claimIds;
            
            event ClaimRecorded(string claimId, string policyNumber, uint256 timestamp);
            event ClaimUpdated(string claimId, string policyNumber, uint256 timestamp);
            
            function recordClaim(string memory claimId, string memory policyNumber, string memory claimData) public returns (bool) {
                require(!claims[claimId].exists, "Claim ID already exists");
                
                claims[claimId] = Claim({
                    policyNumber: policyNumber,
                    claimData: claimData,
                    timestamp: block.timestamp,
                    exists: true
                });
                
                claimIds.push(claimId);
                
                emit ClaimRecorded(claimId, policyNumber, block.timestamp);
                return true;
            }
            
            function updateClaim(string memory claimId, string memory claimData) public returns (bool) {
                require(claims[claimId].exists, "Claim ID does not exist");
                
                claims[claimId].claimData = claimData;
                claims[claimId].timestamp = block.timestamp;
                
                emit ClaimUpdated(claimId, claims[claimId].policyNumber, block.timestamp);
                return true;
            }
            
            function getClaim(string memory claimId) public view returns (string memory, string memory, uint256) {
                require(claims[claimId].exists, "Claim ID does not exist");
                
                return (
                    claims[claimId].policyNumber,
                    claims[claimId].claimData,
                    claims[claimId].timestamp
                );
            }
            
            function getAllClaimIds() public view returns (string[] memory) {
                return claimIds;
            }
        }
        """ 