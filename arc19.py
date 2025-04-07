import hashlib
import base64
import json
import os
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk import mnemonic,account,transaction,encoding
import algokit_utils
import re
import requests
from multiformats_cid import make_cid
import multihash
from dotenv import load_dotenv


load_dotenv()


class ARC19:
    def __init__(self):

        # Initialize client
        self.algod_address = "http://localhost:4001"
        self.indexer_address = "http://localhost:8980"
        self.algod_token = "a" * 64
        self.algod_client = AlgodClient(algod_token=self.algod_token , algod_address=self.algod_address)
        self.algod_indexer = IndexerClient(indexer_token=self.algod_token , indexer_address=self.indexer_address)


        # User account
        self.user_account = algokit_utils.get_localnet_default_account(client=self.algod_client)
        self.private_key = self.user_account.private_key
        self.user_address = self.user_account.address

        # Pinata
        self.pinata_key = os.environ['IPFS_API_KEY']
        self.pinata_secret_key = os.environ['IPFS_SECRET_KEY']  

        # Suggested params
        self.sp = self.algod_client.suggested_params()

        print("Private Key:", self.private_key, "\nAddress:", self.user_address)

    def upload_metadata(self , file_path):
        '''
        This will upload the digital assets to IPFS
        Returns the IPFS hash which will be used to convert to reserve address
        '''
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        headers = {
            "pinata_api_key": self.pinata_key,
            "pinata_secret_api_key": self.pinata_secret_key,
        }
        filename = os.path.basename(file_path)
        with open(file_path , 'rb') as file:

            files = {"file" :(filename , file)}
            response = requests.post(url=url , files=files , headers=headers)
            if response.status_code == 200:
                ipfs_hash = response.json().get("IpfsHash")
                print("IPFS Hash:", ipfs_hash)
                return ipfs_hash
            
            else:
                print("Failed to upload file :-" , response.status_code , response.text)
                return None
            
    def reserve_address_from_cid(self,cid):
        decoded_cid = multihash.decode(make_cid(cid).multihash)
        reserve_address = encoding.encode_address(decoded_cid.digest)
        assert encoding.is_valid_address(reserve_address)
        return reserve_address
        
    def version_from_cid(self,cid):
        return make_cid(cid).version

    def codec_from_cid(self,cid):
        return make_cid(cid).codec

    def hash_from_cid(self,cid):
        return multihash.decode(make_cid(cid).multihash).name