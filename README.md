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

## Supported urls in jupiter.err.ee, jupiterpluss.err.ee and tv and radio portals

Two types of urls exist - episode urls and series urls, and both types look exactly the same.
Both are supported, but their download behaviour differs somewhat - episode urls cause one item of audio/video to be downloaded, whereas series urls can trigger a whole list of media to be downloaded. So, be careful what you demand yt-dlp to do.

*   Episode  url - https://jupiter.err.ee/video_id/display_id
*   Series  url - https://jupiter.err.ee/series_id/display_id

video_id and series_id are numerical, display_id is human-readable alphanumerical string with some additional characters allowed.

Series urls can be found in

*   https://jupiter.err.ee/saated

or on various category pages like

*   https://jupiter.err.ee/raadioteater
*   https://jupiter.err.ee/v-saated
*   https://jupiter.err.ee/sarjad

etc. Episode urls can be found in tv programs and series pages, or directly copied from the player's share link overlay.

## Supported urls in arhiiv.err.ee

Again, there are two types of urls - episode and series urls. Both types are supported and the behaviour of yt-dlp varies according to the type - episode urls trigger single downloads, series urls may cause multiple files to be downloaded.

*   Episode url
    *   https://arhiiv.err.ee/video/vaata/video_id
    *   https://arhiiv.err.ee/video/video_id
    *   https://arhiiv.err.ee/guid/VERYLONGID

*   Series url
    *   https://arhiiv.err.ee/video/vaata/series_id
    *   https://arhiiv.err.ee/video/series_id
    *   https://arhiiv.err.ee/video/seeria/series_id

'Audio urls' work the same, only substitute audio for video in the above description.

## Extractor arguments

Yt-dlp accepts special arguments per extractor or extractor group, see [extractor arguments](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#extractor-arguments) for more details. UglyERR supports following extractor arguments: 

*   `unknown`
*   `und`
*   `original`
*   `yes-playlist`

The first three, i.e. `unknown`, `und` and `original`, may come in useful when dealing with audio and subtitle languages, see [known problems](#known-problems) for examples. `yes-playlist` can be used to force downloading a series when only an episode url is given.

```bash
# Download first five episodes of a series. Without yes-playlist one would get only a single episode.

$ yt-dlp --playlist-items 1:6 --extractor-args 'UglyERR:yes-playlist' https://arhiiv.err.ee/audio/vaata/eesti-lugu-eesti-lugu-1-ajalugu-ja-muudid
```

## Authentication options

etv, jupiter and jupiterpluss support username/password and netrc based authentication, netrc machine should be err.ee. See [authentication with netrc](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#authentication-with-netrc) for further details. 

## Usage terms and rights of downloaded material

ERR usage terms and rights are explained in [https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine](https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine)

## Known problems

jupiter.err.ee sometimes gives strange languages for audio streams, and extractor labels them as 'unknown' or 'original'. Unrecognized subtitle language gets labeled 'und' (undetermined). To avoid fixing them later in some other software, one may use extractor arguments 'unknown', 'original' and 'und' to substitute valid language codes for 'unknown', 'original' and/or 'und', e.g.

    --extractor-args 'UglyERR:unknown=en;original=et;und=de'

## Usage examples

```bash
# Embedded video in a news article

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

$ yt-dlp -f bestaudio --embed-thumbnail --embed-metadata 'https://klassikaraadio.err.ee/arhiiv/album'

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

## Different variations of urls are supported. E.g.
## Download an episode of a series only.

$ yt-dlp https://arhiiv.err.ee/video/vaata/patu-1

## or

$ yt-dlp https://arhiiv.err.ee/video/patu-1

## Download all episodes of a series

$ yt-dlp https://arhiiv.err.ee/video/vaata/patu

## or

$ yt-dlp https://arhiiv.err.ee/video/patu

## or

$ yt-dlp https://arhiiv.err.ee/video/seeria/patu
```
