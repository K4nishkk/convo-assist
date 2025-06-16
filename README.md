## Gemini exceptions

*   Code: 1007
    Reason: API key not valid. Please pass a valid API key.

*   Code: 1011
    Reason: You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: h
    Reason: keepalive ping timeout; no close frame received

## Working of GeminiSession:

* streamer = GeminiSession()
object is created, __init__ function is run

* streamer.open_audio_stream() is run

* streamer.connect_to_session is run
with paramter same_key_id = false
it gets a new key_id from db.getKeyId()
connects to session (with first or new ids)
inserts keyLog

if _recv_loop_running -flag if false
runs the _start_receiver() function
returns key_id

* streamer._start_receiver() is run
it checks if _recv_task is running

if not
runs await _receiver_loop() function
now waits for it to end

* streamer._receiver_loop()
if (_recv_loop_running == true) return
run session.receive() context manager
listen for incoming messages
put them in queue

if (message == go_away) then terminate session and return
if (exeption occurs) ,,    ,,

before returning
set _recv_loop_running to false

after this _start_receiver function which has a loop
will try to reconnect to gemini websocket with same key_id
and run the receiver loop again