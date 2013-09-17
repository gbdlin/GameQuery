#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
	This is an useful library, that can query many of game servers at once (asynchronous)
   Support of query'ing game depends on xxxQuery.py files in that directory.
   This means that if SourceQuery.py is present, you can query Source engine servers.
"""

import StringIO, struct, asyncore

class QueryPacket(StringIO.StringIO):
    # putting and getting values
    def putByte(self, val):
        self.write(struct.pack('<B', val))

    def getByte(self):
        return struct.unpack('<B', self.read(1))[0]

    def putShort(self, val):
        self.write(struct.pack('<h', val))

    def getShort(self):
        return struct.unpack('<h', self.read(2))[0]

    def putLong(self, val):
        self.write(struct.pack('<l', val))

    def getLong(self):
        return struct.unpack('<l', self.read(4))[0]

    def getLongLong(self):
        return struct.unpack('<Q', self.read(8))[0]

    def putFloat(self, val):
        self.write(struct.pack('<f', val))

    def getFloat(self):
        return struct.unpack('<f', self.read(4))[0]

    def putString(self, val):
        self.write(val + '\x00')

    def getString(self):
        val = self.getvalue()
        start = self.tell()
        end = val.index('\0', start)
        val = val[start:end]
        self.seek(end+1)
        return val

class GameQuery(object):
	def __init__(self, serverList={}, timeout=10):
	
		self.queryList = {};
		self.responseList = {};
		
		for name in serverList.keys():
			if len(serverList[name]) == 3 :
				engine, ip, port = serverList[name];
				extrainfo = {}
			else:
				engine, ip, port, extrainfo = serverList[name];
			
			try:
				_className = "%sQuery" % engine
				_mod = __import__("GameQuery.%s" % (_className), fromlist=[_className]);
				_class = getattr(_mod, _className);
				
				self.queryList[name] = _class((ip, port), timeout, extrainfo);
				
			except ImportError:
				print "Engine \"%s\" is not supported" % (engine);

	def getQuery(self):
		for name in self.queryList.keys():
			if name in self.responseList:
				self.queryList[name].reset();
			self.queryList[name].connect();
		asyncore.loop();
		
		self.responseList = {};
		
		for name in self.queryList.keys():
			self.responseList[name] = self.queryList[name].queryResponse;
		
		return self.responseList;