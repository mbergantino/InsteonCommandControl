#!/usr/bin/python
# -*- coding: latin-1 -*-

'''
Insteon Command Control
by Matt Bergantino

### FEATURES ##
-Connect to email account, parse emails matching given subject line, interpret and send command to Insteon Hub
-Ability to control whole scenes, rooms or individual lights
-Option to automatically archive or delete parsed emails

### TODO LIST ###
TODO: Add HTML Formatting to prettify the email report
TODO: Ability to turn lights off in some amount of time in the future
TODO: Ability to make lights flash (i.e. alert that they will be turning off soon)
TODO: Throw cmd execution in a thread for intricate processing (i.e. timers)

'''

import urllib,urllib2,imaplib,email,smtplib,logging,logging.handlers
from time import sleep
from email.parser import HeaderParser
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

# Configure your Insteon Hub
USERNAME  = 'HUB_USER'
PASSWORD  = 'HUB_PASS'
IPADDRESS = '192.168.0.2'

# Configure your email
mail_username       = 'USERNAME@gmail.com'
mail_password       = 'PASSWORD'
imap_server         = 'imap.gmail.com'      # To read email
smtp_server         = 'smtp.gmail.com'      # To send email
smtp_port           = '587'                 # To send email
polling_freq        = 2                     # number of seconds between rechecking for email
target_subject_line = 'InsteonCommand'      # subject line we'll look for
source_folder_name  = 'Inbox'               # name of folder/label where to find email for processing
dest_folder_name    = ''                    # name of folder/label where to store the email after processing
                                            # empty string will result in the email just being deleted

# Load the Device ID dictionary
# Expects placeholder values to be in format 'ABCD##'
devices = { 'base_front':'ABCD01'   , 'base_back':'ABCD10'   ,
            'porch_ohead':'ABCD02'  , 'porch_door':'ABCD11'  ,
            'foyer':'ABCD03'        , 'fl2_landing':'ABCD12' ,
            'lr_1lamp':'ABCD04'     , 'lr_3lamps':'ABCD13'   ,
            'lr_ohlow':'ABCD05'     , 'lr_ohhigh':'ABCD14'   , 'lr_fan':'ABCD19',
            'ktch_ohead_1':'ABCD06' , 'ktch_ohead_2':'ABCD15',
            'ktch_osink':'ABCD07'   , 'ktch_ucabs':'ABCD16'  ,
            'ktch_nook':'ABCD08'    , 'ktch_pen':'ABCD17'    ,
            'mb_matt':'ABCD09'      , 'mb_carol':'ABCD18'    }

devname = { 'base_front':'Basement Main Lights'                 , 'base_back':'Basement Secondary Lights'            ,
            'porch_ohead':'Porch Overhead Lights'               , 'porch_door':'Light by Front Door'                 ,
            'foyer':'Foyer Light'                               , 'fl2_landing':'Second Floor Hallway'               ,
            'lr_1lamp':'Living Room Lamp by wall'               , 'lr_3lamps':'Living Room Lamps'                    ,
            'lr_ohlow':'Living Room Overhead (Lower) Lights'    , 'lr_ohhigh':'Living Room Overhead (Higher) Lights' , 'lr_fan':'Living Room Fan',
            'ktch_ohead_1':'Kitchen Overhead - Bank of 2'       , 'ktch_ohead_2':'Kitch Overhead - Bank of 5'        ,
            'ktch_osink':'Kitchen Light over the sink'          , 'ktch_ucabs':'Kitchen Lights under the cabinets'   ,
            'ktch_nook':'Lights over the Nook'                  , 'ktch_pen':'Kitchen Lights over the peninsula'     ,
            'mb_matt':'Lamp on Matt\'s nightstand'              , 'mb_carol':'Lamp on Carol\'s nightstand'           }

# Insteon Command Format
defaultcmd = 'http://%USERNAME%:%PASSWORD%@%IP%:25105'

