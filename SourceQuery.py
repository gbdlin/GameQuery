#!/usr/bin/python
# -*- coding: utf-8 -*-

import asyncore
import socket
import time
from GameQuery import QueryPacket


PACKETSIZE=1400

WHOLE=-1
SPLIT=-2

# A2S_INFO
A2S_INFO = ord('T')
A2S_INFO_OLD_REPLY = ord('m')       # info packet from old (p.47) GoldSource servers. 
A2S_INFO_STRING = 'Source Engine Query'
A2S_INFO_REPLY = ord('I')

# A2S_PLAYER
A2S_PLAYER = ord('U')
A2S_PLAYER_REPLY = ord('D')

# A2S_RULES
A2S_RULES = ord('V')
A2S_RULES_REPLY = ord('E')

# S2C_CHALLENGE
CHALLENGE = -1
A2S_SERVERQUERY_GETCHALLENGE = ord('W');
S2C_CHALLENGE = ord('A')

######################
# Split packet type
SPLIT_GOLDSOURCE    = 0;
SPLIT_SOURCE        = 1;
SPLIT_COMPRESSED    = 2;


######################
# The Ship modes:
SHIP_GAME_MODES     = (
    "Hunt",
    "Elimination",
    "Duel",
    "Deathmatch",
    "VIP Team",
    "Team Elimination"
);

