# Kinksorter

Recognizes archives of kink-related videos by name or interactively,
to tag, uniformly sort and merge them with other archives of 
the same content.

# Features
- Autodetection by ID of well-named directory structures
- Autodetection by image-recognition (Kink.com-Shootid)
- Interactive Tagging by date, performers, ID or name [TODO]
- Produces clean and changeable directory structures
- Works also with FTP/HTTP-directories [TODO]
- Reversible

# Approach
1. Create a database of {path: properties} - objects by 
extracting the ID of the scene and getting the properties 
from an API.

2. Merge all directories into that database and 
disregard duplicates.
3. Build a new directory structure using the 
API-provided properties.

4. Produce a list of files missing from the 
main-archive and move (or symlink) them to their new
locations, where possible.

5. (Revert the new archive back by using the original paths 
from the database.)

# Installation
1. Install Dependencies:
  - python >3.3
  - python3-opencv
  - tesseract  
  - python3-tqdm
  - python3-fuzzywuzzy
  - python-Levenshtein

2. git clone https://github.com/sistason/kinksorter

3. setup.py [TODO ;)]

# Usage

python3 kinksorter.py $MainDirectory $MergeTarges
- $MainDirectory: What's yours (writeable). The sorted/merged
 directory will be "$MainDirectory_kinksorted/"
- $MergeTargets: What you want integrated/diff-ed (readable). 
 Use ftp(s):// and http(s):// respectively
- -i: Interactive. Confirm API-findings and give inputs 
 when inconclusive/no results occur.
- -t: Default is symlinking/listing only. Use --tested to 
 actually move/download files to their new locations.
- -r: Revert a new location back to it's original state.
 Original is what paths are in the database of $MainDirectory.
- -s: Give the directory of the shootid templates for 
OpenCV Kink.com recognition.
