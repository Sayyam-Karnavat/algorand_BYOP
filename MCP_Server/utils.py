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

if __name__ == "__main__":
    algo_config = AlgorandConfig()

    test_obj = AlgoUtils(algo_config)