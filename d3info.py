#! /usr/bin/python
import httplib
from HTMLParser import HTMLParser, HTMLParseError
import json
import csv
import argparse
import os, sys
try:
    from bs4 import BeautifulSoup
except importError:
    print "need to install BeautifulSoup (pip install BeautifulSoup)"

## --- Classes ---##
class artisan(object):
    def __init__(self, name):
        self.name = name
        self.recipeFolder = '{0.name}-recipe/'.format(self)
        self.trainedItems = 0
        self.taughtItems  = 0
        self.numItems     = 0
        self.reagentNames = []
        self.numReagents = 0
        self.upgradeItems = []
        self.numUpgrdItms = 0
    def __getattribute__(self,key):
        if key == 'numItems':   object.__setattr__(self, key, self.trainedItems + self.taughtItems)
        elif key == 'numReagents':  object.__setattr__(self, key, len(self.reagentNames))
        elif key is 'numUpgrdItms': object.__setattr__(self, key, len(self.upgradeItems))
        return object.__getattribute__(self, key)
    def update(self):
        self.numItems = self.trainedItems + self.taughtItems
        self.numReagents = len(self.reagentNames)
        self.numUpgrdItms = len(self.upgradeItems)

class profile(object):
    def __init__(self, name):
        self.name = name
        self.profBaseFldr = 'profiles/'
        self.profileFolder = '{0.profBaseFldr}{0.name}'.format(self)
        self.profLoc = 'profile/{0.name}'.format(self)
        self.heroLoc = '{0.profLoc}/hero/'.format(self)


## --- Functions ---##
def getDbData(character, verbose=False):
    character = character.lstrip('/').rstrip('/')
    profile = '/api/d3/{}'.format(character)

    #Host: us.battle.net
    try:    conn = httplib.HTTPConnection("us.battle.net")
    except: print("HTTP connection exception")

    try:    conn.request("GET", profile)
    except: print("HTTP connection request")

    if options.debug:
        print "Getting data for {}\t({})".format(character,profile),
#       conn.set_debuglevel(1)

    try:    charFile = conn.getresponse()
    except: print("HTTP connection getresponse")
    if options.debug:   print '\t', charFile.status, charFile.reason

    if charFile.status == 404:
        profile+='/'
        try:
            conn = httplib.HTTPConnection("us.battle.net")
            if options.debug:   print "\tTrying {}".format(profile),
            conn.request("GET", profile)
            charFile = conn.getresponse()
        except: print "Can't get info from {}" .format(profile)
        if options.debug:   print '\t', charFile.status, charFile.reason

    return charFile

def writeJsonFile(inputData, outputFile, verbose=False):
    if verbose: print "\tWritng JSON file to {}".format(outputFile)
    fh = open(outputFile, 'w')
    for line in inputData:
        fh.write(line)
    fh.close()
    return

def artisanInfo(jsonFile, artObj):
    print "=-=-= {} Data =-=-=".format(artObj.name.capitalize())
    if options.debug:   print '\tsaving artisan recipes to {0.recipeFolder}'.format(artObj)

    with os.tmpfile() as tmp_fh:
        csvTmpFd = csv.writer(tmp_fh)
        for tiers in jsonFile['training']['tiers']:
            for levels in tiers['levels']:
                for recipeType in levels:
                    if recipeType in ['trainedRecipes', 'taughtRecipes']:
                        recipe = None
                        for itemData in levels[recipeType]:
                            csvData = [ "{0[tier]}.{0[tierLevel]}".format(levels) ]
                            csvData.append(recipeType.strip('Recipes').capitalize())
                            if 'itemProduced' in itemData:
                                item_name = itemData['itemProduced']['name']
                                recipe = itemData['itemProduced']['tooltipParams']
                                csvData.extend([ item_name, itemData['itemProduced']['displayColor'] ])
                            if 'cost' in itemData:  csvData.extend([ itemData['cost'] ])

                            itemReagents = ['']*len(artObj.reagentNames)
                            for reagents in itemData['reagents']:
                                if reagents['item']['name'] not in artObj.reagentNames:
                                    artObj.reagentNames.append(reagents['item']['name'])
                                    itemReagents.append('')
                                itemReagents[artObj.reagentNames.index(reagents['item']['name'])]=reagents['quantity']
                            csvData.extend(itemReagents)

                            if options.remote and recipe is not None:
                                recipe_data = getDbData('data/{}'.format(recipe)).read()
                                slug = itemData['slug']
                                writeJsonFile(recipe_data, './{0.recipeFolder}{1}.json'.format(artObj,slug))

                            if recipeType == 'trainedRecipes':  artObj.trainedItems += 1
                            elif recipeType == 'taughtRecipes': artObj.taughtItems += 1
                            csvTmpFd.writerow(csvData)
        header = ['Tier', 'Trained/Taught', 'Item Name', 'Type', 'Gold Cost']
        header.extend(artObj.reagentNames)
        with open('{}Items.csv'.format(artObj.name), 'wb') as fh:
            tmp_fh.seek(0)
            dictRdrFd = csv.DictReader(tmp_fh, header)
            dictWtrFd = csv.DictWriter(fh, header)
            dictWtrFd.writeheader()
            for ln in dictRdrFd:
                dictWtrFd.writerow(ln)

    with os.tmpfile() as tmp_fh:
        csvTmpFd = csv.writer(tmp_fh)
        for tiers in jsonFile['training']['tiers']:
            for levels in tiers['levels']:
                csvData = [ "{}.{}".format(levels['tier'], levels['tierLevel']), levels['upgradeCost']]
                try:
                    upgradeReagents = ['']*len(artObj.upgradeItems)
                    for upgrade in levels['upgradeItems']:
                        if upgrade['item']['name'] not in artObj.upgradeItems:
                            artObj.upgradeItems.append(upgrade['item']['name'])
                            upgradeReagents.append('')
                        upgradeReagents[artObj.upgradeItems.index(upgrade['item']['name'])]=upgrade['quantity']
                        csvData.extend(upgradeReagents)
                except: pass
                csvTmpFd.writerow(csvData)
        header = ['Tier', 'Gold Cost']
        header.extend(artObj.upgradeItems)
        with open('{}Levels.csv'.format(artObj.name), 'wb') as fh:
            tmp_fh.seek(0)
            dictRdrFd = csv.DictReader(tmp_fh, header)
            dictWtrFd = csv.DictWriter(fh, header)
            dictWtrFd.writeheader()
            for ln in dictRdrFd:
                dictWtrFd.writerow(ln)

    print "found {0.numItems} items ({0.trainedItems} trained, {0.taughtItems} taught), " \
        "{0.numReagents} reagents, and {0.numUpgrdItms} upgrade items" \
        .format(artObj)
    return

