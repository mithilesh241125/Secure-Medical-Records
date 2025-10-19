"""
Simple Blockchain Implementation for Medical Records Audit Trail
"""

import hashlib
import json
import time
from datetime import datetime

class Block:
    def __init__(self, index, previous_hash, timestamp, data, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.nonce = nonce
        self.hash = self.calculate_hash()
    
    def calculate_hash(self):
        """Calculate the hash of the block"""
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
    
    def create_genesis_block(self):
        """Create the first block in the chain"""
        return Block(0, "0", time.time(), "Genesis Block")
    
    def get_latest_block(self):
        """Get the latest block in the chain"""
        return self.chain[-1]
    
    def add_block(self, data):
        """Add a new block to the chain"""
        latest_block = self.get_latest_block()
        new_block = Block(
            index=latest_block.index + 1,
            previous_hash=latest_block.hash,
            timestamp=time.time(),
            data=data
        )
        self.chain.append(new_block)
        return new_block
    
    def is_chain_valid(self):
        """Verify the integrity of the blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Check if the current block's hash is valid
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Check if the current block points to the correct previous block
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def get_chain_data(self):
        """Get all data from the blockchain"""
        chain_data = []
        for block in self.chain:
            chain_data.append({
                "index": block.index,
                "previous_hash": block.previous_hash,
                "timestamp": block.timestamp,
                "data": block.data,
                "hash": block.hash
            })
        return chain_data

# Global blockchain instance for audit trail
medical_audit_blockchain = Blockchain()

def add_audit_record(action, user_id, table_name, record_id, details=""):
    """Add an audit record to the blockchain"""
    audit_data = {
        "action": action,
        "user_id": user_id,
        "table_name": table_name,
        "record_id": record_id,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    block = medical_audit_blockchain.add_block(audit_data)
    return block

def verify_blockchain_integrity():
    """Verify the integrity of the medical audit blockchain"""
    return medical_audit_blockchain.is_chain_valid()

def get_audit_trail():
    """Get the complete audit trail from the blockchain"""
    return medical_audit_blockchain.get_chain_data()