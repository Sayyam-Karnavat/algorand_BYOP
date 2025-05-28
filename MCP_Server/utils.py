import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import hashlib

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    LoggingLevel, CallToolResult, ListResourcesResult, ListToolsResult,
    ReadResourceResult, GetPromptResult, ListPromptsResult, Prompt,
    PromptArgument, PromptMessage, Role
)
import mcp.types as types
from pydantic import AnyUrl
from algosdk import algod, indexer, kmd, mnemonic, account, encoding, transaction, constants
from algosdk.v2client import algod as algod_client, indexer as indexer_client
from algosdk.transaction import PaymentTxn, AssetTransferTxn, AssetConfigTxn, ApplicationCallTxn
from algosdk.atomic_transaction_composer import AtomicTransactionComposer, TransactionWithSigner
from algosdk.abi import Contract, Method
from algosdk.account import address_from_private_key
from algosdk.encoding import encode_address, decode_address

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("algorand-mcp")

@dataclass 
class AlgorandConfig:
    """Configuration for Algorand network connections"""
    algod_address: str = "https://testnet-api.algonode.cloud"
    algod_token: str = ""
    indexer_address: str = "https://testnet-idx.algonode.cloud"  
    indexer_token: str = ""
    network: str = "testnet"  # testnet, mainnet, betanet


