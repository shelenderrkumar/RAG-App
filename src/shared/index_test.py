import os
import fitz  # PyMuPDF for PDF extraction
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# Extract text from the PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    pdf_text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pdf_text += page.get_text("text")
    return pdf_text

# Load the PDF and extract the text
pdf_path = '/home/shelender/Downloads/index.pdf'  # Change this to your PDF file path
pdf_text = extract_text_from_pdf(pdf_path)

# Optionally, you can split the text into smaller chunks if it's too large
# For example, splitting into paragraphs or by characters:
pdf_text_chunks = pdf_text.split("\n")  # Splitting by lines or use other splitting methods

# Prepare the text and create documents
OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

list_of_documents = []
for chunk in pdf_text_chunks:
    if chunk.strip():  # Only add non-empty chunks
        doc = Document(page_content=chunk)
        list_of_documents.append(doc)

# Create the FAISS index
db = FAISS.from_documents(list_of_documents, embeddings)

# Save the FAISS index locally
db.save_local("index", index_name="index")

print("FAISS index created and saved successfully!")