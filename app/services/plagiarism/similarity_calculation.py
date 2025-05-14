from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from difflib import SequenceMatcher
from sklearn.metrics.pairwise import cosine_similarity
from app.services.plagiarism import preprocess
from nltk.tokenize import word_tokenize


# def compare_similarity(chunk, page_text):
#     # Assume both chunk and page_text are already preprocessed
#     # If not preprocessed, apply preprocess_text to both

#     if not chunk or not page_text:
#         return 0.0  # Handle empty inputs
#     # Optional: SequenceMatcher for exact matches (less relevant after preprocessing)

#     ratio = SequenceMatcher(None, chunk, page_text).ratio()
#     if ratio > 0.85:
#         return ratio
#     # TF-IDF and cosine similarity

#     vectorizer = TfidfVectorizer(
#         min_df=1, stop_words=None
#     )  # Avoid additional stopword removal
#     try:
#         vectors = vectorizer.fit_transform([chunk, page_text])
#         cosine_sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
#         print("Cosine Similarity: ", cosine_sim)
#         return cosine_sim
#     except ValueError:
#         return 0.0
# def compare_similarity(chunk, page_text):
#     if not chunk or not page_text:
#         return 0.0

#     # Direct substring check (preprocessed text)
#     if chunk in page_text:
#         print("Chunk is a direct substring of page_text. Returning similarity 1.0")
#         return 1.0

#     # Token-based containment check
#     chunk_tokens = set(word_tokenize(chunk.lower()))
#     page_tokens = set(word_tokenize(page_text.lower()))
#     is_contained = chunk_tokens.issubset(page_tokens)

#     # Use CountVectorizer with binary mode
#     vectorizer = CountVectorizer(min_df=1, stop_words=None, binary=True)
    
#     try:
#         vectors = vectorizer.fit_transform([chunk, page_text])
#         cosine_sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        
#         if is_contained:
#             cosine_sim = min(1.0, cosine_sim * 1.5)
#             print(f"\n Chunk is contained in page_text. Cosine Similarity: {cosine_sim}")
#         else:
#             print(f"Chunk is NOT fully contained in page_text. Cosine Similarity: {cosine_sim}")

#         return cosine_sim
#     except ValueError as e:
#         print(f"Vectorization error: {e}")
#         return 0.0

def compare_similarity(chunk, page_text):
    if not chunk or not page_text:
        return 0.0

    # Token-based containment check
    chunk_tokens = set(word_tokenize(chunk.lower()))
    page_tokens = set(word_tokenize(page_text.lower()))
    is_contained = chunk_tokens.issubset(page_tokens)

    # Use CountVectorizer with term frequencies
    vectorizer = CountVectorizer(
        min_df=1,
        stop_words=None,
        binary=False  # Use term frequencies
    )
    
    try:
        # Fit and transform both texts
        vectors = vectorizer.fit_transform([chunk, page_text])
        cosine_sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        
        # If chunk is contained, boost similarity significantly
        if is_contained:
            # Compute proportion of shared terms
            shared_terms = len(chunk_tokens & page_tokens)
            total_chunk_terms = len(chunk_tokens)
            containment_ratio = shared_terms / total_chunk_terms if total_chunk_terms > 0 else 0.0
            # Boost similarity based on containment ratio
            cosine_sim = min(1.0, cosine_sim + (containment_ratio * 0.5))
            print(f"Chunk is contained in page_text. Containment ratio: {containment_ratio:.2f}, Cosine Similarity: {cosine_sim:.4f}")
        else:
            print(f"Chunk is NOT fully contained in page_text. Cosine Similarity: {cosine_sim:.4f}")

        return cosine_sim
    except ValueError as e:
        print(f"Vectorization error: {e}")
        return 0.0



# AN OTHER OPTION NEED TO TEST
# def compare_similarity(chunk, page_text):
#     if not chunk or not page_text:
#         return 0.0

#     # Fuzzy substring check for near-exact matches
#     seq_matcher = SequenceMatcher(None, chunk, page_text)
#     match_ratio = seq_matcher.ratio()
#     if match_ratio > 0.8:
#         print(f"Near-exact substring match. SequenceMatcher ratio: {match_ratio:.4f}, Returning similarity: 0.9")
#         return 0.9

#     # Token-based containment check
#     chunk_tokens = set(word_tokenize(chunk.lower()))
#     page_tokens = set(word_tokenize(page_text.lower()))
#     is_contained = chunk_tokens.issubset(page_tokens)

#     # Use CountVectorizer with term frequencies
#     vectorizer = CountVectorizer(min_df=1, stop_words=None, binary=False)
    
#     try:
#         vectors = vectorizer.fit_transform([chunk, page_text])
#         cosine_sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        
#         if is_contained:
#             shared_terms = len(chunk_tokens & page_tokens)
#             total_chunk_terms = len(chunk_tokens)
#             containment_ratio = shared_terms / total_chunk_terms if total_chunk_terms > 0 else 0.0
#             cosine_sim = min(1.0, cosine_sim + (containment_ratio * 0.5))
#             print(f"Chunk is contained in page_text. Containment ratio: {containment_ratio:.2f}, Cosine Similarity: {cosine_sim:.4f}")
#         else:
#             print(f"Chunk is NOT fully contained in page_text. Cosine Similarity: {cosine_sim:.4f}")

#         return cosine_sim
#     except ValueError as e:
#         print(f"Vectorization error: {e}")
#         return 0.0