# Overview

The main purpose of the program is to make audio files posted on Telegram available to regular desktop audio players. This is done via VFS by mapping remote files from telegram's cloud to local file system. Tested with audio players [quodlibet](https://github.com/quodlibet/quodlibet), [deadbeef](https://github.com/DeaDBeeF-Player/deadbeef), [clementine](https://github.com/clementine-player/Clementine).

# Libraries used 
* [telethon](https://github.com/LonamiWebs/Telethon)
* [libfuse](http://github.com/libfuse/libfuse)
* [tqdm](https://github.com/tqdm/tqdm)
* [funcy](https://github.com/Suor/funcy)
* pysocks

# Running

```
$ virtualenv .venv3.7 -p python3.7
$ source .venv3.7/bin/activate
$ pip install -r requirements.txt
$ python tgmount/tgmount.py --list-dialogs
```

# Usage
To obtain your API id follow [official manual](https://core.telegram.org/api/obtaining_api_id).  Running the program for the first time will require authentication.

```
$ export TGAPP=1234567:deadbeef0d04a3efe93e1af778773d6f0
```

Print your dialogs along with their numeric id's:

```
$ tgmount.py --list-dialogs
```

Print 10 newest available documents:

```
$ tgmount.py --list-documents --id 793392913 --limit 10
```

Print 10 oldest available documents:

```
$ tgmount.py --list-documents --id 793392913 --limit 10 --reverse
```

Using global telegram username:

```
$ tgmount.py --list-documents --id techtroit --limit 10 --reverse
```

Json output:
```
$ tgmount.py --list-documents --id techtroit --limit 10 --json
```

Mount channel techtroit to /mnt/techtroit/ loading all the audio files posted after message with id 11286

```
$ tgmount.py --mount /mnt/techtroit/ --id techtroit --offset 11286 --reverse
```

Download files

```
$ tgmount.py --download /ssd/tgfs/download/ --id techtroit --files 11823,11822
```

Download all files uploaded after message with id 11837
```
$ tgmount.py --download /ssd/tgfs/download/ --id techtroit --files $(tgmount.py --list-documents --id techtroit --offset-id 11837 --reverse --json | jq -r 'map(.message_id) | join(",")')
```

More options:
```
usage: tgmount.py [-h] [--id ID] [--mount DIR] [--list-dialogs]
                  [--list-documents] [--download DIR] [--files FILES]
                  [--all-files] [--no-updates] [--reverse] [--limit LIMIT]
                  [--offset-id OFFSET_ID] [--session SESSION]
                  [--fsname FSNAME] [--socks SOCKS] [--debug] [--debug-fuse]
                  [--json]

optional arguments:
  -h, --help            show this help message and exit
  --id ID               chat or channel ID. Telegram username or numeric ID
  --mount DIR           mount to DIR
  --list-dialogs        print available telegram dialogs
  --list-documents      print available documents
  --download DIR        save files to DIR. Use with --files parameter
  --files FILES         comma separated list of document IDs
  --all-files           Retrieve all type of files, not only audio files.
                        Default: no
  --no-updates          don't listen for new files. Default: no
  --reverse             documents will be searched in reverse order (from
                        oldest to newest). Default: from newest to oldest
  --limit LIMIT         limit number of documents or dialogs. default:
                        unlimited
  --offset-id OFFSET_ID
                        offset message ID. Only documents previous to the
                        given ID will be retrieved
  --session SESSION     telegram session name. Default: tgfs
  --fsname FSNAME       VFS name. Default: tgfs
  --socks SOCKS         SOCKS5 proxy i.e. 127.0.0.1:9050
  --debug               enable debugging output
  --debug-fuse          enable FUSE debugging output
  --json                json output. Default: no
```