class AlgoUtils:
    def __init__(self, config: AlgorandConfig):
        self.config = config
        self.server = Server("algorand-mcp")
        self.algod_client = None
        self.indexer_client = None
        self._setup_clients()
        self._register_handlers()


    def _setup_clients(self):
        """Initialize Algorand clients"""
        try:
            self.algod_client = algod_client.AlgodClient(
                self.config.algod_token, 
                self.config.algod_address
            )
            self.indexer_client = indexer_client.IndexerClient(
                self.config.indexer_token,
                self.config.indexer_address  
            )
            logger.info(f"Connected to Algorand {self.config.network}")
        except Exception as e:
            logger.error(f"Failed to initialize Algorand clients: {e}")
            raise

    def _register_handlers(self):
        """Register all MCP handlers"""
        
        # Core handlers
        @self.server.list_resources()
        async def handle_list_resources() -> ListResourcesResult:
            """List all available Algorand resources"""
            return ListResourcesResult(
                resources=[
                    types.Resource(
                        uri=AnyUrl("algorand://network/status"),
                        name="Network Status",
                        description="Current Algorand network status and health",
                        mimeType="application/json",
                    ),
                    types.Resource(
                        uri=AnyUrl("algorand://network/params"), 
                        name="Network Parameters",
                        description="Algorand network consensus parameters",
                        mimeType="application/json",
                    ),
                    types.Resource(
                        uri=AnyUrl("algorand://blocks/latest"),
                        name="Latest Block",
                        description="Information about the latest block",
                        mimeType="application/json",
                    ),
                    types.Resource(
                        uri=AnyUrl("algorand://assets/popular"),
                        name="Popular Assets", 
                        description="List of popular ASAs on Algorand",
                        mimeType="application/json",
                    ),
                    types.Resource(
                        uri=AnyUrl("algorand://apps/popular"),
                        name="Popular Applications",
                        description="List of popular dApps on Algorand", 
                        mimeType="application/json",
                    ),
                    types.Resource(
                        uri=AnyUrl("algorand://stats/daily"),
                        name="Daily Statistics",
                        description="Daily network statistics and metrics",
                        mimeType="application/json",
                    ),
                ]
            )
        
        @self.server.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> ReadResourceResult:
            """Read resource content"""
            try:
                if str(uri) == "algorand://network/status":
                    status = await self._get_network_status()
                    return ReadResourceResult(
                        contents=[
                            TextContent(
                                type="text",
                                text=json.dumps(status, indent=2)
                            )
                        ]
                    )
                elif str(uri) == "algorand://network/params":
                    params = await self._get_network_params()
                    return ReadResourceResult(
                        contents=[
                            TextContent(
                                type="text", 
                                text=json.dumps(params, indent=2)
                            )
                        ]
                    )
                elif str(uri) == "algorand://blocks/latest":
                    block = await self._get_latest_block()
                    return ReadResourceResult(
                        contents=[
                            TextContent(
                                type="text",
                                text=json.dumps(block, indent=2)
                            )
                        ]
                    )
                elif str(uri) == "algorand://assets/popular":
                    assets = await self._get_popular_assets()
                    return ReadResourceResult(
                        contents=[
                            TextContent(
                                type="text",
                                text=json.dumps(assets, indent=2)
                            )
                        ]
                    )
                elif str(uri) == "algorand://apps/popular":
                    apps = await self._get_popular_apps()
                    return ReadResourceResult(
                        contents=[
                            TextContent(
                                type="text",
                                text=json.dumps(apps, indent=2)
                            )
                        ]
                    )
                elif str(uri) == "algorand://stats/daily":
                    stats = await self._get_daily_stats()
                    return ReadResourceResult(
                        contents=[
                            TextContent(
                                type="text",
                                text=json.dumps(stats, indent=2)
                            )
                        ]
                    )
                else:
                    raise ValueError(f"Unknown resource: {uri}")
                    
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                return ReadResourceResult(
                    contents=[
                        TextContent(
                            type="text", 
                            text=f"Error: {str(e)}"
                        )
                    ]
                )
            
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List all available tools"""
            tools = [
                # Account Management Tools
                Tool(
                    name="create_account",
                    description="Generate a new Algorand account with mnemonic",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                ),
                Tool(
                    name="account_info",
                    description="Get detailed account information",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "address": {"type": "string", "description": "Account address"}
                        },
                        "required": ["address"]
                    },
                ),
                Tool(
                    name="account_balance",
                    description="Get account ALGO balance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Account address"}
                        },
                        "required": ["address"]
                    },
                ),
                Tool(
                    name="account_assets",
                    description="List all assets held by an account", 
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Account address"}
                        },
                        "required": ["address"]
                    },
                ),
                Tool(
                    name="account_applications",
                    description="List applications created or opted into by account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Account address"}
                        },
                        "required": ["address"]
                    },
                ),
                Tool(
                    name="account_transactions",
                    description="Get account transaction history",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Account address"},
                            "limit": {"type": "integer", "description": "Number of transactions", "default": 50},
                            "next_token": {"type": "string", "description": "Pagination token", "default": ""}
                        },
                        "required": ["address"]
                    },
                ),
                # Transaction Tools
                Tool(
                    name="create_payment_txn",
                    description="Create a payment transaction",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sender": {"type": "string", "description": "Sender address"},
                            "receiver": {"type": "string", "description": "Receiver address"}, 
                            "amount": {"type": "integer", "description": "Amount in microAlgos"},
                            "note": {"type": "string", "description": "Transaction note", "default": ""}
                        },
                        "required": ["sender", "receiver", "amount"]
                    },
                ),
                Tool(
                    name="send_payment",
                    description="Send ALGO payment (requires private key)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "private_key": {"type": "string", "description": "Sender private key"},
                            "receiver": {"type": "string", "description": "Receiver address"},
                            "amount": {"type": "integer", "description": "Amount in microAlgos"},
                            "note": {"type": "string", "description": "Transaction note", "default": ""}
                        },
                        "required": ["private_key", "receiver", "amount"]
                    },
                ),
                Tool(
                    name="transaction_info",
                    description="Get transaction details by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "txid": {"type": "string", "description": "Transaction ID"}
                        },
                        "required": ["txid"]
                    },
                ),
                Tool(
                    name="pending_transactions",
                    description="Get pending transactions from pool",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max": {"type": "integer", "description": "Maximum transactions", "default": 10}
                        },
                        "required": []
                    },
                ),

                # Asset Tools
                Tool(
                    name="create_asset",
                    description="Create a new ASA (Algorand Standard Asset)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "private_key": {"type": "string", "description": "Creator private key"},
                            "asset_name": {"type": "string", "description": "Asset name"},
                            "unit_name": {"type": "string", "description": "Asset unit name"},
                            "total": {"type": "integer", "description": "Total supply"},
                            "decimals": {"type": "integer", "description": "Decimal places", "default": 0},
                            "url": {"type": "string", "description": "Asset URL", "default": ""},
                            "metadata_hash": {"type": "string", "description": "Metadata hash", "default": ""}
                        },
                        "required": ["private_key", "asset_name", "unit_name", "total"]
                    },
                ),
                Tool(
                    name="asset_info",
                    description="Get asset information by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "asset_id": {"type": "integer", "description": "Asset ID"}
                        },
                        "required": ["asset_id"]
                    },
                ),
                Tool(
                    name="asset_balances",
                    description="Get all holders of an asset",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "asset_id": {"type": "integer", "description": "Asset ID"},
                            "limit": {"type": "integer", "description": "Number of results", "default": 100}
                        },
                        "required": ["asset_id"]
                    },
                ),
                Tool(
                    name="opt_in_asset",
                    description="Opt into an asset",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "private_key": {"type": "string", "description": "Account private key"},
                            "asset_id": {"type": "integer", "description": "Asset ID"}
                        },
                        "required": ["private_key", "asset_id"]
                    },
                ),
                Tool(
                    name="transfer_asset",
                    description="Transfer ASA tokens",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "private_key": {"type": "string", "description": "Sender private key"},
                            "asset_id": {"type": "integer", "description": "Asset ID"},
                            "receiver": {"type": "string", "description": "Receiver address"},
                            "amount": {"type": "integer", "description": "Amount to transfer"}
                        },
                        "required": ["private_key", "asset_id", "receiver", "amount"]
                    },
                ),
                Tool(
                    name="application_state",
                    description="Get application global state",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "app_id": {"type": "integer", "description": "Application ID"}
                        },
                        "required": ["app_id"]
                    },
                ),
                Tool(
                    name="account_app_state",
                    description="Get account's local state for an application",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Account address"},
                            "app_id": {"type": "integer", "description": "Application ID"}
                        },
                        "required": ["address", "app_id"]
                    },
                ),

            Tool(
                    name="validate_address",
                    description="Validate an Algorand address",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Address to validate"}
                        },
                        "required": ["address"]
                    },
                ),
                Tool(
                    name="encode_address",
                    description="Encode public key to address",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "public_key": {"type": "string", "description": "Base64 encoded public key"}
                        },
                        "required": ["public_key"]
                    },
                ),
                Tool(
                    name="decode_address", 
                    description="Decode address to public key",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Algorand address"}
                        },
                        "required": ["address"]
                    },
                ),
                Tool(
                    name="mnemonic_to_private_key",
                    description="Convert mnemonic to private key",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mnemonic": {"type": "string", "description": "25-word mnemonic"}
                        },
                        "required": ["mnemonic"]
                    },
                ),
                Tool(
                    name="private_key_to_address",
                    description="Get address from private key",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "private_key": {"type": "string", "description": "Private key"}
                        },
                        "required": ["private_key"]
                    },
                ),

                # Search Tools
                Tool(
                    name="search_transactions",
                    description="Search transactions with filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "asset_id": {"type": "integer", "description": "Asset ID filter"},
                            "address": {"type": "string", "description": "Address filter"},
                            "tx_type": {"type": "string", "description": "Transaction type filter"},
                            "limit": {"type": "integer", "description": "Number of results", "default": 50}
                        },
                        "required": []
                    },
                ),
                Tool(
                    name="search_assets",
                    description="Search assets by name or creator",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Asset name filter"},
                            "creator": {"type": "string", "description": "Creator address filter"},
                            "limit": {"type": "integer", "description": "Number of results", "default": 50}
                        },
                        "required": []
                    },
                ),
                Tool(
                    name="search_applications",
                    description="Search applications by creator",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "creator": {"type": "string", "description": "Creator address filter"},
                            "limit": {"type": "integer", "description": "Number of results", "default": 50}
                        },
                        "required": []
                    },
                ),
            ]

if __name__ == "__main__":
    algo_config = AlgorandConfig()

    test_obj = AlgoUtils(algo_config)