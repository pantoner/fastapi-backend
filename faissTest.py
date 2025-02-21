from faiss_helper import search_faiss

query = "What should I do for my speed workout today?"
results = search_faiss(query, top_k=3)

print("🔍 FAISS Search Results:")
for result in results:
    print(result)
