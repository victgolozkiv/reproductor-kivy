from extractor import search_youtube, get_audio_url
import time

def test_search():
    query = "Rick Astley"
    print(f"Searching for: {query}...")
    results = search_youtube(query, limit=3)
    
    if not results:
        print("No results found.")
        return
        
    for i, res in enumerate(results):
        print(f"[{i+1}] {res['title']} ({res['url']})")
        
    # Test selecting the first one
    first = results[0]
    print(f"\nSelecting: {first['title']}")
    audio_url, title, thumb, artist = get_audio_url(first['url'])
    
    if audio_url:
        print(f"Success! Direct Audio URL found: {audio_url[:50]}...")
    else:
        print(f"Failed to get audio URL: {title}")

if __name__ == "__main__":
    test_search()
