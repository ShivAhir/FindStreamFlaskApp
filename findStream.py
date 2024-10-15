from collections import defaultdict
from flask import Blueprint, render_template, request # type: ignore
import json
import os
import subprocess

# this function takes a file and scrolls over all the streams in it and returns in a format of a list
def get_codec_info(file_path):
    try:
        ffprobe_cmd = [
            '/usr/bin/ffprobe',
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
                        'resolution': (
                                'UHD' if stream['width'] >= 3840 and stream['height'] >= 2160 else
                                'HD' if stream['width'] >= 1280 and stream['height'] >= 720 else
                                'SD'
                            ),
                        'frame_rate': stream['r_frame_rate'],
                        'pix_fmt': stream['pix_fmt'],
                    })
            elif stream['codec_type'] == 'audio':
                video_info.append({
                    'codec_type': stream['codec_type'],
                    'codec_name': stream['codec_name'],
                    'bits_per_sample': stream.get('bits_per_sample', 'N/A') 
                })
            elif stream['codec_type'] == 'data':
                video_info.append({
                    'id': stream['id'],
                    'codec_type': stream['codec_type'],
                    'codec_name': stream['codec_name'],
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

# this function will add a count of number of channels
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

#Create a blueprint
lookUpStreams_bp = Blueprint('lookUpStreams', __name__)

@lookUpStreams_bp.route('/lookupStreams', methods = ['POST'])
def filter():
    return render_template('lookupStreams.html')

@lookUpStreams_bp.route('/lookupStreams/results', methods = ['POST', 'GET'])
def filterResults():
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
                codec_name = request.form.get('a_codecName', '').lower().strip()
            except KeyError:
                return "Missing form field: a_codecName", 400
        elif codec_type == 'video':
            try:
                codec_name = request.form.get('v_codecName','').lower().strip()
                resolution = request.form.get('v_resolution', '').upper().strip()
                pix_format = request.form.get('v_pixelFmt', '').lower().strip()
            except KeyError as e:
                return f"Missing form field: {e}", 400
        elif codec_type == 'subtitle':
            try:
                codec_name = request.form.get('s_codecName', '').lower().strip()
            except KeyError:
                return "Missing form field: s_codecName", 400     
        elif codec_type == 'data':
            try:
                codec_name = request.form.get('d_type', '').lower().strip()
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
                        elif info.get('codec_type') == 'data':
                            listOfStreams.append({
                                        'stream_name': filename,
                                        'id': info['id'],
                                        'codec_type': info['codec_type'],
                                        'codec_name': info['codec_name'],
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
                    if codec_name and stream['codec_name'] != codec_name:
                        continue
                    if resolution and stream['resolution'] != resolution:
                        continue
                    if pix_format and stream['pix_fmt'] != pix_format:
                        continue
                    filtered_streams.append(stream)
                elif codec_type == 'audio':
                    print('inside audio')
                    if 'bits_per_sample' in stream and stream['codec_name'] == codec_name:
                        filtered_streams.append(stream)
                elif codec_type == 'subtitle':
                    print('inside sub')
                    if stream['codec_name'] == codec_name:
                        filtered_streams.append(stream)
                elif codec_type == 'data':
                    print('inside data')
                    if stream['codec_name'] == codec_name:
                        filtered_streams.append(stream)
        return render_template('lookupStreams.html', streams=filtered_streams, directory=directory)
    return render_template('lookupStreams.html', streams=[])
