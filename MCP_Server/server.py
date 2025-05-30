#!/usr/bin/env python3
"""
Algorand MCP Server - Enhanced with Advanced Blockchain Tools
This MCP server provides comprehensive tools for interacting with the Algorand blockchain.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Algorand SDK imports
from algosdk import account, mnemonic, transaction, logic
from algosdk.v2client import algod, indexer
from algosdk.future.transaction import (
    PaymentTxn, ApplicationCreateTxn, ApplicationCallTxn, 
    AssetCreateTxn, AssetTransferTxn, AssetConfigTxn
)
from algosdk.account import address_from_private_key
from algosdk.encoding import decode_address, encode_address
from algosdk.util import algos_to_microalgos, microalgos_to_algos

# Additional imports
import base64
import hashlib
from dataclasses import dataclass
import aiohttp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("algorand-mcp-server")

@dataclass
class AlgorandConfig:
    """Configuration for Algorand connections"""
    algod_address: str = "https://testnet-api.algonode.cloud"
    algod_token: str = ""
    indexer_address: str = "https://testnet-idx.algonode.cloud"
    indexer_token: str = ""
    network: str = "testnet"  # testnet, mainnet, betanet

class AlgorandMCPServer:
    """Enhanced Algorand MCP Server with comprehensive blockchain tools"""
    
    def __init__(self, config: AlgorandConfig = None):
        self.config = config or AlgorandConfig()
        self.server = Server("algorand-enhanced")
        self.algod_client = None
        self.indexer_client = None
        self._setup_clients()
        self._register_tools()
        self._register_resources()
    
    def _setup_clients(self):
        """Initialize Algorand clients"""
        try:
            self.algod_client = algod.AlgodClient(
                self.config.algod_token,
                self.config.algod_address,
                headers={"User-Agent": "algorand-mcp-server"}
            )
            
            self.indexer_client = indexer.IndexerClient(
                self.config.indexer_token,
                self.config.indexer_address,
                headers={"User-Agent": "algorand-mcp-server"}
            )
            
            # Test connections
            self.algod_client.status()
            logger.info(f"Connected to Algorand {self.config.network}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Algorand: {e}")
            raise
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        # ======================= ACCOUNT TOOLS =======================
        
        @self.server.call_tool()
        async def create_account(arguments: dict) -> List[TextContent]:
            """Create a new Algorand account with private key and mnemonic"""
            try:
                private_key, address = account.generate_account()
                account_mnemonic = mnemonic.from_private_key(private_key)
                
                result = {
                    "address": address,
                    "private_key": private_key,
                    "mnemonic": account_mnemonic,
                    "network": self.config.network,
                    "created_at": datetime.now().isoformat()
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error creating account: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def get_account_info(arguments: dict) -> List[TextContent]:
            """Get detailed account information including balance and assets"""
            try:
                address = arguments.get("address")
                if not address:
                    raise ValueError("Address is required")
                
                # Get account info from algod
                account_info = self.algod_client.account_info(address)
                
                # Get additional info from indexer
                try:
                    indexer_info = self.indexer_client.account_info(address)
                    transactions_count = len(indexer_info.get("account", {}).get("created-apps", []))
                except:
                    transactions_count = 0
                
                result = {
                    "address": address,
                    "balance_algo": microalgos_to_algos(account_info["amount"]),
                    "balance_microalgo": account_info["amount"],
                    "minimum_balance": microalgos_to_algos(account_info["min-balance"]),
                    "round": account_info["round"],
                    "status": account_info["status"],
                    "assets": account_info.get("assets", []),
                    "created_apps": account_info.get("created-apps", []),
                    "apps_local_state": account_info.get("apps-local-state", []),
                    "participation": account_info.get("participation", {}),
                    "transactions_count": transactions_count,
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting account info: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def restore_account_from_mnemonic(arguments: dict) -> List[TextContent]:
            """Restore account from mnemonic phrase"""
            try:
                mnemonic_phrase = arguments.get("mnemonic")
                if not mnemonic_phrase:
                    raise ValueError("Mnemonic phrase is required")
                
                private_key = mnemonic.to_private_key(mnemonic_phrase)
                address = address_from_private_key(private_key)
                
                result = {
                    "address": address,
                    "private_key": private_key,
                    "mnemonic": mnemonic_phrase,
                    "network": self.config.network,
                    "restored_at": datetime.now().isoformat()
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error restoring account: {str(e)}"
                )]
        
        # ======================= TRANSACTION TOOLS =======================
        
        @self.server.call_tool()
        async def send_payment(arguments: dict) -> List[TextContent]:
            """Send ALGO payment transaction"""
            try:
                sender_private_key = arguments.get("sender_private_key")
                receiver_address = arguments.get("receiver_address")
                amount_algo = float(arguments.get("amount_algo", 0))
                note = arguments.get("note", "")
                
                if not all([sender_private_key, receiver_address, amount_algo]):
                    raise ValueError("sender_private_key, receiver_address, and amount_algo are required")
                
                sender_address = address_from_private_key(sender_private_key)
                amount_microalgo = algos_to_microalgos(amount_algo)
                
                # Get suggested parameters
                params = self.algod_client.suggested_params()
                
                # Create transaction
                txn = PaymentTxn(
                    sender=sender_address,
                    sp=params,
                    receiver=receiver_address,
                    amt=amount_microalgo,
                    note=note.encode() if note else None
                )
                
                # Sign transaction
                signed_txn = txn.sign(sender_private_key)
                
                # Send transaction
                tx_id = self.algod_client.send_transaction(signed_txn)
                
                # Wait for confirmation
                confirmed_txn = transaction.wait_for_confirmation(self.algod_client, tx_id, 4)
                
                result = {
                    "transaction_id": tx_id,
                    "sender": sender_address,
                    "receiver": receiver_address,
                    "amount_algo": amount_algo,
                    "amount_microalgo": amount_microalgo,
                    "confirmed_round": confirmed_txn["confirmed-round"],
                    "fee": confirmed_txn["txn"]["txn"]["fee"],
                    "note": note,
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error sending payment: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def get_transaction(arguments: dict) -> List[TextContent]:
            """Get detailed transaction information"""
            try:
                tx_id = arguments.get("transaction_id")
                if not tx_id:
                    raise ValueError("transaction_id is required")
                
                # Get transaction from indexer
                txn_info = self.indexer_client.transaction(tx_id)
                
                result = {
                    "transaction_id": tx_id,
                    "transaction_info": txn_info,
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting transaction: {str(e)}"
                )]
        
        # ======================= ASSET TOOLS =======================
        
        @self.server.call_tool()
        async def create_asset(arguments: dict) -> List[TextContent]:
            """Create a new Algorand Standard Asset (ASA)"""
            try:
                creator_private_key = arguments.get("creator_private_key")
                asset_name = arguments.get("asset_name")
                unit_name = arguments.get("unit_name")
                total_issuance = int(arguments.get("total_issuance", 1))
                decimals = int(arguments.get("decimals", 0))
                default_frozen = arguments.get("default_frozen", False)
                url = arguments.get("url", "")
                metadata_hash = arguments.get("metadata_hash")
                
                if not all([creator_private_key, asset_name, unit_name]):
                    raise ValueError("creator_private_key, asset_name, and unit_name are required")
                
                creator_address = address_from_private_key(creator_private_key)
                
                # Get suggested parameters
                params = self.algod_client.suggested_params()
                
                # Create asset creation transaction
                txn = AssetCreateTxn(
                    sender=creator_address,
                    sp=params,
                    total=total_issuance,
                    default_frozen=default_frozen,
                    unit_name=unit_name,
                    asset_name=asset_name,
                    manager=creator_address,
                    reserve=creator_address,
                    freeze=creator_address,
                    clawback=creator_address,
                    url=url,
                    metadata_hash=metadata_hash.encode() if metadata_hash else None,
                    decimals=decimals
                )
                
                # Sign and send transaction
                signed_txn = txn.sign(creator_private_key)
                tx_id = self.algod_client.send_transaction(signed_txn)
                
                # Wait for confirmation
                confirmed_txn = transaction.wait_for_confirmation(self.algod_client, tx_id, 4)
                
                # Get asset ID
                asset_id = confirmed_txn["asset-index"]
                
                result = {
                    "transaction_id": tx_id,
                    "asset_id": asset_id,
                    "creator": creator_address,
                    "asset_name": asset_name,
                    "unit_name": unit_name,
                    "total_issuance": total_issuance,
                    "decimals": decimals,
                    "confirmed_round": confirmed_txn["confirmed-round"],
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error creating asset: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def transfer_asset(arguments: dict) -> List[TextContent]:
            """Transfer an Algorand Standard Asset (ASA)"""
            try:
                sender_private_key = arguments.get("sender_private_key")
                receiver_address = arguments.get("receiver_address")
                asset_id = int(arguments.get("asset_id"))
                amount = int(arguments.get("amount"))
                
                if not all([sender_private_key, receiver_address, asset_id, amount]):
                    raise ValueError("All parameters are required")
                
                sender_address = address_from_private_key(sender_private_key)
                
                # Get suggested parameters
                params = self.algod_client.suggested_params()
                
                # Create asset transfer transaction
                txn = AssetTransferTxn(
                    sender=sender_address,
                    sp=params,
                    receiver=receiver_address,
                    amt=amount,
                    index=asset_id
                )
                
                # Sign and send transaction
                signed_txn = txn.sign(sender_private_key)
                tx_id = self.algod_client.send_transaction(signed_txn)
                
                # Wait for confirmation
                confirmed_txn = transaction.wait_for_confirmation(self.algod_client, tx_id, 4)
                
                result = {
                    "transaction_id": tx_id,
                    "sender": sender_address,
                    "receiver": receiver_address,
                    "asset_id": asset_id,
                    "amount": amount,
                    "confirmed_round": confirmed_txn["confirmed-round"],
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error transferring asset: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def get_asset_info(arguments: dict) -> List[TextContent]:
            """Get detailed information about an asset"""
            try:
                asset_id = int(arguments.get("asset_id"))
                
                # Get asset info
                asset_info = self.algod_client.asset_info(asset_id)
                
                result = {
                    "asset_id": asset_id,
                    "asset_info": asset_info,
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting asset info: {str(e)}"
                )]
        
        # ======================= APPLICATION TOOLS =======================
        
        @self.server.call_tool()
        async def create_application(arguments: dict) -> List[TextContent]:
            """Create a new smart contract application"""
            try:
                creator_private_key = arguments.get("creator_private_key")
                approval_program = arguments.get("approval_program")  # TEAL code
                clear_program = arguments.get("clear_program")  # TEAL code
                global_schema = arguments.get("global_schema", {"num_ints": 0, "num_byte_slices": 0})
                local_schema = arguments.get("local_schema", {"num_ints": 0, "num_byte_slices": 0})
                app_args = arguments.get("app_args", [])
                
                if not all([creator_private_key, approval_program, clear_program]):
                    raise ValueError("creator_private_key, approval_program, and clear_program are required")
                
                creator_address = address_from_private_key(creator_private_key)
                
                # Compile programs
                approval_result = self.algod_client.compile(approval_program)
                approval_binary = base64.b64decode(approval_result["result"])
                
                clear_result = self.algod_client.compile(clear_program)
                clear_binary = base64.b64decode(clear_result["result"])
                
                # Get suggested parameters
                params = self.algod_client.suggested_params()
                
                # Create application
                txn = ApplicationCreateTxn(
                    sender=creator_address,
                    sp=params,
                    on_complete=0,  # NoOp
                    approval_program=approval_binary,
                    clear_program=clear_binary,
                    global_schema=transaction.StateSchema(
                        global_schema["num_ints"], 
                        global_schema["num_byte_slices"]
                    ),
                    local_schema=transaction.StateSchema(
                        local_schema["num_ints"], 
                        local_schema["num_byte_slices"]
                    ),
                    app_args=app_args
                )
                
                # Sign and send transaction
                signed_txn = txn.sign(creator_private_key)
                tx_id = self.algod_client.send_transaction(signed_txn)
                
                # Wait for confirmation
                confirmed_txn = transaction.wait_for_confirmation(self.algod_client, tx_id, 4)
                
                # Get application ID
                app_id = confirmed_txn["application-index"]
                
                result = {
                    "transaction_id": tx_id,
                    "application_id": app_id,
                    "creator": creator_address,
                    "confirmed_round": confirmed_txn["confirmed-round"],
                    "approval_program_hash": approval_result["hash"],
                    "clear_program_hash": clear_result["hash"],
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error creating application: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def call_application(arguments: dict) -> List[TextContent]:
            """Call a smart contract application"""
            try:
                caller_private_key = arguments.get("caller_private_key")
                app_id = int(arguments.get("app_id"))
                app_args = arguments.get("app_args", [])
                accounts = arguments.get("accounts", [])
                foreign_apps = arguments.get("foreign_apps", [])
                foreign_assets = arguments.get("foreign_assets", [])
                
                if not all([caller_private_key, app_id]):
                    raise ValueError("caller_private_key and app_id are required")
                
                caller_address = address_from_private_key(caller_private_key)
                
                # Get suggested parameters
                params = self.algod_client.suggested_params()
                
                # Create application call transaction
                txn = ApplicationCallTxn(
                    sender=caller_address,
                    sp=params,
                    index=app_id,
                    on_complete=0,  # NoOp
                    app_args=app_args,
                    accounts=accounts,
                    foreign_apps=foreign_apps,
                    foreign_assets=foreign_assets
                )
                
                # Sign and send transaction
                signed_txn = txn.sign(caller_private_key)
                tx_id = self.algod_client.send_transaction(signed_txn)
                
                # Wait for confirmation
                confirmed_txn = transaction.wait_for_confirmation(self.algod_client, tx_id, 4)
                
                result = {
                    "transaction_id": tx_id,
                    "application_id": app_id,
                    "caller": caller_address,
                    "confirmed_round": confirmed_txn["confirmed-round"],
                    "global_state_delta": confirmed_txn.get("global-state-delta", []),
                    "local_state_delta": confirmed_txn.get("local-state-delta", []),
                    "logs": confirmed_txn.get("logs", []),
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error calling application: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def get_application_info(arguments: dict) -> List[TextContent]:
            """Get detailed information about an application"""
            try:
                app_id = int(arguments.get("app_id"))
                
                # Get application info
                app_info = self.algod_client.application_info(app_id)
                
                result = {
                    "application_id": app_id,
                    "application_info": app_info,
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting application info: {str(e)}"
                )]
        
        # ======================= BLOCKCHAIN INFO TOOLS =======================
        
        @self.server.call_tool()
        async def get_blockchain_status(arguments: dict) -> List[TextContent]:
            """Get current blockchain status and network information"""
            try:
                status = self.algod_client.status()
                
                result = {
                    "network": self.config.network,
                    "last_round": status["last-round"],
                    "last_consensus_version": status["last-consensus-version"],
                    "next_consensus_version": status.get("next-consensus-version"),
                    "next_consensus_version_round": status.get("next-consensus-version-round"),
                    "next_consensus_version_supported": status.get("next-consensus-version-supported"),
                    "time_since_last_round": status["time-since-last-round"],
                    "catchup_time": status["catchup-time"],
                    "stopped_at_unsupported_round": status.get("stopped-at-unsupported-round", False)
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting blockchain status: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def get_block_info(arguments: dict) -> List[TextContent]:
            """Get information about a specific block"""
            try:
                round_number = arguments.get("round")
                if round_number is None:
                    # Get latest block
                    status = self.algod_client.status()
                    round_number = status["last-round"]
                else:
                    round_number = int(round_number)
                
                block_info = self.algod_client.block_info(round_number)
                
                result = {
                    "round": round_number,
                    "block_info": block_info,
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting block info: {str(e)}"
                )]
        
        # ======================= ADVANCED QUERY TOOLS =======================
        
        @self.server.call_tool()
        async def search_transactions(arguments: dict) -> List[TextContent]:
            """Search for transactions with various filters"""
            try:
                address = arguments.get("address")
                asset_id = arguments.get("asset_id")
                min_amount = arguments.get("min_amount")
                max_amount = arguments.get("max_amount")
                before_time = arguments.get("before_time")
                after_time = arguments.get("after_time")
                limit = int(arguments.get("limit", 10))
                
                # Build search parameters
                search_params = {"limit": limit}
                
                if address:
                    search_params["address"] = address
                if asset_id:
                    search_params["asset-id"] = int(asset_id)
                if min_amount:
                    search_params["currency-greater-than"] = int(min_amount)
                if max_amount:
                    search_params["currency-less-than"] = int(max_amount)
                if before_time:
                    search_params["before-time"] = before_time
                if after_time:
                    search_params["after-time"] = after_time
                
                # Search transactions
                response = self.indexer_client.search_transactions(**search_params)
                
                result = {
                    "search_params": search_params,
                    "transactions": response["transactions"],
                    "next_token": response.get("next-token"),
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error searching transactions: {str(e)}"
                )]
        
        @self.server.call_tool()
        async def get_account_transactions(arguments: dict) -> List[TextContent]:
            """Get transaction history for a specific account"""
            try:
                address = arguments.get("address")
                limit = int(arguments.get("limit", 50))
                
                if not address:
                    raise ValueError("address is required")
                
                # Get account transactions
                response = self.indexer_client.search_transactions(
                    address=address,
                    limit=limit
                )
                
                # Process transactions
                transactions = []
                for txn in response["transactions"]:
                    tx_type = txn.get("tx-type", "unknown")
                    processed_txn = {
                        "id": txn["id"],
                        "type": tx_type,
                        "round": txn["confirmed-round"],
                        "timestamp": datetime.fromtimestamp(txn["round-time"]).isoformat(),
                        "fee": txn["fee"],
                        "sender": txn["sender"]
                    }
                    
                    # Add type-specific information
                    if tx_type == "pay":
                        processed_txn.update({
                            "receiver": txn["payment-transaction"]["receiver"],
                            "amount": txn["payment-transaction"]["amount"],
                            "amount_algo": microalgos_to_algos(txn["payment-transaction"]["amount"])
                        })
                    elif tx_type == "axfer":
                        processed_txn.update({
                            "asset_id": txn["asset-transfer-transaction"]["asset-id"],
                            "receiver": txn["asset-transfer-transaction"]["receiver"],
                            "amount": txn["asset-transfer-transaction"]["amount"]
                        })
                    elif tx_type == "appl":
                        processed_txn.update({
                            "application_id": txn["application-transaction"]["application-id"]
                        })
                    
                    transactions.append(processed_txn)
                
                result = {
                    "address": address,
                    "transaction_count": len(transactions),
                    "transactions": transactions,
                    "network": self.config.network
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting account transactions: {str(e)}"
                )]
    
    def _register_resources(self):
        """Register MCP resources"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="algorand://network/status",
                    name="Network Status",
                    description="Current Algorand network status and information",
                    mimeType="application/json"
                ),
                Resource(
                    uri="algorand://tools/documentation",
                    name="Tool Documentation",
                    description="Documentation for all available Algorand tools",
                    mimeType="text/markdown"
                )
            ]