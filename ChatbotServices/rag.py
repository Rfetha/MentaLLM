"""
    rag'ın eski hali rarda arşivli 
    
    load ekranı ayarla bağla
    DB cevapları kaydet ...         + 
        burdaki mainde çalışıyor fakat Chatbot.py da bir problem var flaske döndürmüyor        +
    USER ekranı olsun usera göre data table         + 
"""
import sys 
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from DatabaseServices.database import update_conversation
from ChatbotServices import chatbot
from DatabaseServices.database import get_conversation_history
from UserInfo import userInfo

# Global değişkenler
retriever = None

def load_environment():
    """Çevresel değişkenleri yükler"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY çevresel değişkeni eksik!")

def initialize_llm():
    """LLM modelini başlatır"""
    return ChatOpenAI(model="gpt-4o-mini")

def load_pdf(file_path):
    """PDF dosyasını yükler"""
    pdf_loader = PyPDFLoader(file_path)
    return pdf_loader.load()

def load_csv(file_path):
    """CSV dosyasını yükler"""
    csv_data = pd.read_csv(file_path, delimiter=";")
    return [
        Document(page_content=f"Question: {row['question']}\nAnswer: {row['answer']}")
        for _, row in csv_data.iterrows()
    ]

def split_documents(docs, chunk_size=1000, chunk_overlap=200):
    """Dokümanları küçük parçalara ayırır"""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return text_splitter.split_documents(docs)

def create_vectorstore(splits):
    """Vektör veri tabanı oluşturur"""
    return Chroma.from_documents(splits, embedding=OpenAIEmbeddings())

def prepare_data(pdf_path="data/DSM.pdf", csv_path="data/Mental_wellness_data.csv"):
    """Verileri işler ve retriever nesnesini oluşturur"""
    global retriever

    if retriever is None:
        pdf_docs = load_pdf(pdf_path)
        qa_docs = load_csv(csv_path)
        recent_conversations = get_conversation_history(limit=5)
        db_docs = [
            Document(page_content=f"Question: {qa['question']} Answer: {qa['answer']}")
            for qa in recent_conversations
        ]
        all_docs = pdf_docs + qa_docs + db_docs
        splits = split_documents(all_docs)
        vectorstore = create_vectorstore(splits)
        retriever = vectorstore.as_retriever()
    return retriever

def create_prompt():
    """Yanıt formatını belirten prompt oluşturur"""
    return PromptTemplate(
        input_variables=["user","question","previous_conversations"],
        template="""{user}
        You are a mental health assistant trained to provide supportive, empathetic, and scientifically grounded responses.
        However, you cannot make medical diagnoses or prescribe medication.
        If you don't know the answer, just say that you don't know. 
        Answer concisely (max 3 sentences).
        
        {previous_conversations}
        
        Question: {question}

        Answer:"""
    )

def llm_response(question):
    llm = chatbot.get_llm()
    retriever = chatbot.get_retriever()
    
    # None olup olmadığını kontrol et
    if llm is None:
        raise ValueError("LLM object is None. Check chatbot initialization.")
    if retriever is None:
        raise ValueError("Retriever object is None. Check chatbot initialization.")

    # Önceki konuşmaları veritabanından çek
    recent_conversations = get_conversation_history(limit=10)
    history_text = "\n".join([f"User: {entry['question']}\nAssistant: {entry['answer']}" for entry in recent_conversations])
    #history_text = "\n".join([f"Q: {qa['question']} A: {qa['answer']}" for qa in recent_conversations])
    print("recent_conversations:", recent_conversations)
    print("history_text:", history_text)

    # Soruyla ilgili dokümanları al (Hata yakalama ekledim)
    try:
        search_results = retriever.invoke(question)
    except AttributeError:
        raise ValueError("Retriever.invoke failed. Check if retriever is properly initialized.")

    # Prompt’u oluştur
    user = userInfo.get_user()
    prompt = create_prompt()
    prompt_text = prompt.format(
        previous_conversations=f"Here is our chat history:\n{history_text}",
        question=question,
        user=f"This is my name:\n{user}"
    )
    # LLM çağrısı
    print("prompt_text:", prompt_text)
    try:
        answer_llm = llm.invoke(prompt_text).content
    except AttributeError:
        raise ValueError("LLM.invoke failed. Check if LLM object is properly initialized.")

    print("answer created")
    update_conversation(question, answer_llm)
    print("DB saved")
    
    return answer_llm



def main():
    """
    response = llm_response("def", "I'm ill")
    print(response)"""

    return

if __name__ == "__main__":
    main()
