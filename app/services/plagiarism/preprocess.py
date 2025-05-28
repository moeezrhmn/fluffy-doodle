import nltk, re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import sent_tokenize
import numpy as np

from fastapi import UploadFile, HTTPException


# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')

def preprocess_text(text):
    stop_words = set(stopwords.words('english')) - {'not', 'no'}  # Keep negation words
    lemmatizer = WordNetLemmatizer()

    # Convert to lowercase
    text = text.lower()
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    # Tokenize
    tokens = word_tokenize(text)
    # Keep alphanumeric, hyphenated words, and meaningful punctuation
    tokens = [word for word in tokens if (word.isalnum() or '-' in word) and word not in stop_words]
    # Lemmatize
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    # Join tokens
    processed_text = ' '.join(tokens)
    
    return processed_text if processed_text else text

def normalize_whitespace(text):
    return re.sub(r'\s+', ' ', text).strip()

def clean_file_names(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)  # Remove invalid characters
    name = re.sub(r'\s+', '-', name).strip() 
    return name[:100]

def simple_split_into_chunks(text):
    # Avoid splitting at common abbreviations like e.g., i.e., etc.
    # First, temporarily replace them with placeholders
    abbreviations = {
        "e.g.": "___EG___",
        "i.e.": "___IE___",
        "etc.": "___ETC___",
        "Mr.": "___MR___",
        "Mrs.": "___MRS___",
        "Dr.": "___DR___"
    }
    
    for abbr, placeholder in abbreviations.items():
        text = text.replace(abbr, placeholder)
    
    # Split using punctuation followed by whitespace or end of string
    raw_chunks = re.split(r'[.?!]\s*', text)
    
    # Restore the abbreviations and clean up
    clean_chunks = []
    for chunk in raw_chunks:
        for placeholder, abbr in abbreviations.items():
            chunk = chunk.replace(abbr, placeholder)
        chunk = chunk.strip()
        if chunk and len(chunk) > 20:  # Skip empty strings
            clean_chunks.append(chunk)
    
    return clean_chunks


def split_into_chunks(text: str, max_words: int = 10, max_chunks: int = 100):
    sentences = sent_tokenize(text.strip())
    
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk.split()) + len(sentence.split()) <= max_words:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        if len(chunks) >= max_chunks:
            break

    if current_chunk and len(chunks) < max_chunks:
        chunks.append(current_chunk.strip())
    
    return chunks




def smart_tfidf_chunks(text: str, max_words: int = 40, max_chunks: int = 10):
    # Step 1: Tokenize text into sentences
    sentences = sent_tokenize(text)
    if not sentences:
        return []

    # Step 2: Compute TF-IDF scores
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(sentences)
    scores = tfidf_matrix.max(axis=1).toarray().flatten()  # max score per sentence

    # Step 3: Rank sentences by score (descending)
    ranked_sentences = [s for _, s in sorted(zip(scores, sentences), key=lambda x: -x[0])]

    # Step 4: Group sentences into chunks of max_words
    chunks = []
    current_chunk = ""

    for sentence in ranked_sentences:
        if len(current_chunk.split()) + len(sentence.split()) <= max_words:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence

        if len(chunks) >= max_chunks:
            break

    # Last chunk
    if current_chunk and len(chunks) < max_chunks:
        chunks.append(current_chunk.strip())

    return chunks




# File handling
async def extract_file_text(file: UploadFile):

    filename = file.filename
    extension = filename.split('.')[-1].lower()
    # Read file content as bytes
    content = await file.read()
    if len(content) > 10_000_000:  # 10 MB
        raise HTTPException(status_code=400, detail="File too large")
    try:
        if extension == "txt":
            text = content.decode("utf-8")

        elif extension == "pdf":
            text = extract_text_from_pdf(content)

        elif extension == "docx":
            text = extract_text_from_docx(content)

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

    

def extract_text_from_pdf(content: bytes) -> str:
    import fitz  # PyMuPDF
    text = ""
    with fitz.open(stream=content, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()

def extract_text_from_docx(content: bytes) -> str:
    from docx import Document
    import io
    doc = Document(io.BytesIO(content))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

