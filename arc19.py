import hashlib
import json
import os
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk import mnemonic, account, transaction, encoding
import algokit_utils
import re
import requests
from multiformats_cid import make_cid
import multihash
from dotenv import load_dotenv
import logging

class LoadEnvVars:
    """Loads environment variables for API keys and tokens."""
    def __init__(self):
        load_dotenv()

class ARC19:
    def __init__(self):
        self.algod_address = "http://localhost:4001"
        self.indexer_address = "http://localhost:8980"

        # User account
        try:
            self.user_account = algokit_utils.get_localnet_default_account(client=None)
            self.private_key = self.user_account.private_key
            self.user_address = self.user_account.address
        except Exception as e:
            logging.error(f"Failed to retrieve user account: {str(e)}")
            raise

        # Pinata
        self.pinata_api_key = os.environ['IPFS_API_KEY']
        self.pinata_secret_api_key = os.environ['IPFS_SECRET_KEY']

        # Algod client
        try:
            self.algod_token = os.environ.get('ALGOD_TOKEN', '')
            self.algod_client = AlgodClient(algod_token=self.algod_token, algod_address=self.algod_address)
            self.algod_indexer = IndexerClient(indexer_token=self.algod_token, indexer_address=self.indexer_address)

        except Exception as e:
            logging.error(f"Failed to initialize Algod client: {str(e)}")
            raise

        # Suggested params
        try:
            self.sp = self.algod_client.suggested_params()
        except Exception as e:
            logging.error(f"Failed to retrieve suggested parameters: {str(e)}")
            raise

    def upload_metadata(self, file_path: str) -> str | None:
        """
        Uploads the digital assets to IPFS and returns the IPFS hash.
        :param file_path: Path to the file to be uploaded
        :return: The IPFS hash of the uploaded file or None on failure
        """
        if not os.path.exists(file_path):
            logging.error(f"File does not exist at {file_path}")
            return None

        try:
            with open(file_path, 'rb') as file:
                url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
                headers = {
                    "pinata_api_key": self.pinata_api_key,
                    "pinata_secret_api_key": self.pinata_secret_api_key,
                }
                filename = os.path.basename(file_path)

                files = {"file": (filename, file)}
                response = requests.post(url=url, files=files, headers=headers)
                if response.status_code == 200:
                    ipfs_hash = response.json().get("IpfsHash")
                    return ipfs_hash
                else:
                    logging.error(f"Failed to upload file: {response.status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred while uploading metadata: {str(e)}")

        return None

    def reserve_address_from_cid(self, cid: str) -> str:
        decoded_cid = multihash.decode(make_cid(cid).multihash)
        reserve_address = encoding.encode_address(decoded_cid.digest)
        assert encoding.is_valid_address(reserve_address)
        return reserve_address

    def version_from_cid(self, cid: str) -> int:
        return make_cid(cid).version()

    def get_algod_client(self) -> AlgodClient | None:
        try:
            self.algod_token = os.environ.get('ALGOD_TOKEN', '')
            self.algod_client = AlgodClient(algod_token=self.algod_token, algod_address=self.algod_address)
            return self.algod_client
        except Exception as e:
            logging.error(f"Failed to initialize Algod client: {str(e)}")
            return None

if __name__ == "__main__":
    # Load environment variables here or wherever it's necessary
    load_env_vars = LoadEnvVars()