# Dev Features
test    = False  # If sample or offline are True then use sample input, otherwise only make 10 requests to mail server
sample  = False  # Use sample commands as input
offline = False  # If enabled, do not make connections out to the web (to attempt to reach Insteon Hub)

# Logging Control
logging.basicConfig(filename='icc.log',level=logging.INFO,format='%(levelname)s: %(asctime)s - %(message)s',datefmt='%m/%d/%Y %I:%M:%S %p')

def main():

    ### Use for test verification using demo commands below
    asked = []
    
    # ***********************************************
    #             Simple Commands
    # ***********************************************
    #asked.extend(["Turn on the Living Room lamps."])
    #asked.extend(["Turn down the Living Room lamps to 75%."])
    #asked.extend(["Turn on the Lower Living Room overhead lights."])
    #asked.extend(["Turn on the Higher Living Room overhead lights."])
    #asked.extend(["Turn on the Living Room lamp against the wall"])
    #asked.extend(["Turn on the Living Room lamps by the couch"])
    #asked.extend(["Turn off Carol's lamp in the master bedroom"])
    #asked.extend(["Turn off all of the lights on the first floor."])
    #asked.extend(["Turn on the lights under the cabinets in the kitchen."])
    #asked.extend(["Turn on the lights above the counter in the kitchen."])
    #asked.extend(["Turn on all of the lights in the house."])
    #asked.extend(["Turn on the kitchen pendant lights."])
    #asked.extend(["Turn off all lights."])
    #asked.extend(["Turn on the lights by the slider."])
    #asked.extend(["Turn on the outside lights."])
    #asked.extend(["Activate Movie Mode."])
    #asked.extend(["Turn on for what."])
    #asked.extend(["What's the status of the lights in the house."])

    # ***********************************************
    #             Intermediate Commands
    # ***********************************************
    #asked.extend(["Turn on all lights in the house other than the master bedroom."])
    #asked.extend(["Turn on all lights in the living room except for the lamp by the living room wall."])
    #asked.extend(["Turn on all lights in the living room except the lamp by the wall in the living room."])
    #asked.extend(["Turn on all lights in the living room except the lamp along the wall."])
    #asked.extend(["Turn on all lights in the living room except the lamp by the couch."])
    #asked.extend(["Turn on all lights in the living room except the overhead lights."])
    #asked.extend(["Turn off all lights in the kitchen except for the overhead lights."])
    #asked.extend(["Turn on all lights in the kitchen except for those under the cabinet."])
    #asked.extend(["Turn off all lights in the kitchen except for the under cabinet lights."])
    #asked.extend(["Turn off all lights in the kitchen except those over the counter."])
    #asked.extend(["Turn on all lights in the kitchen except those over the peninsula."])
    #asked.extend(["Turn off all lights in the kitchen except for those by the nook."])
    #asked.extend(["Turn off all lights on the first floor except the under cabinet lights in the kitchen."])
    #asked.extend(["Turn off all lights on the first floor except the under cabinet lights in the kitchen."])
    
    # ***********************************************
    #             Advanced Commands
    # ***********************************************
    #asked.extend(["Turn on Matt and Carol's lamps in the Master Bedroom."])
    #asked.extend(["Turn off all lights in the kitchen and foyer."])
    #asked.extend(["Turn off all lights in the kitchen and turn on the under counter lights."])
    #asked.extend(["Turn on all lights in the kitchen but the under counter lights."])
    #asked.extend(["Turn on all lights in the kitchen but turn off the under counter lights."])
    #asked.extend(["Turn on all lights on the first floor but those in the living room."])

    # ***********************************************
    #     Let's Face It, It's Not Gonna Happen
    #       AKA Now you're just showing off
    # ***********************************************
    #asked.extend(["Turn on all lights in the house other than the master bedroom and the 2nd floor landing or the basement."])
    #asked.extend(["Turn off all lights in the kitchen and turn on the living room lights except for the light by the wall and turn off the master bedroom lights except for carol's lamp."])
    #*asked.extend(["Turn off all lights in the kitchen and turn on the living room lights except for the light by the wall and turn off the master bedroom lights except turn on carol's lamp."])

    '''
    * means the command doesn't exactly work, but the commands aren't strictly speaking proper English so I don't feel bad about it.
    '''

    # Test mode to use sample commands above
    if test:
        if sample or offline:
            for asks in asked:
                cmdFromEmail(asks)
            return
        else:
            if test:
                i=1
                while(i<=10):
                    print i
                    pingEmail()
                    sleep(polling_freq)
                    i = i+1
            return

    # Run "indefinitely" mode
    while(1):
        pingEmail()
        sleep(polling_freq)


