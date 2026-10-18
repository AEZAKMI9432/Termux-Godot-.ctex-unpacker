# Godot cmd .ctex texture unpacker

**Create by Aeza Lab.**

A dependency-free Python tool that extracts textures from Godot engine
`.ctex` / `.stex` containers. It scans its own folder (including
subfolders), shows a numbered list of found files and unpacks the
selected ones back to plain **PNG** or **WebP** images.

---

## English

### What it does

Godot does not store plain PNG files in an exported game. On import each
texture is packed into an internal container:

<div class="md-table-wrap"><div class="md-table-scroll"><table class="md-table"><thead><tr><th>Source file</th><th>Container</th><th>Internal image</th></tr></thead><tbody><tr><td>`.png` (lossless import)</td><td>`.ctex` (Godot 4) / `.stex` (Godot 3)</td><td>full PNG</td></tr><tr><td>`.png` (lossy import)</td><td>`.ctex` / `.stex`</td><td>WebP</td></tr><tr><td>`.png` (VRAM compression)</td><td>`.ctex` / `.stex`</td><td>ETC2/ASTC/S3TC — **not supported**</td></tr></tbody></table></div></div>
This tool finds the PNG/WebP signature inside each container and writes
it out as a normal image file. No dependencies, standard library only.

### Requirements

- Python **3.9 or newer**
- Any OS: Windows, Linux, macOS, Android (Termux)

### Installing Python and run script

**Termux**
1. Enter command: pkg install python
2. After installing Python, enter the command: python extract_ctex.py
3. Select the desired action in the program 
