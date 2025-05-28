import streamlit as st
import time
import os
import shutil
from datetime import datetime
from arc19 import ARC19
from Extract_paper_data import fetch_paper
from Summarizer_of_data import extract_text_from_file, save_to_pdf, extract_paper_title, summarize_text

# Page configuration
st.set_page_config(
    page_title="Research Paper AI Agent",
    page_icon="📚",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .status-pending {
        background-color: #FFF3CD;
        border-left: 4px solid #FFC107;
    }
    .status-running {
        background-color: #D4EDDA;
        border-left: 4px solid #28A745;
    }
    .status-completed {
        background-color: #E2E3E5;
        border-left: 4px solid #6C757D;
    }
    .status-error {
        background-color: #F8D7DA;
        border-left: 4px solid #DC3545;
    }
    .paper-summary {
        background-color: #F8F9FA;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #DEE2E6;
        margin: 10px 0;
    }
    .transaction-link {
        background-color: #D1ECF1;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #17A2B8;
    }
</style>
""", unsafe_allow_html=True)

def display_status(step_name, status, content=""):
    """Display status with appropriate styling"""
    status_class = f"status-{status}"
    
    if status == "pending":
        icon = "⏳"
    elif status == "running":
        icon = "🔄"
    elif status == "completed":
        icon = "✅"
    else:  # error
        icon = "❌"
    
    st.markdown(f"""
    <div class="{status_class} status-box">
        <strong>{icon} {step_name}</strong>
        {f"<br>{content}" if content else ""}
    </div>
    """, unsafe_allow_html=True)

def run_research_agent(research_query, max_results=1):
    """Main function to run the research agent with live updates"""
    
    # Initialize session state for tracking progress
    if 'agent_running' not in st.session_state:
        st.session_state.agent_running = False
    
    # Create containers for different sections
    status_container = st.container()
    progress_container = st.container()
    results_container = st.container()
    
    with status_container:
        st.subheader("🤖 AI Agent Journey")
        
        # Create placeholders for each step
        step1_placeholder = st.empty()
        step2_placeholder = st.empty()
        step3_placeholder = st.empty()
        step4_placeholder = st.empty()
        step5_placeholder = st.empty()
        step6_placeholder = st.empty()
    
    with progress_container:
        progress_bar = st.progress(0)
        progress_text = st.empty()
    
    try:
        # File paths
        save_file_path = "research_content.txt"
        pdf_summary_directory = "summaries"
        
        # Step 1: Fetching papers
        with step1_placeholder:
            display_status("Fetching Research Papers", "running", f"Searching for: '{research_query}'")
        progress_bar.progress(10)
        progress_text.text("🔍 Searching research databases...")
        
        fetch_paper(query=research_query, max_results=max_results, save_file=save_file_path)
        
        with step1_placeholder:
            display_status("Fetching Research Papers", "completed", f"Found and downloaded {max_results} paper(s)")
        
        # Step 2: Extracting content
        with step2_placeholder:
            display_status("Extracting Paper Content", "running")
        progress_bar.progress(25)
        progress_text.text("📄 Extracting text content from papers...")
        
        paper_contents = extract_text_from_file(save_file_path)
        
        if not paper_contents:
            with step2_placeholder:
                display_status("Extracting Paper Content", "error", "No content found in papers")
            return
        
        with step2_placeholder:
            display_status("Extracting Paper Content", "completed", f"Extracted content from {len(paper_contents)} paper(s)")
        
        # Step 3: Processing and summarizing papers
        with step3_placeholder:
            display_status("Analyzing and Summarizing Papers", "running")
        progress_bar.progress(40)
        progress_text.text("🧠 AI is analyzing and summarizing papers...")
        
        with results_container:
            st.subheader("📋 Paper Summaries")
        
        summaries_created = 0
        
        for i, paper_content in enumerate(paper_contents, 1):
            # Extract paper title
            paper_title = extract_paper_title(paper_content)
            
            # Display paper being processed
            with results_container:
                st.markdown(f"**Processing Paper {i}: {paper_title}**")
                
                with st.spinner(f"Summarizing paper {i}..."):
                    # Summarize the content
                    summary = summarize_text(paper_content)
                
                # Display the summary
                st.markdown(f"""
                <div class="paper-summary">
                    <h4>📄 {paper_title}</h4>
                    <p><strong>Summary:</strong></p>
                    <p>{summary}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Save summary to PDF
                save_to_pdf(summary, paper_title, output_dir=pdf_summary_directory)
                summaries_created += 1
        
        with step3_placeholder:
            display_status("Analyzing and Summarizing Papers", "completed", f"Created {summaries_created} summary PDF(s)")
        
        # Step 4: Uploading to IPFS
        with step4_placeholder:
            display_status("Uploading to IPFS", "running")
        progress_bar.progress(60)
        progress_text.text("🌐 Uploading files to IPFS...")
        
        # Get all files in summaries directory
        research_paper_file_names = [
            os.path.join(pdf_summary_directory, filename) 
            for filename in os.listdir(pdf_summary_directory)
        ]
        
        with step4_placeholder:
            display_status("Uploading to IPFS", "completed", f"Uploaded {len(research_paper_file_names)} file(s) to IPFS")
        
        # Step 5: Creating ARC19 assets
        with step5_placeholder:
            display_status("Creating ARC19 Assets", "running")
        progress_bar.progress(80)
        progress_text.text("🔗 Creating blockchain assets...")
        
        transaction_links = []
        
        for filename in research_paper_file_names:
            arc_obj = ARC19()
            
            # Upload metadata and get CID
            cid = arc_obj.upload_metadata(file_path=filename)
            
            if cid:
                name = filename
                desc = "Research paper summary"
                
                # Create metadata
                metadata_hash = arc_obj.create_metadata(
                    asset_name=name,
                    description=desc,
                    ipfs_hash=cid
                )
                
                # Get reserve address and URL
                reserve_address = arc_obj.reserve_address_from_cid(cid=cid)
                url = arc_obj.create_url_from_cid(cid=cid)
                
                # Create asset
                transaction_id = arc_obj.create_asset(
                    metadata_hash=metadata_hash,
                    reserve_address=reserve_address,
                    url=url
                )
                
                transaction_links.append(
                    f"https://lora.algokit.io/localnet/transaction/{transaction_id}"
                )
        
        with step5_placeholder:
            display_status("Creating ARC19 Assets", "completed", f"Created {len(transaction_links)} blockchain asset(s)")
        
        # Step 6: Cleanup and completion
        with step6_placeholder:
            display_status("Cleaning Up", "running")
        progress_bar.progress(95)
        progress_text.text("🧹 Cleaning up temporary files...")
        
        # Remove temporary directory
        if os.path.exists(pdf_summary_directory):
            shutil.rmtree(pdf_summary_directory)
        
        # Remove temporary text file
        if os.path.exists(save_file_path):
            os.remove(save_file_path)
        
        with step6_placeholder:
            display_status("Cleaning Up", "completed", "Temporary files removed")
        
        # Final completion
        progress_bar.progress(100)
        progress_text.text("✅ All tasks completed successfully!")
        
        # Display transaction links
        if transaction_links:
            with results_container:
                st.subheader("🔗 Blockchain Transactions")
                for i, link in enumerate(transaction_links, 1):
                    st.markdown(f"""
                    <div class="transaction-link">
                        <strong>Transaction {i}:</strong><br>
                        <a href="{link}" target="_blank">{link}</a>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.success("🎉 Research paper processing completed successfully!")
        
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        with step1_placeholder:
            display_status("Process", "error", f"Error: {str(e)}")

def main():
    """Main Streamlit application"""
    
    # Header
    st.title("📚 Research Paper AI Agent")
    st.markdown("---")
    
    # Description
    st.markdown("""
    This AI agent will:
    1. 🔍 **Fetch research papers** based on your query
    2. 📄 **Extract and analyze** paper content
    3. 🧠 **Generate summaries** using AI
    4. 📋 **Create PDF summaries**
    5. 🌐 **Upload to IPFS**
    6. 🔗 **Create ARC19 blockchain assets**
    """)
    
    # Input section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        research_query = st.text_input(
            "🔍 Research Topic", 
            value="Latest blockchain research",
            help="Enter the research topic you want to explore"
        )
    
    with col2:
        max_results = st.selectbox(
            "📊 Number of Papers",
            options=[1, 2, 3, 5],
            index=0,
            help="Number of papers to fetch and process"
        )
    
    # Action button
    st.markdown("---")
    
    if st.button("🚀 Start AI Research Agent", type="primary", use_container_width=True):
        if research_query.strip():
            # Add timestamp
            st.info(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Run the agent
            run_research_agent(research_query, max_results)
            
        else:
            st.warning("⚠️ Please enter a research topic!")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<small>Built with ❤️ using Streamlit • Research papers processed with AI • Stored on IPFS & Algorand blockchain</small>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()