def pingEmail():
    logging.debug('ping')

    try:
        # Initiate imap email connection
        # Cannot reuse connection to always have most up to date email list
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(mail_username, mail_password)
        ###print mail.list() # list of folders aka labels in gmail.
    
        mail.select(source_folder_name) # connect to folder (i.e. Inbox)

        # Limit to just emails with 'InsteonCommandCentral' in the subject line
        result, data = mail.uid('search', None, '(HEADER Subject "'+target_subject_line+'")')
    
        # Make a backup copy of the data for use later, so we can delete the email now
        datab = data

        if data == ['']: # Escape when no matching email is found
            logging.debug('No matching email(s) found')
            return
        else:
            logging.info('Email found')
            
        # Begin to parse email content
        latest_email_uid = data[0].split()[-1]
        result, data = mail.uid('fetch', latest_email_uid, '(RFC822)')
        raw_email = data[0][1]
        email_message = email.message_from_string(raw_email)

        ###Debug statements to print content from email message
        #print email.utils.parseaddr(email_message['From'])
        #print get_first_text_block(email_message)
        #print email_message.items() # print all headers
    
        # The message comes through with extra text added by IFTTT so...
        # split at 'IFTTT', strip extra white space, and send [0] for logic processing
        asked = get_first_text_block(email_message)
        asked = asked.lower().split('ifttt')[0].strip()
        logging.debug('Emailed request: '+asked)
        cmdFromEmail(asked)

        if dest_folder_name == '':
            # Just send the email right to Trash
            logging.debug('Move email to trash')
            mov, data = mail.uid('STORE', latest_email_uid , '+FLAGS', '(\Deleted)')
            mail.expunge()
        else:
            # Create a backup copy
            # Gmail will autocreate a label for anything that doesn't exist already
            logging.debug('Move email to ' + dest_folder_name)
            result = mail.uid('COPY', latest_email_uid, dest_folder_name)
            if result[0] == 'OK':
                mov, data = mail.uid('STORE', latest_email_uid , '+FLAGS', '(\Deleted)')
                mail.expunge()
        
        mail.close()
        mail.logout()
    except imaplib.IMAP4_SSL.abort:
        return
    except:
        return
 
# note that if you want to get text content (body) and the email contains
# multiple payloads (plaintext/ html), you must parse each message separately.
# use something like the following: (taken from a stackoverflow post)
def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return email_message_instance.get_payload()

def cmdFromEmail(asked):

    # Declare global so we can edit it
    # Then replace the global variable with the user configuration options
    global defaultcmd
    defaultcmd = defaultcmd.replace('%USERNAME%',USERNAME).replace('%PASSWORD%',PASSWORD).replace('%IP%',IPADDRESS)

    omit_list = []

    # Save me from using .lower() in virtually every string operation
    asked = asked.lower()
    logging.debug('cmdFromEmail(asked="' + asked + '")')

    # Check if we're dealing with Scene Modes
    if (asked.find('mode') != -1) or (asked.find('scene') != -1):
        sceneLookup(asked)
        return

    # Check if we just need to check on status
    if (asked.find('status') != -1):
        emailStatus()
        return

    # Careful with keyword 'but'
    # Treat as 'except' unless 2nd part includes an action then treat as and
    if asked.find('but') != -1:
        asks = asked.split('but')
        if containsAction(asks[1]):
            asked = asked.replace('but','and')
        else:
            asked = asked.replace('but','except')
            
    # Careful with keyword 'and'
    # Split on keyword 'and' if [1] includes an action
    # Otherwise treat as action from [0] applies to both parts
    if asked.find('and') != -1:
        asks = asked.split('and')
        if containsAction(asks[1]):
            # For each portion of the command check for device name/location:
            # all, house, porch, outside, foyer, kitchen, living (room), family (room), nook, master, matt, carol, bedroom
            for ask in reversed(asks):
                omit_list = processCmd(ask,omit_list)
            return
        else:
            processCmd(asked,omit_list)
    else:
        processCmd(asked,omit_list)

