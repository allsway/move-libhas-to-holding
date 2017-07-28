# move-libhas-to-holding
Copies a MARC 95X-999 field that contains the LIB HAS information from the bib record to an associated holding

###### move_libhas.py
Takes as arguments
   - initialization file config.txt 
   - an XML export of bib records, exported directly from Alma.  

Run as `python move_libhas.py config.txt bibrecords.xml`

###### config.txt
Configuration setup can be modified in the file config.txt. 
```
[Params]
apikey: apikey 
baseurl: https://api-na.hosted.exlibrisgroup.com
marc_tag: 599
target_marc_tag: 866
```
#### Results:
Copies a MARC field from the bib record (as specified by 'marc_tag' in the config file) to a holding record MARC field.  Currently it selects the last holding that displays in Primo and adds to the last holding that displays in the Primo holding sort order.  However, this can easily be adjusted to add the field to all holdings or holdings that belong to a specific location.  
