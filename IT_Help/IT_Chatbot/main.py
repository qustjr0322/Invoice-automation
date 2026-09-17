import os
import fitz
import pickle
import streamlit as st
from dotenv import load_dotenv

from utils import kiwi_tokenizer

load_dotenv("./.env")
load_dotenv("../.env")

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

FAISS_PATH = "./faiss_index"
BM25_PATH = "./bm25_retriever.pkl"

# --- 하이브리드 RAG 로더 ---
@st.cache_resource
def load_hybrid_retriever():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # 1. FAISS 로드
    vector_store = FAISS.load_local(
        FAISS_PATH, 
        embeddings, 
        allow_dangerous_deserialization=True
    )
    faiss_retriever = vector_store.as_retriever(search_kwargs={"k": 8})

    # 2. BM25 로드
    with open(BM25_PATH, "rb") as f:
        bm25_retriever = pickle.load(f)
    bm25_retriever.k = 8

    # 3. 앙상블 (하이브리드) 결합 (BM25: 0.4 / FAISS: 0.6)
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever],
        weights=[0.4, 0.6]
    )
    return ensemble_retriever

# UI 설정
st.set_page_config(page_title="IT Helpdesk Assistant", page_icon="💻")
st.title("💻 IT Helpdesk 지원 챗봇")
st.caption("사내 IT 장애, PC 설정, 네트워크 관련 문의를 답변해 드립니다.")

# RAG 초기화
try:
    retriever = load_hybrid_retriever()
except Exception as e:
    st.error(f"DB를 읽을 수 없습니다: {e}\n 먼저 'python ingest.py'를 실행해 주세요.")
    st.stop()

# LLM & Prompt
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_template("""
당신은 친절하고 정확한 사내 IT Helpdesk 지원 에이전트입니다.
아래 제공된 [참고 문서]만을 바탕으로 사용자의 IT 문의에 답변하세요.

[필수 수칙]
1. 사용자가 특정 시스템 신청/설치/사용법을 물어볼 경우, 절대 내용을 짧게 요약하지 마세요! 참고 문서에 있는 모든 단계(Step 1, Step 2...)와 상세 설명을 하나도 빠짐없이 구체적으로 나열하세요.
2. 참고 문서에 [관련 시스템 URL]이 포함되어 있다면, "여기를 클릭하세요"처럼 링크를 텍스트 뒤에 숨기지 마세요. 반드시 원본 URL 전체를 그대로 노출하여 답변하세요. 
   (올바른 예시: ITRR 접속 링크: https://www.appsheet.com/...)
3. 매뉴얼에 없는 내용은 지어내지 말고, IT지원팀(내선 6550)으로 문의하도록 안내하세요.
4. IT 장비, PC, 자산 요청 등에 대한 문의일 경우, 단순히 접속 위치만 안내하지 말고 반드시 세부 매뉴얼(예: ITRR Request Guide 등)의 상세 신청 절차(결재, 문서 캡처, 제출 단계 등)를 찾아 함께 안내하세요.

[참고 문서]:
{context}

[사용자 문의]:
{question}

[답변]:
""")

chain = prompt | llm | StrOutputParser()

# 세션 상태
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("예: VPN 접속 시 오류코드 403이 떠요"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("IT 매뉴얼 확인 중..."):
            try:
                # 1. 문서 검색
                retrieved_docs = retriever.invoke(user_input)
                
                # 💡 핵심: 텍스트 조각과 메타데이터의 URL 꼬리표를 합쳐서 AI에게 전달
                context_parts = []
                for d in retrieved_docs:
                    chunk_text = d.page_content
                    chunk_urls = d.metadata.get("urls", [])
                    
                    if chunk_urls:
                        # 조각마다 관련 URL을 명시적으로 적어줌
                        chunk_text += "\n[관련 시스템 URL]: " + ", ".join(chunk_urls)
                        
                    context_parts.append(chunk_text)
                    
                context_text = "\n\n---\n\n".join(context_parts)
                
                # 2. 답변 생성
                response = chain.invoke({"context": context_text, "question": user_input})
                st.write(response)
                
                # 3. 🔍 참고한 매뉴얼의 원본 페이지를 사진으로 보여주기
                with st.expander("🔍 참고한 매뉴얼 원본 이미지 보기"):
                    # 중복된 페이지를 여러 번 보여주지 않기 위해 확인된 페이지 기록
                    seen_pages = set()
                    
                    for doc in retrieved_docs:
                        source_path = doc.metadata.get("source")
                        page_num = doc.metadata.get("page") # 0부터 시작하는 페이지 번호
                        
                        # 파일 경로와 페이지 번호가 있고, 아직 안 보여준 페이지라면
                        if source_path and page_num is not None:
                            page_id = f"{source_path}_{page_num}"
                            
                            if page_id not in seen_pages and os.path.exists(source_path):
                                seen_pages.add(page_id)
                                
                                # PyMuPDF로 해당 PDF 파일 열기
                                pdf_document = fitz.open(source_path)
                                # 해당 페이지 가져오기
                                pdf_page = pdf_document.load_page(page_num)
                                # 해상도(dpi)를 높여서 선명한 이미지(pixmap)로 캡처
                                pix = pdf_page.get_pixmap(dpi=150)
                                
                                # Streamlit에 이미지 띄우기
                                st.image(
                                    pix.tobytes("png"), 
                                    caption=f"📄 {os.path.basename(source_path)} - {page_num + 1}페이지",
                                    use_container_width=True
                                )
                                pdf_document.close()
                                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    st.session_state.messages.append({"role": "assistant", "content": response})
