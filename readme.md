# baywatch

[baywatch](https://github.com/hdb/baywatch) is a TUI for The Pirate Bay built using [Textual](https://github.com/Textualize/textual). It uses [peerflix](https://github.com/mafintosh/peerflix) to stream torrents and [Transmission](https://transmissionbt.com/) to download torrents.

## Install

Optionally install peerflix:

```bash
npm install -g peerflix
```

Optionally install Transmission: [https://transmissionbt.com/download/](https://transmissionbt.com/download/)

Install baywatch via pip:

```bash
pip install bay-watch
```

## Demo

[![asciicast](https://asciinema.org/a/0wqCm9YIv31KUtH1r377DoUEB.svg)](https://asciinema.org/a/0wqCm9YIv31KUtH1r377DoUEB)

## Usage

Launch baywatch

```bash
baywatch
```

To open the configuration editor:

```bash
baywatch -c
```

To output the app log:

```bash
baywatch -l out.log
```

### Streaming Media

By default `play` uses [mpv](https://mpv.io) to handle peerflix streams and open a file selection dialog when multiple files are present in the torrent. To change this, open the config editor using `baywatch -c` and change `Play` and `Play Multifile`.

For instance, to set peerflix to use VLC and to play all files in a multifile torrent (e.g., like an album):

`Play`:

```bash
peerflix '{}' --vlc
```

`Play Multifile`:

```bash
peerflix '{}' --vlc -a
```

See [peerflix documentation](https://github.com/mafintosh/peerflix#usage) for more details.

### Transmission

On `download`, baywatch attempts to connect to Transmission or transmission-daemon. baywatch will try to open `transmission-gtk` if it is unable to find an running Transmission instance. This can be turned off or changed to another transmission interface by setting the `Command (Transmission)` or `Try Open (Transmission)` configuration variables.

## Disclaimer

baywatch is made for educational purposes for downloading legal torrents.
