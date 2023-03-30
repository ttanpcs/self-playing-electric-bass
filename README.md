# self-playing-electric-bass

### Installation
1. Setup a virtual environment named venv with `python -m venv venv`
2. Install ffmpeg using https://phoenixnap.com/kb/ffmpeg-windows
3. `pip install PySoundFile demucs basic-pitch yt_dlp git+https://github.com/pybluez/pybluez.git#egg=pybluez`
4. Restart computer
5. Fill out blt_config.json
6. Go into settings and connect bluetooth to pi, you may havfe to use bluetoothctl in pi to authorize the request
7. ssh into raspberry pi and start bluetooth serverside code
