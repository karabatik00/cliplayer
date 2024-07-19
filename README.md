# CLI Player

CLI Player is a command-line music player that allows you to play music from YouTube. It supports various commands to manage playlists, favorites, and playback controls.

## Features

- Search and play songs from YouTube
- Add and manage favorite songs
- Play songs from YouTube playlists
- Control playback (play, pause, resume, stop, next, previous)
- Set volume and seek within the song
- Display currently playing song information

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/karabatik00/cliplayer
    cd cliplayer
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Set up your YouTube API key:
    ```python
    # Replace 'YOUR_YOUTUBE_API_KEY' with your actual YouTube API key.
    ```

## Usage

1. Run the CLI Player:
    ```bash
    python main.py
    ```

2. Use the following commands to control the player:

    - `play <song name or YouTube URL>`
    - `pp <playlist URL>`
    - `fav`
    - `favlist`
    - `favr <song ID> or fr <song ID>`
    - `favplay <song ID>`
    - `pf`
    - `next [<number>]`
    - `prev or previous`
    - `vol <volume>`
    - `seek <seconds>`
    - `repeat or replay`
    - `now`
    - `pause`
    - `resume`
    - `stop`
    - `close`
    - `playlist restart`
    - `last`
    - `session`
    - `config`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
