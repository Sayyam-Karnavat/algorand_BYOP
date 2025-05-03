from arc19 import ARC19
from Extract_paper_data import fetch_paper
from Summarizer_of_data import extract_text_from_file , save_to_pdf , extract_paper_title , summarize_text
import os
import shutil

if __name__ == "__main__":
    

    save_file_path = "research_content.txt"
    pdf_summary_directory = "summaries"

    research_about = "Latest blockchain research"

    fetch_paper(query=research_about , max_results=1, save_file=save_file_path)
    paper_contents = extract_text_from_file(save_file_path)


    if paper_contents:
        # Process and summarize each paper individually
        for i, paper_content in enumerate(paper_contents, 1):
            print(f"\n{'*'*50}")
            print(f"Processing Paper {i}:")
            print(f"{'*'*50}")
            
            # Extract paper title
            paper_title = extract_paper_title(paper_content)
            print(f"Paper Title: {paper_title}")
            
            # Summarize the content of this paper
            summary = summarize_text(paper_content)
            print(summary)
            print(f"{'*'*50}\n")
            
            # Save summary to PDF
            save_to_pdf(summary, paper_title ,output_dir=pdf_summary_directory)
    

    # Get all files inside summaries directory
    research_paper_file_names = [os.path.join(pdf_summary_directory , filename) for filename in os.listdir(pdf_summary_directory)]

    for filename in research_paper_file_names:

        arc_obj = ARC19()
        # CID is basically the IPFS file hash 
        cid = arc_obj.upload_metadata(file_path=filename)

        if cid:
            name = filename
            desc = "Research paper"

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


            print("Transaction :\n https://lora.algokit.io/localnet/transaction/{}".format(transaction_id))

            
            # Remove the directory after pdf's are minted and uploaded to IPFS as ARC19
            
        else:
            print("CID is empty :( ")

    shutil.rmtree(pdf_summary_directory)