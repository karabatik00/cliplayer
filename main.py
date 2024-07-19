import os
import yaml
import sqlite3
from googleapiclient.discovery import build
from yt_dlp import YoutubeDL
import vlc
import unidecode
import time

# Constants
CONFIG_FILE = "config.yml"
DATABASE_FILE = "music_player.db"
YOUTUBE_API_KEY = 'YOUR_YOUTUBE_API_KEY'  # Replace with your YouTube API key

# Global variables to keep track of VLC player and playlist state
player = None
media = None
current_playlist = []
current_index = 0
paused_time = 0
queue = []
playlist_mode = False

# Logo
def display_logo():
    logo = r'''
 ▄▄▄▄▄▄▄    ▄▄▄        ▄▄▄    ▄▄▄▄▄▄▄    ▄▄▄        ▄▄▄▄▄▄    ▄▄   ▄▄    ▄▄▄▄▄▄▄    ▄▄▄▄▄▄   
█       █  █   █      █   █  █       █  █   █      █      █  █  █ █  █  █       █  █   ▄  █  
█       █  █   █      █   █  █    ▄  █  █   █      █  ▄   █  █  █▄█  █  █    ▄▄▄█  █  █ █ █  
█     ▄▄█  █   █      █   █  █   █▄█ █  █   █      █ █▄█  █  █       █  █   █▄▄▄   █   █▄▄█▄ 
█    █     █   █▄▄▄   █   █  █    ▄▄▄█  █   █▄▄▄   █      █  █▄     ▄█  █    ▄▄▄█  █    ▄▄  █
█    █▄▄   █       █  █   █  █   █      █       █  █  ▄   █    █   █    █   █▄▄▄   █   █  █ █
█▄▄▄▄▄▄▄█  █▄▄▄▄▄▄▄█  █▄▄▄█  █▄▄▄█      █▄▄▄▄▄▄▄█  █▄█ █▄▄█    █▄▄▄█    █▄▄▄▄▄▄▄█  █▄▄▄█  █▄█
    '''
    print(logo)
    print("[ If you don't know how to use **cliplayer**, please type **help**. ]")

# Help command
def display_help():
    help_text = '''
Available Commands:
- play <song name or YouTube URL>: Search and play a song from YouTube.
- pp <playlist URL>: Play all songs from a YouTube playlist.
- fav: Add the currently playing song to favorites.
- favlist: List all favorite songs.
- favr <song ID> or fr <song ID>: Remove a song from favorites by its ID.
- favplay <song ID>: Play a favorite song by its ID or add it to the queue.
- pf: Play all favorite songs.
- next [<number>]: Play the next song or skip to a specific song in the playlist.
- prev or previous: Play the previous song in the playlist.
- vol <volume>: Set the volume (0-100).
- seek <seconds>: Seek to a specific time in the current song.
- repeat or replay: Replay the current song.
- now: Display the currently playing song.
- pause: Pause the current song.
- resume: Resume the paused song.
- stop: Stop the current song.
- close: Close the player and clear the playlist.
- playlist restart: Restart the current playlist.
- last: Play the last played song.
- session: Display session details.
- config: Display the current configuration.
    '''
    print(help_text)

# Load or create config
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            'database': 'sqlite',
            'language': 'en',
            'volume': 50,
            'equalizer': {},
        }
        with open(CONFIG_FILE, 'w') as file:
            yaml.dump(default_config, file)
        return default_config
    else:
        with open(CONFIG_FILE, 'r') as file:
            return yaml.safe_load(file)

config = load_config()