def containsAction(asked):
    if asked.find('turn')  != -1:
        return True
    elif asked.find('set') != -1:
        return True
    elif asked.find('dim') != -1:
        return True
    elif asked.find('%')   != -1:
        return True
    else:
        return False

def processCmd(asked,omit_list):
    logging.debug('-processCmd(asked="' + asked + '",' + str(omit_list) + ')')

    logging.info(asked)

    # Replace word choice 'other than/then' with 'except' to simplify logic
    if asked.find('other than') != -1:
        asked = asked.replace('other than','except')
            
    # In case Siri doesn't use the correct word choice
    if asked.find('other then') != -1:
        asked = asked.replace('other then','except')

    # Split on 'except' and create a Device ID list
    # which we'll use as the basis to omit from the final command we fire
    if asked.find('except') != -1:
        asks = asked.split('except')

        for ask in reversed(asks):
            # We use the omit list from sunsequent parts of the command
            # to determine what should be disregarded
            omit_list = roomLookup(ask,asked,omit_list)
            #TODO: decide if omit_list should be extended or simply overwritten

            # But at the end we do need a list of devices that still need to be acted upon
            did_list = omit_list

    else:
        did_list = roomLookup(asked, asked, omit_list)
            
    # Discern action (i.e. turn on/off, (up/down/set/dim) to xyz%)
    lightLevelHex = actionLookup(asked)
        
    # Fire command for all devices found unless their status is already what we would be setting it to anyways
    logging.debug('expecting: '+str(len(did_list)))

 
    fireCmd(did_list,lightLevelHex)

    logging.debug('-processCmd returning: ' + str(did_list))

    # We'll return did_list as we'll use execute commands in reverse order and omit them from parts
    # that they should be ignored from (thus preventing lights from being turned on and then off
    # when they were off and we wanted them off or vice-versa)
    return did_list

# Actually perform the execution
def fireCmd(did_list,lightLevelHex):
    logging.debug('--fireCmd(' + str(did_list) + ',"' + lightLevelHex + '") - ' + str(len(did_list)) + ' devices')
    
    device_name_length = 0
    for did in did_list:
        temp = len(deviceNameLookup(did))
        if temp > device_name_length:
            device_name_length = temp
            
    i=1
    for did in did_list:
        logging.info(str(i).rjust((len(did_list)/10)+1) + ') Set Device ' + deviceNameLookup(did).ljust(device_name_length) + ' (' + did + ') to LightLevel ' + lightLevelHex)

        if did.find('ABCD') == -1:
            while not compareLightLevel(getLightLevel(did),lightLevelHex):
                setLightLevel(did,lightLevelHex)
            
        i=i+1
        
    return

def compareLightLevel(currentSetting,desiredSetting):
    logging.debug('--compareLightLevel(' + currentSetting + ',' + desiredSetting + ')')
    if offline:
        return True
    
    # Issues with 'is not' trying !=
    if str(currentSetting).strip() != str(desiredSetting).strip():
        logging.debug('Light Setting: ' + currentSetting + ' but should be: "' + desiredSetting + '"')
        return False
    else:
        return True