def userInfo(jsonFile, profileObj):
    print "=-=-= Characters =-=-="
    csvData = ['Hero Name', 'Level', 'Class', 'HC/SC', 'Time Played', 'CharID']
    print "{}  {}   {}\t{} {}  {}".format(*csvData)

    lastHero = jsonFile['lastHeroPlayed']

    for hero_names in jsonFile['heroes']:
        characters = "{0[name]:<12} {0[level]:>2} {0[class]:>12}".format(hero_names)
        if hero_names['hardcore']:
            characters += " hardcore "
        else: characters += "\t      "
        characters += "{0:<5}".format(jsonFile['timePlayed'][hero_names['class']])
        characters += "\t{0:>8}".format(hero_names['id'])
        if hero_names['id'] == lastHero:
            characters += "  *"
        print characters

        if options.remote:
            char_data = getDbData('{0.heroLoc}/{1}'.format(profileObj,hero_names['id'])).read()
            heroName = hero_names['name']
            writeJsonFile(char_data, './{0.profileFolder}/{1}-{2}.json'.format(profileObj, heroName, hero_names['id']))


    print "=-=-= Kills =-=-="
    for kills in jsonFile['kills']:
        print "{:<16}  {:>6}".format(kills, jsonFile['kills'][kills])
    return


## --- Main ---##
parser = argparse.ArgumentParser(description='Get data using the Diablo 3 API', epilog='Writes data to current folder.')
parser.add_argument('-art', '--artisan', help='get data for artisans (Blacksmith & Jeweler)', action='store_true')
parser.add_argument('-p', '--profile', help='get data for specified profile', action='store')
parser.add_argument('--remote', help='actually fetch from battle.net', action='store_true')
parser.add_argument('--debug', help='print debuging info', action='store_true')
options = parser.parse_args()
print options
if options.artisan is False and not options.profile:
    parser.print_help()

if options.artisan:
    json_data=getDbData('data/artisan/', options.debug).read()
    writeJsonFile(json_data, './artisan.json', options.debug)
    jsonFile = json.loads(json_data)
    for artisans in jsonFile['artisans']:
        artisanObj = artisan(artisans['slug'])

        if options.remote:
            json_data=getDbData('data/artisan/{0.name}'.format(artisanObj), options.debug).read()
            if not os.access('./{0.recipeFolder}'.format(artisanObj), os.R_OK | os.W_OK):
                os.mkdir('./{0.recipeFolder}'.format(artisanObj))
            writeJsonFile(json_data, './{0.name}.json'.format(artisanObj), options.debug)
        else:
            if not os.access('./{0.recipeFolder}'.format(artisanObj), os.R_OK):
                sys.exit('./{0.recipeFolder} not readable'.format(artisanObj))
            json_data = open('./{0.name}.json'.format(artisanObj),'rb').read()
        jsonFile = json.loads(json_data)
        artisanInfo(jsonFile, artisanObj)

if options.profile:
    profObj = profile(options.profile)

    if options.remote:
        json_data = getDbData('{0.profLoc}'.format(profObj), options.debug).read()
        if not os.access('./{0.profBaseFldr}'.format(profObj), os.R_OK | os.W_OK):
            os.mkdir('./{0.profBaseFldr}'.format(profObj))
        if not os.access('./{0.profileFolder}'.format(profObj), os.R_OK | os.W_OK):
            os.mkdir('./{0.profileFolder}'.format(profObj))
        writeJsonFile(json_data, './{0.profileFolder}.json'.format(profObj),options.debug)
    else:
        if not os.access('./{0.profileFolder}.json'.format(profObj), os.R_OK):
            sys.exit('./{0.profileFolder}.json not readable'.format(profObj))
        if not os.access('./{0.profileFolder}'.format(profObj), os.R_OK):
            sys.exit('./{0.profileFolder} not readable'.format(profObj))
        json_data = open('./{0.profileFolder}.json'.format(profObj),'rb').read()
    jsonFile = json.loads(json_data)
    userInfo(jsonFile, profObj)
