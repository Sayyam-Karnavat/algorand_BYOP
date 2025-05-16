
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

# Set up logger
logging.basicConfig(level=logging.INFO)

load_dotenv()

class ARC19:
    def __init__(self):
        self.algod_address = "http://localhost:4001"
        self.indexer_address = "http://localhost:8980"
        self.algod_token = "a" * 64
        self.algod_client = AlgodClient(algod_token=self.algod_token, algod_address=self.algod_address)
        self.algod_indexer = IndexerClient(indexer_token=self.algod_token, indexer_address=self.indexer_address)

        # User account
        try:
            self.user_account = algokit_utils.get_localnet_default_account(client=self.algod_client)
            self.private_key = self.user_account.private_key
            self.user_address = self.user_account.address
        except Exception as e:
            logging.error(f"Failed to retrieve user account: {str(e)}")
            raise

        # Pinata
        self.pinata_key = os.environ['IPFS_API_KEY']
        self.pinata_secret_key = os.environ['IPFS_SECRET_KEY']

        # Suggested params
        try:
            self.sp = self.algod_client.suggested_params()
        except Exception as e:
            logging.error(f"Failed to retrieve suggested parameters: {str(e)}")
            raise

    def upload_metadata(self, file_path):
        """
        Uploads the digital assets to IPFS and returns the IPFS hash.
        :param file_path: Path to the file to be uploaded
        :return: The IPFS hash of the uploaded file or None on failure
        """
        if not os.path.exists(file_path):
            logging.error(f"File does not exist at {file_path}")
            return None

        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        headers = {
            "pinata_api_key": self.pinata_key,
            "pinata_secret_api_key": self.pinata_secret_key,
        }
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as file:
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

    def reserve_address_from_cid(self, cid):
        decoded_cid = multihash.decode(make_cid(cid).multihash)
        reserve_address = encoding.encode_address(decoded_cid.digest)
        assert encoding.is_valid_address(reserve_address)
        return reserve_address

    def version_from_cid(self, cid):
        return make_cid(cid).version()

    def create_token(self):
        try:
            token_id = transaction.calculate_min_fee(
                sender=self.user_address,
                receiver=None,
                amount=0,
                close_remainder_to=None
            )
            usigned_txn = transaction.AnnsTxn(
                self.user_address,
                self.algod_client.suggested_params(),
                spamt=token_id,
                note=""
            ).sign(self.private_key)
            txid = self.algod_client.send_transaction(usigned_txn)
            transaction.wait_for_confirmation(algod_client=self.algod_client, txid=txid)

            logging.info(f"Token creation successful. Transaction ID: {txid}")
        except Exception as e:
            logging.error(f"Failed to create token: {str(e)}")

        return txid

# Example usage
arc19 = ARC19()
arc19.create_token()