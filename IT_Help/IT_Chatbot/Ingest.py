import os
import pickle
import fitz  # PyMuPDF 라이브러리 사용
from dotenv import load_dotenv
from langchain_core.documents import Document # 추가
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from utils import kiwi_tokenizer

load_dotenv("./.env")
load_dotenv("../.env")

DATA_PATH = "./Data"
FAISS_PATH = "./faiss_index"
BM25_PATH = "./bm25_retriever.pkl"

def build_hybrid_db():
    print("1. Data 폴더 내 IT 매뉴얼 PDF 및 [하이퍼링크] 로딩 중...")
    
    documents = []
    # Data 폴더 안의 PDF 파일들을 하나씩 엽니다.
    for filename in os.listdir(DATA_PATH):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(DATA_PATH, filename)
            pdf_doc = fitz.open(file_path)
            
            for page_num, page in enumerate(pdf_doc):
                text = page.get_text()
                
                # 페이지에 숨겨진 하이퍼링크 추출
                links = page.get_links()
                urls = [link.get("uri") for link in links if link.get("uri")]
                unique_urls = list(set(urls)) # 중복 제거
                
                # 💡 핵심: 텍스트에 붙이지 않고 metadata(꼬리표)에 urls 리스트를 아예 저장해버림!
                documents.append(Document(
                    page_content=text,
                    metadata={
                        "source": file_path, 
                        "page": page_num,
                        "urls": unique_urls # 문서 조각이 쪼개져도 이 URL 꼬리표는 계속 따라다닙니다.
                    }
                ))
            pdf_doc.close()
            
    print(f"총 {len(documents)}개 페이지(링크 포함) 로드 완료.")

    print("2. 문서 분할 (Chunking) 중...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)
    
    # ...(이하 BM25 및 FAISS 생성 코드는 기존과 동일하게 유지)...
    print("3. BM25 희소 검색기 인덱싱 중...")
    bm25_retriever = BM25Retriever.from_documents(chunks, preprocess_func=kiwi_tokenizer)
    bm25_retriever.k = 3
    
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25_retriever, f)

    print("4. FAISS 밀집 Vector DB 생성 중...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(FAISS_PATH)

    print("✅ BM25 및 FAISS 하이브리드 DB 구축 완료!")

if __name__ == "__main__":
    build_hybrid_db()
