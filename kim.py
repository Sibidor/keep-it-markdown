import sys
import os
import getopt
import gkeepapi
import keyring
import getpass
import re
import configparser
from pathlib import Path

KEEP_CACHE = 'kdata.json'
KEEP_KEYRING_ID = 'google-keep-token'
KEEP_NOTE_URL = "https://keep.google.com/#NOTE/"
CONFIG_FILE = "settings.cfg"
DEFAULT_SECTION = "SETTINGS"
USERID_EMPTY = 'add your google account name here'
OUTPUTPATH = 'mdfiles'

TECH_ERR = " Technical Error Message: "

CONFIG_FILE_MESSAGE = "Your " + CONFIG_FILE + " file contains to the following [" + DEFAULT_SECTION + "] values. Be sure to edit it with your information."
MALFORMED_CONFIG_FILE = "The " + CONFIG_FILE + " default settings file exists but has a malformed header - header should be [DEFAULT]"
UNKNOWNN_CONFIG_FILE = "There is an unknown configuration file issue - " + CONFIG_FILE + " or file system may be locked or corrupted. Try deleting the file and recreating it."
MISSING_CONFIG_FILE = "The configuration file - " + CONFIG_FILE + " is missing. Please check the documention on recreating it"
BADFILE_CONFIG_FILE = "Unable to create " + CONFIG_FILE + ". The file system issue such as locked or corrupted"


default_settings = {
    'google_userid': USERID_EMPTY,
    'output_path': OUTPUTPATH
    }


class ConfigurationException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg



def load_config():
    config = configparser.ConfigParser()
  
    try:
        cfile = config.read(CONFIG_FILE)
    except configparser.MissingSectionHeaderError:
        raise ConfigurationException(MALFORMED_CONFIG_FILE)
    except Exception:
        raise ConfigurationException(UNKNOWNN_CONFIG_FILE)
    
    configdict = {}
    if not cfile:
        config[DEFAULT_SECTION] = default_settings
        try:
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            raise (e)
    options = config.options(DEFAULT_SECTION)
    for option in options:
        configdict[option] = config.get(DEFAULT_SECTION, option)
    return configdict 
    

def keep_init():
    keepapi = gkeepapi.Keep()
    return keepapi


def keep_token(keepapi, userid):
    keep_token = keyring.get_password(KEEP_KEYRING_ID, userid)
    return keep_token


def keep_clear_keyring(keepapi, userid):
    try:
      keyring.delete_password(KEEP_KEYRING_ID, userid)
    except:
      return None
    else:
      return True


def keep_login(keepapi, userid, pw):
    try:
      keepapi.login(userid, pw)
    except:
      return None
    else:
      keep_token = keepapi.getMasterToken()
      keyring.set_password(KEEP_KEYRING_ID, userid, keep_token)
      return keep_token


def keep_resume(keepapi, keeptoken, userid):
    keepapi.resume(userid, keeptoken)


def keep_save_md_file(note_title, note_text, note_labels, note_date, note_created, note_updated, note_id):

    try:
      outpath = load_config().get("output_path")
      if outpath == OUTPUTPATH:
        if not os.path.exists(OUTPUTPATH):
          os.mkdir(OUTPUTPATH)

      md_file = Path(outpath, note_title + ".md")
      if md_file.exists():
        note_title = note_title + note_date
      md_file = Path(outpath, note_title + ".md")
      f=open(md_file,"w+", errors="ignore")
      f.write(note_text + "\n")
      f.write("\n" + note_labels + "\n\n")
      f.write("Created: " + note_created + "      Updated: " + note_updated + "\n\n")
      f.write(KEEP_NOTE_URL + note_id)

      f.close
    except Exception as e:
      raise Exception("Invalid md export file path: " + str(md_file) + "\r\n" + TECH_ERR + repr(e))


  


def keep_query_convert(keepapi, keepquery):

    if keepquery == "--all":
      gnotes = keepapi.all()
    else:
      if keepquery[0] == "#":
        gnotes = keepapi.find(labels=[keepapi.findLabel(keepquery[1:])])
      else:
        gnotes = keepapi.find(query=keepquery, archived=False, trashed=False)

    for gnote in gnotes:
      note_date = re.sub('[^A-z0-9-]', ' ', str(gnote.timestamps.created).replace(":","").replace(".", "-"))
      
      if gnote.title == '':
        gnote.title = note_date

      note_title = re.sub('[^A-z0-9-]', ' ', gnote.title)[0:99]
 
      note_text = gnote.text.replace('”','"').replace('“','"').replace("‘","'").replace("’","'").replace('•', "-").replace(u"\u2610", '[ ]').replace(u"\u2611", '[x]').replace(u'\xa0', u' ').replace(u'\u2013', '--')

      note_label_list = gnote.labels 
      labels = note_label_list.all()
      note_labels = ""
      for label in labels:
        note_labels = note_labels + " #" + str(label).replace(' ','-')

      print (note_title)
      #print (note_text)
      print (note_labels)
      print (note_date + "\r\n")

      keep_save_md_file(note_title, note_text, note_labels, note_date, str(gnote.timestamps.created), str(gnote.timestamps.updated), str(gnote.id))






def ui_check_opts(argv):

  try:
      pw_reset = False
      argv = sys.argv[1:]
      opts, args = getopt.getopt(argv,"r:")
      for opt, arg in opts:
        if opt == "-r" and arg == "pw":
          pw_reset = True
        else:
          raise Exception
  except:
      print ("\r\nIncorrect syntax for resetting your password. Please use: 'python kim.py -r pw'") 
      exit()

  return (pw_reset)


def ui_welcome_config():
    print ("\r\nWelcome to Keep it Markdown or KIM!\r\n")
    return load_config()


def ui_login(keepapi, defaults, keyring_reset):

    try:
      userid = defaults.get("google_userid").strip().lower()
    
      if userid == USERID_EMPTY:
        userid = input('Enter your Google account username: ')
      else:
        print("Your Google account name in the " + CONFIG_FILE + " file is: " + userid + " -- Welcome!")
  
      if keyring_reset:
        print ("Clearing keyring")
        keep_clear_keyring(keepapi, userid)
    
      ktoken = keep_token(keepapi, userid)
      if ktoken == None:
        pw = getpass.getpass(prompt='Enter your Google Password: ', stream=None) 
        print ("\r\n")

        ktoken = keep_login(keepapi, userid, pw)
        if ktoken:
          print ("You've succesfully logged into Google Keep! Your password has been securely stored in this computer's keyring.")
        else:
          print ("Invalid Google userid or pw! Please try again.")

      else:
        print ("You've succesfully logged into Google Keep using local keyring password!")

      keep_resume(keepapi, ktoken, userid)
      return (ktoken)

    except:
      print ("\r\nUsername or password is incorrect") 
      exit()


def ui_query(keepapi):

    kquery = "kquery"
    while kquery:
      kquery = input("\r\nEnter a keyword search, label search or '--all' for all notes to convert to Markdown or just press Enter to exit: ")
      if kquery:
        keep_query_convert(keepapi, kquery)
 


def main(argv):

  try:
    kapi = keep_init()

    ui_login(kapi, ui_welcome_config(), ui_check_opts(argv))

    ui_query(kapi)
      
      
  except Exception as e:
    print (e)
 

if __name__ == '__main__':
    main(sys.argv)
