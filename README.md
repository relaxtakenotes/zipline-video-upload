# zipline-video-upload
 Handy tool for uploading big videos on a zipline sharex server

I was tired of having to compress my clips using handbrake manually and then having to upload them through the web dashboard.

This script automatically merges all audio tracks into one (main + microphone, because that's how I set up my shadowplay. handbrake can't merge them itself afaik), compresses the video through handbrake and then uploads it to your configured zipline server using chunking, so videos bigger than the cloudflare's POST limit will still get uploaded.

To use this, you need to have handbrakecli, ffmpeg, ffprobe all defined in your PATH; install pyperclip and httpx through pip; then configure the token and domain in the script itself; put the script somewhere handy, maybe define it in PATH too so you can quickly access it through the WIN+R keybind; use it, profit.

If you have an NVIDIA gpu you don't need to change the preset.json file, but if you're rocking an AMD gpu, you'll need to open it in handbrake and change the encoder to whatever AMD has.

Zipline in question: https://github.com/diced/zipline