class SourceQuery(asyncore.dispatcher):
    def __init__(self, server, timeout=10, extrainfo={}):
        asyncore.dispatcher.__init__(self);
        
        self.remote = server;
        self.timeout = timeout;
        self.extraInfo = extrainfo;
        
        
        self.reset();
        
    def reset(self):
        self.splitted = {};
        
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM);
        self.socket.settimeout(self.timeout);
        
        infoPacket = QueryPacket();
        infoPacket.putLong(WHOLE);
        infoPacket.putByte(A2S_INFO);
        infoPacket.putString(A2S_INFO_STRING);
        
        playersPacket = QueryPacket();
        playersPacket.putLong(WHOLE);
        playersPacket.putByte(A2S_INFO);
        playersPacket.putLong(CHALLENGE);
        
        rulesPacket = QueryPacket();
        rulesPacket.putLong(WHOLE);
        rulesPacket.putByte(A2S_INFO);
        rulesPacket.putLong(CHALLENGE);
        
        self.buffer = infoPacket.getvalue();
        self.queryResponse = {"ip":self.remote[0], "port":self.remote[1]};
        self.queryResponse.update(self.extraInfo);
        self.queryList = ["rules","players","info"]; # reversed order, so we can easly pop it from list.
        self.oldInfoResponse = False;
        self.challenge = CHALLENGE;
        
    def connect(self):
        asyncore.dispatcher.connect(self, self.remote);
    
    def handle_connect(self):
        pass
    
    def handle_close(self):
        self.close();
        
    def handle_expt(self):
        self.close();
        
    def handle_read(self):
        recPacket = self._get_packet();
        if recPacket:
            type = recPacket.getByte();
            if type == S2C_CHALLENGE:
                # Challenge number
                self.challenge = recPacket.getLong();
                
            elif type == A2S_INFO_REPLY and (("info" in self.queryList) or self.oldInfoResponse):
                # Info query response. We want it only once!
                self._parse_info(recPacket)
                
                # When saved, remove from list, so won't be queried again
                if self.oldInfoResponse:
                    self.oldInfoResponse = False;
                    self.queryResponse['protocol'] = "47+48";
                else:
                    self.queryList.remove("info");
                
            elif type == A2S_PLAYER_REPLY and "players" in self.queryList:
                # Players list query response. We want it only once!
                # On GoldSource servers with dproto, player list might come in response for Info query!
                # Info query also comes, as well... I don't know why it happens (some kind of hybrid response for p.47 clients)
                # that's why i added controling for not querying something again ;)
                self._parse_players(recPacket);
                
                # When saved, remove from list, so won't be queried again
                self.queryList.remove("players");
                
            elif type == A2S_RULES_REPLY and "rules" in self.queryList:
                # Rules list query response. We want it only once!
                self._parse_rules(recPacket);
                
                # When saved, remove from list, so won't be queried again
                self.queryList.remove("rules");
            elif type == A2S_INFO_OLD_REPLY and "info" in self.queryList:
                # OLD Info query response. Old GoldSource servers (p.47) gives it.
                # It also comes together with new info response from servers with dproto with hybrid (p.47+p.48) query
                # It has less info, so we prefer new response. It will be saved to temp field.
                # This field will be deleted when new response comes. When there is no new response, values will be moved to normal fields
                
                self._parse_oldinfo(recPacket);
                
                # We also want it only once, as usualy :) But we will mark it different way.
                self.queryList.remove("info");
                self.oldInfoResponse = True; # we make sure that when new response will come, it will be parsed and old will be removed
            
            if self.queryList:
                toSend = self.queryList[-1];
                
                if toSend == "info":
                    infoPacket = QueryPacket();
                    infoPacket.putLong(WHOLE);
                    infoPacket.putByte(A2S_INFO);
                    infoPacket.putString(A2S_INFO_STRING);
                    
                    self.buffer = infoPacket.getvalue();
                    
                elif toSend == "players":
                    playersPacket = QueryPacket();
                    playersPacket.putLong(WHOLE);
                    playersPacket.putByte(A2S_PLAYER);
                    playersPacket.putLong(self.challenge);
                    
                    self.buffer = playersPacket.getvalue();
                    
                elif toSend == "rules":
                    rulesPacket = QueryPacket();
                    rulesPacket.putLong(WHOLE);
                    rulesPacket.putByte(A2S_RULES);
                    rulesPacket.putLong(self.challenge);
                    
                    self.buffer = rulesPacket.getvalue();
            else:
                if self.oldInfoResponse:
                    self.queryResponse.update(self.temp);
                self.close();
        else:
            print "empty?";
            
    
    def _get_packet(self):
        # if self.splitted:
            # packet = QueryPacket(self.recv(PACKETSIZE))

            # if packet.getLong() == SPLIT and packet.getLong() == self.splitted['reqid']:
                # self.splitted['total'] = packet.getByte()
                # num = packet.getByte()
                # self.splitted['splitsize'] = packet.getShort()
                # self.splitted['result'][num] = packet.read()
            # else:
                # return;
                
            # if self.splitted['total']-1 == num:
                # packet = QueryPacket("".join(self.splitted['result']))

                # self.splitted = {};
                
                # if packet.getLong() == WHOLE:
                    # return packet
                # else:
                    # return;
            # else:
                # return;
        # else:
            packet = QueryPacket(self.recv(PACKETSIZE));
            type = packet.getLong()
            if type == WHOLE:
                return packet;

            elif type == SPLIT:
                # handle split packets
                
                splittedId = packet.getLong()
                
                splitted = {}
                if splittedId in self.splitted:
                    splitted = self.splitted[splittedId];
                else:
                    packet.seek(1, 1)
                    if packet.getLong() == -1:
                        splitted['type'] = SPLIT_GOLDSOURCE;
                        packet.seek(-5, 1)
                    else:
                        packet.seek(-1, 1);
                        if packet.getLong() == -1:
                            splitted['type'] = SPLIT_SOURCE;
                        else:
                            splitted['type'] = SPLIT_COMPRESSED;
                        packet.seek(-8, 1);
                    
                    splitted['result'] = "";
                    #self.close();
                    #return;
                if splitted['type'] == SPLIT_GOLDSOURCE:
                    temp = packet.getByte();
                    splitted['total'] = 0x0F & temp;
                    num = temp>>4;
                    splitted['result']+= packet.read();
                
                elif splitted['type'] == SPLIT_SOURCE:
                    splitted['total'] = packet.getByte()
                    num = packet.getByte()
                    splitted['splitsize'] = packet.getShort()
                    splitted['result']+= packet.read()
                    
                self.splitted[splittedId] = splitted;
                
                if splitted['total'] == num+1:
                    packet = QueryPacket(splitted['result'])

                    splitted = {};
                    
                    if packet.getLong() == WHOLE:
                        return packet
                    else:
                        return;
                else:
                    return;
            return;
    
    def _parse_oldinfo(self, packet):
        
        # old query response goes into temp
        self.temp = {}
        
        self.temp['address']                    = packet.getString();       # dummy value... we are arleady know that...
        self.temp['hostname']                   = packet.getString();
        self.temp['mapname']                    = packet.getString();
        self.temp['game']                       = packet.getString();
        self.temp['gamename']                   = packet.getString();
        self.temp['playerscount']               = packet.getByte();
        self.temp['playersmax']                 = packet.getByte();
        self.temp['protocol']                   = packet.getByte();
        servertype = chr(packet.getByte()).upper();
        self.temp['servertype']                 = "Dedicated" if servertype == 'D' else \
                                                  "Listen" if servertype == 'L' else \
                                                  "HLTV" if servertype == 'P' else \
                                                  "Undefined";
        os = chr(packet.getByte()).upper();
        self.temp['os']                         = "Windows" if os == "W" else \
                                                  "Linux" if os == "L" else \
                                                  "Undefined";
        self.temp['password']                   = packet.getByte() == 1;
        mod = packet.getByte() == 1;
        if mod:
            mod = {};
            mod['link']                         = packet.getString();
            mod['download']                     = packet.getString();
            mod['null']                         = packet.getByte();
            mod['version']                      = packet.getLong();
            mod['size']                         = packet.getLong();
            mod['type']                         = "Single/multi-player" if packet.getByte() == 0 else \
                                                  "Multiplayer only";
            mod['dll']                          = "Own dll" if packet.getByte() == 1 else \
                                                  "Half-Life dll";
            self.temp['mod'] = mod;
        self.temp['secure']                     = packet.getByte() == 1;
        self.temp['botscount']                  = packet.getByte();
    def _parse_info(self, packet):
    
        # REMEMBER !! ALL KEY NAMES MUST BE NORMALIZED FOR EVERY PROTOCOL !!
        self.queryResponse["protocol"]          = packet.getByte();
        self.queryResponse["hostname"]          = packet.getString();
        self.queryResponse['mapname']           = packet.getString()
        self.queryResponse['game']              = packet.getString()
        self.queryResponse['gamename']          = packet.getString()
        self.queryResponse['steam_appid']       = packet.getShort()
        self.queryResponse['playerscount']      = packet.getByte()
        self.queryResponse['playersmax']        = packet.getByte()
        self.queryResponse['botscount']         = packet.getByte()
        servertype = chr(packet.getByte()).upper();
        self.queryResponse['servertype']        = "Dedicated" if servertype == "D" else \
                                                  "Listen";
        os = chr(packet.getByte()).upper()
        self.queryResponse['os']                = "Linux" if os == "L" else \
                                                  "Windows";
        self.queryResponse['password']          = packet.getByte() == 1;
        self.queryResponse['secure']            = packet.getByte() == 1;
        
        # now the real fun begins :) some of below values may be present, but also may not be present. 
        # most of people names that protocol horrible because of that...
        #
        # i think it's awesome :D
        if self.queryResponse['game'] == "ship":
            # first of all. The ship game have some more keys right here. 
            self.queryResponse['ship_mode']     = SHIP_GAME_MODES[packet.getByte()];
            self.queryResponse['ship_witnesses']= packet.getByte();
            self.queryResponse['ship_duration'] = packet.getByte(); 
        
        # this is always here.
        self.queryResponse['serverversion']     = packet.getString();
        
        # now EDF - Extra Data Flag. Yey!
        # packet might be cutted here, so rest of fields are optional
        # including one with flags that tells us which one are present and which one are not present.
        # 
        try:
            edf = packet.getByte();
            
            if edf & 0x80:
                self.queryResponse['gameport']  = packet.getShort();
                
            if edf & 0x10:
                self.queryResponse['steamid']   = packet.getLongLong();
                
            if edf & 0x40:
                self.queryResponse['spectport'] = packet.getShort();
                self.queryResponse['spectname'] = packet.getString();
                
            if edf & 0x20:
                self.queryResponse['keywords']  = packet.getString();
                
            if edf & 0x01:
                self.queryResponse['gameid']    = packet.getLongLOng();
        except:
            # in case that there is no EDF flags at all...
            pass;
            
    def _parse_players(self, packet):
        players_num = packet.getByte();
        
        players = [];
        for x in xrange(players_num):
            players.append({
                'index'     : packet.getByte(),
                'name'      : packet.getString(),
                'score'     : packet.getLong(),
                'playtime'  : packet.getFloat()
            });
            
        self.queryResponse['players'] = players;
    
    def _parse_rules(self, packet):
        rules_num = packet.getShort();
        
        rules = {};
        for x in xrange(rules_num):
            name = packet.getString();
            rules[name] = packet.getString();

        self.queryResponse['rules'] = rules;
        
    def writable(self):
        return (len(self.buffer) > 0);
        
    def handle_write(self):
        sent = self.send(self.buffer);
        self.buffer = self.buffer[sent:];
