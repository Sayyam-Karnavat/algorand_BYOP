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
    

    def create_url_from_cid(self,cid):
        version = self.version_from_cid(cid)
        print("Version:", version)
        codec = self.codec_from_cid(cid)
        print("Codec:", codec)
        hash = self.hash_from_cid(cid)
        print("Hash:", hash)
        url = "template-ipfs://{ipfscid:" + f"{version}:{codec}:reserve:{hash}" + "}"
        valid = re.compile(
            r"template-ipfs://{ipfscid:(?P<version>[01]):(?P<codec>[a-z0-9\-]+):(?P<field>[a-z0-9\-]+):(?P<hash>[a-z0-9\-]+)}"
        )
        assert bool(valid.match(url))
        return url

    def create_metadata(self , asset_name , description , ipfs_hash , image_mimetype = "application/pdf"):


        metadata = {
            "name" : asset_name,
            "description" : description,
            "image" : f"ipfs://{ipfs_hash}",
            "creator" : self.user_address,
            "mimetype" : image_mimetype
        }

        metadata_text = json.dumps(metadata , separators=(",",":"))
        print("Metadata Text :-" , metadata_text)
        
        metadata_hash = hashlib.sha256(metadata_text.encode()).digest()
        print("Metadata Hash :-" , metadata_hash)

        return metadata_hash
    

    def create_asset(self , metadata_hash , reserve_address , url):

        usigned_txn = transaction.AssetCreateTxn(
            sender=self.user_address,
            sp=self.sp,
            total=1, # Because this is an NFT
            decimals=0 ,# Because this is an NFT
            default_frozen=False,
            asset_name="ARC19",
            unit_name="ARC19NFT",
            manager=self.user_address,
            clawback=self.user_address,
            reserve=reserve_address,
            url=url,
            metadata_hash=metadata_hash
        )

        signed_txn = usigned_txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        transaction.wait_for_confirmation(algod_client=self.algod_client , txid=tx_id)

        print("Transaction sent :- {}".format(tx_id))

        return tx_id
    

if __name__ == "__main__":

    arc_obj = ARC19()


    # CID is basically the IPFS file hash 
    cid = arc_obj.upload_metadata(file_path="temp.pdf")

    if cid:
        name = "Blockchain PDF"
        desc = "Research paper blockchain"

        metadata_hash = arc_obj.create_metadata(
            asset_name=name,
            description=desc,
            ipfs_hash=cid
        )

        reserve_address = arc_obj.reserve_address_from_cid(cid=cid)

        url = arc_obj.create_url_from_cid(cid=cid)

        transaction_id = arc_obj.create_asset(
            metadata_hash=metadata_hash,
            reserve_address=reserve_address,
            url=url
        )

    else:
        print("CID is empty :( ")