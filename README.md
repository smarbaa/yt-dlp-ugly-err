This is a plugin for [yt-dlp](https://github.com/yt-dlp/yt-dlp) that adds support for [err.ee](https://www.err.ee/) and its various subchannels:

* [etv.err.ee](https://etv.err.ee)
* [etv2.err.ee](https://etv2.err.ee)
* [etvpluss.err.ee](https://etvpluss.err.ee)
* [jupiter.err.ee](https://jupiter.err.ee)
* [jupiterpluss.err.ee](https://jupiterpluss.err.ee)
* [vikerraadio.err.ee](https://vikerraadio.err.ee)
* [klassikaraadio.err.ee](https://klassikaraadio.err.ee)
* [r2.err.ee](https://r2.err.ee)
* [r4.err.ee](https://r4.err.ee)
* [arhiiv.err.ee](https://arhiiv.err.ee)

## Installation

Requires yt-dlp `2023.01.02` or above.

You can install this package with pip:
```
python3 -m pip install -U https://github.com/smarbaa/yt-dlp-ugly-err/archive/master.zip
```

See [installing yt-dlp plugins](https://github.com/yt-dlp/yt-dlp#installing-plugins) for the other methods this plugin package can be installed.

## Supported features

All provided audio, video and subtitle streams can be downloaded, thumbnails and chapters too if available. Series are handled as playlists.

## Authentication options

etv, jupiter an jupiterpluss support username/password and netrc based authentication, netrc machine should be err.ee.


## Usage terms and rights of downloaded material

ERR usage terms and rights are explained in [https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine](https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine)

## Known problems

jupiter.err.ee sometimes gives strange languages for audio streams, and extractor labels them as 'unknown' or 'original'. Unrecognized subtitle language gets labeled 'und' (undetermined). To avoid fixing them later in some other software, one may use extractor arguments 'unknown', 'original' and 'und' to substitute valid language codes for 'unknown', 'original' and/or 'und', e.g.

    --extractor-args 'err:unknown=en;original=et;und=de'

## Usage examples

```bash
# Embedded video in a news aricle

## Print filename and description, list all available formats in
## a nicely formatted table

$ yt-dlp --print filename --print description --print formats_table 'https://kultuur.err.ee/1609231323/david-vseviov-raamatud-tuleb-lahti-seletada-mitte-ara-keelata'

## Download video stream '136' and audio stream 'unknown' and rename
## 'unknown' to 'et', embed metadata and thumbnail if available

$ yt-dlp -f 136+et --extractor-args 'err:unknown=et' --embed-metadata --embed-thumbnail 'https://kultuur.err.ee/1609231323/david-vseviov-raamatud-tuleb-lahti-seletada-mitte-ara-keelata'

## Radio episodes and podcasts

## List all available formats

$ yt-dlp --list-formats 'https://vikerraadio.err.ee/795251/linnukool-mailopu-helid' 

## Download audio stream format '142', embed metadata and thumbnail

$ yt-dlp -f 142 --embed-thumbnail --embed-metadata 'https://vikerraadio.err.ee/795251/linnukool-mailopu-helid'

## Download all episodes

$ yt-dlp -f bestaudio --embed-thumbnail --embed-metadata --yes-playlist 'https://klassikaraadio.err.ee/arhiiv/album'

## Download all episodes of a podcast this one belongs to

$ yt-dlp -f bestaudio --embed-thumbnail --embed-metadata --yes-playlist 'https://r4.err.ee/1609221212/razbor-poljotov'

## TV, Jupiter, JupiterPluss, ERR Arhiiv

## Download movie with two audio streams, 'et' and 'ru', video stream
## 1280x720, all available subs, metadata and thumbnail and embed them
## all in a matroska container

$ yt-dlp -f 136+et+ru --audio-multistreams --video-multistreams --merge-output-format mkv --sub-langs all --embed-subs --embed-metadata --embed-thumbnail 'https://jupiter.err.ee/1608130759/maekula-piimamees'
```
