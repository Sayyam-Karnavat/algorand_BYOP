from arc19 import ARC19
from Extract_paper_data import fetch_paper
from Summarizer_of_data import extract_text_from_file , save_to_pdf


if __name__ == "__main__":

    save_file_path = "research_content.txt"
    fetch_paper(query="Blockchain" , max_results=3, save_file=save_file_path)
    paper_contents = extract_text_from_file(save_file_path)

    arc_obj = ARC19()


    # CID is basically the IPFS file hash 
    cid = arc_obj.upload_metadata(file_path=save_file_path)

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