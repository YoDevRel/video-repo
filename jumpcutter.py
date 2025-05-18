from contextlib import closing
from PIL import Image
import subprocess
from audiotsm import phasevocoder
from audiotsm.io.wav import WavReader, WavWriter
from scipy.io import wavfile
import numpy as np
import re
import math
import os
import argparse
from pytube import YouTube
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def downloadFile(url):
    try:
        yt = YouTube(url)
        name = yt.streams.first().download()
        newname = name.replace(' ','_')
        os.rename(name,newname)
        return newname
    except Exception as e:
        logging.error(f"Error downloading file from {url}: {e}")
        return None

def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)

def copyFrame(inputFrame,outputFrame,TEMP_FOLDER):
    src = os.path.join(TEMP_FOLDER,"frame{:06d}.jpg".format(inputFrame+1))
    dst = os.path.join(TEMP_FOLDER,"newFrame{:06d}.jpg".format(outputFrame+1))
    if not os.path.isfile(src):
        return False
    shutil.copyfile(src, dst)
    if outputFrame%20 == 19:
        logging.info(f"{outputFrame+1} time-altered frames saved.")
    return True

def inputToOutputFilename(filename):
    dotIndex = filename.rfind(".")
    return filename[:dotIndex]+"_ALTERED"+filename[dotIndex:]

def createPath(s):
    try:
        os.makedirs(s, exist_ok=True)
    except OSError as e:
        logging.error(f"Creation of the directory {s} failed: {e}")
        return False
    return True

def deletePath(s): # Dangerous! Watch out!
    try:
        shutil.rmtree(s,ignore_errors=True)
        logging.info(f"Successfully deleted {s}")
    except OSError as e:
        logging.error(f"Deletion of the directory {s} failed: {e}")

parser = argparse.ArgumentParser(description='Modifies a video file to play at different speeds when there is sound vs. silence.')
parser.add_argument('--input_file', type=str,  help='the video file you want modified', default="original-video.mp4")
parser.add_argument('--url', type=str, help='A youtube url to download and process')
parser.add_argument('--output_file', type=str, default="shortened_video.mp4", help="the output file. (optional. if not included, it'll just modify the input file name)")
parser.add_argument('--silent_threshold', type=float, default=0.03, help="the volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume)")
parser.add_argument('--sounded_speed', type=float, default=1.00, help="the speed that sounded (spoken) frames should be played at. Typically 1.")
parser.add_argument('--silent_speed', type=float, default=5.00, help="the speed that silent frames should be played at. 999999 for jumpcutting.")
parser.add_argument('--frame_margin', type=float, default=1, help="some silent frames adjacent to sounded frames are included to provide context. How many frames on either the side of speech should be included? That's this variable.")
parser.add_argument('--sample_rate', type=float, default=44100, help="sample rate of the input and output videos")
parser.add_argument('--frame_rate', type=float, default=30, help="frame rate of the input and output videos. optional... I try to find it out myself, but it doesn't always work.")
parser.add_argument('--frame_quality', type=int, default=3, help="quality of frames to be extracted from input video. 1 is highest, 31 is lowest, 3 is the default.")

args = parser.parse_args()

frameRate = args.frame_rate
SAMPLE_RATE = args.sample_rate
SILENT_THRESHOLD = args.silent_threshold
FRAME_SPREADAGE = args.frame_margin
NEW_SPEED = [args.silent_speed, args.sounded_speed]
INPUT_FILE = args.input_file
URL = args.url
FRAME_QUALITY = args.frame_quality

if URL is not None:
    INPUT_FILE = downloadFile(URL)
    if INPUT_FILE is None:
        logging.error("Failed to download video from URL. Aborting.")
        exit()
elif not os.path.exists(INPUT_FILE):
    logging.error(f"Input file '{INPUT_FILE}' not found. Aborting.")
    exit()
    
OUTPUT_FILE = args.output_file if args.output_file else inputToOutputFilename(INPUT_FILE)

TEMP_FOLDER = "TEMP"
AUDIO_FADE_ENVELOPE_SIZE = 400 # smooth out transitiion's audio by quickly fading in/out (arbitrary magic number whatever)

if not createPath(TEMP_FOLDER):
    logging.error(f"Could not create temporary directory '{TEMP_FOLDER}'. Aborting.")
    exit()

# Extract frames from video
logging.info(f"Extracting frames from {INPUT_FILE}...")
command = f"ffmpeg -i {INPUT_FILE} -qscale:v {FRAME_QUALITY} {os.path.join(TEMP_FOLDER,'frame%06d.jpg')} -hide_banner"
try:
    subprocess.call(command, shell=True)
except Exception as e:
    logging.error(f"Error extracting frames: {e}")
    deletePath(TEMP_FOLDER)
    exit()

# Extract audio from video
logging.info(f"Extracting audio from {INPUT_FILE}...")
command = f"ffmpeg -i {INPUT_FILE} -ab 160k -ac 2 -ar {SAMPLE_RATE} -vn {os.path.join(TEMP_FOLDER,'audio.wav')}"
try:
    subprocess.call(command, shell=True)
except Exception as e:
    logging.error(f"Error extracting audio: {e}")
    deletePath(TEMP_FOLDER)
    exit()

# Get video parameters
logging.info(f"Getting video parameters from {INPUT_FILE}...")
command = f"ffmpeg -i {INPUT_FILE} 2>&1"
params_file = os.path.join(TEMP_FOLDER, "params.txt")
try:
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    with open(params_file, "w") as f:
        f.write(result.stderr)
