from TelegramBot.helpers.supported_url_regex import SUPPORTED_URL_REGEX
from TelegramBot.helpers.gdrivehelper import GoogleDriveHelper
from TelegramBot.helpers.pasting_services import katbin_paste 
from TelegramBot.helpers.functions import *
from TelegramBot.logging import LOGGER
from TelegramBot.config import prefixes 
from TelegramBot import bot

from pyrogram import Client, filters
from pyrogram.types import Message

from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build

from urllib.parse import unquote
from bs4 import BeautifulSoup
import subprocess
import requests
import json
import re
import os


async def gdrive_mediainfo(client, message, url):
    """
    Generates Mediainfo from a Google Drive file
    """
     	
    try:
        GD = GoogleDriveHelper()
        metadata = GD.get_metadata(url)
        file_id = GD.get_id(url) 

        service = build('drive', 'v3', cache_discovery=False, credentials=GD.get_credentials())
        request = service.files().get_media(fileId=file_id)

        reply_msg = await message.reply_text("Generating Mediainfo, Please wait..", quote=True)
        with open(f"{file_id}", "wb") as file:
        	   downloader = MediaIoBaseDownload(file, request)
        	   downloader.next_chunk()


        mediainfo = subprocess.check_output(['mediainfo', file_id]).decode("utf-8")
        mediainfo_json = json.loads(subprocess.check_output(['mediainfo', file_id, '--Output=JSON']).decode("utf-8"))

        filesize = get_readable_filesize(float(metadata['size']))
        filename = metadata['name']

        lines = mediainfo.splitlines()
        for i in range(len(lines)):
            if 'Complete name' in lines[i]:
                lines[i] = re.sub(r": .+", f': {filename}', lines[i])

            elif 'File size' in lines[i]:
                lines[i] = re.sub(r": .+", f': {filesize}', lines[i])

            elif 'Overall bit rate' in lines[i] and 'Overall bit rate mode' not in lines[i]:
                duration = float(mediainfo_json['media']['track'][0]['Duration'])
                bitrate = get_readable_bitrate(float(metadata['size'])*8/(duration * 1000))
                lines[i] = re.sub(r": .+", f': {bitrate}', lines[i])

            elif 'IsTruncated' in lines[i] or 'FileExtension_Invalid' in lines[i]:
            	lines[i] = ''        

        remove_N(lines)
        with open(f"{file_id}.txt", 'w') as f:
        	f.write('\n'.join(lines))

        with open(f"{file_id}.txt", "r+") as file: content = file.read()
        output = await katbin_paste(content)

        await reply_msg.edit(f"**File Name :** `{filename}`\n\n**Mediainfo :** {output}", disable_web_page_preview=True)
        os.remove(f"{file_id}.txt")
        os.remove(file_id)

    except:
    	await reply_msg.delete()
    	return await message.reply_text(f"Something went wrong with that Gdrive url.\n\n ( make sure that the given drive url is non rate limited , public and not a folder )", quote=True)

   
 

async def ddl_mediainfo(client, message, url):
    """
    Generates Mediainfo from a Direct Download Link.
    """
    
    try:
        filename = re.search(".+/(.+)" , url)[1]
        reply_msg = await message.reply_text("Generating Mediainfo, Please wait..", quote=True)

        with requests.get(url, stream=True) as r:
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(50000000): f.write(chunk); break

        mediainfo = subprocess.check_output(['mediainfo', filename]).decode("utf-8")
        mediainfo_json = json.loads(subprocess.check_output(['mediainfo', filename, '--Output=JSON']).decode("utf-8"))

        filesize = requests.head(url).headers.get('content-length')

        lines = mediainfo.splitlines()
        for i in range(len(lines)):
            if 'Complete name' in lines[i]:
                lines[i] = re.sub(r": .+", f': {unquote(filename)}', lines[i])

            elif 'File size' in lines[i]:
                lines[i] = re.sub(
                    r": .+",
                    f': {get_readable_filesize(float(filesize))}',
                    lines[i],
                )

            elif 'Overall bit rate' in lines[i] and 'Overall bit rate mode' not in lines[i]:
                duration = float(mediainfo_json['media']['track'][0]['Duration'])
                bitrate = get_readable_bitrate(float(filesize)*8/(duration * 1000))
                lines[i] = re.sub(r": .+", f': {bitrate}', lines[i])

            elif 'IsTruncated' in lines[i] or 'FileExtension_Invalid' in lines[i]:
            	lines[i] = ''        


        with open(f'{filename}.txt', 'w') as f:
        	f.write('\n'.join(lines))

        with open(f"{filename}.txt", "r+") as file: content = file.read()
        output = await katbin_paste(content)

        await reply_msg.edit(f"**File Name :** `{unquote(filename)}`\n\n**Mediainfo :** {output}", disable_web_page_preview=True)
        os.remove(f"{filename}.txt")
        os.remove(filename)

    except:
        await reply_msg.delete()
        return await message.reply_text(
            "Something went wrong while generating Mediainfo from the given url.",
            quote=True,
        )
  	 	   