# Database initialization
def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT,
            is_favorite BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS last_played (
            id INTEGER PRIMARY KEY,
            title TEXT,
            url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Transliterate function
def transliterate(text):
    return unidecode.unidecode(text)

# Add favorite song
def add_favorite(title, url):
    title = transliterate(title)
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM songs WHERE title = ? AND url = ? AND is_favorite = 1', (title, url))
        result = cursor.fetchone()
        if result:
            print("Error: This song is already in your favorites.")
        else:
            cursor.execute('INSERT OR IGNORE INTO songs (title, url, is_favorite) VALUES (?, ?, 1)', (title, url))
            conn.commit()
            renumber_favorites()
            print("Song added to favorites.")
        conn.close()
    except sqlite3.IntegrityError as e:
        print(f"Error adding to favorites: {e}")

def renumber_favorites():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT rowid, * FROM songs WHERE is_favorite = 1 ORDER BY rowid')
        favorites = cursor.fetchall()
        for index, song in enumerate(favorites):
            cursor.execute('UPDATE songs SET id = ? WHERE rowid = ?', (index + 1, song[0]))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error renumbering favorites: {e}")

def list_favorites():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, url FROM songs WHERE is_favorite = 1 ORDER BY id')
        favorites = cursor.fetchall()
        conn.close()
        if favorites:
            print("Favorite Songs:")
            for song in favorites:
                print(f"{song[0]}. {song[1]} ({song[2]})")
        else:
            print("No favorite songs found.")
    except Exception as e:
        print(f"Error listing favorites: {e}")

def remove_from_favorites(song_id):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM songs WHERE id = ? AND is_favorite = 1', (song_id,))
        conn.commit()
        renumber_favorites()
        conn.close()
        print("Song removed from favorites.")
    except Exception as e:
        print(f"Error removing from favorites: {e}")

def play_favorites():
    global current_playlist, current_index, playlist_mode
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT title, url FROM songs WHERE is_favorite = 1 ORDER BY id')
        current_playlist = [{'title': row[0], 'url': row[1]} for row in cursor.fetchall()]
        conn.close()
        current_index = 0
        playlist_mode = False
        play_next_song()
    except Exception as e:
        print(f"Error playing favorites: {e}")

def play_favorite_by_id(song_id):
    global queue
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT title, url FROM songs WHERE id = ? AND is_favorite = 1', (song_id,))
        song = cursor.fetchone()
        conn.close()
        if song:
            song_data = {'title': song[0], 'url': song[1]}
            if player and player.is_playing():
                queue.append(song_data)
                print(f"Favorite song added to the queue: {song_data['title']} ({song_data['url']})")
            else:
                current_playlist.append(song_data)
                play_next_song(len(current_playlist))
        else:
            print(f"No favorite song found with ID: {song_id}")
    except Exception as e:
        print(f"Error playing favorite by ID: {e}")

# Update last played song
def update_last_played(title, url):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM last_played')
        cursor.execute('INSERT INTO last_played (id, title, url) VALUES (1, ?, ?)', (title, url))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating last played song: {e}")

# Play last played song
def play_last_played():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT title, url FROM last_played WHERE id = 1')
        last_song = cursor.fetchone()
        conn.close()
        if last_song:
            play_song_from_url(last_song[1])
        else:
            print("No last played song found.")
    except Exception as e:
        print(f"Error playing last played song: {e}")

# YouTube API setup
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def search_youtube(query):
    try:
        request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            maxResults=5
        )
        response = request.execute()
        return [{'title': item['snippet']['title'], 'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"} for item in response['items']]
    except Exception as e:
        print(f"Error searching YouTube: {e}")
        return []

def extract_streaming_url(youtube_url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'force_generic_extractor': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            return info_dict['url']
    except Exception as e:
        print(f"Error extracting streaming URL: {e}")
        return None

def on_media_finished(event):
    global current_index, current_playlist, playlist_mode
    if current_index < len(current_playlist):
        play_next_song()
    else:
        if playlist_mode:
            print("Playlist completely played. Type 'playlist restart' to restart the playlist or 'close' to exit.")

def stream_audio_with_vlc(url):
    global player, media
    try:
        instance = vlc.Instance()
        player = instance.media_player_new()
        media = instance.media_new(url)
        player.set_media(media)
        player.play()
        events = player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, on_media_finished)
        update_display()
    except Exception as e:
        print(f"Error playing audio with VLC: {e}")

def play_next_song(index=None):
    global current_index, current_playlist, queue, playlist_mode
    if player:
        player.stop()
    if index is not None:
        current_index = index - 1
    if current_playlist and current_index < len(current_playlist):
        song = current_playlist[current_index]
        streaming_url = extract_streaming_url(song['url'])
        if streaming_url:
            stream_audio_with_vlc(streaming_url)
            update_last_played(song['title'], song['url'])
            display_now_playing(song['title'], song['url'])
            current_index += 1
        else:
            print(f"Error: Could not stream {song['title']}")
            current_index += 1
            play_next_song()
    elif queue:
        song = queue.pop(0)
        streaming_url = extract_streaming_url(song['url'])
        if streaming_url:
            stream_audio_with_vlc(streaming_url)
            current_playlist.append(song)
            current_index = len(current_playlist)
            update_last_played(song['title'], song['url'])
            display_now_playing(song['title'], song['url'])
        else:
            print(f"Error: Could not stream {song['title']}")
    else:
        if playlist_mode:
            print("Playlist completely played. Type 'playlist restart' to restart the playlist or 'close' to exit.")
        else:
            print("No next song available in the queue.")

def play_previous_song():
    global current_index, current_playlist, queue
    if player:
        player.stop()
    if current_playlist and current_index > 1:
        current_index -= 2
        play_next_song()
    elif queue:
        print("No previous song available in the queue.")
    else:
        print("No previous song available.")

def extract_playlist_videos(playlist_url):
    try:
        playlist_id = playlist_url.split("list=")[-1]
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50
        )
        response = request.execute()
        videos = [{'title': item['snippet']['title'], 'url': f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}"} for item in response['items']]
        playlist_info_request = youtube.playlists().list(
            part="snippet",
            id=playlist_id
        )
        playlist_info_response = playlist_info_request.execute()
        playlist_name = playlist_info_response['items'][0]['snippet']['title']
        # Filter out unavailable videos
        videos = [video for video in videos if 'Deleted video' not in video['title'] and 'Private video' not in video['title']]
        return playlist_name, videos
    except Exception as e:
        print(f"Error extracting playlist videos: {e}")
        return None, []

def play_song_from_url(youtube_url):
    global current_playlist, current_index
    streaming_url = extract_streaming_url(youtube_url)
    if streaming_url:
        stream_audio_with_vlc(streaming_url)
        song = {'title': youtube_url, 'url': youtube_url}  # Assuming title as URL for direct links
        current_playlist.append(song)
        update_last_played(song['title'], song['url'])
        display_now_playing(song['title'], song['url'])
        return True
    else:
        print(f"Error: Could not stream {youtube_url}")
        return False

# Update display function
def update_display():
    if player and player.is_playing():
        song = current_playlist[current_index - 1]
        current_time = player.get_time() // 1000
        length = player.get_length() // 1000
        volume = player.audio_get_volume()
        song_title = song['title']
        duration = f"{length // 60}:{length % 60:02d}"
        elapsed = f"{current_time // 60}:{current_time % 60:02d}"

        volume_bar = '▁▂▃▄▅▆▇'
        volume_level = volume_bar[:volume * len(volume_bar) // 100]

        display_text = f'''
({song_title})
{elapsed} ━{'━' * ((current_time * 10) // length)}❍{'━' * (10 - (current_time * 10) // length)} -{duration}
              ↻     ⊲  Ⅱ  ⊳     ↺
VOLUME: {volume_level}
        '''

        print(display_text)

def display_now_playing(title, url):
    ascii_art = f'''
  ______ _ _       _                                       
 |  ____(_) |     | |                                      
 | |__   _| | ___ | |__   ___ _ __                          
 |  __| | | |/ _ \\| '_ \\ / _ \\ '__|                         
 | |    | | | (_) | |_) |  __/ |                            
 |_|    |_|_|\\___/|_.__/ \\___|_|                            
                                                           
 _   _  ____  _     _____ ____  _        _     _____ ____  
| | | |/ __ \\| |   |_   _|  _ \\| |      | |   |_   _/ __ \\ 
| | | | |  | | |     | | | |_) | |      | |     | || |  | |
| | | | |  | | |     | | |  _ <| |      | |     | || |  | |
| |_| | |__| | |_____| |_| |_) | |____  | |_____| || |__| |
 \\___/ \\____/|______|_____|____/|______| |______|____\\____/ 
                                                           
Now playing: {title} ({url})
'''
    print(ascii_art)

# Command handlers
def handle_command(command):
    global player, media, current_playlist, current_index, paused_time, queue, playlist_mode
    parts = command.split()
    cmd = parts[0]
    args = parts[1:]

    def is_playing():
        if not player or not player.is_playing():
            print(f"Command '{cmd}' cannot be used when no song is playing.")
            return False
        return True

    if cmd == 'play':
        if playlist_mode:
            print("Cannot add songs to the playlist. Please type 'close' to exit the playlist mode.")
        else:
            query = " ".join(args)
            if "youtube.com/watch?v=" in query:
                play_song_from_url(query)
            else:
                results = search_youtube(query)
                for i, result in enumerate(results):
                    print(f"{i+1}. {result['title']} ({result['url']})")
                while True:
                    selection = input("Select a song (1-5) or type 'close' to exit: ")
                    if selection.lower() == 'close':
                        print("Song selection closed.")
                        return
                    try:
                        selection = int(selection) - 1
                        if 0 <= selection < len(results):
                            break
                        else:
                            print("Invalid selection. Please enter a number between 1 and 5.")
                    except ValueError:
                        print("Invalid input. Please enter a number between 1 and 5 or type 'close' to exit.")
                
                new_song = results[selection]
                if player and player.is_playing():
                    queue.append(new_song)
                    print("New song added to the queue.")
                else:
                    current_playlist.append(new_song)
                    current_index = len(current_playlist)
                    streaming_url = extract_streaming_url(new_song['url'])
                    if streaming_url:
                        stream_audio_with_vlc(streaming_url)
                        update_last_played(new_song['title'], new_song['url'])
                        display_now_playing(new_song['title'], new_song['url'])
                    else:
                        print(f"Error: Could not stream {new_song['title']}")
    elif cmd == 'pp':
        playlist_url = args[0]
        playlist_name, current_playlist = extract_playlist_videos(playlist_url)
        if current_playlist:
            current_index = 0
            playlist_mode = True
            print(f"Playlist: {playlist_name}")
            for i, song in enumerate(current_playlist):
                print(f"{i+1}. {song['title']} ({song['url']})")
            play_next_song()
        else:
            print("Error: Could not load playlist.")
    elif cmd == 'fav':
        if current_index > 0 and current_index <= len(current_playlist):
            song = current_playlist[current_index - 1]
            add_favorite(song['title'], song['url'])
        else:
            print("No song is currently playing to add to favorites.")
    elif cmd == 'favlist':
        list_favorites()
    elif cmd == 'favr' or cmd == 'fr':
        if len(args) > 0:
            try:
                song_id = int(args[0])
                remove_from_favorites(song_id)
            except ValueError:
                print("Invalid song ID.")
        else:
            print("Please provide a song ID to remove from favorites.")
    elif cmd == 'favplay':
        if len(args) > 0:
            try:
                song_id = int(args[0])
                play_favorite_by_id(song_id)
            except ValueError:
                print("Invalid song ID.")
        else:
            print("Please provide a song ID to play from favorites.")
    elif cmd == 'pf':
        play_favorites()
    elif cmd == 'next':
        if current_playlist or queue:
            if len(args) > 0:
                song_index = int(args[0])
                if 1 <= song_index <= len(current_playlist):
                    play_next_song(song_index)
                else:
                    print("Invalid song number.")
            else:
                play_next_song()
        else:
            print("No next song available.")
    elif cmd == 'previous' or cmd == 'prev':
        if current_playlist or queue:
            play_previous_song()
        else:
            print("No previous song available.")
    elif cmd == 'vol' or cmd == 'volume':
        volume = int(args[0])
        if 0 <= volume <= 100:
            if player:
                old_volume = player.audio_get_volume()
                player.audio_set_volume(volume)
                print(f"Volume set from {old_volume} to {volume}.")
            else:
                print("No song is currently playing to set volume.")
        else:
            print("Volume must be between 0 and 100.")
    elif cmd == 'seek':
        if len(args) > 0:
            try:
                seek_value = int(args[0])
                if is_playing():
                    length = player.get_length() // 1000  # Get length in seconds
                    if 0 <= seek_value <= length:
                        player.set_time(seek_value * 1000)  # Seek in milliseconds
                        print(f"Seeked to {seek_value} seconds.")
                        update_display()
                    else:
                        print(f"Invalid seek time. Please enter a value between 0 and {length} seconds.")
            except ValueError:
                print("Invalid input. Please enter the number of seconds to seek.")
        else:
            print("Please provide the number of seconds to seek. Usage: seek <seconds>")
    elif cmd == 'repeat' or cmd == 'replay':
        if player:
            player.set_time(0)
            player.play()
            print("Song replayed.")
            update_display()
        else:
            print("No song is currently playing to repeat.")
    elif cmd == 'now':
        if current_index > 0 and current_index <= len(current_playlist):
            song = current_playlist[current_index - 1]
            display_now_playing(song['title'], song['url'])
            update_display()
        else:
            print("No song is currently playing.")
    elif cmd == 'pause':
        if player and player.is_playing():
            paused_time = player.get_time()
            player.pause()
            print("Playback paused.")
            update_display()
        else:
            print("No song is currently playing to pause.")
    elif cmd == 'resume':
        if player:
            player.set_time(paused_time)
            player.play()
            print("Playback resumed.")
            update_display()
        else:
            print("No song is currently paused to resume.")
    elif cmd == 'stop':
        if player and player.is_playing():
            player.stop()
            print("Playback stopped.")
            update_display()
        else:
            print("No song is currently playing to stop.")
    elif cmd == 'close':
        if player:
            if player.is_playing():
                player.stop()
            player.release()
            player = None
            media = None
            current_playlist = []
            current_index = 0
            paused_time = 0
            queue = []
            playlist_mode = False
            print("Player closed.")
            update_display()
        else:
            print("No song is currently playing to close.")
    elif cmd == 'playlist' and args[0] == 'restart':
        if current_playlist:
            current_index = 0
            play_next_song()
        else:
            print("Cannot restart. No playlist loaded.")
    elif cmd == 'last':
        play_last_played()
    elif cmd == 'session':
        if player and player.is_playing():
            song = current_playlist[current_index - 1]
            current_time = player.get_time() // 1000
            length = player.get_length() // 1000
            print(f"Currently playing: {song['title']} ({song['url']})")
            print(f"Time: {current_time} seconds / {length} seconds")
        else:
            print("No song is currently playing.")
    elif cmd == 'config':
        print(yaml.dump(config))
    elif cmd == 'help':
        display_help()

if __name__ == "__main__":
    display_logo()
    while True:
        try:
            command = input("> ")
            handle_command(command)
        except Exception as e:
            print(f"An error occurred: {e}")
