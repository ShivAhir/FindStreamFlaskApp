from flask import Flask, render_template, request, redirect, url_for
from collections import defaultdict
import subprocess
import json
import os
import logging
import re

app = Flask(__name__)

def currentStreams():
    currentStreams = os.popen('ps -o pid,cmd --ppid 1 | grep tsplay')
    output = currentStreams.read()
    outputList = output.split('\n')
    finalOutput = outputList.pop(0)
    print(outputList)
    finalList = []
    for i in outputList:
        app.logger.debug(i)
        if re.search('-loop -maxnowait', i):
            finalList.append(i)
    json_data = json.dumps(finalList, indent=4)
    data = json.loads(json_data)
    last_entry = data[-1]
    parts = last_entry.split()
    ip_address = parts[3]
    ip_parts = ip_address.split('.')
    ip_parts[-1] = str(int(ip_parts[-1]) + 1)
    new_ip_address = '.'.join(ip_parts)
    return new_ip_address


def get_codec_info(file_path):
    try:
        ffprobe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-print_format', 'json',
            '-show_streams',
            file_path
        ]
        result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        info = json.loads(result.stdout)

        video_info = []
        for stream in info['streams']:
            if stream['codec_type'] == 'video':    
                if 'codec_name' in stream and 'width' in stream and 'height' in stream and 'r_frame_rate' in stream:
                    video_info.append({
                        'codec_type': stream['codec_type'],
                        'codec_name': stream['codec_name'],
                        'width': stream["width"],
                        'height': stream["height"],
                        'resolution': 'HD' if stream['width'] >= 1280 and stream['height'] >= 720 else 'SD',
                        'frame_rate': stream['r_frame_rate'],
                        'pix_fmt': stream['pix_fmt'],
                    })
            elif stream['codec_type'] == 'audio':
                video_info.append({
                    'codec_type': stream['codec_type'],
                    'codec_name': stream['codec_name'],
                    'bits_per_sample': stream['bits_per_sample']
                })
            elif stream['codec_type'] == 'subtitle':
                video_info.append({
                    'codec_type': stream['codec_type'],
                    'codec_name': stream['codec_name']
                })
        return video_info

    except Exception as e:
        print(f"An error occurred while processing file {file_path}: {e}")
        return None

def addNumberOfChannels(streams):
    channel = defaultdict(int)
    
    for entry in streams:
        key = tuple(sorted(entry.items()))
        channel[key] += 1
    result = []
    for key, count in channel.items():
        entry_dict = dict(key)
        entry_dict['channel'] = count
        result.append(entry_dict)
    return result

@app.route('/lookupStreams', methods = ['POST'])
def filter():
    return render_template('findStream.html')

@app.route('/', methods = ['GET','POST'])
def filter():
    if request.method == 'POST':
        # try and catch blocks to see if the values entered or selected on the form are accessible or not
        try:
            directory = request.form['directory']
            codec_type = request.form['codec_type'].lower().strip()
        except KeyError as e:
            return f"Missing form field: {e}", 400

        listOfStreams = []

        if codec_type == 'audio':
            try:
                codec_name = request.form['a_codecName'].lower().strip()
            except KeyError:
                return "Missing form field: a_codecName", 400
        elif codec_type == 'video':
            try:
                codec_name = request.form['v_codecName'].lower().strip()
                resolution = request.form['v_resolution'].upper().strip()
                pix_format = request.form['v_pixelFmt'].lower().strip()
            except KeyError as e:
                return f"Missing form field: {e}", 400
        elif codec_type == 'subtitle':
            try:
                codec_name = request.form['s_codecName'].lower().strip()
            except KeyError:
                return "Missing form field: s_codecName", 400
            
        for filename in os.listdir(directory):
            if filename.endswith('.ts'):
                file_path = os.path.join(directory, filename)
                video_info = get_codec_info(file_path)
                if video_info:
                    for info in video_info:
                        if info['codec_type'] == 'audio':
                            if info['codec_name'] == codec_name:
                                listOfStreams.append({
                                        'stream_name': filename,
                                        'codec_type': info['codec_type'],
                                        'codec_name': info['codec_name'],
                                        'bits_per_sample': info['bits_per_sample'],
                                })
                        elif info.get('codec_type') == 'video':
                            listOfStreams.append({
                                        'stream_name': filename,
                                        'codec_type': info['codec_type'],
                                        'codec_name': info['codec_name'],
                                        'resolution': info['resolution'],
                                        'frame_rate': info['frame_rate'],
                                        'pix_fmt': info['pix_fmt'],
                                    })
                        else:
                            listOfStreams.append({
                                        'stream_name': filename,
                                        'codec_type': info['codec_type'],
                                        'codec_name': info['codec_name'],
                                    })

        result = addNumberOfChannels(listOfStreams)
        filtered_streams = []
        if result:
            for stream in result:
                if codec_type == 'video':  
                    if stream['codec_name'] == codec_name and stream['resolution'] == resolution and stream['pix_fmt'] == pix_format:
                        filtered_streams.append(stream)
                elif codec_type == 'audio':
                    if 'bits_per_sample' in stream and stream['codec_name'] == codec_name:
                        filtered_streams.append(stream)
                elif codec_type == 'subtitle':
                    if stream['codec_name'] == codec_name:
                        filtered_streams.append(stream)
        return render_template('findStream.html', streams=filtered_streams)
    return render_template('findStream.html', streams=[])

@app.route('/play_stream', methods = ['POST'])
def playStream():
    data = request.get_json()
    streamName = data.get('stream_name')
    directory = data.get('directory')
    portNumber = '1234'
    multicastAddress = getMulticastAddress()
    os.system('tsplay '+ directory +'/'+ streamName +' '+ multicastAddress +':' + portNumber + ' -loop -maxnowait 240 -i 10.10.179.200 &')
    return jsonify({"message": f"Playing stream: {streamName} from {directory} with Multicast: {multicastAddress} on Port: {portNumber}"})

if __name__ == '__main__':
    app.run(debug=True)