# Query for the name of the device with the given value
def deviceNameLookup(did):
    devkey = (key for key,value in devices.items() if value==did).next()
    return (value for key,value in devname.items() if key==devkey).next()

# Retrieve device status
def getLightLevel(did):
    logging.debug('--getLightLevel(' + did + ')')
        
    currentSetting ='ZZ'
    
    # Prepare & fire command to check Device Status
    chkStatus = defaultcmd+'/sx.xml?%ZZZZZZ%=1900'.replace('%ZZZZZZ%',did)
    logging.debug('--Check Status: ' + chkStatus)

    content = loadUrl(chkStatus)

    if offline:
        return currentSetting
                
    # Parsing Attempt #1
    #currentSetting = content[content.find(did)+10:content.find(did)+12]

    # Parsing Attempt #2
    currentSetting = content.split(did)[1]
    currentSetting = currentSetting[currentSetting.find('"')-2:currentSetting.find('"')]

    # Prep & fire command to clear Insteon Hub's buffer
    clrBufferCmd = defaultcmd+'/1?XB=M=1'
    loadUrl(clrBufferCmd)

    logging.debug('--return from getLightLevel')

    return currentSetting

# Set device status
def setLightLevel(did,lightLevelHex):
    
    # Update the command with the Light Level and device ID & fire the command
    runcmd = defaultcmd+'/3?0262' + did + '0F11' + lightLevelHex + '=I=3'
    if offline:
        logging.info('Set Device ' + did + ' to LightLevel ' + lightLevelHex)
    loadUrl(runcmd)
    sleep(0.15) # allow some time to pass for the command to be received and execute

    # Prep & fire command to clear Insteon Hub's buffer
    clrBufferCmd = runcmd+'/1?XB=M=1'
    if not offline:
        loadUrl(clrBufferCmd)

    return

# Utility method to load URLs
def loadUrl(cmd):
    logging.debug('---loadURL("' + cmd + '")')
        
    if offline:
        return ''
    
    resp = urllib.urlopen(cmd)
    content = resp.read()
    resp.close()
    
    return content

# Check for the status of all and either print or email them out
def emailStatus():
    # Check to make sure this is possible
    if (smtp_server == '') or (smtp_port == ''):
        logging.error('ERROR: SMTP Server or Port not configured, unable to process request.')
        return
    
    # Get the list of all devices
    did_list = deviceLookup('wholehouse','',[])

    # Assemble the list and status for each light into a string
    status = '\n' # The leading '/n' separates the message from the headers
    for did in did_list:
        if did.find('ABCD') == -1:
            lightLevelHex = getLightLevel(did)
            if lightLevelHex != 'XX':
                status = status + deviceNameLookup(did) + ' : ' + ('On' if int(lightLevelHex,16) > 0 else 'Off') + '\n'

    # Now use the device statuses
    logging.debug(status)
    if not offline:
        # Prepare an email message
        fromaddr = mail_username
        toaddr = mail_username
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = 'Insteon Hub: Device Status'
        body = status
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        
        # Connect to the SMTP Server and send email message
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(mail_username, mail_password)
        server.sendmail(mail_username, mail_username, text)

        logging.info('Status email sent.')

