import os
import sys
import glob
import httpx
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/api"

async def upload_file(client: httpx.AsyncClient, file_path: str):
    path = Path(file_path)
    logger.info(f"Uploading {path.name}...")
    
    with open(file_path, "rb") as f:
        files = {"file": (path.name, f, "application/pdf")}
        try:
            response = await client.post(f"{API_URL}/upload", files=files, timeout=60.0)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully uploaded {path.name} - Paper ID: {data['paper_id']}")
                return data['paper_id']
            else:
                logger.error(f"Failed to upload {path.name}. Status: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error uploading {path.name}: {e}")
            return None

async def wait_for_completion(client: httpx.AsyncClient, paper_ids: list):
    logger.info("Waiting for ingestion to complete for all papers...")
    
    pending = set(paper_ids)
    
    while pending:
        await asyncio.sleep(10) # Check every 10 seconds
        
        for pid in list(pending):
            try:
                response = await client.get(f"{API_URL}/paper/{pid}/status", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress_pct", 0)
                    
                    if status == "complete":
                        logger.info(f"Paper {pid} ingestion COMPLETE.")
                        pending.remove(pid)
                    elif status == "failed":
                        logger.error(f"Paper {pid} ingestion FAILED.")
                        pending.remove(pid)
                    else:
                        logger.info(f"Paper {pid} status: {status} ({progress:.1f}%)")
            except Exception as e:
                logger.debug(f"Error checking status for {pid}: {e}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_ingest.py <directory_with_pdfs>")
        sys.exit(1)
        
    pdf_dir = sys.argv[1]
    if not os.path.isdir(pdf_dir):
        print(f"Error: Directory '{pdf_dir}' not found.")
        sys.exit(1)
        
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in '{pdf_dir}'.")
        sys.exit(0)
        
    logger.info(f"Found {len(pdf_files)} PDF files in {pdf_dir}.")
    
    # Check if API is up
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/health")
            if resp.status_code != 200:
                logger.warning("Backend API health check failed. Is the server running?")
    except Exception:
        logger.error("Could not connect to Backend API. Please ensure it is running on port 8000.")
        sys.exit(1)

    paper_ids = []
    async with httpx.AsyncClient() as client:
        # Upload all sequentially to not overwhelm the server initially
        for pdf_file in pdf_files:
            pid = await upload_file(client, pdf_file)
            if pid:
                paper_ids.append(pid)
            
            # Brief pause between uploads
            await asyncio.sleep(1)
            
        if paper_ids:
            await wait_for_completion(client, paper_ids)
            
    logger.info("Batch ingestion process finished.")

if __name__ == "__main__":
    asyncio.run(main())
