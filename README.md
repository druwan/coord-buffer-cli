# Coords Buffer

Fetches geojson data based on LFV echarts and returns new buffer coordiantes based on user input distance (nautical miles).

## Usage

```sh
uv run coord-buffer -h 
usage: coord-buffer [-h] [-l] [--msid MSID] [-f INPUT_FILE] [-b BUFFER]

Creates a specified buffer around user specified area.

options:
  -h, --help            show this help message and exit
  -l, --list            Prints list of available geometries and their
                        id.
  --msid MSID           Get coords for the selected geometries.
  -f INPUT_FILE, --input_file INPUT_FILE
                        Path to a GeoJSON file with coordinates
  -b BUFFER, --buffer BUFFER
                        Buffer size in NM (default: 0)
```