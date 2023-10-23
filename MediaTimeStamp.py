# pip install pillow-heif
# pip install piexif

import os
from pathlib import Path
# import pytz
import argparse
from PIL import Image, ExifTags
from datetime import datetime
# import json
import shutil

import png
# from pypng import png # pip install pypng
# from win32com.propsys import propsys, pscon

# Register the HEIF opener
from pillow_heif import register_heif_opener
register_heif_opener()

'''
Testing:
python MediaTimeStamp.py ./TestFiles/


'''

def process_file(file_path):
    file_extension = file_path.split('.')[-1].upper()
    
    if file_extension == "PY" or file_extension == "PYC":
        return
    elif file_extension == "ZIP":
        return
    elif file_extension == "HEIC":
        create_time = extract_heic_create_time(file_path)
    elif file_extension == "JPG" or file_extension == "JPEG":
        #create_time = extract_jpg_create_time(file_path)
        create_time = extract_heic_create_time(file_path)
    elif file_extension == "PNG" or file_extension == "JPEG":
        create_time = extract_png_create_time(file_path)
    elif file_extension == "MOV":
        create_time = extract_mov_create_time(file_path)
    else:
        print(f"Skipping   : {file_path}")
        return  
    if create_time:
        #print(f"Processing : {file_path:<68} Updating to : {create_time}")
        update_file_timestamp(file_path, create_time)
    else:
        print(f"Processing : {file_path:<68} --- no 'create_tine'!")


def extract_jpg_create_time(file_path):
    # Placeholder for extracting creation time from JPG files
    # JPG can use the same method as HEIC!
    return None
    

def extract_heic_create_time(file_path):
    try:
        image = Image.open(file_path)
        image_exif = image.getexif()
        #if image_exif and ExifTags.TAGS.get('DateTime'):
        if image_exif:
            exif = {ExifTags.TAGS[k]: v for k, v in image_exif.items() if k in ExifTags.TAGS and type(v) is not bytes}
            #print(json.dumps(exif, indent=4))
            date = datetime.strptime(exif['DateTime'], '%Y:%m:%d %H:%M:%S')
            return date
    except Exception as e:
        print(f"Failed to extract Exif data from {file_path}: {e}")
    return None

# Modify the other extraction functions (extract_jpg_create_time, extract_mov_create_time) as needed.

def extract_png_create_time(file_path):
    #im = png.Reader(file_path)
    #for c in im.chunks():   
    #    print(c[0], len(c[1]))
    try:
        exif_time=extract_string_between_tags(file_path, "photoshop:DateCreated")
        #print("extract_string_between_tags():", exif_time)
        date = datetime.strptime(exif_time, '%Y-%m-%dT%H:%M:%S')
        # print("timestamp_suffix = ", f"_{date.strftime('%Y%m%d_%H%M')}")
        return date
    except Exception as e:
        print(f"!!!  Failed to extract Exif data from PNG {file_path}: {e}")
    return None


def extract_string_between_tags(filename, tag):
    start_tag = f"<{tag}>".encode('utf-8')
    end_tag = f"</{tag}>".encode('utf-8')
    #print("start_tag= ",start_tag, "   end_tag= ",end_tag)
    try:
        with open(filename, 'rb') as file:
            content = file.read()
            start_pos = content.find(start_tag)
            end_pos = content.find(end_tag)

            if start_pos != -1 and end_pos != -1 and start_pos < end_pos:
                extracted_data = content[start_pos + len(start_tag):end_pos]
                return extracted_data.decode('utf-8')  # Convert bytes to string
            else:
                return None
    except FileNotFoundError:
        return None


def extract_mov_create_time(file_path):
    return get_mov_timestamps(file_path)[0]
    
    
    # Placeholder for extracting creation time from MOV files
    # You can use a library or method specific to MOV files
    try:

        properties = propsys.SHGetPropertyStoreFromParsingName(filepath)
        dt = properties.GetValue(pscon.PKEY_Media_DateEncoded).GetValue()
        
        if not isinstance(dt, datetime.datetime):
            # In Python 2, PyWin32 returns a custom time type instead of
            # using a datetime subclass. It has a Format method for strftime
            # style formatting, but let's just convert it to datetime:
            dt = datetime.datetime.fromtimestamp(int(dt))
            dt = dt.replace(tzinfo=pytz.timezone('UTC'))

        dt_tokyo = dt.astimezone(pytz.timezone('Asia/Tokyo'))

        image = Image.open(file_path)
        image_exif = image.getexif()
        #if image_exif and ExifTags.TAGS.get('DateTime'):
        if image_exif:
            exif = {ExifTags.TAGS[k]: v for k, v in image_exif.items() if k in ExifTags.TAGS and type(v) is not bytes}
            date = datetime.strptime(exif['DateTime'], '%Y:%m:%d %H:%M:%S')
            return date
    except Exception as e:
        print(f"!!!  Failed to extract Exif data from {file_path}: {e}")
    return None


