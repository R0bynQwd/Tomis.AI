# app.py
import os
import json
import uuid
from flask import Flask, request, jsonify
from google.cloud import storage, secretmanager, speech_v1p1beta1 as speech
from datetime import datetime, timedelta

PROJECT = os.environ.get("GCP_PROJECT", "ro-igpr-speech-to-text")
REGION = os.environ.get("REGION", "europe-west1")
BUCKET = os.environ.get("BUCKET_PUBLIC", "tomis-ai-public")
SPEECH_CLIENT = speech.SpeechClient()
STORAGE_CLIENT = storage.Client()
SM_CLIENT = secretmanager.SecretManagerServiceClient()

app = Flask(__name__)

def upload_fileobj_to_bucket(fileobj, dest_blob_name):
    bucket = STORAGE_CLIENT.bucket(BUCKET)
    blob = bucket.blob(dest_blob_name)
    blob.upload_from_file(fileobj)
    # make it readable by service account; bucket may be public or private
    return f"gs://{BUCKET}/{dest_blob_name}"

@app.route('/upload', methods=['POST'])
def upload_audio():
    """
    Expects multipart/form-data with file field 'audio'
    Returns: { job_name, gcs_uri }
    """
    f = request.files.get('audio')
    if not f:
        return jsonify({"error":"no file"}), 400
    ext = os.path.splitext(f.filename)[1] or ".wav"
    dest = f"uploads/{uuid.uuid4().hex}{ext}"
    gcs_uri = upload_fileobj_to_bucket(f, dest)
    return jsonify({"ok": True, "gcs_uri": gcs_uri}), 200

@app.route('/transcribe', methods=['POST'])
def transcribe_start():
    """
    Start async transcription with diarization + auto language detection.
    POST body: {"gcs_uri":"gs://.../file.wav", "min_speakers":1, "max_speakers":4}
    Returns operation name
    """
    body = request.get_json() or {}
    gcs_uri = body.get("gcs_uri")
    if not gcs_uri:
        return jsonify({"error":"gcs_uri required"}), 400

    min_sp = int(body.get("min_speakers", 1))
    max_sp = int(body.get("max_speakers", 4))

    # Configure recognition features (use latest beta features as necessary)
    config = {
        "encoding": speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        "language_code": "",  # leave empty for auto detection below
        "enable_automatic_punctuation": True,
        "enable_word_time_offsets": True,
        "diarization_config": {
            "enable_speaker_diarization": True,
            "min_speaker_count": min_sp,
            "max_speaker_count": max_sp,
        }
    }

    # Auto language detection: supply a list of possible language_codes
    # If you want full auto-detect from speech doc: use `speech.RecognitionConfig.auto_decoding_config` or use V2 API features.
    # Here we use alternative_language_codes as an approximation:
    config["alternative_language_codes"] = ["ro-RO","en-US"]  # adapt list to expected languages

    audio = {"uri": gcs_uri}
    request_proto = {
        "config": config,
        "audio": audio
    }

    operation = SPEECH_CLIENT.long_running_recognize(request=request_proto)
    return jsonify({"operation_name": operation.operation.name}), 200

@app.route('/transcribe/status', methods=['GET'])
def transcribe_status():
    op_name = request.args.get('op')
    if not op_name:
        return jsonify({"error":"op param required"}), 400
    op = SPEECH_CLIENT._transport.operations_client.get_operation(op_name)
    return jsonify({"done": op.done}), 200

@app.route('/transcribe/result', methods=['GET'])
def transcribe_result():
    op_name = request.args.get('op')
    if not op_name:
        return jsonify({"error":"op param required"}), 400
    op = SPEECH_CLIENT._transport.operations_client.get_operation(op_name)
    if not op.done:
        return jsonify({"done": False}), 200
    resp = speech.types.LongRunningRecognizeResponse()
    op.response.Unpack(resp)
    # resp has results with words + speaker tags if diarization enabled
    # Convert to SRT
    srt = convert_response_to_srt(resp)
    # store SRT to bucket
    out_name = f"transcripts/{uuid.uuid4().hex}.srt"
    bucket = STORAGE_CLIENT.bucket(BUCKET)
    blob = bucket.blob(out_name)
    blob.upload_from_string(srt, content_type='text/plain')
    return jsonify({"done": True, "srt_gs_uri": f"gs://{BUCKET}/{out_name}"}), 200

def convert_response_to_srt(resp):
    """
    Convert Speech-to-Text response to SRT using word_time_offsets and speaker_tag.
    This is a simple implementation that groups by speaker & time windows.
    """
    entries = []
    index = 1
    # iterate through results / words
    # The exact structure depends on client version; adjust indexing accordingly.
    for result in resp.results:
        # result.alternatives[0].words -> each word has start_time, end_time, word, speaker_tag
        if not result.alternatives:
            continue
        words = result.alternatives[0].words
        # group contiguous words by speaker
        if not words:
            continue
        curr_speaker = words[0].speaker_tag if hasattr(words[0], 'speaker_tag') else 1
        curr_start = words[0].start_time
        text_buf = []
        start_time = curr_start
        for w in words:
            speaker = getattr(w, "speaker_tag", curr_speaker)
            if speaker != curr_speaker:
                # flush buffer
                end_time = prev_end
                srt_block = make_srt_block(index, start_time, end_time, f"Speaker {curr_speaker}: " + " ".join(text_buf))
                entries.append(srt_block)
                index += 1
                # reset
                text_buf = []
                curr_speaker = speaker
                start_time = w.start_time
            text_buf.append(w.word)
            prev_end = w.end_time
        # flush last buffer
        srt_block = make_srt_block(index, start_time, prev_end, f"Speaker {curr_speaker}: " + " ".join(text_buf))
        entries.append(srt_block)
        index += 1
    return "\n\n".join(entries)

def make_srt_block(idx, start_proto_ts, end_proto_ts, text):
    # start_proto_ts is protobuf Duration / Timestamp -> has seconds and nanos
    def fmt(ts):
        s = ts.seconds + ts.nanos/1e9
        # convert seconds float to hh:mm:ss,ms
        hours = int(s // 3600)
        minutes = int((s % 3600) // 60)
        seconds = int(s % 60)
        millis = int((s - int(s)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    return f"{idx}\n{fmt(start_proto_ts)} --> {fmt(end_proto_ts)}\n{text}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
