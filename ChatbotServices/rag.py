import sys
import os
import time
import pandas as pd

# Proje kök dizinini sys.path'e ekler
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser # Bu import kullanılmıyor olabilir, ancak orijinal kodda var
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

# Kendi servisleriniz
from DatabaseServices.database import update_conversation, get_conversation_history
from ChatbotServices import chatbot
from UserInfo import userInfo

# Global değişkenler
retriever = None

def load_environment():
    """Çevresel değişkenleri (API anahtarları gibi) yükler."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY çevresel değişkeni eksik!")

def initialize_llm():
    """LLM (Large Language Model) modelini başlatır."""
    return ChatOpenAI(model="gpt-4o-mini") # 4o-mini ya da 3.5-turbo

def load_pdf(file_path):
    """Belirtilen yoldan bir PDF dosyasını yükler."""
    pdf_loader = PyPDFLoader(file_path)
    return pdf_loader.load()

def load_csv(file_path):
    """Belirtilen yoldan bir CSV dosyasını yükler ve Langchain Document formatına dönüştürür."""
    csv_data = pd.read_csv(file_path, delimiter=";")
    return [
        Document(page_content=f"Question: {row['question']}\nAnswer: {row['answer']}")
        for _, row in csv_data.iterrows()
    ]

def split_documents(docs, chunk_size=1000, chunk_overlap=200):
    """Dokümanları belirtilen boyut ve çakışma ile küçük parçalara ayırır."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return text_splitter.split_documents(docs)

def create_vectorstore(splits, persist_directory="data/chroma_db"):
    """
    AYNI RETURN FORMU - sadece gereksiz persist() çağrısı kaldırıldı
    """
    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        print(f"Mevcut vektör veritabanı yükleniyor: {persist_directory}")
        vectorstore = Chroma(
            persist_directory=persist_directory, 
            embedding_function=OpenAIEmbeddings()
        )
    else:
        print(f"Yeni vektör veritabanı oluşturuluyor: {persist_directory}")
        vectorstore = Chroma.from_documents(
            splits, 
            embedding=OpenAIEmbeddings(), 
            persist_directory=persist_directory
        )
    
    return vectorstore  

def prepare_data(pdf_path="data/DSM.pdf", csv_path="data/Mental_wellness_data.csv", persist_directory="data/chroma_db"):
    """
    AYNI RETURN FORMU - sadece hızlandırılmış
    """
    global retriever

    if retriever is None:
        print("Retriever başlatılıyor...")
        
        # ÖNEMLİ: Eğer DB varsa, hiç data okuma!
        if os.path.exists(persist_directory) and os.listdir(persist_directory):
            print("Mevcut DB yükleniyor - data okunmuyor")
            vectorstore = Chroma(
                persist_directory=persist_directory, 
                embedding_function=OpenAIEmbeddings()
            )
        else:
            print("İlk kez çalışıyor, data işleniyor...")
            pdf_docs = load_pdf(pdf_path)
            qa_docs = load_csv(csv_path)
            all_docs = pdf_docs + qa_docs
            splits = split_documents(all_docs)
            vectorstore = Chroma.from_documents(
                splits, 
                embedding=OpenAIEmbeddings(), 
                persist_directory=persist_directory
            )
        
        retriever = vectorstore.as_retriever()
        print("Retriever hazır.")
    
    return retriever  # AYNI RETURN!


def create_prompt_for_header():
    """Konuşma başlığı oluşturmak için kullanılacak prompt'u tanımlar."""
    return PromptTemplate(
        input_variables=["first_message"],
        template="""
    You are a helpful assistant. Given the user's first message, generate a **very short summary** of the main idea in **3 to 5 words** — like a title or tag.

    Avoid full sentences. Be concise, clear, and context-aware.

    First Message:
    {first_message}

    Summary (3-5 words):
    """)

def llm_response_for_header(first_message):
    """İlk mesaja göre konuşma başlığı oluşturmak için LLM'i kullanır."""
    llm = chatbot.get_llm()
    # Başlık oluştururken retriever'a ihtiyaç duyulmayabilir, ancak orijinal kodda çağrılmış.
    # Eğer performans önemliyse bu satır kaldırılabilir.
    retriever_instance = chatbot.get_retriever() 
    
    if llm is None:
        raise ValueError("LLM object is None. Check chatbot initialization.")
    # if retriever_instance is None: # Eğer başlık için retriever gerekmiyorsa bu kontrolü kaldırabiliriz
    #     raise ValueError("Retriever object is None. Check chatbot initialization.")

    prompt = create_prompt_for_header()
    prompt_text = prompt.format(first_message=first_message)
    try:
        answer_llm = llm.invoke(prompt_text).content
    except AttributeError as e:
        raise ValueError(f"LLM.invoke failed for header creation: {e}. Check if LLM object is properly initialized.")

    return answer_llm

def create_prompt():
    """Ana sohbet yanıtı için kullanılacak prompt'u tanımlar."""
    return PromptTemplate(
        input_variables=["user", "question", "previous_conversations"],
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
    """Kullanıcının sorusuna LLM kullanarak yanıt verir ve konuşmayı veritabanına kaydeder."""
    llm = chatbot.get_llm()
    retriever_instance = chatbot.get_retriever() # retriever ismini değiştirdim, global retriever ile çakışmasın

    # None olup olmadığını kontrol et
    if llm is None:
        raise ValueError("LLM object is None. Check chatbot initialization.")
    if retriever_instance is None:
        raise ValueError("Retriever object is None. Check chatbot initialization.")

    # Önceki konuşmaları veritabanından çek
    recent_conversations = get_conversation_history(limit=10)
    history_text = "\n".join(
        [f"User: {entry['question']}\nAssistant: {entry['answer']}" for entry in recent_conversations])
    
    print("recent_conversations:", recent_conversations)
    print("history_text:", history_text)

    # Soruyla ilgili dokümanları al (Hata yakalama ekledim)
    try:
        search_results = retriever_instance.invoke(question)
        # Eğer alınan dokümanlar LLM'e verilecekse burada prompt'a eklenmeli
        # Örneğin: relevant_docs_text = "\n".join([doc.page_content for doc in search_results])
        # ve prompt'a {relevant_docs_text} eklenmeli
    except AttributeError as e:
        raise ValueError(f"Retriever.invoke failed: {e}. Check if retriever is properly initialized.")

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
    except AttributeError as e:
        raise ValueError(f"LLM.invoke failed: {e}. Check if LLM object is properly initialized.")

    print("answer created")
    update_conversation(question, answer_llm)
    print("DB saved")
    return answer_llm

def main():
    """
    Bu fonksiyon main.py veya bir Flask/web uygulaması tarafından çağrılacaktır.
    Burada doğrudan bir sohbet döngüsü bulunmamaktadır.
    """
    # Örnek kullanım (normalde bir web servisi veya ayrı bir başlatma scripti çağırır)
    # load_environment()
    # llm_model = initialize_llm()
    # chatbot.set_llm(llm_model)
    # retriever_instance = prepare_data()
    # chatbot.set_retriever(retriever_instance)

    # test_question = "Anksiyete nedir ve belirtileri nelerdir?"
    # response = llm_response(test_question)
    # print(f"Soru: {test_question}\nCevap: {response}")
    return

if __name__ == "__main__":
    main()