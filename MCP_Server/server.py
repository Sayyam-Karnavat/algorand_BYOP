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