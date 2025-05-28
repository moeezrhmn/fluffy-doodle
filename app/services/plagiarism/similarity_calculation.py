from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.plagiarism import preprocess
from app.services.plagiarism import service as pl_service

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string, re
import faiss
import numpy as np



def find_matched_text(chunk, page_content):
    
    if chunk in page_content:
        print('exact exists: ', chunk)
        return 1.0

    sentences = preprocess.simple_split_into_chunks(page_content)
    # print('sentenaces: ', len(sentences))
    # max_sim = 0.0
    # for sentence in sentences:
    #     sim = compare_similarity(chunk, sentence) 
    #     if sim > max_sim:
    #         max_sim = sim
    # return max_sim
    if not sentences:
        return 0.0

    results, distances = check_plagiarism_webpages(chunk, sentences)
    # print('distances: ', distances.size)
    return max(distances) if distances.size > 0 else 0.0



def check_plagiarism_webpages(target_text, corpus, threshold=0.8):
    # Preprocess all texts
    # corpus = [pl_service.clean_text(doc) for doc in corpus]
    
    # Vectorize texts using TF-IDF
    vectorizer = TfidfVectorizer(max_features=5000)  # Limit features for speed
    tfidf_matrix = vectorizer.fit_transform([target_text] + corpus).toarray()
    
    tfidf_matrix = np.array(tfidf_matrix, dtype=np.float32, order='C')

    # Create FAISS index
    dimension = tfidf_matrix.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner Product (for cosine similarity)
    faiss.normalize_L2(tfidf_matrix)  # Normalize for cosine similarity
    index.add(tfidf_matrix[1:])  # Add corpus vectors (exclude target)
    
    # Query the target text
    target_vector = tfidf_matrix[0:1]
    k = len(corpus)  # Search all documents
    distances, indices = index.search(target_vector, k)
    
    # Collect results above threshold
    results = [(indices[0][i], distances[0][i]) for i in range(len(indices[0])) if distances[0][i] > threshold]
    return results, distances[0]





def compare_similarity(given_text, source_text):
    if not given_text or not source_text:
        return 0.0

    # Token-based containment check
    # given_text_tokens = set(word_tokenize(chunk.lower()))
    # source_text_tokens = set(word_tokenize(page_text.lower()))
    # is_contained = given_text_tokens.issubset(source_text_tokens)
    
    stop_words = set(stopwords.words('english'))
    def clean(text):
        tokens = word_tokenize(text.lower())
        return set(t for t in tokens if t not in stop_words and t not in string.punctuation)

    given_text_tokens = clean(given_text)
    source_text_tokens = clean(source_text)
    is_contained = given_text_tokens.issubset(source_text_tokens)

    # Use CountVectorizer with term frequencies
    # vectorizer = CountVectorizer(
    #     min_df=1,
    #     stop_words=None,
    #     binary=False  # Use term frequencies
    # )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
    try:
        vectors = vectorizer.fit_transform([given_text, source_text])
        cosine_sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        
        # If chunk is contained, boost similarity significantly
        if is_contained:
            shared_terms = len(given_text_tokens & source_text_tokens)
            total_given_text_terms = len(given_text_tokens)
            containment_ratio = shared_terms / total_given_text_terms if total_given_text_terms > 0 else 0.0
            
            # Boost similarity based on containment ratio
            cosine_sim = min(1.0, cosine_sim + (containment_ratio * 0.5))
            print(f"Chunk match in Content. Ratio: {containment_ratio:.2f}, Cosine Similarity: {cosine_sim:.4f}")
        
        # else:
            # print(f"Chunk is NOT fully contained in page_text. Cosine Similarity: {cosine_sim:.4f}")

        return cosine_sim
    except ValueError as e:
        print(f"Vectorization error: {e}")
        print('Given: ', given_text, ' source: ', source_text)
        return 0.0


