# Overview

New version of tgmount


## Requirements
- Linux
- Python?


## Installation:

virtualenv .venv3.7 -p python3.7
source .venv3.7/bin/activate
pip install -r requirements.txt
python tgmount/tgmount.py --list-dialogs

Usage:
```python

```

## Client

`tgmount auth`

`tgmount mount`

`tgmount mount-config`

`tgmount list`

`tgmount list dialogs`

`tgmount list documents`

`tgmount download`

## Basic usage

```
tgmount mount tgmounttestingchannel ~/mnt/tgmount1/ --reverse --limit 100
```

## Config file structure

### Message source 
https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.messages.MessageMethods.get_messages

Sample config
```yaml
mount_dir: /home/horn/mnt/tgmount1
client:
  session: tgfs
  api_id: 123
  api_hash: deadbeed121212121
message_sources:
  ru2chmu:
    entity: ru2chmu
    filter: InputMessagesFilterDocument
  friends:
    entity: -1001678896566
    
caches:
  memory1:
    type: memory
    capacity: 300MB
    block_size: 128KB
root:
  source: {source: ru2chmu, recursive: True}
  music:
    filter: 
      Union: [MessageWithMusic, MessageWithZip]
      producer: UnpackedZip
      cache: memory1
  liked-music:
    filter: 
      Union: 
        - MessageWithMusic
        - ByReaction: reaction: 👍
  texts:
    filter: MessageWithText
    # this commands tgmount to treat file with both document and text
    #  as text messages
    treat_as: MessageWithText
```