async def telegram_mediainfo(client,message):
    """
    Generates Mediainfo from a Telegram File.
    """
 
    message = message.reply_to_message

    if message.text:
    	return await message.reply_text("Reply to a proper media file for generating Mediainfo.**", quote=True)

    elif message.media.value == 'video':
     	media = message.video

    elif message.media.value == 'audio':
    	media = message.audio

    elif message.media.value == 'document':
    	media = message.document

    elif message.media.value == 'voice':
    	media = message.voice

    else:
    	return await message.reply_text("This type of media is not supported for generating Mediainfo.**", quote=True)

    filename = str(media.file_name)
    mime = media.mime_type
    size = media.file_size

    reply_msg = await message.reply_text("Generating Mediainfo, Please wait..", quote=True)

    if int(size) <= 50000000:
        await message.download(os.path.join(os.getcwd(), filename))

    else:
        async for chunk in client.stream_media(message, limit=5):
            with open(filename, 'ab') as f:
                f.write(chunk)


    mediainfo = subprocess.check_output(['mediainfo', filename]).decode("utf-8")
    mediainfo_json = json.loads(subprocess.check_output(['mediainfo', filename, '--Output=JSON']).decode("utf-8"))
    readable_size = get_readable_size(size)

    try:    
        lines = mediainfo.splitlines()
        for i in range(len(lines)):
            if 'File size' in lines[i]:
                lines[i] = re.sub(r": .+", f': {readable_size}', lines[i])

            elif 'Overall bit rate' in lines[i] and 'Overall bit rate mode' not in lines[i]:
            	
                duration = float(mediainfo_json['media']['track'][0]['Duration'])
                bitrate_kbps = (size*8)/(duration*1000)
                bitrate = get_readable_bitrate(bitrate_kbps)

                lines[i] = re.sub(r": .+", f': {bitrate}', lines[i])

            elif 'IsTruncated' in lines[i] or 'FileExtension_Invalid' in lines[i]:
                lines[i] = ''

        remove_N(lines)
        with open(f'{filename}.txt', 'w') as f:
            f.write('\n'.join(lines))

        with open(f"{filename}.txt", "r+") as file:
        	content = file.read()

        output = await katbin_paste(content)

        await reply_msg.edit(f"**File Name :** `{filename}`\n\n**Mediainfo :** {output}", disable_web_page_preview=True)
        os.remove(f'{filename}.txt')
        os.remove(filename)

    except:
        await reply_msg.delete()
        await message.reply_text(
            "Something went wrong while generating Mediainfo of replied Telegram file.",
            quote=True,
        )
        
        

commands = ["mediainfo", "m"]
mediainfo_usage = "**Generate mediainfo from Google Drive Links, Telegram files or direct download links. Reply to any telegram file or just pass the link after the command."
@Client.on_message(filters.command(commands, **prefixes))
async def mediainfo(client, message: Message):
     
    if message.reply_to_message:
    	return await telegram_mediainfo(client, message)
    	
    elif len(message.command) < 2:
      return await message.reply_text(mediainfo_usage, quote=True)
      
    user_url = message.text.split(None, 1)[1].split(" ")[0]    
    for (key, value) in SUPPORTED_URL_REGEX.items():
    	if bool(re.search(FR"{key}", user_url)):
    	 
    	    if value == "gdrive":
    	       return await gdrive_mediainfo(client, message, url=user_url)
    	     
    	    elif value == "ddl":
    	       return await ddl_mediainfo(client, message, url=user_url)
    	      	
    return await message.reply_text("This type of URL is not supported.", quote=True)


