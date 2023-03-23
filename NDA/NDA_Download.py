import base64
import csv
import requests
import json
import urllib.request
import shutil
from pathlib import Path


packageId = 1191861
downloadPath = '/fast_scratch/jdr/downloads/'


# Encode our credentials then convert it to a string.
credentials = base64.b64encode(b'jrusse10:19Ireland61').decode('utf-8')

# Create the headers we will be using for all requests.
headers = {
    'Authorization': 'Basic ' + credentials,
    'User-Agent': 'Example Client',
    'Accept': 'application/json'
}

# Send Http request
response = requests.get('https://nda.nih.gov/api/package/auth', headers=headers)

# Business Logic.

# If the response status code does not equal 200
# throw an exception up.
if response.status_code != requests.codes.ok:
    print('failed to authenticate')
    response.raise_for_status()

# The auth endpoint does no return any data to parse
# only a Http response code is returned.

# ----------------END AUTHENTICATION ------------------------- #

# ---------------STARTING TO GET FILE LIST ------------------- #

# Assume code in authentication section is present.

# Construct the request to get the files of package 1234
# URL structure is: https://nda.nih.gov/api/package/{packageId}/files
response = requests.get('https://nda.nih.gov/api/package/' + str(packageId) + '/files', headers=headers)

# Get the results array from the json response.
results = response.json()['results']

# Business Logic.

files = {}

# Add important file data to the files dictionary.
for f in results:
    files[f['package_file_id']] = {'name': f['download_alias']}

# --------------- END GETTING FILE LIST ------------------- #

# --------------- START DOWNLOADING FILES ----------------- #

# Assume code in authentication section is present.
# Assume that one of the retrieving files implementations is present too

# Create a post request to the batch generate presigned urls endpoint.
# Use keys from files dictionary to form a list, which is converted to
# a json array which is posted.
response = requests.post('https://nda.nih.gov/api/package/' + str(packageId) + '/files/batchGeneratePresignedUrls',
                         json=list(files.keys()), headers=headers)

# Get the presigned urls from the response.
results = response.json()['presignedUrls']

# Business Logic.

# Add a download key to the file's data.
for url in results:
    files[url['package_file_id']]['download'] = url['downloadURL']

# Iterate on file id and it's data to perform the downloads.
for id, data in files.items():
    name = data['name']
    downloadUrl = data['download']
    # Create a downloads directory
    file = downloadPath + name
    # Strip out the file's name for creating non-existent directories
    directory = file[:file.rfind('/')]

    # Create non-existent directories, package files have their
    # own directory structure, and this will ensure that it is
    # kept in tact when downloading.
    Path(directory).mkdir(parents=True, exist_ok=True)

    # Initiate the download.
    with urllib.request.urlopen(downloadUrl) as dl, open(file, 'wb') as out_file:
        shutil.copyfileobj(dl, out_file)
