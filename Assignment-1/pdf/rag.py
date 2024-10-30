import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from groq import Groq

# Load environment variables
load_dotenv()

# Initialize Qdrant
api_key = os.getenv('QDRANT_API_KEY')  # Get the API key from environment variables
qdrant_client = QdrantClient(api_key=api_key)  # Initialize the Qdrant client
collection_name = "pesuio-rag"

# Jina API setup
jina_api_key = os.getenv('JINA_API_KEY')
headers = {
    'Authorization': f'Bearer {jina_api_key}',
    'Content-Type': 'application/json'
}
url = 'https://api.jina.ai/v1/embeddings'

# Initialize Groq client
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

def retrieve_nearest_chunks(query, top_k=5):
    # Embed the query using Jina API
    payload = {
        'input': query,
        'model': 'jina-embeddings-v3'
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Error embedding query: {response.status_code} - {response.text}")
        return []

    query_embedding = response.json()['data'][0]['embedding']

    # Query Qdrant for nearest vectors
    query_response = qdrant_client.search(  # Fixed the client name to qdrant_client
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k,
        with_payload=True  # Set to True to include metadata
    )

    # Extract the matches from the response
    matches = query_response['result']  # Adjust based on your Qdrant client version
    return matches

def generate_response(query, context):
    prompt = f"""You are a helpful AI assistant. Use the following context to answer the user's question. If the answer is not in the context, say "I don't have enough information to answer that question."

Context:
{context}

User's question: {query}

Answer:"""

    response = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ],
        model="llama-3.1-70b-versatile",
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    query = "What is the command to stage my changes?"
    nearest_chunks = retrieve_nearest_chunks(query)

    # Check if any chunks were retrieved
    if nearest_chunks:
        context = "\n".join([chunk['payload']['text'] for chunk in nearest_chunks])  # Changed from 'metadata' to 'payload'
        
        rag_response = generate_response(query, context)

        print(f"\nQuery: {query}")
        print("\nRAG Response:")
        print(rag_response)

        print("\nRetrieved chunks:")
        for i, chunk in enumerate(nearest_chunks, 1):
            print(f"\n{i}. Score: {chunk['score']:.4f}")
            print(f"Text: {chunk['payload']['text'][:200]}...")  # Changed from 'metadata' to 'payload'
    else:
        print("No chunks retrieved.")