except Exception as e:
    logging.error(f"Error getting video parameters: {e}")
    deletePath(TEMP_FOLDER)
    exit()

try:
    sampleRate, audioData = wavfile.read(os.path.join(TEMP_FOLDER,"audio.wav"))
    audioSampleCount = audioData.shape[0]
    maxAudioVolume = getMaxVolume(audioData)
except Exception as e:
    logging.error(f"Error reading audio data: {e}")
    deletePath(TEMP_FOLDER)
    exit()

try:
    with open(params_file, 'r') as f:
        pre_params = f.read()
    params = pre_params.split('\n')
    for line in params:
        m = re.search('Stream #.*Video.* ([0-9]*) fps',line)
        if m is not None:
            frameRate = float(m.group(1))
            break
except Exception as e:
    logging.error(f"Error reading frame rate from parameters file: {e}")
    deletePath(TEMP_FOLDER)
    exit()

samplesPerFrame = sampleRate/frameRate
audioFrameCount = int(math.ceil(audioSampleCount/samplesPerFrame))
hasLoudAudio = np.zeros((audioFrameCount))

for i in range(audioFrameCount):
    start = int(i*samplesPerFrame)
    end = min(int((i+1)*samplesPerFrame),audioSampleCount)
    audiochunks = audioData[start:end]
    maxchunksVolume = float(getMaxVolume(audiochunks))/maxAudioVolume
    if maxchunksVolume >= SILENT_THRESHOLD:
        hasLoudAudio[i] = 1

chunks = [[0,0,0]]
shouldIncludeFrame = np.zeros((audioFrameCount))
for i in range(audioFrameCount):
    start = int(max(0,i-FRAME_SPREADAGE))
    end = int(min(audioFrameCount,i+1+FRAME_SPREADAGE))
    shouldIncludeFrame[i] = np.max(hasLoudAudio[start:end])
    if (i >= 1 and shouldIncludeFrame[i] != shouldIncludeFrame[i-1]): # Did we flip?
        chunks.append([chunks[-1][1],i,shouldIncludeFrame[i-1]])

chunks.append([chunks[-1][1],audioFrameCount,shouldIncludeFrame[i-1]])
chunks = chunks[1:]

outputAudioData = np.zeros((0,audioData.shape[1]))
outputPointer = 0

lastExistingFrame = None
for chunk in chunks:
    audioChunk = audioData[int(chunk[0]*samplesPerFrame):int(chunk[1]*samplesPerFrame)]
    
    sFile = os.path.join(TEMP_FOLDER,"tempStart.wav")
    eFile = os.path.join(TEMP_FOLDER,"tempEnd.wav")
    wavfile.write(sFile,SAMPLE_RATE,audioChunk)
    with WavReader(sFile) as reader:
        with WavWriter(eFile, reader.channels, reader.samplerate) as writer:
            tsm = phasevocoder(reader.channels, speed=NEW_SPEED[int(chunk[2])])
            tsm.run(reader, writer)
    try:
        _, alteredAudioData = wavfile.read(eFile)
        leng = alteredAudioData.shape[0]
        endPointer = outputPointer+leng
        outputAudioData = np.concatenate((outputAudioData,alteredAudioData/maxAudioVolume))

        if leng < AUDIO_FADE_ENVELOPE_SIZE:
            outputAudioData[outputPointer:endPointer] = 0 # audio is less than 0.01 sec, let's just remove it.
        else:
            premask = np.arange(AUDIO_FADE_ENVELOPE_SIZE)/AUDIO_FADE_ENVELOPE_SIZE
            mask = np.repeat(premask[:, np.newaxis],2,axis=1) # make the fade-envelope mask stereo
            outputAudioData[outputPointer:outputPointer+AUDIO_FADE_ENVELOPE_SIZE] *= mask
            outputAudioData[endPointer-AUDIO_FADE_ENVELOPE_SIZE:endPointer] *= 1-mask

        startOutputFrame = int(math.ceil(outputPointer/samplesPerFrame))
        endOutputFrame = int(math.ceil(endPointer/samplesPerFrame))
        for outputFrame in range(startOutputFrame, endOutputFrame):
            inputFrame = int(chunk[0]+NEW_SPEED[int(chunk[2])]*(outputFrame-startOutputFrame))
            didItWork = copyFrame(inputFrame,outputFrame,TEMP_FOLDER)
            if didItWork:
                lastExistingFrame = inputFrame
            else:
                copyFrame(lastExistingFrame,outputFrame,TEMP_FOLDER)

        outputPointer = endPointer
    except Exception as e:
        logging.error(f"Error processing audio chunk: {e}")
        continue

wavfile.write(os.path.join(TEMP_FOLDER,"audioNew.wav"),SAMPLE_RATE,outputAudioData)

# Stitch video and audio together
logging.info(f"Stitching video and audio together to create {OUTPUT_FILE}...")
command = f"ffmpeg -framerate {frameRate} -i {os.path.join(TEMP_FOLDER,'newFrame%06d.jpg')} -i {os.path.join(TEMP_FOLDER,'audioNew.wav')} -strict -2 {OUTPUT_FILE}"
try:
    subprocess.call(command, shell=True)
except Exception as e:
    logging.error(f"Error stitching video and audio: {e}")
    deletePath(TEMP_FOLDER)
    exit()

# Clean up temporary files
logging.info(f"Cleaning up temporary files in {TEMP_FOLDER}...")
deletePath(TEMP_FOLDER)

logging.info(f"Successfully created {OUTPUT_FILE}")
