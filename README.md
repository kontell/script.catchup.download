# Catchup Download

Kodi add-on: save a programme that has already aired, from the TV guide, into your Jellyfin server's recordings.

It adds **Save to recordings** to the context menu of every programme in Kodi's TV guide, whichever PVR client lists it (pvr.kofin, pvr.iptvsimple). Choose it on a programme that has finished, confirm, and the Jellyfin server copies the programme from the IPTV provider's catchup archive into its recordings, with the guide's description and image. The Comseg plugin then marks its commercial breaks. Nothing is downloaded to the Kodi device.

## Requirements

- Kodi 20 or later.
- A Jellyfin 12 server running the [Comseg](https://github.com/kontell/jellyfin-plugin-comseg) plugin, with *Save programmes from the IPTV archive* on.
- An M3U tuner in Jellyfin whose provider keeps a Flussonic-style catchup archive (channel URLs ending in `NAME.m3u8`).
- A Jellyfin user allowed to manage live TV recordings.

## Setup

Open the add-on's settings. Under **Account**, use *Find servers on local network* or type the server's address, then *Log in…* with Quick Connect or a username and password. These work as they do in Kofin.

Kodi keeps one day of past programmes in its guide by default. To save older ones, raise *Settings → PVR & Live TV → Guide → Past days to display* to match the provider's archive, usually 7 days.

## Settings

| Setting | Default | |
| --- | --- | --- |
| Start early | 0 min | Minutes saved before the guide's start. |
| Finish late | 0 min | Minutes saved after the guide's end, for programmes that overrun. |
| Show downloads | | The server's downloads of the last day, with their progress; choose a running one to cancel it. |

## How it finds the programme

A guide programme's path holds its start time, and the add-on asks Kodi's JSON-RPC for the rest: end time, title, description and image. The server finds the channel in its own tuner playlist by the name Kodi shows, then by its number. Kodi numbers channels itself unless *Use channel numbers from backend* is on, so the name is what matches.

The server waits for the IPTV connection when Jellyfin is recording or showing live TV, so a saved programme can take a while to appear. *Show downloads* says what it is waiting for.

## Build

```sh
tools/build.py          # dist/script.catchup.download-<version>.zip
python -m pytest tests  # the Kodi-free modules
```
