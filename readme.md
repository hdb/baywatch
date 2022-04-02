# baywatch

[baywatch](https://github.com/hdb/baywatch) is a TUI for The Pirate Bay built using [Textual](https://github.com/Textualize/textual). It uses [Peerflix](https://github.com/mafintosh/peerflix) to stream torrents and [Transmission](https://transmissionbt.com/) to download.

## Install


```bash
# install dependencies
pip install git+https://github.com/Cvaniak/TextualListViewUnofficial.git@52ea0f2
npm install -g peerflix

# install via pip
pip install bay-watch
```

### Transmission Install (optional)

[https://transmissionbt.com/download/](https://transmissionbt.com/download/)

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

To output the app log (e.g., for development):

```bash
baywatch -l out.log
```

### Streaming Media

`play` uses [mpv](https://mpv.io) to handle peerflix streams and open a file selection dialog when multiple files are present in the torrent. To change this, for instance, to vlc and default to playing all files (e.g., like an album), open the config editor using `baywatch -c` and set `Play` to:

```bash
peerflix '{}' --vlc
```

and `Play Multifile` to:

```bash
peerflix '{}' --vlc -a
```

See [peerflix documentation](https://github.com/mafintosh/peerflix#usage) for more details.

### Transmission

On `download`, baywatch attempts to connect to Transmission app or daemon. baywatch will try to open `transmission-gtk` if it is unable to find an running transmission instance. This can be turned off or changed to another transmission interface by setting the `Command (Transmission)` or `Try Open (Transmission)` variables.

## Disclaimer

baywatch is made for educational purposes for downloading legal torrents.
