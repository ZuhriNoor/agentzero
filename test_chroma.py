import chromadb
print("Connecting to Chroma...")
client = chromadb.PersistentClient(path="data/vector_db")
print("Done.")
