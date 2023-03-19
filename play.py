from yt_dlp import YoutubeDL
import argparse
from demucs.apply import apply_model
from demucs.pretrained import get_model, DEFAULT_MODEL
from demucs.audio import AudioFile, save_audio
from pathlib import Path
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
from mido import MidiFile
from json import load
from bluetooth import BluetoothSocket, RFCOMM, discover_devices, lookup_name

default_path = Path('./temp')
youtube_temp = default_path / 'youtube.mp3'
midi_temp = default_path / 'output.mid'

def connect(bluetooth_config, sock):
    with open(bluetooth_config, 'r') as f:
        data = load(f)
        port = 1
        if "address" in data:
            sock.connect((data["address"], port))
        elif "name" in data:
            nearby_devices = discover_devices()
            for addr in nearby_devices:
                if data["name"] == lookup_name(addr):
                    print("found target bluetooth device with address ", addr)
                    sock.connect((data["address"], port))
                    break

def reset(path_list):
    for path in path_list:
        if path is not None and path.relative_to(default_path):
            if path.is_dir():
                for child in path.iterdir():
                    child.unlink()
                path.rmdir()
            else:
                path.unlink()

def download_youtube_link(url):
    options={
        'format':'worstaudio/worst',
        'keepvideo':False,
        'outtmpl': str(youtube_temp),
    }
    with YoutubeDL(options) as ydl:
        ydl.download([url])

def seperate(args_stem, start, duration):
    model = get_model(name=DEFAULT_MODEL)
    model.cpu()
    model.eval()
    track = youtube_temp
    wav = AudioFile(track).read(
        seek_time = start,
        duration = duration,
        streams=0,
        samplerate=model.samplerate,
        channels=model.audio_channels
    )
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    sources = apply_model(model, wav[None], device="cpu", shifts=1,
                            split=True, overlap=0.25, progress=True,
                            num_workers=0)[0]
    sources = sources * ref.std() + ref.mean()

    kwargs = {
        'samplerate': model.samplerate,
        'bitrate': 320,
        'clip': "rescale",
        'as_float': False,
        'bits_per_sample': 16,
    }
    if args_stem is None:
        for source, name in zip(sources, model.sources):
            stem = default_path / (name + '.wav')
            save_audio(source, str(stem), **kwargs)
    else:
        sources = list(sources)
        stem = default_path / (args_stem + '.wav')
        save_audio(sources.pop(model.sources.index(args_stem)), str(stem), **kwargs)

def play():
    parser = argparse.ArgumentParser("self-playing-bass",
                                    description="play any youtube link's baseline.")
    parser.add_argument("url", type = str, default = None, help = "Youtube url to audio source.")
    parser.add_argument("--reset", "-r", type = Path, default = [], help = "reset selected stored temporaries.", nargs = '*')
    parser.add_argument("--stem", "-s", default = None, help = "Select which stem to use for demucs seperation.")
    parser.add_argument("--start", type = float, default = 0.0, help = "Where the sample should start from.")
    parser.add_argument("--duration", "-d", type = float, default = 30.0, help = "Number of seconds to sample after (start).")
    parser.add_argument("--bluetooth", "-b", default = 'blt_config.json', help = "Bluetooth configuration file path.")
    args = parser.parse_args()

    # Cleans directory
    reset(args.reset)
    default_path.mkdir(parents=True, exist_ok=True)
    print("Cleaning done...")
    
    # Downloads url from youtube
    if not youtube_temp.exists():
        download_youtube_link(args.url)
    print("Downloading done...")

    # # Seperates url into components
    if args.stem is None:
        if any(map(lambda x: not (default_path / (x + '.wav')).exists(), ['bass', 'vocals', 'drums', 'other'])):
            seperate(None, args.start, args.duration)
    elif not (default_path / (args.stem + '.wav')).exists():
        seperate(args.stem, args.start, args.duration)
    print("Seperation done...")

    # Creates midi file from components
    if not midi_temp.exists():
        if args.stem is None:
            args.stem = 'bass'
        _, midi_data, _ = predict(str(default_path / (args.stem + '.wav')))
        midi_data.write(str(midi_temp))
    print("Prediction done...")

    # Connect to raspberry pi
    sock = BluetoothSocket(RFCOMM)
    connect(args.bluetooth, sock)
    print("Connection done...")

    # Send messages to raspberry pi
    for msg in MidiFile(str(midi_temp)).play():
        sock.send(str(msg))
    sock.close()

if __name__ == "__main__":
    play()