# Lookup scenes by keywords in asked
# Translates to device ID list
# Alternatively, could just do a lookup for the scene ID and fire command like this:
# http://X.X.X.X:25105/0?122=I=0 (122 = FAST ON command (12) to scene 2)
# Scene Actions: 11=On, 12=Fast On, 13=Off, 14=Fast Off, 15=Brighten, 16=Dim
def sceneLookup(asked):
    logging.debug('-sceneLookup(asked="' + asked + '")')
        
    # METHOD 1 - Translation
    # Step 1: Assemble 2 lists (who's in and who's out)

    # MOVIE SCENE MODE
    if asked.find('movie') != -1:
        omit_list = []
                
        room = 'under cabinet'
        did_list_on = roomLookup(room,room,omit_list)
        omit_list.extend(did_list_on)
        fireCmd(did_list_on,'FF')   # turn on lights
        
        room = 'living room lamps'
        did_list_on = roomLookup(room,room,omit_list)
        omit_list.extend(did_list_on)
        fireCmd(did_list_on,'7F')   # set lights to 50%
        
        room = 'living room'
        did_list_off = did_list = roomLookup(room,room,did_list_on)

        room = 'kitchen'
        did_list_off.extend(roomLookup(room,room,did_list_on))

    # Step 2: Process and fire commands for both lists
    fireCmd(did_list_on,'FF')
    fireCmd(did_list_off,'00')

    logging.debug('-sceneLookup return')

    return

    # METHOD 2 - Scene URL as 1 step,but not as reliable I've found
    if asked.find('movie') != -1:
        scene_num = '2'
        speed = '12'

    # Update URL format for scenes
    sceneCmd = runcmd.split('/3')[0]+'/0?' + speed + scene_num + '=I=0'
    
    # Fire scene command
    loadUrl(sceneCmd)

    logging.debug('-sceneLookup return')

    return

# Lookup rooms by keywords in asked
def roomLookup(asked,asked_orig,omit_list):
    logging.debug('--roomLookup("' + asked + '","' + asked + '",' + str(omit_list) + ')')
    
    loccode = ''
    modifier = ''
    idlist = []

    # BASEMENT
    if (asked.find('basement') != -1) or (asked.find('cellar') != -1):
        loccode = 'base'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))

    # FIRST FLOOR
    if (asked.find('first floor') != -1) or (asked.find('first level') != -1):
        loccode = 'fl1_all'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))

    # FOYER
    if asked.find('foyer') != -1:
        loccode = 'foyer'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
        
    # OUTSIDE LIGHTS
    if asked.find('front door') != -1:
        loccode = 'porch'
        modifier = 'door'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    if (asked.find('porch') != -1) or (asked.find('outdoor') != -1) or ((asked.find('outside') != -1) and not (asked.find('bedroom') != -1)):
        loccode = 'porch'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))

    # LIVING ROOM
    if asked.find('wall') != -1:
        loccode = 'lr'
        modifier = 'wall'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    elif asked.find('couch') != -1:
        loccode = 'lr'
        modifier = 'couch'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    elif (asked.find('living') != -1) or (asked.find('family') != -1):
        loccode = 'lr'
        if (asked.find('fan') != -1):
            modifier = 'fan'
        elif (asked.find('lamps') != -1):
            modifier = 'all lamps'
        else:
            modifier = 'all lights'
        #we're going to hold out for overhead lighting later, so only get IDs if 'overhead' isn't present
        if asked.find('overhead') == -1:
            idlist.extend(deviceLookup(loccode,modifier,omit_list))

    # LIVINGROOM/KITCHEN
    if asked.find('overhead') != -1:
        if asked.find('kitchen') != -1:
            loccode = 'ktch'
            modifier = 'ohead'
            idlist.extend(deviceLookup(loccode,modifier,omit_list))
        elif asked_orig.find('kitchen') != -1:
            loccode = 'ktch'
            modifier = 'ohead'
            idlist.extend(deviceLookup(loccode,modifier,omit_list))
        elif (asked.find('living') != -1) or (asked.find('family') != -1):
            loccode = 'lr'
            if (asked.find('lower') != -1):
                modifier = 'ohlow'
            elif (asked.find('higher') != -1):
                modifier = 'ohhigh'
            else:
                modifier = 'overhead'
            idlist.extend(deviceLookup(loccode,modifier,omit_list))
        elif (asked_orig.find('living') != -1) or (asked_orig.find('family') != -1):
            loccode = 'lr'
            if (asked.find('lower') != -1):
                modifier = 'ohlow'
            elif (asked.find('higher') != -1):
                modifier = 'ohhigh'
            else:
                modifier = 'overhead'
            idlist.extend(deviceLookup(loccode,modifier,omit_list))
            
    # KITCHEN
    elif ( (asked.find('under') != -1) and ( (asked.find('cabinet') != -1) or (asked.find('counter') != -1) ) ):
        loccode = 'ktch'
        modifier = 'ucabs'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    elif ( ((asked.find('over') != -1) or (asked.find('above') != -1) ) and (asked.find('counter') != -1) ):
        loccode = 'ktch'
        modifier = 'ucabs'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    elif asked.find('nook') != -1:
        loccode = 'ktch'
        modifier = 'nook'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    elif (asked.find('peninsula') != -1) or (asked.find('pendant') != -1):
        loccode = 'ktch'
        modifier = 'pen'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    elif asked.find('slider') != -1:
        loccode = 'ktch'
        modifier = 'slider'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    elif asked.find('kitchen') != -1:
        loccode = 'ktch'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    
    # SECOND FLOOR
    if (asked.find('second floor') != -1) or (asked.find('second level') != -1):
        loccode = 'fl2_all'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))

    # LANDING
    if (asked.find('outside bedroom') != -1) or (asked.find('landing') != -1):
        loccode = 'fl2_landing'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))

    # MASTER
    if ((asked.find('master') != -1) or (asked.find('bedroom') != -1)) and (asked.find('carol') == -1) and (asked.find('matt') == -1):
        loccode = 'mb'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    if asked.find('matt') != -1:
        loccode = 'mb'
        modifier = 'matt'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    if asked.find('carol') != -1:
        loccode = 'mb'
        modifier = 'carol'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
        
    # WHOLE HOUSE
    if asked.find('house') != -1:
        loccode = 'wholehouse'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
    if asked.find('for what') != -1:
        loccode = 'wholehouse'
        modifier = ''
        idlist.extend(deviceLookup(loccode,modifier,omit_list))
        
    # SPECIAL CASE = WHOLE HOUSE
    # There is a use case where you don't specify the location, but mean literally all lights in the house
    if idlist == []:
        loccode = 'wholehouse'
        idlist.extend(deviceLookup(loccode,modifier,omit_list))

    logging.debug('--roomLookup returning: ' + str(idlist))

    # return list of device IDs to reference
    # should all be related to the same action that'll be performed
    # different actions should be performed individually
    return idlist
    
