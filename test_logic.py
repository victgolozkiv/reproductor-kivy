from extractor import get_audio_url
from player import get_best_player
import time

def test():
    print("Testing extraction...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Never Gonna Give You Up
    url, title, thumb, artist = get_audio_url(test_url)
    
    if not url:
        print(f"Extraction failed: {title}")
        return
        
    print(f"Extraction Success: {title}")
    print(f"Artist: {artist}")
    print(f"Thumbnail: {thumb}")
    
    print("Testing player...")
    try:
        player = get_best_player()
        print(f"Using player: {player.__class__.__name__}")
        player.play(url)
        time.sleep(5)
        print(f"Is playing: {player.is_playing()}")
        print(f"Current time: {player.get_time()}ms")
        player.stop()
        print("Test finished.")
    except Exception as e:
        print(f"Player test failed: {e}")

if __name__ == "__main__":
    test()