# exiftool -time:all img_3904.mov
# https://stackoverflow.com/questions/21355316/getting-metadata-for-mov-video/54683292#54683292

def get_mov_timestamps(filename):
    ''' Get the creation and modification date-time from .mov metadata.
        Returns None if a value is not available.
    '''
    from datetime import datetime as DateTime
    import struct

    ATOM_HEADER_SIZE = 8
    # difference between Unix epoch and QuickTime epoch, in seconds
    EPOCH_ADJUSTER = 2082844800

    creation_time = modification_time = None

    try:
        # search for moov item
        with open(filename, "rb") as f:
            while True:
                atom_header = f.read(ATOM_HEADER_SIZE)
                #~ print('atom header:', atom_header)  # debug purposes
                if atom_header[4:8] == b'moov':
                    break  # found
                else:
                    atom_size = struct.unpack('>I', atom_header[0:4])[0]
                    f.seek(atom_size - 8, 1)

            # found 'moov', look for 'mvhd' and timestamps
            atom_header = f.read(ATOM_HEADER_SIZE)
            if atom_header[4:8] == b'cmov':
                raise RuntimeError('moov atom is compressed')
            elif atom_header[4:8] != b'mvhd':
                raise RuntimeError('expected to find "mvhd" header.')
            else:
                f.seek(4, 1)
                creation_time = struct.unpack('>I', f.read(4))[0] - EPOCH_ADJUSTER
                creation_time = DateTime.fromtimestamp(creation_time)
                if creation_time.year < 1990:  # invalid or censored data
                    creation_time = None

                modification_time = struct.unpack('>I', f.read(4))[0] - EPOCH_ADJUSTER
                modification_time = DateTime.fromtimestamp(modification_time)
                if modification_time.year < 1990:  # invalid or censored data
                    modification_time = None
        return creation_time, modification_time
    except Exception as e:
        print(f"!!!  Failed to extract Exif data from MOV {file_path}: {e}")
    return None, None
 

def update_file_attributes_and_rename(file_path, mask=None):
    if os.path.isfile(file_path):
        process_file(file_path)
    elif os.path.isdir(file_path):
        for root, dirs, files in os.walk(file_path):
            for file_name in files:
                if not mask or mask in file_name:
                    file_path = os.path.join(root, file_name)
                    process_file(file_path)


def update_file_timestamp(file_path, timestamp):
    base_name, file_ext = os.path.splitext(file_path)
    # Check if the filename already ends with the timestamp
    timestamp_suffix = f"_{timestamp.strftime('%Y%m%d_%H%M')}"
    destination_path = f"{timestamp.strftime('%Y')}\\{timestamp.strftime('%Y_%m')}"

    # Separate base from extension
    base, extension = os.path.splitext(file_path)
    print(" base, extension = '",  base, "', '", extension ,"'")
    
    #if not os.path.exists(os.path.join(basedir, base)):
    if not os.path.exists(os.path.join(".", destination_path)):
        print( os.path.join(".", destination_path), "not found ==> creating")
        Path(os.path.join(".", destination_path)).mkdir(parents=True, exist_ok=True)
        #continue    # Next filename
        #elif not os.path.exists(new_name):  # folder exists, file does not
        #    shutil.copy(old_name, new_name)
    
    print("destination_path = ", destination_path)
    
    RenameFileInPlace = False 
    
    if RenameFileInPlace:
        if base_name.endswith(timestamp_suffix):
            #print(f"Skipping {file_path} as the timestamp is already appended.")
            return
        
        print(f"Processing : {file_path:<68} Updating to : {timestamp}", end=" ")
        new_name = f"{base_name}{timestamp_suffix}{file_ext}"
        os.rename(file_path, new_name)
        print(f"Renamed to '{new_name}'")

        # Update the file's access and modification timestamps
        os.utime(new_name, (timestamp.timestamp(), timestamp.timestamp()))
    else:   # 
    
        base_name = os.path.basename( base_name )
        root = "."
        new_name = os.path.join( os.path.abspath(destination_path), f"{base_name}{timestamp_suffix}{file_ext}" )
        if not os.path.exists(new_name):  # folder exists, file does not
            print("shutil.copy(file_path, new_name) '",file_path, "', '", new_name,"'")
            shutil.copy(file_path, new_name)
            os.utime(new_name, (timestamp.timestamp(), timestamp.timestamp()))
        #else:  # folder exists, file exists as well
        #    ii = 1


# #####################################################################################################   
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update filenames and file timestamps of media files")
    parser.add_argument("file_path", nargs='?', default=".", help="Path to the directory or file")
    parser.add_argument("--mask", help="File mask (e.g., '.JPG' to process only JPG files)")
    args = parser.parse_args()
    print("\n=================================================================================")
    update_file_attributes_and_rename(args.file_path, args.mask)
