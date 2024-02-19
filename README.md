This is a plugin for [yt-dlp](https://github.com/yt-dlp/yt-dlp) that adds support for [err.ee](https://www.err.ee/) and its various subchannels and portals:

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

All audio, video and subtitle streams that are not DRM-protected can be downloaded, thumbnails and chapters too if available. Series are handled as playlists.

## Authentication options

etv, jupiter an jupiterpluss support username/password and netrc based authentication, netrc machine should be err.ee.

## Usage terms and rights of downloaded material

ERR usage terms and rights are explained in [https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine](https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine)

## Known problems

jupiter.err.ee sometimes gives strange languages for audio streams, and extractor labels them as 'unknown' or 'original'. Unrecognized subtitle language gets labeled 'und' (undetermined). To avoid fixing them later in some other software, one may use extractor arguments 'unknown', 'original' and 'und' to substitute valid language codes for 'unknown', 'original' and/or 'und', e.g.

    --extractor-args 'UglyERR:unknown=en;original=et;und=de'

For episodes, the default behaviour is to download also the series they belong to. One can opt out of this by specifying parameter `--no-playlist`, sadly, a much more reasonable opt-in by `--yes-playlist` doesn't work.

## Usage examples

```bash
# Embedded video in a news aricle

## Print filename and description, list all available formats in
## a nicely formatted table.

$ yt-dlp --print filename --print description --print formats_table 'https://kultuur.err.ee/1609231323/david-vseviov-raamatud-tuleb-lahti-seletada-mitte-ara-keelata'

## Download video stream '136' and audio stream 'unknown' and rename
## 'unknown' to 'et', embed metadata and thumbnail if available.

$ yt-dlp -f 136+et --extractor-args 'UglyERR:unknown=et' --embed-metadata --embed-thumbnail 'https://kultuur.err.ee/1609231323/david-vseviov-raamatud-tuleb-lahti-seletada-mitte-ara-keelata'

## Radio episodes and podcasts

## List all available formats.

$ yt-dlp --list-formats 'https://vikerraadio.err.ee/795251/linnukool-mailopu-helid' 

## Download audio stream format '142', embed metadata and thumbnail.

$ yt-dlp -f 142 --embed-thumbnail --embed-metadata 'https://vikerraadio.err.ee/795251/linnukool-mailopu-helid'

## Download all episodes.

$ yt-dlp -f bestaudio --embed-thumbnail --embed-metadata --yes-playlist 'https://klassikaraadio.err.ee/arhiiv/album'

## Download all episodes of a podcast this one belongs to.

$ yt-dlp -f bestaudio --embed-thumbnail --embed-metadata --yes-playlist 'https://r4.err.ee/1609221212/razbor-poljotov'

## TV, Jupiter, JupiterPluss, ERR Arhiiv

## Check available formats of a documentary film.

$ yt-dlp --list-formats https://arhiiv.err.ee/video/vaata/toonela-lind-must-toonekurg

## Now download it with default format selection, embedded metadata and
## thumbnail, replace 'unknown' audio stream label with 'et', use output
## template to get a nice readable filename

$ yt-dlp --extractor-args 'UglyERR:unknown=et' --embed-thumbnail --embed-metadata --output '%(title)s.%(ext)s' https://arhiiv.err.ee/video/vaata/toonela-lind-must-toonekurg

## List all episodes of a series, their available formats and subtitles.

$ yt-dlp --print filename --print formats_table --print subtitles_table https://arhiiv.err.ee/video/vestlusi-vene-kultuuriloost-juri-lotman

## Download all episodes of a series, video format '136', audio 'ru'
## and subtitles 'et' and embed them into an mkv file using a simple
## output template. Beware, there are 32 of them!

$ yt-dlp -f 136+ru --sub-langs et --embed-subs --embed-thumbnail --embed-metadata --merge-output-format mkv --output '%(title)s.%(ext)s' https://arhiiv.err.ee/video/vestlusi-vene-kultuuriloost-juri-lotman

## Download an episode of a series only. Remark the --no-playlist parameter.

$ yt-dlp --no-playlist https://arhiiv.err.ee/video/vaata/patu-1
```