def deviceLookup(location,modifier,omit_list):
    dids = ''

    logging.debug('---deviceLookup(location="' + location + '",modifier="' + modifier + '",omit_list=' + str(omit_list) + ')')

    # ***********************************************
    #   generalized locations (ones with modifiers)
    # ***********************************************
    
    # for the living room light along the wall
    if modifier == 'wall':
        dids = [devices.get('lr_1lamp')]

    # for the living room lights behind the couch
    elif modifier == 'couch':
        dids = [devices.get('lr_3lamps')]

    # for the living room lamps
    elif (location == 'lr') and (modifier == 'all lamps'):
        dids = [devices.get('lr_1lamp'),devices.get('lr_3lamps')]

    # for all living room lights
    elif (location == 'lr') and (modifier == 'all lights'):
        dids = dictLookup(location)

    # for the lower overhead living room lights
    elif (location == 'lr') and (modifier == 'ohlow'):
        dids = [devices.get('lr_ohlow')]

    # for the higher overhead living room lights
    elif (location == 'lr') and (modifier == 'ohhigh'):
        dids = [devices.get('lr_ohhigh')]

    # for the overhead living room lights
    elif (location == 'lr') and (modifier == 'overhead'):
        dids = [devices.get('lr_ohlow'),devices.get('lr_ohhigh')]

    # for the living room fan
    elif (location == 'lr') and (modifier == 'fan'):
        dids = [devices.get('lr_fan')]
    
    # for any lights near the kitchen slider
    elif modifier == 'slider':
        dids = [devices.get('ktch_nook'),devices.get('ktch_pen')]

    # for the lights next to the front door
    elif modifier == 'door':
        dids = [devices.get('porch_door')]

    # for the lights outside
    elif location == 'porch':
        dids = [devices.get('porch_door'),devices.get('porch_ohead')]

    # for the lights over the nook
    elif modifier == 'nook':
        dids = [devices.get('ktch_nook')]

    # for the lights over the peninsula
    elif modifier == 'pen':
        dids = [devices.get('ktch_pen')]

    # for the lights over the peninsula
    elif modifier == 'ucabs':
        dids = [devices.get('ktch_ucabs')]

    # for the kitchen overhead lights
    elif (location == 'ktch') and (modifier == 'ohead'):
        dids = [devices.get('ktch_ohead_1'),devices.get('ktch_ohead_2'),devices.get('ktch_osink')]

    # for the light over the kitchen sink
    elif (location == 'ktch') and (modifier == 'osink'):
        dids = [devices.get('ktch_osink')]

    # for Matt's lamp in the master bedroom
    elif modifier == 'matt':
        dids = [devices.get('mb_matt')]

    # for Carol's lamp in the master bedroom
    elif modifier == 'carol':
        dids = [devices.get('mb_carol')]

    # for the basement
    elif modifier == 'slider':
        dids = [devices.get('ktch_nook'),devices.get('ktch_pen')]

    # ***********************************************
    #  specific locations (usually multiple lights)
    # ***********************************************
    elif location == 'wholehouse':
        dids = dictLookup('') # empty string used as a wildcard
    elif location == 'fl1_all':
        dids = dictLookup('ktch')
        dids.extend(dictLookup('lr'))
        omit_list.extend(deviceLookup('lr','fan',[]))
        dids.extend(dictLookup('foyer'))
    elif location == 'fl2_all':
        dids = dictLookup('mb')
        dids.extend(dictLookup('fl2_landing'))
    else:
        dids = dictLookup(location)

    logging.debug('---deviceLookup (before omitting): ' + str(dids))
    logging.debug('----omitting Device IDs: ' + str(omit_list))

    # Remove any in omit_list from did
    if omit_list != []:
        dids = [item for item in dids if item not in omit_list]

    logging.debug('---deviceLookup returning: ' + str(dids))
    
    return dids

def dictLookup(prefix):
    dictMatches = []
    
    for k in devices.keys():
        if str(k).startswith(prefix):
            dictMatches.extend([devices[k]])

    return dictMatches

def actionLookup(asked):
    logging.debug('--actionLookup(asked="' + asked + '")')
        
    lightLevelHex = ''
    
    if asked.find('%') != -1:
        # poor man's regex - trying to avoid any extra modules (like re)
        # if percentage is 1 digit
        if asked[asked.find('%')-2:asked.find('%')-1] == ' ':
           lightLevel = int(asked[asked.find('%')-2:asked.find('%')])
        # if percentage is 2 digits
        elif asked[asked.find('%')-3:asked.find('%')-2] == ' ':
            lightLevel = int(asked[asked.find('%')-3:asked.find('%')])
        # if percentage is 3 digits
        elif asked[asked.find('%')-4:asked.find('%')-3] == ' ':
           lightLevel = int(asked[asked.find('%')-4:asked.find('%')])

        # Validate Input
        if lightLevel > 100:
            lightLevel = 100

        # Need to convert inputted percentage to hex
        lightLevel = int(float(lightLevel)/100*255)
        lightLevelHex = str(hex(lightLevel).split('x')[1]).zfill(2).upper()

    elif ( (asked.find('turn') != -1) and (asked.find('off') != -1)) or (asked.find('turn down') != -1) or (asked.find('deactivate') != -1):
        lightLevelHex = '00'

    elif ( (asked.find('turn') != -1) and (asked.find('on') != -1)) or (asked.find('turn up') != -1) or (asked.find('activate') != -1):
        lightLevelHex = 'FF'

    logging.debug('--actionLookup returning LightLevelHex:"' + lightLevelHex + '"')

    return lightLevelHex

if __name__ == '__main__':
    main()
